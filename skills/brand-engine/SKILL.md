---
name: brand-engine
description: Use when someone has a vague brand idea, a loose color, a missing logo, or reference screenshots and needs a defensible, flexible identity turned into an approved HTML brand manual, a brand-kit, and 2–3 HTML formats (landing, deck, report, social, app) built with Tailwind v4, Iconify, Chart.js and placehold.co. Also use when asked to "create a brand", "build a brand guide", "make a one-pager with my brand", "turn this into slides", or to restyle a page for a new brand. Not for .pptx, PDF, Word or e-mail export, social image export, production React/Vue components, or a complete e-commerce build.
metadata:
  version: "0.2.0"
---

# Brand Engine

**CRITICAL LANGUAGE RULE:** All copy, labels, questions and deliverables must be in the language the user speaks to you in. Portuguese in, Portuguese out; English in, English out. The default when the user has not written in a language yet is pt-BR. The generator's starter copy is pt-BR: when the user's language differs, translate the manual and every format before delivery and set `language` in `brand.json` (BCP-47, default `pt-BR`); it is emitted as `<html lang>`. Code, CLI flags and file names stay in English.

## Overview

Brand Engine takes the material a small team actually has — a loose color, a logo that does not exist yet, a few inspiration screenshots, one sentence about the business — and produces a brand system that can survive a real client review.

The manual is the source of truth. The brand-kit is the proof of the system. The other formats apply it. Every HTML file is single-file, mobile-first (375px), light/dark with a switch, and styled only through semantic tokens. The target is WCAG 2.2 AA.

The skill is flexible by design: the route carries the visual system (color roles, type, shape, composition, icons, imagery), the skeletons are starting points, and the agent composes from the reference catalog. The skill is self-contained and vendored: scripts, assets and references live here, and generated brand artifacts live in the user's working directory, never inside this skill.

## Hard Gates

<HARD-GATE>
**No fabrication.** Never invent facts, numbers, dates, clients, testimonials, awards, product names, metrics or sources that the user did not provide. If a needed fact is missing, ask once; if it stays missing, write `[placeholder — what is needed]` and list it in the delivery note. Derived values such as Pantone approximations must be labeled as approximations.
</HARD-GATE>

<HARD-GATE>
**Manual approval is mandatory.** Do not generate the brand-kit or any format before the user explicitly approves the manual. The gate is prompt-only: it lives in this wording, not in a script. No script reads the acceptance flag or blocks `new_page.py`; you are the enforcement.
</HARD-GATE>

<HARD-GATE>
**Never overwrite without `--force`.** Every generator accepts `--force`, but generated files never replace an existing file without it. If a target exists, stop and ask; only pass `--force` when the user explicitly asks to replace it.
</HARD-GATE>

<HARD-GATE>
**Brand artifacts stay outside the skill.** Never write `brand.json`, `theme.css`, `tailwind-theme.css`, `logo.svg`, the manual, the brand-kit or any format inside `skills/brand-engine/`. The skill directory is code and documentation only.
</HARD-GATE>

<HARD-GATE>
**Only semantic tokens in HTML.** Content uses classes and variables such as `bg-surface`, `text-fg-muted`, `border-line` or `var(--b-primary)`. Never a bare hex in a class or `style`, and never a palette utility such as `bg-blue-600`. The theme must switch to dark without editing content.
</HARD-GATE>

<HARD-GATE>
**Online dependencies are part of the contract.** Tailwind, fonts, icons, charts and placeholders load from CDNs. Never promise that a delivered page works offline. Say that it needs internet, and keep textual labels next to every icon.
</HARD-GATE>

## Working with the user

**Propose, don't interrogate.** The skill returns a system the user can react to; it does not collect decisions. Ask only the unanswered discovery questions, then propose the visual system with the route. The user accepts, swaps the route or adjusts one point.

- **Recommended first.** Propose 2–3 routes and mark exactly one as recommended, with the "why" in one line. The same applies to formats: propose the 2–3 that fit the context.
- **Granularity on demand.** The default flow does not ask about radius, spacing, scale, icon family or chart colors. If the user asks ("quero ajustar o radius"), open the control and record the choice in `brand.json`.
- **Post-delivery adjustments.** `brand.json` is the state. "Ajusta X" regenerates the manual and the brand-kit (unless the user skipped it), restyles each delivered page in place so the composed copy survives, then revalidates, without restarting discovery. Full regeneration with `--force` only when the user explicitly asks to replace a page.
- **The delivery note lists assumptions and placeholders.** The user sees what the skill decided for them and what is still missing.

