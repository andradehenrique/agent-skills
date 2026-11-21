"""Contract tests for the brand-engine v2 integration assets.

Covers the three shared pieces Tasks 5-7 consume:

- ``assets/icons.json``: the semantic -> Iconify name map for all four
  supported families (``fluent``, ``lucide``, ``phosphor``/``ph``, ``tabler``);
- ``assets/brand-charts.js``: the ``window.BrandCharts`` helper that reads the
  chart tokens and re-renders on ``data-theme`` changes;
- ``scripts/axe_copy.py``: the axe-core copy generator, which audits every
  theme unless the page locks one.

Run with pytest (``python3 -m pytest
skills/brand-engine/tests/test_integrations.py``) or directly with Python when
pytest is unavailable
(``python3 skills/brand-engine/tests/test_integrations.py``).
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SCRIPTS = ROOT / "scripts"

FAMILY_PREFIX = {
    "fluent": "fluent:",
    "lucide": "lucide:",
    "phosphor": "ph:",
    "tabler": "tabler:",
}

REQUIRED_ICONS = (
    "arrow-right",
    "arrow-left",
    "check",
    "x",
    "plus",
    "search",
    "menu",
    "chevron-down",
    "external-link",
    "alert-triangle",
    "alert-circle",
    "info",
    "check-circle",
    "x-circle",
    "chart-line",
    "chart-bar",
    "users",
    "user",
    "settings",
    "home",
    "file-text",
    "calendar",
    "clock",
    "mail",
    "phone",
    "map-pin",
    "download",
    "upload",
    "trash",
    "edit",
    "filter",
    "star",
    "heart",
    "sun",
    "moon",
)


def load_axe_copy():
    path = SCRIPTS / "axe_copy.py"
    assert path.is_file(), "missing skills/brand-engine/scripts/axe_copy.py"
    spec = importlib.util.spec_from_file_location("axe_copy", path)
    assert spec and spec.loader, f"cannot import {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules["axe_copy"] = module
    spec.loader.exec_module(module)
    return module


def write_page(directory: Path, name: str, html_attrs: str, body: str = "<main><p>Oi</p></main>") -> Path:
    page = directory / name
    page.write_text(
        "<!doctype html>\n<html lang=\"pt-BR\" "
        + html_attrs
        + ">\n<head><meta charset=\"utf-8\"><title>T</title></head>\n<body>"
        + body
        + "</body>\n</html>\n",
        encoding="utf-8",
    )
    return page


def emitted_themes(html: str) -> list[str]:
    match = re.search(r"var themes = (\[[^\]]*\]);", html)
    assert match, "axe copy must emit its theme list as `var themes = [...];`"
    return json.loads(match.group(1))


def test_icons_map_has_required_semantics() -> None:
    path = ASSETS / "icons.json"
    assert path.is_file(), "missing skills/brand-engine/assets/icons.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    families = data.get("families")
    assert isinstance(families, dict), "icons.json needs a `families` object"
    assert set(families) == set(FAMILY_PREFIX), (
        f"families must be exactly {sorted(FAMILY_PREFIX)}; got {sorted(families)}"
    )

    icons = data.get("icons")
    assert isinstance(icons, dict), "icons.json needs an `icons` object"
    missing = [key for key in REQUIRED_ICONS if key not in icons]
    assert not missing, f"icons.json is missing semantic keys: {', '.join(missing)}"

    for key in REQUIRED_ICONS:
        entry = icons[key]
        assert isinstance(entry, dict), f"icons[{key!r}] must be an object"
        assert set(entry) == set(FAMILY_PREFIX), (
            f"icons[{key!r}] must define all four families; got {sorted(entry)}"
        )
        for family, prefix in FAMILY_PREFIX.items():
            value = entry[family]
            assert isinstance(value, str) and value.startswith(prefix), (
                f"icons[{key!r}][{family!r}] must start with {prefix!r}; got {value!r}"
            )
            name = value[len(prefix):]
            assert name and not re.search(r"\s", name), (
                f"icons[{key!r}][{family!r}] has an invalid Iconify name: {value!r}"
            )


def test_brand_charts_reads_tokens() -> None:
    path = ASSETS / "brand-charts.js"
    assert path.is_file(), "missing skills/brand-engine/assets/brand-charts.js"
    source = path.read_text(encoding="utf-8")

    for token in ("--b-chart-1", "--b-fg-subtle", "--b-line", "--b-surface"):
        assert token in source, f"brand-charts.js must read {token}"
    for api in ("getComputedStyle", "MutationObserver", "data-theme"):
        assert api in source, f"brand-charts.js must use {api}"

    assert "window.BrandCharts" in source, "brand-charts.js must expose window.BrandCharts"
    for member in ("colors", "create", "refresh"):
        assert re.search(rf"\b{member}\s*:", source), (
            f"window.BrandCharts must expose {member}()"
        )


def test_axe_copy_creates_copy() -> None:
    axe_copy = load_axe_copy()
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw)
        page = write_page(directory, "page.html", 'data-theme-default="light"')

        assert axe_copy.main([str(page)]) == 0

        out = page.with_suffix(".axe.html")
        assert out.is_file(), "axe_copy must write <name>.axe.html next to the page"
        copy = out.read_text(encoding="utf-8")
        for marker in ("axe.min.js", "#axe-out", "wcag22aa"):
            assert marker in copy, f"axe copy must contain {marker}"
        assert "</html>" in copy


def test_axe_copy_respects_theme_lock() -> None:
    axe_copy = load_axe_copy()
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw)

        locked = write_page(
            directory,
            "locked.html",
            'data-theme="dark" data-theme-lock="dark" data-theme-default="dark"',
        )
        assert axe_copy.main([str(locked), "--out", str(directory / "locked.axe.html")]) == 0
        locked_copy = (directory / "locked.axe.html").read_text(encoding="utf-8")
        assert emitted_themes(locked_copy) == ["dark"]

        unlocked = write_page(directory, "unlocked.html", 'data-theme-default="light"')
        assert axe_copy.main([str(unlocked), "--out", str(directory / "unlocked.axe.html")]) == 0
        unlocked_copy = (directory / "unlocked.axe.html").read_text(encoding="utf-8")
        assert emitted_themes(unlocked_copy) == ["light", "dark"]


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
