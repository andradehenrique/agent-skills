#!/bin/bash
# Builds a fake HOME so the skill can be tested without touching the real disk.
# Usage: make_test_home.sh <folder>
# Then: HOME=<folder> XDG_STATE_HOME=<folder>/.local/state XDG_CONFIG_HOME=<folder>/.config python3 scripts/scan.py
set -e
H="$1"; [ -n "$H" ] || { echo "usage: $0 <folder>"; exit 2; }
rm -rf "$H"; mkdir -p "$H"; H="$(cd "$H" && pwd -P)"
old() { touch -t 202601010000 "$@"; }
blob() { mkdir -p "$(dirname "$1")"; dd if=/dev/urandom of="$1" bs=1048576 count="$2" 2>/dev/null; }

# Candidates
blob "$H/.npm/_cacache/content/a" 3                                    # 🟢 npm cache
blob "$H/Library/Caches/com.example.app/data" 2                        # 🟢 generic cache
blob "$H/Library/Application Support/Claude/Cache/data" 3              # 🟢 🔒 requires the Claude app closed
blob "$H/Downloads/old.dmg" 2; old "$H/Downloads/old.dmg"              # 🟡 old installer
P="$H/.claude/projects/-Users-x-work-repo"
blob "$P/old-session.jsonl" 2; old "$P/old-session.jsonl"              # 🟡 old session

# Traps (none of this may disappear)
blob "$H/Documents/important.txt" 2
mkdir -p "$H/.cache"; ln -s "$H/Documents" "$H/.cache/uv"              # symlink into a protected area
blob "$H/Downloads/new.dmg" 2                                          # recent
blob "$H/Downloads/spreadsheet.xlsx" 2; old "$H/Downloads/spreadsheet.xlsx"  # not an installer
blob "$P/new-session.jsonl" 2                                          # recent session
mkdir -p "$P/memory"; echo "remember" > "$P/memory/MEMORY.md"; old "$P/memory/MEMORY.md" "$P/memory"
mkdir -p "$H/.Trash"

# Repository with one clean and one dirty worktree
G="git -c user.name=t -c user.email=t@t -c init.defaultBranch=main"
R="$H/work/repo"; mkdir -p "$R"; cd "$R"
$G init -q; echo node_modules > .gitignore; echo a > a.txt; echo '{}' > package.json; $G add .; $G commit -qm init
$G clone -q --bare "$R" "$H/remote.git"; $G remote add origin "$H/remote.git"; $G fetch -q origin
$G worktree add -q "$R/.claude/worktrees/clean" -b clean origin/main 2>/dev/null
blob "$R/.claude/worktrees/clean/node_modules/pkg/x.bin" 2
$G worktree add -q "$R/.claude/worktrees/dirty" -b dirty origin/main 2>/dev/null
blob "$R/.claude/worktrees/dirty/node_modules/pkg/x.bin" 2
echo "unsaved work" > "$R/.claude/worktrees/dirty/a.txt"
find "$R/.git/worktrees" \( -name HEAD -o -path '*logs*' \) -exec touch -t 202601010000 {} \;

# Projects outside the standard roots (a fixed folder would never find them)
stale_repo() { # creates a repository idle for months with an ignored node_modules
  local r="$1"; mkdir -p "$r"; ( cd "$r"
    $G init -q; echo node_modules > .gitignore; echo x > x.txt
    [ "${2:-}" = no-manifest ] || echo '{}' > package.json
    $G add .; $G commit -qm init )
  blob "$r/node_modules/dep/lib.bin" 3
  touch -t 202601010000 "$r/.git/HEAD" "$r/.git/logs/HEAD"
}
#  a) too deep for the home search; only Claude Code knows about it
NOTES="$H/Notes/personal/vaults/notes"; stale_repo "$NOTES" no-manifest   # node_modules without package.json
printf '{"projects": {"%s": {}}}\n' "$NOTES" > "$H/.claude.json"
#  b) inside ~/Documents (a personal area); only Cursor knows about it. Has one clean worktree.
APP="$H/Documents/GitHub/app"; stale_repo "$APP"
( cd "$APP"; $G clone -q --bare "$APP" "$H/app-remote.git"; $G remote add origin "$H/app-remote.git"; $G fetch -q origin
  $G worktree add -q "$H/Documents/GitHub/app-hotfix" -b hotfix origin/main 2>/dev/null )
blob "$H/Documents/GitHub/app-hotfix/node_modules/dep/lib.bin" 2
find "$APP/.git/worktrees" \( -name HEAD -o -path '*logs*' \) -exec touch -t 202601010000 {} \;
WS="$H/Library/Application Support/Cursor/User/workspaceStorage/a1b2c3"; mkdir -p "$WS"
printf '{"folder": "file://%s"}\n' "$APP" > "$WS/workspace.json"

# Ages projects and worktrees: without this everything looks "touched in the last 24h"
# just because the fixture was created now. The new session and new.dmg stay recent.
find "$H/work" "$H/Documents/GitHub" "$H/Notes" -exec touch -h -t 202601010000 {} + 2>/dev/null || true

# Config: small items show up and rules that touch the real system stay off
mkdir -p "$H/.config/disk-cleanup"
cat > "$H/.config/disk-cleanup/config.json" <<JSON
{"min_size_mb": 1,
 "rules": {"docker": {"enabled": false}, "homebrew": {"enabled": false},
           "simulators-unavailable": {"enabled": false}, "time-machine-local-snapshots": {"enabled": false}}}
JSON
echo "$H"
