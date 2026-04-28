"""Tests for MCP server."""

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from lp_bug_manager.mcp_server import create_server

READ_TOOLS = {
    "get_bug",
    "get_comments",
    "get_attachments",
    "get_subscriptions",
    "search_bugs",
    "scrub_report",
    "cycle_summary",
    "bugs_reported",
    "bugs_fixed",
    "rotten_bugs",
    "list_cycles",
    "vmt_dashboard",
    "audit_project",
}

WRITE_TOOLS = {
    "file_bug",
    "update_bug",
    "subscribe_bug",
    "link_cve",
    "add_gerrit_link",
    "add_task",
    "intake_bug",
    "retarget_bugs",
}


def _tool_names(server):
    tools = asyncio.run(server.list_tools())
    return {t.name for t in tools}


def _call(server, tool_name, args=None):
    result = asyncio.run(server.call_tool(tool_name, args or {}))
    return result.content[0].text


class TestToolRegistration:
    def test_all_tools_registered(self):
        server = create_server(read_only=False)
        names = _tool_names(server)
        assert READ_TOOLS.issubset(names)
        assert WRITE_TOOLS.issubset(names)
        assert len(names) == len(READ_TOOLS) + len(WRITE_TOOLS)

    def test_read_only_excludes_write_tools(self):
        server = create_server(read_only=True)
        names = _tool_names(server)
        assert READ_TOOLS.issubset(names)
        assert names.isdisjoint(WRITE_TOOLS)
        assert len(names) == len(READ_TOOLS)


class TestReadTools:
    @patch("lp_bug_manager.bugs.get_bug")
    def test_get_bug(self, mock_get):
        mock_get.return_value = {
            "id": 100,
            "title": "Test bug",
            "description": "desc",
            "tags": [],
            "web_link": "https://bugs.launchpad.net/manila/+bug/100",
            "created": datetime(2026, 3, 1, tzinfo=timezone.utc),
            "updated": datetime(2026, 3, 12, tzinfo=timezone.utc),
            "tasks": [
                {
                    "target": "manila",
                    "status": "New",
                    "importance": "Medium",
                    "assignee": "Unassigned",
                }
            ],
        }
        server = create_server(read_only=True)
        text = _call(server, "get_bug", {"bug_id": 100})
        data = json.loads(text)
        assert data["id"] == 100
        assert data["title"] == "Test bug"
        mock_get.assert_called_once_with(100)

    @patch("lp_bug_manager.bugs.search_bugs")
    def test_search_bugs_parses_dates(self, mock_search):
        mock_search.return_value = []
        server = create_server(read_only=True)
        _call(
            server,
            "search_bugs",
            {"project": "manila", "created_since": "2026-01-01"},
        )
        kwargs = mock_search.call_args[1]
        assert kwargs["created_since"].year == 2026
        assert kwargs["created_since"].month == 1
        assert kwargs["created_since"].day == 1

    @patch("lp_bug_manager.bugs.search_bugs")
    def test_search_bugs_optional_params(self, mock_search):
        mock_search.return_value = []
        server = create_server(read_only=True)
        _call(server, "search_bugs", {"project": "nova"})
        mock_search.assert_called_once_with(
            "nova",
            status=None,
            importance=None,
            tags=None,
            search_text=None,
            created_since=None,
            created_before=None,
            max_results=50,
        )

    @patch("lp_bug_manager.releases.list_cycles")
    def test_list_cycles(self, mock_cycles):
        mock_cycles.return_value = {"2026.1": {"name": "Gazpacho"}}
        server = create_server(read_only=True)
        text = _call(server, "list_cycles")
        data = json.loads(text)
        assert "2026.1" in data


class TestWriteTools:
    @patch("lp_bug_manager.bugs.file_bug")
    def test_file_bug(self, mock_file):
        bug = MagicMock()
        bug.id = 200
        bug.web_link = "https://bugs.launchpad.net/manila/+bug/200"
        mock_file.return_value = bug

        server = create_server(read_only=False)
        text = _call(
            server,
            "file_bug",
            {"project": "manila", "title": "New bug", "description": "details"},
        )
        assert "200" in text
        assert bug.web_link in text
        mock_file.assert_called_once_with(
            "manila",
            "New bug",
            "details",
            importance=None,
            status=None,
            tags=None,
            information_type=None,
        )

    @patch("lp_bug_manager.bugs.update_bug")
    def test_update_bug(self, mock_update):
        bug = MagicMock()
        bug.id = 100
        bug.web_link = "https://bugs.launchpad.net/manila/+bug/100"
        mock_update.return_value = bug

        server = create_server(read_only=False)
        text = _call(
            server,
            "update_bug",
            {"bug_id": 100, "status": "Triaged", "importance": "High"},
        )
        assert "100" in text
        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args[1]
        assert call_kwargs["status"] == "Triaged"
        assert call_kwargs["importance"] == "High"

    @patch("lp_bug_manager.bugs.subscribe_bug")
    def test_subscribe_bug(self, mock_sub):
        bug = MagicMock()
        bug.id = 100
        bug.web_link = "https://bugs.launchpad.net/manila/+bug/100"
        mock_sub.return_value = bug

        server = create_server(read_only=False)
        text = _call(server, "subscribe_bug", {"bug_id": 100, "subscriber": "nova-coresec"})
        assert "nova-coresec" in text
        mock_sub.assert_called_once_with(100, "nova-coresec")

    @patch("lp_bug_manager.vmt.intake_bug")
    def test_intake_bug(self, mock_intake):
        mock_intake.return_value = {
            "bug_id": 300,
            "advisory": "ossa",
            "actions": ["Prepended embargo reminder"],
        }
        server = create_server(read_only=False)
        text = _call(server, "intake_bug", {"bug_id": 300})
        data = json.loads(text)
        assert data["bug_id"] == 300
        assert data["advisory"] == "ossa"
        mock_intake.assert_called_once_with(
            300, embargo_days=90, use_ossn=False, skip_subscribe=False
        )
