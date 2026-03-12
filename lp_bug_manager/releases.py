"""OpenStack release cycle definitions."""

from datetime import date

# Release cycles with approximate dates
# Reference: https://releases.openstack.org/
RELEASE_CYCLES = {
    "2025.1": {
        "name": "Epoxy",
        "start": date(2024, 10, 2),
        "end": date(2025, 4, 2),
    },
    "2025.2": {
        "name": "Flamingo",
        "start": date(2025, 4, 2),
        "end": date(2025, 10, 1),
    },
    "2026.1": {
        "name": "Gazpacho",
        "start": date(2025, 10, 1),
        "end": date(2026, 4, 1),
    },
}

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
