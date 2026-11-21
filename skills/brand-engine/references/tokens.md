# Tokens — brand.json, theme.css and the rules that keep them honest

This file is the schema and the usage contract for Phase 2. It describes what
`scripts/build_theme.py` actually enforces, not an idealized token system.

## Pipeline and exact API

```bash
python3 <skill>/scripts/build_theme.py --brand brand.json --out . [--force]
```

The command writes `theme.css` (`--b-*` custom properties, light and dark) and
`tailwind-theme.css` (semantic utility mapping) into `--out`. It refuses to
overwrite either file without `--force`.

| Call | Contract |
|---|---|
| `build_theme(brand_path, out_dir, force=False)` | -> `ThemeBuild(theme_css, tailwind_theme_css)`; validates, renders and writes both files. |
| `load_brand(brand_path)` | -> `dict`; reads and validates `brand.json`, returns the raw object. |
| `render_theme(brand)` | -> `ThemeBuild`; same render with no file I/O. |
| `resolve_brand_path(brand_flag=None, cwd=None)` | -> `Path` or `None`; `--brand` > `./brand.json` > `./brand/brand.json` > `None`. |
| `missing_brand_behavior()` | -> `"ask-for-path-or-discovery"`. |
| `contrast_ratio(foreground, background)` | -> float 1.0–21.0 (WCAG 2.x). |
| `BrandError` | malformed brand, unreadable path or schema violation. |
| `ThemeBuild` | NamedTuple `(theme_css, tailwind_theme_css)`. |

A missing `--brand` path raises `BrandError`; the CLI prints one actionable line
and exits `2`, never a traceback. Discovery order matches Phase 0 of `SKILL.md`.

## brand.json schema v1

Required keys unless marked optional. All strings are non-empty after trimming.

| Key | Shape |
|---|---|
| `purpose` | One sentence. |
| `persona` | Who the brand serves. |
| `territory` | Visual territory. |
| `archetype` | Brand archetype. |
| `attributes` | Non-empty list of short strings, e.g. `["rustico", "direto"]`. |
| `colors` | Object with non-empty `primary` and `secondary` lists of color objects. |
| `allowed_pairs` | Non-empty list of `{"bg": "<color ref>", "fg": "<color ref>", "use": "..."}`. |
| `gradient` | `{"from": "<color ref>", "to": "<color ref>", "angle": 45}`. |
| `fonts` | `{"display": {"family": "...", "fallback": "..."}, "body": {...}}`. |
| `scale` | `{"base": 16, "ratio": 1.25}`; base 12–32, ratio 1.05–1.8. |
| `unit` | Must be `8`; the 8px grid is fixed in V1. |
| `logo` | `{"variant": "C" | "B" | "A", "name": "..."?, "notes": "..."?}`. |
| `aceite` | Required boolean; `true` only after the manual is approved. No script enforces it. |
| `name` | Optional brand name; defaults to `Brand`. |
| `version` | Optional; when present it must be `1`. |
| `$schema` and other metadata | Optional and ignored by the builder. |

A color object is `{"name": "Brasa", "hex": "#A6402F", "note": "optional"}`.
`hex` is exactly `#RRGGBB`. Names must be unique case-insensitively and must not
collapse into the same CSS slug. Every color produces `--b-color-<slug>` with
the **approved hex**; semantic tokens may shift that value to meet contrast.

### Slug-lenient color references

`allowed_pairs[].bg`, `allowed_pairs[].fg`, `gradient.from` and `gradient.to`
accept either the display name (case-insensitive) or the slug derived from it.
A slug is built with NFKD, accents stripped to ASCII, lowercase, runs of
non-alphanumerics replaced by `-`, then trimmed. Examples:

| Color name | Accepted references |
|---|---|
| `Brasa` | `Brasa`, `brasa`, `BRASA` |
| `Terracota` | `Terracota`, `terracota` |
| `Rústico` | `Rústico`, `rustico` |
| `Creme` | `Creme`, `creme` |

Do not invent a spelling that is not the name or its slug: an unknown reference
is a `BrandError` listing the known colors.

## Named palette vs. semantic tokens

- `--b-color-<slug>` is the approved hex and never changes between themes.
- Semantic tokens (`--b-primary`, `--b-fg`, `--b-surface`, ...) are the only
  colors content may use. They are adjusted for WCAG and switch with
  `[data-theme="dark"]`.
- The manual and any swatch must show the approved hex from `brand.json` or
  `--b-color-*`, not an inferred semantic value.

## Semantic tokens and their limits

These limits are produced by `build_theme.py` and must be respected in content.

| Token | Guarantee / allowed use |
|---|---|
| `canvas`, `surface`, `surface-muted`, `surface-raised` | Backgrounds. |
| `fg` | Body text; 7:1 against `canvas`. |
| `fg-muted`, `fg-subtle` | Secondary text; at least 4.5:1 against `canvas`. |
| `fg-disabled` | Decorative disabled state; never essential text. |
| `line`, `line-strong` | **Decorative** separators only. |
| `line-input` | **Control boundaries**; at least 3:1 against `surface` and `canvas` (WCAG 1.4.11). |
| `primary` | **UI fills and large text only**; at least 3:1 against `canvas`. Body text uses `link` or `fg`. |
| `primary-hover` | Hover fill adjusted so the same `on-primary` keeps at least 4.5:1 on both `primary` and `primary-hover`. |
| `on-primary` | Text/icon on `primary` and `primary-hover`; at least 4.5:1. |
| `primary-soft`, `on-primary-soft` | Tinted surface + readable text; at least 4.5:1. |
| `accent`, `link` | At least 4.5:1 against `surface` and `canvas`. |
| `focus` | Focus ring; at least 3:1 against `surface` and `canvas`. |
| `highlight`, `on-highlight` | Highlight fill + readable text; at least 4.5:1. |
| `band`, `on-band`, `on-band-muted`, `band-accent` | Dark brand band and its readable text; accents at least 4.5:1 on the band. |