## Execution Flow

### Phase 0: Resolve the brand source

Look for an existing brand in this order and stop at the first hit:

1. `--brand <path>` passed by the user.
2. `./brand.json` in the working directory.
3. `./brand/brand.json` in the working directory.
4. If none exists, ask one short question and run discovery.

A path the user gives always wins. If a found file is malformed, say what is wrong and ask for a corrected path; never generate HTML with empty tokens. The brand contract is v2 (`"version": 2`); there is no v1 compatibility mode, migrator or dual parser. An older file is rewritten by hand using `references/tokens.md`.

### Phase 1: Discovery — propose routes

Ask 5–8 short questions, only the ones the user has not already answered. Cover purpose in one sentence, persona, visual territory, archetype, two visual references, productive vs. expressive register, and where the brand will live first (landing, deck, report, social, app). Text is enough; images in the working directory are optional input. A corrupt or unreadable image is ignored with one line of explanation — never a crash, never a retry loop.

Propose 2–3 routes. Mark exactly one as recommended and say why in one line. Each route carries the visual system: named palette roles (`canvas`, `surface`, `ink`, `primary`, optional `accent`/`support[]`), display and body type direction, shape (radius profile, unit 4/8, shadows), composition direction, icon family, imagery treatment and the 2–3 formats that fit. Show a short summary (palette, type, shape, composition) so the user can react. Use `references/discovery.md` for the closed question list and the route template.

#### Gate 1 — Route confirmation

**Prompt-only.** Generate nothing — no `brand.json`, no theme, no logo, no HTML — until the user confirms one route. If the user rejects every route, ask one discriminating question and propose a new set. If the user does not answer, stop and wait; do not guess a route.

### Phase 2: Theme and logo

Write `brand.json` from the approved route using the v2 schema in `references/tokens.md` (include `language` when the delivery is not pt-BR), then build the theme:

```bash
python3 <skill>/scripts/build_theme.py --brand brand.json --out . [--force]
```

This emits `theme.css` with `--b-*` variables and `tailwind-theme.css` with the semantic utility mapping (`@theme`, `@theme inline`, `@custom-variant dark`, `--spacing`). Feedback and chart colors default to `auto`; dark and gradient are optional.

Resolve the logo in cascade order C → B → A and write `logo.svg` in the working directory:

- **C:** simple symbol (2–3 geometric shapes) plus wordmark.
- **B:** monogram when the C symbol breaks at small sizes or the lockup is too wide.
- **A:** wordmark alone when the symbol idea is too detailed.

All variants share one grid and angle, stay legible at 16px on light and dark, and keep a breathing area equal to the spacing unit `S` (`--b-space-1`, 4px or 8px). The symbol uses `currentColor`; a monogram tile uses `bg-primary` + `text-on-primary`. A detailed illustrative idea is degraded to B or A with a written reason, never traced. Use `references/logo.md`.

### No third gate

The approved route already carries the proposed visual system. There is no third gate between the route and the manual: show a short summary (palette, type, shape, composition), let the user adjust a point there or at the manual gate, and keep moving. The manual gate is the only mandatory gate.

### Phase 3: Manual — the mandatory gate

Generate the manual:

```bash
python3 <skill>/scripts/new_page.py --brand brand.json --format manual --title "Manual de Marca" --out manual.html
```

The manual contains: purpose and positioning; voice with SOMOS / NÃO SOMOS and right/wrong examples; colors with roles, hex/RGB, feedback, charts, pairs and the optional gradient; display and body type with the scale equation and line-heights; logo construction, variants, breathing area and misuses; grid and spacing; icon family and usage; imagery treatment; components; composition; applications; and signature. "NÃO SOMOS" is proposed from the route and attributes and confirmed at the gate. Use `references/formats.md`.

#### Gate 2 — Manual approval (mandatory, prompt-only)

**Prompt-only.** Present the manual path and a short checklist, then ask for an explicit `ok`. The gate is wording, not enforcement: no script reads the acceptance flag or blocks the next phase. Do not generate any template — not the brand-kit, not a landing — until the user says ok. If the user requests changes, revise the manual and repeat this gate. If the user does not answer, stop; the job stays at the manual. Record the approval as `"aceite": true` in `brand.json` only after the explicit ok.

### Phase 4: Brand-kit and formats

After approval, generate the brand-kit by default:

```bash
python3 <skill>/scripts/new_page.py --brand brand.json --format brand-kit --title "Brand Kit" --out brand-kit.html
```

