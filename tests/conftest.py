"""Shared fixtures for tests."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest


def make_bug(id, title, status="New", importance="Undecided",
             assignee=None, created=None, updated=None, tags=None,
             description="", target="manila"):
    """Create a mock Launchpad bug task and its parent bug."""
    bug = MagicMock()
    bug.id = id
    bug.title = title
    bug.description = description
    bug.web_link = f"https://bugs.launchpad.net/manila/+bug/{id}"
    bug.date_created = created or datetime(2026, 1, 15, tzinfo=timezone.utc)
    bug.date_last_updated = updated or datetime(2026, 3, 1, tzinfo=timezone.utc)
    bug.tags = tags or []

    task = MagicMock()
    task.bug = bug
    task.status = status
    task.importance = importance
    task.bug_target_name = target
    if assignee:
        task.assignee = MagicMock()
        task.assignee.display_name = assignee
    else:
        task.assignee = None

    bug.bug_tasks = [task]
    return bug, task


def make_search_result(id, title, status="New", importance="Undecided",
                       assignee="Unassigned", created=None, updated=None,
                       tags=None):
    """Create a dict matching the format returned by bugs.search_bugs."""
    return {
        "id": id,
        "title": title,
        "status": status,
        "importance": importance,
        "assignee": assignee,
        "created": created or datetime(2026, 1, 15, tzinfo=timezone.utc),
        "updated": updated or datetime(2026, 3, 1, tzinfo=timezone.utc),
        "tags": tags or [],
        "web_link": f"https://bugs.launchpad.net/manila/+bug/{id}",
    }
