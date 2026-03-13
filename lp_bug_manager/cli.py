"""CLI entry point for openstack-lp-bug-manager."""

from datetime import date, timedelta

import click
from prettytable import PrettyTable

from lp_bug_manager import analytics, bugs
from lp_bug_manager.releases import get_cycle, get_milestones_for_project, list_cycles

DEFAULT_PROJECTS = ["manila", "manila-ui", "python-manilaclient"]


def _parse_projects(project, all_projects):
    """Return list of projects to query."""
    if all_projects:
        return DEFAULT_PROJECTS
    return [project]


def _bug_table(bug_list, show_inactive=False, show_project=False):
    """Format a list of bugs as a PrettyTable."""
    t = PrettyTable()
    fields = ["ID"]
    if show_project:
        fields.append("Project")
    fields.extend(["Title", "Status", "Importance", "Assignee", "Updated"])
    if show_inactive:
        fields.append("Days Inactive")
    t.field_names = fields
    t.align["Title"] = "l"
    t.max_width["Title"] = 55

    for b in bug_list:
        row = [b["id"]]
        if show_project:
            row.append(b.get("project", ""))
        row.extend(
            [
                b["title"][:55],
                b["status"],
                b["importance"],
                b["assignee"],
                b["updated"].strftime("%Y-%m-%d"),
            ]
        )
        if show_inactive:
            row.append(b.get("days_inactive", ""))
        t.add_row(row)
    return t


def _search_multi(projects, **kwargs):
    """Search across multiple projects, tagging results with project name."""
    all_results = []
    for proj in projects:
        results = bugs.search_bugs(proj, **kwargs)
        for b in results:
            b["project"] = proj
        all_results.extend(results)
    return all_results


def _kv_table(data, col1="", col2=""):
    """Simple two-column table."""
    t = PrettyTable()
    t.field_names = [col1, col2]
    t.align[col1] = "l"
    t.align[col2] = "r"
    for k, v in data:
        t.add_row([k, v])
    return t


@click.group()
def main():
    """OpenStack Launchpad Bug Manager."""


# -- file --
@main.command("file")
@click.argument("project")
@click.argument("title")
@click.option("--description", "-d", default="", help="Bug description")
@click.option(
    "--importance", "-i", type=click.Choice(bugs.VALID_IMPORTANCES, case_sensitive=False)
)
@click.option("--status", "-s", type=click.Choice(bugs.VALID_STATUSES, case_sensitive=False))
@click.option("--tag", "-t", multiple=True, help="Tags (repeatable)")
def file_bug(project, title, description, importance, status, tag):
    """File a new bug on PROJECT with TITLE."""
    bug = bugs.file_bug(
        project, title, description, importance=importance, status=status, tags=list(tag) or None
    )
    click.echo(f"Created bug #{bug.id}: {bug.web_link}")


# -- show --
@main.command("show")
@click.argument("bug_id", type=int)
def show_bug(bug_id):
    """Show details of a bug by ID."""
    b = bugs.get_bug(bug_id)
    click.echo(f"Bug #{b['id']}: {b['title']}")
    click.echo(f"URL: {b['web_link']}")
    click.echo(f"Created: {b['created'].strftime('%Y-%m-%d')}")
    click.echo(f"Updated: {b['updated'].strftime('%Y-%m-%d')}")
    if b["tags"]:
        click.echo(f"Tags: {', '.join(b['tags'])}")
    click.echo()
    for task in b["tasks"]:
        click.echo(
            f"  [{task['target']}] {task['status']} / {task['importance']} / {task['assignee']}"
        )
    click.echo()
    click.echo(b["description"])