The brand-kit is the living proof of the system and the menu of formats: logo, colors, feedback, charts, type, icons, imagery, components and mini cases. It is not one of the 2–3 delivery formats. If the user asked for a single artifact ("só o relatório", "sem kit"), skip the brand-kit and say so in the delivery note.

Then propose the 2–3 formats that fit the context and confirm the set — a lightweight choice, not a gate:

```bash
python3 <skill>/scripts/new_page.py --brand brand.json --format <fmt> --title "..." --out <name>.html [--theme light|dark|system|light-only|dark-only] [--force]
```

To adjust a delivered page after approval (palette, type, spacing, radius, shadow, gradient) without losing composed copy, restyle only its generated theme blocks:

```bash
python3 <skill>/scripts/new_page.py --brand brand.json --restyle --out <page>.html
```

Use `--force` for a full regeneration only when the user explicitly asks to replace the page.

| Format | Job |
|---|---|
| `manual` | Governs: the approval artifact and source of truth. |
| `brand-kit` | Proves: the living proof and format menu. |
| `onepage` | Sells: one promise, one action. |
| `report` | Explains: conclusion first, evidence next. |
| `deck` | Presents: one idea per slide, at 1280×720. |
| `social` | Interrupts: 1080×1080, 1080×1920 and 1080×1350 mockups. |
| `app` | Operates: the product surface, without a product flavor. |
| `blank` | Hosts: cartaz, convite, menu, cheatsheet or any custom page. |

Each generator output is a **starter page**, not a mold: keep, cut, merge or add sections until the argument is right, guided by `design.composition.direction`. Compose from `references/components.md` and `references/sections.md`; use `references/formats.md` for each format's job and `references/voice.md` for tone. Copy inherits the manual's voice but is never pasted unchanged across formats. Unknown numbers, dates, names, claims or quotes stay `[placeholder]`.

### Phase 5: Validate and deliver

Run the checker on every generated HTML file:

```bash
python3 <skill>/scripts/check_page.py <file> [<file> ...] [--strict] [--brand brand.json]
```

Fix every **ERROR**. Fix **WARN** unless there is a written reason not to. Then check at 375px width, in light and dark, with keyboard navigation. For `deck`, confirm no slide overflows 1280×720; for `social`, respect the safe zones.

If a browser is available, run the optional rendered audit and inspect the pages:

```bash
python3 <skill>/scripts/axe_copy.py <file>
```

Open the `.axe.html` copy over `http://`, read `#axe-out`, then delete the copy. If no browser is available, say the visual check was not performed.

Deliver with the path and a 1–2 line note: what is inside, how to use it (deck keys, theme switch), what was assumed, and every placeholder that remains. Do not paste the full content of the files into chat.

## Dependencies

All pages need internet. Offline they lose styling, icons and charts even though the HTML is local; there is no offline mode and no service worker.

- **Tailwind v4.** The preview pins the browser build, `@tailwindcss/browser@4.3.3`; it compiles in the browser and is a preview convenience, not a production dependency. `tailwind-theme.css` is the portable contract: a real project installs Tailwind v4 and imports `theme.css` + `tailwind-theme.css`, keeping the semantic classes.
- **Google Fonts.** Display and body families load from the Google Fonts CDN; the fallback stack in `brand.json` keeps the page readable if they fail.
- **Iconify.** `iconify-icon@3.0.0` (~24KB); the family comes from `design.icons.family` (`fluent` default, `lucide`, `phosphor`, `tabler`). SVG inherits `currentColor`; decorative icons are `aria-hidden`, meaningful icons have a label.
- **Chart.js.** `chart.js@4.4.7` loads only on `report`, `app` and `brand-kit`. The generated `BrandCharts` helper reads `--b-chart-1`…`--b-chart-8`, `--b-fg-subtle`, `--b-line` and `--b-surface`, and rebuilds on theme change.
- **placehold.co.** Images use `https://placehold.co/{w}x{h}/{bg}/{fg}?text=...` with brand hex without `#`; a dark variant is provided per image and swapped by the theme script. `alt` describes the intention.
- **`axe_copy.py`.** Optional rendered contrast/a11y audit; needs a browser and internet.
- **Not used:** no random stock photography, no Unsplash and no unDraw; no offline promise.

See `references/integrations.md` for the pinned URLs and limits.

## Output Contract

All paths are relative to the user's working directory. Nothing is written inside the skill.