Rules that follow from the table:

- Never put body copy in `text-primary`. Use `text-link` or `text-fg`.
- Never use `border-line` or `border-line-strong` on an input, select, textarea
  or button boundary. Use `border-line-input`.
- A `bg-primary` fill declares `hover:bg-primary-hover`; do not hand-pick a hover
  color.
- Do not derive a new color with opacity or a filter to “fix” contrast; pick the
  semantic token that already carries the guarantee.

## Type scale

The scale has ten steps, `xs` through `6xl`, at exponents `n = -2 … 7`:

```text
size = round(base * ratio^n)
leading = 1.6                when n <= 0
leading = max(1.05, 1.6 - 0.07 * n)    when n > 0
```

`theme.css` emits `--b-text-<step>` and the coupled `--b-leading-<step>`;
`tailwind-theme.css` maps them to `text-<step>` with a coupled line-height.
Body text uses `text-base` or larger for reading. The checker rejects sizes
outside the generated steps (`text-7xl`, `text-[18px]`) unless they are a
semantic color or `var(--b-*)`.

## Spacing, radius and gradient

- `--b-unit: 8px`; spacing tokens are `--b-space-0` through `--b-space-16`,
  each an exact multiple of 8. Tailwind's `--spacing` is also `8px`, so `p-1` is
  8px and `p-4` is 32px.
- The checker rejects fractional steps and the coarse-scale gaps `5`, `7`, `9`,
  `11`; arbitrary pixels must be divisible by 8.
- Radius: `--b-radius-sm` 4px, `md` 8px, `lg` 16px, `xl` 24px, `full` 9999px.
- Gradient: exactly **two stops at 50/50, 45deg**, using the approved hex pair:
  `linear-gradient(45deg, from 50%, to 50%)`. The only utility is
  `bg-grad-brand`. No third stop, no other angle, no other gradient utility.

## Using tokens in HTML

```html
<section class="bg-surface text-fg">
  <p class="text-fg-muted">Leitura contínua.</p>
  <a class="text-link" href="#contato">Falar com a gente</a>
  <button class="bg-primary text-on-primary hover:bg-primary-hover">Pedir agora</button>
  <input class="border border-line-input" />
  <div class="bg-grad-brand">…</div>
</section>
```

Allowed semantic utilities include `bg-surface`, `text-fg`, `text-fg-muted`,
`text-link`, `border-line`, `border-line-input`, `bg-primary`,
`text-on-primary`, `hover:bg-primary-hover`, `bg-band`, `text-on-band`,
`bg-highlight`, `text-on-highlight`, `bg-grad-brand`, `font-display` and the
generated `text-*` steps. Forbidden in content: any bare hex, any
`bg-blue-600`-style palette utility, arbitrary color syntax, `text-primary` as
body text, and any gradient other than `bg-grad-brand`.

Dark mode is automatic through `[data-theme="dark"]`; never duplicate content
for dark. The logo uses tokens only: the symbol inherits `currentColor`, and a
monogram tile uses `bg-primary` + `text-on-primary`; never a bare hex.

## Worked example — Forno & Brasa

```json
{
  "version": 1,
  "name": "Forno & Brasa",
  "colors": {
    "primary": [
      {"name": "Brasa", "hex": "#A6402F", "note": "ação e assinatura"},
      {"name": "Terracota", "hex": "#C97B4A", "note": "apoio quente"}
    ],
    "secondary": [
      {"name": "Oliva", "hex": "#5F6B45", "note": "frescor e contraste"},
      {"name": "Creme", "hex": "#F4E9D8", "note": "superfície clara"}
    ]
  },
  "allowed_pairs": [
    {"bg": "Brasa", "fg": "Creme", "use": "CTA e faixa de marca"},
    {"bg": "creme", "fg": "brasa", "use": "mesmo par, forma slug"},
    {"bg": "Oliva", "fg": "Creme", "use": "selo e rodapé"}
  ],
  "gradient": {"from": "Brasa", "to": "terracota", "angle": 45}
}
```

`Brasa`/`brasa` and `Terracota`/`terracota` are the same reference. The emitted
`--b-color-brasa` stays `#A6402F`; `--b-primary` may move a little to keep 3:1
against the canvas.

## Hand-offs to the other references

- Characterful type and the full scale: `formats.md` shows how each format uses
  the steps; the equation remains this file.
- Discovery image input: a corrupt or unreadable inspiration image falls back to
  **text-only** with one line of explanation and never crashes (`discovery.md`).
- Logo intent: a detailed illustrative idea degrades to a **monogram or
  wordmark** after the 16px test (`logo.md`).
- Copy: unresolved facts stay as `[placeholder]` and are listed in the delivery
  **Nota** (`voice.md`).

## Token checklist

- [ ] `brand.json` parses and every required key is present.
- [ ] Every `allowed_pairs`/gradient reference is a known name or slug.
- [ ] Swatches show `--b-color-*` or the approved hex, not a semantic guess.
- [ ] Body text uses `fg`/`link`; `primary` only on UI or large text.
- [ ] Control boundaries use `line-input`; `line`/`line-strong` stay decorative.
- [ ] Sizes come from the scale; spacing is an 8px multiple.
- [ ] Only `bg-grad-brand`, two stops, 50/50, 45deg.
- [ ] No bare hex, palette utility or arbitrary color in content.
