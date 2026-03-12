"""Tests for release cycle definitions."""

from datetime import date

from lp_bug_manager.releases import get_cycle, list_cycles


class TestGetCycle:
    def test_lookup_by_version(self):
        version, cycle = get_cycle("2026.1")
        assert version == "2026.1"
        assert cycle["name"] == "Gazpacho"
        assert cycle["start"] == date(2025, 10, 1)
        assert cycle["end"] == date(2026, 4, 1)

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

    def test_cycle_has_required_fields(self):
        cycles = list_cycles()
        for version, info in cycles.items():
            assert "name" in info
            assert "start" in info
            assert "end" in info
            assert info["start"] < info["end"]
