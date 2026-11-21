"""End-to-end smoke test for the brand-engine v2 generator.

Run with the stdlib runner (pytest is unavailable in this repo)::

    python3 skills/brand-engine/tests/test_smoke.py

The smoke test uses the coherent ``omnia.brand.json`` fixture and generates
every entry in ``new_page.FORMATS`` into a temp directory. Each file must be a
complete page (no ``{{`` leftovers), pass ``check_page.check_page`` with zero
ERROR, and stay format-specific: ``onepage`` and ``report`` must differ in
``data-format`` and section headings, and ``brand-kit`` must carry the mini
cases.

No network calls: the Iconify/Chart.js/placehold.co URLs are only strings in
the generated HTML.
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
OMNIA = FIXTURES / "omnia.brand.json"
TITLE = "Omnia Labs"

sys.path.insert(0, str(SCRIPTS))

try:  # RED phase: the fixture or the v2 modules may not exist yet.
    import check_page as checking
    import new_page as npg
except ImportError as exc:  # pragma: no cover - only on the first red run
    checking = None  # type: ignore[assignment]
    npg = None  # type: ignore[assignment]
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


def modules():
    assert npg is not None and checking is not None, (
        f"new_page/check_page not importable ({IMPORT_ERROR})"
    )
    return npg, checking


def generate_all(directory: Path) -> dict[str, Path]:
    npg, _ = modules()
    assert OMNIA.is_file(), f"missing v2 fixture: {OMNIA}"
    paths: dict[str, Path] = {}
    for fmt in npg.FORMATS:
        paths[fmt] = npg.new_page(fmt, OMNIA, TITLE, directory / f"{fmt}.html")
    return paths


def data_format(html: str) -> str | None:
    match = re.search(r'data-format="([^"]+)"', html)
    return match.group(1) if match else None


def headings(html: str) -> list[str]:
    found = re.findall(r"<h2\b[^>]*>(.*?)</h2>", html, re.DOTALL | re.IGNORECASE)
    return [
        re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", heading)).strip()
        for heading in found
        if re.sub(r"<[^>]+>", "", heading).strip()
    ]


def test_smoke_generates_every_format() -> None:
    npg, _ = modules()
    with tempfile.TemporaryDirectory() as tmp:
        paths = generate_all(Path(tmp))
        assert set(paths) == set(npg.FORMATS), (
            f"expected {list(npg.FORMATS)}, got {sorted(paths)}"
        )
        for fmt, path in paths.items():
            assert path.is_file(), f"{fmt} was not written to {path}"
            html = path.read_text(encoding="utf-8")
            assert html.strip(), f"{fmt} is empty"
            assert "{{" not in html, f"{fmt} still has a {{{{ placeholder"
            assert data_format(html) == fmt, f"{fmt} has the wrong data-format"
            assert "<html" in html and "<body" in html, f"{fmt} is not a full page"


def test_smoke_checker_zero_errors() -> None:
    _, checking_module = modules()
    with tempfile.TemporaryDirectory() as tmp:
        paths = generate_all(Path(tmp))
        for fmt, path in paths.items():
            findings = checking_module.check_page(path)
            errors = [finding for finding in findings if finding.startswith("ERROR")]
            assert not errors, f"{fmt} has check_page ERRORs: {errors}"


def test_smoke_outputs_differ() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        paths = generate_all(Path(tmp))

        onepage = paths["onepage"].read_text(encoding="utf-8")
        report = paths["report"].read_text(encoding="utf-8")

        assert data_format(onepage) == "onepage"
        assert data_format(report) == "report"

        onepage_headings = headings(onepage)
        report_headings = headings(report)
        assert onepage_headings, "onepage has no h2 section headings"
        assert report_headings, "report has no h2 section headings"
        assert set(onepage_headings) != set(report_headings), (
            "onepage and report must not reuse the same section headings"
        )

        brand_kit = paths["brand-kit"].read_text(encoding="utf-8")
        cases = set(re.findall(r'data-case="([^"]+)"', brand_kit))
        assert {"onepage", "report", "deck", "app"} <= cases, (
            f"brand-kit is missing mini cases, got {sorted(cases)}"
        )
        assert "mini cases" in brand_kit.lower(), (
            "brand-kit must document the mini cases as proof of the system"
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
