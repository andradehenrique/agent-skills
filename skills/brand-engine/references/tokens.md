# Tokens — brand.json v2, theme.css and the rules that keep them honest

This file is the schema and the usage contract for Phase 2. It describes what
`scripts/build_theme.py` actually enforces, not an idealized token system.

## Pipeline and exact API

```bash
python3 <skill>/scripts/build_theme.py --brand brand.json --out . [--force]
```

The command writes `theme.css` (`--b-*` custom properties, light and optional
dark) and `tailwind-theme.css` (the semantic utility mapping) into `--out`. It
refuses to overwrite either file without `--force`.

| Call | Contract |
|---|---|
| `build_theme(brand_path, out_dir, force=False)` | -> `ThemeBuild(theme_css, tailwind_theme_css)`; validates, renders and writes both files. |
| `load_brand(brand_path)` | -> `dict`; reads, validates and returns the brand object. |
| `render_theme(brand)` | -> `ThemeBuild`; same render with no file I/O. |
| `resolve_brand_path(brand_flag=None, cwd=None)` | -> `Path` or `None`; `--brand` > `./brand.json` > `./brand/brand.json` > `None`. |
| `missing_brand_behavior()` | -> `"ask-for-path-or-discovery"`. |
| `contrast_ratio(foreground, background)` | -> float 1.0–21.0 (WCAG 2.x). |
| `BrandError` | malformed brand, unreadable path or schema violation. |

A missing brand raises `BrandError`; the CLI prints one actionable line and
exits `2`, never a traceback.

## brand.json v2

`version` must be `2`. The schema is final: there is no migrator, no dual parser
and no compatibility mode. An older `brand.json` is rewritten by hand. Unknown
keys are rejected instead of ignored, including old top-level keys.

| Key | Shape |
|---|---|
| `version` | Exactly `2`. |
| `name` | Optional brand name; defaults to `Brand`. |
| `purpose`, `persona`, `territory`, `archetype` | One or two sentences each. |
| `attributes` | Non-empty list of short strings. |
| `voice` | Optional object: `summary` (required when present), `principles[]`, `avoid[]`, `person` (default `você`), `emoji` (`none` or `social-only`). |
| `design` | Required object with `colors`, `feedback`, `charts`, `type`, `shape`, `theme`, `icons`, `imagery`, `composition`, `logo`. |
| `aceite` | Required boolean; `true` only after the manual is approved. No script enforces it. |

### colors — roles, not a theme

```json
"colors": {
  "canvas": {"name": "Papel", "hex": "#FBF8F1"},
  "surface": {"name": "Giz", "hex": "#FFFFFF"},
  "ink": {"name": "Tinta", "hex": "#1E1C17"},
  "primary": {"name": "Petróleo", "hex": "#0F5A6B"},
  "accent": {"name": "Areia", "hex": "#E8DFCE"},
  "support": [{"name": "Oliva", "hex": "#7C8363"}]
}
```

- `canvas`, `surface`, `ink` and `primary` are required. `accent` é opcional;
  `support[]` também é opcional. When `accent` is absent the builder uses
  `primary` as the accent source.
- A color is `{"name": "...", "hex": "#RRGGBB", "note": "..."}`; `hex` is exactly
  six hex digits and names are unique case-insensitively.
- Every color emits `--b-color-<slug>` with the **approved hex**, invariant
  between themes. A slug strips accents (NFKD), lowercases and joins runs of
  non-alphanumerics with `-`. References accept the name or the slug,
  case-insensitive: `Papel`, `papel` and `PAPEL` are the same color.
- `ink` is the text role in `brand.json`; in CSS the readable text token remains
  `--b-fg` / `text-fg`. `band` is an optional brand surface derived from
  `ink`/`primary`, not a fixed color.

### feedback and charts — `auto` or explicit

`feedback` and `charts` accept `"auto"` or explicit values.

