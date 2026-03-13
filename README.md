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

# File a new bug
lp-bug file manila-ui "Something is broken" -d "Steps to reproduce..." -i Medium

# Update a bug
lp-bug update 2144047 manila-ui --status Triaged --importance Medium

# Link a Gerrit review to a bug
lp-bug link-gerrit 2144047 https://review.opendev.org/c/openstack/manila-ui/+/976962
```

## Projects

The default project set is `manila`, `manila-ui`, and `python-manilaclient`.
Any Launchpad project name works with the single-project commands.

## License

Apache-2.0
