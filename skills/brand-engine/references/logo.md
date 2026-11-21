# Logo — C → B → A, tested at 16px

The logo is the one asset that must survive the smallest and the darkest place it
appears. Resolve it in **cascade order C → B → A**, test at **16px**, and stop at
the first variant that passes. `brand.json` records the result in
`logo.variant` (`"C"`, `"B"` or `"A"`).

The generator does not draw final geometry. `new_page.py` writes a placeholder
`#be-mark` sprite and a lockup built from the chosen variant; you replace that
symbol's paths with the approved geometry and keep the id. Deliver the chosen
logo as `logo.svg` in the working directory, never inside the skill.

## Cascade

| Step | Variant | Use when |
|---|---|---|
| 1 | **C** — symbol (2–3 geometric shapes) + wordmark | Default. The symbol survives the 16px test and the wordmark is readable at its normal size. |
| 2 | **B** — monogram (1–2 initials) | The C symbol loses detail below ~24px, or the full C lockup is too wide for the nav/favicon. |
| 3 | **A** — wordmark alone | No symbol survives 16px, or the user's idea is too detailed/illustrative to reduce. |

Try C first, then B, then A. Do not skip to A because C is hard; do not keep C
because it looks better at 200%.

### C — symbol + wordmark

Two or three geometric shapes, one idea, no text inside the symbol. The symbol
and the wordmark share one grid and one angle family (0/45/90). C is the default
in `brand.json`.

### B — monogram

One or two initials set in the display face inside a rounded tile. The generated
page fills that tile with the `bg-primary` + `text-on-primary` tokens; a
standalone `logo.svg` draws the same tile and initials as paths. Use B when C's
symbol closes up, merges or disappears at small sizes, or when the C lockup is
too wide for a 16px nav/favicon slot. The monogram keeps the same grid, angle and
stroke weight as C so the family still reads as one brand.

### A — wordmark

The brand name alone, in the approved display face, with no symbol. Use A when
the symbol idea is too detailed to survive reduction or when the name is short
and distinctive enough to carry the brand by itself.

## The 16px rule

The delivered mark must be recognizable at **16×16 CSS px**, on **light and
dark**, at 100% and 200% zoom. Render 16/24/48px samples before approving.

- If a shape closes up, a counter fills in, two shapes merge or the mark becomes
  a blob, the variant fails.
- If C fails, degrade to B (monogram). If B is still ambiguous, degrade to A
  (wordmark). Explain the change in one line and record it in `logo.variant`.
- Never shrink below 16px. For a favicon, use the symbol or monogram at 16px;
  do not add a smaller size.
- The manual shows 16px, 24px and 48px with the breathing area marked.

## Construction and SVG rules

- `viewBox="0 0 32 32"` for the symbol (or a square of the same proportion);
  keep the mark centered with equal optical margins.
- Two or three shapes, one visual idea. No gradients, filters, shadows, bevels or
  3D. No text inside the symbol.
- One color: `fill="currentColor"` / `stroke="currentColor"` for the symbol; no
  hex, no palette utility, no second color.
- A monogram tile uses the semantic tokens `bg-primary` + `text-on-primary` in
  HTML, or the same solid fill in `logo.svg`. No hex and no separate palette.
- Standalone `logo.svg` gets `role="img"` and a `<title>` with the brand name.
  The inline sprite `<symbol id="be-mark">` stays presentational (no title) and
  is referenced with `<use href="#be-mark">`.
- The sprite is the first element inside `<body>` in every generated page; keep
  the id `be-mark` when you replace the placeholder path.
- The wordmark uses the approved display stack. In generated pages it is a
  `span`; in `logo.svg`, outline it or keep a live `text` with the same stack so
  it travels.

## Breathing area = S

Keep clear space equal to **S = 8px = `--b-space-1`** on all four sides. Nothing
enters that area: no text, border, image edge or another logo. Apply it as
padding/margin in layout, not as a visible box. The height S is the same unit
used by the 8px grid, so the logo aligns with the rest of the page.

## Light and dark

`currentColor` is the strategy for the symbol: each placement chooses a token
with a guarantee — `text-fg` on canvas and surface, `text-on-band` on the dark
band, `text-accent` where the nav uses the accent. A monogram tile uses
`bg-primary` + `text-on-primary`. Test light and dark without editing the SVG.
If contrast fails, move the logo to a token with a guarantee (`text-fg`,
`text-on-band`, `text-accent`); never hard-code a color or add an outline to
“fix” it.

## Misuses (usos proibidos)

Document all of these in the manual; the checker looks for the four terms.

- **Recolor** outside the approved palette, or apply a gradient to the logo.
- **Rotate**, tilt, mirror or skew the symbol.
- **Stretch**, compress or change the symbol/wordmark proportion.
- **Replace** the symbol with an emoji, generic icon, raster image or a different
  mark.
- Apply shadow, glow, outline or 3D.
- Place over a photo or color without AA contrast.

## Detailed idea — degrade, do not trace

If the user pastes a **detailed or illustrative** logo idea (many shapes, fine
lines, gradients, text inside the mark, a literal oven with bricks), it will not
survive 16px. Do not trace it into the symbol and do not promise it will work.

1. Say in one line that the idea cannot survive 16px.
2. **Degrade** to B (monogram) or A (wordmark), in that order.
3. Record `logo.variant` and explain the change in the delivery **Nota**.

A detailed illustration can still live as an illustration elsewhere; it is not
the logo.

## Worked example — Forno & Brasa

The approved idea is **Chama**: a flame plus the oven arch, two shapes, one
angle family, `currentColor`. That is C: symbol + “Forno & Brasa” wordmark.

- At 16px the flame's inner curve starts to merge, so the nav/favicon uses the
  **B monogram “FB”**; the landing header may still use C above 24px.
- If the client's real idea is a detailed brick oven with many lines, **degrade**
  to A: the wordmark “Forno & Brasa” in Fraunces, no symbol.
- Keep S = 8px around every variant and test on `canvas`, `surface` and `band`.

## Logo checklist

- [ ] Variant chosen by the cascade, not by preference: C → B → A.
- [ ] Recognizable at 16px on light and dark; 16/24/48px samples checked.
- [ ] Two or three shapes, one idea, no text inside the symbol.
- [ ] Symbol is one color via `currentColor`; a monogram tile is a single solid brand fill (`bg-primary` + `text-on-primary` in HTML). No hex, gradient, shadow or filter.
- [ ] `viewBox` square; `role`/`<title>` on standalone SVG; `#be-mark` kept in
      the sprite.
- [ ] Breathing area S = 8px (`--b-space-1`) on all sides.
- [ ] Misuses documented: recolor, rotate, stretch, replace, shadow, low contrast.
- [ ] A detailed idea degraded to monogram or wordmark with a written reason.