# -- search --
@main.command("search")
@click.argument("project")
@click.option(
    "--status",
    "-s",
    multiple=True,
    type=click.Choice(bugs.VALID_STATUSES, case_sensitive=False),
    help="Filter by status (repeatable)",
)
@click.option(
    "--importance",
    "-i",
    multiple=True,
    type=click.Choice(bugs.VALID_IMPORTANCES, case_sensitive=False),
    help="Filter by importance (repeatable)",
)
@click.option("--tag", "-t", multiple=True, help="Filter by tag (repeatable)")
@click.option("--text", "-q", default=None, help="Full-text search")
@click.option(
    "--since", default=None, help="Created since date (YYYY-MM-DD) or Nd for last N days"
)
@click.option("--before", default=None, help="Created before date (YYYY-MM-DD)")
@click.option("--max", "max_results", default=50, help="Max results")
def search(project, status, importance, tag, text, since, before, max_results):
    """Search bugs on PROJECT."""
    created_since = None
    created_before = None
    if since:
        if since.endswith("d"):
            created_since = date.today() - timedelta(days=int(since[:-1]))
        else:
            created_since = date.fromisoformat(since)
    if before:
        created_before = date.fromisoformat(before)
    results = bugs.search_bugs(
        project,
        status=list(status) or None,
        importance=list(importance) or None,
        tags=list(tag) or None,
        search_text=text,
        created_since=created_since,
        created_before=created_before,
        max_results=max_results,
    )
    if not results:
        click.echo("No bugs found.")
        return
    click.echo(f"Found {len(results)} bug(s):")
    click.echo(_bug_table(results))


# -- update --
@main.command("update")
@click.argument("bug_id", type=int)
@click.argument("project")
@click.option("--status", "-s", type=click.Choice(bugs.VALID_STATUSES, case_sensitive=False))
@click.option(
    "--importance", "-i", type=click.Choice(bugs.VALID_IMPORTANCES, case_sensitive=False)
)
@click.option("--assignee", "-a", default=None, help="Launchpad username")
@click.option("--tag", "-t", multiple=True, help="Set tags (replaces existing)")
def update(bug_id, project, status, importance, assignee, tag):
    """Update bug BUG_ID on PROJECT."""
    bug = bugs.update_bug(
        bug_id,
        project,
        status=status,
        importance=importance,
        assignee=assignee,
        tags=list(tag) if tag else None,
    )
    click.echo(f"Updated bug #{bug.id}: {bug.web_link}")


# -- link-gerrit --
@main.command("link-gerrit")
@click.argument("bug_id", type=int)
@click.argument("gerrit_url")
@click.option("--comment", "-c", default=None, help="Comment text")
def link_gerrit(bug_id, gerrit_url, comment):
    """Add a Gerrit review link to bug BUG_ID."""
    bug = bugs.add_gerrit_link(bug_id, gerrit_url, comment=comment)
    click.echo(f"Linked Gerrit review to bug #{bug.id}")


# -- reported --
@main.command("reported")
@click.argument("project")
@click.argument("cycle")
def reported(project, cycle):
    """Bugs reported during a release CYCLE (e.g., Gazpacho or 2026.1)."""
    result = analytics.bugs_reported_in_cycle(project, cycle)
    version, info = get_cycle(cycle)
    click.echo(
        f"Bugs reported on {project} during {info['name']} "
        f"({info['start']} to {info['end']}): {len(result)}"
    )
    if result:
        click.echo(_bug_table(result))


# -- fixed --
@main.command("fixed")
@click.argument("project")
@click.argument("cycle")
def fixed(project, cycle):
    """Bugs fixed during a release CYCLE."""
    result = analytics.bugs_fixed_in_cycle(project, cycle)
    version, info = get_cycle(cycle)
    click.echo(
        f"Bugs fixed on {project} during {info['name']} "
        f"({info['start']} to {info['end']}): {len(result)}"
    )
    if result:
        click.echo(_bug_table(result))


# -- rotten --
@main.command("rotten")
@click.argument("project")
@click.option("--days", "-d", default=180, help="Days of inactivity (default: 180)")
def rotten(project, days):
    """Find rotten bugs with no activity for N days."""
    result = analytics.rotten_bugs(project, days=days)
    click.echo(f"Rotten bugs on {project} (no activity for {days}+ days): {len(result)}")
    if result:
        click.echo(_bug_table(result, show_inactive=True))


