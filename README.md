# openstack-lp-bug-manager

CLI tool for managing Launchpad bugs across OpenStack projects. Built for
weekly bug scrubs, release cycle retrospectives, and day-to-day bug triaging.

## Setup

```
git clone https://github.com/gouthampacha/openstack-lp-bug-manager.git
cd openstack-lp-bug-manager
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

The first command that hits Launchpad will open a browser for OAuth
authentication. Credentials are stored in your system keyring after that.

## Usage

### Searching bugs

```
# All open bugs on manila
lp-bug search manila --status New --status Confirmed --status Triaged

# Bugs reported in the last 30 days
lp-bug search manila --since 30d

# High importance bugs on python-manilaclient
lp-bug search python-manilaclient --importance High

# Full-text search
lp-bug search manila --text "share server" --status "In Progress"
```

### Bug scrub

The `scrub` command generates a meeting-ready agenda: untriaged bugs,
incomplete bugs, triaged-but-unassigned bugs, stale in-progress bugs,
and what came in this week.

```
# Scrub a single project
lp-bug scrub manila

# Scrub all three manila projects (default when no project given)
lp-bug scrub

# Only bugs created in the last 90 days
lp-bug scrub manila --days 90

# Flag in-progress bugs as stale after 14 days instead of 30
lp-bug scrub manila --stale-days 14
```

### Release cycle summary

Generate a retrospective for a release cycle -- reported vs fixed counts,
importance breakdown, top fixers, and still-open bugs.

```
# Summary for the current cycle
lp-bug summary Gazpacho manila

# All three projects at once (default when no project given)
lp-bug summary Gazpacho

# You can also use the version string
lp-bug summary 2026.1 manila
```

To see which release cycles are available:

```
lp-bug releases
```

### Creating release milestones

Create a release series and its milestones on Launchpad. The milestone
pattern is determined automatically from the project's deliverable file
in the `openstack/releases` repository -- `cycle-with-rc` projects get
milestones 1, 2, 3, and rc1, while client libraries get 1, 2, and
client-release.

```
# Preview what would be created
lp-bug create-release Hibiscus manila-ui --dry-run

# Create series and milestones for a single project
lp-bug create-release Hibiscus manila

# All three projects at once (default when no project given)
lp-bug create-release Hibiscus
```

Existing series and milestones are skipped, so the command is safe to
run repeatedly.

### Retargeting bugs between milestones

Move all open bugs from one milestone to another -- useful at milestone
boundaries when carrying over unfinished work.

```
# Preview what would move
lp-bug retarget manila gazpacho-3 --to gazpacho-rc1 --dry-run

# Retarget and list affected bugs
lp-bug retarget manila gazpacho-3 --to gazpacho-rc1

# Retarget and deactivate the old milestone
lp-bug retarget manila gazpacho-3 --to gazpacho-rc1 --deactivate
```

### Setting the development focus

Switch a project's development focus to a different series. Shows the
current focus and prompts for confirmation.

```
# Interactive confirmation
lp-bug set-focus manila hibiscus

# Skip the prompt
lp-bug set-focus manila hibiscus --yes
```

### Other commands

```
# Bugs reported/fixed during a release cycle
lp-bug reported manila Gazpacho
lp-bug fixed manila Gazpacho

# Bugs with no activity for 90+ days
lp-bug rotten manila --days 90

# Show a single bug
lp-bug show 2144047

# Show bug with comments
lp-bug show 2144047 --comments

# Show bug with attachments
lp-bug show 2144047 --attachments

# Both
lp-bug show 2144047 --comments --attachments

# Show bug subscriptions (teams and individuals)
lp-bug show 2144047 --subscriptions

# File a new bug
lp-bug file manila-ui "Something is broken" -d "Steps to reproduce..." -i Medium

# File a bug with an attachment
lp-bug file manila "Crash on resize" -d "See attached log" --attach /tmp/error.log

# File a bug with a patch
lp-bug file manila "Fix for crash" -d "Proposed fix" --attach fix.patch --patch

# File a private security bug
lp-bug file manila "TLS validation bypass" -d "Details..." --information-type "Private Security"

# Update a bug (project is optional when the bug has a single task)
lp-bug update 2144047 --status Triaged --importance Medium

# Specify the project when a bug spans multiple projects
lp-bug update 2144047 manila-ui --status Triaged --importance Medium

# Target a bug to a milestone
lp-bug update 2144047 --milestone gazpacho-rc1

# Target to an inactive milestone (prompts to temporarily reactivate)
lp-bug update 2144047 --milestone gazpacho-2 --yes

# Add or remove tags without replacing existing ones
lp-bug update 2144047 --add-tag rfe --add-tag netapp
lp-bug update 2144047 --remove-tag stale

# Unassign a bug
lp-bug update 2144047 --unassign --status Triaged

# Add a comment
lp-bug update 2144047 --comment "Unassigning, no progress in 3 months."

# Add a comment from a file (or stdin with -)
lp-bug update 2144047 --comment-file advisory.txt
echo "Closing" | lp-bug update 2144047 --comment-file -

# Attach a file to an existing bug
lp-bug update 2144047 --attach analysis.txt

# Attach a patch
lp-bug update 2144047 --attach fix.patch --patch

# Link a Gerrit review to a bug
lp-bug update 2144047 --link-gerrit https://review.opendev.org/c/openstack/manila-ui/+/976962

# Subscribe a team or person to a bug
lp-bug update 2150316 --subscribe oslo-coresec

# Link a CVE to a bug
lp-bug update 2138575 --link-cve CVE-2026-40212

# Download patch attachments from a bug
lp-bug show 2148398 --fetch-patches
lp-bug show 2148398 --fetch-patches --output-dir /tmp/patches/
```

### VMT (Vulnerability Management Team)

```
# Full intake workflow: embargo reminder, OSSA task, coresec subscription, reception comment
lp-bug intake 2150316

# Custom embargo duration
lp-bug intake 2150316 --embargo-days 60

# OSSN instead of OSSA
lp-bug intake 2150332 --ossn

# Preview without making changes
lp-bug intake 2150316 --dry-run

# Add a bugtask for a project
lp-bug add-task 2150316 ossa --status Incomplete
lp-bug add-task 2146554 ossn --status "In Progress" --assignee gouthamr

# VMT dashboard: open OSSA/OSSN bugs split by assignment
lp-bug vmt-dashboard
lp-bug vmt-dashboard --assigned-only
lp-bug vmt-dashboard --json

# Audit Launchpad project tracker configuration
lp-bug audit-trackers
lp-bug audit-trackers --active-only
lp-bug audit-trackers --json
lp-bug audit-trackers --html report.html
```

## Claude Code integration

This repo includes a [Claude Code](https://claude.com/claude-code) slash
command at `.claude/commands/lp-bug.md`. With Claude Code installed, use
`/lp-bug` followed by any subcommand:

```
/lp-bug show 2144047 --comments
/lp-bug scrub manila
/lp-bug search manila --status New
```

## Projects

The default project set is `manila`, `manila-ui`, and `python-manilaclient`.
Any Launchpad project name works with the single-project commands.

## License

Apache-2.0
