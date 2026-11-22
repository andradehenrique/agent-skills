"""Tests for the brand.json v2 model and validation.

Run with pytest (``python3 -m pytest skills/brand-engine/tests/test_build_theme.py``)
or directly with Python when pytest is unavailable
(``python3 skills/brand-engine/tests/test_build_theme.py``).
"""

from __future__ import annotations

import copy
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
SAMPLE_BRAND = FIXTURES / "forno-e-brasa.brand.json"

sys.path.insert(0, str(SCRIPTS))

try:  # RED phase: the v2 parser does not exist yet.
    import build_theme as bt
except ImportError as exc:  # pragma: no cover - only on the first red run
    bt = None  # type: ignore[assignment]
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


def builder():
    assert bt is not None, f"build_theme not defined ({IMPORT_ERROR})"
    return bt


def fixture(name: str) -> Path:
    return FIXTURES / f"{name}.brand.json"


def brand_data(name: str = "forno-e-brasa") -> dict[str, Any]:
    return json.loads(fixture(name).read_text(encoding="utf-8"))


def expect_error(
    mutate: Callable[[dict[str, Any]], None],
    *needles: str,
    name: str = "forno-e-brasa",
) -> str:
    """Apply ``mutate`` to a fixture copy and assert ``load_brand`` rejects it."""

    mod = builder()
    data = copy.deepcopy(brand_data(name))
    mutate(data)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "brand.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        try:
            mod.load_brand(path)
        except mod.BrandError as exc:
            message = str(exc)
        else:
            raise AssertionError(f"expected BrandError for {name}: {mutate}")
    for needle in needles:
        assert needle.lower() in message.lower(), (needle, message)
    return message


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def test_loads_v2_brand() -> None:
    mod = builder()
    data = mod.load_brand(SAMPLE_BRAND)

    assert data["version"] == 2
    assert data["design"]["colors"]["primary"]["name"] == "Brasa"

    model = mod._build_model(data)
    assert model.name == "Forno & Brasa"
    assert model.purpose.startswith("Levar pizza")
    assert model.persona and model.territory and model.archetype == "O Criador"
    assert model.attributes == ("rústico", "caloroso", "direto", "artesanal")
    assert model.lookup["brasa"].hex == "#A6402F"
    assert model.lookup["brasa"].role == "primary"
    assert {color.role for color in model.colors} == {
        "canvas",
        "surface",
        "ink",
        "primary",
        "accent",
        "support",
    }


def test_loads_varied_fixtures() -> None:
    mod = builder()
    for name in ("brutalist", "luxury"):
        model = mod._build_model(brand_data(name))
        assert model.name
        assert model.colors
        assert model.unit in (4, 8)


def test_applies_defaults() -> None:
    mod = builder()
    data = brand_data()

    data["design"].pop("feedback")
    data["design"].pop("charts")
    data["design"].pop("icons")
    data["design"].pop("imagery")
    data["design"]["shape"].pop("shadows")

    model = mod._build_model(data)

    assert model.feedback == "auto"
    assert model.charts == "auto"
    assert model.shadows == "soft"
    assert model.icons == {"family": "fluent", "size": 16}
    assert model.imagery == {"mode": "abstract", "treatment": ""}


def test_voice_is_optional_with_defaults() -> None:
    mod = builder()
    data = brand_data()
    data.pop("voice")

    model = mod._build_model(data)

    assert model.voice == {
        "summary": "[placeholder — resumo da voz]",
        "principles": [],
        "avoid": [],
        "person": "você",
        "emoji": "none",
    }


def test_rejects_invalid_voice() -> None:
    expect_error(lambda d: d["voice"].__setitem__("emoji", "always"), "none", "social-only")
    expect_error(lambda d: d["voice"].__setitem__("principles", [1, 2]), "principles")
    expect_error(lambda d: d["voice"].pop("summary"), "summary")


# ---------------------------------------------------------------------------
# Version and colour roles
# ---------------------------------------------------------------------------


def test_rejects_v1_brand() -> None:
    expect_error(lambda d: d.__setitem__("version", 1), "version must be 2")
    expect_error(lambda d: d.pop("version"), "version must be 2")


