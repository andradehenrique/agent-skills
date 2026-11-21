"""Contract tests for the brand-engine SKILL.md.

Run with pytest (``python3 -m pytest ...``) or directly with Python when
pytest is unavailable (``python3 skills/brand-engine/tests/test_skill_contract.py``).
"""

from __future__ import annotations

import re
from pathlib import Path

SKILL_PATH = Path(__file__).resolve().parents[1] / "SKILL.md"


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


def has_sections(text: str, names: list[str]) -> None:
    for name in names:
        if name == "HARD-GATE":
            assert "<HARD-GATE>" in text, "missing <HARD-GATE> block"
            assert "</HARD-GATE>" in text, "missing </HARD-GATE> block"
        else:
            pattern = rf"(?mi)^##\s+.*\b{re.escape(name)}\b"
            assert re.search(pattern, text), f"missing section: {name}"


def test_skill_has_frontmatter_with_name_and_use_when() -> None:
    meta = frontmatter(read_skill())
    assert meta.get("name") == "brand-engine", "frontmatter name must be brand-engine"
    description = meta.get("description", "")
    assert description.startswith("Use when"), "description must start with 'Use when'"
    lowered = description.lower()
    for term in ("brand", "manual", "landing", "deck", "report", "social"):
        assert term in lowered, f"description must mention {term}"


def test_skill_body_under_500_lines() -> None:
    text = read_skill()
    assert len(text.splitlines()) < 500, "SKILL.md must stay under 500 lines"


def test_skill_has_sections() -> None:
    has_sections(
        read_skill(),
        [
            "Overview",
            "HARD-GATE",
            "Execution Flow",
            "Output Contract",
            "Validation",
            "Boundaries",
        ],
    )


def test_skill_states_brand_discovery_order_and_no_overwrite_without_force() -> None:
    text = read_skill()
    order = ["--brand", "./brand.json", "./brand/brand.json"]
    positions: list[int] = []
    for token in order:
        index = text.find(token)
        assert index != -1, f"SKILL.md must mention {token}"
        positions.append(index)
    assert positions == sorted(positions), (
        "brand discovery order must be --brand > ./brand.json > ./brand/brand.json"
    )
    tail = text[positions[-1] + len(order[-1]) :]
    assert re.search(r"\bask\b", tail, re.IGNORECASE), (
        "SKILL.md must state that missing brand data falls back to asking"
    )

    plain = text.replace("`", "").lower()
    assert "without --force" in plain, (
        "SKILL.md must state that files are never overwritten without --force"
    )


def test_skill_states_manual_gate_is_prompt_only() -> None:
    text = read_skill()
    gate = re.search(r"Gate 2.*?(?=\n### Phase 4)", text, re.DOTALL)
    assert gate, "SKILL.md must define Gate 2 before Phase 4 (templates)"
    gate_text = gate.group(0).lower()
    assert "prompt-only" in gate_text, "Gate 2 must be described as prompt-only"
    assert "no script" in gate_text, "Gate 2 must state that no script enforces it"
    assert "explicit" in gate_text and "ok" in gate_text, (
        "Gate 2 must require an explicit ok from the user"
    )
    assert "template" in gate_text, (
        "Gate 2 must state that templates wait for approval"
    )


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
