#!/usr/bin/env python3
"""Static v2 brand checker for single-file HTML pages.

``check_page(path) -> list[str]`` reads one HTML file and returns findings.
Every finding is a string starting with ``ERROR`` or ``WARN``::

    ERROR [tokens] line 42: bare hex #A6402F in class="…"
    WARN  [table] line 80: <th> without scope

The v2 contract is the only contract; there is no compatibility mode. The
checker infers the brand rules from the page itself:

- the generated type steps from ``--b-text-*``;
- the spacing unit (4 or 8) from ``--b-unit``;
- whether dark mode exists from a ``[data-theme="dark"]`` block;
- whether a brand gradient exists from ``--b-gradient``.

``--brand`` is optional and only adds strict validation of the brand file,
including a ``<html lang>``/``brand.json`` ``language`` match.

Rules cover the Task 3 HTML contract:

- structure: one ``<main>``, exactly one ``<h1>``, heading order, document shell;
  a theme toggle is required only when both light and dark modes exist and the
  page is not locked with ``data-theme-lock``;
- static a11y: accessible names, table ``caption``/``th``/``scope``, duplicate
  ids, dangling ARIA/fragment references, no inline handlers on ``div``;
- tokens only: no bare hex, palette utilities, raw colours or arbitrary colours
  in content classes/styles, inline styles or non-generated ``<style>`` blocks;
  feedback (``success``/``warning``/``danger``/``info`` with soft/solid/on
  variants) and ``chart-1..8`` are allowed;
- type scale: ``text-*`` sizes from the generated scale embedded in the page;
- spacing: steps on the page's unit scale (unit 8 keeps the coarse scale, unit 4
  allows every whole step) and arbitrary lengths on the unit grid;
- gradient: optional; ad-hoc gradients are rejected and ``bg-grad-brand`` is
  only valid when ``--b-gradient`` exists (any angle, any stops);
- icons: ``<iconify-icon>`` is decorative (``aria-hidden="true"``) or labelled;
- images: ``<img>`` needs ``alt`` (``alt=""`` is valid decorative);
- logo: sprite at the top of ``<body>`` (except the ``app`` format),
  breathing-area comment (except ``app``), documented misuses on the manual,
  no rotate/scale/shadow/raster use;
- semantic token rules: ``text-primary`` is not body text, controls use
  ``border-line-input``, primary fills declare a hover state;
- formats: ``app`` and ``brand-kit`` pages are accepted.

The checker is deliberately static: it does not need a browser, ``brand.json``
or an internet connection. Contrast maths stays in ``build_theme.py``; a
browser pass (axe) is the complementary check described by the skill.

CLI::

    python3 scripts/check_page.py page.html [more.html …] [--strict] [--brand brand.json]

Exit codes: ``0`` clean, ``1`` findings (WARN only counts with ``--strict``),
``2`` unreadable HTML file. The checker never raises a traceback for a bad path.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

import build_theme

# ---------------------------------------------------------------------------
# Contract constants (kept in sync with build_theme.py)
# ---------------------------------------------------------------------------

FEEDBACK_ROLES = ("success", "warning", "danger", "info")

_BASE_SEMANTIC_COLORS = frozenset(
    {
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
    }
)

SEMANTIC_COLORS = frozenset(
    _BASE_SEMANTIC_COLORS
    | {
        suffix
        for role in FEEDBACK_ROLES
        for suffix in (
            role,
            f"{role}-soft",
            f"{role}-solid",
            f"on-{role}",
            f"on-{role}-soft",
        )
    }
    | {f"chart-{index}" for index in range(1, 9)}
)

# Fallback when the page embeds no --b-text-* declarations. Generated pages
# always embed the scale; the fallback keeps the checker useful on partial
# snippets without weakening the off-scale rule.
DEFAULT_TYPE_STEPS = (
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

# The coarse 8px scale used by the skeletons: 1,2,3,4 then 6,8,10,12,16.
# A 4px unit allows every whole step.
SKIPPED_SPACING_STEPS = frozenset({5, 7, 9, 11})

DEFAULT_SPACING_UNIT = 8


HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
BODY_TEXT_TAGS = frozenset(
    {
        "p",
        "li",
        "dd",
        "dt",
        "td",
        "th",
        "blockquote",
        "figcaption",
        "span",
        "strong",
        "em",
        "code",
        "a",
    }
)
CONTROL_TAGS = frozenset({"input", "select", "textarea", "button"})
INTERACTIVE_TAGS = frozenset(
    {"a", "button", "input", "select", "textarea", "summary", "details"}
)
VOID_TAGS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)
ROLE_NAMES = frozenset(
    {
        "img",
        "button",
        "link",
        "checkbox",
        "switch",
        "tab",
        "menuitem",
        "menuitemcheckbox",
        "menuitemradio",
        "radio",
        "slider",
        "combobox",
        "textbox",
        "searchbox",
    }
)
TEXT_UTILITIES = frozenset(
    {
        "left",
        "center",
        "right",
        "justify",
        "start",
        "end",
        "wrap",
        "nowrap",
        "balance",
        "pretty",
        "ellipsis",
        "clip",
        "transparent",
        "current",
        "inherit",
    }
)

HEX_RE = re.compile(r"#(?:[0-9A-Fa-f]{3,4}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})\b")
ARBITRARY_COLOR_RE = re.compile(r"\[(?:#|rgb|rgba|hsl|hsla|oklch|oklab|lab|lch|color)\b", re.I)
PALETTE_RE = re.compile(
    r"^(?:bg|text|border|ring|fill|stroke|from|via|to|divide|outline|decoration|accent|caret)-"
    r"(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|"
    r"cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-"
    r"(?:50|100|200|300|400|500|600|700|800|900|950)(?:/\d+)?$"
)
RAW_COLOR_RE = re.compile(
    r"^(?:bg|text|border|ring|fill|stroke|from|via|to|divide|outline|decoration|accent|caret)-"
    r"(?:white|black)(?:/\d+)?$"
)
GRADIENT_UTILITY_RE = re.compile(r"^(?:bg-(?:gradient|linear)-to-|(?:from|via|to)-)", re.I)

_SPACING_PREFIXES = sorted(
    {
        "p",
        "px",
        "py",
        "pt",
        "pb",
        "pl",
        "pr",
        "m",
        "mx",
        "my",
        "mt",
        "mb",
        "ml",
        "mr",
        "gap",
        "gap-x",
        "gap-y",
        "space-x",
        "space-y",
        "w",
        "h",
        "min-w",
        "min-h",
        "max-w",
        "max-h",
        "size",
        "inset",
        "inset-x",
        "inset-y",
        "top",
        "right",
        "bottom",
        "left",
        "basis",
        "scroll-m",
        "scroll-mt",
        "scroll-mb",
        "scroll-ml",
        "scroll-mr",
        "scroll-p",
        "scroll-pt",
        "scroll-pb",
        "scroll-pl",
        "scroll-pr",
        "translate-x",
        "translate-y",
    },
    key=len,
    reverse=True,
)
SPACING_RE = re.compile(
    r"^-?(?P<prefix>" + "|".join(map(re.escape, _SPACING_PREFIXES)) + r")-(?P<value>.+)$"
)

SPACING_KEYWORDS = frozenset(
    {
        "auto",
        "full",
        "screen",
        "svh",
        "lvh",
        "dvh",
        "min",
        "max",
        "fit",
        "none",
        "prose",
    }
)

SPACING_PROPERTIES = frozenset(
    {
        "margin",
        "margin-top",
        "margin-right",
        "margin-bottom",
        "margin-left",
        "margin-inline",
        "margin-block",
        "padding",
        "padding-top",
        "padding-right",
        "padding-bottom",
        "padding-left",
        "padding-inline",
        "padding-block",
        "gap",
        "row-gap",
        "column-gap",
        "inset",
        "inset-x",
        "inset-y",
        "top",
        "right",
        "bottom",
        "left",
    }
)

COLOR_PROPERTIES = frozenset(
    {
        "color",
        "background",
        "background-color",
        "border",
        "border-top",
        "border-right",
        "border-bottom",
        "border-left",
        "border-color",
        "border-top-color",
        "border-right-color",
        "border-bottom-color",
        "border-left-color",
        "outline",
        "outline-color",
        "text-decoration-color",
        "column-rule-color",
        "fill",
        "stroke",
        "stop-color",
        "flood-color",
        "lighting-color",
        "box-shadow",
        "text-shadow",
        "filter",
        "backdrop-filter",
        "caret-color",
        "accent-color",
    }
)

ALLOWED_COLOR_KEYWORDS = frozenset(
    {"currentcolor", "inherit", "transparent", "none", "unset", "initial", "revert"}
)

# Small, deliberately common subset: enough to catch hand-typed colours in
# inline styles without pretending to validate the whole CSS colour keyword list.
NAMED_COLOURS = frozenset(
    {
        "aqua",
        "beige",
        "black",
        "blue",
        "brown",
        "coral",
        "crimson",
        "cyan",
        "fuchsia",
        "gold",
        "gray",
        "green",
        "grey",
        "indigo",
        "ivory",
        "khaki",
        "lime",
        "magenta",
        "maroon",
        "navy",
        "olive",
        "orange",
        "pink",
        "purple",
        "red",
        "salmon",
        "silver",
        "teal",
        "tomato",
        "turquoise",
        "violet",
        "white",
        "yellow",
    }
)

GRADIENT_RE = re.compile(
    r"(?<![\w-])((?:repeating-)?(?:linear|radial|conic)-gradient)\s*\(", re.I
)
STYLE_BLOCK_RE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.I | re.S)
CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)

# v2 inference: the page carries its own generated contract.
TYPE_TOKEN_RE = re.compile(r"--b-text-([a-z0-9]+)\s*:\s*\d+(?:\.\d+)?px")
SPACING_UNIT_RE = re.compile(r"--b-unit\s*:\s*(4|8)px")
BRAND_GRADIENT_RE = re.compile(r"--b-gradient\s*:\s*[^;}\n]+;?")
# A real dark block declares tokens (or a dark color-scheme) after the
# selector. Bare selectors such as ``@custom-variant dark (...)`` and
# ``[data-theme="dark"] [data-theme-toggle] { ... }`` are emitted on every
# generated page and must not imply that the brand has both modes.
DARK_BLOCK_RE = re.compile(
    r"""\[\s*data-theme\s*=\s*["']?dark["']?\s*\]\s*\{(?:(?!\}).)*?"""
    r"""(?:--b-|color-scheme\s*:\s*dark)""",
    re.S,
)

LOGO_CLASSES = frozenset({"be-mark", "be-wordmark", "be-monogram", "be-brand"})
MISUSE_TERMS = (
    ("recolor", r"recolor|recolorir|cor fora|gradiente no logo"),
    ("rotate", r"rotat|inclinar|espelhar"),
    ("stretch", r"estic|comprim|proporç|distorc|stretch"),
    ("replace", r"trocar|substitu|replace|emoji|ícone genérico"),
)


# ---------------------------------------------------------------------------
# Small HTML tree (stdlib only)
# ---------------------------------------------------------------------------


@dataclass
class _Element:
    tag: str
    attrs: dict[str, str]
    line: int
    parent: "_Element | None" = None
    children: list["_Element"] = field(default_factory=list)
    text_parts: list[str] = field(default_factory=list)

    def get(self, name: str, default: str = "") -> str:
        return self.attrs.get(name, default)

    @property
    def classes(self) -> list[str]:
        return self.get("class").split()

    def text(self) -> str:
        return " ".join("".join(self.text_parts).split())

    def walk(self) -> list["_Element"]:
        nodes = [self]
        for child in self.children:
            nodes.extend(child.walk())
        return nodes


class _Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[_Element] = []
        self.elements: list[_Element] = []
        self.comments: list[tuple[str, int]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        parent = self.stack[-1] if self.stack else None
        element = _Element(
            tag=tag.lower(),
            attrs={key.lower(): (value or "") for key, value in attrs},
            line=self.getpos()[0],
            parent=parent,
        )
        if parent is not None:
            parent.children.append(element)
        self.elements.append(element)
        if tag.lower() not in VOID_TAGS:
            self.stack.append(element)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if self.stack and self.stack[-1].tag == tag.lower():
            self.stack.pop()

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index].tag == tag.lower():
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        if not self.stack or self.stack[-1].tag in ("script", "style"):
            return
        if any(
            "hidden" in element.attrs
            or element.get("aria-hidden").strip().lower() == "true"
            for element in self.stack
        ):
            return
        for element in self.stack:
            element.text_parts.append(data)

    def handle_comment(self, data: str) -> None:
        self.comments.append((data, self.getpos()[0]))


@dataclass
class _Document:
    html: str
    elements: list[_Element]
    comments: list[tuple[str, int]]

    def by_tag(self, tag: str) -> list[_Element]:
        return [element for element in self.elements if element.tag == tag]

    @property
    def body(self) -> _Element | None:
        bodies = self.by_tag("body")
        return bodies[0] if bodies else None

    @property
    def page_format(self) -> str:
        body = self.body
        return body.get("data-format").strip().lower() if body is not None else ""


def _parse(html: str) -> _Document:
    collector = _Collector()
    collector.feed(html)
    collector.close()
    return _Document(html, collector.elements, collector.comments)


def _line_of(html: str, index: int) -> int:
    return html.count("\n", 0, index) + 1


def _finding(severity: str, rule: str, message: str, line: int | None = None) -> str:
    location = f" line {line}" if line else ""
    return f"{severity} [{rule}]{location}: {message}"


def _base_class(token: str) -> str:
    """Strip responsive/state variants without splitting arbitrary values."""

    depth = 0
    start = 0
    for index, char in enumerate(token):
        if char == "[":
            depth += 1
        elif char == "]":
            depth = max(0, depth - 1)
        elif char == ":" and depth == 0:
            start = index + 1
    return token[start:]


def _style_declarations(style: str) -> list[tuple[str, str]]:
    declarations: list[tuple[str, str]] = []
    for part in style.split(";"):
        if ":" not in part:
            continue
        prop, value = part.split(":", 1)
        prop = prop.strip().lower()
        value = value.strip()
        if prop and value:
            declarations.append((prop, value))
    return declarations


def _gradient_calls(css: str) -> list[tuple[str, str, int]]:
    calls: list[tuple[str, str, int]] = []
    for match in GRADIENT_RE.finditer(css):
        depth = 1
        index = match.end()
        while index < len(css) and depth:
            if css[index] == "(":
                depth += 1
            elif css[index] == ")":
                depth -= 1
            index += 1
        body = css[match.end() : index - 1] if depth == 0 else css[match.end() :]
        calls.append((match.group(1).lower(), body, match.start()))
    return calls


def _blank_comments(css: str) -> str:
    """Blank comments while preserving offsets and line numbers."""

    return CSS_COMMENT_RE.sub(
        lambda match: re.sub(r"[^\n]", " ", match.group(0)), css
    )


def _is_hidden(element: _Element) -> bool:
    node: _Element | None = element
    while node is not None:
        if "hidden" in node.attrs:
            return True
        if node.get("aria-hidden").strip().lower() == "true":
            return True
        node = node.parent
    return False


def _has_accessible_name(element: _Element) -> bool:
    for attribute in ("aria-label", "aria-labelledby", "title"):
        if element.get(attribute).strip():
            return True
    if element.tag == "img":
        return "alt" in element.attrs
    if element.tag == "input":
        input_type = element.get("type").lower()
        if input_type in {"submit", "button", "reset"} and element.get("value").strip():
            return True
        if input_type == "image" and element.get("alt").strip():
            return True
    if element.tag in ("input", "select", "textarea"):
        return False
    if element.get("role").strip().lower() == "img":
        # role="img" needs an author name or, for SVG, a <title> child.
        return element.tag == "svg" and any(
            child.tag == "title" and child.text().strip() for child in element.children
        )
    if element.text().strip():
        return True
    for child in element.children:
        if child.get("aria-label").strip() or child.get("title").strip():
            return True
        if child.tag in ("img", "image") and child.get("alt").strip():
            return True
        if child.tag == "svg" and child.get("aria-label").strip():
            return True
    return False


def _has_label(element: _Element, label_for: set[str]) -> bool:
    if element.get("id") in label_for:
        return True
    node = element.parent
    while node is not None:
        if node.tag == "label":
            return True
        node = node.parent
    return False


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def _check_document(doc: _Document, html: str) -> list[str]:
    findings: list[str] = []
    if not re.match(r"\s*<!doctype\s+html", html, re.I):
        findings.append(_finding("WARN", "structure", "missing <!doctype html>"))

    html_tags = doc.by_tag("html")
    if not html_tags:
        findings.append(_finding("ERROR", "structure", "missing <html> element"))
    elif not html_tags[0].get("lang").strip():
        findings.append(
            _finding("ERROR", "a11y", "html element needs a non-empty lang", html_tags[0].line)
        )

    if not doc.by_tag("head"):
        findings.append(_finding("ERROR", "structure", "missing <head> element"))
    if doc.body is None:
        findings.append(_finding("ERROR", "structure", "missing <body> element"))

    titles = doc.by_tag("title")
    if not titles:
        findings.append(_finding("ERROR", "a11y", "missing <title>"))
    elif not titles[0].text().strip():
        findings.append(_finding("ERROR", "a11y", "empty <title>", titles[0].line))

    viewport = any(
        element.tag == "meta"
        and element.get("name").strip().lower() == "viewport"
        and element.get("content").strip()
        for element in doc.elements
    )
    if not viewport:
        findings.append(_finding("WARN", "a11y", "missing viewport meta tag"))

    return findings


def _has_dark_tokens(html: str) -> bool:
    """True when the page defines a dark override block (both modes exist)."""

    return bool(DARK_BLOCK_RE.search(html))


def _has_theme_toggle(doc: _Document) -> bool:
    return any("data-theme-toggle" in element.attrs for element in doc.elements)


def _is_theme_locked(doc: _Document) -> bool:
    return any("data-theme-lock" in element.attrs for element in doc.elements)


def _check_theme(doc: _Document, html: str) -> list[str]:
    """Require a toggle only for both-mode pages without a lock."""

    if _is_theme_locked(doc) or not _has_dark_tokens(html):
        return []
    if _has_theme_toggle(doc):
        return []
    return [
        _finding(
            "ERROR",
            "structure",
            "page defines light and dark modes; add a data-theme-toggle "
            "(or lock the theme with data-theme-lock)",
        )
    ]


def _check_structure(doc: _Document) -> list[str]:
    findings: list[str] = []

    mains = doc.by_tag("main")
    if len(mains) != 1:
        findings.append(
            _finding(
                "ERROR",
                "structure",
                f"expected exactly one <main>, found {len(mains)}",
            )
        )

    h1s = doc.by_tag("h1")
    if not h1s:
        findings.append(_finding("ERROR", "headings", "missing <h1>"))
    elif len(h1s) > 1:
        findings.append(
            _finding(
                "ERROR",
                "headings",
                f"expected exactly one <h1>, found {len(h1s)}",
                h1s[1].line,
            )
        )

    headings = [
        element
        for element in doc.elements
        if element.tag in HEADING_TAGS and not _is_hidden(element)
    ]
    if headings and headings[0].tag != "h1":
        findings.append(
            _finding(
                "ERROR",
                "headings",
                f"first heading is <{headings[0].tag}>; start with <h1>",
                headings[0].line,
            )
        )
    previous = 0
    for heading in headings:
        level = int(heading.tag[1])
        if previous and level > previous + 1:
            findings.append(
                _finding(
                    "ERROR",
                    "headings",
                    f"<{heading.tag}> skips from h{previous}; keep heading order",
                    heading.line,
                )
            )
        if not heading.text().strip():
            findings.append(
                _finding("WARN", "headings", f"empty <{heading.tag}>", heading.line)
            )
        previous = level

    ids: dict[str, _Element] = {}
    for element in doc.elements:
        identifier = element.get("id").strip()
        if not identifier:
            continue
        if identifier in ids:
            findings.append(
                _finding(
                    "ERROR",
                    "a11y",
                    f'duplicate id "{identifier}" (first on line {ids[identifier].line})',
                    element.line,
                )
            )
        else:
            ids[identifier] = element

    label_for = {
        element.get("for").strip()
        for element in doc.by_tag("label")
        if element.get("for").strip()
    }
    for element in doc.by_tag("label"):
        target = element.get("for").strip()
        if target and target not in ids:
            findings.append(
                _finding(
                    "ERROR",
                    "a11y",
                    f'label for="{target}" has no matching id',
                    element.line,
                )
            )

    for element in doc.elements:
        for attribute in ("aria-labelledby", "aria-describedby"):
            value = element.get(attribute).strip()
            if not value:
                continue
            for reference in value.split():
                if reference not in ids:
                    severity = "ERROR" if attribute == "aria-labelledby" else "WARN"
                    findings.append(
                        _finding(
                            severity,
                            "a11y",
                            f'{attribute}="{reference}" has no matching id',
                            element.line,
                        )
                    )

    for element in doc.elements:
        if element.tag in ("a", "use") and element.get("href").strip():
            href = element.get("href").strip()
            if href.startswith("#") and len(href) > 1 and href[1:] not in ids:
                findings.append(
                    _finding(
                        "ERROR",
                        "a11y",
                        f'fragment href="{href}" has no matching id',
                        element.line,
                    )
                )

    skip_link = any(
        element.tag == "a"
        and "be-skip" in element.classes
        and element.get("href").strip()
        for element in doc.elements
    )
    if not skip_link:
        findings.append(_finding("WARN", "a11y", "missing skip link to the main content"))

    return findings


def _check_assets(doc: _Document) -> list[str]:
    findings: list[str] = []
    asset_attrs = {
        "script": ("src",),
        "img": ("src", "srcset"),
        "image": ("href", "xlink:href"),
        "link": ("href",),
        "source": ("src", "srcset"),
        "video": ("src", "poster"),
        "audio": ("src",),
        "iframe": ("src",),
        "embed": ("src",),
        "object": ("data",),
        "use": ("href", "xlink:href"),
    }
    remote_prefixes = (
        "#",
        "data:",
        "https://",
        "http://",
        "//",
        "mailto:",
        "tel:",
        "blob:",
    )
    for element in doc.elements:
        for attribute in asset_attrs.get(element.tag, ()):
            value = element.get(attribute).strip()
            if not value:
                continue
            urls = (
                [
                    item.strip().split()[0]
                    for item in value.split(",")
                    if item.strip()
                ]
                if attribute == "srcset" and not value.lower().startswith("data:")
                else [value]
            )
            for url in urls:
                if url.lower().startswith(remote_prefixes):
                    continue
                findings.append(
                    _finding(
                        "ERROR",
                        "single-file",
                        f'local asset reference {attribute}="{url}" (embed it or use a token)',
                        element.line,
                    )
                )
    return findings


def _check_events(doc: _Document) -> list[str]:
    findings: list[str] = []
    for element in doc.elements:
        for attribute in element.attrs:
            if attribute.startswith("on") and len(attribute) > 2:
                severity = "WARN" if element.tag in INTERACTIVE_TAGS else "ERROR"
                findings.append(
                    _finding(
                        severity,
                        "events",
                        f'inline handler {attribute} on <{element.tag}>; use a listener',
                        element.line,
                    )
                )
        if element.get("href").strip().lower().startswith("javascript:"):
            findings.append(
                _finding(
                    "ERROR",
                    "events",
                    "javascript: href is not keyboard-safe; use a button and a listener",
                    element.line,
                )
            )
    return findings


def _check_a11y_names(doc: _Document) -> list[str]:
    findings: list[str] = []
    label_for = {
        element.get("for").strip()
        for element in doc.by_tag("label")
        if element.get("for").strip()
    }
    for element in doc.elements:
        if _is_hidden(element):
            continue

        if element.tag == "iframe" and not element.get("title").strip():
            findings.append(
                _finding("ERROR", "a11y", "iframe without title", element.line)
            )

        role = element.get("role").strip().lower()

        if element.tag in ("input", "select", "textarea"):
            if element.tag == "input" and element.get("type").lower() == "hidden":
                continue
            if not _has_accessible_name(element) and not _has_label(element, label_for):
                findings.append(
                    _finding(
                        "ERROR",
                        "a11y",
                        f"<{element.tag}> without an associated <label> or aria-label",
                        element.line,
                    )
                )
            continue

        if element.tag == "button":
            needs_name = True
        elif element.tag == "a":
            needs_name = "href" in element.attrs or role in ROLE_NAMES
        else:
            needs_name = role in ROLE_NAMES

        if needs_name and not _has_accessible_name(element):
            findings.append(
                _finding(
                    "ERROR",
                    "a11y",
                    f"<{element.tag}> without an accessible name",
                    element.line,
                )
            )

        if element.tag == "button" and not element.get("type").strip():
            findings.append(
                _finding(
                    "WARN",
                    "a11y",
                    "button without type (defaults to submit)",
                    element.line,
                )
            )
    return findings


def _check_tables(doc: _Document) -> list[str]:
    findings: list[str] = []
    for table in doc.by_tag("table"):
        captions = [child for child in table.children if child.tag == "caption"]
        if not captions:
            findings.append(
                _finding("ERROR", "table", "table without <caption>", table.line)
            )
        elif not captions[0].text().strip():
            findings.append(
                _finding("ERROR", "table", "empty <caption>", captions[0].line)
            )

        headers = [element for element in table.walk() if element.tag == "th"]
        if not headers:
            findings.append(
                _finding("ERROR", "table", "table without <th> header cells", table.line)
            )
        for header in headers:
            scope = header.get("scope").strip().lower()
            if not scope:
                findings.append(
                    _finding(
                        "WARN",
                        "table",
                        "<th> without scope (use scope=\"col\" or \"row\")",
                        header.line,
                    )
                )
            elif scope not in {"col", "row", "colgroup", "rowgroup"}:
                findings.append(
                    _finding(
                        "WARN",
                        "table",
                        f'<th> has invalid scope="{scope}"',
                        header.line,
                    )
                )
    return findings


def _check_tokens(doc: _Document, html: str) -> list[str]:
    findings: list[str] = []
    seen: set[str] = set()

    def add(message: str, line: int) -> None:
        finding = _finding("ERROR", "tokens", message, line)
        if finding not in seen:
            seen.add(finding)
            findings.append(finding)

    for element in doc.elements:
        for token in element.classes:
            base = _base_class(token)
            if not base:
                continue
            if HEX_RE.search(base):
                add(f'bare hex in class="{token}"', element.line)
                continue
            if ARBITRARY_COLOR_RE.search(base):
                add(f'arbitrary colour in class="{token}"', element.line)
                continue
            if PALETTE_RE.match(base):
                add(f'palette utility class="{token}"', element.line)
                continue
            if RAW_COLOR_RE.match(base):
                add(f'raw colour class="{token}"', element.line)

        style = element.get("style")
        if style:
            if HEX_RE.search(style):
                add(f'bare hex in style="{style}"', element.line)
            for prop, value in _style_declarations(style):
                if prop in COLOR_PROPERTIES and _has_raw_colour(value):
                    add(f'raw colour in {prop}: {value}', element.line)

        for attribute in ("fill", "stroke", "stop-color", "flood-color", "lighting-color"):
            value = element.get(attribute).strip()
            if not value:
                continue
            lowered = value.lower()
            if (
                lowered.startswith("var(")
                or lowered.startswith("url(#")
                or lowered in ALLOWED_COLOR_KEYWORDS
            ):
                continue
            add(f'raw colour in {attribute}="{value}"', element.line)

        if element.get("bgcolor").strip():
            add("bgcolor attribute carries a raw colour", element.line)

    findings.extend(_check_style_tokens(html))
    return findings


STYLE_DECLARATION_RE = re.compile(
    r"(?P<prop>--?[A-Za-z][\w-]*|[A-Za-z-]+)\s*:\s*(?P<value>[^;{}]+)"
)


def _check_style_tokens(html: str) -> list[str]:
    """Apply the tokens-only rule to non-generated ``<style>`` blocks.

    The generated ``theme.css`` and ``@theme`` blocks legitimately contain raw
    hex and rgba values (they define the tokens), so they are skipped. Brand
    custom properties (``--b-*``) are token definitions; other declarations and
    utility tokens are checked for bare hex, ``rgb()/hsl()``, named colours and
    palette/raw utilities.
    """

    findings: list[str] = []
    seen: set[str] = set()

    def add(message: str, line: int) -> None:
        finding = _finding("ERROR", "tokens", message, line)
        if finding not in seen:
            seen.add(finding)
            findings.append(finding)

    for block in STYLE_BLOCK_RE.finditer(html):
        css = _blank_comments(block.group(1))
        if "--b-color-" in css or "@theme" in css:
            continue
        for match in STYLE_DECLARATION_RE.finditer(css):
            prop = match.group("prop").lower()
            value = match.group("value").strip()
            line = _line_of(html, block.start(1) + match.start("value"))
            if prop.startswith("--b-"):
                continue
            if prop.startswith("--"):
                if _has_raw_colour(value):
                    add(f"raw colour in custom property {prop}: {value}", line)
                continue
            if prop not in COLOR_PROPERTIES:
                continue
            if _has_raw_colour(value):
                add(f"raw colour in <style> {prop}: {value}", line)

        for apply in re.finditer(r"@apply\s+([^;{}]+)", css):
            for token in apply.group(1).split():
                base = _base_class(token)
                if PALETTE_RE.match(base):
                    add(
                        f'palette utility "{token}" in @apply',
                        _line_of(html, block.start(1) + apply.start()),
                    )
                elif RAW_COLOR_RE.match(base):
                    add(
                        f'raw colour utility "{token}" in @apply',
                        _line_of(html, block.start(1) + apply.start()),
                    )

        for selector in re.finditer(r"\.([A-Za-z][\w-]*(?::[\w-]+)*)", css):
            base = _base_class(selector.group(1))
            if PALETTE_RE.match(base):
                add(
                    f'palette utility class ".{selector.group(1)}" in <style>',
                    _line_of(html, block.start(1) + selector.start()),
                )
            elif RAW_COLOR_RE.match(base):
                add(
                    f'raw colour class ".{selector.group(1)}" in <style>',
                    _line_of(html, block.start(1) + selector.start()),
                )
    return findings


def _has_raw_colour(value: str) -> bool:
    lowered = value.strip().lower()
    if not lowered:
        return False
    if "var(" in lowered or lowered in ALLOWED_COLOR_KEYWORDS:
        return False
    if HEX_RE.search(value):
        return True
    if re.search(r"\b(?:rgba?|hsla?|oklch|oklab|lab|lch|color)\s*\(", lowered):
        return True
    words = re.findall(r"[a-z]+", re.sub(r"url\([^)]*\)", " ", lowered))
    if any(word in NAMED_COLOURS for word in words):
        return True
    if re.fullmatch(r"[a-z]+", lowered):
        return True
    return False


def _generated_type_steps(html: str) -> set[str]:
    """Read the generated type steps from ``--b-text-*`` declarations."""

    return {match.group(1) for match in TYPE_TOKEN_RE.finditer(html)}


def _check_type_scale(doc: _Document, html: str) -> list[str]:
    findings: list[str] = []
    seen: set[str] = set()
    steps = _generated_type_steps(html) or set(DEFAULT_TYPE_STEPS)
    allowed = steps | set(SEMANTIC_COLORS) | set(TEXT_UTILITIES)
    for element in doc.elements:
        for token in element.classes:
            base = _base_class(token)
            if not base.startswith("text-"):
                continue
            value = base[5:]
            if not value:
                continue
            size = value.split("/")[0]
            if size in allowed:
                continue
            if size.startswith("[") and (
                "var(--b-" in size or size.startswith("[color:")
            ):
                continue
            message = (
                f'text size "{token}" is not generated by the page scale '
                f'({" / ".join(sorted(steps))}) or a semantic colour'
            )
            if message not in seen:
                seen.add(message)
                findings.append(_finding("ERROR", "type-scale", message, element.line))
    return findings


def _spacing_unit(html: str) -> int:
    match = SPACING_UNIT_RE.search(html)
    return int(match.group(1)) if match else DEFAULT_SPACING_UNIT


def _step_off_scale(step: int, unit: int) -> bool:
    if unit == 4:
        return False
    return step in SKIPPED_SPACING_STEPS


def _check_spacing(doc: _Document, html: str) -> list[str]:
    findings: list[str] = []
    seen: set[str] = set()
    unit = _spacing_unit(html)

    def add(message: str, line: int) -> None:
        key = message
        if key not in seen:
            seen.add(key)
            findings.append(_finding("ERROR", "spacing", message, line))

    for element in doc.elements:
        for token in element.classes:
            base = _base_class(token)
            match = SPACING_RE.match(base)
            if not match:
                continue
            value = match.group("value")
            if "/" in value and not value.startswith("["):
                continue
            if value.startswith("["):
                inner = value[1:-1] if value.endswith("]") else value[1:]
                pixels = _arbitrary_pixels(inner)
                if pixels is not None and _off_unit(pixels, unit):
                    add(
                        f'spacing "{token}" is off the {unit}px unit '
                        f"(got {pixels:g}px)",
                        element.line,
                    )
                continue
            if value == "px":
                add(f'spacing "{token}" is 1px; use a {unit}px step', element.line)
                continue
            if value in SPACING_KEYWORDS:
                continue
            if re.fullmatch(r"\d+(?:\.\d+)?", value):
                if "." in value:
                    add(
                        f'spacing "{token}" is fractional; use a whole {unit}px step',
                        element.line,
                    )
                    continue
                step = int(value)
                if _step_off_scale(step, unit):
                    add(
                        f'spacing step {step} is outside the coarse {unit}px scale',
                        element.line,
                    )

        style = element.get("style")
        if not style:
            continue
        for prop, value in _style_declarations(style):
            if prop not in SPACING_PROPERTIES or "var(" in value:
                continue
            for pixels in _length_values(value):
                if _off_unit(pixels, unit):
                    add(
                        f"spacing {prop}: {value} is off the {unit}px unit "
                        f"(got {pixels:g}px)",
                        element.line,
                    )
    return findings


def _arbitrary_pixels(value: str) -> float | None:
    match = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)(px|rem)\s*", value, re.I)
    if not match:
        return None
    number = float(match.group(1))
    if match.group(2).lower() == "rem":
        number *= 16
    return number