# -- scrub --
@main.command("scrub")
@click.argument("project", required=False)
@click.option("--all", "all_projects", is_flag=True, help="Run across all Manila projects")
@click.option(
    "--days", "-d", default=None, type=int, help="Only show bugs created in the last N days"
)
@click.option(
    "--stale-days", default=30, type=int, help="Threshold for stale In Progress bugs (default: 30)"
)
def scrub(project, all_projects, days, stale_days):
    """Weekly bug scrub agenda. Shows untriaged, unassigned, stale, and recent bugs."""
    if not project and not all_projects:
        all_projects = True
    projects = _parse_projects(project, all_projects)
    multi = len(projects) > 1

    for proj in projects:
        if multi:
            click.echo(click.style(f"\n{'=' * 60}", bold=True))
            click.echo(click.style(f"  {proj}", bold=True))
            click.echo(click.style(f"{'=' * 60}", bold=True))

        report = analytics.scrub_report(proj, days=days, stale_days=stale_days)

        click.echo(click.style(f"\n-- New / Untriaged ({len(report['new'])}) --", fg="red"))
        if report["new"]:
            click.echo(_bug_table(report["new"]))
        else:
            click.echo("  None")

        click.echo(click.style(f"\n-- Incomplete ({len(report['incomplete'])}) --", fg="yellow"))
        if report["incomplete"]:
            click.echo(_bug_table(report["incomplete"]))
        else:
            click.echo("  None")

        click.echo(
            click.style(
                f"\n-- Triaged but Unassigned ({len(report['unassigned_triaged'])}) --",
                fg="yellow",
            )
        )
        if report["unassigned_triaged"]:
            click.echo(_bug_table(report["unassigned_triaged"]))
        else:
            click.echo("  None")

        click.echo(
            click.style(
                f"\n-- Stale In Progress (30+ days) ({len(report['stale_in_progress'])}) --",
                fg="red",
            )
        )
        if report["stale_in_progress"]:
            click.echo(_bug_table(report["stale_in_progress"], show_inactive=True))
        else:
            click.echo("  None")

        click.echo(
            click.style(f"\n-- Reported This Week ({len(report['recent'])}) --", fg="green")
        )
        if report["recent"]:
            click.echo(_bug_table(report["recent"]))
        else:
            click.echo("  None")

    click.echo()


# -- summary --
@main.command("summary")
@click.argument("cycle")
@click.argument("project", required=False)
@click.option("--all", "all_projects", is_flag=True, help="Run across all Manila projects")
def summary(cycle, project, all_projects):
    """Release cycle retrospective summary for CYCLE (e.g., Gazpacho)."""
    if not project and not all_projects:
        all_projects = True
    projects = _parse_projects(project, all_projects)

    for proj in projects:
        s = analytics.cycle_summary(proj, cycle)

        click.echo(click.style(f"\n{'=' * 60}", bold=True))
        click.echo(click.style(f"  {proj} -- {s['cycle']['name']} ({s['version']})", bold=True))
        click.echo(click.style(f"  {s['cycle']['start']} to {s['cycle']['end']}", bold=True))
        click.echo(click.style(f"{'=' * 60}", bold=True))

        click.echo(f"\n  Bugs reported:   {s['reported_count']}")
        click.echo(f"  Bugs fixed:      {s['fixed_count']}")
        click.echo(f"  Still open:      {len(s['still_open'])}")

        if s["importance_breakdown"]:
            click.echo(click.style("\n-- By Importance --", fg="cyan"))
            click.echo(_kv_table(sorted(s["importance_breakdown"].items()), "Importance", "Count"))

        if s["status_breakdown"]:
            click.echo(click.style("\n-- By Current Status --", fg="cyan"))
            click.echo(_kv_table(sorted(s["status_breakdown"].items()), "Status", "Count"))

        if s["top_fixers"]:
            click.echo(click.style("\n-- Top Fixers --", fg="green"))
            click.echo(_kv_table(s["top_fixers"][:10], "Assignee", "Fixed"))

        if s["still_open"]:
            click.echo(click.style(f"\n-- Still Open ({len(s['still_open'])}) --", fg="yellow"))
            click.echo(_bug_table(s["still_open"]))

    click.echo()


