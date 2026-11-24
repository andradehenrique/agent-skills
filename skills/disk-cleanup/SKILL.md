---
name: disk-cleanup
description: Use when the conversation is about reclaiming space on the local machine or finding out what is using it, even when the request names a single source — Docker, Xcode and simulators, dev caches (brew, npm, pip, gradle, cargo), node_modules, forgotten worktrees such as the ones under .claude/worktrees, ~/Library, System Data, or Claude Code, Cursor and opencode sessions. Worth using even when the person never says "cleanup". It scans, prints a numbered list with size and risk per item, and removes only what the person confirms, item by item. Not for production application caches, container log rotation, Redis eviction, git commands, CI caches, or cleaning source code.
metadata:
  version: "1.0.0"
---

# Disk Cleanup

**CRITICAL LANGUAGE RULE:** Every message you write to the person — the report, the confirmation prompt, the closing summary — must be in their conversational language. The scripts print English by default; translate their output when relaying it. Keep paths, item numbers and command names exactly as the scripts produced them.

The goal is to free space **with no surprises**. Someone using this skill would rather leave 1 GB behind than lose a file that mattered. That is why the work is split into two phases that never mix:

1. **Scan** (`scripts/scan.py`): reads the disk only and produces a numbered plan in JSON.
2. **Apply** (`scripts/apply.py`): removes only the numbers the person confirmed, re-checking every item before touching it.

## Overview

Every removal goes through `apply.py`. Do not use `rm`, `docker`, `brew` or `git worktree remove` directly, even when it looks faster. The scripts guarantee protections a one-off command does not:

- protected areas (Documents, iCloud, Keychains, `.ssh`, the Claude `memory/` folder, and more);
- refusal of symlinks;
- a check that the app owning a cache is closed;
- a re-check of the git state;
- an audit log.

