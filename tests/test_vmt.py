"""Tests for VMT workflow operations."""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from lp_bug_manager.vmt import (
    RECEPTION_COMMENT,
    _action_flag,
    get_coresec_team,
    intake_bug,
    vmt_dashboard,
)
from tests.conftest import make_bug, make_search_result


class TestGetCoresecTeam:
    def test_known_project(self):
        assert get_coresec_team("nova") == "nova-coresec"
        assert get_coresec_team("keystone") == "keystone-coresec"

    def test_fallback(self):
        assert get_coresec_team("designate") == "designate-coresec"

    def test_no_team(self):
        assert get_coresec_team("mistral") is None


@patch("lp_bug_manager.vmt.get_project")
@patch("lp_bug_manager.vmt.get_launchpad")
class TestIntakeBug:
    def test_prepends_embargo_reminder(self, mock_lp, mock_project):
        lp = MagicMock()
        mock_lp.return_value = lp
        bug, task = make_bug(100, "Security vuln", description="Original desc", target="nova")
        lp.bugs.__getitem__.return_value = bug

        intake_bug(100)

        assert bug.description.startswith("This issue is being treated")
        assert "Original desc" in bug.description
        embargo_date = (date.today() + timedelta(days=90)).strftime("%Y-%m-%d")
        assert embargo_date in bug.description
        bug.lp_save.assert_called()

    def test_custom_embargo_days(self, mock_lp, mock_project):
        lp = MagicMock()
        mock_lp.return_value = lp
        bug, task = make_bug(101, "Bug", description="desc", target="nova")
        lp.bugs.__getitem__.return_value = bug

        result = intake_bug(101, embargo_days=60)

        embargo_date = (date.today() + timedelta(days=60)).strftime("%Y-%m-%d")
        assert embargo_date in bug.description
        assert f"expires {embargo_date}" in result["actions"][0]

    def test_adds_ossa_task(self, mock_lp, mock_project):
        lp = MagicMock()
        mock_lp.return_value = lp
        bug, task = make_bug(102, "Bug", target="nova")
        lp.bugs.__getitem__.return_value = bug
        new_task = MagicMock()
        bug.addTask.return_value = new_task

        result = intake_bug(102)

        bug.addTask.assert_called_once()
        assert new_task.status == "Incomplete"
        new_task.lp_save.assert_called_once()
        assert result["advisory"] == "ossa"

    def test_ossn_flag(self, mock_lp, mock_project):
        lp = MagicMock()
        mock_lp.return_value = lp
        bug, task = make_bug(103, "Bug", target="nova")
        lp.bugs.__getitem__.return_value = bug
        new_task = MagicMock()
        bug.addTask.return_value = new_task

        result = intake_bug(103, use_ossn=True)

        mock_project.assert_called_with("ossn")
        assert result["advisory"] == "ossn"

    def test_subscribes_coresec(self, mock_lp, mock_project):
        lp = MagicMock()
        mock_lp.return_value = lp
        bug, task = make_bug(104, "Bug", target="nova")
        lp.bugs.__getitem__.return_value = bug
        new_task = MagicMock()
        bug.addTask.return_value = new_task
        team = MagicMock()
        lp.people.__getitem__.return_value = team

        result = intake_bug(104)

        bug.subscribe.assert_called_once_with(person=team)
        lp.people.__getitem__.assert_called_with("nova-coresec")
        assert "Subscribed 'nova-coresec'" in result["actions"]

    def test_warns_missing_coresec(self, mock_lp, mock_project):
        lp = MagicMock()
        mock_lp.return_value = lp
        bug, task = make_bug(105, "Bug", target="mistral")
        lp.bugs.__getitem__.return_value = bug
        new_task = MagicMock()
        bug.addTask.return_value = new_task

        result = intake_bug(105)

        bug.subscribe.assert_not_called()
        assert any("subscribe manually" in a for a in result["actions"])

    def test_warns_nonexistent_team(self, mock_lp, mock_project):
        lp = MagicMock()
        mock_lp.return_value = lp
        bug, task = make_bug(106, "Bug", target="designate")
        lp.bugs.__getitem__.return_value = bug
        new_task = MagicMock()
        bug.addTask.return_value = new_task
        lp.people.__getitem__.side_effect = KeyError("not found")
        bug.subscribe.side_effect = Exception("not found")

        result = intake_bug(106)

        assert any("not found on Launchpad" in a for a in result["actions"])

    def test_posts_reception_comment(self, mock_lp, mock_project):
        lp = MagicMock()
        mock_lp.return_value = lp
        bug, task = make_bug(107, "Bug", target="nova")
        lp.bugs.__getitem__.return_value = bug
        new_task = MagicMock()
        bug.addTask.return_value = new_task

        intake_bug(107)

        bug.newMessage.assert_called_once_with(content=RECEPTION_COMMENT)

    def test_dry_run(self, mock_lp, mock_project):
        lp = MagicMock()
        mock_lp.return_value = lp
        bug, task = make_bug(108, "Bug", description="Original", target="nova")
        lp.bugs.__getitem__.return_value = bug

        result = intake_bug(108, dry_run=True)

        assert bug.description == "Original"
        bug.lp_save.assert_not_called()
        bug.addTask.assert_not_called()
        bug.subscribe.assert_not_called()
        bug.newMessage.assert_not_called()
        assert all("Would" in a for a in result["actions"])

    def test_skip_subscribe(self, mock_lp, mock_project):
        lp = MagicMock()
        mock_lp.return_value = lp
        bug, task = make_bug(109, "Bug", target="nova")
        lp.bugs.__getitem__.return_value = bug
        new_task = MagicMock()
        bug.addTask.return_value = new_task

        result = intake_bug(109, skip_subscribe=True)

        bug.subscribe.assert_not_called()
        assert not any("subscribe" in a.lower() for a in result["actions"])