def test_rejects_v1_color_shape() -> None:
    expect_error(
        lambda d: d["design"].__setitem__(
            "colors",
            {
                "primary": [{"name": "Brasa", "hex": "#A6402F"}],
                "secondary": [{"name": "Creme", "hex": "#F4E9D8"}],
            },
        ),
        "design.colors",
    )


def test_rejects_v1_leftovers() -> None:
    expect_error(lambda d: d.__setitem__("allowed_pairs", []), "allowed_pairs")
    expect_error(
        lambda d: d.__setitem__("gradient", {"from": "Creme", "to": "Massa", "angle": 45}),
        "schema v1",
    )
    expect_error(
        lambda d: d["design"].__setitem__("allowed_pairs", []),
        "allowed_pairs",
    )
    expect_error(
        lambda d: d.__setitem__("logo", {"variant": "C", "name": "Chama"}),
        "logo",
    )


def test_type_defaults_when_omitted() -> None:
    mod = builder()
    data = brand_data()
    data["design"].pop("type")

    model = mod._build_model(data)

    assert model.display_stack == '"system-ui", sans-serif'
    assert model.body_stack == '"system-ui", sans-serif'
    assert model.display_weight == 600
    assert model.body_weight == 400
    assert model.scale == (16.0, 1.25)


def test_rejects_missing_required_role() -> None:
    expect_error(lambda d: d["design"]["colors"].pop("canvas"), "canvas")
    expect_error(lambda d: d["design"]["colors"].pop("surface"), "surface")
    expect_error(lambda d: d["design"]["colors"].pop("ink"), "ink")
    expect_error(lambda d: d["design"]["colors"].pop("primary"), "primary")


def test_rejects_invalid_hex() -> None:
    expect_error(
        lambda d: d["design"]["colors"]["primary"].__setitem__("hex", "#12345"),
        "#RRGGBB",
    )


def test_rejects_duplicate_color_names() -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["design"]["colors"]["support"][0]["name"] = "Creme"

    expect_error(mutate, "duplicate")


def test_rejects_duplicate_slugs() -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["design"]["colors"]["support"][0]["name"] = "Brasa!"

    expect_error(mutate, "same CSS token")


# ---------------------------------------------------------------------------
# Shape, theme, icons, composition
# ---------------------------------------------------------------------------


def test_rejects_invalid_unit() -> None:
    expect_error(lambda d: d["design"]["shape"].__setitem__("unit", 6), "4 or 8")


def test_accepts_unit_4() -> None:
    mod = builder()
    data = brand_data()
    data["design"]["shape"]["unit"] = 4

    assert mod._build_model(data).unit == 4


def test_rejects_invalid_radius_profile() -> None:
    expect_error(
        lambda d: d["design"]["shape"].__setitem__("radius", "blob"),
        "sharp",
        "soft",
        "round",
    )


def test_radius_profiles_and_custom_object() -> None:
    mod = builder()

    soft = mod._build_model(brand_data())
    assert [soft.radius[key] for key in ("xs", "sm", "md", "lg", "xl")] == [4, 8, 12, 16, 24]

    data = brand_data()
    data["design"]["shape"]["radius"] = "sharp"
    sharp = mod._build_model(data)
    assert [sharp.radius[key] for key in ("xs", "sm", "md", "lg", "xl")] == [0, 0, 2, 4, 4]

    data["design"]["shape"]["radius"] = {"xs": 1, "lg": 10}
    custom = mod._build_model(data)
    assert custom.radius["xs"] == 1
    assert custom.radius["lg"] == 10
    assert custom.radius["sm"] == 8  # filled from the soft profile


def test_rejects_invalid_shadows() -> None:
    expect_error(lambda d: d["design"]["shape"].__setitem__("shadows", "fuzzy"), "none", "soft", "strong")


