"""OpenStack release cycle definitions."""

import logging
from datetime import date
from functools import lru_cache

import requests
import yaml

log = logging.getLogger(__name__)

# Release cycles with approximate dates
# Reference: https://releases.openstack.org/
RELEASE_CYCLES = {
    "2025.1": {
        "name": "Epoxy",
        "start": date(2024, 10, 2),
        "end": date(2025, 4, 2),
        "milestones": {
            "1": date(2024, 11, 14),
            "2": date(2025, 1, 9),
            "3": date(2025, 2, 27),
            "rc1": date(2025, 3, 13),
        },
    },
    "2025.2": {
        "name": "Flamingo",
        "start": date(2025, 4, 2),
        "end": date(2025, 10, 1),
        "milestones": {
            "1": date(2025, 5, 15),
            "2": date(2025, 7, 3),
            "3": date(2025, 8, 28),
            "rc1": date(2025, 9, 11),
        },
    },
    "2026.1": {
        "name": "Gazpacho",
        "start": date(2025, 10, 1),
        "end": date(2026, 4, 2),
        "milestones": {
            "1": date(2025, 11, 14),
            "2": date(2026, 1, 9),
            "3": date(2026, 2, 27),
            "rc1": date(2026, 3, 12),
        },
    },
    "2026.2": {
        "name": "Hibiscus",
        "start": date(2026, 4, 2),
        "end": date(2026, 9, 30),
        "milestones": {
            "1": date(2026, 5, 14),
            "2": date(2026, 7, 2),
            "3": date(2026, 8, 27),
            "rc1": date(2026, 9, 7),
        },
    },
}

# OpenStack release models determine milestone patterns.
# Reference: https://releases.openstack.org/reference/release_models.html
RELEASE_MODELS = {
    "cycle-with-rc": {
        "milestones": ["1", "2", "3", "rc1"],
    },
    "cycle-with-intermediary": {
        "milestones": ["1", "2", "3"],
    },
}

# Client libraries follow cycle-with-intermediary but get a single
# release at milestone 3 instead of independent releases throughout.
CLIENT_LIBRARY_MILESTONES = ["1", "2", "client-release"]

_DELIVERABLE_URL = (
    "https://opendev.org/openstack/releases/raw/branch/master"
    "/deliverables/{codename}/{project}.yaml"
)


@lru_cache(maxsize=64)
def _fetch_deliverable(project_name, codename):
    """Fetch a project's deliverable YAML from the openstack/releases repo.

    Returns parsed dict or None on failure.
    """
    url = _DELIVERABLE_URL.format(codename=codename, project=project_name)
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return yaml.safe_load(resp.text)
    except (requests.RequestException, yaml.YAMLError) as exc:
        log.debug("Could not fetch deliverable for %s/%s: %s", codename, project_name, exc)
        return None


def _resolve_release_info(project_name, codename):
    """Look up release-model and type from openstack/releases.

    Returns (release_model, project_type) or (None, None) on failure.
    """
    data = _fetch_deliverable(project_name, codename)
    if data is None:
        return None, None
    return data.get("release-model"), data.get("type")


def get_milestone_pattern(project_name, cycle_id=None):
    """Return the milestone pattern for a project based on its release model.

    Looks up the release model from the openstack/releases repository.
    Falls back to cycle-with-rc if the lookup fails.
    """
    model = None
    project_type = None

    if cycle_id is not None:
        _, cycle = get_cycle(cycle_id)
        if cycle is not None:
            codename = cycle["name"].lower()
            model, project_type = _resolve_release_info(project_name, codename)

    if model is None:
        # Try the most recent known cycle as fallback
        for cycle_info in reversed(list(RELEASE_CYCLES.values())):
            codename = cycle_info["name"].lower()
            model, project_type = _resolve_release_info(project_name, codename)
            if model is not None:
                break

    if model is None:
        return RELEASE_MODELS["cycle-with-rc"]["milestones"]

    if project_type == "client-library":
        return CLIENT_LIBRARY_MILESTONES

    if model in RELEASE_MODELS:
        return RELEASE_MODELS[model]["milestones"]

    return RELEASE_MODELS["cycle-with-rc"]["milestones"]


def get_milestones_for_project(project_name, cycle_id):
    """Return milestone names and dates for a project and cycle.

    Returns a list of (milestone_name, date) tuples. The milestone
    pattern is determined by the project's release model, looked up
    from the openstack/releases repository.
    """
    version, cycle = get_cycle(cycle_id)
    if cycle is None:
        raise ValueError(f"Unknown release cycle: {cycle_id}")

    codename = cycle["name"].lower()
    ms_dates = cycle.get("milestones", {})
    pattern = get_milestone_pattern(project_name, cycle_id)

    milestones = []
    for key in pattern:
        # client-release uses milestone 3's date
        date_key = "3" if key == "client-release" else key
        ms_date = ms_dates.get(date_key)
        ms_name = f"{codename}-{key}"
        milestones.append((ms_name, ms_date))

    return milestones


# Allow lookup by codename too
_BY_NAME = {v["name"].lower(): (k, v) for k, v in RELEASE_CYCLES.items()}


def get_cycle(identifier):
    """Look up a release cycle by version (2026.1) or codename (Gazpacho)."""
    if identifier in RELEASE_CYCLES:
        return identifier, RELEASE_CYCLES[identifier]
    lower = identifier.lower()
    if lower in _BY_NAME:
        return _BY_NAME[lower]
    return None, None


def list_cycles():
    """Return all known release cycles."""
    return RELEASE_CYCLES
