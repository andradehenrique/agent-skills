"""Shared helpers for scan.py and apply.py.

Standard library only, compatible with Python 3.9 (the python3 that ships with
the macOS Command Line Tools). Everything OS-specific stays isolated in
functions with per-OS branches, so Linux and Windows can land later without
touching the flow.
"""
import glob
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import tempfile
import time
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
RULES_DIR = SKILL_DIR / "rules"


def home():
    return os.path.realpath(os.path.expanduser("~"))


def state_dir():
    base = os.environ.get("XDG_STATE_HOME") or os.path.join(home(), ".local", "state")
    return os.path.join(base, "disk-cleanup")


def config_path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(home(), ".config")
    return os.path.join(base, "disk-cleanup", "config.json")


def current_os():
    return {"Darwin": "macos", "Linux": "linux", "Windows": "windows"}.get(
        platform.system(), platform.system().lower()
    )


# ---------------------------------------------------------------------------
# User configuration
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = {
    # Where to look for git repositories (worktrees and build artifacts).
    "project_roots": ["~/work", "~/projects", "~/dev", "~/code", "~/src", "~/Developer"],
    # Paths the skill must never list or touch, beyond the fixed protection.
    "exclude_paths": [],
    # Candidates smaller than this stay out of the report (they only add to the footer).
    "min_size_mb": 10,
    # A project with no git activity for longer than this gets its build artifacts listed.
    "stale_project_days": 30,
    # Anything modified more recently than this counts as "in use".
    "active_guard_hours": 24,
    # A scan older than this cannot be applied.
    "scan_max_age_hours": 4,
    # Per-rule overrides: {"<rule-id>": {"enabled": false, "min_age_days": 60}}.
    # For safety, a rule's risk can only go up, never down.
    "rules": {},
}


def load_config():
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    path = config_path()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            user = json.load(fh)
        for key, value in user.items():
            cfg[key] = value
    cfg["project_roots"] = [expand(p) for p in cfg["project_roots"]]
    cfg["exclude_paths"] = [expand(p) for p in cfg["exclude_paths"]]
    return cfg


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def _uid():
    return str(os.getuid()) if hasattr(os, "getuid") else ""


def _env_dir(var, default):
    value = os.environ.get(var)
    return value if value else os.path.expanduser(default)


def placeholders():
    """Directories each person may have moved through an environment variable."""
    return {
        "{uid}": _uid(),
        "{tmpdir}": tempfile.gettempdir().rstrip("/\\"),
        "{claude_dir}": _env_dir("CLAUDE_CONFIG_DIR", "~/.claude"),
        "{xdg_data}": _env_dir("XDG_DATA_HOME", "~/.local/share"),
        "{xdg_cache}": _env_dir("XDG_CACHE_HOME", "~/.cache"),
        "{xdg_config}": _env_dir("XDG_CONFIG_HOME", "~/.config"),
        "{cargo_home}": _env_dir("CARGO_HOME", "~/.cargo"),
        "{gradle_home}": _env_dir("GRADLE_USER_HOME", "~/.gradle"),
    }


def expand(pattern):
    """Expands ~, $VARS and the placeholders above. Does not resolve symlinks."""
    for key, value in placeholders().items():
        pattern = pattern.replace(key, value)
    return os.path.expandvars(os.path.expanduser(pattern))


