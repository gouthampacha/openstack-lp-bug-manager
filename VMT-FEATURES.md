# VMT Feature Specification for openstack-lp-bug-manager

This document specifies new commands and enhancements to support the
OpenStack Vulnerability Management Team (VMT) workflow. The VMT
triages security vulnerabilities across all OpenStack projects,
manages embargoes, requests CVEs, and publishes security advisories.

## Context

The tool currently supports bug lifecycle management for a single
project team (manila). The VMT needs cross-project capabilities
for security bug intake, triage, and tracking. All new commands
operate on the "ossa" and "ossn" Launchpad projects in addition
to individual project trackers.

The tool uses Click for CLI, launchpadlib for the LP API, and
PrettyTable for output. New commands should follow the same
patterns. Tests live in tests/ and use pytest.

## Priority 1: VMT Intake Command

### `lp-bug intake BUG_ID`

Automates the full VMT bug reception process per the documented
VMT process (https://security.openstack.org/vmt-process.html).

Steps performed:
1. Prepend the embargo reminder to the bug description, with
   a 90-day expiration date computed from today.
2. Add an "ossa" bugtask set to Incomplete status.
3. Subscribe the affected project's core security review team.
   Use a lookup table mapping project names to their coresec
   team names (e.g., keystone -> keystone-coresec,
   nova -> nova-coresec, ironic -> ironic-coresec). Fall back
   to {project}-coresec if not in the table. Print a warning
   if the team doesn't exist on LP.
4. Post the standard reception comment:
   "Since this report concerns a possible security risk, an
   incomplete security advisory task has been added while the
   core security reviewers for the affected project or projects
   confirm the bug and discuss the scope of any vulnerability
   along with potential solutions."

The embargo reminder text (from the VMT process doc):

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
    This embargo shall not extend past $NINETY_DAYS and will be
    made public by or on that date even if no fix is identified.

Options:
- `--embargo-days N` (default 90): override the embargo duration
- `--ossn`: add an "ossn" task instead of "ossa"
- `--skip-subscribe`: don't subscribe the coresec team
- `--dry-run`: show what would be done without making changes

Example:
    lp-bug intake 2150316
    lp-bug intake 2150332 --embargo-days 60

## Priority 2: Subscribe Command

### `lp-bug subscribe BUG_ID TEAM`

Subscribe a Launchpad team (or person) to a bug.

Example:
    lp-bug subscribe 2150316 oslo-coresec
    lp-bug subscribe 2150332 ironic-coresec

## Priority 3: Add Task Command

### `lp-bug add-task BUG_ID PROJECT`

Add a new bugtask for PROJECT on an existing bug. Optionally set
status and importance.

Options:
- `-s, --status STATUS` (default: Incomplete)
- `-i, --importance IMPORTANCE`
- `-a, --assignee USERNAME`

Example:
    lp-bug add-task 2150316 ossa --status incomplete
    lp-bug add-task 2146554 ossn --status "in progress" --assignee gouthamr

## Priority 4: VMT Dashboard Command

### `lp-bug vmt-dashboard`

Show all open OSSA and OSSN bugs, split into "assigned to me"
and "other open bugs". For each bug, show:
- Bug ID (linked), project, OSSA/OSSN task status, importance
- Last updated date
- Last comment author and date
- Action flag: Needs response / Pending / Waiting on others / Overdue

Sort by last updated, most recent first. Use the same logic as
the /vmt-bugs skill in the user's Claude Code configuration.

Options:
- `--assigned-only`: only show bugs assigned to me
- `--json`: output as JSON for programmatic use

## Priority 5: Link CVE Command

### `lp-bug link-cve BUG_ID CVE_ID`

Link a CVE identifier to a bug on Launchpad. If LP's CVE
database hasn't indexed the CVE yet, print a clear error
message rather than failing silently.

Example:
    lp-bug link-cve 2138575 CVE-2026-40212

## Priority 6: Audit Command

### `lp-bug audit-trackers`

Audit Launchpad project tracker configuration. For each
OpenStack project using Launchpad (derived from
openstack/project-config gerrit/projects.yaml), check:
- driver: is it a team owned by ~openstack-admins?
- bug_supervisor: is it a team owned by ~openstack-admins?

Output a table of misconfigured projects, grouped by
driver team owner, with an active/retired status column.

Options:
- `--active-only`: only show projects in TC governance
- `--html FILE`: generate an HTML report
- `--json`: output as JSON

## Priority 7: Fetch Patch Command

### `lp-bug fetch-patch BUG_ID [--output-dir DIR]`

Download all patch attachments from a bug to a local directory.
Default output directory is the current directory.

Example:
    lp-bug fetch-patch 2148398 --output-dir /tmp/patches/

## Priority 8: Show Subscriptions

### `lp-bug show --subscriptions BUG_ID`

Extend the existing `show` command to display bug subscriptions
(team and individual subscribers).

## Implementation Notes

- The coresec team lookup table for `intake` should be
  maintainable (a dict in a separate module or a config file).
  Known mappings include:
  - keystone -> keystone-coresec
  - nova -> nova-coresec
  - neutron -> neutron-coresec
  - cinder -> cinder-coresec
  - glance -> glance-coresec
  - ironic -> ironic-coresec
  - swift -> swift-coresec
  - horizon -> horizon-coresec
  - octavia -> octavia-coresec
  - barbican -> barbican-coresec
  - manila -> manila-coresec
  - heat -> heat-coresec
  - mistral: no coresec team (warn, subscribe PTL manually)

- The `vmt-dashboard` command should work without hardcoding
  the current user. Use `lp.me` from launchpadlib.

- All commands that modify bugs should support `--dry-run` and
  `--yes` (skip confirmation) flags, consistent with the
  existing `update` command.

- The `update` command's `--comment` flag should also accept
  `--comment-file PATH` to read multi-line comments from a file
  or stdin (`--comment-file -`).