- `feedback: "auto"` derives `success`, `warning`, `danger` and `info` from
  functional anchors, then adjusts each derived token until it clears contrast
  against the brand's canvas and surface. An override maps a role to a hex or a
  color object: `{"danger": "#B3261E"}`.
- Each feedback role emits five tokens: `--b-<role>`, `--b-<role>-soft`,
  `--b-<role>-solid`, `--b-on-<role>` and `--b-on-<role>-soft`. For `success`
  that is `--b-success`, `--b-success-soft`, `--b-success-solid`,
  `--b-on-success` and `--b-on-success-soft`; the same pattern applies to
  `warning`, `danger` and `info`. The text role needs 4.5:1, `-solid` needs 3:1
  against canvas and surface, and `on-*` must stay readable on the fill it names.
- `charts: "auto"` derives eight distinct data colors by mixing functional
  anchors with the brand `primary` and shifting them until each clears 3:1
  against `surface`. An explicit list seeds the same derivation. They emit
  `--b-chart-1` through `--b-chart-8`.
- Charts are **data, not text**: use them for series marks at 3:1, never for body
  copy. One series is highlighted; the rest are context.

### type

```json
"type": {
  "display": {"family": "Newsreader", "fallback": "Georgia, serif", "weight": 600},
  "body": {"family": "Source Sans 3", "fallback": "system-ui, sans-serif", "weight": 400},
  "scale": {"base": 16, "ratio": 1.25}
}
```

- `display` and `body` each take `family` (one name), `fallback`, `weight`
  (multiple of 100), `tracking` and `case` (`none`/`uppercase`/`lowercase`/
  `capitalize`). Display and body may share a family.
- `scale.base` is 12–32; `scale.ratio` is 1.05–1.8. The default is 16/1.25.
- Twelve steps, `xs` through `8xl`, at exponents `n = -2 … 9`:

```text
size    = round(base * ratio^n)
leading = 1.6                          when n <= 0
leading = max(1.05, 1.6 - 0.07 * n)    when n > 0
```

`theme.css` emits `--b-text-<step>` and `--b-leading-<step>`;
`tailwind-theme.css` couples them as `text-<step>`. `7xl`/`8xl` exist for hero
and deck headlines. Body reading uses `text-base` or larger.

### shape — radius, unit, shadows

```json
"shape": {"radius": "soft", "unit": 8, "shadows": "soft"}
```

| Radius profile | xs / sm / md / lg / xl / full |
|---|---|
| `sharp` | 0/0/2/4/4 / 9999 |
| `soft` (default) | 4/8/12/16/24 / 9999 |
| `round` | 8/12/16/24/9999 / 9999 |

- `radius` also accepts a partial `xs`/`sm`/`md`/`lg`/`xl`/`full` object; missing keys fall back to `soft`.
- `unit` is `4` or `8` (default 8). It sets `--b-unit` and
  `--b-space-0` … `--b-space-16`, each an exact multiple, and Tailwind's
  `--spacing`. `p-4` is 16px on unit 4 and 32px on unit 8.
- `shadows` is `none`, `soft` or `strong`; it emits `--b-shadow-1/2/3` and the
  matching `--shadow-*` entries.

### theme — modes and the optional gradient

```json
"theme": {"modes": ["light", "dark"], "default": "light", "gradient": null}
```

- `modes` is a non-empty subset of `light` and `dark`; `default` must be one of
  them. A light-only brand emits no `[data-theme="dark"]` block. A dark-only
  brand emits one root dark block. Both modes emit the switch.
- `gradient` is optional. When null there is no `--b-gradient`, no
  `bg-grad-brand` utility and no gradient section in the manual. When present:

```json
"gradient": {"from": "Petróleo", "to": "Areia", "angle": 45, "via": null}
```

`from` and `to` accept a color name, slug or `#RRGGBB`; `via` is optional;
`angle` is 0–360 (default 45).

### icons, imagery, composition, logo