def resolve_paths(rule, osname):
    """Paths of a rule, asking the tool itself when possible.

    `resolve` is a list of sources tried in order; the first one that returns an
    existing folder wins. If none answers, `paths` (the default) is used.
    Returns (paths, origin) so the report can say where the path came from.
      {"cmd": ["npm", "config", "get", "cache"], "suffix": "_cacache"}
      {"defaults": ["com.apple.dt.Xcode", "IDECustomDerivedDataLocation"]}
    """
    for source in pick_for_os(rule.get("resolve"), osname) or []:
        value, label = None, None
        if "cmd" in source and tool_available(source["cmd"][0]):
            code, out, _ = run(source["cmd"], timeout=15)
            lines = [l.strip() for l in out.splitlines() if l.strip()]
            if code == 0 and lines:
                value, label = lines[-1], " ".join(source["cmd"])
        elif "defaults" in source and osname == "macos":
            code, out, _ = run(["defaults", "read"] + source["defaults"], timeout=10)
            if code == 0 and out.strip():
                value, label = out.strip(), "defaults read " + " ".join(source["defaults"])
        if not value or value in ("undefined", "null"):
            continue
        path = os.path.join(os.path.expanduser(value), source.get("suffix", ""))
        path = path.rstrip("/\\") or path
        if os.path.exists(path):
            return [path], label
    return glob_paths(rule.get("paths", []), osname), "default path"


def pick_for_os(value, osname):
    """Rule fields may be a list/value or a dict {"macos": ..., "linux": ...}."""
    if isinstance(value, dict):
        return value.get(osname, value.get("default"))
    return value


def glob_paths(patterns, osname):
    out = []
    for pattern in pick_for_os(patterns, osname) or []:
        for match in sorted(glob.glob(expand(pattern))):
            if match not in out:
                out.append(match)
    return out


def is_within(child, parent):
    child = os.path.normpath(child)
    parent = os.path.normpath(parent)
    return child == parent or child.startswith(parent.rstrip(os.sep) + os.sep)


# Fixed protection: it cannot be switched off by config. The skill never enters
# these paths and never deletes anything that contains them (an ancestor).
#
# Two levels:
# - PERSONAL_HOME: folders where people keep files, but where code is also
#   common (GitHub Desktop clones into ~/Documents/GitHub). Generic rules never
#   act here; only git rules do, since git itself confirms what is a worktree
#   and what is ignored.
# - PROTECTED_HOME / PROTECTED_ABS: nothing enters, under any rule.
PERSONAL_HOME = ["Documents", "Desktop"]

PROTECTED_HOME = {
    "common": [
        "Pictures", "Movies", "Music", "Videos",
        ".ssh", ".gnupg", ".aws", ".kube", ".docker/config.json", ".netrc",
        ".config/gcloud", ".config/gh", ".config/opencode",
        ".claude/settings.json", ".claude/settings.local.json", ".claude/CLAUDE.md",
        ".claude/skills", ".claude/plugins", ".claude/agents", ".claude/commands",
        ".claude/hooks", ".claude.json", ".cursor/mcp.json",
    ],
    "macos": [
        "Library/Mobile Documents", "Library/CloudStorage", "Library/Keychains",
        "Library/Mail", "Library/Messages", "Library/Photos", "Library/Calendars",
        "Library/Contacts", "Library/Notes", "Library/Safari",
        "Library/Group Containers", "Library/Containers",
        "Library/Application Support/AddressBook",
        "Library/Application Support/MobileSync",
    ],
}

PROTECTED_ABS = {
    "macos": ["/System", "/Library", "/Applications", "/bin", "/sbin", "/usr",
              "/private/etc", "/private/var/db", "/Volumes"],
    "linux": ["/bin", "/boot", "/etc", "/lib", "/lib64", "/opt", "/root", "/sbin",
              "/snap", "/srv", "/sys", "/proc", "/usr", "/var/lib", "/mnt", "/media"],
    "windows": [],
}


def protected_paths(osname, git_verified=False):
    h = home()
    rel = PROTECTED_HOME["common"] + PROTECTED_HOME.get(osname, [])
    if not git_verified:
        rel = rel + PERSONAL_HOME
    out = [os.path.join(h, p) for p in rel] + PROTECTED_ABS.get(osname, [])
    claude_dir = placeholders()["{claude_dir}"]
    for name in ("settings.json", "settings.local.json", "CLAUDE.md", "skills", "plugins",
                 "agents", "commands", "hooks"):
        out.append(os.path.join(claude_dir, name))
    return out


