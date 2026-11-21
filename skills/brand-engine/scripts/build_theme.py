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
        "icons": {"family": "fluent", "style": "regular", "size": 16},
        "imagery": {"mode": "abstract", "treatment": "...", "placeholder": "placehold"},
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

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

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
DEFAULT_ICONS: dict[str, Any] = {"family": "fluent", "style": "regular", "size": 16}
DEFAULT_IMAGERY: dict[str, Any] = {
    "mode": "abstract",
    "treatment": "",
    "placeholder": "placehold",
}
DEFAULT_COMPOSITION: dict[str, Any] = {
    "direction": "structured",
    "measure": "65ch",
    "grid": "12",
}
DEFAULT_LOGO: dict[str, str] = {"variant": "C", "name": "", "notes": ""}
DEFAULT_VOICE_SUMMARY = "[placeholder — resumo da voz]"

_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


class BrandError(ValueError):
    """A malformed or incomplete brand.json, or an unusable --brand path."""


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
    _reject_unknown(block, "design.icons", ("family", "style", "size"))

    family = _choice(block.get("family", "fluent"), "design.icons.family", ICON_FAMILIES)
    style = _text(block.get("style", "regular"), "design.icons.style")
    size = _integer(block.get("size", 16), "design.icons.size", 8, 64)
    return {"family": family, "style": style, "size": size}


def _parse_imagery(design: dict[str, Any]) -> dict[str, Any]:
    block = design.get("imagery", {})
    block = _object(block, "design.imagery")
    _reject_unknown(block, "design.imagery", ("mode", "treatment", "placeholder"))

    mode = _choice(block.get("mode", "abstract"), "design.imagery.mode", IMAGERY_MODES)

    treatment = block.get("treatment", "")
    if treatment is None:
        treatment = ""
    if not isinstance(treatment, str):
        raise BrandError("brand.json: design.imagery.treatment must be a string")

    placeholder = _text(
        block.get("placeholder", DEFAULT_IMAGERY["placeholder"]),
        "design.imagery.placeholder",
    )
    return {"mode": mode, "treatment": treatment.strip(), "placeholder": placeholder}


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


if __name__ == "__main__":
    raise SystemExit(
        "build_theme: the theme builder lands in a later task; "
        "this module currently exposes the v2 brand model only."
    )
