#!/usr/bin/env python3
"""Scans the system and lists cleanup candidates. READ ONLY.

Usage:
    python3 scan.py [--out FILE.json] [--rule ID ...] [--quiet]

Writes a JSON with the candidates (the "plan" apply.py accepts) and prints a
summary report. Nothing is deleted here.
"""
import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import socket
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

RISK_ORDER = {"green": 0, "yellow": 1, "red": 2}
RECENT_MATTERS = {"worktree", "sessions", "downloads", "build"}
RISK_LABEL = {"green": "🟢 Safe (regenerable)", "yellow": "🟡 Needs your decision",
              "red": "🔴 Informational only (the skill does not remove)"}


class Ctx:
    def __init__(self, cfg, osname):
        self.cfg = cfg
        self.os = osname
        self.now = time.time()
        self.procs = C.running_processes(osname)
        self.warnings = []
        self._repos = None
        self.repo_sources = {}
        self.path_sources = {}
        self.present = set()  # rules whose tool/folder exists on this machine

    def age_days(self, ts):
        return (self.now - ts) / 86400 if ts else None

    def guard_seconds(self):
        return self.cfg["active_guard_hours"] * 3600


def make_candidate(rule, ctx, title, paths, measured=None, **extra):
    if measured is None:
        measured = {"bytes": 0, "shared_bytes": 0, "files": 0, "newest": 0.0, "errors": 0}
        for p in paths:
            m = C.measure(p)
            for k in ("bytes", "shared_bytes", "files", "errors"):
                measured[k] += m[k]
            measured["newest"] = max(measured["newest"], m["newest"])
    closed = C.pick_for_os(rule.get("requires_closed"), ctx.os) or []
    blocked = [name for name in closed if name in ctx.procs]
    key = rule["id"] + "|" + "|".join(paths) + "|" + title
    cand = {
        "id": rule["id"] + ":" + hashlib.sha1(key.encode()).hexdigest()[:8],
        "rule": rule["id"],
        "tool": rule.get("tool", ""),
        "category": rule.get("category", ""),
        "title": title,
        "paths": paths,
        "bytes": measured["bytes"],
        "shared_bytes": measured["shared_bytes"],
        "files": measured["files"],
        "newest_mtime": measured["newest"],
        "age_days": round(ctx.age_days(measured["newest"]), 1) if measured["newest"] else None,
        "partial": measured["errors"] > 0,
        "risk": rule.get("risk", "yellow"),
        "method": rule.get("method", "delete"),
        "command": rule.get("command"),
        "fallback": rule.get("fallback"),
        "requires_closed": closed,
        "blocked_by": blocked,
        "regenerates": rule.get("regenerates", False),
        "verified": rule.get("verified", True),
        "note": rule.get("note", ""),
        "always_show": rule.get("always_show", False),
        "generic": rule.get("generic", False),
        # For a cache, log or version, being modified recently is normal; the flag
        # only makes sense where it signals work in progress.
        "recently_used": rule.get("category") in RECENT_MATTERS and bool(measured["newest"])
                         and ctx.now - measured["newest"] < ctx.guard_seconds(),
    }
    cand.update(extra)
    return cand


def _age_ok(rule, ctx, newest):
    """Honors the rule min_age_* and the recent-activity guard."""
    age = ctx.now - newest if newest else float("inf")
    min_days = rule.get("min_age_days")
    if min_days is not None and age < min_days * 86400:
        return False
    if rule.get("min_age_hours") is not None and age < rule["min_age_hours"] * 3600:
        return False
    return True


def _matches(name, patterns):
    return any(fnmatch.fnmatch(name, p) for p in patterns)


# ---------------------------------------------------------------------------
# Rule kinds
# ---------------------------------------------------------------------------

def kind_paths(rule, ctx):
    """Every existing path becomes a whole candidate."""
    out = []
    paths, source = C.resolve_paths(rule, ctx.os)
    ctx.path_sources[rule["id"]] = source
    if paths:
        ctx.present.add(rule["id"])
    for path in paths:
        m = C.measure(path)
        if not _age_ok(rule, ctx, m["newest"]):
            continue
        name = rule.get("title", "{name}").format(name=os.path.basename(path), path=path)
        out.append(make_candidate(rule, ctx, name, [path], m, path_source=source))
    return out


