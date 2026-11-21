# Formats — eight formats, eight jobs, one system

`scripts/new_page.py` turns an approved `brand.json` v2 into one self-contained
HTML **starter page** per format. The starter has default sections and copy
slots; it is a ponto de partida, not a finished page and not a mold (não é
molde). Compose from
`components.md` and `sections.md`, guided by `design.composition.direction`.

```bash
python3 <skill>/scripts/new_page.py --brand brand.json --format <fmt> \
  --title "..." --out <name>.html [--theme light|dark|system|light-only|dark-only] [--force]
```

| Call | Contract |
|---|---|
| `new_page(fmt, brand, title, out, theme=None, force=False)` | -> `Path` of the written file; `brand` is a `brand.json` path. |
| `render_page(fmt, brand, title, theme=None)` | -> HTML string, no I/O; `brand` is the parsed dict. |
| `--out` | An `.html`/`.htm` file, or a directory where `<fmt>.html` is written. |
| `--theme` | `light`, `dark`, `system`, `light-only` or `dark-only`; `None` follows `design.theme.default`. Single-mode brands are locked and render no toggle. |
| `--force` | Required to replace an existing file; nothing is overwritten silently. |

`fmt` is exactly `manual`, `brand-kit`, `onepage`, `report`, `deck`, `social`,
`app` or `blank`. Every page embeds the pinned Tailwind browser CDN, the Google
Fonts link, the generated `theme.css` + `tailwind-theme.css`, the no-flash theme
script, the logo lockup and the theme toggle (when the brand has both modes).
Iconify loads only on `manual`, `onepage`, `report`, `app` and `brand-kit`;
Chart.js only on `report`, `app` and `brand-kit`; `placehold.co` appears only
where the composition needs an image. Every page has one `<main>`, one `<h1>`,
semantic tokens only, and must pass `check_page.py` with zero ERROR before
delivery.

## Starter page, not mold

- The skeleton is ponto de partida: keep, cut, merge or add sections until the
  argument is right. A page that only fills the default slots usually looks like
  every other page.
- Sections give the vocabulary; `components.md` gives the markup; this file
  gives the format's job. The composition direction (direção de composição)
  gives the hierarchy: `editorial` (large headline, reading column, images with
  air), `structured` (explicit grid, aligned blocks, medium density), `poster`
  (large type, high contrast, few elements) and `minimal` (space, hierarchy by
  weight and position).
- `design.composition.direction` guides section order, grid, measure and rhythm.
  It does **not** generate a 4×8 matrix of skeleton files. Variety comes from
  composition plus the catalog, not from 32 files.
- Default sections are a suggestion, not a checklist. Format-specific rules
  below are jobs; obey the job, not the count.

## Format map

| Format | Job | Default starter |
|---|---|---|
| `manual` | Governs: approval artifact and source of truth. | Purpose, voice, colors, type, logo, grid, icons, imagery, components, composition, applications, signature. |
| `brand-kit` | Proves: the living proof and format menu. | Logo, colors, feedback, charts, type, icons, imagery, components, mini cases. |
| `onepage` | **Vende**: one promise, one action. | Hero, proof, how it works, testimonial, CTA. |
| `report` | **Explica**: conclusion first, evidence next. | Cover, executive summary, data, trend, findings, recommendations. |
| `deck` | **Apresenta**: one idea per slide. | Cover, divider, assertion, big number, quote, closing. |
| `social` | **Interrompe**: one idea per frame. | 1080×1080 feed, 1080×1920 story, 1080×1350 image mockups. |
| `app` | **Opera**: the product surface. | Topbar, sidebar, page header, stats, list, states, chart, dialog form. |
| `blank` | Hosts: cartaz, convite, menu, cheatsheet or any custom page. | Logo, `h1`, purpose, attribute chips, theme toggle. |

In one line: **onepage vende, report explica, deck apresenta, social interrompe,
app opera, brand-kit prova; manual governa.** The manual sets the rules; the
brand-kit is the proof; the other formats apply them. The delivery is 2–3
formats chosen for the context, not every file.

## Copy that inherits the voice

Read `voice.md` before drafting. The rules that apply to every format:

- Use the manual's voice and the approved attributes; adapt angle and length to
  the format. Never paste the same paragraph into a landing, a deck and a report.
- One idea per section, slide or frame.
- Lead with the promise for `onepage`, the conclusion for `report`/`deck`, the
  interruption for `social`, the task for `app`.
- No invented fact. Numbers, dates, names, clients, awards, addresses, hours,
  prices and testimonials stay `[placeholder — what is needed]` until the user
  supplies them. Every unresolved placeholder appears in the delivery note
  (**Nota**).
- Keep the user's language. pt-BR is the default; code, flags and file names stay
  English.

## manual — the approval artifact

Generate after the route is approved, before any template. Default sections:
purpose and positioning; voice with **SOMOS / NÃO SOMOS** and **Certo / Errado**;
colors with roles, hex/RGB, feedback, charts, pairs and the optional gradient;
display and body type with the scale equation and line-heights; logo
construction, variants, breathing area and misuses; grid and spacing; icon
style; imagery treatment; components; composition rules; applications; signature.

- “NÃO SOMOS” is proposed from the route and attributes; the generator seeds it
  from a fixed attribute→antonym map and leaves unknown attributes as
  `[placeholder — oposto de …]`; edit after generation. The user confirms it at
  the gate.
- The gradient section exists only when the brand defines a gradient.
- The checker requires the misuse terms recolor/rotate/stretch/replace and a
  breathing-area comment.

The manual is the mandatory approval gate. Present its path and a short
checklist, ask for an explicit `ok`, and only then set `"aceite": true` in
`brand.json`. No script blocks the next phase, so you are the enforcement.

