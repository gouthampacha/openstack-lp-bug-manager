# Contributing

## Getting started

```
git clone https://github.com/gouthampacha/openstack-lp-bug-manager.git
cd openstack-lp-bug-manager
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
pre-commit install
```

## Running tests

```
pytest -v
```

All Launchpad API calls are mocked in tests, so you don't need
credentials or network access to run them.

## Code style

This project uses [ruff](https://docs.astral.sh/ruff/) for linting and
formatting, enforced via pre-commit hooks. The hooks run automatically
on commit, but you can also run them manually:

```
pre-commit run --all-files
```

## Project layout

```
lp_bug_manager/
    client.py      # Launchpad API authentication and connection
    bugs.py        # Bug CRUD operations (file, search, update, get)
    releases.py    # Release cycles, milestone patterns (fetched from openstack/releases)
    analytics.py   # Scrub reports, cycle summaries, rotten bug detection
    cli.py         # Click CLI commands
    ...
tests/
    conftest.py    # Shared mock helpers (make_bug, make_search_result)
    test_*.py      # Unit tests for each module
```

## Ideas for improvement

Here are some directions this tool could grow. If you're interested in
working on any of these, open an issue to discuss the approach first.

**More output formats.** The CLI currently only outputs pretty-printed
tables. Adding `--format json` and `--format csv` would make it easier
to pipe results into other tools, scripts, or meeting agendas.

**Assignee workload report.** A command that shows how many bugs each
person is carrying, broken down by status. Useful for balancing work
during bug scrubs.

**Caching.** Launchpad API calls are slow. A local cache with a
configurable TTL would make repeated queries (like running `scrub`
and then `summary` in the same meeting) much faster.

**More release cycles.** The release cycle dates in `releases.py` are
manually maintained. They could be extended with older cycles, or
potentially parsed from the OpenStack releases repository.

**Bug activity timeline.** Show the history of status changes on a bug,
not just its current state. Useful for understanding how long bugs sat
in each status.

## Adding a new CLI command

1. If the command needs new Launchpad queries, add them to `bugs.py`
   or `analytics.py`.
2. Add the Click command in `cli.py`.
3. Add tests -- mock the API layer and test both the logic and the
   CLI output using Click's `CliRunner`.
4. Run `pytest -v` and `pre-commit run --all-files` before submitting.

## openstack/releases dependency

The `create-release` command and milestone pattern logic depend on the
[openstack/releases](https://opendev.org/openstack/releases) repository.
Each project has a deliverable YAML file per cycle at:

```
deliverables/{codename}/{project}.yaml
```

The `release-model` field (e.g., `cycle-with-rc`, `cycle-with-intermediary`)
and `type` field (e.g., `service`, `client-library`) determine which
milestones get created. This is fetched at runtime from opendev.org and
cached in-process with `lru_cache`. Tests mock `_resolve_release_info`
to avoid network calls.

## Launchpad API notes

A few things that are useful to know when working with launchpadlib:

- Date parameters to `searchTasks` must be timezone-aware `datetime`
  objects, not `date` objects. The `_to_utc_datetime` helper in
  `bugs.py` handles this.
- The API supports `modified_since` but not `modified_before`, so
  end-date filtering has to happen client-side.
- The first API call triggers browser-based OAuth. Credentials are
  stored in the system keyring after that.
