# lp-bug demo — Launchpad Bug Manager for OpenStack
# Record: vhs demo.tape
# Output: demo.gif (default) or demo.mp4 with -o flag

Output demo.gif

Set Shell "zsh"
Set FontSize 20
Set Width 1400
Set Height 700
Set Theme "Catppuccin Mocha"
Set TypingSpeed 60ms
Set PlaybackSpeed 2
Set Padding 20

# ── Activate venv + enable comments (hidden from viewer) ────

Hide
Type "source /Users/gpachara/repos/openstack-lp-bug-manager/.venv/bin/activate"
Enter
Sleep 1s
Type "cd /Users/gpachara/repos/openstack-lp-bug-manager"
Enter
Sleep 1s
Type "setopt INTERACTIVE_COMMENTS"
Enter
Sleep 500ms
Type "clear"
Enter
Sleep 500ms
Show

# ── Title card ──────────────────────────────────────────────

Type "# lp-bug — Launchpad Bug Manager for OpenStack"
Enter
Type "# CLI + MCP server for bug scrubs, triaging, and analytics"
Enter
Sleep 3s
Type "clear"
Enter

# ── CLI demo ────────────────────────────────────────────────

Sleep 1s

# Search bugs — broad filter for more results
Type "# Search open bugs on manila"
Enter
Sleep 1s
Type "lp-bug search manila --status New --status Confirmed --status Triaged --status 'In Progress'"
Enter
Wait+Screen@60s /Found/
Sleep 5s

Type "clear"
Enter
Sleep 500ms

# Show a single bug
Type "# Show a single bug with details"
Enter
Sleep 1s
Type "lp-bug show 2148644"
Enter
Wait+Screen@60s /URL:/
Sleep 5s

Type "clear"
Enter
Sleep 500ms

# Releases
Type "# List known OpenStack release cycles"
Enter
Sleep 1s
Type "lp-bug releases"
Enter
Wait+Screen@30s /Gazpacho/
Sleep 3s

# End card
Type "clear"
Enter
Sleep 1s
Type "# github.com/gouthampacha/openstack-lp-bug-manager"
Enter
Type "# pip install openstack-lp-bug-manager[mcp]"
Enter
Sleep 5s