def kind_children(rule, ctx):
    """Children of a folder, filtered by name and age.

    aggregate=true joins the eligible children of each base folder into a single
    candidate (e.g. "142 sessions older than 30 days in <project>").
    """
    out = []
    match = rule.get("match", ["*"])
    exclude = rule.get("exclude", [])
    for base in C.resolve_paths(rule, ctx.os)[0]:
        if not os.path.isdir(base):
            continue
        ctx.present.add(rule["id"])
        picked, total = [], {"bytes": 0, "shared_bytes": 0, "files": 0, "newest": 0.0, "errors": 0}
        try:
            names = sorted(os.listdir(base))
        except OSError:
            ctx.warnings.append("no permission to list %s" % base)
            continue
        for name in names:
            if not _matches(name, match) or _matches(name, exclude):
                continue
            path = os.path.join(base, name)
            if os.path.islink(path):
                continue
            if rule.get("dirs_only") and not os.path.isdir(path):
                continue
            if rule.get("files_only") and not os.path.isfile(path):
                continue
            m = C.measure(path)
            if not _age_ok(rule, ctx, m["newest"]):
                continue
            if rule.get("aggregate"):
                picked.append(path)
                for k in ("bytes", "shared_bytes", "files", "errors"):
                    total[k] += m[k]
                total["newest"] = max(total["newest"], m["newest"])
            else:
                title = rule.get("title", "{name}").format(name=name, base=os.path.basename(base), path=path)
                out.append(make_candidate(rule, ctx, title, [path], m))
        if rule.get("aggregate") and picked:
            title = rule.get("title", "{count} items in {base}").format(
                count=len(picked), base=os.path.basename(base), path=base)
            out.append(make_candidate(rule, ctx, title, picked, total, base=base))
    return out


def kind_versions(rule, ctx):
    """Old versions side by side in a folder. Keeps the N newest and the one in use."""
    out = []
    keep = rule.get("keep_latest", 1)
    in_use = set()
    for link in C.pick_for_os(rule.get("in_use_link"), ctx.os) or []:
        in_use.add(os.path.realpath(C.expand(link)))
    for binary in rule.get("in_use_which", []):
        found = shutil.which(binary)
        if found:
            in_use.add(os.path.realpath(found))
    for base in C.resolve_paths(rule, ctx.os)[0]:
        if not os.path.isdir(base):
            continue
        ctx.present.add(rule["id"])
        entries = [os.path.join(base, n) for n in os.listdir(base)
                   if not n.startswith(".") and _matches(n, rule.get("match", ["*"]))]
        entries = [e for e in entries if not os.path.islink(e)]
        if rule.get("version_sort", "semver") == "mtime":
            entries.sort(key=lambda p: os.lstat(p).st_mtime, reverse=True)
        else:
            entries.sort(key=lambda p: C.version_key(os.path.basename(p)), reverse=True)
        for path in entries[keep:]:
            real = os.path.realpath(path)
            if any(C.is_within(u, real) for u in in_use):
                continue
            m = C.measure(path)
            if not _age_ok(rule, ctx, m["newest"]):
                continue
            title = rule.get("title", "{name}").format(name=os.path.basename(path), keep=os.path.basename(entries[0]))
            out.append(make_candidate(rule, ctx, title, [path], m,
                                      kept=[os.path.basename(e) for e in entries[:keep]]))
    return out


def kind_extension_dups(rule, ctx):
    """Editor extensions (VS Code/Cursor) with more than one version installed."""
    import re
    out = []
    pattern = re.compile(r"^(?P<id>.+?)-(?P<ver>\d+\.\d+\.\d+[^/]*)$")
    for base in C.glob_paths(rule["paths"], ctx.os):
        ctx.present.add(rule["id"])
        groups = {}
        for name in os.listdir(base):
            m = pattern.match(name)
            if m and os.path.isdir(os.path.join(base, name)):
                groups.setdefault(m.group("id"), []).append((C.version_key(m.group("ver")), name))
        for ext_id, versions in groups.items():
            if len(versions) < 2:
                continue
            versions.sort(reverse=True)
            for _, name in versions[1:]:
                path = os.path.join(base, name)
                title = rule.get("title", "{name}").format(name=name, ext=ext_id, keep=versions[0][1])
                out.append(make_candidate(rule, ctx, title, [path], kept=[versions[0][1]]))
    return out


