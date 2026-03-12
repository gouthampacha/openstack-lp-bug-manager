"""Bug operations: create, list, search, update."""

from datetime import date, datetime, timezone

from lp_bug_manager.client import get_launchpad, get_project


# Valid Launchpad bug statuses and importances
VALID_STATUSES = [
    "New", "Incomplete", "Opinion", "Invalid", "Won't Fix",
    "Confirmed", "Triaged", "In Progress", "Fix Committed", "Fix Released",
]

VALID_IMPORTANCES = [
    "Critical", "High", "Medium", "Low", "Wishlist", "Undecided",
]


def file_bug(project_name, title, description, importance=None, status=None, tags=None):
    """Create a new bug on a Launchpad project."""
    lp = get_launchpad()
    project = get_project(project_name)
    bug = lp.bugs.createBug(
        target=project,
        title=title,
        description=description,
    )
    task = bug.bug_tasks[0]
    if importance:
        task.importance = importance
    if status:
        task.status = status
    if importance or status:
        task.lp_save()
    if tags:
        bug.tags = tags
        bug.lp_save()
    return bug


def search_bugs(project_name, status=None, importance=None,
                created_since=None, created_before=None,
                tags=None, search_text=None, max_results=50):
    """Search bugs on a project with filters."""
    project = get_project(project_name)

    kwargs = {}
    if status:
        kwargs["status"] = status if isinstance(status, list) else [status]
    if importance:
        kwargs["importance"] = importance if isinstance(importance, list) else [importance]
    if created_since:
        kwargs["created_since"] = created_since
    if created_before:
        kwargs["created_before"] = created_before
    if tags:
        kwargs["tags"] = tags if isinstance(tags, list) else [tags]
    if search_text:
        kwargs["search_text"] = search_text

    tasks = project.searchTasks(**kwargs)
    results = []
    for i, task in enumerate(tasks):
        if i >= max_results:
            break
        bug = task.bug
        results.append({
            "id": bug.id,
            "title": bug.title,
            "status": task.status,
            "importance": task.importance,
            "assignee": task.assignee.display_name if task.assignee else "Unassigned",
            "created": bug.date_created,
            "updated": bug.date_last_updated,
            "tags": list(bug.tags),
            "web_link": bug.web_link,
        })
    return results


def update_bug(bug_id, project_name, status=None, importance=None,
               assignee=None, tags=None):
    """Update an existing bug's status, importance, assignee, or tags."""
    lp = get_launchpad()
    bug = lp.bugs[bug_id]

    # Find the bug task for this project
    task = None
    for t in bug.bug_tasks:
        if project_name in t.bug_target_name:
            task = t
            break
    if task is None:
        raise ValueError(f"Bug {bug_id} has no task for project {project_name}")

    if status:
        task.status = status
    if importance:
        task.importance = importance
    if assignee:
        task.assignee = lp.people[assignee]
    if status or importance or assignee:
        task.lp_save()

    if tags is not None:
        bug.tags = tags
        bug.lp_save()

    return bug


def add_gerrit_link(bug_id, gerrit_url, comment=None):
    """Add a Gerrit review link to a bug as a comment."""
    lp = get_launchpad()
    bug = lp.bugs[bug_id]
    msg = comment or f"Related Gerrit review: {gerrit_url}"
    if gerrit_url not in msg:
        msg = f"{msg}\n\n{gerrit_url}"
    bug.newMessage(content=msg)
    return bug


def get_bug(bug_id):
    """Fetch a single bug by ID."""
    lp = get_launchpad()
    bug = lp.bugs[bug_id]
    return {
        "id": bug.id,
        "title": bug.title,
        "description": bug.description,
        "tags": list(bug.tags),
        "web_link": bug.web_link,
        "created": bug.date_created,
        "updated": bug.date_last_updated,
        "tasks": [
            {
                "target": t.bug_target_name,
                "status": t.status,
                "importance": t.importance,
                "assignee": t.assignee.display_name if t.assignee else "Unassigned",
            }
            for t in bug.bug_tasks
        ],
    }
