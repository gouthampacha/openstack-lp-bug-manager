Interpret the user's Launchpad bug request and call the appropriate MCP tool from the `lp-bug` server. Parse `$ARGUMENTS` using the mapping below.

## Tool mapping

| Pattern | MCP tool | Key parameters |
|---------|----------|----------------|
| `show <id>` | `mcp__lp-bug__get_bug` | `bug_id` |
| `show <id> --comments` | `mcp__lp-bug__get_comments` | `bug_id` |
| `show <id> --attachments` | `mcp__lp-bug__get_attachments` | `bug_id` |
| `show <id> --subscriptions` | `mcp__lp-bug__get_subscriptions` | `bug_id` |
| `search <project> [--status ...] [--importance ...] [--text ...]` | `mcp__lp-bug__search_bugs` | `project`, `status`, `importance`, `search_text`, `created_since`, `created_before` |
| `scrub <project> [--days N] [--stale-days N]` | `mcp__lp-bug__scrub_report` | `project`, `days`, `stale_days` |
| `summary <cycle> <project>` | `mcp__lp-bug__cycle_summary` | `project`, `cycle` |
| `reported <project> <cycle>` | `mcp__lp-bug__bugs_reported` | `project`, `cycle` |
| `fixed <project> <cycle>` | `mcp__lp-bug__bugs_fixed` | `project`, `cycle` |
| `rotten <project> [--days N]` | `mcp__lp-bug__rotten_bugs` | `project`, `days` |
| `releases` | `mcp__lp-bug__list_cycles` | (none) |
| `vmt-dashboard [--assigned-only]` | `mcp__lp-bug__vmt_dashboard` | `assigned_only` |
| `audit-trackers <project>` | `mcp__lp-bug__audit_project` | `project` |
| `file <project> <title> [-d desc] [-i importance] [--status ...] [--information-type ...]` | `mcp__lp-bug__file_bug` | `project`, `title`, `description`, `importance`, `status`, `information_type` |
| `update <id> [--status ...] [--importance ...] [--assignee ...] [--comment ...]` | `mcp__lp-bug__update_bug` | `bug_id`, `status`, `importance`, `assignee`, `comment`, `add_tags`, `remove_tags`, `milestone` |
| `update <id> --subscribe <name>` | `mcp__lp-bug__subscribe_bug` | `bug_id`, `subscriber` |
| `update <id> --link-cve <cve>` | `mcp__lp-bug__link_cve` | `bug_id`, `cve_id` |
| `update <id> --link-gerrit <url>` | `mcp__lp-bug__add_gerrit_link` | `bug_id`, `gerrit_url` |
| `add-task <id> <project> [--status ...] [--importance ...]` | `mcp__lp-bug__add_task` | `bug_id`, `project`, `status`, `importance` |
| `intake <id> [--embargo-days N] [--ossn]` | `mcp__lp-bug__intake_bug` | `bug_id`, `embargo_days`, `use_ossn` |
| `retarget <project> <from> --to <to>` | `mcp__lp-bug__retarget_bugs` | `project`, `from_milestone`, `to_milestone` |

## Rules

- Call the MCP tool directly — do not shell out to the `lp-bug` CLI
- Display results in a readable format (tables for lists, structured output for single bugs)
- When `update` includes both field changes and `--subscribe`/`--link-cve`/`--link-gerrit`, call `update_bug` first, then the additional tool(s)
- If no arguments are provided, ask what the user wants to do
