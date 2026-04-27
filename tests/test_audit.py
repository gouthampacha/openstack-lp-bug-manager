"""Tests for audit module."""

from unittest.mock import MagicMock, patch

from lp_bug_manager.audit import _check_team_owner, audit_project, render_html


class TestCheckTeamOwner:
    def test_correct_owner(self):
        team = MagicMock()
        team.team_owner.name = "openstack-admins"
        ok, owner = _check_team_owner(team)
        assert ok is True
        assert owner == "openstack-admins"

    def test_wrong_owner(self):
        team = MagicMock()
        team.team_owner.name = "some-other-team"
        ok, owner = _check_team_owner(team)
        assert ok is False
        assert owner == "some-other-team"

    def test_none(self):
        ok, owner = _check_team_owner(None)
        assert ok is False
        assert owner is None


@patch("lp_bug_manager.audit.get_launchpad")
class TestAuditProject:
    def test_misconfigured_driver(self, mock_lp):
        lp = MagicMock()
        mock_lp.return_value = lp

        project = MagicMock()
        project.driver.name = "bad-team"
        project.driver.team_owner.name = "some-user"
        project.bug_supervisor.name = "good-team"
        project.bug_supervisor.team_owner.name = "openstack-admins"
        lp.projects.__getitem__.return_value = project

        result = audit_project("openstack/nova")

        assert len(result["issues"]) == 1
        assert "Driver" in result["issues"][0]
        assert result["driver"] == "bad-team"

    def test_no_bug_supervisor(self, mock_lp):
        lp = MagicMock()
        mock_lp.return_value = lp

        project = MagicMock()
        project.driver.name = "good-team"
        project.driver.team_owner.name = "openstack-admins"
        project.bug_supervisor = None
        lp.projects.__getitem__.return_value = project

        result = audit_project("openstack/nova")

        assert any("No bug_supervisor" in i for i in result["issues"])

    def test_all_ok(self, mock_lp):
        lp = MagicMock()
        mock_lp.return_value = lp

        project = MagicMock()
        project.driver.name = "nova-drivers"
        project.driver.team_owner.name = "openstack-admins"
        project.bug_supervisor.name = "nova-bugs"
        project.bug_supervisor.team_owner.name = "openstack-admins"
        lp.projects.__getitem__.return_value = project

        result = audit_project("openstack/nova")

        assert result["issues"] == []

    def test_project_not_found(self, mock_lp):
        lp = MagicMock()
        mock_lp.return_value = lp
        lp.projects.__getitem__.side_effect = KeyError("not found")

        result = audit_project("openstack/nonexistent")

        assert "not found" in result["issues"][0].lower()


class TestRenderHtml:
    def test_generates_file(self, tmp_path):
        results = [
            {
                "project": "openstack/nova",
                "driver": "bad-team",
                "driver_owner": "some-user",
                "bug_supervisor": None,
                "bug_supervisor_owner": None,
                "issues": ["Driver not owned by openstack-admins"],
            }
        ]
        output = tmp_path / "report.html"
        render_html(results, str(output))

        content = output.read_text()
        assert "nova" in content
        assert "bad-team" in content
        assert "<table>" in content
