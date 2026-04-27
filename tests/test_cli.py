"""Tests for CLI commands."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

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


class TestShowFetchPatches:
    @patch("lp_bug_manager.cli.bugs.fetch_patches")
    @patch("lp_bug_manager.cli.bugs.get_bug")
    def test_downloads_patches(self, mock_get, mock_fetch, runner):
        mock_get.return_value = {
            "id": 2148398,
            "title": "Crash on resize",
            "description": "desc",
            "tags": [],
            "web_link": "https://bugs.launchpad.net/manila/+bug/2148398",
            "created": datetime(2026, 3, 1, tzinfo=timezone.utc),
            "updated": datetime(2026, 3, 12, tzinfo=timezone.utc),
            "tasks": [
                {
                    "target": "manila",
                    "status": "New",
                    "importance": "Medium",
                    "assignee": "Unassigned",
                }
            ],
        }
        mock_fetch.return_value = ["/tmp/fix.patch"]

        result = runner.invoke(main, ["show", "2148398", "--fetch-patches"])
        assert result.exit_code == 0
        assert "fix.patch" in result.output
        assert "Downloaded 1 patch(es)" in result.output

    @patch("lp_bug_manager.cli.bugs.fetch_patches")
    @patch("lp_bug_manager.cli.bugs.get_bug")
    def test_no_patches(self, mock_get, mock_fetch, runner):
        mock_get.return_value = {
            "id": 100,
            "title": "Test bug",
            "description": "desc",
            "tags": [],
            "web_link": "https://bugs.launchpad.net/manila/+bug/100",
            "created": datetime(2026, 3, 1, tzinfo=timezone.utc),
            "updated": datetime(2026, 3, 12, tzinfo=timezone.utc),
            "tasks": [
                {
                    "target": "manila",
                    "status": "New",
                    "importance": "Medium",
                    "assignee": "Unassigned",
                }
            ],
        }
        mock_fetch.return_value = []

        result = runner.invoke(main, ["show", "100", "--fetch-patches"])
        assert result.exit_code == 0
        assert "No patch attachments found" in result.output


class TestUpdate:
    @patch("lp_bug_manager.cli.bugs.update_bug")
    @patch("lp_bug_manager.client.get_project")
    def test_inactive_milestone_prompts(self, mock_get_project, mock_update, runner):
        project = MagicMock()
        mock_get_project.return_value = project

        ms = MagicMock()
        ms.is_active = False
        project.getMilestone.return_value = ms

        mock_bug = MagicMock()
        mock_bug.id = 100
        mock_bug.web_link = "https://bugs.launchpad.net/manila/+bug/100"
        mock_update.return_value = mock_bug

        result = runner.invoke(
            main, ["update", "100", "manila", "--milestone", "gazpacho-2"], input="y\n"
        )
        assert result.exit_code == 0
        assert "inactive" in result.output
        assert "deactivated again" in result.output
        # Activated then deactivated
        assert ms.is_active is False
        assert ms.lp_save.call_count == 2

    @patch("lp_bug_manager.cli.bugs.update_bug")
    @patch("lp_bug_manager.client.get_project")
    def test_inactive_milestone_abort(self, mock_get_project, mock_update, runner):
        project = MagicMock()
        mock_get_project.return_value = project

        ms = MagicMock()
        ms.is_active = False
        project.getMilestone.return_value = ms

        result = runner.invoke(
            main, ["update", "100", "manila", "--milestone", "gazpacho-2"], input="n\n"
        )
        assert result.exit_code == 0
        assert "Aborted" in result.output
        mock_update.assert_not_called()

    @patch("lp_bug_manager.cli.bugs.update_bug")
    @patch("lp_bug_manager.client.get_project")
    def test_inactive_milestone_yes_flag(self, mock_get_project, mock_update, runner):
        project = MagicMock()
        mock_get_project.return_value = project

        ms = MagicMock()
        ms.is_active = False
        project.getMilestone.return_value = ms

        mock_bug = MagicMock()
        mock_bug.id = 100
        mock_bug.web_link = "https://bugs.launchpad.net/manila/+bug/100"
        mock_update.return_value = mock_bug

        result = runner.invoke(
            main, ["update", "100", "manila", "--milestone", "gazpacho-2", "--yes"]
        )
        assert result.exit_code == 0
        assert "Temporarily activate" not in result.output
        assert "deactivated again" in result.output
        mock_update.assert_called_once()

    @patch("lp_bug_manager.cli.bugs.subscribe_bug")
    def test_subscribe_option(self, mock_subscribe, runner):
        result = runner.invoke(main, ["update", "2150316", "--subscribe", "oslo-coresec"])
        assert result.exit_code == 0
        assert "Subscribed 'oslo-coresec' to bug #2150316" in result.output
        mock_subscribe.assert_called_once_with(2150316, "oslo-coresec")

    @patch("lp_bug_manager.cli.bugs.link_cve")
    def test_link_cve_option(self, mock_link, runner):
        mock_link.return_value = MagicMock()
        result = runner.invoke(main, ["update", "2138575", "--link-cve", "CVE-2026-40212"])
        assert result.exit_code == 0
        assert "Linked CVE-2026-40212 to bug #2138575" in result.output
        mock_link.assert_called_once_with(2138575, "CVE-2026-40212")

    @patch("lp_bug_manager.cli.bugs.link_cve")
    def test_link_cve_not_found(self, mock_link, runner):
        mock_link.side_effect = ValueError("CVE-9999-99999 not found")
        result = runner.invoke(main, ["update", "100", "--link-cve", "CVE-9999-99999"])
        assert result.exit_code != 0
        assert "not found" in result.output

    @patch("lp_bug_manager.cli.bugs.add_gerrit_link")
    def test_link_gerrit_option(self, mock_gerrit, runner):
        mock_gerrit.return_value = MagicMock()
        result = runner.invoke(
            main,
            [
                "update",
                "100",
                "--link-gerrit",
                "https://review.opendev.org/c/openstack/manila/+/976962",
            ],
        )
        assert result.exit_code == 0
        assert "Linked Gerrit review" in result.output
        mock_gerrit.assert_called_once()

    @patch("lp_bug_manager.cli.bugs.update_bug")
    @patch("lp_bug_manager.cli.bugs.subscribe_bug")
    def test_subscribe_with_status_update(self, mock_subscribe, mock_update, runner):
        mock_bug = MagicMock()
        mock_bug.id = 100
        mock_bug.web_link = "https://bugs.launchpad.net/manila/+bug/100"
        mock_update.return_value = mock_bug

        result = runner.invoke(
            main, ["update", "100", "manila", "-s", "Triaged", "--subscribe", "nova-coresec"]
        )
        assert result.exit_code == 0
        mock_update.assert_called_once()
        mock_subscribe.assert_called_once_with(100, "nova-coresec")

    @patch("lp_bug_manager.cli.bugs.update_bug")
    @patch("lp_bug_manager.client.get_project")
    def test_active_milestone_no_prompt(self, mock_get_project, mock_update, runner):
        project = MagicMock()
        mock_get_project.return_value = project

        ms = MagicMock()
        ms.is_active = True
        project.getMilestone.return_value = ms

        mock_bug = MagicMock()
        mock_bug.id = 100
        mock_bug.web_link = "https://bugs.launchpad.net/manila/+bug/100"
        mock_update.return_value = mock_bug

        result = runner.invoke(main, ["update", "100", "manila", "--milestone", "gazpacho-3"])
        assert result.exit_code == 0
        assert "inactive" not in result.output
        assert "deactivated" not in result.output
        ms.lp_save.assert_not_called()


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


def _mock_resolve(project_name, codename):
    """Simulate openstack/releases lookup for test projects."""
    models = {
        "manila": ("cycle-with-rc", "service"),
        "manila-ui": ("cycle-with-rc", "horizon-plugin"),
        "python-manilaclient": ("cycle-with-intermediary", "client-library"),
    }
    return models.get(project_name, (None, None))


@patch("lp_bug_manager.releases._resolve_release_info", side_effect=_mock_resolve)
class TestCreateRelease:
    def test_dry_run_shows_plan(self, mock_resolve, runner):
        result = runner.invoke(main, ["create-release", "Hibiscus", "manila", "--dry-run"])
        assert result.exit_code == 0
        assert "Would create series: hibiscus (2026.2)" in result.output
        assert "hibiscus-1" in result.output
        assert "hibiscus-2" in result.output
        assert "hibiscus-3" in result.output
        assert "hibiscus-rc1" in result.output

    def test_dry_run_manilaclient(self, mock_resolve, runner):
        result = runner.invoke(
            main, ["create-release", "Hibiscus", "python-manilaclient", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "hibiscus-client-release" in result.output
        assert "hibiscus-3" not in result.output
        assert "hibiscus-rc1" not in result.output

    def test_dry_run_defaults_to_all_projects(self, mock_resolve, runner):
        result = runner.invoke(main, ["create-release", "Hibiscus", "--dry-run"])
        assert result.exit_code == 0
        assert "manila\n" in result.output
        assert "manila-ui" in result.output
        assert "python-manilaclient" in result.output

    def test_unknown_cycle_errors(self, mock_resolve, runner):
        result = runner.invoke(main, ["create-release", "Nonexistent", "--dry-run"])
        assert result.exit_code != 0
        assert "Unknown release cycle" in result.output

    @patch("lp_bug_manager.client.get_project")
    def test_creates_series_and_milestones(self, mock_get_project, mock_resolve, runner):
        project = MagicMock()
        mock_get_project.return_value = project
        project.series = []

        series = MagicMock()
        project.newSeries.return_value = series
        series.all_milestones = []

        result = runner.invoke(main, ["create-release", "Hibiscus", "manila"])
        assert result.exit_code == 0
        project.newSeries.assert_called_once()
        assert series.newMilestone.call_count == 4

    @patch("lp_bug_manager.client.get_project")
    def test_skips_existing_series(self, mock_get_project, mock_resolve, runner):
        project = MagicMock()
        mock_get_project.return_value = project

        existing_series = MagicMock()
        existing_series.name = "hibiscus"
        existing_series.all_milestones = []
        project.series = [existing_series]

        result = runner.invoke(main, ["create-release", "Hibiscus", "manila"])
        assert result.exit_code == 0
        assert "already exists, skipping creation" in result.output
        project.newSeries.assert_not_called()

    @patch("lp_bug_manager.client.get_project")
    def test_skips_existing_milestones(self, mock_get_project, mock_resolve, runner):
        project = MagicMock()
        mock_get_project.return_value = project
        project.series = []

        series = MagicMock()
        project.newSeries.return_value = series
        existing_ms = MagicMock()
        existing_ms.name = "hibiscus-1"
        series.all_milestones = [existing_ms]

        result = runner.invoke(main, ["create-release", "Hibiscus", "manila"])
        assert result.exit_code == 0
        # Should create 3 milestones (skipping hibiscus-1)
        assert series.newMilestone.call_count == 3


class TestRetarget:
    @patch("lp_bug_manager.cli.bugs.retarget_bugs")
    def test_dry_run(self, mock_retarget, runner):
        mock_retarget.return_value = [
            make_search_result(800, "Open bug", status="Triaged", importance="Medium"),
        ]
        result = runner.invoke(
            main, ["retarget", "manila", "gazpacho-2", "--to", "gazpacho-3", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "Would retarget 1 open bug(s)" in result.output
        assert "800" in result.output
        assert "Open bug" in result.output
        mock_retarget.assert_called_once_with("manila", "gazpacho-2", "gazpacho-3", dry_run=True)

    @patch("lp_bug_manager.cli.bugs.retarget_bugs")
    def test_retargets_bugs(self, mock_retarget, runner):
        mock_retarget.return_value = [
            make_search_result(801, "Bug A"),
            make_search_result(802, "Bug B"),
        ]
        result = runner.invoke(main, ["retarget", "manila", "gazpacho-2", "--to", "gazpacho-3"])
        assert result.exit_code == 0
        assert "Retargeted 2 open bug(s)" in result.output
        assert "801" in result.output
        assert "802" in result.output
        mock_retarget.assert_called_once_with("manila", "gazpacho-2", "gazpacho-3", dry_run=False)

    @patch("lp_bug_manager.cli.bugs.retarget_bugs")
    def test_no_open_bugs(self, mock_retarget, runner):
        mock_retarget.return_value = []
        result = runner.invoke(main, ["retarget", "manila", "gazpacho-2", "--to", "gazpacho-3"])
        assert result.exit_code == 0
        assert "Retargeted 0 open bug(s)" in result.output

    @patch("lp_bug_manager.cli.bugs.deactivate_milestone")
    @patch("lp_bug_manager.cli.bugs.retarget_bugs")
    def test_deactivate_flag(self, mock_retarget, mock_deactivate, runner):
        mock_retarget.return_value = []
        result = runner.invoke(
            main,
            ["retarget", "manila", "gazpacho-2", "--to", "gazpacho-3", "--deactivate"],
        )
        assert result.exit_code == 0
        assert "Deactivated milestone: gazpacho-2" in result.output
        mock_deactivate.assert_called_once_with("manila", "gazpacho-2")

    @patch("lp_bug_manager.cli.bugs.retarget_bugs")
    def test_deactivate_dry_run(self, mock_retarget, runner):
        mock_retarget.return_value = []
        result = runner.invoke(
            main,
            [
                "retarget",
                "manila",
                "gazpacho-2",
                "--to",
                "gazpacho-3",
                "--deactivate",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "Would deactivate milestone: gazpacho-2" in result.output


class TestSetFocus:
    @patch("lp_bug_manager.client.get_project")
    def test_updates_focus(self, mock_get_project, runner):
        project = MagicMock()
        mock_get_project.return_value = project

        current_series = MagicMock()
        current_series.name = "gazpacho"
        project.development_focus = current_series

        new_series = MagicMock()
        new_series.name = "hibiscus"
        project.series = [current_series, new_series]

        result = runner.invoke(main, ["set-focus", "manila", "hibiscus"], input="y\n")
        assert result.exit_code == 0
        assert "Current focus:     gazpacho" in result.output
        assert "New focus:         hibiscus" in result.output
        assert project.development_focus == new_series
        project.lp_save.assert_called_once()

    @patch("lp_bug_manager.client.get_project")
    def test_yes_skips_prompt(self, mock_get_project, runner):
        project = MagicMock()
        mock_get_project.return_value = project

        current_series = MagicMock()
        current_series.name = "gazpacho"
        project.development_focus = current_series

        new_series = MagicMock()
        new_series.name = "hibiscus"
        project.series = [current_series, new_series]

        result = runner.invoke(main, ["set-focus", "manila", "hibiscus", "--yes"])
        assert result.exit_code == 0
        assert "Update development focus?" not in result.output
        assert project.development_focus == new_series
        project.lp_save.assert_called_once()

    @patch("lp_bug_manager.client.get_project")
    def test_aborts_on_no(self, mock_get_project, runner):
        project = MagicMock()
        mock_get_project.return_value = project

        current_series = MagicMock()
        current_series.name = "gazpacho"
        project.development_focus = current_series

        new_series = MagicMock()
        new_series.name = "hibiscus"
        project.series = [current_series, new_series]

        result = runner.invoke(main, ["set-focus", "manila", "hibiscus"], input="n\n")
        assert result.exit_code == 0
        assert "Aborted" in result.output
        project.lp_save.assert_not_called()

    @patch("lp_bug_manager.client.get_project")
    def test_already_set(self, mock_get_project, runner):
        project = MagicMock()
        mock_get_project.return_value = project

        current_series = MagicMock()
        current_series.name = "hibiscus"
        project.development_focus = current_series

        result = runner.invoke(main, ["set-focus", "manila", "hibiscus"])
        assert result.exit_code == 0
        assert "already" in result.output
        project.lp_save.assert_not_called()

    @patch("lp_bug_manager.client.get_project")
    def test_unknown_series_errors(self, mock_get_project, runner):
        project = MagicMock()
        mock_get_project.return_value = project

        current_series = MagicMock()
        current_series.name = "gazpacho"
        project.development_focus = current_series
        project.series = [current_series]

        result = runner.invoke(main, ["set-focus", "manila", "nonexistent"])
        assert result.exit_code != 0
        assert "not found" in result.output


class TestIntake:
    @patch("lp_bug_manager.cli.vmt.intake_bug")
    def test_intake(self, mock_intake, runner):
        mock_intake.return_value = {
            "bug_id": 2150316,
            "advisory": "ossa",
            "actions": [
                "Prepended embargo reminder (expires 2026-07-26)",
                "Added 'ossa' task (Incomplete)",
                "Subscribed 'nova-coresec'",
                "Posted reception comment",
            ],
        }
        result = runner.invoke(main, ["intake", "2150316"])
        assert result.exit_code == 0
        assert "Intake for bug #2150316 (ossa)" in result.output
        assert "Subscribed 'nova-coresec'" in result.output
        mock_intake.assert_called_once_with(
            2150316, embargo_days=90, use_ossn=False, skip_subscribe=False, dry_run=False
        )

    @patch("lp_bug_manager.cli.vmt.intake_bug")
    def test_intake_dry_run(self, mock_intake, runner):
        mock_intake.return_value = {
            "bug_id": 2150316,
            "advisory": "ossa",
            "actions": ["Would prepend embargo reminder (expires 2026-07-26)"],
        }
        result = runner.invoke(main, ["intake", "2150316", "--dry-run"])
        assert result.exit_code == 0
        assert "[DRY RUN]" in result.output
        mock_intake.assert_called_once_with(
            2150316, embargo_days=90, use_ossn=False, skip_subscribe=False, dry_run=True
        )

    @patch("lp_bug_manager.cli.vmt.intake_bug")
    def test_intake_ossn(self, mock_intake, runner):
        mock_intake.return_value = {
            "bug_id": 100,
            "advisory": "ossn",
            "actions": [],
        }
        result = runner.invoke(main, ["intake", "100", "--ossn"])
        assert result.exit_code == 0
        assert "(ossn)" in result.output
        mock_intake.assert_called_once_with(
            100, embargo_days=90, use_ossn=True, skip_subscribe=False, dry_run=False
        )


class TestVmtDashboard:
    @patch("lp_bug_manager.cli.vmt.vmt_dashboard")
    def test_table_output(self, mock_dashboard, runner):
        mock_dashboard.return_value = {
            "me": "Goutham",
            "assigned": [
                make_search_result(1, "My bug", assignee="Goutham")
                | {"action": "Needs response", "advisory": "ossa"},
            ],
            "other": [
                make_search_result(2, "Other bug", assignee="Alice")
                | {"action": "Pending", "advisory": "ossn"},
            ],
        }

        result = runner.invoke(main, ["vmt-dashboard"])
        assert result.exit_code == 0
        assert "Goutham" in result.output
        assert "Assigned to me (1)" in result.output
        assert "Other open bugs (1)" in result.output
        assert "My bug" in result.output
        assert "Other bug" in result.output

    @patch("lp_bug_manager.cli.vmt.vmt_dashboard")
    def test_assigned_only(self, mock_dashboard, runner):
        mock_dashboard.return_value = {
            "me": "Goutham",
            "assigned": [],
        }

        result = runner.invoke(main, ["vmt-dashboard", "--assigned-only"])
        assert result.exit_code == 0
        assert "Assigned to me" in result.output
        assert "Other open bugs" not in result.output
        mock_dashboard.assert_called_once_with(assigned_only=True)

    @patch("lp_bug_manager.cli.vmt.vmt_dashboard")
    def test_json_output(self, mock_dashboard, runner):
        mock_dashboard.return_value = {
            "me": "Goutham",
            "assigned": [
                make_search_result(1, "Bug") | {"action": "Pending", "advisory": "ossa"},
            ],
            "other": [],
        }

        result = runner.invoke(main, ["vmt-dashboard", "--json"])
        assert result.exit_code == 0
        import json

        data = json.loads(result.output)
        assert data["me"] == "Goutham"
        assert len(data["assigned"]) == 1


class TestAddTask:
    @patch("lp_bug_manager.cli.bugs.add_task")
    def test_adds_task(self, mock_add_task, runner):
        mock_bug = MagicMock()
        mock_bug.id = 2150316
        mock_bug.web_link = "https://bugs.launchpad.net/ossa/+bug/2150316"
        mock_add_task.return_value = mock_bug

        result = runner.invoke(main, ["add-task", "2150316", "ossa"])
        assert result.exit_code == 0
        assert "Added 'ossa' task to bug #2150316" in result.output
        mock_add_task.assert_called_once_with(
            2150316, "ossa", status=None, importance=None, assignee=None
        )

    @patch("lp_bug_manager.cli.bugs.add_task")
    def test_with_options(self, mock_add_task, runner):
        mock_bug = MagicMock()
        mock_bug.id = 2150316
        mock_bug.web_link = "https://bugs.launchpad.net/ossa/+bug/2150316"
        mock_add_task.return_value = mock_bug

        result = runner.invoke(
            main,
            ["add-task", "2150316", "ossa", "-s", "Incomplete", "-i", "High", "-a", "gouthamr"],
        )
        assert result.exit_code == 0
        mock_add_task.assert_called_once_with(
            2150316, "ossa", status="Incomplete", importance="High", assignee="gouthamr"
        )


class TestShowSubscriptions:
    @patch("lp_bug_manager.cli.bugs.get_subscriptions")
    @patch("lp_bug_manager.cli.bugs.get_bug")
    def test_shows_subscriptions(self, mock_get, mock_subs, runner):
        mock_get.return_value = {
            "id": 100,
            "title": "Test bug",
            "description": "desc",
            "tags": [],
            "web_link": "https://bugs.launchpad.net/manila/+bug/100",
            "created": datetime(2026, 3, 1, tzinfo=timezone.utc),
            "updated": datetime(2026, 3, 12, tzinfo=timezone.utc),
            "tasks": [
                {
                    "target": "manila",
                    "status": "New",
                    "importance": "Medium",
                    "assignee": "Unassigned",
                }
            ],
        }
        mock_subs.return_value = [
            {"name": "nova-coresec", "display_name": "Nova Core Security", "is_team": True},
            {"name": "gouthamr", "display_name": "Goutham Pacha Ravi", "is_team": False},
        ]

        result = runner.invoke(main, ["show", "100", "--subscriptions"])
        assert result.exit_code == 0
        assert "Nova Core Security" in result.output
        assert "[team]" in result.output
        assert "Goutham Pacha Ravi" in result.output
        assert "[user]" in result.output


class TestCommentFile:
    @patch("lp_bug_manager.cli.bugs.update_bug")
    def test_reads_from_file(self, mock_update, runner, tmp_path):
        comment_file = tmp_path / "comment.txt"
        comment_file.write_text("Multi-line\ncomment here")

        mock_bug = MagicMock()
        mock_bug.id = 100
        mock_bug.web_link = "https://bugs.launchpad.net/manila/+bug/100"
        mock_update.return_value = mock_bug

        result = runner.invoke(
            main, ["update", "100", "manila", "--comment-file", str(comment_file)]
        )
        assert result.exit_code == 0
        call_kwargs = mock_update.call_args[1]
        assert call_kwargs["comment"] == "Multi-line\ncomment here"

    @patch("lp_bug_manager.cli.bugs.update_bug")
    def test_comment_and_file_errors(self, mock_update, runner, tmp_path):
        comment_file = tmp_path / "comment.txt"
        comment_file.write_text("from file")

        result = runner.invoke(
            main,
            [
                "update",
                "100",
                "manila",
                "--comment",
                "inline",
                "--comment-file",
                str(comment_file),
            ],
        )
        assert result.exit_code != 0
        assert "Cannot use both" in result.output
