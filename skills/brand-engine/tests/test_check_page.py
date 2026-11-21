"""Tests for the extended brand checker.

Run with pytest (``python3 -m pytest skills/brand-engine/tests/test_check_page.py``)
or directly with Python when pytest is unavailable
(``python3 skills/brand-engine/tests/test_check_page.py``).

The fixtures are real ``new_page()`` output, so the checker is validated against
the same HTML contract Task 3 ships. Each test then mutates one thing and
asserts the matching rule fires.
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

try:  # RED phase: the checker does not exist yet.
    import check_page as checking
except ImportError as exc:  # pragma: no cover - only on the first red run
    checking = None  # type: ignore[assignment]
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None

try:  # Task 3 output is the fixture for the checker.
    import new_page as npg
except ImportError as exc:  # pragma: no cover - already covered by Task 3 tests
    npg = None  # type: ignore[assignment]
    NEW_PAGE_ERROR = exc
else:
    NEW_PAGE_ERROR = None


def checker():
    assert checking is not None, f"check_page not defined ({IMPORT_ERROR})"
    return checking


def generator():
    assert npg is not None, f"new_page not defined ({NEW_PAGE_ERROR})"
    return npg


def render(fmt: str, tmp: str | Path, **kwargs: object) -> str:
    path = generator().new_page(
        fmt, SAMPLE_BRAND, "Forno & Brasa", tmp, force=True, **kwargs
    )
    return path.read_text(encoding="utf-8")


def write(tmp: str | Path, name: str, html: str) -> str:
    path = Path(tmp) / name
    path.write_text(html, encoding="utf-8")
    return str(path)


def findings(path: str) -> list[str]:
    return checker().check_page(path)


def errors(path: str) -> list[str]:
    return [item for item in findings(path) if item.startswith("ERROR")]


def assert_rule(path: str, rule: str, severity: str = "ERROR") -> str:
    matches = [
        item
        for item in findings(path)
        if item.startswith(severity) and f"[{rule}]" in item
    ]
    assert matches, f"expected {severity} [{rule}], got {findings(path)}"
    return matches[0]


def strip_block(html: str, pattern: str) -> str:
    return re.sub(pattern, "", html, count=1, flags=re.S)


def test_generated_pages_have_no_errors() -> None:
    """The generator's six formats are the checker's clean baseline."""

    with tempfile.TemporaryDirectory() as tmp:
        for fmt in FORMATS:
            render(fmt, tmp)
            path = str(Path(tmp) / f"{fmt}.html")
            problems = errors(path)
            assert problems == [], (fmt, problems)


def test_checker_catches_brand_violations() -> None:
    """The five violations from the plan brief, as real assertions."""

    with tempfile.TemporaryDirectory() as tmp:
        good = render("blank", tmp)
        good_path = write(tmp, "good.html", good)
        assert errors(good_path) == []

        hex_in_class = good.replace(
            'class="min-h-svh bg-canvas', 'class="min-h-svh bg-[#A6402F]', 1
        )
        assert_rule(write(tmp, "hex-class.html", hex_in_class), "tokens")

        hex_in_style = good.replace(
            "</main>", '<div style="color:#A6402F">x</div></main>', 1
        )
        assert_rule(write(tmp, "hex-style.html", hex_in_style), "tokens")

        missing_sprite = strip_block(
            good, r"\s*<div hidden aria-hidden=\"true\" data-logo-sprite>.*?</div>"
        )
        assert_rule(write(tmp, "no-sprite.html", missing_sprite), "sprite")

        three_stop = good.replace(
            "linear-gradient(45deg, #A6402F 50%, #C97B4A 50%)",
            "linear-gradient(45deg, #A6402F 33%, #C97B4A 66%, #5F6B45 100%)",
            1,
        )
        assert_rule(write(tmp, "three-stop.html", three_stop), "gradient")

        report = render("report", tmp)
        no_caption = strip_block(report, r"<caption>.*?</caption>")
        assert_rule(write(tmp, "no-caption.html", no_caption), "table")


def test_checker_catches_structure_and_accessibility_failures() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        good = render("blank", tmp)

        unlabelled = good.replace(
            'data-theme-toggle aria-label="Alternar tema claro/escuro" aria-pressed="false"',
            'data-theme-toggle aria-pressed="false"',
            1,
        )
        assert_rule(write(tmp, "unlabelled.html", unlabelled), "a11y")

        onclick = good.replace(
            "</main>", '<div onclick="alert(1)">x</div></main>', 1
        )
        assert_rule(write(tmp, "onclick.html", onclick), "events")

        heading_skip = good.replace(
            "</main>", '<h4 class="text-lg">Salto</h4></main>', 1
        )
        assert_rule(write(tmp, "heading-skip.html", heading_skip), "headings")

        two_h1 = good.replace(
            "</main>", '<h1 class="text-3xl">Outro</h1></main>', 1
        )
        assert_rule(write(tmp, "two-h1.html", two_h1), "headings")

        two_main = good.replace(
            "</body>", '<main id="outro">Texto</main></body>', 1
        )
        assert_rule(write(tmp, "two-main.html", two_main), "structure")

        duplicate_id = good.replace(
            "</main>", '<span id="conteudo">x</span></main>', 1
        )
        assert_rule(write(tmp, "duplicate-id.html", duplicate_id), "a11y")

        dangling = good.replace('<main id="conteudo"', "<main", 1)
        assert_rule(write(tmp, "dangling-anchor.html", dangling), "a11y")

        no_alt = good.replace(
            "</main>", '<img src="data:image/png;base64,AA">' + "</main>", 1
        )
        assert_rule(write(tmp, "no-alt.html", no_alt), "a11y")

        unlabelled_input = good.replace(
            "</main>", '<input type="text"></main>', 1
        )
        assert_rule(write(tmp, "unlabelled-input.html", unlabelled_input), "a11y")

        no_scope = render("report", tmp).replace(
            '<th scope="col">', "<th>", 1
        )
        assert_rule(write(tmp, "no-scope.html", no_scope), "table", severity="WARN")


def test_checker_catches_token_type_and_spacing_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        good = render("blank", tmp)

        palette = good.replace(
            "</main>", '<div class="bg-blue-600 p-2">x</div></main>', 1
        )
        assert_rule(write(tmp, "palette.html", palette), "tokens")

        off_scale_type = good.replace(
            "</main>", '<p class="text-7xl">x</p></main>', 1
        )
        assert_rule(write(tmp, "type-7xl.html", off_scale_type), "type-scale")

        arbitrary_type = good.replace(
            "</main>", '<p class="text-[18px]">x</p></main>', 1
        )
        assert_rule(write(tmp, "type-arbitrary.html", arbitrary_type), "type-scale")

        skipped_step = good.replace(
            "</main>", '<div class="p-5">x</div></main>', 1
        )
        assert_rule(write(tmp, "spacing-5.html", skipped_step), "spacing")

        off_grid = good.replace(
            "</main>", '<div class="p-[20px]">x</div></main>', 1
        )
        assert_rule(write(tmp, "spacing-20.html", off_grid), "spacing")

        on_grid = good.replace(
            "</main>", '<div class="p-[24px]">x</div></main>', 1
        )
        assert errors(write(tmp, "spacing-24.html", on_grid)) == []

        inline_style = good.replace(
            "</main>", '<div style="margin: 5px">x</div></main>', 1
        )
        assert_rule(write(tmp, "spacing-inline.html", inline_style), "spacing")

        raw_color = good.replace(
            "</main>", '<div style="color: red">x</div></main>', 1
        )
        assert_rule(write(tmp, "raw-color.html", raw_color), "tokens")

        primary_body = good.replace(
            "</main>", '<p class="text-primary">x</p></main>', 1
        )
        assert_rule(write(tmp, "primary-body.html", primary_body), "tokens")

        primary_heading = good.replace(
            "</main>", '<h2 class="text-primary">Título</h2></main>', 1
        )
        assert not any(
            "[tokens]" in item and "text-primary" in item
            for item in findings(write(tmp, "primary-heading.html", primary_heading))
        )

        weak_control = good.replace(
            "</main>",
            '<input type="text" aria-label="Nome" class="border border-line">'
            + "</main>",
            1,
        )
        assert_rule(write(tmp, "weak-control.html", weak_control), "tokens")

        primary_no_hover = good.replace(
            "</main>",
            '<a href="#" class="bg-primary text-on-primary">Ação</a></main>',
            1,
        )
        assert_rule(write(tmp, "primary-hover.html", primary_no_hover), "tokens", "WARN")


def test_checker_catches_gradient_and_logo_misuse() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        good = render("blank", tmp)

        tailwind_gradient = good.replace(
            "</main>", '<div class="bg-gradient-to-r from-primary to-accent">x</div></main>', 1
        )
        assert_rule(write(tmp, "tw-gradient.html", tailwind_gradient), "gradient")

        wrong_angle = good.replace("linear-gradient(45deg", "linear-gradient(90deg", 1)
        assert_rule(write(tmp, "angle.html", wrong_angle), "gradient")

        wrong_stops = good.replace(
            "#A6402F 50%, #C97B4A 50%", "#A6402F 0%, #C97B4A 100%", 1
        )
        assert_rule(write(tmp, "stops.html", wrong_stops), "gradient")

        radial = good.replace(
            "</head>",
            "<style>.x{background-image: radial-gradient(circle, #fff, #000)}</style>"
            + "</head>",
            1,
        )
        assert_rule(write(tmp, "radial.html", radial), "gradient")

        no_breathing = strip_block(
            good, r"\s*<!-- logo: breathing area.*?-->"
        )
        assert_rule(write(tmp, "no-breathing.html", no_breathing), "logo-breathing")

        transformed = good.replace(
            '<svg class="be-mark" aria-hidden="true">',
            '<svg class="be-mark" aria-hidden="true" style="transform: rotate(10deg)">',
            1,
        )
        assert_rule(write(tmp, "logo-rotate.html", transformed), "logo-misuse")

        raster_logo = good.replace(
            "</main>", '<img src="data:image/png;base64,AA" alt="Logo">' + "</main>", 1
        )
        assert_rule(write(tmp, "logo-raster.html", raster_logo), "logo-misuse")

        manual = render("manual", tmp)
        for phrase, rule in (
            (r"<li>Recolorir.*?</li>", "recolor"),
            (r"<li>Rotacionar.*?</li>", "rotate"),
            (r"<li>Esticar.*?</li>", "stretch"),
            (r"<li>Trocar.*?</li>", "replace"),
        ):
            mutated = strip_block(manual, phrase)
            found = assert_rule(
                write(tmp, f"misuse-{rule}.html", mutated), "misuse"
            )
            assert rule in found, (rule, found)


def test_checker_cli_reports_and_exits() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        clean = Path(write(tmp, "clean.html", render("blank", tmp)))
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "check_page.py"), str(clean)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "ok:" in result.stdout
        assert "Traceback" not in result.stderr

        broken = Path(
            write(
                tmp,
                "broken.html",
                render("blank", tmp).replace(
                    "</main>", '<div class="p-5">x</div></main>', 1
                ),
            )
        )
        failed = subprocess.run(
            [sys.executable, str(SCRIPTS / "check_page.py"), str(broken)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert failed.returncode == 1
        assert "ERROR [spacing]" in failed.stdout
        assert "Traceback" not in failed.stderr

        missing = subprocess.run(
            [sys.executable, str(SCRIPTS / "check_page.py"), str(Path(tmp) / "nope.html")],
            capture_output=True,
            text=True,
            check=False,
        )
        assert missing.returncode == 2
        assert "Traceback" not in missing.stderr
        assert "check_page:" in missing.stderr

        warns = Path(
            write(
                tmp,
                "warns.html",
                render("report", tmp).replace('<th scope="col">', "<th>", 1),
            )
        )
        lenient = subprocess.run(
            [sys.executable, str(SCRIPTS / "check_page.py"), str(warns)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert lenient.returncode == 0, lenient.stdout + lenient.stderr
        assert "WARN [table]" in lenient.stdout

        strict = subprocess.run(
            [sys.executable, str(SCRIPTS / "check_page.py"), str(warns), "--strict"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert strict.returncode == 1
        assert "WARN [table]" in strict.stdout


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