def test_rejects_invalid_theme_modes() -> None:
    expect_error(lambda d: d["design"]["theme"].__setitem__("modes", []), "modes")
    expect_error(
        lambda d: d["design"]["theme"].__setitem__("modes", ["light", "sepia"]),
        "light",
        "dark",
    )
    expect_error(
        lambda d: d["design"]["theme"].__setitem__("default", "system"),
        "default",
    )


def test_rejects_default_mode_outside_modes() -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["design"]["theme"]["modes"] = ["light"]
        data["design"]["theme"]["default"] = "dark"

    expect_error(mutate, "default")


def test_accepts_null_gradient() -> None:
    mod = builder()
    model = mod._build_model(brand_data())
    assert model.gradient is None


def test_parses_gradient_with_via() -> None:
    mod = builder()
    model = mod._build_model(brand_data("luxury"))

    assert model.gradient is not None
    assert model.gradient["from"] == "#C6A15B"
    assert model.gradient["to"] == "#6E3B52"
    assert model.gradient["via"] == "#F2EBDD"
    assert model.gradient["angle"] == 120


def test_rejects_invalid_gradient() -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["design"]["theme"]["gradient"] = {"from": "Creme", "to": "Creme", "angle": 45}

    expect_error(mutate, "different")

    def unknown_color(data: dict[str, Any]) -> None:
        data["design"]["theme"]["gradient"] = {"from": "Nada", "to": "Creme", "angle": 45}

    expect_error(unknown_color, "unknown colour")


def test_rejects_invalid_icon_family() -> None:
    expect_error(
        lambda d: d["design"]["icons"].__setitem__("family", "material"),
        "fluent",
        "lucide",
        "phosphor",
        "tabler",
    )


def test_rejects_removed_icon_style_and_imagery_placeholder() -> None:
    """Fields removed from the schema fail loudly instead of staying inert."""
    expect_error(
        lambda d: d["design"]["icons"].__setitem__("style", "thin"),
        "unknown",
        "design.icons",
    )
    expect_error(
        lambda d: d["design"]["imagery"].__setitem__("placeholder", "placehold"),
        "unknown",
        "design.imagery",
    )


def test_language_defaults_and_validates() -> None:
    mod = builder()
    data = brand_data()
    assert mod._build_model(data).language == "pt-BR"

    data["language"] = "en"
    assert mod._build_model(data).language == "en"

    data["language"] = "pt_BR"
    expect_error(lambda d: d.__setitem__("language", "pt_BR"), "BCP-47")


def test_rejects_invalid_composition_direction() -> None:
    expect_error(
        lambda d: d["design"]["composition"].__setitem__("direction", "heroic"),
        "editorial",
        "structured",
        "poster",
        "minimal",
    )


def test_rejects_invalid_logo_variant() -> None:
    expect_error(lambda d: d["design"]["logo"].__setitem__("variant", "D"), "C", "B", "A")


def test_rejects_non_boolean_aceite() -> None:
    expect_error(lambda d: d.__setitem__("aceite", "sim"), "aceite")


def test_rejects_missing_design_block() -> None:
    expect_error(lambda d: d.pop("design"), "design")


# ---------------------------------------------------------------------------
# Discovery and error handling
# ---------------------------------------------------------------------------


def test_resolve_brand_path_order() -> None:
    mod = builder()
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        flag = cwd / "custom.json"
        flag.write_text("{}", encoding="utf-8")
        (cwd / "brand.json").write_text("{}", encoding="utf-8")
        (cwd / "brand").mkdir()
        (cwd / "brand" / "brand.json").write_text("{}", encoding="utf-8")

        assert mod.resolve_brand_path(flag, cwd) == flag
        assert mod.resolve_brand_path("custom.json", cwd) == flag
        assert mod.resolve_brand_path(None, cwd) == cwd / "brand.json"

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


def test_missing_brand_behavior() -> None:
    assert builder().missing_brand_behavior() == "ask-for-path-or-discovery"


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


# ---------------------------------------------------------------------------
# Theme generation
# ---------------------------------------------------------------------------

TYPE_STEP_NAMES = (
    "xs",
    "sm",
    "base",
    "lg",
    "xl",
    "2xl",
    "3xl",
    "4xl",
    "5xl",
    "6xl",
    "7xl",
    "8xl",
)


