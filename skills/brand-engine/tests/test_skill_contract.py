"""Contract tests for the brand-engine v2 SKILL.md and README row.

The skill is the agent-facing contract: frontmatter, the eight formats, the
online dependencies, the two gates, the propose-first UX and the output
contract. Run with the stdlib runner:

    python3 skills/brand-engine/tests/test_skill_contract.py
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = ROOT / "SKILL.md"
README_PATH = ROOT.parents[1] / "README.md"

FORMATS = (
    "manual",
    "brand-kit",
    "onepage",
    "report",
    "deck",
    "social",
    "app",
    "blank",
)
REFERENCES = (
    "discovery",
    "tokens",
    "formats",
    "voice",
    "logo",
    "components",
    "design-principles",
    "sections",
    "integrations",
)


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

    assert meta.get("name") == "brand-engine", "frontmatter name must be brand-engine"

    description = meta.get("description", "")
    assert description.startswith("Use when"), "description must start with 'Use when'"
    lowered = description.lower()
    for term in ("brand", "manual", "landing", "deck", "report", "social", "app"):
        assert term in lowered, f"description must mention {term}"

    assert re.search(r'(?m)^\s*version:\s*["\']?0\.2\.0["\']?\s*$', text), (
        "frontmatter version must be 0.2.0"
    )
    lines = len(text.splitlines())
    assert lines < 500, f"SKILL.md must stay under 500 lines (found {lines})"

    for section in ("Overview", "Execution Flow", "Output Contract", "Validation", "Boundaries"):
        assert has_section(text, section), f"missing section: {section}"
    assert "<HARD-GATE>" in text and "</HARD-GATE>" in text, "missing <HARD-GATE> block"


def test_skill_lists_v2_formats() -> None:
    text = read_skill()
    for fmt in FORMATS:
        assert fmt in text, f"SKILL.md must list the {fmt!r} format"
    assert "--format" in text, "SKILL.md must document the generator --format flag"

    # The flow must show the eight formats as a map, not only inside a table.
    for job in ("governs", "proves", "sells", "explains", "presents", "interrupts", "operates", "hosts"):
        assert job in text.lower(), f"the format map must state that a format {job}"


def test_skill_documents_dependencies() -> None:
    text = read_skill()
    lowered = text.lower()
    for fragment in (
        "Tailwind v4",
        "@tailwindcss/browser",
        "Google Fonts",
        "Iconify",
        "Chart.js",
        "placehold.co",
        "axe_copy.py",
    ):
        assert fragment in text, f"SKILL.md must document {fragment!r}"

    assert "internet" in lowered, "SKILL.md must state that the page needs internet"
    assert "offline" in lowered, "SKILL.md must state the offline caveat"
    assert re.search(r"(?i)(no|not|never|sem)\s+unsplash", text), (
        "SKILL.md must rule out Unsplash"
    )
    assert re.search(r"(?i)(no|not|never|sem)\s+undraw", text), (
        "SKILL.md must rule out unDraw"
    )


def test_skill_has_no_v1_or_product_flavor() -> None:
    text = read_skill()
    lowered = text.lower()
    for banned in ("--flavor", "data-flavor", "gc-", "gupy"):
        assert banned not in lowered, f"SKILL.md must not mention {banned!r}"
    assert not re.search(r'(?i)"version"\s*:\s*1\b', text), (
        "SKILL.md must not document the v1 version value"
    )
    assert not re.search(r"(?i)version\s*:\s*1\b", text), (
        "SKILL.md must not document the v1 version value"
    )
    assert "allowed_pairs" not in lowered, "SKILL.md must not document allowed_pairs"
    assert "colors.secondary" not in lowered, "SKILL.md must not document v1 colour keys"
    assert "colors.primary" not in lowered, "SKILL.md must not document v1 colour keys"


def test_skill_gates() -> None:
    text = read_skill()
    lowered = text.lower()

    assert "route" in lowered and "gate 1" in lowered, "SKILL.md must keep the route gate"
    assert "manual" in lowered and "gate 2" in lowered, "SKILL.md must keep the manual gate"
    assert re.search(r"(?i)(no third gate|not a third gate|only mandatory gate)", text), (
        "SKILL.md must state that the manual is the only mandatory gate"
    )
    assert "prompt-only" in lowered, "the manual gate must be prompt-only"
    assert "explicit `ok`" in text, "the manual gate must ask for an explicit `ok`"
    assert "Do not generate any template" in text, (
        "SKILL.md must stop template generation until the manual is approved"
    )
    assert re.search(r"(?i)(no script|not enforcement|you are the enforcement)", text), (
        "SKILL.md must state that no script enforces the manual gate"
    )


def test_skill_ux() -> None:
    text = read_skill()
    lowered = text.lower()

    assert "propose, don't interrogate" in lowered, (
        "SKILL.md must state the propose-don't-interrogate rule"
    )
    assert re.search(r"(?i)(one|exactly one).{0,40}recommended", text), (
        "each route set must mark exactly one route as recommended"
    )
    assert "granularity on demand" in lowered, (
        "SKILL.md must state the granularity-on-demand rule"
    )
    assert "2–3" in text or "2-3" in text, "SKILL.md must propose 2-3 routes and formats"
    assert "5–8" in text or "5-8" in text, "SKILL.md must ask 5-8 discovery questions"

    assert re.search(r"(?i)brand-kit.{0,80}(by default|default)", text), (
        "the brand-kit must be generated by default"
    )
    assert re.search(r"(?i)(skip|omit|opt out).{0,80}brand-kit|brand-kit.{0,80}(skip|single artifact)", text), (
        "the brand-kit must be skippable for single-artifact requests"
    )
    assert re.search(r"(?i)(ajusta|adjust)", text) and "brand.json" in text, (
        "SKILL.md must state that post-delivery adjustments reuse brand.json"
    )


def test_skill_output_contract() -> None:
    text = read_skill()
    for name in REFERENCES:
        assert f"references/{name}.md" in text, (
            f"SKILL.md must link references/{name}.md"
        )

    for artifact in ("brand.json", "theme.css", "tailwind-theme.css", "logo.svg"):
        assert artifact in text, f"SKILL.md must document the {artifact} artifact"
    for fmt in FORMATS:
        assert fmt in text, f"SKILL.md must document the {fmt} output"

    assert re.search(r"(?i)outside", text) and re.search(r"(?i)skill", text), (
        "SKILL.md must state that artifacts stay outside the skill directory"
    )
    assert "without --force" in text.replace("`", "").lower(), (
        "SKILL.md must state that files are never overwritten without --force"
    )
    assert "v2" in text.lower() and "version" in text.lower(), (
        "SKILL.md must state the brand.json v2 contract"
    )


def test_publish_gate() -> None:
    text = read_skill()

    plain = text.replace("`", "").lower()
    assert "without --force" in plain, "files are never overwritten without --force"
    assert "outside" in plain and "skill" in plain, (
        "brand artifacts must live outside the skill directory"
    )

    gate = re.search(r"Gate 2.*?(?=### Phase 4|## Output Contract)", text, re.DOTALL)
    assert gate, "SKILL.md must define Gate 2 before Phase 4"
    gate_text = gate.group(0).lower()
    assert "prompt-only" in gate_text, "Gate 2 must be prompt-only"
    assert "explicit" in gate_text and "ok" in gate_text, (
        "Gate 2 must require an explicit ok"
    )
    assert "no script" in gate_text or "not enforcement" in gate_text, (
        "Gate 2 must state that no script enforces it"
    )


def test_readme_row() -> None:
    assert README_PATH.is_file(), "README.md not found"
    row = ""
    for line in README_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("| [brand-engine]("):
            row = line
            break
    assert row, "README.md is missing the brand-engine row"

    lowered = row.lower()
    for term in ("flexible", "tailwind", "iconify", "chart.js", "placehold", "app", "brand-kit"):
        assert term in lowered, f"README row must mention {term}"

    # The row must not promise the retired v1 / product flavor.
    assert "v1" not in lowered, "README row must not advertise v1"
    assert "--flavor" not in lowered and "product flavor" not in lowered, (
        "README row must not advertise a product flavor"
    )
    assert "gupy" not in lowered, "README row must not mention Gupy"


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
