"""Publication gate for the brand-engine skill.

The gate is the release contract: the evals exist and describe the three
canonical jobs, the README row mirrors what ``SKILL.md`` promises (including
when not to use it), the repository authoring checklist holds, and a fresh run
of the generator for every format still passes ``check_page.py`` with zero
ERROR.

Run with pytest (``python3 -m pytest skills/brand-engine/tests/test_publish_gate.py``)
or directly with Python when pytest is unavailable
(``python3 skills/brand-engine/tests/test_publish_gate.py``).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
EVALS = ROOT / "evals" / "evals.json"
README = ROOT.parents[1] / "README.md"
SCRIPTS = ROOT / "scripts"
SAMPLE_BRAND = Path(__file__).resolve().parent / "fixtures" / "forno-e-brasa.brand.json"
FORMATS = ("manual", "onepage", "deck", "report", "social", "blank")
TOPICS = ("vague pizzeria", "b2b consultancy", "internal report")

sys.path.insert(0, str(SCRIPTS))

try:  # RED phase: these modules may not exist yet.
    import check_page as cp
    import new_page as npg
except ImportError as exc:  # pragma: no cover - only on the first red run
    cp = None  # type: ignore[assignment]
    npg = None  # type: ignore[assignment]
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


def skill_text() -> str:
    assert SKILL.is_file(), "SKILL.md not found"
    return SKILL.read_text(encoding="utf-8")


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


def load_evals() -> dict:
    assert EVALS.is_file(), "evals.json not found"
    data = json.loads(EVALS.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "evals.json must be an object"
    return data


def evals_has_3_prompts(topics: tuple[str, ...] | list[str] = TOPICS) -> dict:
    """Assert the three canonical eval scenarios and their contract."""

    data = load_evals()
    assert data.get("skill_name") == "brand-engine", "evals.json skill_name must be brand-engine"
    evals = data.get("evals")
    assert isinstance(evals, list) and len(evals) == 3, "evals.json must define exactly 3 evals"

    haystack = " ".join(
        str(item.get("prompt", "")) + " " + " ".join(item.get("tags", []))
        for item in evals
    ).lower()
    for topic in topics:
        assert topic in haystack, f"evals.json is missing the {topic!r} prompt"

    for item in evals:
        assert item.get("prompt"), "each eval needs a prompt"
        expected = item.get("expected_output", "")
        assert expected, "each eval needs an expected_output"
        files = item.get("files")
        assert isinstance(files, list) and files, "each eval needs an expected files list"
        assert "[placeholder]" in expected, (
            "each eval must state the [placeholder] rule for unresolved facts"
        )
        assert "manual" in expected.lower(), (
            "each eval must expect the mandatory manual gate before templates"
        )
        assert "currentColor" in expected, (
            "each eval must keep the logo one-color rule for the symbol"
        )
        assert "bg-primary" in expected and "text-on-primary" in expected, (
            "each eval must keep the monogram tile rule (bg-primary + text-on-primary)"
        )
        assert "zero ERROR" in expected or "0 ERROR" in expected, (
            "each eval must require a clean check_page run"
        )

    # The brief fixes the template set per scenario: pizzeria -> landing+social,
    # consultancy -> landing+deck+report, internal report -> report only.
    template_formats = {"manual.html", "onepage.html", "deck.html", "report.html", "social.html"}
    expected_sets = {
        "vague pizzeria": {"manual.html", "onepage.html", "social.html"},
        "b2b consultancy": {"manual.html", "onepage.html", "deck.html", "report.html"},
        "internal report": {"manual.html", "report.html"},
    }
    for topic in topics:
        item = next(
            (
                candidate
                for candidate in evals
                if topic
                in (
                    str(candidate.get("prompt", "")) + " " + " ".join(candidate.get("tags", []))
                ).lower()
            ),
            None,
        )
        assert item is not None, f"evals.json is missing the {topic!r} prompt"
        files = set(item["files"])
        required = expected_sets[topic]
        assert required <= files, f"{topic} must expect {sorted(required - files)}"
        assert not (template_formats - required) & files, (
            f"{topic} must not expect {sorted((template_formats - required) & files)}"
        )
    return data


def readme_row() -> str:
    assert README.is_file(), "README.md not found"
    for line in README.read_text(encoding="utf-8").splitlines():
        if line.startswith("| [brand-engine]("):
            return line
    raise AssertionError("README.md is missing the brand-engine row")


def readme_row_matches_skill_outputs() -> str:
    row = readme_row()
    skill = skill_text()

    # The row must mirror the shipped formats and the trigger vocabulary.
    for term in ("brand", "manual", "landing", "deck", "report", "social"):
        assert term in row.lower(), f"README row must mention {term}"
    for term in ("vague", "logo", "reference screenshots"):
        assert term in row.lower(), f"README row must mirror the {term} trigger"
    assert "iterative" in row.lower(), (
        "README must state the iterative behavior of the multi-step skill"
    )

    # When not to use must match the SKILL.md boundaries.
    assert "Not for" in row, "README row must state when not to use the skill"
    for term in (".pptx", "PDF", "React", "e-commerce"):
        assert term in row, f"README row must repeat the {term} boundary"
        assert term in skill, f"README row claims {term} but SKILL.md does not"

    # Every format the row advertises is a real generated format.
    for fmt in ("manual", "onepage", "deck", "report", "social"):
        assert fmt in skill, f"README advertises {fmt} but SKILL.md does not output it"
    return row


def skill_authoring_checklist_passes() -> None:
    skill = skill_text()
    meta = frontmatter(skill)

    assert meta.get("name") == "brand-engine", "frontmatter name must be brand-engine"
    assert meta.get("description", "").startswith("Use when"), (
        "description must start with 'Use when'"
    )
    assert len(skill.splitlines()) < 500, "SKILL.md must stay under 500 lines"

    for section in ("Overview", "Execution Flow", "Output Contract", "Validation", "Boundaries"):
        assert re.search(rf"(?mi)^##\s+.*\b{re.escape(section)}\b", skill), (
            f"missing section: {section}"
        )
    assert "<HARD-GATE>" in skill and "</HARD-GATE>" in skill, "missing <HARD-GATE>"

    # Mandatory reliability rules from docs/skill-authoring-standard.md.
    assert "CRITICAL LANGUAGE RULE" in skill, "missing the language-matching rule"
    assert "No fabrication" in skill and "[placeholder]" in skill, (
        "missing the no-fabrication / [placeholder] rule"
    )
    assert re.search(r"ask(?:s|ed)? once", skill, re.IGNORECASE), (
        "missing the clarification-first fallback"
    )
    assert re.search(r"stop and wait|If the user does not answer, stop", skill), (
        "missing an explicit stop condition"
    )
    assert "explicit `ok`" in skill and "Do not generate any template" in skill, (
        "missing the manual approval loop"
    )
    assert "Do not use this skill for" in skill, "missing the Boundaries list"


def fresh_generator_output_has_no_errors() -> list[str]:
    """Re-run the generator for every format and require zero ERROR."""

    assert npg is not None and cp is not None, f"generator/checker not importable ({IMPORT_ERROR})"
    evidence: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        paths: list[Path] = []
        for fmt in FORMATS:
            path = npg.new_page(fmt, SAMPLE_BRAND, "Forno & Brasa", Path(tmp) / f"{fmt}.html")
            assert isinstance(path, Path) and path.is_file(), f"new_page did not write {fmt}"
            errors = [item for item in cp.check_page(path) if item.startswith("ERROR")]
            assert not errors, f"{fmt} has check_page ERRORs: {errors}"
            paths.append(path)
            evidence.append(f"{fmt}: 0 ERROR")

        cli = subprocess.run(
            [sys.executable, str(SCRIPTS / "check_page.py"), *map(str, paths)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert cli.returncode == 0, (
            "check_page CLI must exit 0 on fresh output:\n"
            + cli.stdout
            + cli.stderr
        )
        assert "Traceback" not in cli.stderr
    return evidence


def test_evals_has_three_prompts() -> None:
    data = evals_has_3_prompts()
    assert len(data["evals"]) == 3


def test_readme_row_matches_skill_outputs() -> None:
    readme_row_matches_skill_outputs()


def test_skill_authoring_checklist_passes() -> None:
    skill_authoring_checklist_passes()


def test_fresh_generator_output_has_zero_errors() -> None:
    evidence = fresh_generator_output_has_no_errors()
    assert len(evidence) == len(FORMATS)


def test_publish_gate() -> None:
    """The release gate: evals, README and authoring bar in one place."""

    evals_has_3_prompts(list(TOPICS))
    readme_row_matches_skill_outputs()
    skill_authoring_checklist_passes()
    fresh_generator_output_has_no_errors()


if __name__ == "__main__":
    failures = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
            except Exception as exc:  # noqa: BLE001 - stdlib runner reports every failure
                failures += 1
                print(f"FAIL {name}: {type(exc).__name__}: {exc}")
            else:
                print(f"PASS {name}")
    raise SystemExit(1 if failures else 0)
