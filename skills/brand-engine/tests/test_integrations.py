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
import shutil
import subprocess
import sys
import tempfile
import textwrap
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


BRAND_CHARTS_HARNESS = r"""
const fs = require("fs");
const vm = require("vm");

const source = fs.readFileSync(process.argv[2], "utf8");
const tokens = {
  "--b-chart-1": "#101010",
  "--b-chart-2": "#202020",
  "--b-fg-subtle": "#666666",
  "--b-line": "#dddddd",
  "--b-surface": "#ffffff"
};
const canvases = { chart: { id: "chart" } };
const created = [];

function Chart(canvas, config) {
  this.canvas = canvas;
  this.config = config;
  created.push(this);
}
Chart.prototype.destroy = function () {};

const documentElement = {
  getAttribute: function () { return "light"; },
  setAttribute: function () {}
};
const sandbox = {
  window: null,
  document: {
    documentElement: documentElement,
    getElementById: function (id) { return canvases[id] || null; },
    body: {}
  },
  MutationObserver: function (callback) { this.callback = callback; }
};
sandbox.MutationObserver.prototype.observe = function () {};
sandbox.window = sandbox;
sandbox.window.Chart = Chart;
sandbox.window.MutationObserver = sandbox.MutationObserver;
sandbox.window.getComputedStyle = function () {
  return {
    getPropertyValue: function (name) { return tokens[name] || ""; }
  };
};

vm.createContext(sandbox);
vm.runInContext(source, sandbox);

const BrandCharts = sandbox.window.BrandCharts;
if (!BrandCharts) throw new Error("BrandCharts was not exposed");

function spec(options) {
  return {
    type: "bar",
    data: { labels: ["a"], datasets: [{ data: [1] }] },
    options: options
  };
}
function lastConfig() {
  return created[created.length - 1].config;
}

BrandCharts.create("chart", spec({ plugins: { legend: false, title: false } }));
let cfg = lastConfig();
if (cfg.options.plugins.legend !== false) {
  throw new Error("legend:false was replaced with " + JSON.stringify(cfg.options.plugins.legend));
}
if (cfg.options.plugins.title !== false) {
  throw new Error("title:false was replaced with " + JSON.stringify(cfg.options.plugins.title));
}

BrandCharts.create("chart", spec({ plugins: { legend: {}, title: {} } }));
cfg = lastConfig();
if (!cfg.options.plugins.legend || cfg.options.plugins.legend.labels.color !== "#666666") {
  throw new Error("legend:{} did not receive the fg token: " + JSON.stringify(cfg.options.plugins.legend));
}
if (!cfg.options.plugins.title || cfg.options.plugins.title.color !== "#666666") {
  throw new Error("title:{} did not receive the fg token: " + JSON.stringify(cfg.options.plugins.title));
}

BrandCharts.create("chart", spec({ scales: { x: { grid: false, ticks: false } } }));
cfg = lastConfig();
if (cfg.options.scales.x.grid !== false) {
  throw new Error("grid:false was replaced with " + JSON.stringify(cfg.options.scales.x.grid));
}
if (cfg.options.scales.x.ticks !== false) {
  throw new Error("ticks:false was replaced with " + JSON.stringify(cfg.options.scales.x.ticks));
}

console.log("ok");
"""


def test_brand_charts_preserves_disabled_plugins() -> None:
    source = ASSETS / "brand-charts.js"
    assert source.is_file(), "missing skills/brand-engine/assets/brand-charts.js"
    node = shutil.which("node")
    assert node, (
        "node is required for the brand-charts behavioral test; install Node.js "
        "so the harness can run rather than silently skipping"
    )

    with tempfile.TemporaryDirectory() as raw:
        harness = Path(raw) / "brand_charts_harness.js"
        harness.write_text(textwrap.dedent(BRAND_CHARTS_HARNESS), encoding="utf-8")
        result = subprocess.run(
            [node, str(harness), str(source)],
            capture_output=True,
            text=True,
            timeout=30,
        )

    assert result.returncode == 0, (
        "brand-charts harness failed:\n"
        f"stdout: {result.stdout.strip()}\n"
        f"stderr: {result.stderr.strip()}"
    )
    assert "ok" in result.stdout


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
