"""Launchpad API client wrapper."""

from launchpadlib.launchpad import Launchpad

_lp = None


def get_launchpad():
    """Get a cached, authenticated Launchpad client."""
    global _lp
    if _lp is None:
        _lp = Launchpad.login_with(
            "openstack-lp-bug-manager", "production", version="devel"
        )
    return _lp


def get_project(name):
    """Get a Launchpad project by name."""
    lp = get_launchpad()
    return lp.projects[name]