def allowed_roots(osname, cfg):
    roots = [home(), os.path.realpath(tempfile.gettempdir())]
    if osname == "macos":
        roots += ["/private/tmp"]
    elif osname == "linux":
        roots += ["/tmp", "/var/tmp"]
    roots += [os.path.realpath(p) for p in cfg.get("project_roots", []) if os.path.isdir(p)]
    return roots


def safety_problem(path, osname, cfg, git_verified=False):
    """Returns a reason (str) when the path cannot be touched, or None.

    git_verified=True only for candidates git confirmed (a registered worktree
    or an ignored folder): that unlocks Documents/Desktop, nothing beyond that.
    """
    real = os.path.realpath(path)
    h = home()
    if real in ("/", h) or len(Path(real).parts) <= 2:
        return "root path or the home directory itself"
    personal = {os.path.join(h, p) for p in PERSONAL_HOME}
    for p in protected_paths(osname, git_verified):
        rp = os.path.realpath(p) if os.path.exists(p) else p
        if is_within(real, rp):
            if p in personal:
                return ("points inside %s, a personal folder: only git rules act there, "
                        "since they confirm worktree and ignored folder" % p.replace(h, "~"))
            return "inside a protected area (%s)" % p
        if is_within(rp, real):
            return "contains a protected area (%s)" % p
    for p in cfg.get("exclude_paths", []):
        rp = os.path.realpath(p) if os.path.exists(p) else p
        if is_within(real, rp) or is_within(rp, real):
            return "excluded in the config (%s)" % p
    if not any(is_within(real, r) for r in allowed_roots(osname, cfg)):
        return "outside the allowed roots"
    return None


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------

def measure(path):
    """Measures what deleting `path` would really free.

    - Does not follow symlinks and does not cross into another volume (network mounts).
    - Uses allocated blocks (st_blocks), so sparse files do not inflate the total.
    - Hardlinks: an inode only counts as freeable when all of its links are inside
      `path`. Otherwise it goes to `shared_bytes` (e.g. a pnpm node_modules
      pointing into the global store, which keeps taking space).
    - APFS clones cannot be detected cheaply: the total is an estimate.
    """
    result = {"bytes": 0, "shared_bytes": 0, "files": 0, "newest": 0.0, "errors": 0}
    try:
        root = os.lstat(path)
    except OSError:
        result["errors"] += 1
        return result
    device = root.st_dev
    links = {}

    def account(st):
        size = st.st_blocks * 512 if hasattr(st, "st_blocks") else st.st_size
        if st.st_mtime > result["newest"]:
            result["newest"] = st.st_mtime
        if not stat.S_ISDIR(st.st_mode) and st.st_nlink > 1:
            key = (st.st_dev, st.st_ino)
            seen = links.get(key)
            if seen:
                seen[0] += 1
            else:
                links[key] = [1, st.st_nlink, size]
            return
        result["bytes"] += size

    account(root)
    if stat.S_ISDIR(root.st_mode):
        stack = [path]
        while stack:
            current = stack.pop()
            try:
                with os.scandir(current) as it:
                    for entry in it:
                        try:
                            st = entry.stat(follow_symlinks=False)
                        except OSError:
                            result["errors"] += 1
                            continue
                        if st.st_dev != device:
                            continue
                        account(st)
                        if stat.S_ISDIR(st.st_mode):
                            stack.append(entry.path)
                        else:
                            result["files"] += 1
            except OSError:
                result["errors"] += 1
    else:
        result["files"] = 1

    for count, nlink, size in links.values():
        if count >= nlink:
            result["bytes"] += size
        else:
            result["shared_bytes"] += size
    return result


def newest_mtime(path):
    return measure(path)["newest"]


def human(n):
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024 or unit == "TB":
            return ("%.0f %s" if unit in ("B", "KB") else "%.1f %s") % (n, unit)
        n /= 1024.0
    return "%.1f TB" % n


_SIZE_RE = re.compile(r"([\d.]+)\s*([KMGT]?i?B|[kKmMgGtT]B?|B)", re.I)