def _length_values(value: str) -> list[float]:
    values: list[float] = []
    for match in re.finditer(r"(-?\d+(?:\.\d+)?)(px|rem)\b", value, re.I):
        number = float(match.group(1))
        if match.group(2).lower() == "rem":
            number *= 16
        values.append(number)
    return values


def _off_unit(pixels: float, unit: int) -> bool:
    magnitude = abs(pixels)
    if magnitude == 0:
        return False
    return magnitude % unit != 0


def _has_brand_gradient(html: str) -> bool:
    return bool(BRAND_GRADIENT_RE.search(html))


def _blank_brand_gradient(css: str) -> str:
    """Blank the ``--b-gradient`` declaration so its own stops are not flagged."""

    return BRAND_GRADIENT_RE.sub(
        lambda match: re.sub(r"[^\n]", " ", match.group(0)), css
    )


def _check_gradient(doc: _Document, html: str) -> list[str]:
    findings: list[str] = []
    has_brand_gradient = _has_brand_gradient(html)

    for block in STYLE_BLOCK_RE.finditer(html):
        css = _blank_brand_gradient(_blank_comments(block.group(1)))
        for name, _body, offset in _gradient_calls(css):
            line = _line_of(html, block.start(1) + offset)
            findings.append(
                _finding(
                    "ERROR",
                    "gradient",
                    f"{name} is an ad-hoc gradient; define --b-gradient and "
                    "use bg-grad-brand",
                    line,
                )
            )

    for element in doc.elements:
        style = element.get("style")
        if not style:
            continue
        for name, _body, _ in _gradient_calls(style):
            findings.append(
                _finding(
                    "ERROR",
                    "gradient",
                    f"{name} in an inline style; use the bg-grad-brand utility",
                    element.line,
                )
            )

    for element in doc.elements:
        for token in element.classes:
            base = _base_class(token)
            if base == "bg-grad-brand":
                if not has_brand_gradient:
                    findings.append(
                        _finding(
                            "ERROR",
                            "gradient",
                            "bg-grad-brand is used but --b-gradient is not defined",
                            element.line,
                        )
                    )
                continue
            if "gradient(" in base:
                findings.append(
                    _finding(
                        "ERROR",
                        "gradient",
                        f'ad-hoc gradient in class "{token}"; use bg-grad-brand',
                        element.line,
                    )
                )
                continue
            if GRADIENT_UTILITY_RE.match(base):
                findings.append(
                    _finding(
                        "ERROR",
                        "gradient",
                        f'ad-hoc gradient utility "{token}"; use bg-grad-brand',
                        element.line,
                    )
                )
        if element.tag in ("lineargradient", "radialgradient", "conicgradient"):
            findings.append(
                _finding(
                    "ERROR",
                    "gradient",
                    f"<{element.tag}> is an ad-hoc SVG gradient; use the brand token",
                    element.line,
                )
            )

    return findings


