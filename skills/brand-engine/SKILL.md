---
name: brand-engine
description: Use when someone has a vague brand idea, a loose color, a missing logo, or reference screenshots and needs a defensible identity turned into an approved HTML brand manual plus landing, deck, report, or social HTML. Also use when asked to "create a brand", "build a brand guide", "make a one-pager with my brand", "turn this into slides", or to restyle a page for a new brand. Not for .pptx, PDF, Word, or e-mail HTML export, production React components, or a complete e-commerce build.
metadata:
  version: "0.1.0"
---

# Brand Engine

**CRITICAL LANGUAGE RULE:** All copy, labels, questions and deliverables must be in the language the user speaks to you in. Portuguese in, Portuguese out; English in, English out. The default when the user has not written in a language yet is pt-BR. Code, CLI flags and file names stay in English.

## Overview

Brand Engine takes the material a small team actually has — a loose color, a logo that does not exist yet, a few inspiration screenshots, one sentence about the business — and produces a brand system that can survive a real client review.

The manual is the source of truth. Templates are proof that the manual works, not a substitute for it. Every HTML file is single-file, mobile-first (375px), light/dark with a switch, and styled only through semantic tokens. The target is WCAG 2.2 AA.

The skill is self-contained and vendored: scripts, assets and references live here, and generated brand artifacts live in the user's working directory, never inside this skill.

## Hard Gates

<HARD-GATE>
**No fabrication.** Never invent facts, numbers, dates, testimonials, clients, awards, color names, Pantone matches or sources that the user did not provide. If a needed fact is missing, ask once; if it stays missing, write `[placeholder]` and list it in the delivery note. Pantone values derived from hex are approximations and must be labeled as such.
</HARD-GATE>

<HARD-GATE>
**Manual approval is mandatory.** Do not generate any template before the user explicitly approves the manual. The gate is prompt-only: it lives in this wording, not in a script. No script checks the acceptance flag or blocks `new_page.py`; you are the enforcement.
</HARD-GATE>

<HARD-GATE>
**Never overwrite without `--force`.** If a target file exists, stop and ask. Only pass `--force` when the user explicitly asks to replace it.
</HARD-GATE>

<HARD-GATE>
**Brand artifacts stay in the working directory.** Never write `brand.json`, `theme.css`, `tailwind-theme.css`, `logo.svg`, the manual or any template inside `skills/brand-engine/`. The skill directory is code and documentation only.
</HARD-GATE>

<HARD-GATE>
**Only semantic tokens in HTML.** Content uses classes and variables such as `bg-surface`, `text-fg-muted`, `border-line` or `var(--b-primary)`. Never a bare hex in a class or `style`, and never a palette utility such as `bg-blue-600`. The theme must be able to switch to dark without editing content.
</HARD-GATE>

## Execution Flow

### Phase 0: Resolve the brand source

Look for an existing brand in this order and stop at the first hit:

1. `--brand <path>` passed by the user.
2. `./brand.json` in the working directory.
3. `./brand/brand.json` in the working directory.
4. If none exists, ask one short question and run discovery.

A path the user gives always wins. If a found file is malformed, say what is wrong and ask for a corrected path; never generate HTML with empty tokens. Every generator script (`build_theme.py`, `new_page.py`) accepts `--force`, but generated files never overwrite an existing file without it.

### Phase 1: Discover — propose routes

Ask 5–8 short questions, only the ones the user has not already answered. Cover purpose in one sentence, persona, territory, archetype, two visual references, productive vs. expressive register, and where the brand will live (landing, deck, report, social). Text is enough; if images are in the working directory, read them as optional input. A corrupt or unreadable image is ignored with one line of explanation — never a crash.

Propose 2–3 routes. Each route needs a name, a one-line idea, the palette and type direction it implies, and why it fits the answers. Use `references/discovery.md` for the closed question list and the route template.

#### Gate 1 — Route confirmation

**Prompt-only.** Ask the user to pick one route. Do not generate the theme, the logo or any file before the answer. If the user does not answer, stop and wait; do not guess a route. If the user rejects every route, ask one discriminating question and propose a new set.

### Phase 2: Theme and logo

Write `brand.json` from the approved route using the schema in `references/tokens.md`. Then build the theme:

```bash
python3 <skill>/scripts/build_theme.py --brand brand.json --out .
```

This emits `theme.css` with `--b-*` variables and `tailwind-theme.css` with the semantic utility mapping. Resolve the logo in cascade order C → B → A:

- **C:** simple symbol (2–3 geometric shapes) plus wordmark.
- **B:** monogram when C would break at small sizes.
- **A:** wordmark alone when the symbol idea is too detailed.

All variants share one grid and angle, use `currentColor`, stay legible at 16px, and keep a breathing area equal to the spacing unit `S`. Test on light and dark before showing the result. If the user pastes a detailed illustrative logo idea that cannot survive 16px, degrade to B or A and explain why. Use `references/logo.md` for construction, the 16px test and the fallback rules.

### Phase 3: Manual — the mandatory gate

Generate the manual:

```bash
python3 <skill>/scripts/new_page.py --brand brand.json --format manual --title "Manual de Marca" --out marca-manual.html
```

The manual contains: purpose and positioning; tone of voice with SOMOS / NÃO SOMOS and right/wrong examples; colors with hex, RGB and approximate Pantone, allowed pairs and the 50/50 gradient at 45°; display and body type with the scale equation and line-height; logo construction, variants, breathing area and misuses; grid and spacing in multiples of 8px; photo and icon checklists; and signature rules.

#### Gate 2 — Manual approval (mandatory, prompt-only)

**Prompt-only.** Present the manual path and a short checklist, then ask for an explicit `ok`. The gate is wording, not enforcement: no script reads the acceptance flag or blocks the next phase. Do not generate any template until the user says ok. If the user requests changes, revise the manual and repeat this gate. If the user does not answer, stop; the job stays at the manual. Record the approval as `"aceite": true` in `brand.json` only after the explicit ok.

### Phase 4: Templates

Propose the formats that fit where the brand will live. A pizzeria usually needs a landing plus social posts; a B2B consultancy usually needs a landing, a deck and a report. Ask for confirmation of the set — this is a lightweight choice, not a third hard gate.

```bash
python3 <skill>/scripts/new_page.py --brand brand.json --format onepage --title "..." --out <name>.html
python3 <skill>/scripts/new_page.py --brand brand.json --format deck --title "..." --out <name>.html
python3 <skill>/scripts/new_page.py --brand brand.json --format report --title "..." --out <name>.html
python3 <skill>/scripts/new_page.py --brand brand.json --format social --title "..." --out <name>.html
```

Each format has its own job: landing sells, report explains, deck presents, social interrupts. Copy inherits the manual's voice but never copies the same text across formats. Use `references/formats.md` for structure and `references/voice.md` for tone. Unknown numbers, dates, names or claims stay as `[placeholder]`.

### Phase 5: Validate and deliver

Run the checker on every generated HTML file:

```bash
python3 <skill>/scripts/check_page.py <file>
```

Fix every **ERROR**. Fix **WARN** unless there is a written reason not to. Then check the manual and templates at 375px width, in light and dark, with keyboard navigation. If a browser is available, open the files and inspect them; if not, say the visual check was not performed.

Deliver with the path and a 1–2 line note: what is inside, how to use it (deck keys, theme switch), and what was assumed or left out. Do not paste the full content of the files into chat.

## Output Contract

All paths are relative to the user's working directory. Nothing is written inside the skill.

| File | Contents |
|---|---|
| `brand.json` | Approved decisions: purpose, persona, territory, archetype, attributes, named primary/secondary colors with hex, allowed pairs, gradient 50/50 at 45°, display/body fonts, scale, 8px unit, logo variant, and the `aceite` flag. |
| `theme.css` | `--b-*` custom properties for colors, type, spacing, radius and theme switching. |
| `tailwind-theme.css` | Maps the `--b-*` variables to semantic utilities such as `bg-surface`, `text-fg-muted`, `border-line`. |
| `logo.svg` | The chosen logo variant, one color via `currentColor`, with viewBox and accessible title. |
| `marca-manual.html` | The single-file manual described in Phase 3; the approval artifact. |
| Format HTML files | One file per confirmed format (`onepage`, `deck`, `report`, `social`), single-file, mobile-first, light/dark, tokens only. |

File names for templates are chosen with the user in kebab-case. Every HTML file embeds the logo sprite at the top of `<body>` and keeps the theme toggle.

## Validation

Before delivering, confirm:

- [ ] `brand.json` parses and every color pair used in the HTML is in its allowed pairs.
- [ ] `check_page.py` reports zero ERROR on each HTML file.
- [ ] One `<main>`, one `h1`, heading order intact, accessible names on controls, tables with `caption` and `th`.
- [ ] Logo sprite present in `<body>`; logo legible at 16px, one color via `currentColor`, breathing area = `S`.
- [ ] Contrast meets WCAG 2.2 AA in light and dark; gradient has exactly two stops at 45°.
- [ ] Type sizes belong to the scale; spacing is a multiple of 8px.
- [ ] Copy contains no invented fact; unresolved facts use `[placeholder]` and appear in the delivery note.
- [ ] Language matches the user; default is pt-BR.
- [ ] 375px has no horizontal scroll; keyboard reaches all controls; theme switch works.

## Boundaries

Do not use this skill for:

- `.pptx`, Google Slides, PDF, Word or e-mail HTML export. This skill produces **HTML** only.
- Social image export (PNG/JPG). Social formats are HTML mockups at 1080×1080 and 1080×1920 for reference.
- Production React/Next components. Templates are meant to be componentized later, not shipped as a design system.
- A complete e-commerce, checkout, payment flow, backend or platform build. At most, a template that a storefront team can adapt.
- Self-service onboarding, billing or support products.

Other limits: Tailwind loads from a pinned CDN, so **offline the page loses its styling**. The manual gate is prompt-only and depends on you actually asking. If the user asks for any out-of-scope deliverable, say what this skill produces and stop.