def render(
    mutate: Callable[[dict[str, Any]], None] | None = None,
    name: str = "forno-e-brasa",
):
    mod = builder()
    data = copy.deepcopy(brand_data(name))
    if mutate is not None:
        mutate(data)
    return mod, data, mod.render_theme(data)


def css_block(css: str, selector: str) -> str:
    pattern = re.escape(selector) + r"\s*\{(.*?)\n\}"
    match = re.search(pattern, css, re.S)
    assert match is not None, f"missing CSS block: {selector}"
    return match.group(1)


def css_tokens(css: str, selector: str = ":root") -> dict[str, str]:
    return dict(re.findall(r"(--b-[a-z0-9-]+):\s*([^;\n]+);", css_block(css, selector)))


def test_theme_has_core_tokens() -> None:
    mod, data, built = render()
    model = mod._build_model(data)
    ink_slug = next(color.slug for color in model.colors if color.role == "ink")
    css = built.theme_css

    for token in (
        "--b-canvas",
        "--b-surface",
        "--b-primary",
        "--b-accent",
        "--b-accent-soft",
        "--b-on-accent",
        "--b-band",
        "--b-fg",
        "--b-link",
        "--b-focus",
        f"--b-color-{ink_slug}",
    ):
        assert f"{token}:" in css, token


def test_feedback_tokens_meet_contrast() -> None:
    mod, _, built = render()
    css = built.theme_css

    for selector in (":root", '[data-theme="dark"]'):
        tokens = css_tokens(css, selector)
        canvas = tokens["--b-canvas"]
        surface = tokens["--b-surface"]
        for role in ("success", "warning", "danger", "info"):
            text = tokens[f"--b-{role}"]
            soft = tokens[f"--b-{role}-soft"]
            solid = tokens[f"--b-{role}-solid"]
            on_soft = tokens[f"--b-on-{role}-soft"]
            on_solid = tokens[f"--b-on-{role}"]

            assert mod.contrast_ratio(text, canvas) >= 4.5, (selector, role, "text on canvas")
            assert mod.contrast_ratio(on_soft, soft) >= 4.5, (selector, role, "on soft")
            assert mod.contrast_ratio(on_solid, solid) >= 4.5, (selector, role, "on solid")
            assert mod.contrast_ratio(solid, surface) >= 3.0, (selector, role, "solid on surface")


def test_chart_tokens_count_and_contrast() -> None:
    mod, _, built = render()
    css = built.theme_css

    for selector in (":root", '[data-theme="dark"]'):
        tokens = css_tokens(css, selector)
        surface = tokens["--b-surface"]
        numbers = {
            int(match.group(1))
            for key in tokens
            if (match := re.match(r"--b-chart-(\d+)$", key))
        }
        assert numbers == set(range(1, 9)), selector
        values = [tokens[f"--b-chart-{index}"] for index in range(1, 9)]
        assert len(set(values)) == 8, (selector, values)
        for value in values:
            assert mod.contrast_ratio(value, surface) >= 3.0, (selector, value)


def test_dark_mode_optional() -> None:
    mod = builder()

    def build(modes: list[str]):
        data = copy.deepcopy(brand_data())
        data["design"]["theme"]["modes"] = modes
        data["design"]["theme"]["default"] = modes[0]
        model = mod._build_model(data)
        return model, mod.render_theme(data)

    light_model, light_built = build(["light"])
    assert '[data-theme="dark"]' not in light_built.theme_css
    assert "color-scheme: light" in light_built.theme_css

    dark_model, dark_built = build(["dark"])
    assert '[data-theme="dark"]' not in dark_built.theme_css
    assert "color-scheme: dark" in dark_built.theme_css
    dark_root = css_tokens(dark_built.theme_css)
    assert dark_root["--b-canvas"] == mod._semantic_tokens(dark_model, "dark")["canvas"]

    light_canvas = css_tokens(light_built.theme_css)["--b-canvas"]
    assert mod.relative_luminance(dark_root["--b-canvas"]) < mod.relative_luminance(
        light_canvas
    )

    both_model, both_built = build(["light", "dark"])
    assert "color-scheme: light" in both_built.theme_css
    assert "color-scheme: dark" in both_built.theme_css
    assert '[data-theme="dark"]' in both_built.theme_css


