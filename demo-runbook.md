# MCP Server Demo Runbook

**All Hands Presentation — April 29, 2026**
**Duration:** ~3 minutes (+ optional bonus scene)

---

## Pre-Recording Checklist

- [ ] Terminal: maximize window, set font size to 16-18pt
- [ ] Hide desktop clutter — close other apps, clean dock
- [ ] QuickTime Player: File > New Screen Recording
      - Select "Record Selected Portion" or the terminal window
- [ ] Start a fresh Claude Code session:
      ```
      cd ~/repos/openstack-lp-bug-manager && claude
      ```
- [ ] Warm-up test (don't record this): type `/lp-bug releases`
      — confirm you see Epoxy through Hibiscus cycles
- [ ] Start QuickTime recording, then begin Scene 1

---

## Scene 1: Bug Scrub Report (~1.5 min)

**Type this prompt:**

```
Generate a bug scrub report for manila for the last 7 days and summarize the key takeaways
```

**What the audience sees:**
Claude calls the `scrub_report` MCP tool, receives categorized bug lists
(new bugs, incomplete, unassigned triaged, stale in-progress, recent activity),
then provides an actionable summary with highlights.

**Talking point:**
> "I use this to prep for our weekly bug scrub meetings — it replaces
> manually browsing Launchpad and assembling an agenda."

**Pause** a beat to let the audience read the summary, then move on.

---

## Scene 2: Release Cycle Retrospective (~1.5 min)

**Type this prompt:**

```
Give me a retrospective summary for Manila during the Gazpacho release cycle
```

**What the audience sees:**
Claude calls `cycle_summary`, gets reported vs. fixed counts, importance
breakdown, top reporters, top fixers, and still-open bugs — then presents
a narrative retrospective summary.

**Talking point:**
> "This is what I present at our end-of-cycle retrospective — analytics
> that would take manual spreadsheet work, done in seconds."

---

## Bonus Scene: Bug Deep-Dive (~1 min, if time allows)

**Type this prompt:**
``

```
Show me bug 2058427 with its comments and tell me what's the current status
```

**Why this bug works for the demo:**
7 comments spanning 2 years — community discussion, triage meeting notes,
code reviews, and a merged fix. Good for showing Claude synthesizing a
timeline instead of making the audience read raw comments.

**Talking point:**
> "Instead of reading through the full comment thread on Launchpad,
> Claude gives me the TLDR."

---

## Closing

After the last scene, mention:
- GitHub: `github.com/gouthampacha/openstack-lp-bug-manager`
- Install: `pip install openstack-lp-bug-manager[mcp]`

Stop QuickTime recording.

---

## Recovery Tips

| Problem | Fix |
|---------|-----|
| MCP tool hangs | Ctrl+C, re-type the prompt |
| Output too long / scrolls off screen | Follow up: "summarize that more briefly" |
| A scene fails entirely | Skip it — each scene is independent |
| Bug ID doesn't exist | Substitute any open manila bug |
| Claude asks for clarification | Just say "yes, go ahead" |
