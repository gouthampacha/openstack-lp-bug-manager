"""MCP server for Launchpad bug management."""

import argparse
import json
import sys
from datetime import date


def create_server(read_only=False):
    """Create and configure the MCP server."""
    try:
        from fastmcp import FastMCP
    except ImportError:
        print(
            "FastMCP is not installed. Install with: pip install openstack-lp-bug-manager[mcp]",
            file=sys.stderr,
        )
        sys.exit(1)

    from mcp.types import ToolAnnotations

    from lp_bug_manager import analytics, audit, bugs, vmt
    from lp_bug_manager.bugs import VALID_IMPORTANCES, VALID_STATUSES
    from lp_bug_manager.releases import list_cycles as _list_cycles
    from lp_bug_manager.serializers import serialize_value

    READ = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=True)
    WRITE = ToolAnnotations(readOnlyHint=False, openWorldHint=True)
    WRITE_IDEMPOTENT = ToolAnnotations(readOnlyHint=False, idempotentHint=True, openWorldHint=True)
    DESTRUCTIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=True)

    mcp = FastMCP(
        "Launchpad Bug Manager",
        instructions="MCP server for managing bugs on Launchpad.net",
        version="0.1.0",
    )

    def _json(obj):
        return json.dumps(serialize_value(obj), indent=2)

    def _bug_result(bug):
        return f"Bug #{bug.id}: {bug.web_link}"

    def _validate_statuses(values):
        if values:
            bad = [v for v in values if v not in VALID_STATUSES]
            if bad:
                raise ValueError(
                    f"Invalid status: {', '.join(bad)}. Valid values: {', '.join(VALID_STATUSES)}"
                )

    def _validate_importances(values):
        if values:
            bad = [v for v in values if v not in VALID_IMPORTANCES]
            if bad:
                raise ValueError(
                    f"Invalid importance: {', '.join(bad)}. "
                    f"Valid values: {', '.join(VALID_IMPORTANCES)}"
                )

    def _error(msg):
        return json.dumps({"error": str(msg)})

    # --- Read tools ---

    @mcp.tool(annotations=READ)
    def get_bug(bug_id: int) -> str:
        """Get full details of a Launchpad bug by ID.

        Returns bug title, description, tags, web link, timestamps,
        and all bug tasks with their status/importance/assignee.
        """
        try:
            return _json(bugs.get_bug(bug_id))
        except Exception as e:
            return _error(e)

    @mcp.tool(annotations=READ)
    def get_comments(bug_id: int) -> str:
        """Get all comments on a Launchpad bug.

        Returns a list of comments with index, author, date, and content.
        The original bug description (index 0) is excluded.
        """
        try:
            return _json(bugs.get_comments(bug_id))
        except Exception as e:
            return _error(e)

    @mcp.tool(annotations=READ)
    def get_attachments(bug_id: int) -> str:
        """Get all attachments on a Launchpad bug.

        Returns a list of attachments with title, type, and URL.
        """
        try:
            return _json(bugs.get_attachments(bug_id))
        except Exception as e:
            return _error(e)

    @mcp.tool(annotations=READ)
    def get_subscriptions(bug_id: int) -> str:
        """Get all subscriptions on a Launchpad bug.

        Returns a list of subscribers with name, display name,
        and whether they are a team or individual.
        """
        try:
            return _json(bugs.get_subscriptions(bug_id))
        except Exception as e:
            return _error(e)

    @mcp.tool(annotations=READ)
    def search_bugs(
        project: str,
        status: list[str] | None = None,
        importance: list[str] | None = None,
        tags: list[str] | None = None,
        search_text: str | None = None,
        created_since: str | None = None,
        created_before: str | None = None,
        max_results: int = 50,
    ) -> str:
        """Search bugs on a Launchpad project.

        Args:
            project: Launchpad project name (e.g. "manila", "nova").
            status: Filter by status. Valid values: New, Incomplete,
                Opinion, Invalid, Won't Fix, Confirmed, Triaged,
                In Progress, Fix Committed, Fix Released.
            importance: Filter by importance. Valid values: Critical,
                High, Medium, Low, Wishlist, Undecided.
            tags: Filter by tags.
            search_text: Full-text search query.
            created_since: Only bugs created after this date (YYYY-MM-DD).
            created_before: Only bugs created before this date (YYYY-MM-DD).
            max_results: Maximum number of results (default 50).
        """
        try:
            _validate_statuses(status)
            _validate_importances(importance)
            since = date.fromisoformat(created_since) if created_since else None
            before = date.fromisoformat(created_before) if created_before else None
            results = bugs.search_bugs(
                project,
                status=status,
                importance=importance,
                tags=tags,
                search_text=search_text,
                created_since=since,
                created_before=before,
                max_results=max_results,
            )
            return _json(results)
        except Exception as e:
            return _error(e)

    @mcp.tool(annotations=READ)
    def scrub_report(
        project: str,
        days: int | None = None,
        stale_days: int = 30,
    ) -> str:
        """Generate a bug scrub agenda for a Launchpad project.

        Returns categorized bug lists: untriaged, incomplete,
        triaged-but-unassigned, stale in-progress, and recent bugs.

        Args:
            project: Launchpad project name.
            days: Only include bugs created in the last N days.
            stale_days: Threshold for flagging in-progress bugs as
                stale (default 30).
        """
        try:
            return _json(analytics.scrub_report(project, days=days, stale_days=stale_days))
        except Exception as e:
            return _error(e)

    @mcp.tool(annotations=READ)
    def cycle_summary(project: str, cycle: str) -> str:
        """Generate a release cycle retrospective for a project.

        Returns reported/fixed counts, importance breakdown,
        top fixers, and still-open bugs.

        Args:
            project: Launchpad project name.
            cycle: Release cycle name or version (e.g. "Gazpacho" or "2026.1").
        """
        try:
            return _json(analytics.cycle_summary(project, cycle))
        except Exception as e:
            return _error(e)

    @mcp.tool(annotations=READ)
    def bugs_reported(project: str, cycle: str) -> str:
        """List bugs reported during a release cycle.

        Args:
            project: Launchpad project name.
            cycle: Release cycle name or version.
        """
        try:
            return _json(analytics.bugs_reported_in_cycle(project, cycle))
        except Exception as e:
            return _error(e)

    @mcp.tool(annotations=READ)
    def bugs_fixed(project: str, cycle: str) -> str:
        """List bugs fixed during a release cycle.

        Args:
            project: Launchpad project name.
            cycle: Release cycle name or version.
        """
        try:
            return _json(analytics.bugs_fixed_in_cycle(project, cycle))
        except Exception as e:
            return _error(e)

    @mcp.tool(annotations=READ)
    def rotten_bugs(project: str, days: int = 180) -> str:
        """Find bugs with no activity for a given number of days.

        Args:
            project: Launchpad project name.
            days: Inactivity threshold in days (default 180).
        """
        try:
            return _json(analytics.rotten_bugs(project, days=days))
        except Exception as e:
            return _error(e)

    @mcp.tool(annotations=READ)
    def list_cycles() -> str:
        """List all known OpenStack release cycles with their dates."""
        try:
            return _json(_list_cycles())
        except Exception as e:
            return _error(e)

    @mcp.tool(annotations=READ)
    def vmt_dashboard(assigned_only: bool = False) -> str:
        """Show open OSSA and OSSN security bugs.

        Returns bugs split into "assigned to me" and "other open bugs"
        with action flags (Needs response, Pending, Waiting on others,
        Overdue).

        Args:
            assigned_only: Only return bugs assigned to the current user.
        """
        try:
            return _json(vmt.vmt_dashboard(assigned_only=assigned_only))
        except Exception as e:
            return _error(e)

    @mcp.tool(annotations=READ)
    def audit_project(project: str) -> str:
        """Audit a Launchpad project's tracker configuration.

        Checks whether the project's driver and bug_supervisor are
        teams owned by ~openstack-admins.

        Args:
            project: Full project path (e.g. "openstack/nova") or
                short name (e.g. "nova").
        """
        try:
            return _json(audit.audit_project(project))
        except Exception as e:
            return _error(e)

    # --- Write tools (only when not read-only) ---

    if not read_only:

        @mcp.tool(annotations=WRITE)
        def file_bug(
            project: str,
            title: str,
            description: str = "",
            importance: str | None = None,
            status: str | None = None,
            tags: list[str] | None = None,
            information_type: str | None = None,
        ) -> str:
            """File a new bug on a Launchpad project.

            Args:
                project: Launchpad project name.
                title: Bug title.
                description: Bug description.
                importance: Bug importance (Critical/High/Medium/Low/
                    Wishlist/Undecided).
                status: Initial status.
                tags: List of tags.
                information_type: Visibility (Public, Public Security,
                    Private Security, Private).
            """
            try:
                if status:
                    _validate_statuses([status])
                if importance:
                    _validate_importances([importance])
                bug = bugs.file_bug(
                    project,
                    title,
                    description,
                    importance=importance,
                    status=status,
                    tags=tags,
                    information_type=information_type,
                )
                return _bug_result(bug)
            except Exception as e:
                return _error(e)

        @mcp.tool(annotations=WRITE)
        def update_bug(
            bug_id: int,
            project: str | None = None,
            status: str | None = None,
            importance: str | None = None,
            assignee: str | None = None,
            unassign: bool = False,
            milestone: str | None = None,
            tags: list[str] | None = None,
            add_tags: list[str] | None = None,
            remove_tags: list[str] | None = None,
            comment: str | None = None,
        ) -> str:
            """Update an existing bug's fields.

            Args:
                bug_id: Launchpad bug ID.
                project: Project name (required when the bug has
                    tasks on multiple projects).
                status: New status.
                importance: New importance.
                assignee: Launchpad username to assign.
                unassign: Remove the current assignee.
                milestone: Target milestone name.
                tags: Replace all tags with this list.
                add_tags: Add these tags (without removing existing).
                remove_tags: Remove these tags.
                comment: Add a comment to the bug.
            """
            try:
                if status:
                    _validate_statuses([status])
                if importance:
                    _validate_importances([importance])
                bug = bugs.update_bug(
                    bug_id,
                    project,
                    status=status,
                    importance=importance,
                    assignee=assignee,
                    unassign=unassign,
                    milestone=milestone,
                    tags=tags,
                    add_tags=add_tags,
                    remove_tags=remove_tags,
                    comment=comment,
                )
                return _bug_result(bug)
            except Exception as e:
                return _error(e)

        @mcp.tool(annotations=WRITE_IDEMPOTENT)
        def subscribe_bug(bug_id: int, subscriber: str) -> str:
            """Subscribe a team or person to a bug.

            Args:
                bug_id: Launchpad bug ID.
                subscriber: Launchpad username or team name.
            """
            try:
                bug = bugs.subscribe_bug(bug_id, subscriber)
                return f"Subscribed '{subscriber}' to {_bug_result(bug)}"
            except Exception as e:
                return _error(e)

        @mcp.tool(annotations=WRITE_IDEMPOTENT)
        def link_cve(bug_id: int, cve_id: str) -> str:
            """Link a CVE identifier to a bug.

            Args:
                bug_id: Launchpad bug ID.
                cve_id: CVE identifier (e.g. "CVE-2026-40212").
            """
            try:
                bug = bugs.link_cve(bug_id, cve_id)
                return f"Linked {cve_id} to {_bug_result(bug)}"
            except Exception as e:
                return _error(e)

        @mcp.tool(annotations=WRITE)
        def add_gerrit_link(
            bug_id: int,
            gerrit_url: str,
            comment: str | None = None,
        ) -> str:
            """Link a Gerrit review to a bug.

            Adds the review URL as a comment on the bug.

            Args:
                bug_id: Launchpad bug ID.
                gerrit_url: Full Gerrit review URL.
                comment: Optional comment text (URL is appended).
            """
            try:
                bug = bugs.add_gerrit_link(bug_id, gerrit_url, comment=comment)
                return f"Linked Gerrit review to {_bug_result(bug)}"
            except Exception as e:
                return _error(e)

        @mcp.tool(annotations=WRITE)
        def add_task(
            bug_id: int,
            project: str,
            status: str | None = None,
            importance: str | None = None,
            assignee: str | None = None,
        ) -> str:
            """Add a new bugtask for a project on an existing bug.

            Args:
                bug_id: Launchpad bug ID.
                project: Launchpad project name for the new task.
                status: Initial status for the task.
                importance: Initial importance.
                assignee: Launchpad username to assign.
            """
            try:
                if status:
                    _validate_statuses([status])
                if importance:
                    _validate_importances([importance])
                bug = bugs.add_task(
                    bug_id, project, status=status, importance=importance, assignee=assignee
                )
                return f"Added '{project}' task to {_bug_result(bug)}"
            except Exception as e:
                return _error(e)

        @mcp.tool(annotations=WRITE)
        def intake_bug(
            bug_id: int,
            embargo_days: int = 90,
            use_ossn: bool = False,
            skip_subscribe: bool = False,
        ) -> str:
            """Run the VMT intake workflow on a security bug.

            Performs four steps:
            1. Prepend embargo reminder to the bug description
            2. Add an OSSA (or OSSN) bugtask set to Incomplete
            3. Subscribe the affected project's coresec team
            4. Post the standard reception comment

            Args:
                bug_id: Launchpad bug ID.
                embargo_days: Embargo duration in days (default 90).
                use_ossn: Add an OSSN task instead of OSSA.
                skip_subscribe: Don't subscribe the coresec team.
            """
            try:
                result = vmt.intake_bug(
                    bug_id,
                    embargo_days=embargo_days,
                    use_ossn=use_ossn,
                    skip_subscribe=skip_subscribe,
                )
                return _json(result)
            except Exception as e:
                return _error(e)

        @mcp.tool(annotations=DESTRUCTIVE)
        def retarget_bugs(
            project: str,
            from_milestone: str,
            to_milestone: str,
        ) -> str:
            """Move all open bugs from one milestone to another.

            Retargets bugs with open statuses (New, Incomplete,
            Confirmed, Triaged, In Progress) from the source
            milestone to the target milestone.

            Args:
                project: Launchpad project name.
                from_milestone: Source milestone name.
                to_milestone: Target milestone name.
            """
            try:
                retargeted = bugs.retarget_bugs(project, from_milestone, to_milestone)
                return _json(retargeted)
            except Exception as e:
                return _error(e)

    return mcp


def main():
    parser = argparse.ArgumentParser(description="Launchpad MCP server")
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Only expose read operations (no bug creation or modification)",
    )
    args = parser.parse_args()
    server = create_server(read_only=args.read_only)
    server.run()


if __name__ == "__main__":
    main()