| File | Contents |
|---|---|
| `brand.json` | The approved v2 state: purpose, persona, territory, archetype, attributes, optional `language` and voice, `design` (colors by role, feedback, charts, type, shape, theme, icons, imagery, composition, logo) and the `aceite` flag. |
| `theme.css` | `--b-*` custom properties for colors, surfaces, text, feedback, charts, focus, type, spacing, radius, shadows, optional gradient, light and optional dark. |
| `tailwind-theme.css` | Maps the `--b-*` variables to Tailwind v4 semantic utilities such as `bg-surface`, `text-fg-muted`, `border-line`. |
| `logo.svg` | The chosen logo variant: symbol in one color via `currentColor`, a monogram tile as a single solid brand fill, with viewBox and accessible title. |
| `manual.html` | The single-file manual; the approval artifact and source of truth. |
| `brand-kit.html` | The living proof of the system and the format menu; generated by default. |
| Format HTML files | One file per confirmed format (`onepage`, `report`, `deck`, `social`, `app`, `blank`), single-file, mobile-first, light/dark, tokens only, semantic and composed from the catalog. |

File names for templates are chosen with the user in kebab-case. Every generated page embeds the logo sprite at the top of `<body>` (`app` uses an inline topbar lockup) and keeps the theme toggle when the brand has both modes.

## Validation

Before delivering, confirm:

- [ ] `brand.json` parses as v2 and `aceite` is `true` only after the explicit ok.
- [ ] `check_page.py` reports zero ERROR on every generated HTML file.
- [ ] One `<main>`, one `h1`, heading order intact, accessible names on controls, tables with `caption` and scoped `th`.
- [ ] Only semantic tokens: no bare hex, no palette utilities, no product flavor.
- [ ] Contrast meets WCAG 2.2 AA in light and dark, including feedback and chart tokens; the logo is legible at 16px.
- [ ] Type sizes belong to the generated scale; spacing is a multiple of the brand unit (4 or 8).
- [ ] Icons are decorative or labeled; images use `placehold.co` with a meaningful `alt` and the dark variant when needed.
- [ ] Copy contains no invented fact; unresolved facts use `[placeholder]` and appear in the delivery note.
- [ ] Language matches the user; `language` is set (default pt-BR) and matches `<html lang>`; the starter copy was translated when needed.
- [ ] 375px has no horizontal scroll; keyboard reaches all controls; the theme switch works; deck overflow and social safe zones were checked.
- [ ] The delivery note says the page needs internet and whether the browser check was performed.

## Boundaries

Do not use this skill for:

- **v1 compatibility.** The v2 contract is final; there is no migrator, no dual parser and no legacy token mode. Rewrite an older `brand.json` by hand.
- **Product flavor.** No flavor flag, no flavor attribute, no fixed palette or tokens borrowed from another product.
- **Stock imagery.** No Unsplash and no unDraw.
- **`.pptx`, Google Slides, PDF, Word or e-mail HTML export.** This skill produces **HTML** only.
- **Social image export (PNG/JPG).** Social formats are HTML mockups at 1080×1080, 1080×1920 and 1080×1350 for reference.
- **Production React/Vue/Next components.** Templates are meant to be componentized later, not shipped as a design system.
- **A complete e-commerce, checkout, payment flow, backend or platform build.** At most, a template that a storefront team can adapt.
- **Self-service onboarding, billing or support products.**

Other limits: Tailwind loads from a pinned CDN and every page needs internet. The manual gate is prompt-only and depends on you actually asking. If the user asks for any out-of-scope deliverable, say what this skill produces and stop.

## References

| Reference | Use it for |
|---|---|
| [discovery.md](references/discovery.md) | The 5–8 questions, route template, optional images and Gate 1. |
| [tokens.md](references/tokens.md) | The `brand.json` v2 schema, `theme.css`, `tailwind-theme.css` and contrast. |
| [formats.md](references/formats.md) | The eight formats, their jobs, starter sections and copy rules. |
| [voice.md](references/voice.md) | Brand-agnostic tone derived from attributes, SOMOS / NÃO SOMOS, examples. |
| [logo.md](references/logo.md) | The C → B → A cascade, the 16px test, breathing area and misuses. |
| [components.md](references/components.md) | 21 component patterns with semantic classes, light/dark and a11y. |
| [design-principles.md](references/design-principles.md) | Message, space, hierarchy, composition directions and what to avoid. |
| [sections.md](references/sections.md) | The section catalog (hero, proof, app shell, states, forms) — not a renderer. |
| [integrations.md](references/integrations.md) | Tailwind v4, Iconify, Chart.js, `placehold.co` and `axe_copy.py` contracts. |