# -- create-release --
@main.command("create-release")
@click.argument("cycle")
@click.argument("project", required=False)
@click.option("--all", "all_projects", is_flag=True, help="Create across all Manila projects")
@click.option("--dry-run", is_flag=True, help="Show what would be created without doing it")
def create_release(cycle, project, all_projects, dry_run):
    """Create a release series and milestones on Launchpad for CYCLE.

    Creates the series and its milestones with the correct dates.
    Manila and manila-ui get milestones 1, 2, 3, and rc1.
    python-manilaclient gets milestones 1, 2, and client-release.
    """
    from lp_bug_manager.client import get_project

    version, info = get_cycle(cycle)
    if info is None:
        raise click.ClickException(f"Unknown release cycle: {cycle}")

    if not project and not all_projects:
        all_projects = True
    projects = _parse_projects(project, all_projects)
    codename = info["name"].lower()

    for proj_name in projects:
        click.echo(click.style(f"\n{proj_name}", bold=True))

        milestones = get_milestones_for_project(proj_name, cycle)

        if dry_run:
            click.echo(f"  Would create series: {codename} ({version})")
            click.echo(f"    Summary: The OpenStack {version} {info['name']} release cycle")
            for ms_name, ms_date in milestones:
                click.echo(f"  Would create milestone: {ms_name} ({ms_date})")
            continue

        lp_project = get_project(proj_name)

        # Check if series already exists
        existing = None
        for s in lp_project.series:
            if s.name == codename:
                existing = s
                break

        if existing:
            click.echo(f"  Series '{codename}' already exists, skipping creation")
            series = existing
        else:
            summary = f"The OpenStack {version} {info['name']} release cycle"
            series = lp_project.newSeries(name=codename, summary=summary)
            click.echo(f"  Created series: {codename}")

        # Create milestones
        existing_ms = {m.name for m in series.all_milestones}
        for ms_name, ms_date in milestones:
            if ms_name in existing_ms:
                click.echo(f"  Milestone '{ms_name}' already exists, skipping")
                continue
            series.newMilestone(name=ms_name, date_targeted=bugs._to_utc_datetime(ms_date))
            click.echo(f"  Created milestone: {ms_name} ({ms_date})")

    click.echo()


# -- retarget --
@main.command("retarget")
@click.argument("project")
@click.argument("from_milestone")
@click.option("--to", "to_milestone", required=True, help="Target milestone name")
@click.option(
    "--deactivate", is_flag=True, help="Deactivate the source milestone after retargeting"
)
@click.option("--dry-run", is_flag=True, help="Show what would be retargeted without doing it")
def retarget(project, from_milestone, to_milestone, deactivate, dry_run):
    """Retarget open bugs from FROM_MILESTONE to another milestone.

    Moves all open bugs (New, Incomplete, Confirmed, Triaged, In Progress)
    from FROM_MILESTONE to the milestone specified with --to.
    """
    retargeted = bugs.retarget_bugs(project, from_milestone, to_milestone, dry_run=dry_run)

    if dry_run:
        prefix = "Would retarget"
    else:
        prefix = "Retargeted"

    click.echo(f"{prefix} {len(retargeted)} open bug(s) from {from_milestone} to {to_milestone}")

    if retargeted:
        click.echo(_bug_table(retargeted))

    if deactivate:
        if dry_run:
            click.echo(f"\nWould deactivate milestone: {from_milestone}")
        else:
            bugs.deactivate_milestone(project, from_milestone)
            click.echo(f"\nDeactivated milestone: {from_milestone}")

    click.echo()


# -- releases --
@main.command("releases")
def releases():
    """List known OpenStack release cycles."""
    t = PrettyTable()
    t.field_names = ["Version", "Codename", "Start", "End"]
    for version, info in list_cycles().items():
        t.add_row([version, info["name"], info["start"], info["end"]])
    click.echo(t)


if __name__ == "__main__":
    main()
