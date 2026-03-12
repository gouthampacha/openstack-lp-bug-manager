"""Tests for analytics module."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from lp_bug_manager.analytics import (
    bugs_reported_in_cycle, bugs_fixed_in_cycle, rotten_bugs,
    scrub_report, cycle_summary,
)
from tests.conftest import make_search_result


@patch("lp_bug_manager.analytics.search_bugs")
class TestBugsReportedInCycle:
    def test_queries_cycle_date_range(self, mock_search):
        mock_search.return_value = []
        bugs_reported_in_cycle("manila", "Gazpacho")

        kwargs = mock_search.call_args[1]
        assert kwargs["created_since"].year == 2025
        assert kwargs["created_since"].month == 10
        assert kwargs["created_before"].year == 2026
        assert kwargs["created_before"].month == 4

    def test_returns_search_results(self, mock_search):
        mock_search.return_value = [
            make_search_result(1, "Bug A"),
            make_search_result(2, "Bug B"),
        ]
        result = bugs_reported_in_cycle("manila", "2026.1")
        assert len(result) == 2

    def test_unknown_cycle_raises(self, mock_search):
        with pytest.raises(ValueError, match="Unknown release cycle"):
            bugs_reported_in_cycle("manila", "Nonexistent")


@patch("lp_bug_manager.analytics.search_bugs")
class TestBugsFixedInCycle:
    def test_queries_both_fix_statuses(self, mock_search):
        mock_search.return_value = []
        bugs_fixed_in_cycle("manila", "Gazpacho")

        calls = mock_search.call_args_list
        statuses = [c[1]["status"] for c in calls]
        assert "Fix Committed" in statuses
        assert "Fix Released" in statuses

    def test_uses_modified_since(self, mock_search):
        mock_search.return_value = []
        bugs_fixed_in_cycle("manila", "Gazpacho")

        for call in mock_search.call_args_list:
            assert "modified_since" in call[1]

    def test_filters_out_bugs_updated_after_cycle_end(self, mock_search):
        in_cycle = make_search_result(
            1, "Fixed in cycle", status="Fix Committed",
            updated=datetime(2026, 2, 1, tzinfo=timezone.utc))
        after_cycle = make_search_result(
            2, "Fixed after cycle", status="Fix Released",
            updated=datetime(2026, 5, 1, tzinfo=timezone.utc))

        # First call (Fix Committed) returns the in-cycle bug,
        # second call (Fix Released) returns the after-cycle bug
        mock_search.side_effect = [[in_cycle], [after_cycle]]

        result = bugs_fixed_in_cycle("manila", "Gazpacho")
        assert len(result) == 1
        assert result[0]["id"] == 1


@patch("lp_bug_manager.analytics.search_bugs")
class TestRottenBugs:
    def test_finds_inactive_bugs(self, mock_search):
        old_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        recent_date = datetime(2026, 3, 1, tzinfo=timezone.utc)

        def side_effect(project, status=None, **kwargs):
            if status == "New":
                return [
                    make_search_result(1, "Old bug", status="New",
                                       updated=old_date),
                    make_search_result(2, "Recent bug", status="New",
                                       updated=recent_date),
                ]
            return []

        mock_search.side_effect = side_effect
        result = rotten_bugs("manila", days=180)

        assert len(result) == 1
        assert result[0]["id"] == 1
        assert "days_inactive" in result[0]

    def test_sorted_by_staleness(self, mock_search):
        def side_effect(project, status=None, **kwargs):
            if status == "New":
                return [
                    make_search_result(1, "Kinda old", status="New",
                                       updated=datetime(2025, 6, 1, tzinfo=timezone.utc)),
                    make_search_result(2, "Very old", status="New",
                                       updated=datetime(2024, 1, 1, tzinfo=timezone.utc)),
                ]
            return []

        mock_search.side_effect = side_effect
        result = rotten_bugs("manila", days=180)

        assert result[0]["id"] == 2  # oldest first


@patch("lp_bug_manager.analytics.search_bugs")
class TestScrubReport:
    def test_returns_all_sections(self, mock_search):
        mock_search.return_value = []
        report = scrub_report("manila")

        assert "new" in report
        assert "incomplete" in report
        assert "unassigned_triaged" in report
        assert "stale_in_progress" in report
        assert "recent" in report

    def test_filters_unassigned_triaged(self, mock_search):
        def side_effect(project, status=None, **kwargs):
            if status == ["Confirmed", "Triaged"]:
                return [
                    make_search_result(1, "Assigned", status="Triaged",
                                       assignee="gouthamr"),
                    make_search_result(2, "Unassigned", status="Triaged",
                                       assignee="Unassigned"),
                ]
            return []

        mock_search.side_effect = side_effect
        report = scrub_report("manila")

        assert len(report["unassigned_triaged"]) == 1
        assert report["unassigned_triaged"][0]["id"] == 2

    def test_stale_in_progress(self, mock_search):
        old = datetime(2025, 1, 1, tzinfo=timezone.utc)
        recent = datetime(2026, 3, 10, tzinfo=timezone.utc)

        def side_effect(project, status=None, **kwargs):
            if status == "In Progress":
                return [
                    make_search_result(1, "Stale", status="In Progress",
                                       updated=old),
                    make_search_result(2, "Active", status="In Progress",
                                       updated=recent),
                ]
            return []

        mock_search.side_effect = side_effect
        report = scrub_report("manila")

        assert len(report["stale_in_progress"]) == 1
        assert report["stale_in_progress"][0]["id"] == 1
        assert "days_inactive" in report["stale_in_progress"][0]

    def test_days_param_scopes_queries(self, mock_search):
        mock_search.return_value = []
        scrub_report("manila", days=30)

        # new, incomplete, and triaged queries should have created_since
        for call in mock_search.call_args_list:
            kwargs = call[1]
            status = kwargs.get("status")
            if status in ["New", "Incomplete", ["Confirmed", "Triaged"]]:
                assert "created_since" in kwargs


@patch("lp_bug_manager.analytics.bugs_fixed_in_cycle")
@patch("lp_bug_manager.analytics.bugs_reported_in_cycle")
class TestCycleSummary:
    def test_computes_stats(self, mock_reported, mock_fixed):
        mock_reported.return_value = [
            make_search_result(1, "Bug A", importance="High",
                               status="Fix Released", assignee="alice"),
            make_search_result(2, "Bug B", importance="Medium",
                               status="New", assignee="Unassigned"),
            make_search_result(3, "Bug C", importance="High",
                               status="In Progress", assignee="bob"),
        ]
        mock_fixed.return_value = [
            make_search_result(1, "Bug A", status="Fix Released",
                               assignee="alice"),
            make_search_result(4, "Old bug", status="Fix Released",
                               assignee="alice"),
        ]

        s = cycle_summary("manila", "Gazpacho")

        assert s["reported_count"] == 3
        assert s["fixed_count"] == 2
        assert s["importance_breakdown"]["High"] == 2
        assert s["importance_breakdown"]["Medium"] == 1
        assert s["status_breakdown"]["New"] == 1
        assert len(s["still_open"]) == 2  # Bug B (New) and Bug C (In Progress)

    def test_top_fixers_sorted(self, mock_reported, mock_fixed):
        mock_reported.return_value = []
        mock_fixed.return_value = [
            make_search_result(1, "A", assignee="alice"),
            make_search_result(2, "B", assignee="bob"),
            make_search_result(3, "C", assignee="alice"),
        ]

        s = cycle_summary("manila", "Gazpacho")

        assert s["top_fixers"][0] == ("alice", 2)
        assert s["top_fixers"][1] == ("bob", 1)

    def test_unknown_cycle_raises(self, mock_reported, mock_fixed):
        mock_reported.side_effect = ValueError("Unknown release cycle")
        with pytest.raises(ValueError):
            cycle_summary("manila", "Nonexistent")