def _check_sprite(doc: _Document) -> list[str]:
    findings: list[str] = []
    body = doc.body
    # Every generated page carries the sprite (the app shell included), but the
    # sprite contract is enforced only on brand-facing formats: the app is a
    # product surface, so it stays exempt from the brand-proof requirement.
    if body is None or doc.page_format == "app":
        return findings

    sprite = next(
        (
            element
            for element in doc.elements
            if element.tag == "div" and "data-logo-sprite" in element.attrs
        ),
        None,
    )
    if sprite is None:
        sprite = next(
            (
                element
                for element in doc.elements
                if element.tag == "svg"
                and any(child.tag == "symbol" for child in element.children)
            ),
            None,
        )

    if sprite is None:
        findings.append(
            _finding(
                "ERROR",
                "sprite",
                "missing single-file logo sprite (<svg><symbol> at the top of <body>)",
            )
        )
        return findings

    symbols = [element for element in sprite.walk() if element.tag == "symbol"]
    if not symbols:
        findings.append(
            _finding("ERROR", "sprite", "logo sprite has no <symbol>", sprite.line)
        )
        return findings

    body_children = body.children
    if body_children and body_children[0] is not sprite:
        findings.append(
            _finding(
                "ERROR",
                "sprite",
                "logo sprite must be the first element inside <body>",
                sprite.line,
            )
        )
    if sprite.parent is not body:
        findings.append(
            _finding(
                "ERROR",
                "sprite",
                "logo sprite must be a direct child of <body>",
                sprite.line,
            )
        )

    symbol_ids = {
        symbol.get("id").strip() for symbol in symbols if symbol.get("id").strip()
    }
    if not symbol_ids:
        findings.append(
            _finding("ERROR", "sprite", "logo <symbol> needs an id", symbols[0].line)
        )

    for element in doc.by_tag("use"):
        href = element.get("href").strip() or element.get("xlink:href").strip()
        if not href.startswith("#"):
            continue
        if href[1:] not in symbol_ids:
            findings.append(
                _finding(
                    "ERROR",
                    "sprite",
                    f'<use href="{href}"> does not resolve to a sprite symbol',
                    element.line,
                )
            )
    return findings