# --- git repositories ------------------------------------------------------

SKIP_DIRS = {"node_modules", ".git", ".venv", "venv", "vendor", "target", "dist", "build",
             ".next", ".cache", "Library", ".Trash"}


def _walk_for_repos(root, max_depth, skip_names=()):
    """Folders with .git up to max_depth levels below root (does not descend into repositories)."""
    found = []
    stack = [(root, 0)]
    while stack:
        path, depth = stack.pop()
        if os.path.isdir(os.path.join(path, ".git")):
            found.append(path)
            continue
        if depth >= max_depth:
            continue
        try:
            for entry in os.scandir(path):
                if entry.is_dir(follow_symlinks=False) and entry.name not in SKIP_DIRS \
                        and entry.name not in skip_names and not entry.name.startswith("."):
                    stack.append((entry.path, depth + 1))
        except OSError:
            continue
    return found


def _editor_storage_dirs(osname):
    apps = ["Cursor", "Code", "Code - Insiders", "Windsurf", "VSCodium"]
    if osname == "macos":
        base = C.expand("~/Library/Application Support")
    elif osname == "linux":
        base = C.expand("{xdg_config}")
    elif osname == "windows":
        base = os.environ.get("APPDATA", "")
    else:
        return []
    return [(app, os.path.join(base, app, "User", "workspaceStorage")) for app in apps]


def project_hints(ctx):
    """Project folders the person's tools already know about: (path, source)."""
    from urllib.parse import unquote, urlparse
    hints = []
    # Claude Code stores the exact path of every project opened.
    claude_json = os.path.join(os.environ.get("CLAUDE_CONFIG_DIR") or C.home(), ".claude.json")
    try:
        with open(claude_json, encoding="utf-8") as fh:
            for path in json.load(fh).get("projects", {}):
                hints.append((path, "Claude Code"))
    except (OSError, ValueError):
        pass
    # Cursor / VS Code / Windsurf: one workspace.json per opened folder.
    for app, storage in _editor_storage_dirs(ctx.os):
        if not os.path.isdir(storage):
            continue
        for name in os.listdir(storage):
            try:
                with open(os.path.join(storage, name, "workspace.json"), encoding="utf-8") as fh:
                    uri = json.load(fh).get("folder", "")
            except (OSError, ValueError):
                continue
            if uri.startswith("file://"):
                hints.append((unquote(urlparse(uri).path), app))
    return hints


def _repo_top(path):
    """Main repository containing `path` (resolves subfolders and worktrees)."""
    code, out, _ = C.run(["git", "-C", path, "rev-parse", "--git-common-dir"], timeout=10)
    if code != 0 or not out.strip():
        return None
    common = os.path.normpath(os.path.join(path, out.strip()))
    if os.path.basename(common) != ".git":
        return None  # bare repository or unusual layout: better not to touch
    return os.path.dirname(common)


def find_repos(ctx):
    """Main repositories, from four sources, with each one's origin.

    1. `project_roots` from the config (defaults + whatever the person adds), up to 4 levels;
    2. projects registered by Claude Code;
    3. workspaces opened in Cursor, VS Code and Windsurf;
    4. a shallow home search (3 levels), skipping Library, hidden folders and the
       personal folders (Documents, Desktop, Downloads...), so macOS privacy
       prompts are not triggered. Projects in those folders arrive through
       sources 1 to 3.
    """
    if ctx._repos is not None:
        return ctx._repos
    if not C.tool_available("git"):
        ctx._repos = []
        ctx.warnings.append("git is not available: worktrees and build artifacts were not analyzed.")
        return ctx._repos
    sources = {}

    def add(repo, source):
        if repo:
            sources.setdefault(os.path.realpath(repo), set()).add(source)

    for root in ctx.cfg["project_roots"]:
        if os.path.isdir(root):
            for repo in _walk_for_repos(root, 4):
                add(repo, "config: " + root.replace(C.home(), "~"))
    seen_hint = set()
    for path, source in project_hints(ctx):
        if path in seen_hint or not os.path.isdir(path):
            continue
        seen_hint.add(path)
        add(_repo_top(path), source)
    skip = set(C.PERSONAL_HOME) | {"Downloads", "Pictures", "Movies", "Music", "Library",
                                   "Applications", "Public", "Videos"}
    for repo in _walk_for_repos(C.home(), 3, skip):
        add(repo, "home search")

    home = C.home()
    ctx.repo_sources = {}
    for repo, srcs in sources.items():
        if not C.is_within(repo, home) and not any(C.is_within(repo, r) for r in ctx.cfg["project_roots"]):
            ctx.warnings.append("Repository outside the home ignored (add the folder to project_roots if you want it): "
                                + repo)
            continue
        ctx.repo_sources[repo] = sorted(srcs)
    ctx._repos = sorted(ctx.repo_sources)
    return ctx._repos