| Block | Values |
|---|---|
| `icons` | `family`: `fluent`/`lucide`/`phosphor`/`tabler`; `style` (e.g. `regular`); `size` 8–64 (default 16). Icons are Iconify web components, SVG with `currentColor`, tinted by `text-*`. |
| `imagery` | `mode`: `photo`/`illustration`/`abstract`/`none`; `treatment` (free text); `placeholder` (default `placehold`). Use `placehold.co` while the real asset is missing. |
| `composition` | `direction`: `editorial`/`structured`/`poster`/`minimal`; `measure` (default `65ch`); `grid` (default `"12"`). Direction guides sections, grid and rhythm; it does not select a different skeleton file. |
| `logo` | `variant`: `C`/`B`/`A`; `name`; `notes`. Resolve by the cascade in `logo.md`. |

### Full example

```json
{
  "version": 2,
  "name": "Omnia Labs",
  "purpose": "Traduzir IA em operação real para empresas que precisam decidir agora.",
  "persona": "Donos e diretores de PMEs que já sentem a pressão da IA.",
  "territory": "editorial humanista com precisão técnica",
  "archetype": "Sábio",
  "attributes": ["claro", "humano", "preciso", "sem jargão"],
  "voice": {
    "summary": "Explica antes de vender; mostra o método.",
    "principles": ["conclusão primeiro", "número com base", "zero jargão"],
    "avoid": ["hype de IA", "promessa sem dono"],
    "person": "você",
    "emoji": "none"
  },
  "design": {
    "colors": {
      "canvas": {"name": "Papel", "hex": "#FBF8F1"},
      "surface": {"name": "Giz", "hex": "#FFFFFF"},
      "ink": {"name": "Tinta", "hex": "#1E1C17"},
      "primary": {"name": "Petróleo", "hex": "#0F5A6B"},
      "accent": {"name": "Areia", "hex": "#E8DFCE"},
      "support": [{"name": "Oliva", "hex": "#7C8363"}]
    },
    "feedback": "auto",
    "charts": "auto",
    "type": {
      "display": {"family": "Newsreader", "fallback": "Georgia, serif", "weight": 600},
      "body": {"family": "Source Sans 3", "fallback": "system-ui, sans-serif", "weight": 400},
      "scale": {"base": 16, "ratio": 1.25}
    },
    "shape": {"radius": "soft", "unit": 8, "shadows": "soft"},
    "theme": {"modes": ["light", "dark"], "default": "light", "gradient": null},
    "icons": {"family": "fluent", "style": "regular", "size": 16},
    "imagery": {"mode": "abstract", "treatment": "papel, grão leve", "placeholder": "placehold"},
    "composition": {"direction": "editorial", "measure": "65ch", "grid": "12"},
    "logo": {"variant": "C", "name": "Colchete", "notes": "Dois colchetes e um bloco."}
  },
  "aceite": false
}
```

## Semantic tokens and their limits

`--b-color-<slug>` is the approved hex. Semantic tokens are the only colors
content may use; they may shift to meet WCAG and switch with the theme. Each is
emitted as `--b-<name>`: `--b-primary`, `--b-fg`, `--b-chart-1` and so on.

