#!/usr/bin/env python3
"""Brand Engine brand model (schema v2).

Reads and validates the approved ``brand.json`` v2. This module is the single
source of truth for the brand contract: every other script (theme builder,
page generator, checker) consumes ``load_brand``/``_build_model`` instead of
re-parsing JSON.

Contract (schema v2, the final one -- there is no v1 compatibility)::

    {
      "version": 2,
      "name": "...",                     # optional, defaults to "Brand"
      "language": "pt-BR",               # optional BCP-47 tag, defaults to pt-BR
      "purpose": "...",                  # required
      "persona": "...",                  # required
      "territory": "...",                # required
      "archetype": "...",                # required
      "attributes": ["...", ...],        # required, non-empty
      "voice": {                         # optional, see DEFAULT_VOICE
        "summary": "...", "principles": ["..."], "avoid": ["..."],
        "person": "você", "emoji": "none" | "social-only"
      },
      "design": {
        "colors": {                      # canvas, surface, ink, primary required
          "canvas": {"name": "...", "hex": "#RRGGBB", "note": "..."},
          "surface": {...}, "ink": {...}, "primary": {...},
          "accent": {...},               # optional
          "support": [{...}, ...]        # optional
        },
        "feedback": "auto" | {"success": "#RRGGBB", ...},
        "charts": "auto" | ["#RRGGBB", ...],
        "type": {
          "display": {"family": "...", "fallback": "...", "weight": 600,
                      "tracking": "normal", "case": "none"},
          "body": {...},
          "scale": {"base": 16, "ratio": 1.25}
        },
        "shape": {"radius": "soft" | {...}, "unit": 8, "shadows": "soft"},
        "theme": {"modes": ["light", "dark"], "default": "light",
                  "gradient": null | {"from": "...", "to": "...",
                                      "angle": 45, "via": "..."}},
        "icons": {"family": "fluent", "size": 16},
        "imagery": {"mode": "abstract", "treatment": "..."},
        "composition": {"direction": "structured", "measure": "65ch", "grid": "12"},
        "logo": {"variant": "C", "name": "...", "notes": "..."}
      },
      "aceite": false                    # manual approval flag
    }

``version: 1``, ``colors.primary``/``colors.secondary`` lists, ``allowed_pairs``
and a fixed ``unit: 8`` are rejected on purpose: the v2 schema is the final
contract.

Brand discovery order (CLI): ``--brand <path>`` > ``./brand.json`` >
``./brand/brand.json`` > ask the user. A missing brand never raises a
traceback: callers use :func:`resolve_brand_path` and
:func:`missing_brand_behavior`.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, NamedTuple

# ---------------------------------------------------------------------------
# Contract constants
# ---------------------------------------------------------------------------

REQUIRED_COLOR_ROLES: tuple[str, ...] = ("canvas", "surface", "ink", "primary")
OPTIONAL_COLOR_ROLES: tuple[str, ...] = ("accent", "support")
FEEDBACK_ROLES: tuple[str, ...] = ("success", "warning", "danger", "info")
THEME_MODES: tuple[str, ...] = ("light", "dark")
SHADOWS: tuple[str, ...] = ("none", "soft", "strong")
ICON_FAMILIES: tuple[str, ...] = ("fluent", "lucide", "phosphor", "tabler")
IMAGERY_MODES: tuple[str, ...] = ("photo", "illustration", "abstract", "none")
COMPOSITION_DIRECTIONS: tuple[str, ...] = ("editorial", "structured", "poster", "minimal")
LOGO_VARIANTS: tuple[str, ...] = ("C", "B", "A")
TEXT_CASES: tuple[str, ...] = ("none", "uppercase", "lowercase", "capitalize")
VOICE_EMOJI: tuple[str, ...] = ("none", "social-only")

DESIGN_KEYS: tuple[str, ...] = (
    "colors",
    "feedback",
    "charts",
    "type",
    "shape",
    "theme",
    "icons",
    "imagery",
    "composition",
    "logo",
)

# Top-level keys from the v1 schema. They are rejected explicitly so a stale
# brand.json fails loudly instead of being silently ignored.
V1_TOP_LEVEL_KEYS: tuple[str, ...] = (
    "colors",
    "allowed_pairs",
    "gradient",
    "fonts",
    "scale",
    "unit",
    "logo",
)

# Radius profiles: xs, sm, md, lg, xl (+ full). The defaults in the builder
# mirror the design spec: sharp 0/0/2/4/4, soft 4/8/12/16/24, round
# 8/12/16/24/9999.
RADIUS_PROFILES: dict[str, dict[str, float]] = {
    "sharp": {"xs": 0, "sm": 0, "md": 2, "lg": 4, "xl": 4, "full": 9999},
    "soft": {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24, "full": 9999},
    "round": {"xs": 8, "sm": 12, "md": 16, "lg": 24, "xl": 9999, "full": 9999},
}
RADIUS_KEYS: tuple[str, ...] = ("xs", "sm", "md", "lg", "xl", "full")

DEFAULT_UNIT = 8
DEFAULT_RADIUS = "soft"
DEFAULT_SHADOWS = "soft"
DEFAULT_MODES: tuple[str, ...] = ("light", "dark")
DEFAULT_TYPE_FAMILY = "system-ui"
DEFAULT_SCALE = (16.0, 1.25)
DEFAULT_ICONS: dict[str, Any] = {"family": "fluent", "size": 16}
DEFAULT_IMAGERY: dict[str, Any] = {
    "mode": "abstract",
    "treatment": "",
}
DEFAULT_COMPOSITION: dict[str, Any] = {
    "direction": "structured",
    "measure": "65ch",
    "grid": "12",
}
DEFAULT_LOGO: dict[str, str] = {"variant": "C", "name": "", "notes": ""}
DEFAULT_VOICE_SUMMARY = "[placeholder — resumo da voz]"

THEME_FILE = "theme.css"
TAILWIND_FILE = "tailwind-theme.css"

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
TEMPLATE_FILE = ASSETS_DIR / "theme-template.css"

# Twelve steps: xs..8xl. 4xl/5xl cover hero and deck headlines. The size is
# ``base * ratio**exponent``; leading shrinks as the size grows (floor 1.05).
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
    ("7xl", 8),
    ("8xl", 9),
)

# Feedback anchors: functional hues that are readable on light surfaces. Every
# token derived from them is re-checked against the brand surfaces.
FEEDBACK_ANCHORS: dict[str, str] = {
    "success": "#1E7A3C",
    "warning": "#B26A00",
    "danger": "#B3261E",
    "info": "#0B6E99",
}

# Chart anchors: eight distinguishable hues (data, not text; 3:1 vs surface).
CHART_ANCHORS: tuple[str, ...] = (
    "#0B6E99",
    "#B26A00",
    "#1E7A3C",
    "#B3261E",
    "#6A4C93",
    "#0F7C7B",
    "#8A5A2B",
    "#4B6A88",
)

SHADOW_SCALES: dict[str, tuple[str, str, str]] = {
    "none": ("none", "none", "none"),
    "soft": (
        "0 1px 2px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.08)",
        "0 4px 8px rgba(0, 0, 0, 0.08), 0 2px 4px rgba(0, 0, 0, 0.06)",
        "0 12px 24px rgba(0, 0, 0, 0.12), 0 4px 8px rgba(0, 0, 0, 0.08)",
    ),
    "strong": (
        "0 1px 2px rgba(0, 0, 0, 0.16), 0 2px 4px rgba(0, 0, 0, 0.14)",
        "0 6px 12px rgba(0, 0, 0, 0.18), 0 3px 6px rgba(0, 0, 0, 0.12)",
        "0 16px 32px rgba(0, 0, 0, 0.22), 0 6px 12px rgba(0, 0, 0, 0.14)",
    ),
}

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
    "accent-soft",
    "on-accent",
    "link",
    "focus",
    "highlight",
    "on-highlight",
) + tuple(
    key
    for role in FEEDBACK_ROLES
    for key in (role, f"{role}-soft", f"{role}-solid", f"on-{role}", f"on-{role}-soft")
) + tuple(f"chart-{index}" for index in range(1, 9))

_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
# Deliberately permissive BCP-47 shape: language (2-3 letters) plus optional
# alphanumeric subtags. The exact registry is not the skill's job.
_LANGUAGE_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{1,8})*$")
DEFAULT_LANGUAGE = "pt-BR"


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
    role: str
    note: str


@dataclass(frozen=True)
class _Model:
    """Validated brand.json v2, ready for the theme builder and generators.

    ``tracking`` and ``case`` are ``(display, body)`` tuples; ``scale`` is
    ``(base, ratio)``. ``feedback`` is ``"auto"`` or a ``{role: hex}`` dict.
    ``charts`` is ``"auto"`` or a tuple of hex strings. ``radius`` is a
    normalized dict with ``xs/sm/md/lg/xl/full`` keys.
    """

    name: str
    language: str
    purpose: str
    persona: str
    territory: str
    archetype: str
    attributes: tuple[str, ...]
    voice: dict[str, Any]
    colors: tuple[_Color, ...]
    lookup: dict[str, _Color]
    feedback: Any
    charts: Any
    display_stack: str
    body_stack: str
    display_weight: int
    body_weight: int
    tracking: tuple[str, str]
    case: tuple[str, str]
    scale: tuple[float, float]
    radius: dict[str, float]
    unit: int
    shadows: str
    modes: tuple[str, ...]
    default_mode: str
    gradient: dict[str, Any] | None
    icons: dict[str, Any]
    imagery: dict[str, Any]
    composition: dict[str, Any]
    logo: dict[str, str]


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


def ensure_background_contrast(
    foreground: str, background: str, minimum: float = 4.5
) -> str:
    """Shift a background away from ``foreground`` until the pair reaches ``minimum``.

    Used for hover fills: the same ``on-primary`` foreground must stay readable
    when the button background moves to ``primary-hover``.
    """

    if contrast_ratio(foreground, background) >= minimum:
        return background.upper()

    target = "#FFFFFF" if relative_luminance(foreground) < 0.18 else "#000000"
    for step in range(1, 21):
        candidate = mix(background, target, step / 20)
        if contrast_ratio(foreground, candidate) >= minimum:
            return candidate
    return target


def _ensure_contrast_all(
    foreground: str, backgrounds: Iterable[str], minimum: float = 4.5
) -> str:
    """Ensure one foreground clears ``minimum`` against every background."""

    color = foreground.upper()
    options = tuple(backgrounds)
    for _ in range(5):
        worst = min(options, key=lambda background: contrast_ratio(color, background))
        if contrast_ratio(color, worst) >= minimum:
            return color
        color = ensure_contrast(color, worst, minimum)
    return color


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
# Primitive validators
# ---------------------------------------------------------------------------


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BrandError(f"brand.json: {field} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise BrandError(f"brand.json: {field} must be a list of strings")
    return [_text(item, f"{field}[{index}]") for index, item in enumerate(value)]


def _number(value: Any, field: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BrandError(f"brand.json: {field} must be a number")
    if not minimum <= float(value) <= maximum:
        raise BrandError(f"brand.json: {field} must be between {minimum:g} and {maximum:g}")
    return float(value)


def _integer(value: Any, field: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise BrandError(f"brand.json: {field} must be an integer")
    if not minimum <= value <= maximum:
        raise BrandError(f"brand.json: {field} must be between {minimum} and {maximum}")
    return value


def _hex(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _HEX_RE.match(value):
        raise BrandError(
            f"brand.json: {field} must be a 6-digit hex colour (#RRGGBB) "
            f"such as #A6402F (got {value!r})"
        )
    return value.upper()


def _slug(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "color"


def _object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BrandError(f"brand.json: {field} must be an object")
    return value


def _reject_unknown(block: dict[str, Any], field: str, allowed: Iterable[str]) -> None:
    unknown = sorted(set(block) - set(allowed))
    if unknown:
        raise BrandError(
            f"brand.json: {field} has unknown key(s) {', '.join(unknown)} "
            f"(allowed: {', '.join(allowed)})"
        )


def _choice(value: Any, field: str, options: Iterable[str]) -> str:
    options = tuple(options)
    if value not in options:
        raise BrandError(
            f"brand.json: {field} must be one of {', '.join(options)} (got {value!r})"
        )
    return value


# ---------------------------------------------------------------------------
# Colour parsing
# ---------------------------------------------------------------------------


def _parse_color_role(value: Any, field: str, role: str) -> _Color:
    spec = _object(value, field)
    _reject_unknown(spec, field, ("name", "hex", "note"))
    name = _text(spec.get("name"), f"{field}.name")
    note = spec.get("note", "")
    if note is None:
        note = ""
    if not isinstance(note, str):
        raise BrandError(f"brand.json: {field}.note must be a string when present")
    return _Color(
        name=name,
        hex=_hex(spec.get("hex"), f"{field}.hex"),
        slug=_slug(name),
        role=role,
        note=note.strip(),
    )


def _parse_colors(design: dict[str, Any]) -> tuple[_Color, ...]:
    block = design.get("colors")
    if not isinstance(block, dict):
        raise BrandError(
            "brand.json: design.colors must be an object with canvas, surface, "
            "ink and primary roles"
        )
    _reject_unknown(
        block,
        "design.colors",
        REQUIRED_COLOR_ROLES + OPTIONAL_COLOR_ROLES,
    )

    colors: list[_Color] = []
    for role in REQUIRED_COLOR_ROLES:
        if role not in block:
            raise BrandError(
                f"brand.json: design.colors.{role} is required "
                f"(roles: {', '.join(REQUIRED_COLOR_ROLES + OPTIONAL_COLOR_ROLES)})"
            )
        colors.append(_parse_color_role(block[role], f"design.colors.{role}", role))

    if block.get("accent") is not None:
        colors.append(_parse_color_role(block["accent"], "design.colors.accent", "accent"))

    support = block.get("support")
    if support is not None:
        if not isinstance(support, list):
            raise BrandError("brand.json: design.colors.support must be a list of colours")
        for index, item in enumerate(support):
            colors.append(
                _parse_color_role(item, f"design.colors.support[{index}]", "support")
            )

    seen_names: dict[str, str] = {}
    seen_slugs: dict[str, _Color] = {}
    for color in colors:
        name_key = color.name.casefold()
        if name_key in seen_names:
            raise BrandError(
                f"brand.json: duplicate colour name {color.name!r} "
                f"(already used by {seen_names[name_key]})"
            )
        if color.slug in seen_slugs:
            other = seen_slugs[color.slug]
            raise BrandError(
                f"brand.json: colour names {other.name!r} and {color.name!r} "
                f"produce the same CSS token {color.slug!r} (duplicate slug)"
            )
        seen_names[name_key] = color.role
        seen_slugs[color.slug] = color

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


# ---------------------------------------------------------------------------
# Design blocks
# ---------------------------------------------------------------------------


def _parse_feedback(value: Any) -> Any:
    if value == "auto":
        return "auto"
    if not isinstance(value, dict):
        raise BrandError(
            'brand.json: design.feedback must be "auto" or an object with '
            f"{', '.join(FEEDBACK_ROLES)} overrides"
        )
    _reject_unknown(value, "design.feedback", FEEDBACK_ROLES)

    overrides: dict[str, str] = {}
    for role, spec in value.items():
        field = f"design.feedback.{role}"
        if isinstance(spec, str):
            overrides[role] = _hex(spec, field)
        elif isinstance(spec, dict):
            overrides[role] = _parse_color_role(spec, field, role).hex
        else:
            raise BrandError(
                f"brand.json: {field} must be a hex colour or an object with name and hex"
            )
    return overrides


def _parse_charts(value: Any) -> Any:
    if value == "auto":
        return "auto"
    if not isinstance(value, list) or not value:
        raise BrandError(
            'brand.json: design.charts must be "auto" or a non-empty list of colours'
        )

    charts: list[str] = []
    for index, item in enumerate(value):
        field = f"design.charts[{index}]"
        if isinstance(item, str):
            charts.append(_hex(item, field))
        elif isinstance(item, dict):
            charts.append(_parse_color_role(item, field, "chart").hex)
        else:
            raise BrandError(
                f"brand.json: {field} must be a hex colour or an object with name and hex"
            )
    return tuple(charts)


def _parse_type(
    design: dict[str, Any],
) -> tuple[
    str,
    str,
    int,
    int,
    tuple[str, str],
    tuple[str, str],
    tuple[float, float],
]:
    block = _object(design.get("type", {}), "design.type")
    _reject_unknown(block, "design.type", ("display", "body", "scale"))

    stacks: list[str] = []
    weights: list[int] = []
    trackings: list[str] = []
    cases: list[str] = []

    for role, default_fallback, default_weight in (
        ("display", "sans-serif", 600),
        ("body", "sans-serif", 400),
    ):
        field = f"design.type.{role}"
        spec = _object(block.get(role, {}), field)
        _reject_unknown(spec, field, ("family", "fallback", "weight", "tracking", "case"))

        family = _text(spec.get("family", DEFAULT_TYPE_FAMILY), f"{field}.family")
        family = family.strip('"').strip("'")
        if "," in family or '"' in family:
            raise BrandError(f"brand.json: {field}.family must be a single font family name")

        fallback = _text(spec.get("fallback", default_fallback), f"{field}.fallback")
        weight = _integer(spec.get("weight", default_weight), f"{field}.weight", 100, 900)
        if weight % 100:
            raise BrandError(f"brand.json: {field}.weight must be a multiple of 100")

        tracking = spec.get("tracking", "normal")
        if not isinstance(tracking, str) or not tracking.strip():
            raise BrandError(f"brand.json: {field}.tracking must be a non-empty string")

        case = _choice(spec.get("case", "none"), f"{field}.case", TEXT_CASES)

        stacks.append(f'"{family}", {fallback}')
        weights.append(weight)
        trackings.append(tracking.strip())
        cases.append(case)

    scale_block = block.get("scale", {})
    scale_block = _object(scale_block, "design.type.scale")
    _reject_unknown(scale_block, "design.type.scale", ("base", "ratio"))
    base = _number(scale_block.get("base", DEFAULT_SCALE[0]), "design.type.scale.base", 12, 32)
    ratio = _number(scale_block.get("ratio", DEFAULT_SCALE[1]), "design.type.scale.ratio", 1.05, 1.8)

    return (
        stacks[0],
        stacks[1],
        weights[0],
        weights[1],
        (trackings[0], trackings[1]),
        (cases[0], cases[1]),
        (base, ratio),
    )


def _parse_radius(value: Any) -> dict[str, float]:
    if isinstance(value, str):
        profile = _choice(
            value,
            "design.shape.radius",
            tuple(RADIUS_PROFILES),
        )
        return dict(RADIUS_PROFILES[profile])
    if isinstance(value, dict):
        _reject_unknown(value, "design.shape.radius", RADIUS_KEYS)
        radius = dict(RADIUS_PROFILES[DEFAULT_RADIUS])
        for key, raw in value.items():
            radius[key] = float(
                _integer(raw, f"design.shape.radius.{key}", 0, 9999)
            )
        return radius
    raise BrandError(
        "brand.json: design.shape.radius must be a profile "
        f"({', '.join(RADIUS_PROFILES)}) or an object with "
        f"{', '.join(RADIUS_KEYS)}"
    )


def _parse_shape(design: dict[str, Any]) -> tuple[dict[str, float], int, str]:
    block = design.get("shape", {})
    block = _object(block, "design.shape")
    _reject_unknown(block, "design.shape", ("radius", "unit", "shadows"))

    radius = _parse_radius(block.get("radius", DEFAULT_RADIUS))

    unit = block.get("unit", DEFAULT_UNIT)
    if isinstance(unit, bool) or unit not in (4, 8):
        raise BrandError(
            f"brand.json: design.shape.unit must be 4 or 8 (got {unit!r})"
        )

    shadows = _choice(block.get("shadows", DEFAULT_SHADOWS), "design.shape.shadows", SHADOWS)
    return radius, int(unit), shadows


def _gradient_reference(reference: Any, field: str, index: dict[str, _Color]) -> str:
    if isinstance(reference, str) and reference.startswith("#"):
        return _hex(reference, field)
    return _lookup_color(index, reference, field).hex


def _parse_gradient(value: Any, index: dict[str, _Color]) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise BrandError(
            "brand.json: design.theme.gradient must be null or an object "
            "with from, to and angle"
        )
    _reject_unknown(value, "design.theme.gradient", ("from", "to", "angle", "via"))

    start = _gradient_reference(value.get("from"), "design.theme.gradient.from", index)
    end = _gradient_reference(value.get("to"), "design.theme.gradient.to", index)
    if start == end:
        raise BrandError(
            "brand.json: design.theme.gradient.from and .to must be different colours"
        )

    angle = _number(value.get("angle", 45), "design.theme.gradient.angle", 0, 360)

    via = value.get("via")
    via_hex = None
    if via is not None:
        via_hex = _gradient_reference(via, "design.theme.gradient.via", index)

    return {"from": start, "to": end, "angle": angle, "via": via_hex}


def _parse_theme(
    design: dict[str, Any], index: dict[str, _Color]
) -> tuple[tuple[str, ...], str, dict[str, Any] | None]:
    block = design.get("theme", {})
    block = _object(block, "design.theme")
    _reject_unknown(block, "design.theme", ("modes", "default", "gradient"))

    modes_raw = block.get("modes", list(DEFAULT_MODES))
    if not isinstance(modes_raw, list) or not modes_raw:
        raise BrandError(
            "brand.json: design.theme.modes must be a non-empty list containing "
            f"{' and/or '.join(THEME_MODES)}"
        )

    modes: list[str] = []
    for position, mode in enumerate(modes_raw):
        mode = _choice(mode, f"design.theme.modes[{position}]", THEME_MODES)
        if mode in modes:
            raise BrandError(f"brand.json: design.theme.modes repeats {mode!r}")
        modes.append(mode)

    default = block.get("default", "light" if "light" in modes else modes[0])
    if default not in modes:
        raise BrandError(
            f"brand.json: design.theme.default must be one of the enabled modes "
            f"({', '.join(modes)}), got {default!r}"
        )

    gradient = _parse_gradient(block.get("gradient"), index)
    return tuple(modes), default, gradient


def _parse_icons(design: dict[str, Any]) -> dict[str, Any]:
    block = design.get("icons", {})
    block = _object(block, "design.icons")
    _reject_unknown(block, "design.icons", ("family", "size"))

    family = _choice(block.get("family", "fluent"), "design.icons.family", ICON_FAMILIES)
    size = _integer(block.get("size", 16), "design.icons.size", 8, 64)
    return {"family": family, "size": size}


def _parse_imagery(design: dict[str, Any]) -> dict[str, Any]:
    block = design.get("imagery", {})
    block = _object(block, "design.imagery")
    _reject_unknown(block, "design.imagery", ("mode", "treatment"))

    mode = _choice(block.get("mode", "abstract"), "design.imagery.mode", IMAGERY_MODES)

    treatment = block.get("treatment", "")
    if treatment is None:
        treatment = ""
    if not isinstance(treatment, str):
        raise BrandError("brand.json: design.imagery.treatment must be a string")

    return {"mode": mode, "treatment": treatment.strip()}


def _parse_composition(design: dict[str, Any]) -> dict[str, Any]:
    block = design.get("composition", {})
    block = _object(block, "design.composition")
    _reject_unknown(block, "design.composition", ("direction", "measure", "grid"))

    direction = _choice(
        block.get("direction", "structured"),
        "design.composition.direction",
        COMPOSITION_DIRECTIONS,
    )
    measure = _text(block.get("measure", "65ch"), "design.composition.measure")

    grid_raw = block.get("grid", "12")
    if isinstance(grid_raw, int) and not isinstance(grid_raw, bool):
        grid = str(grid_raw)
    elif isinstance(grid_raw, str):
        grid = _text(grid_raw, "design.composition.grid")
    else:
        raise BrandError(
            "brand.json: design.composition.grid must be a string such as \"12\""
        )

    return {"direction": direction, "measure": measure, "grid": grid}


def _parse_logo(design: dict[str, Any]) -> dict[str, str]:
    block = design.get("logo", {})
    block = _object(block, "design.logo")
    _reject_unknown(block, "design.logo", ("variant", "name", "notes"))

    variant = _choice(block.get("variant", "C"), "design.logo.variant", LOGO_VARIANTS)

    name = block.get("name", "")
    notes = block.get("notes", "")
    if name is None:
        name = ""
    if notes is None:
        notes = ""
    if not isinstance(name, str):
        raise BrandError("brand.json: design.logo.name must be a string when present")
    if not isinstance(notes, str):
        raise BrandError("brand.json: design.logo.notes must be a string when present")

    return {"variant": variant, "name": name.strip(), "notes": notes.strip()}


def _parse_language(brand: dict[str, Any]) -> str:
    value = brand.get("language")
    if value is None:
        return DEFAULT_LANGUAGE
    if not isinstance(value, str) or not _LANGUAGE_RE.match(value.strip()):
        raise BrandError(
            "brand.json: language must be a BCP-47 tag such as pt-BR or en "
            f"(got {value!r})"
        )
    return value.strip()


def _parse_voice(brand: dict[str, Any]) -> dict[str, Any]:
    value = brand.get("voice")
    if value is None:
        return {
            "summary": DEFAULT_VOICE_SUMMARY,
            "principles": [],
            "avoid": [],
            "person": "você",
            "emoji": "none",
        }
    if not isinstance(value, dict):
        raise BrandError("brand.json: voice must be an object when present")
    _reject_unknown(value, "voice", ("summary", "principles", "avoid", "person", "emoji"))

    return {
        "summary": _text(value.get("summary"), "voice.summary"),
        "principles": _string_list(value.get("principles", []), "voice.principles"),
        "avoid": _string_list(value.get("avoid", []), "voice.avoid"),
        "person": _text(value.get("person", "você"), "voice.person"),
        "emoji": _choice(value.get("emoji", "none"), "voice.emoji", VOICE_EMOJI),
    }


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


def _build_model(brand: Any) -> _Model:
    if not isinstance(brand, dict):
        raise BrandError("brand.json: top level must be a JSON object")

    version = brand.get("version")
    if isinstance(version, bool) or version != 2:
        raise BrandError(
            "brand.json: version must be 2 (the v2 schema is the final contract; "
            "v1 brand.json is not supported)"
        )

    v1_keys = [key for key in V1_TOP_LEVEL_KEYS if key in brand]
    if v1_keys:
        raise BrandError(
            f"brand.json: {', '.join(v1_keys)} belong to schema v1 and are not "
            "accepted in v2 (colors/type/shape/theme live under design)"
        )

    name = "Brand"
    if brand.get("name") is not None:
        name = _text(brand.get("name"), "name")

    language = _parse_language(brand)

    purpose = _text(brand.get("purpose"), "purpose")
    persona = _text(brand.get("persona"), "persona")
    territory = _text(brand.get("territory"), "territory")
    archetype = _text(brand.get("archetype"), "archetype")

    attributes = _string_list(brand.get("attributes"), "attributes")
    if not attributes:
        raise BrandError("brand.json: attributes must be a non-empty list of strings")

    voice = _parse_voice(brand)

    design = _object(brand.get("design"), "design")
    _reject_unknown(design, "design", DESIGN_KEYS)
    colors = _parse_colors(design)
    index = _color_index(colors)

    feedback = _parse_feedback(design.get("feedback", "auto"))
    charts = _parse_charts(design.get("charts", "auto"))

    (
        display_stack,
        body_stack,
        display_weight,
        body_weight,
        tracking,
        case,
        scale,
    ) = _parse_type(design)

    radius, unit, shadows = _parse_shape(design)
    modes, default_mode, gradient = _parse_theme(design, index)
    icons = _parse_icons(design)
    imagery = _parse_imagery(design)
    composition = _parse_composition(design)
    logo = _parse_logo(design)

    aceite = brand.get("aceite")
    if not isinstance(aceite, bool):
        raise BrandError("brand.json: aceite must be true or false (manual approval flag)")

    return _Model(
        name=name,
        language=language,
        purpose=purpose,
        persona=persona,
        territory=territory,
        archetype=archetype,
        attributes=tuple(attributes),
        voice=voice,
        colors=colors,
        lookup=index,
        feedback=feedback,
        charts=charts,
        display_stack=display_stack,
        body_stack=body_stack,
        display_weight=display_weight,
        body_weight=body_weight,
        tracking=tracking,
        case=case,
        scale=scale,
        radius=radius,
        unit=unit,
        shadows=shadows,
        modes=modes,
        default_mode=default_mode,
        gradient=gradient,
        icons=icons,
        imagery=imagery,
        composition=composition,
        logo=logo,
    )


# ---------------------------------------------------------------------------
# Semantic tokens
# ---------------------------------------------------------------------------


def _stack_family(stack: str) -> str:
    """Extract the first, quoted family from a generated CSS stack."""
    return stack.split('"', 2)[1]


def _stack_fallback(stack: str, default: str) -> str:
    """Extract the fallback tail from ``"Family", fallback``."""
    if '", ' not in stack:
        return default
    return stack.split('", ', 1)[1]


def normalize_brand(brand: dict[str, Any]) -> dict[str, Any]:
    """Return a validated brand object with every optional block filled in.

    ``render_theme``/``render_page`` must never raw-access an optional block:
    the parser defaults ``feedback``, ``charts``, ``type``, ``shape``, ``theme``,
    ``icons``, ``imagery``, ``composition`` and ``logo``, so the generator
    consumes this defaults-filled object instead.
    """

    model = _build_model(brand)
    design = brand.get("design") or {}

    def type_block(stack: str, weight: int, tracking: str, case: str) -> dict[str, Any]:
        return {
            "family": _stack_family(stack),
            "fallback": _stack_fallback(stack, "sans-serif"),
            "weight": weight,
            "tracking": tracking,
            "case": case,
        }

    return {
        "version": 2,
        "name": model.name,
        "language": model.language,
        "purpose": model.purpose,
        "persona": model.persona,
        "territory": model.territory,
        "archetype": model.archetype,
        "attributes": list(model.attributes),
        "voice": copy.deepcopy(model.voice),
        "design": {
            "colors": copy.deepcopy(design.get("colors") or {}),
            "feedback": copy.deepcopy(model.feedback),
            "charts": "auto" if model.charts == "auto" else list(model.charts),
            "type": {
                "display": type_block(
                    model.display_stack,
                    model.display_weight,
                    model.tracking[0],
                    model.case[0],
                ),
                "body": type_block(
                    model.body_stack,
                    model.body_weight,
                    model.tracking[1],
                    model.case[1],
                ),
                "scale": {"base": model.scale[0], "ratio": model.scale[1]},
            },
            "shape": {
                "radius": {key: int(value) for key, value in model.radius.items()},
                "unit": model.unit,
                "shadows": model.shadows,
            },
            "theme": {
                "modes": list(model.modes),
                "default": model.default_mode,
                "gradient": copy.deepcopy(model.gradient),
            },
            "icons": dict(model.icons),
            "imagery": dict(model.imagery),
            "composition": dict(model.composition),
            "logo": dict(model.logo),
        },
        "aceite": brand.get("aceite"),
    }


def _role_hex(model: _Model, role: str) -> str:
    """Return the approved hex for a colour role (accent falls back to primary)."""

    for color in model.colors:
        if color.role == role:
            return color.hex
    if role == "accent":
        return _role_hex(model, "primary")
    raise RuntimeError(f"brand model has no {role!r} colour role")


def _type_steps(model: _Model) -> tuple[tuple[str, int, float], ...]:
    base, ratio = model.scale
    steps: list[tuple[str, int, float]] = []
    for name, exponent in TYPE_STEPS:
        size = int(round(base * (ratio**exponent)))
        if exponent <= 0:
            leading = 1.6
        else:
            leading = max(1.05, 1.6 - 0.07 * exponent)
        steps.append((name, size, round(leading, 2)))
    return tuple(steps)


def _gradient_css(gradient: dict[str, Any]) -> str:
    stops = [f"{gradient['from']} 0%"]
    if gradient.get("via"):
        stops.append(f"{gradient['via']} 50%")
    stops.append(f"{gradient['to']} 100%")
    return f"linear-gradient({gradient['angle']:g}deg, {', '.join(stops)})"


def _mode_surfaces(model: _Model, mode: str) -> tuple[str, str, str]:
    """Return ``(canvas, surface, fg_seed)`` for a mode.

    The approved canvas/surface are role colours, not per-mode values: a light
    brand that enables dark (and vice versa) would otherwise get an identical
    dark block. When the approved surface sits on the wrong side of the mode,
    derive the opposite paper from ``ink``/``primary`` instead.
    """

    canvas_approved = _role_hex(model, "canvas")
    surface_approved = _role_hex(model, "surface")
    ink = _role_hex(model, "ink")
    primary = _role_hex(model, "primary")

    if mode == "light":
        canvas = (
            canvas_approved
            if relative_luminance(canvas_approved) >= 0.5
            else mix("#FFFFFF", ink, 0.04)
        )
        surface = (
            surface_approved
            if relative_luminance(surface_approved) >= 0.5
            else mix(canvas, "#FFFFFF", 0.5)
        )
        fg_seed = ink if relative_luminance(ink) < 0.5 else mix("#141110", ink, 0.08)
    else:
        canvas = (
            canvas_approved
            if relative_luminance(canvas_approved) < 0.2
            else mix(ink, primary, 0.06)
        )
        surface = (
            surface_approved
            if relative_luminance(surface_approved) < 0.2
            else mix(canvas, "#FFFFFF", 0.05)
        )
        fg_seed = (
            ink
            if relative_luminance(ink) >= 0.5
            else mix("#FFFFFF", canvas_approved, 0.06)
        )

    return canvas, surface, fg_seed


def _chart_tokens(model: _Model, mode: str, surface: str) -> dict[str, str]:
    """Eight chart colours that clear 3:1 against ``surface``, unique and stable."""

    primary = _role_hex(model, "primary")
    anchors = model.charts if isinstance(model.charts, tuple) else CHART_ANCHORS

    shift_target = "#000000" if mode == "light" else "#FFFFFF"
    bases: list[str] = []
    variants: list[list[str]] = []
    for anchor in anchors:
        base = (
            mix(anchor, primary, 0.10)
            if mode == "light"
            else mix(anchor, "#FFFFFF", 0.15)
        )
        bases.append(_ensure_contrast_all(base, (surface,), 3.0))
        variants.append(
            [
                _ensure_contrast_all(mix(base, shift_target, step * 0.06), (surface,), 3.0)
                for step in range(1, 9)
            ]
        )

    # One base hue per anchor first, so eight brands of colour survive; shifted
    # variants only fill the gaps left by contrast collisions.
    candidates = bases + [candidate for group in variants for candidate in group]

    unique: list[str] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
        if len(unique) == 8:
            break

    # Deterministic grayscale fallback for pathological palettes.
    for step in range(0, 21):
        if len(unique) == 8:
            break
        grey = mix("#808080", "#000000" if mode == "light" else "#FFFFFF", step / 20)
        candidate = _ensure_contrast_all(grey, (surface,), 3.0)
        if candidate not in unique:
            unique.append(candidate)

    if len(unique) != 8:
        raise RuntimeError("could not derive eight unique chart colours")

    return {f"chart-{index}": value for index, value in enumerate(unique, start=1)}


def _semantic_tokens(model: _Model, mode: str) -> dict[str, str]:
    """Full semantic colour set for one mode.

    Surfaces keep the approved canvas/surface hex; text, action, accent,
    feedback and chart tokens may shift to meet WCAG contrast.
    """

    if mode not in THEME_MODES:
        raise ValueError(f"unknown theme mode: {mode}")

    ink = _role_hex(model, "ink")
    primary_source = _role_hex(model, "primary")
    accent_source = _role_hex(model, "accent")
    canvas, surface, fg_seed = _mode_surfaces(model, mode)

    light = mode == "light"
    surface_muted = mix(surface, canvas, 0.55)
    if light:
        surface_raised = surface
        band_seed = ink if relative_luminance(ink) < 0.18 else "#141110"
        band = mix(band_seed, primary_source, 0.38)
        highlight = mix(surface, accent_source, 0.22)
        primary_soft = mix(canvas, primary_source, 0.14)
        accent_soft = mix(canvas, accent_source, 0.14)
        feedback_soft = 0.14
    else:
        surface_raised = mix(surface, "#FFFFFF", 0.04)
        band_seed = ink if relative_luminance(ink) < 0.18 else "#0B0A09"
        band = mix(band_seed, primary_source, 0.30)
        highlight = mix(canvas, accent_source, 0.38)
        primary_soft = mix(canvas, primary_source, 0.24)
        accent_soft = mix(canvas, accent_source, 0.24)
        feedback_soft = 0.24

    fg = _ensure_contrast_all(fg_seed, (canvas, surface), 7.0)
    on_highlight = ensure_contrast(fg_seed if light else "#FFFFFF", highlight, 4.5)

    primary = ensure_contrast(primary_source, canvas, 3.0)
    on_primary = _on_color(primary)
    primary_hover = mix(primary, "#000000" if light else "#FFFFFF", 0.12)
    # The hover fill must keep the same on-primary readable (no contrast dip).
    primary_hover = ensure_background_contrast(on_primary, primary_hover, 4.5)
    on_primary_soft = ensure_contrast(primary_source, primary_soft, 4.5)

    accent = _ensure_contrast_all(accent_source, (surface, canvas), 4.5)
    on_accent = _on_color(accent)
    link = _ensure_contrast_all(primary_source, (surface, canvas), 4.5)
    focus = _ensure_contrast_all(accent_source, (surface, canvas), 3.0)

    on_band = _on_color(band)
    on_band_muted = ensure_contrast(mix(on_band, band, 0.25), band, 4.5)
    band_accent = _first_with_contrast((accent, highlight, "#FFFFFF"), band, 4.5)

    tokens: dict[str, str] = {
        "canvas": canvas,
        "surface": surface,
        "surface-muted": surface_muted,
        "surface-raised": surface_raised,
        "band": band,
        "on-band": on_band,
        "on-band-muted": on_band_muted,
        "band-accent": band_accent,
        "fg": fg,
        "fg-muted": _ensure_contrast_all(mix(fg, canvas, 0.30), (canvas, surface), 4.5),
        "fg-subtle": _ensure_contrast_all(mix(fg, canvas, 0.42), (canvas, surface), 4.5),
        "fg-disabled": mix(fg, canvas, 0.62),
        "line": mix(canvas, fg, 0.12),
        "line-strong": mix(canvas, fg, 0.24),
        "line-input": _ensure_contrast_all(
            mix(canvas, fg, 0.45), (surface, canvas), 3.0
        ),
        "primary": primary,
        "primary-hover": primary_hover,
        "on-primary": on_primary,
        "primary-soft": primary_soft,
        "on-primary-soft": on_primary_soft,
        "accent": accent,
        "accent-soft": accent_soft,
        "on-accent": on_accent,
        "link": link,
        "focus": focus,
        "highlight": highlight,
        "on-highlight": on_highlight,
    }

    overrides = model.feedback if isinstance(model.feedback, dict) else {}
    for role in FEEDBACK_ROLES:
        anchor = overrides.get(role, FEEDBACK_ANCHORS[role])
        soft = mix(canvas, anchor, feedback_soft)
        solid = _ensure_contrast_all(anchor, (canvas, surface), 3.0)
        text = _ensure_contrast_all(anchor, (canvas, surface), 4.5)
        tokens[role] = text
        tokens[f"{role}-soft"] = soft
        tokens[f"{role}-solid"] = solid
        tokens[f"on-{role}"] = _on_color(solid)
        tokens[f"on-{role}-soft"] = ensure_contrast(text, soft, 4.5)

    tokens.update(_chart_tokens(model, mode, surface))

    if set(tokens) != set(SEMANTIC_COLOR_KEYS):
        raise RuntimeError("semantic token set drifted from SEMANTIC_COLOR_KEYS")
    return tokens


# ---------------------------------------------------------------------------
# CSS rendering
# ---------------------------------------------------------------------------


def _comment(text: Any) -> str:
    return " ".join(str(text).split()).replace("*/", "* /")


def _css_px(value: float) -> str:
    return f"{value:g}px"


def _declarations(tokens: dict[str, str]) -> list[str]:
    lines: list[str] = []
    for key in SEMANTIC_COLOR_KEYS:
        if key == "line":
            lines.append(
                "  /* line and line-strong are decorative separators. "
                "Use --b-line-input (>=3:1) for control boundaries (WCAG 1.4.11). */"
            )
        if key == "primary":
            lines.append(
                "  /* primary is UI and large text only (>=3:1 vs canvas). "
                "For body text use --b-link or --b-fg. */"
            )
        lines.append(f"  --b-{key}: {tokens[key]};")
    return lines


def _common_declarations(model: _Model) -> list[str]:
    lines: list[str] = ["  /* Brand palette — approved hex, theme invariant */"]
    lines.extend(
        f"  --b-color-{color.slug}: {color.hex}; "
        f"/* {_comment(color.name)} · {color.role} */"
        for color in model.colors
    )

    lines.extend(
        (
            "",
            "  /* Type — display for headlines, body for reading. */",
            f"  --b-display: {model.display_stack};",
            f"  --b-body: {model.body_stack};",
            f"  --b-weight-display: {model.display_weight};",
            f"  --b-weight-body: {model.body_weight};",
            f"  --b-tracking-display: {model.tracking[0]};",
            f"  --b-tracking-body: {model.tracking[1]};",
            f"  --b-case-display: {model.case[0]};",
            f"  --b-case-body: {model.case[1]};",
            "",
            "  /* Type scale — size = base * ratio^n; leading = 1.6 - 0.07n (floor 1.05). */",
        )
    )
    for name, size, leading in _type_steps(model):
        lines.append(f"  --b-text-{name}: {size}px;")
        lines.append(f"  --b-leading-{name}: {leading:g};")

    lines.extend(
        (
            "",
            f"  /* Spacing — multiples of the {model.unit}px unit */",
            f"  --b-unit: {model.unit}px;",
        )
    )
    for step in range(0, 17):
        lines.append(f"  --b-space-{step}: {step * model.unit}px;")

    lines.extend(("", "  /* Radius */"))
    for key in RADIUS_KEYS:
        lines.append(f"  --b-radius-{key}: {_css_px(model.radius[key])};")

    lines.extend(("", "  /* Elevation */"))
    for index, value in enumerate(SHADOW_SCALES[model.shadows], start=1):
        lines.append(f"  --b-shadow-{index}: {value};")

    if model.gradient is not None:
        lines.extend(
            ("", "  /* Brand gradient */", f"  --b-gradient: {_gradient_css(model.gradient)};")
        )
    return lines


def _theme_css(model: _Model) -> str:
    header = "\n".join(
        (
            "/* Brand Engine · theme.css — generated by scripts/build_theme.py from brand.json.",
            "   Do not edit by hand; change brand.json and regenerate.",
            f"   Brand: {_comment(model.name)}",
            f"   Purpose: {_comment(model.purpose)}",
            "   --b-color-* keeps the approved hex; semantic tokens may shift for contrast.",
            f"   Modes: {', '.join(model.modes)} (default: {model.default_mode}). "
            f"Gradient: {'yes' if model.gradient else 'none'}. */",
        )
    )

    tokens = {mode: _semantic_tokens(model, mode) for mode in THEME_MODES}
    root_mode = "light" if "light" in model.modes else "dark"

    lines: list[str] = [":root {", f"  color-scheme: {root_mode};", ""]
    lines.extend(_common_declarations(model))
    lines.extend(("", f"  /* Semantic tokens — {root_mode} */"))
    lines.extend(_declarations(tokens[root_mode]))
    lines.append("}")

    if "light" in model.modes and "dark" in model.modes:
        lines.extend(
            (
                "",
                '[data-theme="dark"] {',
                "  color-scheme: dark;",
                "",
                "  /* Semantic tokens — dark */",
            )
        )
        lines.extend(_declarations(tokens["dark"]))
        lines.append("}")

    tokens_block = "\n".join(lines)
    template = TEMPLATE_FILE.read_text(encoding="utf-8")
    if "{{BRAND_HEADER}}" not in template or "{{BRAND_TOKENS}}" not in template:
        raise BrandError(f"theme template is missing placeholders: {TEMPLATE_FILE}")
    return template.replace("{{BRAND_HEADER}}", header).replace(
        "{{BRAND_TOKENS}}", tokens_block
    )


def _tailwind_css(model: _Model) -> str:
    lines: list[str] = [
        "/* Brand Engine · tailwind-theme.css — generated by scripts/build_theme.py.",
        '   Load inside <style type="text/tailwindcss">. Colors point at --b-* tokens,',
        "   so bg-surface and text-fg-muted switch with the theme automatically.",
        "   Semantic utilities only: bg-surface, text-fg-muted, border-line, bg-primary,",
        "   text-on-primary, text-accent, bg-highlight, and the brand gradient utility.",
        "   primary is UI and large text only (>=3:1 vs canvas); use text-link or text-fg for body text.",
        "   line and line-strong are decorative separators; use line-input for control boundaries.",
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
            "  /* Type scale — size and coupled line-height */",
        )
    )
    for name, size, leading in _type_steps(model):
        lines.append(f"  --text-{name}: {size}px;")
        lines.append(f"  --text-{name}--line-height: {leading:g};")

    lines.extend(("", "  /* Radius */"))
    for key in RADIUS_KEYS:
        lines.append(f"  --radius-{key}: {_css_px(model.radius[key])};")

    lines.extend(("", "  /* Elevation */"))
    for index, value in enumerate(SHADOW_SCALES[model.shadows], start=1):
        lines.append(f"  --shadow-{index}: {value};")

    lines.append("}")

    if model.gradient is not None:
        lines.extend(
            (
                "",
                "/* Brand gradient utility (emitted only when brand.json defines a gradient). */",
                "@utility bg-grad-brand { background-image: var(--b-gradient); }",
            )
        )
    return "\n".join(lines) + "\n"


def render_theme(brand: dict[str, Any]) -> ThemeBuild:
    """Render both stylesheets from an already parsed brand object."""

    model = _build_model(brand)
    return ThemeBuild(
        theme_css=_theme_css(model),
        tailwind_theme_css=_tailwind_css(model),
    )


# ---------------------------------------------------------------------------
# Public API
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
    """Read, validate and normalize brand.json (optional blocks filled in).

    The returned object is what the theme builder, the page generator and the
    checker consume: no consumer has to raw-access an optional block.
    """

    data = _read_brand(brand_path)
    return normalize_brand(data)


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
