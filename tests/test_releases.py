"""Tests for release cycle definitions."""

from datetime import date
from unittest.mock import patch

from lp_bug_manager.releases import (
    get_cycle,
    get_milestone_pattern,
    get_milestones_for_project,
    list_cycles,
)


def _mock_resolve(project_name, codename):
    """Simulate openstack/releases lookup for test projects."""
    models = {
        "manila": ("cycle-with-rc", "service"),
        "manila-ui": ("cycle-with-rc", "horizon-plugin"),
        "python-manilaclient": ("cycle-with-intermediary", "client-library"),
    }
    return models.get(project_name, (None, None))


class TestGetCycle:
    def test_lookup_by_version(self):
        version, cycle = get_cycle("2026.1")
        assert version == "2026.1"
        assert cycle["name"] == "Gazpacho"
        assert cycle["start"] == date(2025, 10, 1)
        assert cycle["end"] == date(2026, 4, 2)

    def test_lookup_by_codename(self):
        version, cycle = get_cycle("Gazpacho")
        assert version == "2026.1"
        assert cycle["name"] == "Gazpacho"

    def test_lookup_by_codename_case_insensitive(self):
        version, cycle = get_cycle("gazpacho")
        assert version == "2026.1"

    def test_lookup_unknown(self):
        version, cycle = get_cycle("nonexistent")
        assert version is None
        assert cycle is None


class TestListCycles:
    def test_returns_all_cycles(self):
        cycles = list_cycles()
        assert "2025.1" in cycles
        assert "2025.2" in cycles
        assert "2026.1" in cycles
        assert "2026.2" in cycles

    def test_cycle_has_required_fields(self):
        cycles = list_cycles()
        for version, info in cycles.items():
            assert "name" in info
            assert "start" in info
            assert "end" in info
            assert "milestones" in info
            assert info["start"] < info["end"]


@patch("lp_bug_manager.releases._resolve_release_info", side_effect=_mock_resolve)
class TestGetMilestonesForProject:
    def test_manila_gets_four_milestones(self, mock_resolve):
        milestones = get_milestones_for_project("manila", "Hibiscus")
        names = [name for name, _ in milestones]
        assert names == [
            "hibiscus-1",
            "hibiscus-2",
            "hibiscus-3",
            "hibiscus-rc1",
        ]

    def test_manila_ui_matches_manila(self, mock_resolve):
        manila = get_milestones_for_project("manila", "Hibiscus")
        manila_ui = get_milestones_for_project("manila-ui", "Hibiscus")
        assert [n for n, _ in manila] == [n for n, _ in manila_ui]

    def test_manilaclient_gets_client_release(self, mock_resolve):
        milestones = get_milestones_for_project("python-manilaclient", "Hibiscus")
        names = [name for name, _ in milestones]
        assert names == [
            "hibiscus-1",
            "hibiscus-2",
            "hibiscus-client-release",
        ]

    def test_client_release_uses_milestone3_date(self, mock_resolve):
        client_ms = get_milestones_for_project("python-manilaclient", "Hibiscus")
        manila_ms = get_milestones_for_project("manila", "Hibiscus")
        # client-release date should match manila's milestone 3 date
        client_release_date = client_ms[-1][1]
        manila_m3_date = manila_ms[2][1]  # index 2 = milestone 3
        assert client_release_date == manila_m3_date

    def test_milestone_dates_are_set(self, mock_resolve):
        milestones = get_milestones_for_project("manila", "Gazpacho")
        for name, ms_date in milestones:
            assert ms_date is not None
            assert isinstance(ms_date, date)

    def test_unknown_cycle_raises(self, mock_resolve):
        import pytest

        with pytest.raises(ValueError, match="Unknown release cycle"):
            get_milestones_for_project("manila", "Nonexistent")


@patch("lp_bug_manager.releases._resolve_release_info")
class TestGetMilestonePattern:
    def test_falls_back_to_cycle_with_rc(self, mock_resolve):
        mock_resolve.return_value = (None, None)
        pattern = get_milestone_pattern("unknown-project", "Hibiscus")
        assert pattern == ["1", "2", "3", "rc1"]

    def test_client_library_pattern(self, mock_resolve):
        mock_resolve.return_value = ("cycle-with-intermediary", "client-library")
        pattern = get_milestone_pattern("python-manilaclient", "Hibiscus")
        assert pattern == ["1", "2", "client-release"]

    def test_cycle_with_rc_pattern(self, mock_resolve):
        mock_resolve.return_value = ("cycle-with-rc", "service")
        pattern = get_milestone_pattern("manila", "Hibiscus")
        assert pattern == ["1", "2", "3", "rc1"]
