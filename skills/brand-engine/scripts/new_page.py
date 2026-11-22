#!/usr/bin/env python3
"""Brand Engine v2 page generator: one self-contained HTML file per format.

Reads the approved ``brand.json`` v2, reuses the theme builder, and writes a
single-file starter page. Formats and their job:

``manual``     brand manual (the approval artifact and gate)
``onepage``    landing page: hero, proof, reasons, CTA
``deck``       1280x720 container-query slides with keyboard navigation
``report``     long-form report with accessible tables and one chart
``social``     1080x1080 and 1080x1920 HTML mockups (reference, not export)
``app``        application shell: topbar, sidebar, stats, list, states, form
``brand-kit``  living proof of the system plus the mini cases
``blank``      the shell with logo, title and theme toggle

Every page embeds, in this order:

1. a ``<head>`` with the pinned Tailwind CDN, Google Fonts link, generated
   ``theme.css`` (``--b-*`` tokens, optional light/dark), the no-flash theme
   script, and ``tailwind-theme.css`` (semantic utilities);
2. the logo sprite as ``<svg><symbol ...>`` at the very top of ``<body>``;
3. the per-format skeleton.

Token rules inherited from the theme builder (binding):

- body text uses ``text-fg`` / ``text-fg-muted`` / ``text-link``, never
  ``text-primary``;
- buttons may use ``bg-primary`` + ``text-on-primary`` and
  ``hover:bg-primary-hover``;
- control boundaries use ``border-line-input``; ``border-line`` and
  ``border-line-strong`` are decorative;
- the only gradient is ``bg-grad-brand`` and only when the brand defines one.

External CDNs are conditional:

- Iconify (``<iconify-icon>``) only on formats whose skeletons use it;
- Chart.js only on ``report``, ``app`` and ``brand-kit``, the formats with a
  ``<canvas>``;
- ``placehold.co`` for image placeholders, with the brand colours and a
  ``data-placehold-dark`` variant when the brand has both modes.

Public API::

    new_page(fmt, brand, title, out, theme=None, force=False) -> Path
    render_page(fmt, brand, title, theme=None) -> str

``brand`` is a ``brand.json`` path (``new_page``) or the raw dict returned by
``build_theme.load_brand`` (``render_page``). ``out`` is either an ``.html``
file path or a directory (the file is then ``<fmt>.html``). Existing files are
never replaced without ``force=True`` (CLI ``--force``).

``restyle(page, brand)`` (CLI ``--restyle``) replaces only the generated
``theme.css``/``tailwind-theme.css`` blocks of an existing page, preserving the
composed body. It is the post-delivery adjustment path; full regeneration still
requires ``--force`` and an explicit user request.

``language`` (BCP-47, default ``pt-BR``) is emitted as the ``<html lang>``
attribute. The skeleton copy is pt-BR; translate it when the brand language is
different.

``theme`` accepts ``light|dark|system|light-only|dark-only``: ``system`` only
when the brand has both modes, ``*-only`` only when that mode exists. ``None``
follows ``design.theme.default``. Single-mode brands are locked and render no
toggle.

CLI::

    python3 scripts/new_page.py --brand brand.json --format onepage \
        --title "Forno & Brasa" --out landing.html

Brand discovery follows ``build_theme.resolve_brand_path``:
``--brand`` > ``./brand.json`` > ``./brand/brand.json`` > ask the user.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import quote_plus

from build_theme import (
    BrandError,
    contrast_ratio,
    load_brand,
    normalize_brand,
    render_theme,
    resolve_brand_path,
)

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
SKELETONS = ASSETS / "skeletons"

FORMATS = (
    "manual",
    "onepage",
    "deck",
    "report",
    "social",
    "app",
    "brand-kit",
    "blank",
)

THEMES = ("light", "dark", "system", "light-only", "dark-only")
DEFAULT_THEME_MODES = ("light", "dark")

# Formats whose skeletons actually render ``<iconify-icon>``. Deck and social
# use inline SVG only, so they do not need the ~24KB CDN component.
FORMAT_ICONS = frozenset({"manual", "onepage", "report", "app", "brand-kit"})
# Formats with a <canvas> and a BrandCharts call in the skeleton.
FORMAT_CHARTS = frozenset({"report", "app", "brand-kit"})

TAILWIND_VERSION = "4.3.3"  # pinned @tailwindcss/browser; test before bumping
ICONIFY_VERSION = "3.0.0"  # pinned iconify-icon web component
CHARTJS_VERSION = "4.4.7"  # pinned Chart.js UMD build

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

DIRECTION_NOTES = {
    "editorial": "manchete grande, coluna de leitura e imagens com respiro",
    "structured": "grid explícito, blocos alinhados e densidade média",
    "poster": "tipografia grande, contraste alto e poucos elementos",
    "minimal": "muito espaço, hierarquia por peso e posição",
}

ROLE_LABELS = {
    "canvas": "fundo",
    "surface": "superfície",
    "ink": "texto",
    "primary": "ação",
    "accent": "destaque",
    "support": "apoio",
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
  function swapPlaceholders(t) {
    var imgs = document.querySelectorAll("img[data-placehold-dark]");
    for (var j = 0; j < imgs.length; j++) {
      var img = imgs[j];
      if (!img.getAttribute("data-placehold-light")) {
        img.setAttribute("data-placehold-light", img.getAttribute("src") || "");
      }
      var next = t === "dark"
        ? img.getAttribute("data-placehold-dark")
        : img.getAttribute("data-placehold-light");
      if (next) img.setAttribute("src", next);
    }
  }
  function apply(t) {
    root.setAttribute("data-theme", t);
    var btns = document.querySelectorAll("[data-theme-toggle]");
    for (var i = 0; i < btns.length; i++) {
      btns[i].setAttribute("aria-pressed", t === "dark" ? "true" : "false");
      btns[i].setAttribute("aria-label", "Alternar tema claro/escuro");
      btns[i].setAttribute("title", "Alternar tema claro/escuro");
    }
    swapPlaceholders(t);
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

_ICONS_CACHE: dict | None = None


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _inline_script(text: str) -> str:
    """Make ``text`` safe to inline inside a ``<script>`` element.

    Only a closing tag can terminate the element early; the escaped form is a
    valid JavaScript string/comment sequence and keeps the helper intact.
    """

    return re.sub(r"</script", r"<\\/script", text, flags=re.I)


def _strip_css_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _read(rel: str) -> str:
    return (ASSETS / rel).read_text(encoding="utf-8")


def _iconify_script() -> str:
    return (
        f'<script src="https://cdn.jsdelivr.net/npm/iconify-icon@{ICONIFY_VERSION}'
        '/dist/iconify-icon.min.js"></script>'
    )


def _chart_script() -> str:
    helper = _inline_script(_read("brand-charts.js").strip())
    return (
        f'<script src="https://cdn.jsdelivr.net/npm/chart.js@{CHARTJS_VERSION}'
        '/dist/chart.umd.min.js"></script>\n'
        "<script>\n" + helper + "\n</script>"
    )


def _icons_doc() -> dict:
    global _ICONS_CACHE
    if _ICONS_CACHE is None:
        _ICONS_CACHE = json.loads(_read("icons.json"))
    return _ICONS_CACHE


def _icon_name(brand: dict, semantic: str) -> str:
    family = brand["design"]["icons"]["family"]
    entry = _icons_doc()["icons"].get(semantic, {})
    # Never fall back to another family: unresolved is better than the wrong set.
    return entry.get(family) or f"{family}:{semantic}"


def _resolve_icon_family(markup: str, brand: dict) -> str:
    """Rewrite the skeletons' Fluent icon names to the brand's icon family.

    Skeletons use Fluent names as the neutral default. ``assets/icons.json``
    maps each semantic key to every supported family, so the reverse lookup
    translates only names the map knows; unknown names stay unchanged.
    """

    family = brand["design"]["icons"]["family"]
    if family == "fluent":
        return markup

    reverse: dict[str, str] = {}
    for semantic, names in _icons_doc()["icons"].items():
        fluent = names.get("fluent")
        if fluent and fluent not in reverse:
            reverse[fluent] = semantic

    def replace(match: re.Match[str]) -> str:
        value = match.group(2)
        semantic = reverse.get(value)
        if semantic is None:
            return match.group(0)
        target = _icons_doc()["icons"][semantic].get(family)
        if not target:
            return match.group(0)
        return match.group(1) + target + match.group(3)

    return re.sub(r'(icon=")([^"]+)(")', replace, markup)


def _font_families(brand: dict) -> list[str]:
    families: list[str] = []
    type_block = brand["design"]["type"]
    for role in ("display", "body"):
        family = type_block[role]["family"]
        if family not in families:
            families.append(family)
    return families


def _font_links(brand: dict) -> str:
    # No weight axis on purpose: single-weight display families reject
    # ``wght@400;600;700`` and would lose the whole stylesheet. The CSS stack
    # from brand.json remains the safety net when a family is not on Google.
    query = "&".join(
        f"family={quote_plus(family)}" for family in _font_families(brand)
    )
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


def _root_colors(theme_css: str) -> dict[str, str]:
    """Semantic colour tokens from the ``:root`` block (the light/default set)."""

    match = re.search(r":root\s*\{(.*?)\n\}", theme_css, re.S)
    block = match.group(1) if match else theme_css.split("}", 1)[0]
    colors: dict[str, str] = {}
    for name, value in re.findall(r"--b-([a-z0-9-]+):\s*(#[0-9A-Fa-f]{6});", block):
        colors.setdefault(name, value.upper())
    return colors


def _rgb(value: str) -> str:
    red, green, blue = (int(value[index : index + 2], 16) for index in (1, 3, 5))
    return f"{red} {green} {blue}"


def _slugify(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "color"


def _initials(name: str) -> str:
    words = [word for word in re.split(r"\s+", name.strip()) if word]
    if not words:
        return "B"
    if len(words) == 1:
        return words[0][:1].upper()
    return (words[0][:1] + words[1][:1]).upper()


def _mark(size_class: str = "") -> str:
    classes = ("be-mark " + size_class).strip()
    return f'<svg class="{classes}" aria-hidden="true"><use href="#be-mark"/></svg>'


def _wordmark(name: str) -> str:
    return f'<span class="be-wordmark">{_esc(name)}</span>'


def _monogram(name: str) -> str:
    return f'<span class="be-monogram" aria-hidden="true">{_esc(_initials(name))}</span>'


def _lockup(variant: str, name: str) -> str:
    if variant == "C":
        inner = _mark() + _wordmark(name)
    elif variant == "B":
        inner = _monogram(name)
    else:
        inner = _wordmark(name)
    return f'<span class="be-brand" role="img" aria-label="{_esc(name)}">{inner}</span>'


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


def _color_entries(brand: dict) -> list[tuple[str, dict]]:
    block = brand["design"]["colors"]
    entries: list[tuple[str, dict]] = []
    for role in ("canvas", "surface", "ink", "primary", "accent"):
        color = block.get(role)
        if isinstance(color, dict):
            entries.append((role, color))
    for color in block.get("support") or []:
        if isinstance(color, dict):
            entries.append(("support", color))
    return entries


def _color_cards(brand: dict) -> str:
    cards: list[str] = []
    for role, color in _color_entries(brand):
        slug = _slugify(color["name"])
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
                    f'<dd class="font-medium">{_esc(color["hex"].upper())}</dd></div>',
                    f'    <div class="flex justify-between gap-2"><dt class="text-fg-subtle">RGB</dt>'
                    f"<dd>{_rgb(color['hex'].upper())}</dd></div>",
                    '    <div class="flex justify-between gap-2"><dt class="text-fg-subtle">Pantone</dt>'
                    '<dd class="text-right">[placeholder — confirmar]</dd></div>',
                    f'    <div class="flex justify-between gap-2"><dt class="text-fg-subtle">Token</dt>'
                    f"<dd>--b-color-{slug}</dd></div>",
                    "  </dl>",
                    f'  <p class="mt-2 text-xs text-fg-subtle">{_esc(ROLE_LABELS.get(role, role))} · {_esc(note)}</p>',
                    "</article>",
                )
            )
        )
    return "\n        ".join(cards)


PAIR_ROLES = (
    ("canvas", "fg", "texto principal sobre o fundo"),
    ("surface", "fg", "texto principal sobre o cartão"),
    ("surface", "fg-muted", "texto secundário"),
    ("primary", "on-primary", "ação sólida"),
    ("band", "on-band", "faixa de marca"),
    ("accent", "on-accent", "destaque sólido"),
    ("highlight", "on-highlight", "realce"),
)


def _pair_rows(theme_css: str) -> str:
    colors = _root_colors(theme_css)
    rows: list[str] = []
    for background, foreground, use in PAIR_ROLES:
        bg = colors.get(background)
        fg = colors.get(foreground)
        if not bg or not fg:
            continue
        ratio = contrast_ratio(fg, bg)
        verdict = "AA" if ratio >= 4.5 else ("AA (texto grande)" if ratio >= 3.0 else "Falha AA")
        rows.append(
            "<tr>"
            f'<td class="font-medium">--b-{background}</td>'
            f"<td>--b-{foreground}</td>"
            f'<td class="tabular-nums">{ratio:.2f}:1</td>'
            f"<td>{verdict}</td>"
            f"<td>{_esc(use)}</td>"
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


def _spacing_rows(unit: int) -> str:
    """Spacing table rows generated from the same unit as ``theme.css``."""

    rows = (
        (1, "respiro mínimo, ícone e etiqueta"),
        (2, "entre linhas de um bloco"),
        (3, "padding de cartão compacto"),
        (4, "padding de cartão e coluna"),
        (6, "entre grupos"),
        (8, "entre seções no celular"),
        (12, "entre seções no desktop"),
        (16, "abertura de página"),
    )
    return "\n            ".join(
        f'<tr><td>--b-space-{step}</td><td>{step * unit}px</td><td>{_esc(use)}</td></tr>'
        for step, use in rows
    )


def _voice_summary(brand: dict) -> str:
    return _esc(brand["voice"]["summary"])


def _voice_rules(brand: dict) -> str:
    voice = brand["voice"]
    principles = "\n                ".join(
        f"<li>{_esc(item)}</li>" for item in voice["principles"]
    ) or "<li>[placeholder — princípios de voz]</li>"
    avoid = "\n                ".join(
        f"<li>{_esc(item)}</li>" for item in voice["avoid"]
    ) or "<li>[placeholder — o que evitar]</li>"
    emoji = (
        "Emoji só em social, nunca em interface ou relatório."
        if voice["emoji"] == "social-only"
        else "Sem emoji."
    )
    return "\n        ".join(
        (
            '<div class="rounded-lg border border-line bg-surface p-4">',
            '  <h3 class="text-lg font-semibold">Princípios</h3>',
            '  <ul class="mt-3 list-disc space-y-1 pl-4 text-sm text-fg-muted">',
            f"                {principles}",
            "  </ul>",
            "</div>",
            '<div class="rounded-lg border border-line bg-surface p-4">',
            '  <h3 class="text-lg font-semibold">Evitar</h3>',
            '  <ul class="mt-3 list-disc space-y-1 pl-4 text-sm text-fg-muted">',
            f"                {avoid}",
            "  </ul>",
            "</div>",
            '<div class="rounded-lg border border-line bg-surface p-4">',
            '  <h3 class="text-lg font-semibold">Pessoa e emoji</h3>',
            f'  <p class="mt-3 text-sm text-fg-muted">Trate o leitor por “{_esc(voice["person"])}”.</p>',
            f'  <p class="mt-1 text-sm text-fg-muted">{_esc(emoji)}</p>',
            "</div>",
        )
    )


def _logo_name(brand: dict) -> str:
    name = brand["design"]["logo"].get("name") or "[placeholder — nome do logo]"
    return _esc(name)


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


def _icon_samples(brand: dict) -> str:
    family = brand["design"]["icons"]["family"]
    size = brand["design"]["icons"]["size"]
    samples = (
        ("home", "início"),
        ("search", "busca"),
        ("settings", "ajustes"),
        ("users", "pessoas"),
        ("chart-line", "dados"),
        ("calendar", "agenda"),
    )
    cards: list[str] = []
    for semantic, label in samples:
        name = _icon_name(brand, semantic)
        cards.append(
            "\n".join(
                (
                    '<div class="rounded-lg border border-line bg-surface p-4">',
                    f'  <p class="flex items-center gap-2 text-sm font-medium">',
                    f'    <iconify-icon icon="{_esc(name)}" width="{size}" height="{size}"'
                    ' aria-hidden="true" class="text-lg text-fg-muted"></iconify-icon>',
                    f"    {_esc(label)}",
                    "  </p>",
                    f'  <code class="mt-2 block text-xs text-fg-subtle">{_esc(name)}</code>',
                    "</div>",
                )
            )
        )
    cards.append(
        "\n".join(
            (
                '<div class="rounded-lg border border-line bg-surface p-4">',
                '  <p class="text-xs font-semibold uppercase tracking-widest text-fg-subtle">Família</p>',
                f'  <p class="mt-2 text-lg font-semibold">{_esc(family)}</p>',
                f'  <code class="mt-2 block text-xs text-fg-subtle">design.icons.family</code>',
                "</div>",
            )
        )
    )
    return "\n        ".join(cards)


def _chart_swatches() -> str:
    return "\n        ".join(
        f'<div class="h-10 w-10 rounded-md bg-chart-{index}" role="img" '
        f'aria-label="chart-{index}"></div>'
        for index in range(1, 9)
    )


def _feedback_cards(brand: dict) -> str:
    roles = (
        ("success", "Sucesso", "check-circle", "confirmação com o próximo passo"),
        ("warning", "Atenção", "alert-triangle", "o risco e como evitá-lo"),
        ("danger", "Erro", "alert-circle", "o que falhou e o que fazer agora"),
        ("info", "Informação", "info", "contexto que evita uma dúvida"),
    )
    cards: list[str] = []
    for role, label, semantic, note in roles:
        icon = _icon_name(brand, semantic)
        cards.append(
            "\n".join(
                (
                    f'<div class="rounded-lg bg-{role}-soft p-3">',
                    f'  <p class="flex items-center gap-2 text-sm font-semibold text-on-{role}-soft">',
                    f'    <iconify-icon icon="{_esc(icon)}" aria-hidden="true"'
                    f' class="text-base text-{role}"></iconify-icon>',
                    f"    {label}",
                    "  </p>",
                    f'  <p class="mt-1 text-sm text-fg-muted">[placeholder — {_esc(note)}.]</p>',
                    f'  <code class="mt-2 block text-xs text-fg-subtle">bg-{role}-soft · text-on-{role}-soft</code>',
                    "</div>",
                )
            )
        )
    return "\n        ".join(cards)


def _component_samples(brand: dict) -> str:
    info_icon = _icon_name(brand, "info")
    return "\n        ".join(
        (
            "\n".join(
                (
                    '<div class="rounded-lg border border-line bg-surface p-4">',
                    '  <h3 class="text-lg font-semibold">Ações</h3>',
                    '  <div class="mt-3 flex flex-wrap items-center gap-2">',
                    '    <button type="button" class="inline-flex h-6 items-center rounded-md bg-primary px-3 text-sm font-semibold text-on-primary hover:bg-primary-hover">Primária</button>',
                    '    <button type="button" class="inline-flex h-6 items-center rounded-md border border-line-input bg-surface px-3 text-sm font-semibold text-fg hover:bg-surface-muted">Secundária</button>',
                    '    <a href="#componentes" class="text-sm text-link">Ação terciária</a>',
                    "  </div>",
                    "</div>",
                )
            ),
            "\n".join(
                (
                    '<div class="rounded-lg border border-line bg-surface p-4">',
                    '  <h3 class="text-lg font-semibold">Campos</h3>',
                    '  <label for="manual-campo" class="mt-3 block text-sm font-medium">[placeholder — rótulo do campo]</label>',
                    '  <input id="manual-campo" name="campo" type="text" class="mt-1 h-6 w-full rounded-md border border-line-input bg-surface px-2 text-sm text-fg">',
                    '  <p class="mt-1 text-xs text-fg-subtle">[placeholder — ajuda curta, sempre visível.]</p>',
                    "</div>",
                )
            ),
            "\n".join(
                (
                    '<div class="rounded-lg bg-info-soft p-3">',
                    '  <p class="flex items-center gap-2 text-sm font-semibold text-on-info-soft">',
                    f'    <iconify-icon icon="{_esc(info_icon)}" aria-hidden="true" class="text-base text-info"></iconify-icon>',
                    "    Callout",
                    "  </p>",
                    '  <p class="mt-1 text-sm text-fg-muted">[placeholder — contexto que muda a decisão de quem lê.]</p>',
                    "</div>",
                )
            ),
            "\n".join(
                (
                    '<div class="rounded-lg border border-line bg-surface p-4">',
                    '  <h3 class="text-lg font-semibold">Etiquetas e estados</h3>',
                    '  <div class="mt-3 flex flex-wrap items-center gap-2">',
                    '    <span class="rounded-full bg-primary-soft px-2 py-1 text-xs font-medium text-on-primary-soft">Etiqueta</span>',
                    '    <span class="rounded-full bg-success-soft px-2 py-1 text-xs font-medium text-on-success-soft">Concluído</span>',
                    '    <span class="rounded-full border border-line px-2 py-1 text-xs text-fg-muted">Neutra</span>',
                    "  </div>",
                    '  <p class="mt-3 text-sm text-fg-muted">[placeholder — use estado só quando algo muda.]</p>',
                    "</div>",
                )
            ),
        )
    )


def _composition_rules(brand: dict) -> str:
    composition = brand["design"]["composition"]
    direction = composition["direction"]
    cards = (
        (
            "Direção",
            direction,
            DIRECTION_NOTES.get(direction, "derive a composição da rota aprovada"),
        ),
        ("Medida", composition["measure"], "largura máxima de leitura; não estique o texto"),
        ("Grid", composition["grid"], "colunas do desktop; no celular, uma coluna"),
    )
    return "\n        ".join(
        "\n".join(
            (
                '<div class="rounded-lg border border-line bg-surface p-4">',
                f'  <p class="text-xs font-semibold uppercase tracking-widest text-fg-subtle">{_esc(title)}</p>',
                f'  <p class="mt-2 text-lg font-semibold">{_esc(value)}</p>',
                f'  <p class="mt-1 text-sm text-fg-muted">{_esc(note)}.</p>',
                "</div>",
            )
        )
        for title, value, note in cards
    )


def _application_cards(brand: dict) -> str:
    applications = (
        ("onepage", "Landing page", "promessa, prova e uma ação"),
        ("report", "Relatório", "conclusão primeiro, tabela e gráfico de apoio"),
        ("deck", "Apresentação", "uma ideia por slide, tipo grande"),
        ("app", "App", "topbar, sidebar, lista, estados e formulário"),
        ("social", "Social", "mockup quadrado e vertical, não export"),
        ("brand-kit", "Brand kit", "a prova viva do sistema e o menu de formatos"),
    )
    cards: list[str] = []
    for fmt, title, job in applications:
        cards.append(
            "\n".join(
                (
                    f'<article data-application="{fmt}" class="rounded-lg border border-line bg-surface p-4">',
                    f'  <h3 class="text-lg font-semibold">{_esc(title)}</h3>',
                    f'  <p class="mt-1 text-sm text-fg-muted">{_esc(job)}.</p>',
                    f'  <code class="mt-3 block text-xs text-fg-subtle">--format {fmt}</code>',
                    "</article>",
                )
            )
        )
    return "\n        ".join(cards)


def _placehold(width: int, height: int, text: str, bg: str, fg: str) -> str:
    """A placehold.co URL with brand colours (hex without the leading ``#``)."""

    return (
        f"https://placehold.co/{width}x{height}/"
        f"{bg.lstrip('#').upper()}/{fg.lstrip('#').upper()}"
        f"?text={quote_plus(text)}"
    )


def _image_sample(
    brand: dict,
    width: int = 1200,
    height: int = 800,
    label: str = "imagem da marca",
) -> str:
    design = brand["design"]
    colors = design["colors"]
    canvas = colors["canvas"]["hex"]
    ink = colors["ink"]["hex"]
    primary = colors["primary"]["hex"]
    imagery = design["imagery"]
    theme = design["theme"]
    modes = tuple(theme.get("modes") or DEFAULT_THEME_MODES)
    both = "light" in modes and "dark" in modes

    if imagery["mode"] == "none":
        treatment = (
            f" {_esc(imagery['treatment'])}." if imagery.get("treatment") else ""
        )
        return "\n".join(
            (
                '<div class="rounded-lg border border-dashed border-line-strong bg-surface p-6">',
                '  <p class="text-sm font-semibold">Sem imagem de banco</p>',
                '  <p class="mt-1 text-sm text-fg-muted">'
                "Esta marca não usa fotografia nem ilustração: a textura vem do CSS "
                f"e dos próprios componentes.{treatment}</p>",
                '  <code class="mt-2 block text-xs text-fg-subtle">design.imagery.mode · none</code>',
                "</div>",
            )
        )

    alt = f"Imagem de exemplo — {imagery.get('treatment') or imagery['mode']}"
    light_url = _placehold(width, height, label, canvas, primary)

    if both:
        dark_url = _placehold(width, height, label, ink, canvas)
        initial_dark = (theme.get("default") or "light") == "dark"
        src = dark_url if initial_dark else light_url
        attrs = (
            f' data-placehold-light="{_esc(light_url)}"'
            f' data-placehold-dark="{_esc(dark_url)}"'
        )
    else:
        src = light_url
        attrs = ""

    return "\n".join(
        (
            '<figure class="rounded-lg border border-line bg-surface p-3">',
            f'  <img src="{_esc(src)}"{attrs} alt="{_esc(alt)}" '
            f'class="block h-auto w-full rounded-md" width="{width}" height="{height}" loading="lazy">',
            '  <figcaption class="mt-2 text-xs text-fg-subtle">'
            "[placeholder — troque pelo asset real; a nota de entrega lista os placeholders.]"
            "</figcaption>",
            "</figure>",
        )
    )


def _gradient_section(brand: dict) -> str:
    gradient = brand["design"]["theme"].get("gradient")
    if not gradient:
        return ""
    angle = gradient.get("angle", 45)
    stops = "três stops" if gradient.get("via") else "dois stops"
    return "\n".join(
        (
            '<div class="mt-8">',
            '  <h3 class="text-xl font-semibold">Gradiente</h3>',
            '  <p class="mt-2 max-w-3xl text-sm text-fg-muted">'
            f"Único gradiente aprovado: {stops} em {float(angle):g}°. Use "
            '<code class="text-link">bg-grad-brand</code>; qualquer outro gradiente é um desvio.</p>',
            '  <div class="mt-3 h-20 rounded-lg bg-grad-brand" role="img" '
            'aria-label="Amostra do gradiente da marca"></div>',
            '  <p class="mt-2 text-xs text-fg-subtle"><code class="text-link">bg-grad-brand</code> · '
            '<code class="text-link">--b-gradient</code></p>',
            "</div>",
        )
    )


def _theme_parts(theme: str | None, brand: dict) -> tuple[str, str, str, str | None]:
    """Resolve ``(default, lock_attr, toggle_html, initial_mode)`` for the page."""

    block = brand["design"]["theme"]
    modes = tuple(block.get("modes") or DEFAULT_THEME_MODES)
    default = block.get("default") or ("light" if "light" in modes else modes[0])
    if theme is None:
        theme = default

    if not isinstance(theme, str) or theme not in THEMES:
        raise ValueError(f"unknown theme {theme!r} (choose from {', '.join(THEMES)})")

    both = "light" in modes and "dark" in modes

    if theme == "system":
        if not both:
            raise ValueError(
                "theme 'system' needs a brand with both light and dark modes "
                f"(this brand has: {', '.join(modes)})"
            )
        return "system", "", THEME_TOGGLE, None

    if theme.endswith("-only"):
        mode = theme[: -len("-only")]
        if mode not in modes:
            raise ValueError(
                f"theme {theme!r} is not available: brand modes are {', '.join(modes)}"
            )
        return mode, f' data-theme-lock="{mode}"', "", mode

    if theme not in modes:
        raise ValueError(
            f"theme {theme!r} is not available: brand modes are {', '.join(modes)}"
        )

    if not both:
        # A single-mode brand is always locked and renders no toggle.
        return theme, f' data-theme-lock="{theme}"', "", theme

    return theme, "", THEME_TOGGLE, theme


def _set_initial_theme(page: str, mode: str | None) -> str:
    if mode not in ("light", "dark"):
        return page

    def replace(match: re.Match[str]) -> str:
        attrs = match.group(1)
        if re.search(r"\bdata-theme=", attrs):
            return match.group(0)
        return f'<html{attrs} data-theme="{mode}">'

    return re.sub(r"<html\b([^>]*)>", replace, page, count=1)


def render_page(fmt: str, brand: dict, title: str, theme: str | None = None) -> str:
    """Render one format from a v2 brand object (raw or normalized)."""

    if fmt not in FORMATS:
        raise ValueError(f"unknown format {fmt!r} (choose from {', '.join(FORMATS)})")

    brand = normalize_brand(brand)
    built = render_theme(brand)
    theme_css = built.theme_css
    tailwind_css = built.tailwind_theme_css

    design = brand["design"]
    name = brand.get("name") or "Brand"
    attributes = [str(item) for item in brand["attributes"]]
    display = design["type"]["display"]
    body_type = design["type"]["body"]
    scale = design["type"].get("scale", {})
    variant = design["logo"]["variant"]
    logo_notes = design["logo"].get("notes") or "Geometria e proporção definidas na fase de logo."
    unit = design["shape"]["unit"]

    theme_default, theme_lock, toggle, initial = _theme_parts(theme, brand)
    safe_title = _esc(title)

    mapping = {
        "TITLE": safe_title,
        "BRAND_NAME": _esc(name),
        "LANGUAGE": _esc(brand["language"]),
        "PURPOSE": _esc(brand["purpose"]),
        "PERSONA": _esc(brand["persona"]),
        "TERRITORY": _esc(brand["territory"]),
        "ARCHETYPE": _esc(brand["archetype"]),
        "ATTRIBUTE_LEAD": _esc(" · ".join(attributes[:2])),
        "ATTRIBUTE_CHIPS": _chips(attributes),
        "HEADLINE": safe_title,
        "SOMOS_LIST": _somos_list(attributes),
        "NAO_SOMOS_LIST": _nao_somos_list(attributes),
        "VOICE_SUMMARY": _voice_summary(brand),
        "VOICE_RULES": _voice_rules(brand),
        "COLOR_CARDS": _color_cards(brand),
        "PAIR_ROWS": _pair_rows(theme_css),
        "TYPE_ROWS": _type_rows(theme_css),
        "SPACING_UNIT": f"{unit}px",
        "SPACING_ROWS": _spacing_rows(unit),
        "FEEDBACK_CARDS": _feedback_cards(brand),
        "CHART_SWATCHES": _chart_swatches(),
        "ICON_SAMPLES": _icon_samples(brand),
        "IMAGE_SAMPLE": _image_sample(brand),
        "SOCIAL_IMAGE": _image_sample(brand, 1080, 1350, "imagem do post"),
        "COMPONENT_SAMPLES": _component_samples(brand),
        "COMPOSITION_RULES": _composition_rules(brand),
        "APPLICATION_CARDS": _application_cards(brand),
        "GRADIENT_SECTION": _gradient_section(brand),
        "ICONIFY_SCRIPT": _iconify_script() if fmt in FORMAT_ICONS else "",
        "CHART_SCRIPT": _chart_script() if fmt in FORMAT_CHARTS else "",
        "FONT_DISPLAY": _esc(display["family"]),
        "FONT_BODY": _esc(body_type["family"]),
        "SCALE_BASE": _esc(scale.get("base", 16)),
        "SCALE_RATIO": _esc(scale.get("ratio", 1.25)),
        "LOGO_VARIANT": _esc(variant),
        "LOGO_NAME": _logo_name(brand),
        "LOGO_NOTES": _esc(logo_notes),
        "LOGO_C": _lockup("C", name),
        "LOGO_B": _lockup("B", name),
        "LOGO_A": _lockup("A", name),
        "LOGO_HEADER": _lockup(variant, name),
        "LOGO_MARK_ONLY": _logo_for_nav(variant, name),
        "LOGO_SIZE_SAMPLES": _logo_size_samples(variant, name),
        "LOGO_BREATHING": f"{unit}px",
        "THEME_TOGGLE": toggle,
        "THEME_DEFAULT": theme_default,
        "THEME_LOCK": theme_lock,
        "THEME_JS": _inline_script(THEME_JS),
        "THEME_CSS": _strip_css_comments(theme_css).strip(),
        "TAILWIND_THEME": _strip_css_comments(tailwind_css).strip(),
        "TAILWIND_VERSION": TAILWIND_VERSION,
        "FONT_LINKS": _font_links(brand),
    }

    body = _read(f"skeletons/{fmt}.html")
    for key, value in mapping.items():
        body = body.replace("{{" + key + "}}", value)
    body = _resolve_icon_family(body, brand)

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
        page = page.replace("</body>", "<script>\n" + _inline_script(DECK_JS) + "\n</script>\n</body>")
    page = _set_initial_theme(page, initial)

    leftover = re.findall(r"\{\{[A-Z0-9_]+\}\}", page)
    if leftover:
        raise RuntimeError(f"unreplaced placeholders in {fmt}: {sorted(set(leftover))}")
    return page


def _replace_generated_style(html: str, needle: str, replacement: str) -> str:
    """Replace one ``<style>`` block whose content contains ``needle``."""

    pattern = re.compile(r"<style>\s*(.*?)</style>", re.S)
    found = False

    def repl(match: re.Match[str]) -> str:
        nonlocal found
        if needle not in match.group(1):
            return match.group(0)
        found = True
        return replacement

    updated = pattern.sub(repl, html)
    if not found:
        raise ValueError("page has no generated brand-engine theme block")
    return updated


def restyle_html(html: str, brand: dict) -> str:
    """Replace only the generated theme/tailwind-theme blocks, keeping the body.

    This is the post-delivery adjustment path: the composed copy, sections and
    page shell stay untouched; palette, type, spacing, radius, shadow, modes and
    gradient tokens come from the current ``brand.json``.
    """

    brand = normalize_brand(brand)
    built = render_theme(brand)
    theme_css = _strip_css_comments(built.theme_css).strip()
    tailwind_css = _strip_css_comments(built.tailwind_theme_css).strip()

    html = _replace_generated_style(
        html, "--b-color-", f"<style>\n{theme_css}\n</style>"
    )
    tailwind = re.compile(r'<style type="text/tailwindcss">\s*.*?</style>', re.S)
    updated, count = tailwind.subn(
        lambda match: f'<style type="text/tailwindcss">\n{tailwind_css}\n</style>',
        html,
        count=1,
    )
    if count != 1:
        raise ValueError("page has no generated tailwind-theme block")
    return updated


def restyle(
    page: str | Path, brand: str | Path, out: str | Path | None = None
) -> Path:
    """Rewrite an existing generated page's theme blocks in place."""

    data = load_brand(brand)
    source = Path(page).expanduser()
    html = source.read_text(encoding="utf-8")
    updated = restyle_html(html, data)

    destination = Path(out).expanduser() if out is not None else source
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(updated, encoding="utf-8")
    return destination


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
    theme: str | None = None,
    force: bool = False,
) -> Path:
    """Render and write one format; return the path of the written file.

    ``out`` is an ``.html`` path or a directory (``<fmt>.html`` is written).
    """

    if fmt not in FORMATS:
        raise ValueError(f"unknown format {fmt!r} (choose from {', '.join(FORMATS)})")
    if theme is not None and theme not in THEMES:
        raise ValueError(f"unknown theme {theme!r} (choose from {', '.join(THEMES)})")
    data = load_brand(brand)
    page = render_page(fmt, data, title, theme)

    destination = _destination(out, fmt)
    if destination.exists() and not force:
        raise FileExistsError(f"refusing to overwrite {destination} without --force")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(page, encoding="utf-8")
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a branded single-file HTML starter page from brand.json."
    )
    parser.add_argument("--brand", help="path to brand.json (flag wins over discovery)")
    parser.add_argument(
        "--format",
        choices=FORMATS,
        help="format to generate (required unless --restyle)",
    )
    parser.add_argument(
        "--title", help="page title (required unless --restyle)"
    )
    parser.add_argument(
        "--out",
        required=True,
        help="output .html file (or directory to hold <format>.html); with --restyle, the page to adjust",
    )
    parser.add_argument(
        "--restyle",
        action="store_true",
        help="replace only the generated theme blocks of an existing page",
    )
    parser.add_argument("--theme", default=None, choices=THEMES)
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

        if args.restyle:
            conflicts = [
                flag
                for flag, value in (
                    ("--format", args.format),
                    ("--title", args.title),
                    ("--theme", args.theme),
                    ("--force", args.force),
                )
                if value
            ]
            if conflicts:
                print(
                    "new_page: --restyle only rewrites the generated theme blocks; "
                    f"drop {', '.join(conflicts)}. Use a normal --format run "
                    "(with --force) for a full page or a theme-mode change.",
                    file=sys.stderr,
                )
                return 2
            destination = restyle(args.out, brand_path)
            print(f"ok: {destination} (theme blocks restyled)")
            return 0

        if not args.format or not args.title:
            parser.error("--format and --title are required unless --restyle")

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

    theme_label = args.theme or "padrão da marca"
    print(f"ok: {destination} ({args.format}, tema {theme_label})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
