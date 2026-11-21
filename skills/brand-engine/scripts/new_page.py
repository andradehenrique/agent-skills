#!/usr/bin/env python3
"""Brand Engine page generator: one self-contained HTML file per format.

Reads the approved ``brand.json``, reuses the Task 2 theme builder, and writes
a single-file page. Formats and their job:

``manual``   brand manual (the approval artifact)
``onepage``  landing page: hero, proof, CTA
``deck``     1280x720 container-query slides with keyboard navigation
``report``   long-form report with tables that carry ``caption`` and ``th``
``social``   1080x1080 and 1080x1920 HTML mockups (reference, not an export)
``blank``    the shell with logo, title and theme toggle

Every page embeds the same pieces, in this order:

1. a ``<head>`` with the pinned Tailwind CDN, Google Fonts link, generated
   ``theme.css`` (``--b-*`` tokens, light/dark), the no-flash theme script,
   and ``tailwind-theme.css`` (semantic utilities);
2. the logo sprite as ``<svg><symbol ...>`` at the very top of ``<body>``;
3. the per-format skeleton.

Token rules inherited from Task 2 (binding):

- body text uses ``text-fg`` / ``text-fg-muted`` / ``text-link``, never
  ``text-primary``;
- buttons may use ``bg-primary`` + ``text-on-primary`` and
  ``hover:bg-primary-hover``;
- control boundaries use ``border-line-input``; ``border-line`` and
  ``border-line-strong`` are decorative;
- the only gradient is ``bg-grad-brand`` (two stops, 50/50, 45deg).

Public API::

    new_page(fmt, brand, title, out, theme="light", force=False) -> Path

``brand`` is a ``brand.json`` path. ``out`` is either an ``.html`` file path or
a directory (the file is then ``<fmt>.html``). The path of the written file is
returned; use ``render_page()`` when you need the HTML string without I/O.
Existing files are never replaced without ``force=True`` (CLI ``--force``).

CLI::

    python3 scripts/new_page.py --brand brand.json --format onepage \
        --title "Forno & Brasa" --out landing.html

Brand discovery follows ``build_theme.resolve_brand_path``:
``--brand`` > ``./brand.json`` > ``./brand/brand.json`` > ask the user.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path
from urllib.parse import quote_plus

from build_theme import (
    BrandError,
    contrast_ratio,
    load_brand,
    render_theme,
    resolve_brand_path,
)

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
SKELETONS = ASSETS / "skeletons"

FORMATS = ("manual", "onepage", "deck", "report", "social", "blank")
THEMES = ("light", "dark", "system", "light-only", "dark-only")
TAILWIND_VERSION = "4.3.3"  # pinned @tailwindcss/browser; test before bumping

# Deterministic opposites for the manual's NÃO SOMOS column. Unknown
# attributes stay an explicit placeholder instead of an invented word.
ANTONYMS = {
    "acolhedor": "distante",
    "afetivo": "impessoal",
    "artesanal": "industrial",
    "classico": "efêmero",
    "clássico": "efêmero",
    "confiavel": "arriscado",
    "confiável": "arriscado",
    "caloroso": "frio",
    "direto": "evasivo",
    "divertido": "sério",
    "elegante": "desleixado",
    "energetico": "apático",
    "energético": "apático",
    "humano": "robótico",
    "jovem": "sisudo",
    "minimalista": "carregado",
    "moderno": "datado",
    "ousado": "tímido",
    "popular": "exclusivo",
    "premium": "barato",
    "robótico": "distante",
    "rustico": "artificial",
    "rústico": "artificial",
    "serio": "leviano",
    "sério": "leviano",
    "simples": "confuso",
    "sofisticado": "popular",
    "sustentavel": "descartável",
    "sustentável": "descartável",
    "tecnico": "vago",
    "técnico": "vago",
    "timido": "exagerado",
    "tímido": "exagerado",
}

THEME_JS = """(function () {
  var root = document.documentElement;
  var KEY = "be-theme";
  var lock = root.getAttribute("data-theme-lock");
  function stored() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function save(v) { try { localStorage.setItem(KEY, v); } catch (e) {} }
  function initial() {
    if (lock === "light" || lock === "dark") return lock;
    var s = stored();
    if (s === "light" || s === "dark") return s;
    var d = root.getAttribute("data-theme-default") || "light";
    if (d === "system") return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    return d === "dark" ? "dark" : "light";
  }
  function apply(t) {
    root.setAttribute("data-theme", t);
    var btns = document.querySelectorAll("[data-theme-toggle]");
    for (var i = 0; i < btns.length; i++) {
      btns[i].setAttribute("aria-pressed", t === "dark" ? "true" : "false");
      btns[i].setAttribute("aria-label", "Alternar tema claro/escuro");
      btns[i].setAttribute("title", "Alternar tema claro/escuro");
    }
  }
  apply(initial());
  window.beToggleTheme = function () {
    if (lock) return;
    var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    apply(next); save(next);
  };
  document.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest("[data-theme-toggle]");
    if (b) { e.preventDefault(); window.beToggleTheme(); }
  });
  document.addEventListener("DOMContentLoaded", function () { apply(root.getAttribute("data-theme")); });
  var before;
  addEventListener("beforeprint", function () { before = root.getAttribute("data-theme"); root.setAttribute("data-theme", "light"); });
  addEventListener("afterprint", function () { if (before) root.setAttribute("data-theme", before); });
})();"""

DECK_JS = """(function () {
  var root = document.documentElement;
  var W = 1280, H = 720, BAR = 56;
  var slides = [].slice.call(document.querySelectorAll("[data-slide]"));
  if (!slides.length) return;
  var i = 0;
  slides.forEach(function (s, n) {
    s.setAttribute("role", "group");
    s.setAttribute("aria-roledescription", "slide");
    var base = s.getAttribute("aria-label") || ("Slide " + (n + 1));
    s.setAttribute("aria-label", (n + 1) + " de " + slides.length + ": " + base);
  });
  var counter = document.querySelector("[data-deck-counter]");
  var bar = document.querySelector("[data-deck-progress] .be-progress");

  function mode() {
    var m = innerWidth >= 900 && innerWidth > innerHeight ? "present" : "scroll";
    if (root.getAttribute("data-deck-mode") !== m) root.setAttribute("data-deck-mode", m);
    return m;
  }
  function scale() {
    var s = Math.min(innerWidth / W, (innerHeight - BAR) / H) * 0.96;
    root.style.setProperty("--be-scale", s.toFixed(4));
  }
  function checkOverflow() {
    if (root.getAttribute("data-deck-mode") !== "present") return;
    slides.forEach(function (s, n) {
      var over = s.scrollHeight > H + 1 || s.scrollWidth > W + 1;
      if (over) { s.setAttribute("data-overflow", ""); console.warn("[brand-engine] slide " + (n + 1) + " estourou 1280x720"); }
      else s.removeAttribute("data-overflow");
    });
  }
  function go(n, fromHash) {
    i = Math.max(0, Math.min(slides.length - 1, n));
    slides.forEach(function (s, k) {
      s.setAttribute("aria-current", k === i ? "true" : "false");
      if (root.getAttribute("data-deck-mode") === "present") s.setAttribute("aria-hidden", k === i ? "false" : "true");
      else s.removeAttribute("aria-hidden");
    });
    if (counter) counter.textContent = (i + 1) + " / " + slides.length;
    if (bar) bar.style.width = ((i + 1) / slides.length * 100) + "%";
    if (!fromHash) { try { history.replaceState(null, "", "#" + (i + 1)); } catch (e) {} }
  }
  function layout() { var m = mode(); if (m === "present") scale(); go(i, true); checkOverflow(); }

  addEventListener("resize", layout);
  addEventListener("hashchange", function () { go((parseInt(location.hash.slice(1), 10) || 1) - 1, true); });
  document.addEventListener("keydown", function (e) {
    if (e.target.closest && e.target.closest("input, textarea, select, [contenteditable]")) return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    var present = root.getAttribute("data-deck-mode") === "present";
    var k = e.key;
    if (present && (k === "ArrowRight" || k === "PageDown" || k === " ")) { e.preventDefault(); go(i + 1); }
    else if (present && (k === "ArrowLeft" || k === "PageUp")) { e.preventDefault(); go(i - 1); }
    else if (present && k === "Home") go(0);
    else if (present && k === "End") go(slides.length - 1);
    else if (k === "t" || k === "T") window.beToggleTheme && window.beToggleTheme();
    else if ((k === "f" || k === "F") && document.fullscreenEnabled) {
      document.fullscreenElement ? document.exitFullscreen() : root.requestFullscreen();
    }
  });
  document.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest("[data-deck-prev],[data-deck-next]");
    if (!b) return;
    go(i + (b.hasAttribute("data-deck-next") ? 1 : -1));
  });
  var x0 = null;
  document.addEventListener("touchstart", function (e) { x0 = e.touches[0].clientX; }, { passive: true });
  document.addEventListener("touchend", function (e) {
    if (x0 === null || root.getAttribute("data-deck-mode") !== "present") return;
    var dx = e.changedTouches[0].clientX - x0; x0 = null;
    if (Math.abs(dx) > 50) go(i + (dx < 0 ? 1 : -1));
  }, { passive: true });

  i = (parseInt(location.hash.slice(1), 10) || 1) - 1;
  layout();
  addEventListener("load", function () { setTimeout(checkOverflow, 300); });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { setTimeout(checkOverflow, 300); });
})();"""

ICON_MOON = (
    '<svg class="be-icon-moon size-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M20.985 12.486a9 9 0 1 1-9.473-9.472c.405-.022.617.46.402.803a6 6 0 0 0 8.268 8.268c.344-.215.825-.004.803.401"/>'
    "</svg>"
)
ICON_SUN = (
    '<svg class="be-icon-sun size-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>'
    "</svg>"
)
THEME_TOGGLE = (
    '<button type="button" data-theme-toggle aria-label="Alternar tema claro/escuro" '
    'aria-pressed="false" class="inline-flex size-6 items-center justify-center rounded-full '
    'border border-line-input bg-surface text-fg-muted hover:bg-surface-muted hover:text-fg">'
    + ICON_MOON
    + ICON_SUN
    + "</button>"
)

# Placeholder sprite. The generator has no logo geometry in brand.json: the
# approved logo.svg from the theme/logo phase replaces this mark's path.
SPRITE = (
    '<div hidden aria-hidden="true" data-logo-sprite>'
    '<svg><symbol id="be-mark" viewBox="0 0 32 32">'
    '<path d="M4 28V14a12 12 0 0 1 24 0v14h-7V14a5 5 0 0 0-10 0v14H4Z"/>'
    '<circle cx="16" cy="23" r="2.5"/>'
    "</symbol></svg>"
    "</div>"
)


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _strip_css_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _read(rel: str) -> str:
    return (ASSETS / rel).read_text(encoding="utf-8")


def _font_links(brand: dict) -> str:
    families: list[str] = []
    for role in ("display", "body"):
        family = brand["fonts"][role]["family"]
        if family not in families:
            families.append(family)
    # No weight axis on purpose: single-weight display families reject
    # ``wght@400;600;700`` and would lose the whole stylesheet. The CSS stack
    # from brand.json remains the safety net when a family is not on Google.
    query = "&".join(f"family={quote_plus(family)}" for family in families)
    return (
        '<link href="https://fonts.googleapis.com/css2?'
        + query
        + '&display=swap" rel="stylesheet">'
    )


def _type_scale(theme_css: str) -> list[tuple[str, int, str]]:
    """Read the generated scale back from theme.css (single source of truth)."""

    sizes: list[tuple[str, int]] = []
    for match in re.finditer(r"--b-text-([a-z0-9]+):\s*(\d+)px;", theme_css):
        name = match.group(1)
        if name not in {item[0] for item in sizes}:
            sizes.append((name, int(match.group(2))))
    leadings = dict(re.findall(r"--b-leading-([a-z0-9]+):\s*([0-9.]+);", theme_css))
    return [(name, size, leadings.get(name, "")) for name, size in sizes]


def _color_tokens(theme_css: str) -> dict[str, str]:
    tokens: dict[str, str] = {}
    for slug, value in re.findall(
        r"--b-color-([\w-]+):\s*(#[0-9A-Fa-f]{6});", theme_css
    ):
        tokens.setdefault(value.upper(), slug)
    return tokens


def _rgb(value: str) -> str:
    red, green, blue = (int(value[index : index + 2], 16) for index in (1, 3, 5))
    return f"{red} {green} {blue}"


def _initials(name: str) -> str:
    words = [word for word in re.split(r"\s+", name.strip()) if word]
    if not words:
        return "B"
    if len(words) == 1:
        return words[0][:1].upper()
    return (words[0][:1] + words[1][:1]).upper()


def _mark(size_class: str = "") -> str:
    classes = ("be-mark " + size_class).strip()
    return (
        f'<svg class="{classes}" aria-hidden="true"><use href="#be-mark"/></svg>'
    )


def _wordmark(name: str) -> str:
    return f'<span class="be-wordmark">{_esc(name)}</span>'


def _monogram(name: str) -> str:
    return (
        f'<span class="be-monogram" aria-hidden="true">{_esc(_initials(name))}</span>'
    )


def _lockup(variant: str, name: str) -> str:
    if variant == "C":
        inner = _mark() + _wordmark(name)
    elif variant == "B":
        inner = _monogram(name)
    else:
        inner = _wordmark(name)
    return (
        f'<span class="be-brand" role="img" aria-label="{_esc(name)}">{inner}</span>'
    )


def _logo_for_nav(variant: str, name: str) -> str:
    if variant == "C":
        return (
            f'<svg class="be-mark size-3 text-accent" role="img" aria-label="{_esc(name)}">'
            '<use href="#be-mark"/></svg>'
        )
    if variant == "B":
        return (
            f'<span class="be-monogram" role="img" aria-label="{_esc(name)}">'
            f"{_esc(_initials(name))}</span>"
        )
    return (
        f'<span class="be-wordmark text-sm text-accent" role="img" aria-label="{_esc(name)}">'
        f"{_esc(name)}</span>"
    )


def _logo_size_samples(variant: str, name: str) -> str:
    items: list[str] = []
    for pixels in (16, 24, 48):
        if variant == "C":
            body = (
                f'<svg class="be-mark" style="width:{pixels}px;height:{pixels}px" '
                'aria-hidden="true"><use href="#be-mark"/></svg>'
            )
        elif variant == "B":
            font = max(10, pixels // 2)
            body = (
                f'<span class="be-monogram" aria-hidden="true" style="width:{pixels}px;'
                f'height:{pixels}px;font-size:{font}px">{_esc(_initials(name))}</span>'
            )
        else:
            body = f'<span class="be-wordmark" style="font-size:{pixels}px">{_esc(name)}</span>'
        items.append(
            f'<div class="border border-dashed border-line-strong p-1">{body}</div>'
        )
    return "\n        ".join(items)


def _color_cards(brand: dict, tokens: dict[str, str]) -> str:
    cards: list[str] = []
    for group in ("primary", "secondary"):
        for color in brand["colors"][group]:
            value = color["hex"].upper()
            slug = tokens.get(value)
            if slug is None:
                raise RuntimeError(f"theme.css is missing --b-color-* for {value}")
            note = color.get("note") or "sem nota"
            cards.append(
                "\n".join(
                    (
                        '<article class="rounded-lg border border-line bg-surface p-3">',
                        f'  <div class="be-swatch h-10" style="background-color: var(--b-color-{slug})" '
                        f'role="img" aria-label="Amostra da cor {_esc(color["name"])}"></div>',
                        f'  <h3 class="mt-2 text-lg font-semibold">{_esc(color["name"])}</h3>',
                        '  <dl class="mt-2 space-y-1 text-xs">',
                        f'    <div class="flex justify-between gap-2"><dt class="text-fg-subtle">HEX</dt>'
                        f'<dd class="font-medium">{_esc(value)}</dd></div>',
                        f'    <div class="flex justify-between gap-2"><dt class="text-fg-subtle">RGB</dt>'
                        f"<dd>{_rgb(value)}</dd></div>",
                        '    <div class="flex justify-between gap-2"><dt class="text-fg-subtle">Pantone</dt>'
                        '<dd class="text-right">[placeholder — confirmar]</dd></div>',
                        f'    <div class="flex justify-between gap-2"><dt class="text-fg-subtle">Token</dt>'
                        f"<dd>--b-color-{slug}</dd></div>",
                        "  </dl>",
                        f'  <p class="mt-2 text-xs text-fg-subtle">{_esc(group)} · {_esc(note)}</p>',
                        "</article>",
                    )
                )
            )
    return "\n        ".join(cards)


def _pair_rows(brand: dict) -> str:
    lookup: dict[str, dict] = {}
    for group in ("primary", "secondary"):
        for color in brand["colors"][group]:
            lookup[color["name"].casefold()] = color

    rows: list[str] = []
    for pair in brand["allowed_pairs"]:
        background = lookup.get(str(pair["bg"]).casefold())
        foreground = lookup.get(str(pair["fg"]).casefold())
        if background is None or foreground is None:
            raise RuntimeError(f"allowed_pairs references an unknown colour: {pair}")
        ratio = contrast_ratio(foreground["hex"], background["hex"])
        verdict = "AA" if ratio >= 4.5 else ("AA (texto grande)" if ratio >= 3.0 else "Falha AA")
        rows.append(
            "<tr>"
            f'<td class="font-medium">{_esc(background["name"])}</td>'
            f"<td>{_esc(foreground['name'])}</td>"
            f'<td class="tabular-nums">{ratio:.2f}:1</td>'
            f"<td>{verdict}</td>"
            f'<td>{_esc(pair.get("use") or "—")}</td>'
            "</tr>"
        )
    return "\n            ".join(rows)


def _type_rows(theme_css: str) -> str:
    rows: list[str] = []
    for name, size, leading in _type_scale(theme_css):
        rows.append(
            "<tr>"
            f'<td class="font-medium">text-{name}</td>'
            f'<td class="tabular-nums">{size}px</td>'
            f'<td class="tabular-nums">{leading}</td>'
            f'<td><span class="text-{name}">Aa</span></td>'
            "</tr>"
        )
    return "\n            ".join(rows)


def _somos_list(attributes: list[str]) -> str:
    return "\n            ".join(f"<li>{_esc(item)}</li>" for item in attributes)


def _nao_somos_list(attributes: list[str]) -> str:
    items: list[str] = []
    for attribute in attributes:
        opposite = ANTONYMS.get(attribute.casefold())
        text = opposite if opposite else f"[placeholder — oposto de {attribute}]"
        items.append(f"<li>{_esc(text)}</li>")
    return "\n            ".join(items)


def _chips(attributes: list[str]) -> str:
    return "\n        ".join(
        f'<li class="rounded-full border border-line bg-surface px-2 py-1 text-xs text-fg-muted">{_esc(item)}</li>'
        for item in attributes
    )


def _theme_parts(theme: str) -> tuple[str, str]:
    if theme.endswith("-only"):
        mode = theme.split("-")[0]
        return mode, f' data-theme-lock="{mode}"'
    return theme, ""


def render_page(fmt: str, brand: dict, title: str, theme: str = "light") -> str:
    """Render one format from an already loaded brand object."""

    if fmt not in FORMATS:
        raise ValueError(f"unknown format {fmt!r} (choose from {', '.join(FORMATS)})")
    if theme not in THEMES:
        raise ValueError(f"unknown theme {theme!r} (choose from {', '.join(THEMES)})")

    built = render_theme(brand)
    theme_css = built.theme_css
    tailwind_css = built.tailwind_theme_css

    name = brand.get("name") or "Brand"
    attributes = [str(item) for item in brand["attributes"]]
    variant = brand["logo"]["variant"]
    logo_notes = brand["logo"].get("notes") or "Geometria e proporção definidas na fase de logo."

    theme_default, theme_lock = _theme_parts(theme)
    safe_title = _esc(title)

    mapping = {
        "TITLE": safe_title,
        "BRAND_NAME": _esc(name),
        "PURPOSE": _esc(brand["purpose"]),
        "PERSONA": _esc(brand["persona"]),
        "TERRITORY": _esc(brand["territory"]),
        "ARCHETYPE": _esc(brand["archetype"]),
        "ATTRIBUTE_LEAD": _esc(" · ".join(attributes[:2])),
        "ATTRIBUTE_CHIPS": _chips(attributes),
        "HEADLINE": safe_title,
        "SOMOS_LIST": _somos_list(attributes),
        "NAO_SOMOS_LIST": _nao_somos_list(attributes),
        "COLOR_CARDS": _color_cards(brand, _color_tokens(theme_css)),
        "PAIR_ROWS": _pair_rows(brand),
        "TYPE_ROWS": _type_rows(theme_css),
        "GRADIENT_FROM": _esc(brand["gradient"]["from"]),
        "GRADIENT_TO": _esc(brand["gradient"]["to"]),
        "FONT_DISPLAY": _esc(brand["fonts"]["display"]["family"]),
        "FONT_BODY": _esc(brand["fonts"]["body"]["family"]),
        "SCALE_BASE": _esc(brand["scale"]["base"]),
        "SCALE_RATIO": _esc(brand["scale"]["ratio"]),
        "LOGO_VARIANT": _esc(variant),
        "LOGO_NOTES": _esc(logo_notes),
        "LOGO_C": _lockup("C", name),
        "LOGO_B": _lockup("B", name),
        "LOGO_A": _lockup("A", name),
        "LOGO_HEADER": _lockup(variant, name),
        "LOGO_MARK_ONLY": _logo_for_nav(variant, name),
        "LOGO_SIZE_SAMPLES": _logo_size_samples(variant, name),
        "LOGO_BREATHING": f"{brand['unit']}px",
        "THEME_TOGGLE": THEME_TOGGLE,
        "THEME_DEFAULT": theme_default,
        "THEME_LOCK": theme_lock,
        "THEME_JS": THEME_JS,
        "THEME_CSS": _strip_css_comments(theme_css).strip(),
        "TAILWIND_THEME": _strip_css_comments(tailwind_css).strip(),
        "TAILWIND_VERSION": TAILWIND_VERSION,
        "FONT_LINKS": _font_links(brand),
    }

    body = _read(f"skeletons/{fmt}.html")
    for key, value in mapping.items():
        body = body.replace("{{" + key + "}}", value)

    if "<body" not in body:
        raise RuntimeError(f"skeleton {fmt}.html has no <body>")
    body = re.sub(
        r"(<body[^>]*>)", lambda match: match.group(1) + "\n  " + SPRITE, body, count=1
    )

    page = _read("base.html")
    for key, value in mapping.items():
        page = page.replace("{{" + key + "}}", value)
    page = page.replace("{{BODY}}", body.strip())
    if fmt == "deck":
        page = page.replace("</body>", "<script>\n" + DECK_JS + "\n</script>\n</body>")

    leftover = re.findall(r"\{\{[A-Z0-9_]+\}\}", page)
    if leftover:
        raise RuntimeError(f"unreplaced placeholders in {fmt}: {sorted(set(leftover))}")
    return page


def _destination(out: str | Path, fmt: str) -> Path:
    path = Path(out).expanduser()
    if path.suffix.lower() in (".html", ".htm"):
        return path
    if path.suffix:
        raise ValueError(f"{path}: --out must be a directory or an .html file")
    if path.exists() and not path.is_dir():
        raise ValueError(f"{path}: --out must be a directory or an .html file")
    return path / f"{fmt}.html"


def new_page(
    fmt: str,
    brand: str | Path,
    title: str,
    out: str | Path,
    theme: str = "light",
    force: bool = False,
) -> Path:
    """Render and write one format; return the path of the written file.

    ``out`` is an ``.html`` path or a directory (``<fmt>.html`` is written).
    """

    if fmt not in FORMATS:
        raise ValueError(f"unknown format {fmt!r} (choose from {', '.join(FORMATS)})")
    if theme not in THEMES:
        raise ValueError(f"unknown theme {theme!r} (choose from {', '.join(THEMES)})")
    data = load_brand(brand)
    page = render_page(fmt, data, title, theme)

    destination = _destination(out, fmt)
    if destination.exists() and not force:
        raise FileExistsError(
            f"refusing to overwrite {destination} without --force"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(page, encoding="utf-8")
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a branded single-file HTML page from brand.json."
    )
    parser.add_argument("--brand", help="path to brand.json (flag wins over discovery)")
    parser.add_argument("--format", required=True, choices=FORMATS)
    parser.add_argument("--title", required=True)
    parser.add_argument(
        "--out", required=True, help="output .html file (or directory to hold <format>.html)"
    )
    parser.add_argument("--theme", default="light", choices=THEMES)
    parser.add_argument("--force", action="store_true", help="replace an existing output file")
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
        destination = _destination(args.out, args.format)
        new_page(
            args.format,
            brand_path,
            args.title,
            destination,
            theme=args.theme,
            force=args.force,
        )
    except (BrandError, FileExistsError, OSError, ValueError) as exc:
        print(f"new_page: {exc}", file=sys.stderr)
        return 2

    print(f"ok: {destination} ({args.format}, tema {args.theme})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
