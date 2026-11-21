# Design principles — how a brand behaves on a page

The system gives you tokens and components; these principles decide what
deserves to be on the page. They hold for every format and every brand, from a
pizzeria to a museum. When two rules collide, protect the message and the
reader, in that order.

## Message before layout

Write the one sentence the page must land before choosing a grid. A headline is
an argument, not a label; the subhead explains the mechanism; the action names
the next step. If the copy does not survive being read aloud, layout will not
save it. One page, one promise; one section, one idea.

## Space

Space is hierarchy. Start with generous padding (`p-4`/`p-6`, `py-8 md:py-12`
between sections) and remove only where density is the job. The spacing unit is
fixed by the brand (`4` or `8`), so every step is a multiple of `--b-unit`;
never use arbitrary pixels. On mobile, vertical rhythm matters more than
horizontal decoration. Empty space is not wasted space.

## Surfaces

`canvas` is the page; `surface` is a card or panel; `surface-muted` separates a
section without a border; `surface-raised` is an overlay; `band` is the optional
dark brand band. Pick one surface logic per page and keep it. A card that adds a
border, a shadow and a tint is doing three jobs at once. `line` is decorative;
`line-input` is a control boundary and must clear 3:1.

## Hierarchy

One `h1`; headings descend in order; size, weight and position do the work
before color. Use the display face for the one big statement and the body face
for reading; `text-base` or larger is the reading size. A page where everything
is bold has no hierarchy. The most important element gets the most space, not
the loudest color.

## Mobile-first

Design at 375px first: one column, no horizontal scroll, tap targets at least
24×24px, text that reflows rather than shrinks. Add columns at `sm`/`md`/`lg`
when the content earns them. Test the theme switch, the keyboard path and the
narrowest viewport before calling a page done. A desktop-only composition is
not finished.

## Data

A number without a base and a date is decoration. Pair every metric with what
it is compared against, the period and the source. Charts get one highlighted
series, direct labels and a table fallback with the same values; `chart-1` is
the highlight, the other chart tokens are context. Use 3:1 data marks, never
chart colors for body text. Never invent a data point.

## Accessibility

Target WCAG 2.2 AA in both themes: 4.5:1 for body text, 3:1 for large text,
controls and focus. Use landmarks (`header`, `nav`, `main`, `footer`), a skip
link on long pages, one logical heading order, visible focus and real `<button>`
/ `<a>` elements. Every control and image has an accessible name; form errors
say what to fix. Run `check_page.py` and, when a browser exists,
`axe_copy.py`; fix every ERROR.

## Dark mode

Dark is a mode, not a second design. Never duplicate content or write a
`dark:` color when a semantic token already switches; use `bg-surface` and
`text-fg`, and test both themes at 375px and desktop. Placeholders need a dark
variant (`data-placehold-dark`) when the brand has both modes. If the brand is
light-only, do not fake a dark block; if it is dark-only, the root is dark and
there is no switch to a light theme.

## What to avoid

No palette utilities (`bg-blue-600`), bare hex, arbitrary colors, ad-hoc
gradients or `text-primary` as body copy. No feedback color as decoration, no
icon-only control without a name, no invented fact, client, metric or
testimonial. No hero paragraph, no centered long text, no more than two actions
in a hero, no card grid as the default answer to every section. No duplicated
dark markup, no gradient unless the brand defines one.

## Composition directions

`design.composition.direction` guides section order, grid, measure and rhythm.
It does not select a different skeleton file. Pick one direction per page and
let it be visible.

### Editorial

A large headline, a narrow reading column (`max-w-2xl`/`max-w-3xl`), images with
air, asymmetric blocks. Best for explanation, reports, museums and brands with a
human voice. Rhythm: slow, generous, text-led.

### Structured

An explicit grid, aligned blocks, medium density, visible labels. Best for B2B,
dashboards, pricing and comparisons. Rhythm: regular, scannable, evidence-led.
Do not let the grid flatten every section into the same card row.

### Poster

Large type, high contrast, few elements, one idea per view. Best for launches,
events, social and manifestos. Rhythm: abrupt and deliberate; the whitespace is
part of the composition.

### Minimal

Space, hierarchy by weight and position, one accent. Best for premium, cultural
and product surfaces. Rhythm: quiet and precise; minimal is not empty, every
remaining element is intentional.

## Color

Use the roles, not a mood board: neutral surfaces carry most of the page, the
brand `primary` marks action, `accent` marks a highlight, `support` adds a
second note. One accent per screen. Aim for roughly 70% neutral / 20% brand /
10% accent and adjust by context, not by formula. Feedback appears only when
state changes. Charts use one highlighted series. Never fix contrast with
opacity or a filter; choose the token that already guarantees it.

## Icons

One family, one style, one stroke weight. Size follows the text (`text-base`,
`text-lg`) or the configured icon size; icons inherit `currentColor`, so they
switch with the theme. Icons support labels; they rarely replace them. Use the
semantic names from `assets/icons.json` when the meaning exists, and the brand's
family from `design.icons.family` for everything else.

## Images

Images must do a job: show the product, the place, the person or the evidence.
Choose a treatment (photo, illustration, abstract or none) and keep it. While
the real asset is missing, use `placehold.co` with the brand colors and an `alt`
that describes the intention; list every placeholder in the delivery note. No
Unsplash and no unDraw: a random stock photo or generic illustration undermines
the brand more than an honest placeholder.

## Density

Density follows the context: a landing page breathes, a report is medium, an app
is compact. Change padding and type scale between contexts, not the tokens.
Compact does not mean cramped: keep 24px targets, visible focus and readable
line length. The same components can carry all three densities.

## Starting point, not a mold

The skeleton is a starting point, not a mold. Keep, cut, merge or add sections
until the argument is right; a page that only fills the default slots tends to
look like every other page. Use `sections.md` for the catalog and
`components.md` for the markup, then compose for this brand, this audience and
this idea.