def parse_size(text, binary=False):
    """Converts '1.2GB', '512.5kB', '0B' into bytes. Docker uses base 1000, Homebrew 1024."""
    m = _SIZE_RE.search(text or "")
    if not m:
        return 0
    value = float(m.group(1))
    unit = m.group(2).upper().replace("I", "").rstrip("B") or "B"
    base = 1024 if binary or "I" in m.group(2).upper() else 1000
    power = {"B": 0, "K": 1, "M": 2, "G": 3, "T": 4}.get(unit[0], 0)
    return int(value * (base ** power))


def free_bytes(path=None):
    return shutil.disk_usage(path or home()).free


# ---------------------------------------------------------------------------
# Processes and commands
# ---------------------------------------------------------------------------

def running_processes(osname):
    try:
        if osname == "macos":
            out = subprocess.run(["ps", "-axco", "comm="], capture_output=True, text=True, timeout=10).stdout
        elif osname == "linux":
            out = subprocess.run(["ps", "-eo", "comm="], capture_output=True, text=True, timeout=10).stdout
        elif osname == "windows":
            out = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True, timeout=10).stdout
            out = "\n".join(line.split(",")[0].strip('"').rsplit(".exe", 1)[0] for line in out.splitlines())
        else:
            return set()
    except (OSError, subprocess.SubprocessError):
        return set()
    return {line.strip() for line in out.splitlines() if line.strip()}


def run(cmd, timeout=60, cwd=None):
    """Runs a command without a shell. Returns (code, stdout, stderr)."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, "", "command not found: %s" % cmd[0]
    except subprocess.TimeoutExpired:
        return 124, "", "timed out (%ss)" % timeout


# On macOS, /usr/bin/git, pip3 and python3 are shims that open the Command Line
# Tools install window when the tools are missing. A scan must not make that
# window pop up on the person's screen.
_CLT_SHIMS = {"git", "pip3", "python3", "xcrun", "make", "clang"}
_clt_ok = None


def tool_available(name):
    global _clt_ok
    found = shutil.which(name)
    if not found:
        return False
    if current_os() == "macos" and name in _CLT_SHIMS and found.startswith("/usr/bin/"):
        if _clt_ok is None:
            _clt_ok = run(["xcode-select", "-p"], timeout=10)[0] == 0
        return _clt_ok
    return True


def version_key(name):
    parts = re.findall(r"\d+|[A-Za-z]+", name)
    return [(0, int(p)) if p.isdigit() else (1, p) for p in parts]


# ---------------------------------------------------------------------------
# Removal
# ---------------------------------------------------------------------------

def _force_writable(func, path, _exc):
    # E.g. the Go module cache is read-only.
    try:
        os.chmod(path, stat.S_IWUSR | stat.S_IRUSR | stat.S_IXUSR)
        parent = os.path.dirname(path)
        os.chmod(parent, stat.S_IWUSR | stat.S_IRUSR | stat.S_IXUSR)
        func(path)
    except OSError:
        raise


def delete_path(path):
    if os.path.islink(path) or not os.path.isdir(path):
        os.unlink(path)
    else:
        shutil.rmtree(path, onerror=_force_writable)


def move_to_trash(path, osname):
    if osname == "macos":
        trash = os.path.join(home(), ".Trash")
        target = os.path.join(trash, os.path.basename(path))
        if os.path.exists(target):
            stem, ext = os.path.splitext(os.path.basename(path))
            target = os.path.join(trash, "%s %s%s" % (stem, time.strftime("%H-%M-%S"), ext))
        try:
            os.rename(path, target)
            return
        except OSError:
            pass
        # Fallback: ask the Finder (may open an Automation permission prompt).
        escaped = path.replace("\\", "\\\\").replace('"', '\\"')
        code, _, err = run(["osascript", "-e",
                            'tell application "Finder" to delete POSIX file "%s"' % escaped], timeout=30)
        if code != 0:
            raise OSError("could not move to Trash: %s" % err.strip())
        return
    raise OSError("moving to Trash is not implemented yet on %s" % osname)
