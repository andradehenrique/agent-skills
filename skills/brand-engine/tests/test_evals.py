"""Tests for the brand-engine v2 eval catalog.

Run with the stdlib runner (pytest is unavailable in this repo)::

    python3 skills/brand-engine/tests/test_evals.py

``evals.json`` is a prompt + ``expected_output`` + rubric contract. The six
scenarios cover varied brands (pizzeria, B2B consultancy, brutalist record
label, luxury perfume, kids science museum and an internal dashboard). Every
expected output must check the recommended route, the mandatory manual gate,
no fabrication (``[placeholder]``), a clean ``check_page`` run and a real
visual difference across composition, type, shape and color — not just a
palette or font swap.

The catalog is v2-only: no v1 fields, no product flavor, no Gupy tokens.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals" / "evals.json"

# Topic -> fragments that must all appear in the prompt/tags of one scenario.
TOPICS = {
    "pizzeria": ("pizzeria",),
    "b2b consultancy": ("b2b", "consultancy"),
    "brutalist record label": ("brutalist", "record label"),
    "luxury perfume": ("luxury", "perfume"),
    "kids science museum": ("kids", "science", "museum"),
    "internal dashboard": ("internal", "dashboard"),
}

# v2 is the final contract: these must never become an expectation.
RETIRED = (
    "v1",
    "gupy",
    "gc-",
    "--flavor",
    "data-flavor",
    "product flavor",
    "allowed_pairs",
    "colors.secondary",
    "color.secondary",
)

# Formats shipped by new_page.py; an eval may also list brand assets.
FORMAT_FILES = {
    "manual.html",
    "brand-kit.html",
    "onepage.html",
    "report.html",
    "deck.html",
    "social.html",
    "app.html",
    "blank.html",
}
BRAND_FILES = {"brand.json", "theme.css", "tailwind-theme.css", "logo.svg"}


def load_evals() -> dict:
    assert EVALS.is_file(), "evals.json not found"
    data = json.loads(EVALS.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "evals.json must be an object"
    return data


def scenarios() -> list[dict]:
    data = load_evals()
    evals = data.get("evals")
    assert isinstance(evals, list), "evals.json must have an evals list"
    return evals


def haystack(item: dict) -> str:
    return " ".join(
        (
            str(item.get("prompt", "")),
            str(item.get("expected_output", "")),
            " ".join(str(tag) for tag in item.get("tags", [])),
        )
    ).lower()


def test_evals_json_has_six_scenarios() -> None:
    data = load_evals()
    assert data.get("skill_name") == "brand-engine", "skill_name must be brand-engine"
    evals = data.get("evals")
    assert isinstance(evals, list) and len(evals) == 6, "evals.json must define 6 evals"

    ids = [item.get("id") for item in evals]
    assert all(isinstance(item_id, int) for item_id in ids), "eval ids must be integers"
    assert len(ids) == len(set(ids)), f"eval ids must be unique, got {ids}"

    for item in evals:
        tags = item.get("tags")
        assert isinstance(tags, list) and tags, f"eval {item.get('id')} needs tags"
        assert all(isinstance(tag, str) and tag.strip() for tag in tags), (
            f"eval {item.get('id')} has an empty tag"
        )
        prompt = item.get("prompt")
        assert isinstance(prompt, str) and len(prompt.strip()) > 40, (
            f"eval {item.get('id')} needs a realistic prompt"
        )
        expected = item.get("expected_output")
        assert isinstance(expected, str) and len(expected.strip()) > 200, (
            f"eval {item.get('id')} needs a detailed expected_output"
        )
        files = item.get("files")
        assert isinstance(files, list) and files, f"eval {item.get('id')} needs files"
        assert all(isinstance(name, str) and name for name in files), (
            f"eval {item.get('id')} has an empty file name"
        )
        unknown = set(files) - FORMAT_FILES - BRAND_FILES
        assert not unknown, f"eval {item.get('id')} lists unknown files: {sorted(unknown)}"
        assert "manual.html" in files, f"eval {item.get('id')} must deliver the manual"


def test_evals_cover_varied_brands() -> None:
    evals = scenarios()
    matched: dict[str, int] = {}
    for label, needles in TOPICS.items():
        found = [
            index
            for index, item in enumerate(evals)
            if all(needle in haystack(item) for needle in needles)
        ]
        assert found, f"no eval covers the {label!r} brand"
        matched[label] = found[0]
    assert len(set(matched.values())) == len(TOPICS), (
        f"topics must map to distinct scenarios, got {matched}"
    )


def test_evals_require_gate_and_variety() -> None:
    for item in scenarios():
        expected = str(item.get("expected_output", ""))
        lowered = expected.lower()
        label = item.get("id")

        assert "route" in lowered, f"eval {label} must recommend named routes"
        assert "manual" in lowered, f"eval {label} must require the manual"
        assert "gate 2" in lowered and "explicit" in lowered and "ok" in lowered, (
            f"eval {label} must stop at the manual gate for an explicit ok"
        )
        assert "[placeholder]" in expected, (
            f"eval {label} must forbid fabrication with [placeholder]"
        )
        assert "zero error" in lowered or "0 error" in lowered, (
            f"eval {label} must require zero ERROR from check_page"
        )
        assert "brand-kit" in lowered, (
            f"eval {label} must state the brand-kit default or opt-out"
        )

        # Visual difference must include composition, type, shape and color.
        for aspect in ("composition", "type", "shape", "color"):
            assert aspect in lowered, (
                f"eval {label} must require a visual difference in {aspect}"
            )
        assert "visual difference" in lowered, (
            f"eval {label} must name the visual-difference requirement"
        )


def test_evals_forbid_v1_and_product_flavor() -> None:
    for item in scenarios():
        text = haystack(item)
        for retired in RETIRED:
            assert retired not in text, (
                f"eval {item.get('id')} still expects retired term {retired!r}"
            )
        files = " ".join(str(name) for name in item.get("files", []))
        assert "--flavor" not in files and "flavor" not in files.lower(), (
            f"eval {item.get('id')} lists a flavor artifact"
        )


def test_evals_match_context_formats_and_integrations() -> None:
    evals = scenarios()
    by_label: dict[str, dict] = {}
    for label, needles in TOPICS.items():
        by_label[label] = next(
            item
            for item in evals
            if all(needle in haystack(item) for needle in needles)
        )

    # Formats follow the job the user described, not one template for all.
    assert {"onepage.html", "social.html"} <= set(by_label["pizzeria"]["files"])
    assert {"onepage.html", "deck.html", "report.html"} <= set(
        by_label["b2b consultancy"]["files"]
    )
    assert {"blank.html", "social.html"} <= set(by_label["brutalist record label"]["files"])
    assert {"onepage.html", "deck.html"} <= set(by_label["luxury perfume"]["files"])
    assert {"onepage.html", "social.html"} <= set(by_label["kids science museum"]["files"])
    assert "app.html" in by_label["internal dashboard"]["files"]
    assert "onepage.html" not in by_label["internal dashboard"]["files"]

    # Integrations appear where the context calls for them, and stay out when
    # it does not. CDN URLs are documented, never fetched by the test.
    corpus = " ".join(haystack(item) for item in evals)
    for integration in ("iconify", "chart.js", "placehold.co"):
        assert integration in corpus, f"evals never mention {integration}"

    assert "chart.js" in haystack(by_label["b2b consultancy"])
    assert "chart.js" in haystack(by_label["internal dashboard"])
    assert "no chart.js" in haystack(by_label["brutalist record label"])
    assert "placehold.co" in haystack(by_label["pizzeria"])
    assert "placehold.co" in haystack(by_label["luxury perfume"])
    assert re.search(r"\biconify\b", haystack(by_label["kids science museum"])), (
        "the kids museum eval must use the icon family integration"
    )


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
