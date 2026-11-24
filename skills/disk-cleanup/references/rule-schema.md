# Rule format

Rules live in `rules/common.json` (valid on any OS) and `rules/<os>.json`
(`macos`, `linux`, `windows`). `scan.py` loads both, in that order. Each rule
is an object inside `rules`.

## Fields

| Field | Required | Description |
|---|---|---|
| `id` | yes | Unique identifier, kebab-case. The user config refers to it. |
| `tool` | yes | Name shown in the report ("Cursor", "Docker", "macOS"). |
| `category` | yes | `cache`, `versions`, `logs`, `sessions`, `temp`, `state`, `build`, `worktree`, `container`, `downloads`, `system`. |
| `kind` | yes | How to find candidates (see below). |
| `risk` | yes | `green` (regenerable), `yellow` (needs a decision), `red` (informational only, never removed). |
| `method` | yes | `delete`, `trash` (Trash), `command` (native command) or `manual` (not removable by the skill). |
| `paths` | depends on `kind` | List of paths or globs, or a dict per OS: `{"macos": [...], "linux": [...]}`. Accepts `~`, `$VAR`, `{uid}`, `{tmpdir}`, `{claude_dir}`, `{xdg_data}`, `{xdg_cache}`, `{xdg_config}`, `{cargo_home}` and `{gradle_home}`. Placeholders honor the matching environment variables. Never write a hardcoded user path. |
| `resolve` | no | Sources tried before `paths`: `{"cmd": [...], "suffix": "..."}` (the last output line is the path) or `{"defaults": [domain, key]}` (macOS only). The first one that returns an existing folder wins. |
| `in_use_which` | no | Only for `kind: versions`. Binaries whose real target (via `which`) is never removed. |
| `title` | no | Title template. Variables: `{name}`, `{base}`, `{count}`, `{keep}`, `{path}`. |
| `note` | no | Short explanation shown to the user: what is lost, how to recover it. |
| `requires_closed` | no | Process names that must be closed (`ps -axco comm`). List or dict per OS. |
| `min_age_days` / `min_age_hours` | no | Ignores items modified more recently than this. Measured on the newest file inside the item. |
| `command` / `fallback` | with `method: command` | Command without a shell, as a list. `fallback: "delete"` deletes the paths when the command does not exist. |
| `regenerates` | no | `true` when the tool recreates the content on its own. |
| `verified` | no | `false` for rules written from documentation, without a test on a real machine. |
| `generic` | no | Broad sweep (e.g. `~/Library/Caches/*`). Gives way to specific rules covering the same path. |
| `always_show` | no | Shows even below `min_size_mb`. |
| `os` | no | Restricts the rule to certain OSes, e.g. `["macos", "linux"]`. |

## Kinds

- **`paths`**: every existing path becomes a candidate.
- **`children`**: every child of a folder becomes a candidate. Extra fields:
  - `match` and `exclude` (name globs);
  - `dirs_only` and `files_only`;
  - `aggregate: true`, which joins the eligible children of each base folder into a
    single item. `apply.py` deletes exactly the list recorded at scan time.
- **`versions`**: versions side by side in a folder. Extra fields:
  - `keep_latest` (default 1);
  - `version_sort` (`semver` or `mtime`);
  - `in_use_link`, a symlink whose target is never removed.
- **`extension_dups`**: editor extensions with more than one version. Keeps the highest.
- **`git_worktrees`**: worktrees of the repositories in `project_roots`. The git
  state decides the risk, not the rule:
  - with changes, with commits missing from the remote, locked or with recent activity → 🔴;
  - clean → 🟡, removed with `git worktree remove`, without `--force`;
  - orphan record → 🟢, removed with `git worktree prune`.
- **`stale_build_dirs`**: folders listed in `names` (with each one's risk) inside
  repositories idle for `stale_project_days`. Only those `git check-ignore` confirms
  as ignored enter. 🟢 also requires the manifest next to it (`MANIFESTS` in
  `scan.py`): `package.json` for `node_modules`; `pyproject.toml`,
  `requirements.txt` and so on for `.venv`; `Cargo.toml` or `pom.xml` for `target`.
  Without the manifest the item becomes 🟡, because "recreatable" would be a promise
  with no guarantee. The same check applies to the `node_modules` offered next to a
  worktree.
- **`command`**: its own logic in `scan.py` (`HANDLERS`). Examples: `docker`,
  `brew`, `simctl_unavailable`, `tm_snapshots`.

## Criteria for classifying risk

- **🟢** The owner of the content recreates it without intervention and without loss
  to the user. The worst case is being slower or downloading something small again.
- **🟡** It can be recovered, but at a noticeable cost (large download, long rebuild)
  or with a loss of convenience (session history, project context).
- **🔴** It may hold the user's work or data, or we do not know whether it is
  regenerable. When in doubt, use 🔴: a rule can be lowered after verification.

## Checklist for a new rule

1. Confirm on a real machine the path, the size, and what the app does when the
   folder disappears. If that is not possible, mark `"verified": false`.
2. Prefer the tool's own cleanup command (`method: command`) over deleting the folder.
3. Fill in `requires_closed` for caches of running apps.
4. Write a `note` that answers: "what do I lose if I delete this?"
5. Run `python3 scripts/scan.py --rule <id>` and check the result.
