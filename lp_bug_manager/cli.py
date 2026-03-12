"""CLI entry point for openstack-lp-bug-manager."""

from datetime import date, timedelta

import click
from prettytable import PrettyTable

from lp_bug_manager import bugs
from lp_bug_manager.releases import list_cycles

DEFAULT_PROJECTS = ["manila", "manila-ui", "python-manilaclient"]


def _bug_table(bug_list, show_inactive=False):
    """Format a list of bugs as a PrettyTable."""
    t = PrettyTable()
    fields = ["ID", "Title", "Status", "Importance", "Assignee", "Updated"]
    if show_inactive:
        fields.append("Days Inactive")
    t.field_names = fields
    t.align["Title"] = "l"
    t.max_width["Title"] = 60

    for b in bug_list:
        row = [
            b["id"],
            b["title"][:60],
            b["status"],
            b["importance"],
            b["assignee"],
            b["updated"].strftime("%Y-%m-%d"),
        ]
        if show_inactive:
            row.append(b.get("days_inactive", ""))
        t.add_row(row)
    return t


@click.group()
def main():
    """OpenStack Launchpad Bug Manager."""


# -- file --
@main.command("file")
@click.argument("project")
@click.argument("title")
@click.option("--description", "-d", default="", help="Bug description")
@click.option("--importance", "-i", type=click.Choice(bugs.VALID_IMPORTANCES, case_sensitive=False))
@click.option("--status", "-s", type=click.Choice(bugs.VALID_STATUSES, case_sensitive=False))
@click.option("--tag", "-t", multiple=True, help="Tags (repeatable)")
def file_bug(project, title, description, importance, status, tag):
    """File a new bug on PROJECT with TITLE."""
    bug = bugs.file_bug(project, title, description,
                        importance=importance, status=status,
                        tags=list(tag) or None)
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
        click.echo(f"  [{task['target']}] {task['status']} / "
                    f"{task['importance']} / {task['assignee']}")
    click.echo()
    click.echo(b["description"])


# -- search --
@main.command("search")
@click.argument("project")
@click.option("--status", "-s", multiple=True,
              type=click.Choice(bugs.VALID_STATUSES, case_sensitive=False),
              help="Filter by status (repeatable)")
@click.option("--importance", "-i", multiple=True,
              type=click.Choice(bugs.VALID_IMPORTANCES, case_sensitive=False),
              help="Filter by importance (repeatable)")
@click.option("--tag", "-t", multiple=True, help="Filter by tag (repeatable)")
@click.option("--text", "-q", default=None, help="Full-text search")
@click.option("--since", default=None, help="Created since date (YYYY-MM-DD) or Nd for last N days")
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
@click.option("--importance", "-i", type=click.Choice(bugs.VALID_IMPORTANCES, case_sensitive=False))
@click.option("--assignee", "-a", default=None, help="Launchpad username")
@click.option("--tag", "-t", multiple=True, help="Set tags (replaces existing)")
def update(bug_id, project, status, importance, assignee, tag):
    """Update bug BUG_ID on PROJECT."""
    bug = bugs.update_bug(
        bug_id, project,
        status=status, importance=importance,
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
