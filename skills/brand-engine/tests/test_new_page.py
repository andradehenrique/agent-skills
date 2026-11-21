"""Tests for the branded single-file page generator.

Run with pytest (``python3 -m pytest skills/brand-engine/tests/test_new_page.py``)
or directly with Python when pytest is unavailable
(``python3 skills/brand-engine/tests/test_new_page.py``).

The generated HTML is the contract Task 4's checker consumes: a single file
with the logo sprite at the top of ``<body>``, a theme toggle, semantic tokens
only, and one ``<main>``/``<h1>`` per format.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SAMPLE_BRAND = Path(__file__).resolve().parent / "fixtures" / "forno-e-brasa.brand.json"
FORMATS = ("manual", "onepage", "deck", "report", "social", "blank")

sys.path.insert(0, str(SCRIPTS))

try:  # RED phase: the generator does not exist yet.
    import new_page as npg
except ImportError as exc:  # pragma: no cover - only on the first red run
    npg = None  # type: ignore[assignment]
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


def generator():
    assert npg is not None, f"new_page not defined ({IMPORT_ERROR})"
    return npg


def content_html(html: str) -> str:
    """The page markup without <style>/<script> blocks or comments.

    Tokens live in the stylesheet and comments; the content itself must never
    carry a bare hex or a palette utility.
    """

    without_blocks = re.sub(r"<style\b.*?</style>", "", html, flags=re.S | re.I)
    without_blocks = re.sub(r"<script\b.*?</script>", "", without_blocks, flags=re.S | re.I)
    return re.sub(r"<!--.*?-->", "", without_blocks, flags=re.S)


def content_classes(html: str) -> list[str]:
    classes: list[str] = []
    for group in re.findall(r'class="([^"]*)"', content_html(html), flags=re.I):
        classes.extend(group.split())
    return classes


def generate(fmt: str, out: str | Path, **kwargs: object) -> str:
    mod = generator()
    return mod.new_page(fmt, SAMPLE_BRAND, "Forno & Brasa", out, **kwargs)


def test_generates_six_formats_with_sprite_and_no_hex() -> None:
    mod = generator()
    with tempfile.TemporaryDirectory() as tmp:
        for fmt in FORMATS:
            html = generate(fmt, tmp)
            assert "<svg><symbol" in html, fmt
            assert "data-theme-toggle" in html, fmt
            assert f'data-format="{fmt}"' in html, fmt
            # The sprite is injected at the top of <body>, before the content.
            assert html.index("<svg><symbol") < html.index("<main"), fmt
            assert html.index("<svg><symbol") > html.index("<body"), fmt
            # No palette utilities, no bare hex in class or style.
            assert "bg-blue-600" not in html, fmt
            classes = " ".join(content_classes(html))
            assert not re.search(r"#[0-9A-Fa-f]{6}\b", classes), fmt
            assert not re.search(
                r'style="[^"]*#[0-9A-Fa-f]{3,8}', content_html(html)
            ), fmt
            assert (Path(tmp) / f"{fmt}.html").is_file(), fmt

        manual = generate("manual", tmp, force=True)
        assert "SOMOS" in manual
        assert "NÃO SOMOS" in manual
        # Only the single approved gradient utility; no ad-hoc gradients.
        assert "bg-grad-brand" in manual
        assert "bg-gradient-to" not in manual
        # Single-file: nothing but the six HTML files lands in the directory.
        assert sorted(path.name for path in Path(tmp).iterdir()) == sorted(
            f"{fmt}.html" for fmt in FORMATS
        )
        assert mod is npg


def test_each_format_does_its_own_job() -> None:
    generator()
    with tempfile.TemporaryDirectory() as tmp:
        onepage = generate("onepage", tmp)
        assert 'data-page="hero"' in onepage
        assert 'data-page="proof"' in onepage
        assert 'data-page="cta"' in onepage

        deck = generate("deck", tmp)
        assert deck.count("data-slide") >= 4
        assert "1280px" in deck and "720px" in deck
        assert "container-type: inline-size" in deck

        report = generate("report", tmp)
        assert "<table" in report
        assert "<caption" in report
        assert '<th scope="col"' in report
        assert "tabular-nums" in report

        social = generate("social", tmp)
        assert 'data-social="square"' in social
        assert 'data-social="story"' in social
        assert "1080px" in social
        assert "1080 × 1080" in social and "1080 × 1920" in social

        blank = generate("blank", tmp)
        assert "<main" in blank and "<h1" in blank
        assert "<table" not in blank

        manual = generate("manual", tmp)
        for term in (
            "Propósito",
            "Tom de voz",
            "Cores",
            "Brasa",
            "#A6402F",
            "Pantone",
            "Tipografia",
            "8px",
            "área de respiro",
            "Misuses",
        ):
            assert term in manual, term


def test_every_page_has_one_main_one_h1_and_accessible_tables() -> None:
    generator()
    with tempfile.TemporaryDirectory() as tmp:
        for fmt in FORMATS:
            html = generate(fmt, tmp)
            assert html.lower().count("<main") == 1, fmt
            assert html.lower().count("<h1") == 1, fmt
            for table in re.findall(r"<table\b.*?</table>", html, flags=re.S | re.I):
                assert "<caption" in table, fmt
                assert "<th" in table, fmt
            for button in re.findall(r"<button\b[^>]*>", html, flags=re.I):
                assert "aria-label" in button or "title=" in button, (fmt, button)


def test_titles_and_brand_copy_are_escaped() -> None:
    mod = generator()
    with tempfile.TemporaryDirectory() as tmp:
        html = mod.new_page(
            "blank", SAMPLE_BRAND, 'Forno & <Brasa> "x"', tmp, force=True
        )
        assert "<title>Forno &amp; &lt;Brasa&gt; &quot;x&quot;</title>" in html
        assert "<h1" in html and "Forno &amp; &lt;Brasa&gt;" in html
        assert "<Brasa>" not in html


def test_theme_modes_set_default_and_lock() -> None:
    generator()
    with tempfile.TemporaryDirectory() as tmp:
        dark = generate("blank", tmp, theme="dark", force=True)
        assert 'data-theme-default="dark"' in dark
        assert 'data-theme-lock="' not in dark

        system = generate("blank", tmp, theme="system", force=True)
        assert 'data-theme-default="system"' in system
        assert 'data-theme-lock="' not in system

        locked = generate("blank", tmp, theme="dark-only", force=True)
        assert 'data-theme-default="dark"' in locked
        assert 'data-theme-lock="dark"' in locked
        # The toggle markup stays for the checker; the lock hides it visually.
        assert "data-theme-toggle" in locked

        try:
            generate("blank", tmp, theme="neon", force=True)
        except ValueError as exc:
            assert "theme" in str(exc)
        else:
            raise AssertionError("an unknown theme must raise ValueError")


def test_refuses_overwrite_without_force() -> None:
    generator()
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "page.html"
        assert (target).exists() is False
        generate("blank", target)
        assert target.is_file()

        before = target.read_text(encoding="utf-8")
        try:
            generate("blank", target)
        except FileExistsError as exc:
            assert "--force" in str(exc)
        else:
            raise AssertionError("expected FileExistsError without force")
        assert target.read_text(encoding="utf-8") == before

        generator().new_page("blank", SAMPLE_BRAND, "Outro título", target, force=True)
        forced = target.read_text(encoding="utf-8")
        assert forced != before
        assert "Outro título" in forced


def test_cli_writes_page_and_explains_errors() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "landing.html"
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "new_page.py"),
                "--brand",
                str(SAMPLE_BRAND),
                "--format",
                "onepage",
                "--title",
                "Forno & Brasa",
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert out.is_file()
        assert "ok:" in result.stdout
        assert 'data-format="onepage"' in out.read_text(encoding="utf-8")

        again = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "new_page.py"),
                "--brand",
                str(SAMPLE_BRAND),
                "--format",
                "onepage",
                "--title",
                "Forno & Brasa",
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert again.returncode == 2
        assert "--force" in again.stderr
        assert "Traceback" not in again.stderr

        forced = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "new_page.py"),
                "--brand",
                str(SAMPLE_BRAND),
                "--format",
                "onepage",
                "--title",
                "Forno & Brasa",
                "--out",
                str(out),
                "--force",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert forced.returncode == 0, forced.stderr


def test_cli_without_brand_asks_instead_of_crashing() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "new_page.py"),
                "--format",
                "blank",
                "--title",
                "Sem marca",
                "--out",
                str(Path(tmp) / "blank.html"),
            ],
            cwd=tmp,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 2, result.stderr
        assert "Traceback" not in result.stderr
        assert "--brand" in result.stderr
        assert "brand.json" in result.stderr


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