def git_activity(repo_or_worktree):
    """Last sign of local use: HEAD and reflog (commits, checkouts, rebases).
    FETCH_HEAD stays out because IDEs fetch on their own."""
    code, gitdir, _ = C.run(["git", "-C", repo_or_worktree, "rev-parse", "--absolute-git-dir"], timeout=10)
    if code != 0:
        return 0
    gitdir = gitdir.strip()
    stamps = []
    # The index stays out: any `git status` (from IDEs or from this very scan,
    # if it did not use --no-optional-locks) updates its date.
    for name in ("HEAD", os.path.join("logs", "HEAD")):
        try:
            stamps.append(os.stat(os.path.join(gitdir, name)).st_mtime)
        except OSError:
            pass
    return max(stamps) if stamps else 0


def worktree_state(path):
    """State that decides whether a worktree can go: changes and unpushed commits."""
    code, status, _ = C.run(["git", "--no-optional-locks", "-C", path, "status", "--porcelain"], timeout=30)
    dirty = len([line for line in status.splitlines() if line.strip()]) if code == 0 else None
    code, ahead, _ = C.run(["git", "-C", path, "rev-list", "--count", "HEAD", "--not", "--remotes"], timeout=30)
    unpushed = int(ahead.strip()) if code == 0 and ahead.strip().isdigit() else None
    return {"dirty": dirty, "unpushed": unpushed}


def kind_git_worktrees(rule, ctx):
    out = []
    if not C.tool_available("git"):
        return out
    if find_repos(ctx):
        ctx.present.add(rule["id"])
    for repo in find_repos(ctx):
        code, text, _ = C.run(["git", "-C", repo, "worktree", "list", "--porcelain"], timeout=20)
        if code != 0:
            continue
        blocks = [b for b in text.strip().split("\n\n") if b.strip()]
        for block in blocks[1:]:  # the first one is the main repository
            info = {}
            for line in block.splitlines():
                key, _, value = line.partition(" ")
                info[key] = value or True
            path = info.get("worktree")
            branch = str(info.get("branch", "detached HEAD")).replace("refs/heads/", "")
            label = "%s → %s (%s)" % (os.path.basename(repo), os.path.basename(path), branch)
            if info.get("prunable") or not os.path.isdir(path):
                out.append(make_candidate(
                    dict(rule, risk="green", method="command"), ctx,
                    "Orphan worktree record: " + label, [],
                    command=["git", "-C", repo, "worktree", "prune"], always_show=True, git_verified=True,
                    note="The folder is already gone; this only cleans the git record.", repo=repo))
                continue
            state = worktree_state(path)
            activity = git_activity(path)
            problems = []
            if info.get("locked"):
                problems.append("locked (git worktree lock)")
            if state["dirty"]:
                problems.append("%d uncommitted change(s)" % state["dirty"])
            if state["unpushed"]:
                problems.append("%d commit(s) not on any remote" % state["unpushed"])
            if state["dirty"] is None or state["unpushed"] is None:
                problems.append("could not read the git state")
            if activity and ctx.now - activity < ctx.guard_seconds():
                problems.append("used in the last %dh (a session may still be active)" % ctx.cfg["active_guard_hours"])
            m = C.measure(path)
            age = ctx.age_days(activity or m["newest"])
            extra = dict(repo=repo, branch=branch, worktree_state=state, git_verified=True,
                         last_activity_days=round(age, 1) if age is not None else None,
                         recheck="worktree")
            if problems:
                out.append(make_candidate(
                    dict(rule, risk="red", method="manual"), ctx, "Worktree " + label, [path], m,
                    note="Not removing: " + "; ".join(problems) + ".", always_show=True, **extra))
                continue
            out.append(make_candidate(
                dict(rule, method="command"), ctx, "Worktree " + label, [path], m,
                command=["git", "-C", repo, "worktree", "remove", path],
                note="No changes and everything pushed to the remote. Removes the folder and the record (git worktree remove, without --force).",
                **extra))
            nm = os.path.join(path, "node_modules")
            if os.path.isdir(nm) and not os.path.islink(nm):
                ok, mnote = manifest_check(nm)
                out.append(make_candidate(
                    dict(rule, risk="green" if ok else "yellow", method="delete", category="build",
                         regenerates=ok), ctx,
                    "Only the node_modules of worktree " + label, [nm],
                    note="Lighter alternative: keeps the worktree and deletes only the dependencies. " + mnote,
                    repo=repo, git_verified=True))
    return out