| Token | Guarantee / allowed use |
|---|---|
| `canvas`, `surface`, `surface-muted`, `surface-raised` | Backgrounds. |
| `band`, `on-band`, `on-band-muted`, `band-accent` | Optional dark brand band and readable text/accent. |
| `fg` | Body text; 7:1 against canvas and surface. |
| `fg-muted`, `fg-subtle` | Secondary text; at least 4.5:1. |
| `fg-disabled` | Decorative disabled state; never essential text. |
| `line`, `line-strong` | **Decorative** separators only. |
| `line-input` | **Control boundaries**; at least 3:1 against surface and canvas (WCAG 1.4.11). |
| `primary` | **UI fills and large text only**; at least 3:1 against canvas. Body text uses `link` or `fg`. |
| `primary-hover` | Hover fill; keeps the same `on-primary` at 4.5:1. |
| `on-primary` | Text/icon on `primary` and `primary-hover`; at least 4.5:1. |
| `primary-soft`, `on-primary-soft` | Tinted surface + readable text; 4.5:1. |
| `accent`, `accent-soft`, `on-accent` | Accent action and its readable text; 4.5:1. |
| `link` | Inline and body links; 4.5:1 against surface and canvas. |
| `focus` | Focus ring; at least 3:1. |
| `highlight`, `on-highlight` | Highlight fill + readable text; 4.5:1. |
| `--b-success`, `--b-warning`, `--b-danger`, `--b-info` | Feedback text; 4.5:1. |
| `<role>-soft`, `on-<role>-soft` | Tinted feedback surface + readable text; 4.5:1. |
| `<role>-solid`, `on-<role>` | Solid feedback fill + readable text; fill 3:1, text 4.5:1. |
| `chart-1` … `chart-8` | Data marks only; at least 3:1 against `surface`. |

Rules that follow:

- Never put body copy in `text-primary`; use `text-link` or `text-fg`.
- Never use `border-line` or `border-line-strong` on an input, select, textarea
  or button boundary. Use `border-line-input`.
- A `bg-primary` fill declares `hover:bg-primary-hover`; do not hand-pick a
  hover color.
- Feedback is for state, not decoration. Charts highlight one series and keep a
  table fallback.
- Do not derive a new color with opacity or a filter to "fix" contrast; pick the
  token that already carries the guarantee.

## Tailwind v4 mapping

`tailwind-theme.css` is the portable contract:

- `@custom-variant dark` binds `dark:` to `[data-theme="dark"]`.
- `@theme inline` maps every semantic color: `--color-surface: var(--b-surface)`,
  so `bg-surface` and `text-fg-muted` switch with the theme; `--font-sans` and
  `--font-display` point at `--b-body` and `--b-display`.
- `@theme` maps `--spacing` (unit), `--text-*` with coupled line-height,
  `--radius-*` and `--shadow-*`.
- `@utility bg-grad-brand` exists only when the brand defines a gradient.

The preview uses the pinned `@tailwindcss/browser` CDN. Production is the same
contract: install Tailwind v4, import `tailwind-theme.css` with the generated
`theme.css`, and keep the semantic classes. The CDN compiles in the browser and
costs startup time; it is a preview convenience, not a production dependency.

No product flavor and no fixed palette: every color, font, radius, spacing,
shadow and gradient comes from this `brand.json`.

## Using tokens in HTML

```html
<section class="bg-surface text-fg">
  <p class="text-fg-muted">Leitura contínua.</p>
  <a class="text-link" href="#contato">Falar com a gente</a>
  <button class="bg-primary text-on-primary hover:bg-primary-hover">Pedir agora</button>
  <input class="border border-line-input" />
  <p class="text-danger">[placeholder — mensagem de erro]</p>
  <div class="bg-grad-brand">…</div>
</section>
```

Forbidden in content: any bare hex, any `bg-blue-600`-style palette utility,
arbitrary color syntax, `text-primary` as body text, and any gradient other than
`bg-grad-brand` when the brand has one. Never duplicate content for dark; the
tokens switch.

## Token checklist

- [ ] `version` is `2` and every required key is present.
- [ ] Required roles exist; `accent`/`support` only if the route uses them.
- [ ] Feedback and charts are `auto` or intentional overrides.
- [ ] Radius, unit and shadows match the route; unit is 4 or 8.
- [ ] Dark is optional and tested; gradient is optional and absent by default.
- [ ] Body text uses `fg`/`link`; `primary` only on UI or large text.
- [ ] Control boundaries use `line-input`; `line`/`line-strong` stay decorative.
- [ ] Tailwind classes are semantic; no palette utility, bare hex or custom
      gradient.
- [ ] Swatches show `--b-color-*` or the approved hex, not a semantic guess.