def _check_logo_rules(doc: _Document) -> list[str]:
    findings: list[str] = []
    page_text = " ".join(
        element.text()
        for element in doc.elements
        if element.tag in ("li", "p", "dd", "dt", "h2", "h3", "figcaption")
    )

    if doc.page_format == "manual":
        for label, pattern in MISUSE_TERMS:
            if not re.search(pattern, page_text, re.I):
                findings.append(
                    _finding(
                        "ERROR",
                        "misuse",
                        f"manual must document the {label} logo misuse",
                    )
                )
        if not any(
            "misuse" in element.text().lower()
            or "uso proibido" in element.text().lower()
            for element in doc.elements
            if element.tag in HEADING_TAGS
        ):
            findings.append(
                _finding(
                    "WARN",
                    "misuse",
                    "manual has no 'Misuses (usos proibidos)' heading",
                )
            )

    comments = " ".join(comment for comment, _ in doc.comments)
    if doc.page_format != "app" and not re.search(
        r"breathing area|área de respiro|area de respiro", comments, re.I
    ):
        findings.append(
            _finding(
                "ERROR",
                "logo-breathing",
                "missing comment documenting the logo breathing area (S)",
            )
        )
    elif doc.page_format != "app" and not re.search(
        r"--b-space-1|space-1|\bS\b", comments
    ):
        findings.append(
            _finding(
                "WARN",
                "logo-breathing",
                "breathing-area comment does not name the S token (--b-space-1)",
            )
        )

    for element in doc.elements:
        classes = {_base_class(token) for token in element.classes}
        is_logo = (
            bool(classes & LOGO_CLASSES)
            or element.tag == "use"
            or (element.tag == "svg" and any(child.tag == "use" for child in element.children))
        )
        if is_logo:
            style = element.get("style")
            transform = element.get("transform")
            if re.search(
                r"transform\s*:[^;]*(?:rotate|scale[xy]?|skew)", style, re.I
            ) or re.search(r"(?:rotate|scale[xy]?|skew)", transform, re.I):
                findings.append(
                    _finding(
                        "ERROR",
                        "logo-misuse",
                        "logo must not be rotated, skewed or stretched",
                        element.line,
                    )
                )
            if re.search(r"filter\s*:", style, re.I):
                findings.append(
                    _finding(
                        "ERROR",
                        "logo-misuse",
                        "logo must not use filters or shadows",
                        element.line,
                    )
                )
            if any(
                token == "shadow"
                or token.startswith("shadow-")
                or token.startswith("drop-shadow")
                for token in classes
            ):
                findings.append(
                    _finding(
                        "ERROR",
                        "logo-misuse",
                        "logo must not use shadows",
                        element.line,
                    )
                )

        if element.tag in ("img", "image"):
            alt = element.get("alt").lower()
            src = element.get("src").lower() or element.get("href").lower()
            if "logo" in alt or "logo" in src:
                findings.append(
                    _finding(
                        "ERROR",
                        "logo-misuse",
                        "logo must be the inline sprite, not a raster/external image",
                        element.line,
                    )
                )
    return findings


