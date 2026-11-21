"""Tests for the v2 branded single-file page generator.

Run with the stdlib runner (pytest is unavailable in this repo)::

    python3 skills/brand-engine/tests/test_new_page.py

The generated HTML is the contract the checker consumes: a single file with
the logo sprite at the top of ``<body>``, semantic tokens only, one
``<main>``/``<h1>`` per page, and conditional CDN scripts (Iconify only where
icons are used, Chart.js only on formats with a chart).

Every format reads the v2 brand model: all visual data lives under
``design`` and the raw dict returned by ``build_theme.load_brand`` is what
``render_page`` receives.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

sys.path.insert(0, str(SCRIPTS))

try:  # RED phase: the v2 generator may not be importable yet.
    import new_page as npg
except ImportError as exc:  # pragma: no cover - only on the first red run
    npg = None  # type: ignore[assignment]
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None

EXPECTED_FORMATS = (
    "manual",
    "onepage",
    "deck",
    "report",
    "social",
    "app",
    "brand-kit",
    "blank",
)


def generator():
    assert npg is not None, f"new_page not importable ({IMPORT_ERROR})"
    return npg


def brand(fixture: str) -> dict:
    return generator().load_brand(FIXTURES / f"{fixture}.brand.json")


def render(fmt: str, theme: str | None = None, fixture: str = "forno-e-brasa") -> str:
    return generator().render_page(fmt, brand(fixture), "Forno & Brasa", theme)


def generate(fmt: str, out: str | Path, **kwargs: object) -> str:
    mod = generator()
    path = mod.new_page(fmt, FIXTURES / "forno-e-brasa.brand.json", "Forno & Brasa", out, **kwargs)
    assert isinstance(path, Path), f"new_page must return a path, got {type(path)}"
    return path.read_text(encoding="utf-8")


def headings(html: str) -> list[str]:
    found = re.findall(r"<h[123][^>]*>(.*?)</h[123]>", html, flags=re.S | re.I)
    return [re.sub(r"<[^>]+>", "", item).strip().casefold() for item in found]


# ---------------------------------------------------------------------------
# Every format
# ---------------------------------------------------------------------------


def test_render_every_format() -> None:
    mod = generator()
    assert mod.FORMATS == EXPECTED_FORMATS, mod.FORMATS
    assert tuple(mod.FORMATS) == EXPECTED_FORMATS

    for fmt in EXPECTED_FORMATS:
        html = render(fmt)
        assert html.lower().count("<main") == 1, fmt
        assert html.lower().count("<h1") == 1, fmt
        assert not re.search(r"\{\{[A-Z0-9_]+\}\}", html), fmt
        assert "<svg><symbol" in html, f"{fmt} has no logo sprite"
        assert html.index("<svg><symbol") < html.index("<main"), fmt
        assert "--b-canvas:" in html and "--b-color-" in html, f"{fmt} has no theme CSS"
        assert f'data-format="{fmt}"' in html, fmt
        assert "prefers-color-scheme" in html, fmt


def test_format_scripts_are_conditional() -> None:
    report = render("report")
    assert "chart.umd" in report, "report must load Chart.js"
    assert "BrandCharts" in report, "report must load the BrandCharts helper"

    onepage = render("onepage")
    assert "chart.umd" not in onepage, "onepage has no chart and must not load Chart.js"
    assert "BrandCharts" not in onepage

    for fmt in ("onepage", "app", "brand-kit", "manual", "report"):
        assert "iconify-icon" in render(fmt), f"{fmt} uses Iconify icons"

    blank = render("blank")
    assert "chart.umd" not in blank
    assert "cdn.jsdelivr.net/npm/iconify-icon" not in blank, (
        "blank has no icons and must not load Iconify"
    )


# ---------------------------------------------------------------------------
# placehold.co
# ---------------------------------------------------------------------------


def test_placehold_url_uses_brand_colors() -> None:
    data = brand("forno-e-brasa")
    canvas = data["design"]["colors"]["canvas"]["hex"].lstrip("#").upper()
    primary = data["design"]["colors"]["primary"]["hex"].lstrip("#").upper()

    html = render("brand-kit")
    urls = re.findall(r"https://placehold\.co/[^\s\"'<>]+", html)
    assert urls, "brand-kit needs a placehold.co image sample"
    assert any(canvas in url and primary in url for url in urls), urls
    assert not any("#" in url for url in urls), "placehold colours carry no #"


def test_placehold_theme_swap() -> None:
    html = render("brand-kit")
    assert "data-placehold-dark" in html
    assert "data-placehold-light" in html
    assert "img[data-placehold-dark]" in generator().THEME_JS, (
        "THEME_JS must swap img[data-placehold-dark] on theme change"
    )

    light_only = render("brand-kit", fixture="brutalist")
    assert "data-placehold-dark=" not in light_only


# ---------------------------------------------------------------------------
# Theme modes
# ---------------------------------------------------------------------------


def test_theme_modes() -> None:
    mod = generator()

    dark_only = render("blank", fixture="luxury")
    assert 'data-theme-default="dark"' in dark_only
    assert 'data-theme="dark"' in dark_only
    assert 'data-theme-lock="dark"' in dark_only
    # The shared bare CSS mentions [data-theme-toggle]; the button is what is gone.
    assert "data-theme-toggle aria-label" not in dark_only
    assert 'd === "dark" ? "dark" : "light"' in dark_only

    light_only = render("blank", fixture="brutalist")
    assert 'data-theme-default="light"' in light_only
    assert 'data-theme-lock="light"' in light_only
    assert "data-theme-toggle aria-label" not in light_only
    assert '[data-theme="dark"] {' not in light_only

    both = render("blank")
    assert "data-theme-toggle" in both
    assert 'data-theme-lock="' not in both
    assert '[data-theme="dark"] {' in both

    # A single-mode brand rejects a mode it does not have and `system`.
    for bad in ("light", "system", "light-only"):
        try:
            mod.render_page("blank", brand("luxury"), "X", bad)
        except ValueError as exc:
            assert "theme" in str(exc)
        else:
            raise AssertionError(f"{bad!r} must be rejected by a dark-only brand")

    # `theme=None` follows design.theme.default.
    assert 'data-theme-default="dark"' in render("blank", fixture="luxury")


def test_theme_default_dark_applies_dark() -> None:
    data = brand("forno-e-brasa")
    data = json.loads(json.dumps(data))
    data["design"]["theme"]["default"] = "dark"

    html = generator().render_page("blank", data, "Forno & Brasa", None)
    assert 'data-theme-default="dark"' in html
    assert 'data-theme="dark"' in html


# ---------------------------------------------------------------------------
# New formats and the manual's new sections
# ---------------------------------------------------------------------------


def test_brand_kit_is_supported() -> None:
    html = render("brand-kit")
    assert "<main" in html and "data-theme-toggle" in html
    for case in ("onepage", "report", "deck", "app", "social"):
        assert f'data-case="{case}"' in html, f"brand-kit is missing the {case} mini case"
    for heading in ("logo", "cores", "feedback", "gráficos", "tipografia", "ícones"):
        assert heading in headings(html), heading


def test_app_is_supported() -> None:
    html = render("app")
    assert 'data-region="topbar"' in html
    assert 'data-region="sidebar"' in html
    assert "<table" in html and "<caption" in html
    assert "<dialog" in html


def test_manual_has_feedback_and_chart_sections() -> None:
    html = render("manual")
    found = headings(html)
    for heading in ("feedback", "gráficos", "ícones", "imagem", "componentes", "composição", "aplicações"):
        assert any(heading in item for item in found), heading

    assert "bg-success-soft" in html
    assert "bg-chart-1" in html
    assert "iconify-icon" in html
    assert "placehold.co" in html


def test_gradient_section_only_when_defined() -> None:
    assert "bg-grad-brand" not in render("manual")
    gradient = render("manual", fixture="luxury")
    assert "bg-grad-brand" in gradient


def test_font_links_include_display_and_body() -> None:
    html = render("blank")
    assert html.count("family=Fraunces") == 1
    assert html.count("family=Source+Sans+3") == 1

    # A single-family brand links it once, not twice.
    data = brand("forno-e-brasa")
    data = json.loads(json.dumps(data))
    data["design"]["type"]["body"]["family"] = "Fraunces"
    html = generator().render_page("blank", data, "Uma família", None)
    assert html.count("family=Fraunces") == 1


def test_manual_nao_somos_fallback() -> None:
    data = brand("forno-e-brasa")
    data = json.loads(json.dumps(data))
    data["attributes"] = ["artesanal", "lunar"]

    html = generator().render_page("manual", data, "Manual", None)
    assert "industrial" in html, "a known attribute uses the antonym map"
    assert "[placeholder — oposto de lunar]" in html


# ---------------------------------------------------------------------------
# Overwrite protection and CLI
# ---------------------------------------------------------------------------


def test_new_page_refuses_overwrite() -> None:
    mod = generator()
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "page.html"
        generate("blank", target)
        before = target.read_text(encoding="utf-8")
        assert before

        try:
            generate("blank", target)
        except FileExistsError as exc:
            assert "--force" in str(exc)
        else:
            raise AssertionError("expected FileExistsError without force")
        assert target.read_text(encoding="utf-8") == before

        mod.new_page(
            "blank",
            FIXTURES / "forno-e-brasa.brand.json",
            "Outro título",
            target,
            force=True,
        )
        forced = target.read_text(encoding="utf-8")
        assert forced != before
        assert "Outro título" in forced


def test_cli_missing_brand_exits_2() -> None:
    mod = generator()
    with tempfile.TemporaryDirectory() as tmp:
        previous = os.getcwd()
        os.chdir(tmp)
        stderr = io.StringIO()
        try:
            with contextlib.redirect_stderr(stderr):
                code = mod.main(
                    [
                        "--format",
                        "blank",
                        "--title",
                        "Sem marca",
                        "--out",
                        str(Path(tmp) / "blank.html"),
                    ]
                )
        finally:
            os.chdir(previous)

        message = stderr.getvalue()
        assert code == 2, message
        assert "Traceback" not in message
        assert "--brand" in message
        assert "brand.json" in message


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