# What must sit next to the folder for it to be recreatable. Without the
# manifest, "comes back with npm install" would be a false promise.
MANIFESTS = {
    "node_modules": ["package.json"],
    ".next": ["package.json"], ".nuxt": ["package.json"], ".turbo": ["package.json"],
    ".parcel-cache": ["package.json"], ".angular": ["angular.json", "package.json"],
    ".venv": ["pyproject.toml", "requirements.txt", "Pipfile", "setup.py", "uv.lock", "poetry.lock"],
    "venv": ["pyproject.toml", "requirements.txt", "Pipfile", "setup.py", "uv.lock", "poetry.lock"],
    "target": ["Cargo.toml", "pom.xml", "build.sbt"],
    ".gradle": ["build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts"],
}
REBUILD_HINT = {"node_modules": "npm/yarn/pnpm install", ".venv": "recreate the virtual environment",
                "venv": "recreate the virtual environment", "target": "run the build again"}


def manifest_check(path):
    """(has_manifest, note). Folders without a manifest rule pass through."""
    name = os.path.basename(path)
    needed = MANIFESTS.get(name)
    if not needed:
        return True, ""
    parent = os.path.dirname(path)
    if any(os.path.exists(os.path.join(parent, m)) for m in needed):
        return True, "Recreatable with %s (found %s next to it)." % (
            REBUILD_HINT.get(name, "the project build"),
            next(m for m in needed if os.path.exists(os.path.join(parent, m))))
    return False, ("No %s next to it: this folder may not be recreatable. "
                   "It may have been installed by hand or by a plugin." % " / ".join(needed[:3]))


def kind_stale_build_dirs(rule, ctx):
    """Build artifacts ignored by git in projects idle for N days."""
    out = []
    names = rule["names"]  # {"node_modules": "green", "dist": "yellow", ...}
    stale = ctx.cfg["stale_project_days"] * 86400
    if find_repos(ctx):
        ctx.present.add(rule["id"])
    for repo in find_repos(ctx):
        activity = git_activity(repo)
        if not activity or ctx.now - activity < stale:
            continue
        found = []
        stack = [(repo, 0)]
        while stack:
            path, depth = stack.pop()
            try:
                entries = list(os.scandir(path))
            except OSError:
                continue
            for entry in entries:
                if not entry.is_dir(follow_symlinks=False):
                    continue
                if entry.name in names:
                    found.append(entry.path)
                elif depth < rule.get("max_depth", 3) and entry.name != ".git" \
                        and not os.path.exists(os.path.join(entry.path, ".git")):
                    stack.append((entry.path, depth + 1))
        for path in found:
            # Only what git ignores: this way a versioned "dist" is never deleted.
            if C.run(["git", "-C", repo, "check-ignore", "-q", path], timeout=10)[0] != 0:
                continue
            name = os.path.basename(path)
            rel = os.path.relpath(path, os.path.dirname(repo))
            ok, note = manifest_check(path)
            risk = names[name] if ok else "yellow"
            out.append(make_candidate(
                dict(rule, risk=risk, regenerates=ok, note=note or rule.get("note", "")), ctx,
                "%s (project idle for %d days)" % (rel, ctx.age_days(activity)),
                [path], repo=repo, git_verified=True))
    return out


# --- comandos nativos ----------------------------------------------------------