LABEL_TAGS = frozenset(
    {
        "a",
        "button",
        "dd",
        "dt",
        "em",
        "figcaption",
        "label",
        "legend",
        "li",
        "p",
        "small",
        "span",
        "strong",
        "td",
        "th",
    }
)


def _adjacent_label(element: _Element) -> bool:
    """A nearby visible label: labelled parent or a text label sibling."""

    parent = element.parent
    if parent is None:
        return False
    if parent.get("aria-label").strip() or parent.get("title").strip():
        return True
    if parent.tag in BODY_TEXT_TAGS and parent.text().strip():
        return True
    siblings = parent.children
    try:
        index = siblings.index(element)
    except ValueError:
        return False
    for sibling in siblings[max(0, index - 1) : index + 2]:
        if sibling is element or sibling.tag not in LABEL_TAGS:
            continue
        if sibling.text().strip():
            return True
    return False


def _check_icons(doc: _Document) -> list[str]:
    """Iconify icons are decorative (hidden) or carry an accessible name."""

    findings: list[str] = []
    for element in doc.by_tag("iconify-icon"):
        name = element.get("icon").strip()
        if not name:
            findings.append(
                _finding(
                    "ERROR",
                    "icons",
                    "iconify-icon without an icon name",
                    element.line,
                )
            )
        if _is_hidden(element) or element.get("aria-hidden").strip().lower() == "true":
            continue
        labelled = any(
            element.get(attribute).strip()
            for attribute in ("aria-label", "aria-labelledby", "title")
        )
        if labelled or _adjacent_label(element):
            continue
        findings.append(
            _finding(
                "ERROR",
                "icons",
                f'iconify-icon "{name}" needs aria-label, an adjacent label, '
                'or aria-hidden="true"',
                element.line,
            )
        )
    return findings


