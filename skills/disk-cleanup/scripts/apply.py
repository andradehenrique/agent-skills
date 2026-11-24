#!/usr/bin/env python3
"""Removes the chosen items from a scan made by scan.py.

Usage:
    python3 apply.py --scan FILE.json --select "1,3,5-7"          # simulation
    python3 apply.py --scan FILE.json --select "1,3,5-7" --yes    # executes

Without --yes nothing is deleted: the script only shows what it would do. Use
--yes only after the user confirms, in the chat, exactly those numbers.

Before each item the script checks again: recent scan, same computer, allowed
risk, app closed, path still exists, not a symlink, still outside the protected
areas, not modified after the scan and (for worktrees) still clean and without
commits missing from every remote.
"""
import argparse
import json
import os
import shutil
import socket
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
from scan import worktree_state  # noqa: E402


def parse_selection(text):
    picked = []
    for part in text.replace(" ", "").split(","):
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            picked += list(range(int(a), int(b) + 1))
        else:
            picked.append(int(part))
    return sorted(set(picked))


def check_scan(scan, cfg, osname):
    age_h = (time.time() - scan["created_at"]) / 3600
    if age_h > cfg["scan_max_age_hours"]:
        return "the scan is %.1fh old (limit %sh). Run scan.py again." % (age_h, cfg["scan_max_age_hours"])
    if scan["os"] != osname or scan["host"] != socket.gethostname() or scan["home"] != C.home():
        return "the scan was made on another computer, system or user."
    return None


def check_item(c, cfg, osname, procs):
    """Returns a reason to skip the item, or None when it can proceed."""
    if c["risk"] == "red" or c["method"] == "manual":
        return "informational item: the skill does not remove it (%s)" % (c.get("note") or "high risk")
    blocked = [p for p in c.get("requires_closed", []) if p in procs]
    if blocked:
        return "close first: " + ", ".join(blocked)
    for p in c["paths"]:
        if not os.path.lexists(p):
            if c["method"] == "delete" and len(c["paths"]) == 1:
                return "already gone"
            continue
        if os.path.islink(p):
            return "became a symlink after the scan: %s" % p
        problem = C.safety_problem(p, osname, cfg, c.get("git_verified", False))
        if problem:
            return "blocked for safety (%s): %s" % (problem, p)
    # Regenerable caches of an app that must be closed change on their own while
    # the app runs, so the date would always be "newer than the scan". For them
    # the guarantee is the app being closed right now (checked above).
    owned_cache = bool(c.get("requires_closed")) and c.get("regenerates")
    if c["paths"] and c.get("newest_mtime") and not owned_cache:
        newest = max((C.newest_mtime(p) for p in c["paths"] if os.path.lexists(p)), default=0)
        if newest > c["newest_mtime"] + 1:
            return "was modified after the scan; run the scan again"
    if c.get("recheck") == "worktree":
        state = worktree_state(c["paths"][0])
        if state["dirty"] or state["unpushed"] or state["dirty"] is None or state["unpushed"] is None:
            return "the worktree changed: %s" % state
    return None


def describe(c):
    if c["method"] == "command":
        cmd = c["command"] or []
        fb = " (if the command is missing: delete %d path(s))" % len(c["paths"]) if c.get("fallback") == "delete" else ""
        return "run: " + " ".join(cmd) + fb
    verb = "move to Trash" if c["method"] == "trash" else "delete"
    if len(c["paths"]) == 1:
        return "%s %s" % (verb, c["paths"][0])
    return "%s %d paths (e.g. %s)" % (verb, len(c["paths"]), c["paths"][0])


