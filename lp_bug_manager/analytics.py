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