def _check_images(doc: _Document) -> list[str]:
    """Every image declares alt; ``alt=""`` is the valid decorative form."""

    findings: list[str] = []
    for element in doc.by_tag("img"):
        if _is_hidden(element):
            continue
        if "alt" not in element.attrs:
            findings.append(
                _finding(
                    "ERROR",
                    "images",
                    'img without alt (use alt="" when decorative)',
                    element.line,
                )
            )
    return findings


def _check_semantic_tokens(doc: _Document) -> list[str]:
    findings: list[str] = []
    for element in doc.elements:
        tokens = element.classes
        bases = {_base_class(token) for token in tokens}

        if "text-primary" in bases and not _is_hidden(element):
            if element.tag in BODY_TEXT_TAGS:
                findings.append(
                    _finding(
                        "ERROR",
                        "tokens",
                        f"text-primary on <{element.tag}>; body text uses text-link or text-fg",
                        element.line,
                    )
                )
            elif element.tag not in HEADING_TAGS:
                findings.append(
                    _finding(
                        "WARN",
                        "tokens",
                        f"text-primary on <{element.tag}>; reserve primary for UI/large text",
                        element.line,
                    )
                )

        if element.tag in CONTROL_TAGS:
            if bases & {"border-line", "border-line-strong"} and "border-line-input" not in bases:
                findings.append(
                    _finding(
                        "ERROR",
                        "tokens",
                        "control boundary must use border-line-input (WCAG 1.4.11)",
                        element.line,
                    )
                )

        if "bg-primary" in bases and not any(
            "hover:" in token and token.endswith("bg-primary-hover")
            for token in tokens
        ):
            findings.append(
                _finding(
                    "WARN",
                    "tokens",
                    "bg-primary fill without hover:bg-primary-hover",
                    element.line,
                )
            )
    return findings


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _finalize(findings: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for finding in findings:
        if finding not in seen:
            seen.add(finding)
            unique.append(finding)

    def sort_key(finding: str) -> tuple[int, int, str]:
        line_match = re.search(r" line (\d+)", finding)
        line = int(line_match.group(1)) if line_match else 0
        return (0 if finding.startswith("ERROR") else 1, line, finding)

    return sorted(unique, key=sort_key)


def _check_brand(brand_path: str | Path, html: str) -> list[str]:
    """Optional strict validation: parse the brand and match ``<html lang>``."""

    try:
        data = build_theme.load_brand(brand_path)
    except (build_theme.BrandError, OSError, ValueError) as exc:
        return [_finding("ERROR", "brand", str(exc))]

    findings: list[str] = []
    expected = str(data.get("language") or build_theme.DEFAULT_LANGUAGE)
    for element in _parse(html).by_tag("html"):
        actual = element.get("lang").strip()
        if actual and actual.casefold() != expected.casefold():
            findings.append(
                _finding(
                    "ERROR",
                    "language",
                    f'html lang="{actual}" disagrees with brand language "{expected}"',
                    element.line,
                )
            )
    return findings


def check_html(html: str) -> list[str]:
    """Check an HTML string and return the findings (strings, ERROR/WARN)."""

    doc = _parse(html)
    findings: list[str] = []
    findings.extend(_check_document(doc, html))
    findings.extend(_check_theme(doc, html))
    findings.extend(_check_structure(doc))
    findings.extend(_check_assets(doc))
    findings.extend(_check_events(doc))
    findings.extend(_check_a11y_names(doc))
    findings.extend(_check_icons(doc))
    findings.extend(_check_images(doc))
    findings.extend(_check_tables(doc))
    findings.extend(_check_tokens(doc, html))
    findings.extend(_check_type_scale(doc, html))
    findings.extend(_check_spacing(doc, html))
    findings.extend(_check_gradient(doc, html))
    findings.extend(_check_sprite(doc))
    findings.extend(_check_logo_rules(doc))
    findings.extend(_check_semantic_tokens(doc))
    return _finalize(findings)


def check_page(
    html_path: str | Path, brand_path: str | Path | None = None
) -> list[str]:
    """Read ``html_path`` and return findings; raises ``OSError`` if unreadable.

    ``brand_path`` is optional. When given, the brand file must exist and parse
    as a v2 brand (via ``build_theme.load_brand``); failures become findings.
    """

    path = Path(html_path)
    html = path.read_text(encoding="utf-8")
    findings = check_html(html)
    if brand_path is not None:
        findings = _finalize(_check_brand(brand_path, html) + findings)
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Static brand checker for single-file HTML pages."
    )
    parser.add_argument("files", nargs="+", help="HTML files to check")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 when only WARN findings remain",
    )
    parser.add_argument(
        "--brand",
        default=None,
        metavar="brand.json",
        help="also validate the v2 brand file (optional)",
    )
    args = parser.parse_args(argv)

    total_errors = 0
    total_warnings = 0
    failed = False
    for name in args.files:
        try:
            findings = check_page(name, args.brand)
        except (OSError, UnicodeError) as exc:
            print(f"check_page: {name}: {exc}", file=sys.stderr)
            return 2

        errors = sum(1 for finding in findings if finding.startswith("ERROR"))
        warnings = sum(1 for finding in findings if finding.startswith("WARN"))
        total_errors += errors
        total_warnings += warnings

        for finding in findings:
            print(finding)

        if errors or (args.strict and warnings):
            failed = True
            print(f"FAIL: {name} ({errors} ERROR, {warnings} WARN)")
        else:
            print(f"ok: {name} ({errors} ERROR, {warnings} WARN)")

    if failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
