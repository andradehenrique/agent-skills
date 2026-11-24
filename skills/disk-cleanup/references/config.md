# Configuration

Optional file at `~/.config/disk-cleanup/config.json`. If `XDG_CONFIG_HOME` is
set, the file lives at `$XDG_CONFIG_HOME/disk-cleanup/config.json`. Missing
fields use the default.

```json
{
  "project_roots": ["~/work", "~/projects"],
  "exclude_paths": ["~/work/legacy-project/node_modules"],
  "min_size_mb": 10,
  "stale_project_days": 30,
  "active_guard_hours": 24,
  "scan_max_age_hours": 4,
  "rules": {
    "claude-app-vm": {"enabled": false},
    "claude-code-sessions": {"min_age_days": 90},
    "user-caches": {"risk": "yellow"}
  }
}
```

| Field | Default | Effect |
|---|---|---|
| `project_roots` | `~/work`, `~/projects`, `~/dev`, `~/code`, `~/src`, `~/Developer` | Where to look for repositories, up to 4 levels deep. |
| `exclude_paths` | `[]` | Never listed, never touched, and neither are their children or parents. |
| `min_size_mb` | 10 | Smaller items only add to the footer total. |
| `stale_project_days` | 30 | Projects with no local git activity for longer than this get their build artifacts listed. |
| `active_guard_hours` | 24 | Worktrees with activity more recent than this become 🔴. Other items show the "touched in the last Xh" flag. |
| `scan_max_age_hours` | 4 | Maximum age of a scan for `apply.py` to accept it. |
| `rules.<id>` | — | `enabled`, `min_age_days`, `min_age_hours`, `keep_latest` and `risk` (only accepts a higher risk). |

## Where the skill looks for repositories

Worktrees and build artifacts depend on finding the repositories. The skill
does not rely on a fixed folder; it merges four sources, and the report shows
how many repositories came from each one:

1. **`project_roots`**: the defaults above plus whatever the person adds. Walks up to 4 levels.
2. **Claude Code**: the paths registered under `projects` in `~/.claude.json`
   (or `$CLAUDE_CONFIG_DIR/.claude.json`).
3. **Cursor, VS Code, VS Code Insiders, Windsurf and VSCodium**: the `workspace.json`
   of each folder opened in `User/workspaceStorage`.
4. **Shallow home search**: up to 3 levels, skipping `Library`, hidden folders and the
   personal and media folders.

Every path found goes through `git rev-parse --git-common-dir`. That way a
subfolder or a worktree points to the main repository, and the worktrees come
from that repository's `git worktree list`.

Repositories outside the home only enter if the folder is in `project_roots`.
That includes external disks (`/Volumes/...`) and `/opt/code`.

## Paths each person may have moved

Before the default path, the rules ask the tool itself or read the environment
variable:

| Tool | Where the path comes from |
|---|---|
| npm | `npm config get cache` |
| pnpm | `pnpm store path` |
| Yarn 1 | `yarn cache dir` |
| pip | `pip3 cache dir` |
| uv | `uv cache dir` |
| Go | `go env GOMODCACHE` |
| Cargo | `$CARGO_HOME` |
| Gradle | `$GRADLE_USER_HOME` |
| Xcode DerivedData | the `IDECustomDerivedDataLocation` preference |
| Claude Code | `$CLAUDE_CONFIG_DIR` |
| opencode and others | `$XDG_DATA_HOME`, `$XDG_CACHE_HOME`, `$XDG_CONFIG_HOME` |

Not covered yet: the Maven `localRepository` set in `settings.xml` and the
Yarn Berry per-project caches.

On macOS, `git`, `pip3` and `xcrun` in `/usr/bin` are shims that open the
Command Line Tools install window. When the tools are not installed, the skill
does not call those shims and says so in the report.

## Protection the config cannot change

Protection has two levels:

- **Absolute:** nothing enters, under any rule. Applies to the list below.
- **Personal (Documents and Desktop):** generic rules never enter. Git rules can
  act on a repository there, because git itself confirms what is a registered
  worktree and what is an ignored folder.

The fixed list in `scripts/common.py` (`PROTECTED_HOME` and `PROTECTED_ABS`)
cannot be switched off. It covers:

- media folders (Pictures, Movies, Music);
- iCloud, Keychains, Mail, Messages and Photos;
- `~/Library/Containers`;
- credentials (`.ssh`, `.aws`, `.kube`, `.gnupg`);
- Claude Code configuration (`settings.json`, `CLAUDE.md`, `skills/`, `plugins/`);
- Cursor and opencode configuration.

The `memory/` folder of Claude Code sessions stays out of the session rule.

## Scheduling (future)

The design already separates what can run with nobody watching:

- **`scan.py --quiet`** is read-only and can run on a schedule to produce reports
  (e.g. warn when more than X GB are reclaimable).
- **`apply.py --yes`** still needs a person. To automate it in the future, the
  intended path is an explicit list of pre-approved 🟢 rules in the config
  (e.g. `"auto_apply": ["npm-cache", "claude-code-tmp"]`), never including 🟡 or 🔴.
  That is not implemented yet.
- `log.jsonl` already records every run, which allows auditing later what a
  scheduled job did.