Paths in this document are relative to the skill directory. Replace `<skill_path>` with the absolute path of this skill (the one that appears in the session's skill list).

## Hard Gates

<HARD-GATE>
**Never delete outside the scripts.** The only removal path is `python3 <skill_path>/scripts/apply.py`. No `rm -rf`, no `docker system prune`, no `brew cleanup`, no `git worktree remove --force`, no `sudo`, and no hand-written loop over a path list — not even to "just test". If the scripts refuse an item, report the refusal; do not work around it.
</HARD-GATE>

<HARD-GATE>
**No removal without an explicit confirmation of exact items.** "clean everything", "go ahead" or "I trust you" is not confirmation of a list. Repeat the numbers and the total and wait for a yes. Yellow items enter only when the person names them by number or by name. Red items are never removed.
</HARD-GATE>

<HARD-GATE>
**Never invent sizes, paths or reasons.** Every number in the report comes from the scan JSON. Every path comes from the JSON. Every "why this can go" comes from the rule's `note` or from the reference docs. When the data is missing, say it is missing.
</HARD-GATE>

<HARD-GATE>
**A stale scan is never applied.** `apply.py` refuses scans older than `scan_max_age_hours` (4h by default), made on another machine, or items modified after the scan. When that happens, re-run the scan and ask again with the new numbers, because numbering changes.
</HARD-GATE>

## Execution Flow

### Phase 1: Scan

```bash
python3 <skill_path>/scripts/scan.py
```

This takes seconds to a few minutes. The script prints a summary and the path of the JSON (`~/.local/state/disk-cleanup/scans/<date>.json`). **Read the JSON** — it holds paths, notes, worktree state and coverage that the terminal summary only hints at.

- **No `python3`:** on macOS, ask the person to run `xcode-select --install`. Do not install anything yourself.
- **Outside macOS:** the script uses the common rules only. Say that coverage is partial.
- **A rule failed:** the scan keeps going and records the failure in `warnings`. Mention it in the report instead of hiding it.

**Move on when** the JSON exists and you have read `candidates`, `totals`, `omitted_small`, `coverage` and `warnings`.

### Phase 2: Present the report

Build one table per risk level, keeping **the same numbers** as the scan, because those numbers are what the person will use to choose:

| # | Size | What | Why it can go | Note |
|---|---|---|---|---|

- **🟢 Safe:** caches and old versions that regenerate themselves. You may group similar items into one text line, but keep the numbers.
- **🟡 Needs your decision:** explain each item in one sentence: what is lost and how to recover it (e.g. "the VM image is downloaded again, around 10 GB").
- **🔴 Informational only:** the skill does not remove these. Say why and, when it helps, how the person can handle it themselves (e.g. "empty the Trash in Finder").

After the tables, cover these points:

- **Totals per risk.** Items marked "inside #N" do not add up: they are contained in another item.
- **Items with 🔒** require closing an app. If the session runs inside that very app (Claude, Cursor), its caches only leave with the app closed. Suggest running the skill through the `claude` CLI in a terminal.
- **"touched in the last 24h"** only appears on worktrees, sessions, downloads and builds, where it signals work in progress. Recommend leaving those for later. Caches never carry this flag, because being modified recently is normal there.
- **"shared (hardlinks)"** is space that does **not** come back when deleted (e.g. a pnpm `node_modules` pointing into the store).
- **Scan warnings:** partial reads caused by missing permission, and rules that failed.
- **Coverage:** a short block, because a report missing an item does not prove the item does not exist. Show:
  - how many repositories were analyzed and where they came from (config, Claude Code, Cursor/VS Code, home search);
  - which tools were not found;
  - which paths came from the tool itself (e.g. `npm config get cache`).

Then ask, in one sentence, whether there are projects elsewhere, especially in `~/Documents` or on an external disk. Those folders are not scanned, so macOS privacy prompts are not triggered. If the person names folders, offer to write them into `project_roots` in `~/.config/disk-cleanup/config.json`, create or edit the file only with a yes, and re-run the scan.

- **About the estimate:** the exact number only appears later. On macOS, APFS snapshots and the Docker virtual disk can hold on to part of the space.

**Move on when** the report is on screen and the person has either chosen numbers or asked questions.

### Phase 3: Ask for explicit confirmation

Ask for the numbers. The request has to be unambiguous, because deletion has no undo:

- "you can clean the green ones" → repeat the exact list (numbers and total) and ask for a yes.
- "clean everything" / "just do it" → does **not** include yellow items. 🟡 items enter only when the person names them by number or name.
- If the person asks for a 🔴 item or something outside the report, explain that this skill does not remove it and why. Do not work around it with ad-hoc commands.

Before executing, run the simulation with the chosen numbers and show the result:

```bash
python3 <skill_path>/scripts/apply.py --scan <json> --select "1,3,5-7"
```

If any item comes back as SKIPPED, explain the reason.

**Move on when** the person answers with a yes for that exact list.

If the person does not answer, do not execute. Nothing is removed; the scan simply expires after `scan_max_age_hours`.

### Phase 4: Execute

Only after the yes for that exact list:

```bash
python3 <skill_path>/scripts/apply.py --scan <json> --select "1,3,5-7" --yes
```

The script refuses scans older than 4 hours, scans from another machine, 🔴 items, items modified after the scan, and worktrees that gained changes. When it refuses, re-run the scan and repeat the confirmation with the new numbers, because numbering changes.

**🔒 items (app open).** You may be running inside the very app whose cache the person wants to clear (e.g. the Claude or Cursor app). In that case the app cannot be closed while the conversation continues. Include the confirmed 🔒 items in the same `--select`: the script executes what it can and, for the rest, prints a `PENDING` line with the exact command and the scan's expiry time. Relay that command to the person in a code block so they can run it in the terminal after closing the app. The confirmation was already given, so the command already carries `--yes`. Another option is for the person to close the app and invoke the skill from another tool (the `claude` CLI in a terminal, or Cursor to clean Claude and vice versa).

For those caches the script does not compare modification dates, because the app writes to them constantly. The safety guarantee becomes the app being closed at execution time.

### Phase 5: Report the result

- **What left and what was skipped**, each item with the reason.
- **Pending command**, if there are 🔒 items: repeat the command at the end so it does not get lost in the middle of the report.
- **Estimate vs. actual gain** in free space, which the script measures before and after. If the actual gain is much smaller, explain the likely cause: local Time Machine snapshots, the Docker virtual disk, an app that recreated the cache, or hardlinks.
- **Where the log is:** `~/.local/state/disk-cleanup/log.jsonl`.
- **If Claude Code session cleanup keeps recurring**, suggest adjusting `cleanupPeriodDays` in `~/.claude/settings.json`.

## Output Contract

The report is chat text. Do not write files. Use this shape, translated into the person's language:

```markdown
Disk: X free of Y

🟢 Safe (regenerable) — total Z
| # | Size | What | Why it can go | Note |

🟡 Needs your decision — total Z
| # | Size | What | Why it can go | Note |

🔴 Informational only
| # | Size | What | Why it can go | Note |

Omitted: N items below the MB threshold (total Z).

Coverage: tools found, tools not found, repositories analyzed and their sources,
paths reported by the tools themselves.

Warnings: ...

Do you have projects elsewhere, e.g. in ~/Documents or on an external disk?
```

Rules for the report:

- **Keep the numbers.** The person answers with them, and `--select` takes those numbers.
- **Never merge two items into one row** when their numbers differ; a merged row makes the selection ambiguous.
- **No preamble, no praise, no "great question".** Start with the disk line.
- **Do not paste the raw scan output.** It is a machine summary; the table is the deliverable.
- **Do not promise exact space.** Call it an estimate and explain why in one line.

## Validation Checklist

Before sending the report, reread it as the person would:

- [ ] Does every number come from the scan JSON, including totals and omitted items?
- [ ] Does every listed path exist in the JSON?
- [ ] Are the numbers identical to the scan, with no renumbering or merging?
- [ ] Is every "why it can go" traceable to a rule `note` or a reference doc?
- [ ] Did you mention the 🔒 apps, the "touched in the last 24h" items, the hardlink caveat and the coverage block?
- [ ] Did you ask whether projects exist outside the scanned folders?
- [ ] Is the report in the person's language, with paths and numbers untouched?

Before executing anything, check one more time:

- [ ] Did the person confirm **this** exact list, by number?
- [ ] Did you show the simulation output first?
- [ ] Were any SKIPPED items explained?
- [ ] Is `--yes` on the command only after that confirmation?

## Failure and Fallback Handling

| Situation | Behavior |
|---|---|
| `python3` missing | On macOS, ask for `xcode-select --install`. Never install tooling yourself. |
| No OS-specific rules for this system | The scan prints a warning and uses common rules only. Tell the person coverage is partial. |
| Scan JSON missing or unreadable | Re-run `scan.py`. Do not reconstruct the report from the terminal summary. |
| `apply.py` refuses ("cannot apply") | Re-run the scan and repeat the confirmation with the new numbers. Never lower the guard by editing the JSON. |
| Item comes back SKIPPED | Report the reason verbatim in the person's language. Do not retry it with a manual command. |
| App is open (🔒) | Include the item, relay the `PENDING` command in a code block, and give the expiry time. |
| Person asks for 🔴 items | Explain why the skill will not remove them and, if it exists, the manual path (e.g. empty the Trash in Finder). |
| Person asks for something outside the report | Explain that it is not in this scan and offer a scan with `project_roots` or `exclude_paths` adjusted instead. |
| Actual freed space much lower than estimated | Explain the likely cause from `references/macos.md` (APFS snapshots, Docker virtual disk, hardlinks, app cache rebuilt). |
| No usable content ("free space") | Run the scan; that request is enough. Only ask a question when the scan cannot run. |

## Personalization

The person may create `~/.config/disk-cleanup/config.json` to:

- declare where projects live;
- exclude paths;
- change age thresholds;
- disable rules.

See `references/config.md`. For safety, the config can disable rules or **raise** their risk, but never lower it.

## References

- `references/config.md`: configuration options. Read when the person wants to adjust behavior or when a project lives outside the usual folders.
- `references/rule-schema.md`: format of the rules in `rules/*.json`. Read before adding or changing a rule.
- `references/macos.md`: macOS specifics (APFS, permissions, Docker Desktop, Time Machine). Read when the actual gain diverges from the estimate or a permission error appears.
- `references/adding-an-os.md`: how to bring the skill to Linux or Windows.

## Boundaries (When Not to Use)

- **Production application caches**, container log rotation, Redis eviction: these are runtime concerns, not disk reclaiming on a developer machine.
- **Git commands** (deleting branches, fixing a broken `worktree add`): use git directly. Only worktree *removal* is in scope, and only through `apply.py`.
- **CI caches** and remote build artifacts.
- **Reviewing or cleaning source code** of any kind.
- **Scheduled destruction.** The scan phase is safe to run unattended, but applying always needs a person. See "Scheduling" in `references/config.md` for the intended design.
- **Items that need `sudo`:** these appear as informational only. The skill never runs `sudo`.