class TestActionFlag:
    def test_overdue(self):
        bug = {"updated": datetime.now(timezone.utc) - timedelta(days=20)}
        assert _action_flag(bug, "me", {"author": "other"}) == "Overdue"

    def test_needs_response(self):
        bug = {"updated": datetime.now(timezone.utc) - timedelta(days=1)}
        assert _action_flag(bug, "me", {"author": "other"}) == "Needs response"

    def test_waiting_on_others(self):
        bug = {"updated": datetime.now(timezone.utc) - timedelta(days=1)}
        assert _action_flag(bug, "me", {"author": "me"}) == "Waiting on others"

    def test_pending_no_comment(self):
        bug = {"updated": datetime.now(timezone.utc) - timedelta(days=1)}
        assert _action_flag(bug, "me", None) == "Pending"


@patch("lp_bug_manager.vmt._get_last_comment")
@patch("lp_bug_manager.vmt.search_bugs")
@patch("lp_bug_manager.vmt.get_launchpad")
class TestVmtDashboard:
    def test_splits_by_assignee(self, mock_lp, mock_search, mock_comment):
        lp = MagicMock()
        mock_lp.return_value = lp
        lp.me.display_name = "Goutham"

        mock_search.side_effect = [
            [
                make_search_result(1, "My bug", assignee="Goutham"),
                make_search_result(2, "Other bug", assignee="Alice"),
            ],
            [],
        ]
        mock_comment.return_value = None

        result = vmt_dashboard()

        assert len(result["assigned"]) == 1
        assert result["assigned"][0]["id"] == 1
        assert len(result["other"]) == 1
        assert result["other"][0]["id"] == 2

    def test_assigned_only(self, mock_lp, mock_search, mock_comment):
        lp = MagicMock()
        mock_lp.return_value = lp
        lp.me.display_name = "Goutham"

        mock_search.side_effect = [
            [make_search_result(1, "My bug", assignee="Goutham")],
            [],
        ]
        mock_comment.return_value = None

        result = vmt_dashboard(assigned_only=True)

        assert "assigned" in result
        assert "other" not in result

    def test_action_flags_set(self, mock_lp, mock_search, mock_comment):
        lp = MagicMock()
        mock_lp.return_value = lp
        lp.me.display_name = "Goutham"

        mock_search.side_effect = [
            [make_search_result(1, "Bug", assignee="Goutham")],
            [],
        ]
        mock_comment.return_value = {"author": "Alice", "date": datetime.now(timezone.utc)}

        result = vmt_dashboard()

        assert result["assigned"][0]["action"] in (
            "Needs response",
            "Waiting on others",
            "Overdue",
            "Pending",
        )
