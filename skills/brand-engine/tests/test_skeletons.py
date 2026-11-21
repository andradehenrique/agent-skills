"""Contract tests for the brand-engine v2 skeletons and base shell.

These tests pin the v2 expectations Task 7 relies on: semantic tokens only
(no palette utilities or bare hex), Iconify/Chart.js/placehold examples where
the format needs them, the manual's new sections, the conditional gradient
slot, and the shared shell rules.

Run with pytest (``python3 -m pytest
skills/brand-engine/tests/test_skeletons.py``) or directly with Python when
pytest is unavailable
(``python3 skills/brand-engine/tests/test_skeletons.py``).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SKELETONS = ASSETS / "skeletons"

HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")


def read(name: str) -> str:
    path = SKELETONS / name
    assert path.is_file(), f"missing skeleton: {path}"
    return path.read_text(encoding="utf-8")


def test_onepage_uses_v2_tokens_and_icons() -> None:
    page = read("onepage.html")
    for needle in ("bg-surface", "text-fg-muted", "iconify-icon"):
        assert needle in page, f"onepage.html is missing {needle!r}"
    # The toggle is rendered from the shared placeholder; accept either form.
    assert "{{THEME_TOGGLE}}" in page or "data-theme-toggle" in page, (
        "onepage.html is missing the theme toggle"
    )
    assert "bg-blue-" not in page, "onepage.html still uses a palette utility"
    hexes = HEX_RE.findall(page)
    assert not hexes, f"onepage.html hardcodes hex colours: {hexes}"


def test_report_has_chart_and_feedback() -> None:
    page = read("report.html")
    assert re.search(r"<canvas[^>]*\bid=\"[^\"]+\"", page), "report.html needs a canvas with an id"
    assert "BrandCharts" in page, "report.html needs a BrandCharts example"
    assert (
        ("bg-success-soft" in page and "text-success" in page)
        or "bg-info-soft" in page
    ), "report.html needs a feedback state using v2 feedback tokens"


def test_deck_uses_7xl_or_8xl() -> None:
    page = read("deck.html")
    assert "@5xl:text-7xl" in page or "@5xl:text-8xl" in page, (
        "deck.html needs a hero-size step (@5xl:text-7xl or @5xl:text-8xl)"
    )


def test_social_uses_placehold() -> None:
    page = read("social.html")
    assert "placehold.co" in page, "social.html needs a placehold.co image placeholder"


def test_manual_has_new_sections() -> None:
    page = read("manual.html")
    headings = re.findall(r"<h[23][^>]*>(.*?)</h[23]>", page, flags=re.S)
    plain = [re.sub(r"<[^>]+>", "", heading).strip().lower() for heading in headings]
    for word in (
        "feedback",
        "gráficos",
        "ícones",
        "imagem",
        "componentes",
        "composição",
        "aplicações",
    ):
        assert any(word in heading for heading in plain), (
            f"manual.html has no heading for {word!r}"
        )
    for placeholder in (
        "{{FEEDBACK_CARDS}}",
        "{{CHART_SWATCHES}}",
        "{{ICON_SAMPLES}}",
        "{{IMAGE_SAMPLE}}",
        "{{COMPONENT_SAMPLES}}",
        "{{COMPOSITION_RULES}}",
        "{{APPLICATION_CARDS}}",
        "{{ICONIFY_SCRIPT}}",
        "{{CHART_SCRIPT}}",
    ):
        assert placeholder in page, f"manual.html is missing {placeholder}"


def test_manual_has_gradient_placeholder() -> None:
    page = read("manual.html")
    assert "{{GRADIENT_SECTION}}" in page, "manual.html needs the {{GRADIENT_SECTION}} slot"
    without_slot = page.replace("{{GRADIENT_SECTION}}", "")
    assert "bg-grad-brand" not in without_slot, (
        "manual.html hardcodes bg-grad-brand outside {{GRADIENT_SECTION}}"
    )


def test_theme_template_has_band_link_rule() -> None:
    css = (ASSETS / "theme-template.css").read_text(encoding="utf-8")
    assert "--b-band-accent" in css, "theme.css must style links on band surfaces"
    assert re.search(r"\.bg-band\s+a\b", css), "band link rule is missing"


def test_every_skeleton_has_logo_breathing_comment() -> None:
    pages = sorted(SKELETONS.glob("*.html"))
    assert pages, "no skeletons found"
    for path in pages:
        text = path.read_text(encoding="utf-8")
        assert "área de respiro = S" in text, (
            f"{path.name} is missing the logo breathing-area comment"
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
