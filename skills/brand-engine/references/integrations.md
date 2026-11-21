# Integrations — CDN contracts and their limits

Every generated page depends on the internet. Tailwind, fonts, icons, charts and
placeholders are loaded from CDNs, so a page opened offline loses styling,
icons and charts even though the HTML is local. There is no offline mode and no
service worker; never promise that a file works offline. Keep textual labels next
to every icon, and treat the CDN dependencies as part of the delivery note when
it matters.

## Tailwind v4

The preview pins the browser build:

```html
<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4.3.3"></script>
<style type="text/tailwindcss">
  /* generated tailwind-theme.css, inlined */
</style>
```

`@tailwindcss/browser@4.3.3` compiles in the browser, which costs startup time;
it is a preview convenience, not a production dependency. Do not bump the pin
without re-running the tests.

Production is the same contract: install Tailwind v4, import `theme.css` and
`tailwind-theme.css`, and keep the semantic classes. The generated
`tailwind-theme.css` uses `@theme` for spacing, type, radius and shadows,
`@theme inline` for colors (`--color-surface: var(--b-surface)`, so
`bg-surface` and `text-fg-muted` follow the theme), `@custom-variant dark` bound
to `[data-theme="dark"]`, and `--spacing` set by the brand unit. A brand with a
gradient also gets `@utility bg-grad-brand`; without one the utility does not
exist. There is no product flavor, no fixed palette and no second theme
stylesheet for production.

## Iconify

Icons are the Iconify web component, pinned at `iconify-icon@3.0.0`:

```html
<script src="https://cdn.jsdelivr.net/npm/iconify-icon@3.0.0/dist/iconify-icon.min.js"></script>
<iconify-icon icon="fluent:arrow-right-24-regular" aria-hidden="true" class="text-base"></iconify-icon>
```

The component is ~24KB. Its SVG inherits `currentColor`, so `text-*` classes and
the dark theme work without extra markup; size follows the text class or the
configured icon size (`width`/`height` attributes).

The family comes from `design.icons.family` (`fluent`, `lucide`, `phosphor` or
`tabler`). `fluent` is the default; `phosphor` names use the `ph:` prefix and
the others use `lucide:` and `tabler:`. `assets/icons.json` maps the semantic
names used by skeletons (Fluent names) to all four families; the generator
rewrites the names it knows to the brand's family and leaves unknown names
unchanged. Use raw Iconify names when the semantic map has no entry, and never
fall back to another family: an unresolved icon is better than the wrong set.

Accessibility: a decorative icon gets `aria-hidden="true"`; a meaningful icon
needs `role="img"` and an `aria-label`; an icon-only control needs its own
accessible name. Never let an icon be the only carrier of meaning. Offline the
component does not render, so the text label must still make sense.

## Chart.js

Chart.js is loaded only on pages with a chart (`report`, `app` and
`brand-kit`), pinned at `chart.js@4.4.7`:

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<script>
  /* generated brand-charts.js, inlined */
</script>
```

The helper is `window.BrandCharts` and exposes:

| Member | Contract |
|---|---|
| `BrandCharts.colors()` | `{chart, fg, line, surface}` read from the live tokens. |
| `BrandCharts.create(canvasId, config)` | Creates or recreates the chart; returns the Chart instance, or `null` without a canvas/Chart.js. |
| `BrandCharts.refresh()` | Rebuilds every registered chart with the current tokens. |

It reads `--b-chart-1` through `--b-chart-8` (series, 3:1 against `surface`),
`--b-fg-subtle` (axis, legend and title labels), `--b-line` (grid and borders)
and `--b-surface` (canvas and point borders). It fills only the colors the
author omitted, preserves deliberate `false` toggles (`legend: false`,
`grid: false`, `ticks: false`), and observes `data-theme` on the root with a
`MutationObserver`; when the theme changes every registered chart is rebuilt.
The caller's config is never mutated.

Use Chart.js for line, area and scatter. For simple bars and part-of-whole use
CSS bars or the SVG donut, so the page does not load a chart library for a
single shape. One series is highlighted, the rest are context; add direct
labels and a table fallback with the same values. The canvas carries
`role="img"` and a meaningful `aria-label`; the table is the accessible source
of the data.

## placehold.co

While a real asset is missing, images use `placehold.co`:

```text
https://placehold.co/{w}x{h}/{bg}/{fg}?text=...
```

`{w}` and `{h}` are pixels; `{bg}` and `{fg}` are brand hex values **without the
leading `#`** (the generator uppercases them); `text` is URL-encoded (`+` for
spaces). Example:

```text
https://placehold.co/1200x800/FBF8F1/0F5A6B?text=imagem+da+marca
```

Use it for product shots, photos, avatars and screenshots until the real asset
exists. When the brand has both themes, provide both URLs:

```html
<img src="https://placehold.co/1200x800/FBF8F1/0F5A6B?text=imagem"
     data-placehold-light="https://placehold.co/1200x800/FBF8F1/0F5A6B?text=imagem"
     data-placehold-dark="https://placehold.co/1200x800/1E1C17/FBF8F1?text=imagem"
     alt="[placeholder — o que a imagem mostra]" width="1200" height="800">
```

The theme script swaps `src` from `data-placehold-dark`/`data-placehold-light`
on every theme change. `alt` describes the intention, not the placeholder; every
placeholder is listed in the delivery note (**Nota**). Unsplash and unDraw are
not used: no random stock photo, no generic illustration.

## axe_copy.py

`scripts/axe_copy.py` builds a disposable copy of a page for a rendered
contrast/a11y audit:

```bash
python3 scripts/axe_copy.py pagina.html            # writes pagina.axe.html
python3 scripts/axe_copy.py pagina.html --out /tmp/x.html
```

The copy loads axe-core 4.10.2 from cdnjs, waits 1.5s for the Tailwind browser
CDN and webfonts, then runs WCAG 2.2 A/AA plus best-practice rules
(`wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, `wcag22aa`, `best-practice`). A page with `data-theme-lock` is audited
once in the locked theme; a page with both themes is audited in light and dark.
Results are written to `<pre id="axe-out">` at the top of the copy and to the
console. Open the copy in a browser over `http://` (not `file://`), read
`#axe-out`, and delete the copy. The delivered page is never modified.

This is an optional rendered check: it needs a browser and internet. The
deterministic gate is `check_page.py`, which must report zero ERROR on every
generated page.

## Dependency checklist

- [ ] Tailwind browser CDN is pinned at 4.3.3 in the preview; production imports
      the generated theme into Tailwind v4.
- [ ] Icons load from `iconify-icon@3.0.0`; the family matches
      `design.icons.family`; every icon is decorative or labeled.
- [ ] Chart.js loads only on chart pages, via `chart.js@4.4.7`, and the chart
      reads the brand tokens and rebuilds on theme change.
- [ ] Images use `placehold.co` with brand hex without `#`, a dark variant when
      needed, and a meaningful `alt`.
- [ ] Unsplash and unDraw are not used.
- [ ] The delivery note says the page needs internet; no offline promise.
- [ ] `axe_copy.py` is used only when a browser exists, and its copy is deleted.
