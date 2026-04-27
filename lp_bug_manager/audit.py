"""Audit Launchpad project tracker configuration."""

import requests
import yaml

from lp_bug_manager.client import get_launchpad

PROJECTS_YAML_URL = (
    "https://opendev.org/openstack/project-config/raw/branch/master/gerrit/projects.yaml"
)

GOVERNANCE_PROJECTS_URL = (
    "https://opendev.org/openstack/governance/raw/branch/master/reference/projects.yaml"
)


def fetch_project_list():
    """Fetch OpenStack projects from openstack/project-config gerrit/projects.yaml."""
    resp = requests.get(PROJECTS_YAML_URL, timeout=30)
    resp.raise_for_status()
    projects = yaml.safe_load(resp.text)
    return [p["project"] for p in projects if p.get("project", "").startswith("openstack/")]


def fetch_governance_projects():
    """Fetch the set of projects under TC governance."""
    resp = requests.get(GOVERNANCE_PROJECTS_URL, timeout=30)
    resp.raise_for_status()
    governance = yaml.safe_load(resp.text)
    governed = set()
    for team_data in governance.values():
        if isinstance(team_data, dict) and "deliverables" in team_data:
            for deliverable_data in team_data["deliverables"].values():
                for repo in deliverable_data.get("repos", []):
                    governed.add(repo)
    return governed


def _check_team_owner(team, expected_owner="openstack-admins"):
    """Check if a team is owned by the expected owner. Returns (is_ok, owner_name)."""
    if team is None:
        return False, None
    try:
        if not hasattr(team, "team_owner") or team.team_owner is None:
            return False, "(not a team)"
        owner = team.team_owner
        return owner.name == expected_owner, owner.name
    except Exception:
        return False, "(unknown)"


def audit_project(project_name):
    """Check a single project's driver and bug_supervisor configuration."""
    lp = get_launchpad()
    short_name = project_name.split("/")[-1]
    try:
        project = lp.projects[short_name]
    except Exception:
        return {
            "project": project_name,
            "driver": None,
            "driver_owner": None,
            "bug_supervisor": None,
            "bug_supervisor_owner": None,
            "issues": ["Project not found on Launchpad"],
        }

    issues = []
    driver = project.driver
    driver_ok, driver_owner = _check_team_owner(driver)
    if driver is None:
        issues.append("No driver set")
    elif not driver_ok:
        issues.append(
            f"Driver '{driver.name}' not owned by openstack-admins (owner: {driver_owner})"
        )

    bug_sup = project.bug_supervisor
    bug_sup_ok, bug_sup_owner = _check_team_owner(bug_sup)
    if bug_sup is None:
        issues.append("No bug_supervisor set")
    elif not bug_sup_ok:
        issues.append(
            f"Bug supervisor '{bug_sup.name}' not owned by openstack-admins "
            f"(owner: {bug_sup_owner})"
        )

    return {
        "project": project_name,
        "driver": driver.name if driver else None,
        "driver_owner": driver_owner,
        "bug_supervisor": bug_sup.name if bug_sup else None,
        "bug_supervisor_owner": bug_sup_owner,
        "issues": issues,
    }


def audit_all(active_only=False):
    """Audit all OpenStack projects. Returns list of misconfigured projects."""
    projects = fetch_project_list()

    if active_only:
        governed = fetch_governance_projects()
        projects = [p for p in projects if p in governed]

    results = []
    for project_name in projects:
        result = audit_project(project_name)
        if result["issues"]:
            results.append(result)

    results.sort(key=lambda r: r.get("driver_owner") or "zzz")
    return results


def render_html(results, output_path):
    """Generate an HTML report of misconfigured projects."""
    html = ["<html><head><title>LP Tracker Audit</title>"]
    html.append("<style>table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:6px}")
    html.append("tr.issue{background:#fff3cd}</style></head><body>")
    html.append("<h1>Launchpad Tracker Audit</h1>")
    html.append(f"<p>{len(results)} misconfigured project(s)</p>")
    html.append("<table><tr><th>Project</th><th>Driver</th><th>Driver Owner</th>")
    html.append("<th>Bug Supervisor</th><th>Bug Sup Owner</th><th>Issues</th></tr>")
    for r in results:
        html.append("<tr class='issue'>")
        html.append(f"<td>{r['project']}</td>")
        html.append(f"<td>{r['driver'] or '—'}</td>")
        html.append(f"<td>{r['driver_owner'] or '—'}</td>")
        html.append(f"<td>{r['bug_supervisor'] or '—'}</td>")
        html.append(f"<td>{r['bug_supervisor_owner'] or '—'}</td>")
        html.append(f"<td>{'<br>'.join(r['issues'])}</td>")
        html.append("</tr>")
    html.append("</table></body></html>")

    with open(output_path, "w") as f:
        f.write("\n".join(html))
