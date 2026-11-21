#!/usr/bin/env python3
"""Brand Engine theme builder.

Reads the approved ``brand.json`` and writes ``theme.css`` (``--b-*`` custom
properties, light and dark) plus ``tailwind-theme.css`` (semantic utility
mapping) into ``--out``.

Contract (shared with ``SKILL.md`` and consumed by ``new_page.py``)::

    build_theme(brand_path, out_dir, force=False)
        -> ThemeBuild(theme_css, tailwind_theme_css)

``theme.css`` and ``tailwind-theme.css`` are also written to ``out_dir``.
Existing files are never replaced without ``force=True`` (CLI ``--force``).

Brand discovery order (CLI): ``--brand <path>`` > ``./brand.json`` >
``./brand/brand.json`` > ask the user. The CLI prints an actionable message
and exits 2 when no brand is found, instead of raising a traceback.

brand.json schema v1
--------------------

Required keys (all strings unless noted)::

    purpose        one sentence
    persona        who the brand serves
    territory      visual territory
    archetype      brand archetype
    attributes     non-empty list of short strings, e.g. ["rustico", "direto"]
    colors         {"primary": [color, ...], "secondary": [color, ...]}
    allowed_pairs  [{"bg": "<color name>", "fg": "<color name>", "use": "..."}]
    gradient       {"from": "<color name>", "to": "<color name>", "angle": 45}
    fonts          {"display": {"family": "Fraunces", "fallback": "Georgia, serif"},
                    "body": {"family": "Source Sans 3", "fallback": "system-ui, sans-serif"}}
    scale          {"base": 16, "ratio": 1.25}
    unit           8 (the 8px grid is fixed in V1)
    logo           {"variant": "C" | "B" | "A", "name": "...", "notes": "..."}
    aceite         false until the user approves the manual

Optional keys: ``name`` (brand name), ``version`` (must be 1 when present),
``$schema`` and other metadata. A color object is::

    {"name": "Brasa", "hex": "#A6402F", "note": "optional"}

``--b-color-<slug>`` keeps the approved hex for every named color. Semantic
tokens (``--b-primary``, ``--b-fg``, ...) may shift slightly to meet WCAG
contrast; the gradient always uses the approved hex pair.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, NamedTuple

THEME_FILE = "theme.css"
TAILWIND_FILE = "tailwind-theme.css"

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
TEMPLATE_FILE = ASSETS_DIR / "theme-template.css"

UNIT_PX = 8
GRADIENT_ANGLE = 45

TYPE_STEPS: tuple[tuple[str, int], ...] = (
    ("xs", -2),
    ("sm", -1),
    ("base", 0),
    ("lg", 1),
    ("xl", 2),
    ("2xl", 3),
    ("3xl", 4),
    ("4xl", 5),
    ("5xl", 6),
    ("6xl", 7),
)

SEMANTIC_COLOR_KEYS: tuple[str, ...] = (
    "canvas",
    "surface",
    "surface-muted",
    "surface-raised",
    "band",
    "on-band",
    "on-band-muted",
    "band-accent",
    "fg",
    "fg-muted",
    "fg-subtle",
    "fg-disabled",
    "line",
    "line-strong",
    "line-input",
    "primary",
    "primary-hover",
    "on-primary",
    "primary-soft",
    "on-primary-soft",
    "accent",
    "link",
    "focus",
    "highlight",
    "on-highlight",
)

_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


class BrandError(ValueError):
    """A malformed or incomplete brand.json, or an unusable --brand path."""


class ThemeBuild(NamedTuple):
    """The two generated stylesheets (also written to ``out_dir``)."""

    theme_css: str
    tailwind_theme_css: str


@dataclass(frozen=True)
class _Color:
    name: str
    hex: str
    slug: str
    group: str


@dataclass(frozen=True)
class _Model:
    name: str
    purpose: str
    colors: tuple[_Color, ...]
    lookup: dict[str, _Color]
    pairs: tuple[tuple[_Color, _Color, str], ...]
    gradient_from: _Color
    gradient_to: _Color
    display_stack: str
    body_stack: str
    scale: tuple[tuple[str, int, float], ...]
    unit: int


# ---------------------------------------------------------------------------
# Colour maths (WCAG 2.x)
# ---------------------------------------------------------------------------


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    return int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)


def _rgb_to_hex(rgb: Iterable[float]) -> str:
    channels = [min(255, max(0, int(round(channel)))) for channel in rgb]
    return "#{:02X}{:02X}{:02X}".format(*channels)


def mix(color_a: str, color_b: str, amount: float) -> str:
    """Mix two hex colours in sRGB. ``amount=0`` returns ``color_a``."""

    ratio = min(1.0, max(0.0, amount))
    a_r, a_g, a_b = _hex_to_rgb(color_a)
    b_r, b_g, b_b = _hex_to_rgb(color_b)
    return _rgb_to_hex(
        (
            a_r + (b_r - a_r) * ratio,
            a_g + (b_g - a_g) * ratio,
            a_b + (b_b - a_b) * ratio,
        )
    )


def _linear_channel(channel: int) -> float:
    value = channel / 255
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def relative_luminance(color: str) -> float:
    red, green, blue = _hex_to_rgb(color)
    return (
        0.2126 * _linear_channel(red)
        + 0.7152 * _linear_channel(green)
        + 0.0722 * _linear_channel(blue)
    )


def contrast_ratio(foreground: str, background: str) -> float:
    """WCAG contrast ratio between two hex colours (1.0 to 21.0)."""

    first = relative_luminance(foreground)
    second = relative_luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def ensure_contrast(foreground: str, background: str, minimum: float = 4.5) -> str:
    """Return ``foreground`` or the nearest black/white mix that reaches ``minimum``."""

    if contrast_ratio(foreground, background) >= minimum:
        return foreground.upper()

    target = "#000000" if relative_luminance(background) > 0.18 else "#FFFFFF"
    for step in range(1, 21):
        candidate = mix(foreground, target, step / 20)
        if contrast_ratio(candidate, background) >= minimum:
            return candidate
    return target


def _on_color(background: str) -> str:
    """Pick a readable foreground for a filled colour (buttons, badges)."""

    dark = ensure_contrast("#141110", background, 4.5)
    light = ensure_contrast("#FFFFFF", background, 4.5)
    return max((dark, light), key=lambda candidate: contrast_ratio(candidate, background))


def _first_with_contrast(candidates: Iterable[str], background: str, minimum: float) -> str:
    options = list(candidates)
    for candidate in options:
        if contrast_ratio(candidate, background) >= minimum:
            return candidate
    return ensure_contrast(options[0], background, minimum)


# ---------------------------------------------------------------------------
# Input parsing and validation
# ---------------------------------------------------------------------------


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BrandError(f"brand.json: {field} must be a non-empty string")
    return value.strip()


def _number(value: Any, field: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BrandError(f"brand.json: {field} must be a number")
    if not minimum <= float(value) <= maximum:
        raise BrandError(f"brand.json: {field} must be between {minimum:g} and {maximum:g}")
    return float(value)


def _hex(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _HEX_RE.match(value):
        raise BrandError(
            f"brand.json: {field} must be a 6-digit hex colour such as #A6402F "
            f"(got {value!r})"
        )
    return value.upper()


def _slug(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "color"


def _parse_colors(brand: dict[str, Any]) -> tuple[_Color, ...]:
    block = brand.get("colors")
    if not isinstance(block, dict):
        raise BrandError("brand.json: colors must be an object with primary and secondary lists")

    colors: list[_Color] = []
    seen_names: dict[str, str] = {}
    seen_slugs: dict[str, str] = {}

    for group in ("primary", "secondary"):
        items = block.get(group)
        if not isinstance(items, list) or not items:
            raise BrandError(f"brand.json: colors.{group} must be a non-empty list")
        for index, item in enumerate(items):
            field = f"colors.{group}[{index}]"
            if not isinstance(item, dict):
                raise BrandError(f"brand.json: {field} must be an object with name and hex")
            name = _text(item.get("name"), f"{field}.name")
            hex_value = _hex(item.get("hex"), f"{field}.hex")
            key = name.casefold()
            if key in seen_names:
                raise BrandError(
                    f"brand.json: duplicate colour name {name!r} "
                    f"(already used by {seen_names[key]})"
                )
            slug = _slug(name)
            if slug in seen_slugs:
                raise BrandError(
                    f"brand.json: colour names {seen_slugs[slug]!r} and {name!r} "
                    "produce the same CSS token"
                )
            note = item.get("note")
            if note is not None and not isinstance(note, str):
                raise BrandError(f"brand.json: {field}.note must be a string when present")
            seen_names[key] = field
            seen_slugs[slug] = name
            colors.append(_Color(name=name, hex=hex_value, slug=slug, group=group))

    if not any(color.group == "primary" for color in colors):
        raise BrandError("brand.json: colors.primary needs at least one colour")
    return tuple(colors)


def _color_index(colors: Iterable[_Color]) -> dict[str, _Color]:
    index: dict[str, _Color] = {}
    for color in colors:
        index[color.name.casefold()] = color
        index[color.slug] = color
    return index


def _lookup_color(index: dict[str, _Color], reference: Any, field: str) -> _Color:
    name = _text(reference, field)
    color = index.get(name.casefold()) or index.get(_slug(name))
    if color is None:
        known = ", ".join(sorted({item.name for item in index.values()}))
        raise BrandError(
            f"brand.json: {field} references unknown colour {name!r} "
            f"(known colours: {known})"
        )
    return color


def _parse_pairs(
    brand: dict[str, Any], index: dict[str, _Color]
) -> tuple[tuple[_Color, _Color, str], ...]:
    pairs = brand.get("allowed_pairs")
    if not isinstance(pairs, list) or not pairs:
        raise BrandError("brand.json: allowed_pairs must be a non-empty list")

    result: list[tuple[_Color, _Color, str]] = []
    for position, pair in enumerate(pairs):
        field = f"allowed_pairs[{position}]"
        if not isinstance(pair, dict):
            raise BrandError(f"brand.json: {field} must be an object with bg and fg")
        background = _lookup_color(index, pair.get("bg"), f"{field}.bg")
        foreground = _lookup_color(index, pair.get("fg"), f"{field}.fg")
        use = pair.get("use", "")
        if use is not None and not isinstance(use, str):
            raise BrandError(f"brand.json: {field}.use must be a string when present")
        result.append((background, foreground, (use or "").strip()))
    return tuple(result)


def _parse_gradient(
    brand: dict[str, Any], index: dict[str, _Color]
) -> tuple[_Color, _Color]:
    gradient = brand.get("gradient")
    if not isinstance(gradient, dict):
        raise BrandError("brand.json: gradient must be an object with from, to and angle")

    start = _lookup_color(index, gradient.get("from"), "gradient.from")
    end = _lookup_color(index, gradient.get("to"), "gradient.to")

    angle = gradient.get("angle")
    if isinstance(angle, bool) or not isinstance(angle, (int, float)):
        raise BrandError("brand.json: gradient.angle must be 45")
    if float(angle) != float(GRADIENT_ANGLE):
        raise BrandError(
            "brand.json: gradient.angle must be 45 "
            "(V1 allows only the two-stop 50/50 gradient at 45 degrees)"
        )
    if start.hex == end.hex:
        raise BrandError("brand.json: gradient.from and gradient.to must be different colours")
    return start, end


def _parse_fonts(brand: dict[str, Any]) -> tuple[str, str]:
    fonts = brand.get("fonts")
    if not isinstance(fonts, dict):
        raise BrandError("brand.json: fonts must be an object with display and body")

    stacks: list[str] = []
    for role, default_fallback in (("display", "serif"), ("body", "sans-serif")):
        field = f"fonts.{role}"
        spec = fonts.get(role)
        if not isinstance(spec, dict):
            raise BrandError(
                f"brand.json: {field} must be an object with family and optional fallback"
            )
        family = _text(spec.get("family"), f"{field}.family").strip('"').strip("'")
        if "," in family or '"' in family:
            raise BrandError(f"brand.json: {field}.family must be a single font family name")
        fallback = _text(spec.get("fallback", default_fallback), f"{field}.fallback")
        stacks.append(f'"{family}", {fallback}')
    return stacks[0], stacks[1]


def _type_scale(brand: dict[str, Any]) -> tuple[tuple[str, int, float], ...]:
    scale = brand.get("scale")
    if not isinstance(scale, dict):
        raise BrandError("brand.json: scale must be an object with base and ratio")
    base = _number(scale.get("base"), "scale.base", 12, 32)
    ratio = _number(scale.get("ratio"), "scale.ratio", 1.05, 1.8)

    steps: list[tuple[str, int, float]] = []
    for name, exponent in TYPE_STEPS:
        size = int(round(base * (ratio**exponent)))
        if exponent <= 0:
            leading = 1.6
        else:
            leading = max(1.05, 1.6 - 0.07 * exponent)
        steps.append((name, size, round(leading, 2)))
    return tuple(steps)


def _build_model(brand: Any) -> _Model:
    if not isinstance(brand, dict):
        raise BrandError("brand.json: top level must be a JSON object")

    version = brand.get("version", 1)
    if isinstance(version, bool) or version != 1:
        raise BrandError("brand.json: version must be 1")

    name = "Brand"
    if brand.get("name") is not None:
        name = _text(brand.get("name"), "name")
    purpose = _text(brand.get("purpose"), "purpose")
    for key in ("persona", "territory", "archetype"):
        _text(brand.get(key), key)

    attributes = brand.get("attributes")
    if not isinstance(attributes, list) or not attributes:
        raise BrandError("brand.json: attributes must be a non-empty list of strings")
    for position, attribute in enumerate(attributes):
        _text(attribute, f"attributes[{position}]")

    colors = _parse_colors(brand)
    index = _color_index(colors)
    pairs = _parse_pairs(brand, index)
    gradient_from, gradient_to = _parse_gradient(brand, index)
    display_stack, body_stack = _parse_fonts(brand)
    scale = _type_scale(brand)

    unit = brand.get("unit")
    if isinstance(unit, bool) or not isinstance(unit, (int, float)) or float(unit) != UNIT_PX:
        raise BrandError("brand.json: unit must be 8 (the 8px grid is fixed in V1)")

    logo = brand.get("logo")
    if not isinstance(logo, dict):
        raise BrandError("brand.json: logo must be an object with a variant")
    if logo.get("variant") not in ("C", "B", "A"):
        raise BrandError("brand.json: logo.variant must be C, B or A")
    if logo.get("name") is not None:
        _text(logo.get("name"), "logo.name")
    if logo.get("notes") is not None and not isinstance(logo.get("notes"), str):
        raise BrandError("brand.json: logo.notes must be a string when present")

    if not isinstance(brand.get("aceite"), bool):
        raise BrandError("brand.json: aceite must be true or false (manual approval flag)")

    return _Model(
        name=name,
        purpose=purpose,
        colors=colors,
        lookup=index,
        pairs=pairs,
        gradient_from=gradient_from,
        gradient_to=gradient_to,
        display_stack=display_stack,
        body_stack=body_stack,
        scale=scale,
        unit=UNIT_PX,
    )


# ---------------------------------------------------------------------------
# Semantic tokens
# ---------------------------------------------------------------------------


def _semantic_tokens(model: _Model, mode: str) -> dict[str, str]:
    if mode not in ("light", "dark"):
        raise ValueError(f"unknown theme mode: {mode}")

    primary_source = next(color.hex for color in model.colors if color.group == "primary")
    secondary_sources = [color.hex for color in model.colors if color.group == "secondary"]

    if mode == "light":
        canvas = mix("#FFFFFF", primary_source, 0.04)
        surface = "#FFFFFF"
        surface_muted = mix("#FFFFFF", primary_source, 0.08)
        surface_raised = "#FFFFFF"
        band = mix("#141110", primary_source, 0.32)
        fg = ensure_contrast(mix("#171310", primary_source, 0.10), canvas, 7.0)
        primary = ensure_contrast(primary_source, canvas, 3.0)
        primary_hover = mix(primary, "#000000", 0.12)
        primary_soft = mix(canvas, primary_source, 0.14)
    else:
        canvas = mix("#121110", primary_source, 0.06)
        surface = mix("#1A1816", primary_source, 0.06)
        surface_muted = mix("#221F1C", primary_source, 0.08)
        surface_raised = mix("#27231F", primary_source, 0.08)
        band = mix("#0C0B0A", primary_source, 0.30)
        fg = ensure_contrast(mix("#F7F3ED", primary_source, 0.08), canvas, 7.0)
        primary = ensure_contrast(primary_source, canvas, 3.0)
        primary_hover = mix(primary, "#FFFFFF", 0.12)
        primary_soft = mix(canvas, primary_source, 0.24)

    accent_source = max(secondary_sources, key=lambda value: contrast_ratio(value, surface))
    if mode == "light":
        highlight = mix("#FFFFFF", accent_source, 0.22)
        on_highlight = ensure_contrast("#141110", highlight, 4.5)
    else:
        highlight = mix("#121110", accent_source, 0.38)
        on_highlight = ensure_contrast("#FFFFFF", highlight, 4.5)

    accent = ensure_contrast(accent_source, surface, 4.5)
    link = ensure_contrast(primary_source, surface, 4.5)
    focus = ensure_contrast(accent_source, surface, 3.0)
    on_primary = _on_color(primary)
    on_primary_soft = ensure_contrast(primary_source, primary_soft, 4.5)
    on_band = ensure_contrast("#FFFFFF", band, 4.5)
    on_band_muted = ensure_contrast(mix(on_band, band, 0.25), band, 4.5)
    band_accent = _first_with_contrast((accent, highlight, "#FFFFFF"), band, 4.5)

    tokens = {
        "canvas": canvas,
        "surface": surface,
        "surface-muted": surface_muted,
        "surface-raised": surface_raised,
        "band": band,
        "on-band": on_band,
        "on-band-muted": on_band_muted,
        "band-accent": band_accent,
        "fg": fg,
        "fg-muted": ensure_contrast(mix(fg, canvas, 0.30), canvas, 4.5),
        "fg-subtle": ensure_contrast(mix(fg, canvas, 0.42), canvas, 4.5),
        "fg-disabled": mix(fg, canvas, 0.62),
        "line": mix(canvas, fg, 0.12),
        "line-strong": mix(canvas, fg, 0.24),
        "line-input": ensure_contrast(mix(canvas, fg, 0.45), surface, 3.0),
        "primary": primary,
        "primary-hover": primary_hover,
        "on-primary": on_primary,
        "primary-soft": primary_soft,
        "on-primary-soft": on_primary_soft,
        "accent": accent,
        "link": link,
        "focus": focus,
        "highlight": highlight,
        "on-highlight": on_highlight,
    }
    if set(tokens) != set(SEMANTIC_COLOR_KEYS):
        raise RuntimeError("semantic token set drifted from SEMANTIC_COLOR_KEYS")
    return tokens


# ---------------------------------------------------------------------------
# CSS rendering
# ---------------------------------------------------------------------------


def _comment(text: Any) -> str:
    return " ".join(str(text).split()).replace("*/", "* /")


def _declarations(tokens: dict[str, str]) -> list[str]:
    return [f"  --b-{key}: {value};" for key, value in tokens.items()]


def _theme_css(model: _Model, light: dict[str, str], dark: dict[str, str]) -> str:
    header = "\n".join(
        (
            "/* Brand Engine · theme.css — generated by scripts/build_theme.py from brand.json.",
            "   Do not edit by hand; change brand.json and regenerate.",
            f"   Brand: {_comment(model.name)}",
            f"   Purpose: {_comment(model.purpose)}",
            "   --b-color-* keeps the approved hex; semantic tokens may shift for contrast.",
            "   Gradient rule: exactly two stops at 50/50, 45deg. */",
        )
    )

    root: list[str] = [":root {", "  color-scheme: light;", "", "  /* Brand palette — approved hex, theme invariant */"]
    root.extend(
        f"  --b-color-{color.slug}: {color.hex}; /* {_comment(color.name)} · {color.group} */"
        for color in model.colors
    )
    root.extend(("", "  /* Type — display for headlines, body for reading. */"))
    root.append("  /* Scale: size = base * ratio^n; leading = 1.6 - 0.07n (floor 1.05). */")
    root.append(f"  --b-display: {model.display_stack};")
    root.append(f"  --b-body: {model.body_stack};")
    for name, size, leading in model.scale:
        root.append(f"  --b-text-{name}: {size}px;")
        root.append(f"  --b-leading-{name}: {leading:g};")

    root.extend(("", f"  /* Spacing — multiples of the {model.unit}px unit */"))
    root.append(f"  --b-unit: {model.unit}px;")
    for step in range(0, 17):
        root.append(f"  --b-space-{step}: {step * model.unit}px;")

    root.extend(("", "  /* Radius — derived from the unit */"))
    root.append(f"  --b-radius-sm: {model.unit // 2}px;")
    root.append(f"  --b-radius-md: {model.unit}px;")
    root.append(f"  --b-radius-lg: {model.unit * 2}px;")
    root.append(f"  --b-radius-xl: {model.unit * 3}px;")
    root.append("  --b-radius-full: 9999px;")

    root.extend(
        (
            "",
            "  /* Brand expression — the only allowed gradient */",
            f"  --b-gradient: linear-gradient({GRADIENT_ANGLE}deg, "
            f"{model.gradient_from.hex} 50%, {model.gradient_to.hex} 50%);",
            "",
            "  /* Semantic tokens — light */",
        )
    )
    root.extend(_declarations(light))
    root.append("}")

    pair_lines = ["", "/* Allowed color pairs from brand.json (WCAG contrast checked at build time)."]
    for background, foreground, use in model.pairs:
        ratio = contrast_ratio(foreground.hex, background.hex)
        verdict = "AA" if ratio >= 4.5 else ("AA-large" if ratio >= 3.0 else "FAIL-AA")
        suffix = f" · {_comment(use)}" if use else ""
        pair_lines.append(
            f" * {_comment(foreground.name)} on {_comment(background.name)} — "
            f"{ratio:.2f}:1 ({verdict}){suffix}"
        )
    pair_lines.append(" */")

    dark_lines = ["", '[data-theme="dark"] {', "  color-scheme: dark;", "", "  /* Semantic tokens — dark */"]
    dark_lines.extend(_declarations(dark))
    dark_lines.append("}")

    tokens_block = "\n".join(root + pair_lines + dark_lines)

    template = TEMPLATE_FILE.read_text(encoding="utf-8")
    if "{{BRAND_HEADER}}" not in template or "{{BRAND_TOKENS}}" not in template:
        raise BrandError(f"theme template is missing placeholders: {TEMPLATE_FILE}")
    return template.replace("{{BRAND_HEADER}}", header).replace("{{BRAND_TOKENS}}", tokens_block)


def _tailwind_css(model: _Model) -> str:
    lines = [
        "/* Brand Engine · tailwind-theme.css — generated by scripts/build_theme.py.",
        "   Load inside <style type=\"text/tailwindcss\">. Colors point at --b-* tokens,",
        "   so bg-surface and text-fg-muted switch with the theme automatically.",
        "   Semantic utilities only: bg-surface, text-fg-muted, border-line, bg-primary,",
        "   text-on-primary, text-accent, bg-highlight, bg-grad-brand.",
        "   Never use palette utilities such as bg-blue-600 or a bare hex in content. */",
        "",
        "@custom-variant dark (&:where([data-theme=dark], [data-theme=dark] *));",
        "",
        "@theme inline {",
        "  --font-sans: var(--b-body);",
        "  --font-display: var(--b-display);",
        "",
        "  /* Semantic colors */",
    ]
    lines.extend(f"  --color-{key}: var(--b-{key});" for key in SEMANTIC_COLOR_KEYS)
    lines.extend(
        (
            "}",
            "",
            "@theme {",
            f"  --spacing: {model.unit}px;",
            "",
            "  /* Type scale — sizes and coupled line-heights from brand.json */",
        )
    )
    for name, size, leading in model.scale:
        lines.append(f"  --text-{name}: {size}px;")
        lines.append(f"  --text-{name}--line-height: {leading:g};")
    lines.extend(("", "  /* Radius */"))
    lines.append(f"  --radius-sm: {model.unit // 2}px;")
    lines.append(f"  --radius-md: {model.unit}px;")
    lines.append(f"  --radius-lg: {model.unit * 2}px;")
    lines.append(f"  --radius-xl: {model.unit * 3}px;")
    lines.append("  --radius-full: 9999px;")
    lines.extend(
        (
            "}",
            "",
            "/* The only allowed gradient: two stops, 50/50, 45deg. */",
            "@utility bg-grad-brand { background-image: var(--b-gradient); }",
        )
    )
    return "\n".join(lines) + "\n"


def render_theme(brand: dict[str, Any]) -> ThemeBuild:
    """Render both stylesheets from an already parsed brand object."""

    model = _build_model(brand)
    light = _semantic_tokens(model, "light")
    dark = _semantic_tokens(model, "dark")
    return ThemeBuild(
        theme_css=_theme_css(model, light, dark),
        tailwind_theme_css=_tailwind_css(model),
    )


# ---------------------------------------------------------------------------
# Public API and CLI
# ---------------------------------------------------------------------------


def _read_brand(brand_path: str | Path) -> dict[str, Any]:
    path = Path(brand_path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BrandError(f"{path}: cannot read brand.json ({exc})") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise BrandError(
            f"{path}: invalid JSON at line {exc.lineno} column {exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(data, dict):
        raise BrandError(f"{path}: brand.json must contain a JSON object")
    return data


def load_brand(brand_path: str | Path) -> dict[str, Any]:
    """Read and validate brand.json, returning the raw object for other scripts."""

    data = _read_brand(brand_path)
    _build_model(data)
    return data


def resolve_brand_path(
    brand_flag: str | Path | None = None, cwd: str | Path | None = None
) -> Path | None:
    """Resolve the brand source: flag > ./brand.json > ./brand/brand.json > None.

    ``None`` means the caller must ask the user for a path or run discovery.
    """

    base = Path(cwd) if cwd is not None else Path.cwd()
    if brand_flag:
        candidate = Path(brand_flag).expanduser()
        if not candidate.is_absolute():
            candidate = base / candidate
        if not candidate.is_file():
            raise BrandError(f"{candidate}: brand file not found (--brand path)")
        return candidate

    for candidate in (base / "brand.json", base / "brand" / "brand.json"):
        if candidate.is_file():
            return candidate
    return None


def missing_brand_behavior() -> str:
    """The contract for a missing brand: ask for a path or run discovery."""

    return "ask-for-path-or-discovery"


def build_theme(
    brand_path: str | Path, out_dir: str | Path, force: bool = False
) -> ThemeBuild:
    """Build and write ``theme.css`` and ``tailwind-theme.css`` into ``out_dir``."""

    data = _read_brand(brand_path)
    result = render_theme(data)

    out = Path(out_dir)
    if out.exists() and not out.is_dir():
        raise BrandError(f"{out}: --out must be a directory")
    out.mkdir(parents=True, exist_ok=True)

    targets = (out / THEME_FILE, out / TAILWIND_FILE)
    if not force:
        existing = [str(target) for target in targets if target.exists()]
        if existing:
            raise FileExistsError(
                f"refusing to overwrite {', '.join(existing)} without --force"
            )

    targets[0].write_text(result.theme_css, encoding="utf-8")
    targets[1].write_text(result.tailwind_theme_css, encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build theme.css and tailwind-theme.css from brand.json."
    )
    parser.add_argument("--brand", help="path to brand.json (flag wins over discovery)")
    parser.add_argument("--out", default=".", help="output directory (default: .)")
    parser.add_argument("--force", action="store_true", help="replace existing output files")
    args = parser.parse_args(argv)

    try:
        brand_path = resolve_brand_path(args.brand)
        if brand_path is None:
            print(
                "No brand.json found. Pass --brand <path>, create ./brand.json, "
                "or run discovery first (see SKILL.md, Phase 0).",
                file=sys.stderr,
            )
            return 2
        build_theme(brand_path, args.out, force=args.force)
    except (BrandError, FileExistsError, OSError) as exc:
        print(f"build_theme: {exc}", file=sys.stderr)
        return 2

    out = Path(args.out)
    print(f"wrote {out / THEME_FILE} and {out / TAILWIND_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