def handler_docker(rule, ctx):
    if not C.run(["docker", "--version"], timeout=10)[0] == 0:
        return []
    ctx.present.add(rule["id"])
    code, out, err = C.run(["docker", "system", "df", "--format", "{{json .}}"], timeout=60)
    if code != 0:
        ctx.warnings.append("Docker is installed but did not answer (is Docker Desktop running?): %s" % err.strip()[:120])
        return []
    plan = {
        "Build Cache": ("green", ["docker", "builder", "prune", "-f"], "Docker build cache",
                        "Regenerable; the next build is slower."),
        "Images": ("yellow", ["docker", "image", "prune", "-a", "-f"], "Images no container is using",
                   "They have to be downloaded again when you need them."),
        "Containers": ("yellow", ["docker", "container", "prune", "-f"], "Stopped containers",
                       "Loses the internal state of stopped containers (anything not in a volume)."),
        "Local Volumes": ("red", None, "Volumes with no container",
                          "Volumes hold data (e.g. local databases). Remove them by hand with `docker volume rm <name>` only if you are sure."),
    }
    cands = []
    for line in out.splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        item = plan.get(row.get("Type"))
        if not item:
            continue
        reclaim = C.parse_size(row.get("Reclaimable", ""))
        risk, cmd, title, note = item
        measured = {"bytes": reclaim, "shared_bytes": 0, "files": 0, "newest": 0, "errors": 0}
        if ctx.os == "macos":
            note += " On the Mac, Docker Desktop keeps everything in a virtual disk that may not shrink right away."
        cands.append(make_candidate(dict(rule, risk=risk, method="command" if cmd else "manual"), ctx,
                                    title, [], measured, command=cmd, note=note))
    return cands


def handler_brew(rule, ctx):
    if not C.run(["brew", "--version"], timeout=10)[0] == 0:
        return []
    ctx.present.add(rule["id"])
    code, out, err = C.run(["brew", "cleanup", "-n", "--prune=all"], timeout=180)
    text = out + err
    import re
    m = re.search(r"free approximately ([\d.]+\s*[KMGT]?B)", text)
    reclaim = C.parse_size(m.group(1), binary=True) if m else 0
    lines = len([l for l in out.splitlines() if l.startswith("Would remove")])
    measured = {"bytes": reclaim, "shared_bytes": 0, "files": lines, "newest": 0, "errors": 0}
    return [make_candidate(rule, ctx, "Homebrew: old versions and cached downloads", [], measured,
                           command=["brew", "cleanup", "--prune=all"])] if reclaim else []


def handler_simctl_unavailable(rule, ctx):
    if not C.tool_available("xcrun"):
        return []
    code, out, _ = C.run(["xcrun", "simctl", "list", "devices", "unavailable", "-j"], timeout=60)
    if code != 0:
        return []
    ctx.present.add(rule["id"])
    try:
        data = json.loads(out)
    except ValueError:
        return []
    base = C.expand("~/Library/Developer/CoreSimulator/Devices")
    paths = []
    for devices in data.get("devices", {}).values():
        for dev in devices:
            p = os.path.join(base, dev.get("udid", ""))
            if os.path.isdir(p):
                paths.append(p)
    if not paths:
        return []
    return [make_candidate(rule, ctx, "%d iOS simulators from uninstalled versions" % len(paths), paths,
                           command=["xcrun", "simctl", "delete", "unavailable"])]


def handler_tm_snapshots(rule, ctx):
    code, out, _ = C.run(["tmutil", "listlocalsnapshots", "/"], timeout=30)
    snaps = [l for l in out.splitlines() if "com.apple.TimeMachine" in l] if code == 0 else []
    if code == 0:
        ctx.present.add(rule["id"])
    if not snaps:
        return []
    measured = {"bytes": 0, "shared_bytes": 0, "files": len(snaps), "newest": 0, "errors": 0}
    return [make_candidate(rule, ctx, "%d local Time Machine snapshots" % len(snaps), [], measured,
                           always_show=True)]


HANDLERS = {
    "docker": handler_docker,
    "brew": handler_brew,
    "simctl_unavailable": handler_simctl_unavailable,
    "tm_snapshots": handler_tm_snapshots,
}


def kind_command(rule, ctx):
    return HANDLERS[rule["handler"]](rule, ctx)