def execute(c, osname):
    if c["method"] == "command":
        cmd = c["command"]
        if not shutil.which(cmd[0]):
            if c.get("fallback") == "delete":
                for p in c["paths"]:
                    if os.path.lexists(p):
                        C.delete_path(p)
                return "command %s missing; paths deleted directly" % cmd[0]
            raise OSError("command not found: %s" % cmd[0])
        code, out, err = C.run(cmd, timeout=1800)
        if code != 0:
            raise OSError((err or out).strip()[:300] or "exit code %d" % code)
        return (out.strip().splitlines() or [""])[-1][:200]
    done = 0
    for p in c["paths"]:
        if not os.path.lexists(p):
            continue
        if c["method"] == "trash":
            C.move_to_trash(p, osname)
        else:
            C.delete_path(p)
        done += 1
    return "%d path(s) %s" % (done, "moved to Trash" if c["method"] == "trash" else "deleted")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scan", required=True, help="JSON produced by scan.py")
    ap.add_argument("--select", required=True, help='report numbers, e.g. "1,3,5-7"')
    ap.add_argument("--yes", action="store_true", help="really executes (only after explicit confirmation)")
    args = ap.parse_args()

    osname = C.current_os()
    cfg = C.load_config()
    with open(args.scan, encoding="utf-8") as fh:
        scan = json.load(fh)
    problem = check_scan(scan, cfg, osname)
    if problem:
        print("Cannot apply: " + problem)
        sys.exit(2)

    by_n = {c["n"]: c for c in scan["candidates"]}
    selected = parse_selection(args.select)
    unknown = [n for n in selected if n not in by_n]
    if unknown:
        print("Numbers that do not exist in this scan: %s" % unknown)
        sys.exit(2)
    # Parent before child: if the whole worktree goes, its node_modules becomes "already gone".
    items = sorted((by_n[n] for n in selected), key=lambda c: (c["nested_in"] is not None, c["n"]))
    procs = C.running_processes(osname)

    mode = "EXECUTING" if args.yes else "SIMULATION (nothing will be deleted; use --yes after the confirmation)"
    print(mode)
    free_before = C.free_bytes()
    results, estimated, deferred = [], 0, []
    for c in items:
        reason = check_item(c, cfg, osname, procs)
        entry = {"n": c["n"], "id": c["id"], "title": c["title"], "bytes": c["bytes"], "method": c["method"],
                 "paths": c["paths"], "command": c.get("command")}
        if reason:
            entry.update(status="pulado", reason=reason)
            if reason.startswith("close first"):
                deferred.append(c)
            print("  #%d SKIPPED %s — %s" % (c["n"], c["title"], reason))
        elif not args.yes:
            entry.update(status="simulated")
            print("  #%d OK      %s (%s) — %s" % (c["n"], c["title"], C.human(c["bytes"]), describe(c)))
            if c["nested_in"] is None:
                estimated += c["bytes"]
        else:
            try:
                detail = execute(c, osname)
                entry.update(status="removed", detail=detail)
                if c["nested_in"] is None:
                    estimated += c["bytes"]
                print("  #%d DONE    %s (%s) — %s" % (c["n"], c["title"], C.human(c["bytes"]), detail))
            except Exception as exc:  # move on to the next item
                entry.update(status="error", reason=str(exc))
                print("  #%d ERROR   %s — %s" % (c["n"], c["title"], exc))
        results.append(entry)

    free_after = C.free_bytes()
    print("\nEstimated: %s" % C.human(estimated))
    if args.yes:
        delta = free_after - free_before
        print("Free space: %s → %s (%s%s)" % (C.human(free_before), C.human(free_after),
                                                "+" if delta >= 0 else "-", C.human(abs(delta))))
        log = os.path.join(C.state_dir(), "log.jsonl")
        os.makedirs(os.path.dirname(log), exist_ok=True)
        with open(log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "scan_file": args.scan,
                "selected": selected, "estimated_bytes": estimated,
                "free_before": free_before, "free_after": free_after, "results": results,
            }, ensure_ascii=False) + "\n")
        print("Log: " + log)
    if deferred:
        apps = sorted({p for c in deferred for p in c["requires_closed"] if p in procs})
        nums = ",".join(str(c["n"]) for c in sorted(deferred, key=lambda c: c["n"]))
        print("\nPENDING: %d item(s) depend on closing %s." % (len(deferred), ", ".join(apps)))
        print("Close the app(s) and run in the Terminal (valid until %s):" % time.strftime(
            "%d/%m %H:%M", time.localtime(scan["created_at"] + cfg["scan_max_age_hours"] * 3600)))
        print('  python3 "%s" --scan "%s" --select "%s" --yes' % (
            os.path.abspath(__file__), os.path.abspath(args.scan), nums))
    if any(r["status"] == "error" for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
