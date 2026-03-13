"""Tests for bug operations."""

from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

from lp_bug_manager.bugs import (
    _to_utc_datetime,
    add_gerrit_link,
    deactivate_milestone,
    file_bug,
    get_bug,
    retarget_bugs,
    search_bugs,
    update_bug,
)
from tests.conftest import make_bug


class TestToUtcDatetime:
    def test_converts_date_to_datetime(self):
        d = date(2026, 3, 12)
        result = _to_utc_datetime(d)
        assert isinstance(result, datetime)
        assert result == datetime(2026, 3, 12, tzinfo=timezone.utc)

    def test_passes_through_datetime(self):
        dt = datetime(2026, 3, 12, 15, 30, tzinfo=timezone.utc)
        result = _to_utc_datetime(dt)
        assert result is dt


class TestFileBug:
    @patch("lp_bug_manager.bugs.get_project")
    @patch("lp_bug_manager.bugs.get_launchpad")
    def test_creates_bug(self, mock_lp, mock_project):
        lp = MagicMock()
        mock_lp.return_value = lp

        bug, task = make_bug(123, "Test bug")
        lp.bugs.createBug.return_value = bug

        result = file_bug("manila", "Test bug", "A description")
        lp.bugs.createBug.assert_called_once()
        assert result.id == 123

    @patch("lp_bug_manager.bugs.get_project")
    @patch("lp_bug_manager.bugs.get_launchpad")
    def test_sets_importance_and_status(self, mock_lp, mock_project):
        lp = MagicMock()
        mock_lp.return_value = lp
        bug, task = make_bug(124, "Important bug")
        lp.bugs.createBug.return_value = bug

        file_bug("manila", "Important bug", "desc", importance="High", status="Triaged")

        assert task.importance == "High"
        assert task.status == "Triaged"
        task.lp_save.assert_called_once()

    @patch("lp_bug_manager.bugs.get_project")
    @patch("lp_bug_manager.bugs.get_launchpad")
    def test_sets_tags(self, mock_lp, mock_project):
        lp = MagicMock()
        mock_lp.return_value = lp
        bug, task = make_bug(125, "Tagged bug")
        lp.bugs.createBug.return_value = bug

        file_bug("manila", "Tagged bug", "desc", tags=["rfe", "netapp"])

        assert bug.tags == ["rfe", "netapp"]
        bug.lp_save.assert_called_once()


class TestSearchBugs:
    @patch("lp_bug_manager.bugs.get_project")
    def test_basic_search(self, mock_get_project):
        project = MagicMock()
        mock_get_project.return_value = project

        bug, task = make_bug(
            200, "Found bug", status="New", importance="Medium", assignee="gouthamr"
        )
        project.searchTasks.return_value = [task]

        results = search_bugs("manila", status="New")
        assert len(results) == 1
        assert results[0]["id"] == 200
        assert results[0]["title"] == "Found bug"
        assert results[0]["status"] == "New"
        assert results[0]["importance"] == "Medium"
        assert results[0]["assignee"] == "gouthamr"

    @patch("lp_bug_manager.bugs.get_project")
    def test_max_results(self, mock_get_project):
        project = MagicMock()
        mock_get_project.return_value = project

        tasks = []
        for i in range(10):
            _, task = make_bug(300 + i, f"Bug {i}")
            tasks.append(task)
        project.searchTasks.return_value = tasks

        results = search_bugs("manila", max_results=3)
        assert len(results) == 3

    @patch("lp_bug_manager.bugs.get_project")
    def test_unassigned_bug(self, mock_get_project):
        project = MagicMock()
        mock_get_project.return_value = project

        bug, task = make_bug(201, "Unassigned bug")
        project.searchTasks.return_value = [task]

        results = search_bugs("manila")
        assert results[0]["assignee"] == "Unassigned"

    @patch("lp_bug_manager.bugs.get_project")
    def test_date_filter_converts_to_datetime(self, mock_get_project):
        project = MagicMock()
        mock_get_project.return_value = project
        project.searchTasks.return_value = []

        search_bugs("manila", created_since=date(2026, 1, 1))

        call_kwargs = project.searchTasks.call_args[1]
        assert isinstance(call_kwargs["created_since"], datetime)
        assert call_kwargs["created_since"].tzinfo == timezone.utc


class TestUpdateBug:
    @patch("lp_bug_manager.bugs.get_launchpad")
    def test_updates_status(self, mock_lp):
        lp = MagicMock()
        mock_lp.return_value = lp
        bug, task = make_bug(400, "Bug to update", target="manila")
        lp.bugs.__getitem__.return_value = bug

        update_bug(400, "manila", status="Triaged")

        assert task.status == "Triaged"
        task.lp_save.assert_called_once()

    @patch("lp_bug_manager.bugs.get_launchpad")
    def test_wrong_project_raises(self, mock_lp):
        lp = MagicMock()
        mock_lp.return_value = lp
        bug, task = make_bug(401, "Bug", target="nova")
        lp.bugs.__getitem__.return_value = bug

        import pytest

        with pytest.raises(ValueError, match="no task for project manila"):
            update_bug(401, "manila", status="Triaged")