KINDS = {
    "paths": kind_paths,
    "children": kind_children,
    "versions": kind_versions,
    "extension_dups": kind_extension_dups,
    "git_worktrees": kind_git_worktrees,
    "stale_build_dirs": kind_stale_build_dirs,
    "command": kind_command,
}


# ---------------------------------------------------------------------------
# Report assembly
# ---------------------------------------------------------------------------

def load_rules(osname, cfg, only=None):
    rules = []
    for fname in ("common.json", "%s.json" % osname):
        path = C.RULES_DIR / fname
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as fh:
            for rule in json.load(fh)["rules"]:
                if osname not in rule.get("os", [osname]):
                    continue
                override = cfg.get("rules", {}).get(rule["id"], {})
                if override.get("enabled") is False:
                    continue
                for key in ("min_age_days", "min_age_hours", "keep_latest"):
                    if key in override:
                        rule[key] = override[key]
                if RISK_ORDER.get(override.get("risk"), -1) > RISK_ORDER[rule.get("risk", "yellow")]:
                    rule["risk"] = override["risk"]  # only goes up, never down
                if only and rule["id"] not in only:
                    continue
                rules.append(rule)
    if osname != "macos" and not (C.RULES_DIR / ("%s.json" % osname)).exists():
        print("Warning: no OS-specific rules for %s yet; using only the common ones." % osname, file=sys.stderr)
    return rules


def finalize(cands, ctx):
    # 1. Fixed protection, exclusions and allowed roots.
    kept = []
    for c in cands:
        gv = c.get("git_verified", False)
        reason = next((C.safety_problem(p, ctx.os, ctx.cfg, gv) for p in c["paths"]
                       if C.safety_problem(p, ctx.os, ctx.cfg, gv)), None)
        if reason:
            ctx.warnings.append("Skipped for safety (%s): %s" % (reason, c["title"]))
            continue
        kept.append(c)
    # 2. Generic rules give way to specific ones covering the same path.
    specific = [p for c in kept if not c["generic"] for p in c["paths"]]
    kept = [c for c in kept if not c["generic"] or not any(
        C.is_within(p, s) or C.is_within(s, p) for p in c["paths"] for s in specific)]
    # 3. Small items leave the report (but still count in the footer).
    min_bytes = ctx.cfg["min_size_mb"] * 1024 * 1024
    small = [c for c in kept if c["bytes"] < min_bytes and not c["always_show"]]
    kept = [c for c in kept if c not in small]
    # 4. Sort and number.
    kept.sort(key=lambda c: (RISK_ORDER[c["risk"]], -c["bytes"]))
    for i, c in enumerate(kept, 1):
        c["n"] = i
    # 5. Nested items (e.g. node_modules inside a listed worktree) do not add to the total.
    for c in kept:
        c["nested_in"] = None
        for other in kept:
            if other is c or not other["paths"] or not c["paths"]:
                continue
            if all(any(C.is_within(p, o) and p != o for o in other["paths"]) for p in c["paths"]):
                c["nested_in"] = other["n"]
                break
    return kept, small


def totals(cands):
    out = {r: 0 for r in RISK_ORDER}
    for c in cands:
        if c["nested_in"] is None:
            out[c["risk"]] += c["bytes"]
    return out


def coverage(rules, ctx):
    tools = {}
    for rule in rules:
        tool = rule.get("tool", rule["id"])
        tools[tool] = tools.get(tool, False) or rule["id"] in ctx.present
    by_source = {}
    for repo, srcs in ctx.repo_sources.items():
        for src in srcs:
            by_source[src] = by_source.get(src, 0) + 1
    return {
        "tools_found": sorted(t for t, ok in tools.items() if ok),
        "tools_not_found": sorted(t for t, ok in tools.items() if not ok),
        "repos": [{"path": r, "sources": s} for r, s in sorted(ctx.repo_sources.items())],
        "repos_by_source": by_source,
        "custom_paths": {rid: src for rid, src in ctx.path_sources.items() if src != "default path"},
        "not_scanned": "Documents, Desktop, Downloads and media folders are not searched for "
                       "repositories (so macOS privacy prompts are not triggered); projects there "
                       "come in if Claude Code, Cursor or VS Code already opened them, or via project_roots.",
    }