def test_gradient_optional() -> None:
    _, _, plain = render()
    assert "--b-gradient:" not in plain.theme_css
    assert "bg-grad-brand" not in plain.tailwind_theme_css

    _, _, gradient = render(name="luxury")
    assert "--b-gradient:" in gradient.theme_css
    assert "bg-grad-brand" in gradient.tailwind_theme_css


def test_gradient_three_stops() -> None:
    _, _, built = render(name="luxury")
    assert (
        "linear-gradient(120deg, #C6A15B 0%, #F2EBDD 50%, #6E3B52 100%)"
        in built.theme_css
    )


def test_unit_4_and_8() -> None:
    def build(unit: int) -> str:
        data = copy.deepcopy(brand_data())
        data["design"]["shape"]["unit"] = unit
        return builder().render_theme(data).theme_css

    four = build(4)
    assert "--b-unit: 4px;" in four
    assert "--b-space-1: 4px;" in four

    eight = build(8)
    assert "--b-unit: 8px;" in eight
    assert "--b-space-1: 8px;" in eight


def test_radius_profiles() -> None:
    def radius_tokens(radius: Any) -> list[str]:
        data = copy.deepcopy(brand_data())
        data["design"]["shape"]["radius"] = radius
        tokens = css_tokens(builder().render_theme(data).theme_css)
        return [tokens[f"--b-radius-{key}"] for key in ("xs", "sm", "md", "lg", "xl")]

    assert radius_tokens("sharp") == ["0px", "0px", "2px", "4px", "4px"]
    assert radius_tokens("soft") == ["4px", "8px", "12px", "16px", "24px"]
    assert radius_tokens("round") == ["8px", "12px", "16px", "24px", "9999px"]

    custom = radius_tokens({"xs": 1, "lg": 10})
    assert custom[0] == "1px"
    assert custom[3] == "10px"
    assert custom[1] == "8px"  # filled from the soft profile


def test_type_scale_has_12_steps() -> None:
    _, _, built = render()
    tokens = css_tokens(built.theme_css)

    sizes = [int(tokens[f"--b-text-{name}"].removesuffix("px")) for name in TYPE_STEP_NAMES]
    assert len(sizes) == 12
    assert sizes == sorted(sizes)
    assert len(set(sizes)) == 12
    assert sizes[2] == 16  # base
    assert sizes[3] == 20  # base * 1.25

    for name in TYPE_STEP_NAMES:
        assert f"--b-leading-{name}:" in built.theme_css


def test_tailwind_theme_maps_new_tokens() -> None:
    _, _, built = render()
    css = built.tailwind_theme_css

    for token in (
        "--color-success",
        "--color-chart-1",
        "--color-accent-soft",
        "--font-display",
        "--text-7xl",
        "--radius-xs",
        "--shadow-2",
    ):
        assert f"{token}:" in css, token


def test_build_theme_writes_files_and_refuses_overwrite() -> None:
    mod = builder()
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "theme"
        result = mod.build_theme(SAMPLE_BRAND, out)

        assert (out / "theme.css").read_text(encoding="utf-8") == result.theme_css
        assert (out / "tailwind-theme.css").read_text(
            encoding="utf-8"
        ) == result.tailwind_theme_css

        try:
            mod.build_theme(SAMPLE_BRAND, out)
        except FileExistsError:
            pass
        else:
            raise AssertionError("a second build must raise FileExistsError")

        rewritten = mod.build_theme(SAMPLE_BRAND, out, force=True)
        assert (out / "theme.css").read_text(encoding="utf-8") == rewritten.theme_css


def test_theme_is_deterministic() -> None:
    _, _, first = render(name="luxury")
    _, _, second = render(name="luxury")
    assert first.theme_css == second.theme_css
    assert first.tailwind_theme_css == second.tailwind_theme_css


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