## brand-kit — the proof

Generated **by default** after the manual. It is a live, responsive, light/dark
page with Logo, Cores, Feedback, Gráficos, Tipografia, Ícones, Imagem,
Componentes and Aplicações. The applications are mini cases: landing, report,
deck, app and social, each rendered with the same components.

- It is the proof of the system and the menu of formats, not one of the 2–3
  formats proposed for delivery.
- If the user asks for a single artifact ("só o relatório", "sem kit"), skip the
  brand-kit and say so in the Nota.
- Keep it alive: no static screenshot, no invented metrics. Labels, tokens and
  components are the demonstration.

## onepage — vende

Default starter: hero, proof, how it works, testimonial, CTA.

1. **Hero** — outcome headline (`TITLE`), mechanism subhead (purpose), one
   primary action, at most one secondary.
2. **Proof** — three or four numbers, each with label, base and date; never
   invent a metric.
3. **How it works** — one mechanism per step or card, two lines of support.
4. **Testimonial** — only with a real quote, name, role and permission.
5. **CTA** — one action, one owner, one deadline.

Variations: editorial hero with a full-width image; product hero with a framed
screenshot; proof-led hero when the number is the argument. Copy formula:
headline = the result the customer wants; subhead = how; CTA = imperative verb.
Keep the hero under ~12 words.

Example (consultoria B2B): **“A decisão certa sobre IA começa com um diagnóstico
curto.”** · *Plano de [placeholder] semanas, com dono e prazo.* · **Agendar
diagnóstico** · Prova: [placeholder — número verificado, base e data].

## report — explica

Default starter: cover with subject + conclusion; executive summary with 3–4
indicators, each with **base and period**; data table with `<caption>` describing
the cut and `<th scope="col">`; trend chart with one highlighted series; findings
with an explicit evidence pointer; recommendations with owner and deadline.

Variations: memo (no cover), board pack (two-column summary), research note
(method section before findings). Copy formula: conclusion first, then evidence,
then action. Every number carries a comparison base. A number without a base is
decoration, not a report. The chart always has a table fallback.

Example: **Resumo:** no período [placeholder], o indicador foi [placeholder],
variação de [placeholder] sobre a base [placeholder]. **Recomendação:**
[placeholder] · dono [placeholder] · prazo [placeholder].

## deck — apresenta

Default starter: cover, divider, assertion slide, big number (with base), quote
(real and authorized), closing (next step with owner and deadline). This is a
default, **sem número fixo de slides**: add a slide when the argument needs one,
cut when it repeats. Split a slide that carries two ideas.

The present stage is 1280×720 with container queries; phones get scroll mode.
Keys: `←`/`→`, `PageUp`/`PageDown`, `Space`, `Home`, `End`, `t` for theme, `f`
for fullscreen. `#3` deep-links to slide 3. Slides that overflow 1280×720 are
flagged in the console.

Variations: pitch (problem/insight/proof/ask), class (one concept per slide),
readout (data first). Copy formula: an assertion as the title, at most two lines
of support, no paragraph. One idea per slide.

Example: Slide 1 **“O método importa mais que a ferramenta.”** Slide 4
**+[placeholder]%** no período [placeholder] · base [placeholder].

## social — interrompe

Three real-size mockups: 1080×1080 feed, 1080×1920 story and 1080×1350 image.
They are **mockups, not PNG/JPG export**; the user composes or captures them in
the destination app. Keep the logo legible, the headline short and the CTA in the
lower third (feed) or above the story UI safe zone.

Variations: single statement, carousel cover, quote card, date/event card. Copy
formula: one idea per frame; at most one CTA; no paragraph. A square post has one
headline and one support line; a story is a 1–3 screen sequence, one idea per
screen.

Example: **“A mostra fecha domingo.”** · [placeholder — horário] · [placeholder
— @perfil]. Story 1/3 **“Uma sala, seis décadas.”** Story 2/3 **“Entrada
[placeholder].”** Story 3/3 **“Últimos dias.”**

## app — opera

Default shell: topbar with mobile disclosure, sidebar on desktop, page header,
stats, table/list with filters, empty/loading/error states, a chart with a table
fallback, a native `<dialog>` modal and a form. Same tokens, more compact rhythm
for the context; **no product flavor** and no fake product name.

- A11y: landmarks, a skip link, keyboard access, visible focus, `<dialog>` for
  modal focus trapping, labels on every control.
- The layout is a starter: a settings page may drop stats and the chart; a
  dashboard may promote the trend. Keep the operational job and the states.
- `app` is exempt from the sprite/breathing-area checker rule; the generated page
  still injects the sprite, and its visible lockup is inline in the topbar.

## blank — the shell

Use `blank` for a cartaz, convite, menu, cheatsheet, certificate or any page that
is not one of the application formats. It carries the logo, `h1`, purpose,
attribute chips and theme toggle, with no invented sections. Build the rest with
semantic tokens, compose from the section catalog and run the checker.

## Cross-format checklist

- [ ] The format job is respected: vende / explica / apresenta / interrompe /
      opera / prova / governa.
- [ ] The skeleton was treated as a starting point, not a mold; sections were
      composed for this argument.
- [ ] Composition direction, measure and grid guided the layout.
- [ ] Copy is not duplicated across formats; the angle changes with the job.
- [ ] Every number has a base and date, or is `[placeholder]`.
- [ ] Every placeholder is listed in the delivery **Nota**.
- [ ] `check_page.py` reports zero ERROR on the file.
- [ ] 375px has no horizontal scroll; light/dark and keyboard were checked.
- [ ] Deck overflow and social safe zones were checked; social is described as a
      mockup, not an export.
