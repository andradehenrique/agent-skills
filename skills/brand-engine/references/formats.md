# Formats — six files, six jobs, one voice

`scripts/new_page.py` turns an approved `brand.json` into one self-contained HTML
file per format. Each format has a different job; reusing the same copy across
them is a defect.

```bash
python3 <skill>/scripts/new_page.py --brand brand.json --format <fmt> \
  --title "..." --out <name>.html [--theme light|dark|system|light-only|dark-only] [--force]
```

| Call | Contract |
|---|---|
| `new_page(fmt, brand, title, out, theme="light", force=False)` | -> `Path` of the written file; `brand` is a `brand.json` path. |
| `render_page(fmt, brand, title, theme="light")` | -> HTML string, no I/O. |
| `--out` | An `.html`/`.htm` file, or a directory where `<fmt>.html` is written. |
| `--force` | Required to replace an existing file; nothing is overwritten silently. |

`fmt` is exactly `manual`, `onepage`, `deck`, `report`, `social` or `blank`.
Every page embeds the pinned Tailwind CDN, the Google Fonts link, the generated
`theme.css` + `tailwind-theme.css`, the no-flash theme script, the logo sprite
as the first element inside `<body>`, and the theme toggle. Every page has one
`<main>`, one `<h1>`, semantic tokens only, and must pass `check_page.py` with
zero ERROR before delivery.

## Format map

| Format | Job | Primary structure |
|---|---|---|
| `manual` | Governs: the approval artifact and source of truth. | Purpose, voice, colors, pairs, gradient, type, logo, grid, image, signature. |
| `onepage` | **Sells**: one promise, one action. | Hero, proof, three reasons, testimonial, CTA. |
| `report` | **Explains**: conclusion first, evidence next. | Cover, summary, data table, findings, recommendations. |
| `deck` | **Presents**: one idea per slide. | Cover, divider, content, big number, quote, closing. |
| `social` | **Interrupts**: one idea per frame, made to stop a scroll. | 1080×1080 feed + 1080×1920 story HTML mockups. |
| `blank` | A shell for a custom page. | Logo, `h1`, purpose, attribute chips, theme toggle. |

In one line: **onepage sells, report explains, deck presents, social
interrupts**. The manual does none of those; it sets the rules the others obey.

## Copy that inherits the voice

Read `voice.md` before drafting. The rules that apply to every format:

- Use the manual's voice and the approved attributes; adapt the angle and length
  to the format. Never paste the same paragraph into a landing, a deck and a
  report.
- One idea per section, slide or frame.
- Lead with the conclusion for report/deck; lead with the promise for onepage;
  lead with the interruption for social.
- No invented fact. Numbers, dates, names, clients, awards, addresses, hours,
  prices and testimonials stay `[placeholder]` until the user supplies them.
  Every unresolved placeholder appears in the delivery note (**Nota**).
- Keep the user's language. pt-BR is the default; code and flags stay English.

## manual — the approval artifact

Generate after the route is approved, before any template:

```bash
python3 <skill>/scripts/new_page.py --brand brand.json --format manual \
  --title "Manual de Marca" --out marca-manual.html
```

Sections, in order: purpose and positioning; tone with **SOMOS / NÃO SOMOS**
and **Certo / Errado**; colors with HEX, RGB, approximate Pantone (always marked
as an approximation) and named pairs; the 50/50 gradient at 45°; display and
body type with the scale equation and line-heights; logo construction,
variants, breathing area and misuses; the 8px grid; photo and icon checklists;
signature rules. The checker requires the misuse terms
recolor/rotate/stretch/replace and a breathing-area comment.

The manual is the mandatory approval gate. Present its path and a short
checklist, ask for an explicit `ok`, and only then set `"aceite": true` in
`brand.json`. No script blocks the next phase, so you are the enforcement.

## onepage — sells

Structure and copy job:

1. **Hero** — outcome headline (`TITLE`), mechanism subhead (purpose), one
   primary action and at most one secondary action.
2. **Proof** — three or four numbers, each with label and basis; never invent a
   metric.
3. **Three reasons** — one mechanism per card, two lines of support each.
4. **Testimonial** — only with a real quote, name, role and permission.
5. **CTA** — one action, one owner, one deadline.

Copy formula: headline = the result the customer wants; subhead = how; CTA =
imperative verb. Keep the hero under ~12 words.

Forno & Brasa snippet:

> **Massa de fermentação longa, assada na lenha, na sua mesa.**
> Pedir a pizza de hoje · [placeholder — horário e canal de pedido]
> Prova: [placeholder — número verificado e base]; [placeholder — bairro e
> tempo de entrega].

Do not add "a melhor do bairro", years in business or awards without a source.

## report — explains

Structure: cover with subject + conclusion; executive summary with 3–4
indicators, each with **base and period**; data table with `<caption>` describing
the cut and `<th scope="col">` on every column; findings with an explicit
evidence pointer; recommendations with owner and deadline.

Copy formula: conclusion first, then the evidence, then the action. Every number
carries a comparison base. A number without a base is a decoration, not a
report.

Forno & Brasa snippet:

> **Resumo:** o fim de semana [placeholder — período] vendeu [placeholder —
> número] pizzas, [placeholder — variação] sobre a base [placeholder — base].
> **Recomendação:** [placeholder — ação] · dono [placeholder] · prazo
> [placeholder].

## deck — presents

Six slides by default: cover, divider, content (title + three points), big
number (with comparison base), quote (real and authorized), closing (next step
with owner and deadline). The present stage is 1280×720 with container queries;
phones get scroll mode. Keys: `←`/`→`, `PageUp`/`PageDown`, `Space`, `Home`,
`End`, `t` for theme, `f` for fullscreen. `#3` deep-links to slide 3. Slides
that overflow 1280×720 are flagged in the console.

Copy formula: an assertion as the title, at most two lines of support, no
paragraph. One idea per slide; if a slide needs a second idea, split it.

Forno & Brasa snippet:

> Slide 1: **O forno não é cenário. É o método.**
> Slide 4: **+[placeholder]%** de pedidos no fim de semana · base
> [placeholder — período e canal].

## social — interrupts

Two real-size HTML mockups: 1080×1080 feed and 1080×1920 story. They are
**reference mockups, not PNG/JPG export**; the user composes or captures them in
the destination app. Keep the logo legible, the headline short and the CTA in
the lower third (feed) or above the story UI safe zone.

Copy formula: one idea per frame; at most one CTA; no paragraph. A square post
has one headline and one support line. A story is a 1–3 screen sequence, one
idea per screen.

Forno & Brasa snippet:

> **Hoje tem forno a lenha.**
> [placeholder — sabor do dia] · [placeholder — horário] · [placeholder —
> @perfil]
> Story 1/3: **A massa começou ontem.** Story 2/3: **O forno acendeu às
> [placeholder].** Story 3/3: **Peça até [placeholder].**

## blank — the shell

Use `blank` when the user needs a page that is not one of the four marketing
formats. It carries the logo, `h1`, purpose, attribute chips and theme toggle,
with no invented sections. Build the rest with semantic tokens and run the
checker.

## Cross-format checklist

- [ ] One format job respected: sells / explains / presents / interrupts.
- [ ] Copy is not duplicated across formats; angle changes with the job.
- [ ] Every number has a source or is `[placeholder]`.
- [ ] Every placeholder is listed in the delivery **Nota**.
- [ ] `check_page.py` reports zero ERROR on the file.
- [ ] 375px has no horizontal scroll; light/dark and keyboard were checked.
- [ ] Social files are described as mockups, not image exports.
