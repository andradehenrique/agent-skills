"""Tests for the brand.json contract and the theme builder.

Run with pytest (``python3 -m pytest skills/brand-engine/tests/test_build_theme.py``)
or directly with Python when pytest is unavailable
(``python3 skills/brand-engine/tests/test_build_theme.py``).
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SAMPLE_BRAND = Path(__file__).resolve().parent / "fixtures" / "forno-e-brasa.brand.json"

sys.path.insert(0, str(SCRIPTS))

try:  # RED phase: the builder does not exist yet.
    import build_theme as bt
except ImportError as exc:  # pragma: no cover - only on the first red run
    bt = None  # type: ignore[assignment]
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


def builder():
    assert bt is not None, f"build_theme not defined ({IMPORT_ERROR})"
    return bt


def write_brand(directory: Path, data: dict[str, Any]) -> Path:
    path = directory / "brand.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_build_theme_from_sample_brand() -> None:
    mod = builder()
    with tempfile.TemporaryDirectory() as tmp:
        theme_css, tailwind_theme_css = mod.build_theme(SAMPLE_BRAND, tmp)

        assert "--b-primary" in theme_css
        assert "--b-display" in theme_css
        assert "--b-color-brasa" in theme_css
        assert '"Fraunces"' in theme_css
        assert '[data-theme="dark"]' in theme_css
        assert "--b-unit: 8px" in theme_css
        assert "--b-space-2: 16px" in theme_css
        assert "--b-text-base: 16px" in theme_css
        assert "--b-leading-base" in theme_css

        gradient = next(line for line in theme_css.splitlines() if "linear-gradient" in line)
        assert "45deg" in gradient
        assert gradient.count("50%") == 2, "gradient must be exactly 50/50, two stops"

        assert "Allowed color pairs" in theme_css
        assert "Creme on Brasa" in theme_css
        assert "AA" in theme_css

        assert "bg-surface" in tailwind_theme_css
        assert "text-fg-muted" in tailwind_theme_css
        assert "border-line" in tailwind_theme_css
        assert "--color-primary: var(--b-primary)" in tailwind_theme_css
        assert "@custom-variant dark" in tailwind_theme_css
        assert "--spacing: 8px" in tailwind_theme_css

        out = Path(tmp)
        assert (out / "theme.css").read_text(encoding="utf-8") == theme_css
        assert (out / "tailwind-theme.css").read_text(encoding="utf-8") == tailwind_theme_css


def test_build_theme_refuses_overwrite_without_force() -> None:
    mod = builder()
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        (out / "theme.css").write_text("keep me", encoding="utf-8")

        try:
            mod.build_theme(SAMPLE_BRAND, out)
        except FileExistsError as exc:
            assert "--force" in str(exc)
        else:
            raise AssertionError("expected FileExistsError without force")

        assert (out / "theme.css").read_text(encoding="utf-8") == "keep me"
        assert not (out / "tailwind-theme.css").exists(), "no partial write before force"

        mod.build_theme(SAMPLE_BRAND, out, force=True)
        assert "--b-primary" in (out / "theme.css").read_text(encoding="utf-8")


def test_resolve_brand_path_precedence() -> None:
    mod = builder()
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        flag = cwd / "custom.json"
        flag.write_text("{}", encoding="utf-8")
        (cwd / "brand.json").write_text("{}", encoding="utf-8")
        (cwd / "brand").mkdir()
        (cwd / "brand" / "brand.json").write_text("{}", encoding="utf-8")

        assert mod.resolve_brand_path(flag, cwd) == flag
        assert mod.resolve_brand_path(cwd / "brand.json", cwd) == cwd / "brand.json"

        (cwd / "brand.json").unlink()
        assert mod.resolve_brand_path(None, cwd) == cwd / "brand" / "brand.json"

        (cwd / "brand" / "brand.json").unlink()
        assert mod.resolve_brand_path(None, cwd) is None

        try:
            mod.resolve_brand_path(cwd / "missing.json", cwd)
        except mod.BrandError as exc:
            assert "not found" in str(exc)
        else:
            raise AssertionError("a missing --brand path must raise BrandError")


def test_missing_brand_asks_instead_of_crashing() -> None:
    mod = builder()
    assert mod.missing_brand_behavior() == "ask-for-path-or-discovery"

    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "build_theme.py"), "--out", tmp],
            cwd=tmp,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 2, result.stderr
        assert "Traceback" not in result.stderr
        assert "--brand" in result.stderr
        assert "brand.json" in result.stderr


def test_schema_validation_is_actionable() -> None:
    mod = builder()
    original = json.loads(SAMPLE_BRAND.read_text(encoding="utf-8"))

    mutations: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("missing purpose", lambda d: d.pop("purpose")),
        ("empty purpose", lambda d: d.__setitem__("purpose", "   ")),
        ("bad hex", lambda d: d["colors"]["primary"][0].__setitem__("hex", "#NOTHEX")),
        ("bad gradient angle", lambda d: d["gradient"].__setitem__("angle", 30)),
        ("bad logo variant", lambda d: d["logo"].__setitem__("variant", "D")),
        ("bad unit", lambda d: d.__setitem__("unit", 4)),
        ("unknown pair color", lambda d: d.__setitem__("allowed_pairs", [{"bg": "Brasa", "fg": "Cinza"}])),
        (
            "duplicate color name",
            lambda d: d["colors"]["secondary"].append({"name": "brasa", "hex": "#123456"}),
        ),
        ("same gradient colors", lambda d: d["gradient"].__setitem__("to", "Brasa")),
    ]

    for label, mutate in mutations:
        data = copy.deepcopy(original)
        mutate(data)
        with tempfile.TemporaryDirectory() as tmp:
            path = write_brand(Path(tmp), data)
            try:
                mod.load_brand(path)
            except mod.BrandError as exc:
                assert "brand.json" in str(exc), (label, str(exc))
            else:
                raise AssertionError(f"expected BrandError for {label}")


def test_malformed_json_is_a_brand_error() -> None:
    mod = builder()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "brand.json"
        path.write_text("{ not json", encoding="utf-8")
        try:
            mod.load_brand(path)
        except mod.BrandError as exc:
            assert "JSON" in str(exc)
        else:
            raise AssertionError("malformed JSON must raise BrandError")


def test_contrast_ratio_matches_wcag_reference() -> None:
    mod = builder()
    assert abs(mod.contrast_ratio("#000000", "#FFFFFF") - 21.0) < 0.01
    assert abs(mod.contrast_ratio("#A6402F", "#A6402F") - 1.0) < 0.001


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
