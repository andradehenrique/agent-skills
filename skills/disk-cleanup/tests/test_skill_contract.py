"""Contract tests for the disk-cleanup skill and its README row.

The skill is the agent-facing contract: frontmatter, the two-phase flow, the
hard gates, the scripts it must never bypass, the output contract and the
references. Run with the stdlib runner:

    python3 skills/disk-cleanup/tests/test_skill_contract.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = ROOT / "SKILL.md"
README_PATH = ROOT.parents[1] / "README.md"
REFERENCES = ("config", "rule-schema", "macos", "adding-an-os")
SCRIPTS = ("scan.py", "apply.py", "common.py")
RULES = ("common.json", "macos.json")


def read_skill() -> str:
    assert SKILL_PATH.is_file(), "SKILL.md not found"
    return SKILL_PATH.read_text(encoding="utf-8")


def frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    assert match, "SKILL.md must start with YAML frontmatter"
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line or line.startswith((" ", "\t")) or ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields


def has_section(text: str, name: str) -> bool:
    return bool(re.search(rf"(?mi)^##\s+.*\b{re.escape(name)}\b", text))


def test_frontmatter_and_size() -> None:
    text = read_skill()
    meta = frontmatter(text)

    assert meta.get("name") == "disk-cleanup", "frontmatter name must be disk-cleanup"

    description = meta.get("description", "")
    assert description.startswith("Use when"), "description must start with 'Use when'"
    lowered = description.lower()
    for term in ("space", "docker", "xcode", "cache", "node_modules", "worktree", "library"):
        assert term in lowered, f"description must mention {term}"

    assert re.search(r'(?m)^\s*version:\s*["\']?\d+\.\d+\.\d+["\']?\s*$', text), (
        "frontmatter must carry a semver version"
    )
    lines = len(text.splitlines())
    assert lines < 500, f"SKILL.md must stay under 500 lines (found {lines})"

    for section in ("Overview", "Execution Flow", "Output Contract", "Validation", "Boundaries"):
        assert has_section(text, section), f"missing section: {section}"
    assert "<HARD-GATE>" in text and "</HARD-GATE>" in text, "missing <HARD-GATE> block"


def test_language_rule_and_no_deletion_bypass() -> None:
    text = read_skill()
    assert "CRITICAL LANGUAGE RULE" in text, "missing the language rule"

    plain = text.replace("`", "").lower()
    assert "never delete outside the scripts" in plain, (
        "missing the hard gate against ad-hoc deletion"
    )
    for banned in ("rm -rf", "docker system prune", "brew cleanup", "sudo"):
        assert banned in plain, f"SKILL.md must name the forbidden shortcut {banned!r}"
    assert "apply.py" in text, "SKILL.md must route every removal through apply.py"
    assert "scan.py" in text, "SKILL.md must document the scan phase"


def test_confirmation_gates() -> None:
    text = read_skill()
    lowered = text.lower()

    assert "explicit confirmation" in lowered, "missing the explicit-confirmation gate"
    assert "scan_max_age_hours" in text or "4 hours" in lowered, (
        "SKILL.md must state the staleness limit"
    )
    assert "--yes" in text, "SKILL.md must document the --yes flag"
    assert "--select" in text, "SKILL.md must document the --select flag"
    assert re.search(r"(?i)yell?ow items? (enter|only)", text), (
        "SKILL.md must state that yellow items need to be named"
    )
    assert re.search(r"(?i)red items are never removed", text), (
        "SKILL.md must state that red items are never removed"
    )
    assert "PENDING" in text, "SKILL.md must document the pending handoff for open apps"


def test_language_of_shipped_assets() -> None:
    """Scripts, rules and references ship in English, like the rest of the repo."""
    accented = re.compile(r"[ãáâàéêíóôõúçÃÁÂÀÉÊÍÓÔÕÚÇ]")
    for name in SCRIPTS:
        text = (ROOT / "scripts" / name).read_text(encoding="utf-8")
        assert not accented.search(text), f"scripts/{name} still contains Portuguese text"
    for name in RULES:
        text = (ROOT / "rules" / name).read_text(encoding="utf-8")
        assert not accented.search(text), f"rules/{name} still contains Portuguese text"
    for name in REFERENCES:
        text = (ROOT / "references" / f"{name}.md").read_text(encoding="utf-8")
        assert not accented.search(text), f"references/{name}.md still contains Portuguese text"


def test_rules_parse_and_cover_macos() -> None:
    for name in RULES:
        data = json.loads((ROOT / "rules" / name).read_text(encoding="utf-8"))
        assert isinstance(data.get("rules"), list) and data["rules"], f"{name} has no rules"
        for rule in data["rules"]:
            for field in ("id", "tool", "category", "kind"):
                assert rule.get(field), f"{name}: rule {rule.get('id')} is missing {field}"
            risks = [rule["risk"]] if "risk" in rule else []
            # stale_build_dirs carries one risk per folder name instead.
            risks += list(rule.get("names", {}).values())
            assert risks, f"{name}: rule {rule['id']} declares no risk"
            for risk in risks:
                assert risk in ("green", "yellow", "red"), (
                    f"{name}: rule {rule['id']} has an invalid risk {risk!r}"
                )

    macos = {r["id"] for r in json.loads((ROOT / "rules" / "macos.json").read_text())["rules"]}
    for expected in ("xcode-derived-data", "trash", "user-caches", "downloads-installers"):
        assert expected in macos, f"macos rules must keep {expected}"


def test_scripts_are_stdlib_and_compilable() -> None:
    import py_compile
    import tempfile

    for name in SCRIPTS:
        path = ROOT / "scripts" / name
        assert path.is_file(), f"scripts/{name} not found"
        with tempfile.TemporaryDirectory() as tmp:
            py_compile.compile(str(path), cfile=str(Path(tmp) / "out.pyc"), doraise=True)

    apply_text = (ROOT / "scripts" / "apply.py").read_text(encoding="utf-8")
    assert "--yes" in apply_text, "apply.py must require --yes to execute"


def test_evals_catalog() -> None:
    data = json.loads((ROOT / "evals" / "evals.json").read_text(encoding="utf-8"))
    assert data.get("skill_name") == "disk-cleanup", "skill_name must be disk-cleanup"
    evals = data.get("evals")
    assert isinstance(evals, list) and len(evals) >= 5, "evals.json must define 5+ evals"

    ids = [item.get("id") for item in evals]
    assert len(ids) == len(set(ids)), f"eval ids must be unique, got {ids}"

    corpus = ""
    for item in evals:
        expected = str(item.get("expected_output", ""))
        assert len(expected) > 200, f"eval {item.get('id')} needs a detailed expected_output"
        corpus += " " + expected.lower()
        corpus += " " + " ".join(str(tag) for tag in item.get("tags", [])).lower()

    for topic in ("report", "confirmation", "open app", "worktree", "coverage"):
        assert topic in corpus, f"evals must cover {topic!r}"
    assert "nothing is removed" in corpus or "nothing is deleted" in corpus, (
        "evals must assert that nothing is removed"
    )


def test_readme_row() -> None:
    assert README_PATH.is_file(), "README.md not found"
    row = ""
    for line in README_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("| [disk-cleanup]("):
            row = line
            break
    assert row, "README.md is missing the disk-cleanup row"

    lowered = row.lower()
    for term in ("numbered", "risk", "confirm", "macos"):
        assert term in lowered, f"README row must mention {term}"


if __name__ == "__main__":
    failures = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
            else:
                print(f"PASS {name}")
    raise SystemExit(1 if failures else 0)
