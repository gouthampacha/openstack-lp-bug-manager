"""Tests for CLI commands."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from lp_bug_manager.cli import main
from tests.conftest import make_search_result


@pytest.fixture
def runner():
    return CliRunner()


class TestReleases:
    def test_lists_cycles(self, runner):
        result = runner.invoke(main, ["releases"])
        assert result.exit_code == 0
        assert "Gazpacho" in result.output
        assert "2026.1" in result.output
        assert "Epoxy" in result.output
        assert "Flamingo" in result.output


class TestSearch:
    @patch("lp_bug_manager.cli.bugs.search_bugs")
    def test_no_results(self, mock_search, runner):
        mock_search.return_value = []
        result = runner.invoke(main, ["search", "manila", "-s", "New"])
        assert result.exit_code == 0
        assert "No bugs found" in result.output

    @patch("lp_bug_manager.cli.bugs.search_bugs")
    def test_displays_results(self, mock_search, runner):
        mock_search.return_value = [
            make_search_result(
                2143047,
                "Netapp: Add support for force-delete",
                status="New",
                importance="Undecided",
            ),
        ]
        result = runner.invoke(main, ["search", "manila", "-s", "New"])
        assert result.exit_code == 0
        assert "2143047" in result.output
        assert "Netapp" in result.output

    @patch("lp_bug_manager.cli.bugs.search_bugs")
    def test_since_days_shorthand(self, mock_search, runner):
        mock_search.return_value = []
        result = runner.invoke(main, ["search", "manila", "--since", "30d"])
        assert result.exit_code == 0
        kwargs = mock_search.call_args[1]
        assert kwargs["created_since"] is not None

    @patch("lp_bug_manager.cli.bugs.search_bugs")
    def test_since_iso_date(self, mock_search, runner):
        mock_search.return_value = []
        result = runner.invoke(main, ["search", "manila", "--since", "2026-01-01"])
        assert result.exit_code == 0
        kwargs = mock_search.call_args[1]
        assert kwargs["created_since"].year == 2026
        assert kwargs["created_since"].month == 1


class TestShow:
    @patch("lp_bug_manager.cli.bugs.get_bug")
    def test_displays_bug(self, mock_get, runner):
        mock_get.return_value = {
            "id": 2144047,
            "title": "Resource Locks panel",
            "description": "Add ability to create resource locks",
            "tags": ["ui", "locks"],
            "web_link": "https://bugs.launchpad.net/manila-ui/+bug/2144047",
            "created": datetime(2026, 3, 1, tzinfo=timezone.utc),
            "updated": datetime(2026, 3, 12, tzinfo=timezone.utc),
            "tasks": [
                {
                    "target": "manila-ui",
                    "status": "New",
                    "importance": "Medium",
                    "assignee": "Rose Kimondo",
                }
            ],
        }
        result = runner.invoke(main, ["show", "2144047"])
        assert result.exit_code == 0
        assert "Resource Locks panel" in result.output
        assert "Rose Kimondo" in result.output
        assert "ui, locks" in result.output


class TestScrub:
    @patch("lp_bug_manager.cli.analytics.scrub_report")
    def test_single_project(self, mock_scrub, runner):
        mock_scrub.return_value = {
            "new": [make_search_result(1, "Untriaged bug")],
            "incomplete": [],
            "unassigned_triaged": [],
            "stale_in_progress": [],
            "recent": [],
        }
        result = runner.invoke(main, ["scrub", "manila"])
        assert result.exit_code == 0
        assert "Untriaged bug" in result.output
        assert "New / Untriaged (1)" in result.output
        mock_scrub.assert_called_once_with("manila", days=None, stale_days=30)

    @patch("lp_bug_manager.cli.analytics.scrub_report")
    def test_with_days(self, mock_scrub, runner):
        mock_scrub.return_value = {
            "new": [],
            "incomplete": [],
            "unassigned_triaged": [],
            "stale_in_progress": [],
            "recent": [],
        }
        runner.invoke(main, ["scrub", "manila", "--days", "90"])
        mock_scrub.assert_called_once_with("manila", days=90, stale_days=30)

    @patch("lp_bug_manager.cli.analytics.scrub_report")
    def test_defaults_to_all_projects(self, mock_scrub, runner):
        mock_scrub.return_value = {
            "new": [],
            "incomplete": [],
            "unassigned_triaged": [],
            "stale_in_progress": [],
            "recent": [],
        }
        runner.invoke(main, ["scrub"])
        assert mock_scrub.call_count == 3
        projects = [c[0][0] for c in mock_scrub.call_args_list]
        assert "manila" in projects
        assert "manila-ui" in projects
        assert "python-manilaclient" in projects


class TestSummary:
    @patch("lp_bug_manager.cli.analytics.cycle_summary")
    def test_displays_summary(self, mock_summary, runner):
        mock_summary.return_value = {
            "version": "2026.1",
            "cycle": {"name": "Gazpacho", "start": "2025-10-01", "end": "2026-04-01"},
            "reported_count": 13,
            "fixed_count": 65,
            "still_open": [],
            "importance_breakdown": {"High": 1, "Medium": 2},
            "status_breakdown": {"New": 5, "Triaged": 5},
            "top_reporters": [],
            "top_fixers": [("kiran pawar", 15), ("Carlos da Silva", 6)],
        }
        result = runner.invoke(main, ["summary", "Gazpacho", "manila"])
        assert result.exit_code == 0
        assert "Gazpacho" in result.output
        assert "13" in result.output
        assert "65" in result.output
        assert "kiran pawar" in result.output

    @patch("lp_bug_manager.cli.analytics.cycle_summary")
    def test_defaults_to_all_projects(self, mock_summary, runner):
        mock_summary.return_value = {
            "version": "2026.1",
            "cycle": {"name": "Gazpacho", "start": "2025-10-01", "end": "2026-04-01"},
            "reported_count": 0,
            "fixed_count": 0,
            "still_open": [],
            "importance_breakdown": {},
            "status_breakdown": {},
            "top_reporters": [],
            "top_fixers": [],
        }
        runner.invoke(main, ["summary", "Gazpacho"])
        assert mock_summary.call_count == 3