def print_report(scan):
    cands = scan["candidates"]
    print("Disk: %s free of %s" % (C.human(scan["disk"]["free"]), C.human(scan["disk"]["total"])))
    for risk in ("green", "yellow", "red"):
        group = [c for c in cands if c["risk"] == risk]
        if not group:
            continue
        print("\n%s: %s" % (RISK_LABEL[risk], C.human(scan["totals"][risk])))
        for c in group:
            flags = []
            if c["blocked_by"]:
                flags.append("🔒 close: " + ", ".join(c["blocked_by"]))
            if c["recently_used"] and not c["blocked_by"]:
                flags.append("touched in the last %dh" % scan["config"]["active_guard_hours"])
            if c["nested_in"]:
                flags.append("inside #%d" % c["nested_in"])
            if c["partial"]:
                flags.append("partial read")
            if c["shared_bytes"]:
                flags.append("+%s shared (hardlinks)" % C.human(c["shared_bytes"]))
            if not c["verified"]:
                flags.append("unverified rule")
            age = " · %sd" % int(c["age_days"]) if c.get("age_days") is not None else ""
            print("  %3d. %10s  %s · %s%s%s" % (c["n"], C.human(c["bytes"]), c["tool"], c["title"], age,
                                                ("  [" + "; ".join(flags) + "]") if flags else ""))
    if scan["omitted_small"]["count"]:
        print("\n%d items below %d MB omitted (%s in total)." % (
            scan["omitted_small"]["count"], scan["config"]["min_size_mb"], C.human(scan["omitted_small"]["bytes"])))
    cov = scan["coverage"]
    print("\nCoverage:")
    print("  Tools found: " + (", ".join(cov["tools_found"]) or "none"))
    if cov["tools_not_found"]:
        print("  Not found (nothing to clean from them): " + ", ".join(cov["tools_not_found"]))
    srcs = ", ".join("%s (%d)" % kv for kv in sorted(cov["repos_by_source"].items()))
    print("  Repositories analyzed: %d — sources: %s" % (len(cov["repos"]), srcs or "none"))
    for rid, src in sorted(cov["custom_paths"].items()):
        print("  Path reported by the tool (%s): %s" % (rid, src))
    print("  " + cov["not_scanned"])
    for w in scan["warnings"]:
        print("Warning: " + w)
    print("\nPlan saved to: " + scan["scan_file"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", help="where to write the scan JSON")
    ap.add_argument("--rule", action="append", help="run only this rule (may repeat)")
    ap.add_argument("--quiet", action="store_true", help="do not print the report, only the JSON path")
    args = ap.parse_args()

    osname = C.current_os()
    cfg = C.load_config()
    ctx = Ctx(cfg, osname)
    started = time.time()
    cands = []
    rules = load_rules(osname, cfg, args.rule)
    for rule in rules:
        try:
            cands += KINDS[rule["kind"]](rule, ctx)
        except Exception as exc:  # one broken rule must not take the scan down
            ctx.warnings.append("Rule %s failed: %s" % (rule["id"], exc))
    cands, small = finalize(cands, ctx)
    find_repos(ctx)  # keeps the repository list in the coverage even with --rule
    usage = __import__("shutil").disk_usage(C.home())
    out = args.out or os.path.join(C.state_dir(), "scans", time.strftime("%Y%m%d-%H%M%S") + ".json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    scan = {
        "version": 1,
        "created_at": ctx.now,
        "created_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(ctx.now)),
        "duration_s": round(time.time() - started, 1),
        "os": osname,
        "host": socket.gethostname(),
        "home": C.home(),
        "disk": {"free": usage.free, "total": usage.total},
        "config": {k: cfg[k] for k in ("min_size_mb", "stale_project_days", "active_guard_hours",
                                       "scan_max_age_hours", "project_roots")},
        "running_processes_checked": sorted({n for c in cands for n in c["requires_closed"]}),
        "totals": totals(cands),
        "omitted_small": {"count": len(small), "bytes": sum(c["bytes"] for c in small)},
        "warnings": ctx.warnings,
        "coverage": coverage(rules, ctx),
        "candidates": cands,
        "scan_file": out,
    }
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(scan, fh, ensure_ascii=False, indent=2)
    if args.quiet:
        print(out)
    else:
        print_report(scan)


if __name__ == "__main__":
    main()
