"""Release cycle analytics and rotten bug detection."""

from datetime import date, datetime, timedelta, timezone

from lp_bug_manager.bugs import search_bugs
from lp_bug_manager.releases import get_cycle


def bugs_reported_in_cycle(project_name, cycle_id):
    """Count and list bugs reported during a release cycle."""
    version, cycle = get_cycle(cycle_id)
    if cycle is None:
        raise ValueError(f"Unknown release cycle: {cycle_id}")

    return search_bugs(
        project_name,
        created_since=cycle["start"],
        created_before=cycle["end"],
        max_results=500,
    )


def bugs_fixed_in_cycle(project_name, cycle_id):
    """Bugs that were fixed (Fix Committed/Fix Released) during a cycle.

    Uses modified_since to scope the API query to the cycle window,
    avoiding a full scan of all historically fixed bugs. The end date
    is filtered client-side since the LP API does not support
    modified_before.
    """
    version, cycle = get_cycle(cycle_id)
    if cycle is None:
        raise ValueError(f"Unknown release cycle: {cycle_id}")

    end_dt = datetime(cycle["end"].year, cycle["end"].month,
                      cycle["end"].day, tzinfo=timezone.utc)
    fixed = []
    for status in ["Fix Committed", "Fix Released"]:
        fixed.extend(search_bugs(
            project_name,
            status=status,
            modified_since=cycle["start"],
            max_results=500,
        ))

    return [b for b in fixed if b["updated"] <= end_dt]


def rotten_bugs(project_name, days=180):
    """Find bugs open or incomplete with no activity for N days."""
    cutoff = date.today() - timedelta(days=days)
    cutoff_dt = datetime(cutoff.year, cutoff.month, cutoff.day,
                         tzinfo=timezone.utc)
    results = []
    for status in ["New", "Incomplete", "Confirmed", "Triaged"]:
        bugs = search_bugs(
            project_name,
            status=status,
            max_results=500,
        )
        for b in bugs:
            if b["updated"] < cutoff_dt:
                b["days_inactive"] = (datetime.now(timezone.utc) - b["updated"]).days
                results.append(b)
    results.sort(key=lambda b: b.get("days_inactive", 0), reverse=True)
    return results


def scrub_report(project_name, days=None, stale_days=30):
    """Generate a bug scrub report with categorized sections.

    Args:
        days: If set, only show bugs with activity in the last N days.
              Applies to new, incomplete, and unassigned sections.
        stale_days: Threshold for "stale in progress" (default 30).
    """
    created_since = None
    if days:
        created_since = date.today() - timedelta(days=days)

    recent_window = date.today() - timedelta(days=7)

    new_bugs = search_bugs(project_name, status="New",
                           created_since=created_since, max_results=100)
    incomplete = search_bugs(project_name, status="Incomplete",
                             created_since=created_since, max_results=100)

    unassigned_triaged = [
        b for b in search_bugs(project_name, status=["Confirmed", "Triaged"],
                               created_since=created_since, max_results=200)
        if b["assignee"] == "Unassigned"
    ]

    stale_cutoff = datetime(*(date.today() - timedelta(days=stale_days)).timetuple()[:3],
                            tzinfo=timezone.utc)
    in_progress = search_bugs(project_name, status="In Progress", max_results=200)
    stale_in_progress = [
        b for b in in_progress if b["updated"] < stale_cutoff
    ]
    for b in stale_in_progress:
        b["days_inactive"] = (datetime.now(timezone.utc) - b["updated"]).days

    recent = search_bugs(project_name, created_since=recent_window, max_results=100)

    return {
        "new": new_bugs,
        "incomplete": incomplete,
        "unassigned_triaged": unassigned_triaged,
        "stale_in_progress": stale_in_progress,
        "recent": recent,
    }


def cycle_summary(project_name, cycle_id):
    """Generate a cycle retrospective summary with stats."""
    version, cycle = get_cycle(cycle_id)
    if cycle is None:
        raise ValueError(f"Unknown release cycle: {cycle_id}")

    reported = bugs_reported_in_cycle(project_name, cycle_id)
    fixed = bugs_fixed_in_cycle(project_name, cycle_id)

    # Importance breakdown of reported bugs
    importance_counts = {}
    for b in reported:
        imp = b["importance"]
        importance_counts[imp] = importance_counts.get(imp, 0) + 1

    # Status breakdown of reported bugs (current status)
    status_counts = {}
    for b in reported:
        st = b["status"]
        status_counts[st] = status_counts.get(st, 0) + 1

    # Assignee stats from reported bugs
    assignee_counts = {}
    for b in reported:
        a = b["assignee"]
        assignee_counts[a] = assignee_counts.get(a, 0) + 1

    # Assignee stats from fixed bugs
    fixer_counts = {}
    for b in fixed:
        a = b["assignee"]
        fixer_counts[a] = fixer_counts.get(a, 0) + 1

    # Still open from this cycle
    open_statuses = {"New", "Incomplete", "Confirmed", "Triaged", "In Progress"}
    still_open = [b for b in reported if b["status"] in open_statuses]

    return {
        "version": version,
        "cycle": cycle,
        "reported_count": len(reported),
        "fixed_count": len(fixed),
        "still_open": still_open,
        "importance_breakdown": importance_counts,
        "status_breakdown": status_counts,
        "top_reporters": sorted(assignee_counts.items(),
                                key=lambda x: x[1], reverse=True),
        "top_fixers": sorted(fixer_counts.items(),
                             key=lambda x: x[1], reverse=True),
    }
