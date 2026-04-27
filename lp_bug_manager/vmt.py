"""VMT (Vulnerability Management Team) workflow operations."""

from datetime import date, datetime, timedelta, timezone

from lp_bug_manager.bugs import OPEN_STATUSES, search_bugs
from lp_bug_manager.client import get_launchpad, get_project

EMBARGO_REMINDER = """\
This issue is being treated as a potential security risk under
embargo. Please do not make any public mention of embargoed
(private) security vulnerabilities before their coordinated
publication by the OpenStack Vulnerability Management Team in
the form of an official OpenStack Security Advisory. This
includes discussion of the bug or associated fixes in public
forums such as mailing lists, code review systems and bug
trackers. Please also avoid private disclosure to other
individuals not already approved for access to this
information, and provide this same reminder to those who are
made aware of the issue prior to publication. All discussion
should remain confined to this private bug report, and any
proposed fixes should be added to the bug as attachments.
This embargo shall not extend past {embargo_date} and will be
made public by or on that date even if no fix is identified."""

RECEPTION_COMMENT = (
    "Since this report concerns a possible security risk, an incomplete security "
    "advisory task has been added while the core security reviewers for the "
    "affected project or projects confirm the bug and discuss the scope of any "
    "vulnerability along with potential solutions."
)

CORESEC_TEAMS = {
    "keystone": "keystone-coresec",
    "nova": "nova-coresec",
    "neutron": "neutron-coresec",
    "cinder": "cinder-coresec",
    "glance": "glance-coresec",
    "ironic": "ironic-coresec",
    "swift": "swift-coresec",
    "horizon": "horizon-coresec",
    "octavia": "octavia-coresec",
    "barbican": "barbican-coresec",
    "manila": "manila-coresec",
    "heat": "heat-coresec",
    "mistral": None,
}


def get_coresec_team(project_name):
    """Return the coresec team name for a project.

    Returns None for projects known to have no coresec team (e.g. mistral).
    Falls back to {project}-coresec for unknown projects.
    """
    if project_name in CORESEC_TEAMS:
        return CORESEC_TEAMS[project_name]
    return f"{project_name}-coresec"


def _find_affected_project(bug):
    """Identify the affected project from a bug's tasks (ignoring ossa/ossn)."""
    advisory_projects = {"ossa", "ossn"}
    for task in bug.bug_tasks:
        target = task.bug_target_name.lower()
        if target not in advisory_projects:
            return target
    return None


def intake_bug(bug_id, embargo_days=90, use_ossn=False, skip_subscribe=False, dry_run=False):
    """Full VMT intake workflow for a security bug.

    Steps:
    1. Prepend embargo reminder to bug description
    2. Add OSSA (or OSSN) bugtask set to Incomplete
    3. Subscribe the affected project's coresec team
    4. Post the standard reception comment

    Returns a dict describing actions taken/planned.
    """
    lp = get_launchpad()
    bug = lp.bugs[bug_id]
    advisory_project = "ossn" if use_ossn else "ossa"
    embargo_date = (date.today() + timedelta(days=embargo_days)).strftime("%Y-%m-%d")
    actions = []

    # 1. Prepend embargo reminder
    reminder = EMBARGO_REMINDER.format(embargo_date=embargo_date)
    new_description = reminder + "\n\n" + bug.description
    if dry_run:
        actions.append(f"Would prepend embargo reminder (expires {embargo_date})")
    else:
        bug.description = new_description
        bug.lp_save()
        actions.append(f"Prepended embargo reminder (expires {embargo_date})")

    # 2. Add advisory bugtask
    project = get_project(advisory_project)
    if dry_run:
        actions.append(f"Would add '{advisory_project}' task (Incomplete)")
    else:
        new_task = bug.addTask(target=project)
        new_task.status = "Incomplete"
        new_task.lp_save()
        actions.append(f"Added '{advisory_project}' task (Incomplete)")

    # 3. Subscribe coresec team
    if not skip_subscribe:
        affected = _find_affected_project(bug)
        team_name = get_coresec_team(affected) if affected else None
        if team_name is None:
            warning = f"No coresec team for '{affected}' — subscribe manually"
            actions.append(warning)
        elif dry_run:
            actions.append(f"Would subscribe '{team_name}'")
        else:
            try:
                team = lp.people[team_name]
                bug.subscribe(person=team)
                actions.append(f"Subscribed '{team_name}'")
            except Exception:
                actions.append(f"Warning: team '{team_name}' not found on Launchpad")

    # 4. Post reception comment
    if dry_run:
        actions.append("Would post reception comment")
    else:
        bug.newMessage(content=RECEPTION_COMMENT)
        actions.append("Posted reception comment")

    return {"bug_id": bug_id, "advisory": advisory_project, "actions": actions}


def _action_flag(bug_dict, me_name, last_comment):
    """Compute an action flag for a dashboard bug."""
    now = datetime.now(timezone.utc)
    days_since_update = (now - bug_dict["updated"]).days

    if days_since_update >= 14:
        return "Overdue"
    if last_comment and last_comment["author"] != me_name:
        return "Needs response"
    if last_comment and last_comment["author"] == me_name:
        return "Waiting on others"
    return "Pending"


def _get_last_comment(bug_id):
    """Fetch the last comment on a bug, or None."""
    from lp_bug_manager.bugs import get_comments

    comments = get_comments(bug_id)
    return comments[-1] if comments else None


def vmt_dashboard(assigned_only=False):
    """Get open OSSA and OSSN bugs, split by assignment to current user."""
    lp = get_launchpad()
    me = lp.me
    me_name = me.display_name

    assigned = []
    other = []

    for advisory_project in ("ossa", "ossn"):
        bugs = search_bugs(advisory_project, status=OPEN_STATUSES, max_results=200)
        for bug_dict in bugs:
            last_comment = _get_last_comment(bug_dict["id"])
            bug_dict["action"] = _action_flag(bug_dict, me_name, last_comment)
            bug_dict["advisory"] = advisory_project
            if last_comment:
                bug_dict["last_comment_author"] = last_comment["author"]
                bug_dict["last_comment_date"] = last_comment["date"]

            if bug_dict["assignee"] == me_name:
                assigned.append(bug_dict)
            else:
                other.append(bug_dict)

    assigned.sort(key=lambda b: b["updated"], reverse=True)
    other.sort(key=lambda b: b["updated"], reverse=True)

    result = {"me": me_name, "assigned": assigned}
    if not assigned_only:
        result["other"] = other
    return result