class TestAddGerritLink:
    @patch("lp_bug_manager.bugs.get_launchpad")
    def test_adds_comment(self, mock_lp):
        lp = MagicMock()
        mock_lp.return_value = lp
        bug, _ = make_bug(500, "Bug with review")
        lp.bugs.__getitem__.return_value = bug

        add_gerrit_link(500, "https://review.opendev.org/c/976962")

        bug.newMessage.assert_called_once()
        msg = bug.newMessage.call_args[1]["content"]
        assert "https://review.opendev.org/c/976962" in msg

    @patch("lp_bug_manager.bugs.get_launchpad")
    def test_custom_comment(self, mock_lp):
        lp = MagicMock()
        mock_lp.return_value = lp
        bug, _ = make_bug(501, "Bug")
        lp.bugs.__getitem__.return_value = bug

        add_gerrit_link(
            501, "https://review.opendev.org/c/123", comment="Fix for the share export issue"
        )

        msg = bug.newMessage.call_args[1]["content"]
        assert "Fix for the share export issue" in msg
        assert "https://review.opendev.org/c/123" in msg


class TestGetBug:
    @patch("lp_bug_manager.bugs.get_launchpad")
    def test_returns_bug_details(self, mock_lp):
        lp = MagicMock()
        mock_lp.return_value = lp
        bug, task = make_bug(
            600,
            "Detailed bug",
            status="Triaged",
            importance="High",
            assignee="gouthamr",
            tags=["rfe"],
            description="Full description",
        )
        lp.bugs.__getitem__.return_value = bug

        result = get_bug(600)
        assert result["id"] == 600
        assert result["title"] == "Detailed bug"
        assert result["description"] == "Full description"
        assert result["tags"] == ["rfe"]
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["status"] == "Triaged"
        assert result["tasks"][0]["assignee"] == "gouthamr"


class TestRetargetBugs:
    @patch("lp_bug_manager.bugs.get_project")
    def test_retargets_open_bugs(self, mock_get_project):
        project = MagicMock()
        mock_get_project.return_value = project

        from_ms = MagicMock()
        to_ms = MagicMock()
        project.getMilestone.side_effect = lambda name: (
            from_ms if name == "gazpacho-2" else to_ms
        )

        _, task1 = make_bug(700, "Open bug 1", status="Triaged", assignee="alice")
        _, task2 = make_bug(701, "Open bug 2", status="In Progress", assignee="bob")
        project.searchTasks.return_value = [task1, task2]

        result = retarget_bugs("manila", "gazpacho-2", "gazpacho-3")

        assert len(result) == 2
        assert result[0]["id"] == 700
        assert result[1]["id"] == 701
        assert task1.milestone == to_ms
        assert task2.milestone == to_ms
        assert task1.lp_save.called
        assert task2.lp_save.called

    @patch("lp_bug_manager.bugs.get_project")
    def test_dry_run_does_not_modify(self, mock_get_project):
        project = MagicMock()
        mock_get_project.return_value = project

        from_ms = MagicMock()
        to_ms = MagicMock()
        project.getMilestone.side_effect = lambda name: (
            from_ms if name == "gazpacho-2" else to_ms
        )

        _, task = make_bug(702, "Bug to keep", status="New")
        project.searchTasks.return_value = [task]

        result = retarget_bugs("manila", "gazpacho-2", "gazpacho-3", dry_run=True)

        assert len(result) == 1
        task.lp_save.assert_not_called()

    @patch("lp_bug_manager.bugs.get_project")
    def test_unknown_from_milestone_raises(self, mock_get_project):
        project = MagicMock()
        mock_get_project.return_value = project
        project.getMilestone.return_value = None

        import pytest

        with pytest.raises(ValueError, match="not found"):
            retarget_bugs("manila", "nonexistent", "gazpacho-3")

    @patch("lp_bug_manager.bugs.get_project")
    def test_unknown_to_milestone_raises(self, mock_get_project):
        project = MagicMock()
        mock_get_project.return_value = project
        from_ms = MagicMock()
        project.getMilestone.side_effect = lambda name: (from_ms if name == "gazpacho-2" else None)

        import pytest

        with pytest.raises(ValueError, match="not found"):
            retarget_bugs("manila", "gazpacho-2", "nonexistent")

    @patch("lp_bug_manager.bugs.get_project")
    def test_searches_with_open_statuses(self, mock_get_project):
        project = MagicMock()
        mock_get_project.return_value = project

        from_ms = MagicMock()
        to_ms = MagicMock()
        project.getMilestone.side_effect = lambda name: (
            from_ms if name == "gazpacho-2" else to_ms
        )
        project.searchTasks.return_value = []

        retarget_bugs("manila", "gazpacho-2", "gazpacho-3")

        call_kwargs = project.searchTasks.call_args[1]
        assert call_kwargs["milestone"] == from_ms
        assert "New" in call_kwargs["status"]
        assert "In Progress" in call_kwargs["status"]
        assert "Fix Released" not in call_kwargs["status"]


class TestDeactivateMilestone:
    @patch("lp_bug_manager.bugs.get_project")
    def test_deactivates(self, mock_get_project):
        project = MagicMock()
        mock_get_project.return_value = project

        ms = MagicMock()
        ms.is_active = True
        project.getMilestone.return_value = ms

        deactivate_milestone("manila", "gazpacho-2")

        assert ms.is_active is False
        ms.lp_save.assert_called_once()

    @patch("lp_bug_manager.bugs.get_project")
    def test_unknown_milestone_raises(self, mock_get_project):
        project = MagicMock()
        mock_get_project.return_value = project
        project.getMilestone.return_value = None

        import pytest

        with pytest.raises(ValueError, match="not found"):
            deactivate_milestone("manila", "nonexistent")
