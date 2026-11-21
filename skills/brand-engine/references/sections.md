# Sections — a catalog for composing pages

A section is a job, not a block to fill. This catalog lists the jobs, the
structure that usually serves them, the classes and tokens that keep them on
brand, and the copy the section has to deliver. It is a catalog, not a renderer:
`sections.md` gives vocabulary and judgment; the agent composes the page and
`new_page.py` only emits a starter. Cut, merge and reorder freely.

Rules that apply to every section: one idea per section; tokens only; no bare
hex or palette utility; one `h1` on the page; headings in order; every number has
a base and a period; unresolved facts stay `[placeholder]` and appear in the
delivery note.

## Hero

**When:** first screen of a landing or a blank page. Variants: split (copy left,
image right), centered (one promise, no image), editorial (large headline and a
reading column), product (a framed screenshot is the argument).
**Structure:** eyebrow, `h1`, one-line subhead, one primary action and at most
one secondary; optional image or framed product shot. Keep the headline under
~12 words.
**Classes/tokens:** `py-8 md:py-12`, `max-w-3xl`, `text-3xl md:text-6xl`,
`text-fg-muted`, `bg-primary text-on-primary`, optional `bg-band text-on-band`.
**Copy job:** the result the reader wants; the mechanism in one line; the next
step as an imperative verb. No paragraph, no invented proof.

## Proof

**When:** right after the hero, when a number, a logo or a real quote can carry
more weight than another paragraph.
**Structure:** three or four metrics, each with label, value, base and date; or
a quote with name and role; or a compact logo row. One proof type per section.
**Classes/tokens:** `dl` grid with `border-t-2 border-primary`, `tabular-nums`,
`text-fg-muted`, `text-fg-subtle` for the base.
**Copy job:** evidence, not adjectives. “X, compared with Y, in period Z.” If the
number is not verified, it stays `[placeholder]`.

## Features

**When:** explaining how the offer works or what is included, after the promise
is clear.
**Structure:** two to six items, each with a heading and two lines of support;
use a grid (`md:grid-cols-3`) or alternating text/image rows. Not every item
needs an icon.
**Classes/tokens:** `article`, `rounded-lg border border-line bg-surface p-4`,
`text-lg font-semibold`, `text-sm text-fg-muted`, `gap-4`.
**Copy job:** one mechanism or benefit per item, with a concrete detail. Avoid a
list of abstract capabilities; say what changes for the reader.

## Pricing

**When:** the offer has a price or a set of plans the reader must compare.
**Structure:** two or three plans, one recommended, each with price, unit,
included items and one action; a comparison table when the list is long.
**Classes/tokens:** `bg-surface border border-line`, recommended plan with
`border-primary` or `bg-band text-on-band`, `text-3xl tabular-nums`,
`bg-primary text-on-primary`.
**Copy job:** the real price, what is included, what is not, and the billing
period. No invented discount, urgency or “most popular” without evidence.

## Menu

**When:** a restaurant, a service list or any catalog read as items and prices.
**Structure:** groups by category, each item with name, short description and
price; `dl` for pairs or a simple table for many items; optional dietary notes.
**Classes/tokens:** `dl`, `border-b border-line` between items, `text-fg-muted`
for the description, `tabular-nums` for the price.
**Copy job:** the item name, what it is in one line, the price and the unit.
Prices, allergens and availability are facts: `[placeholder]` until confirmed.

## Gallery

**When:** the work, the place or the product needs to be seen, not described.
**Structure:** a responsive grid of figures, one caption per image, optional
filter chips; 3–8 images is usually enough; one image may be the hero of the
group.
**Classes/tokens:** `grid gap-3 sm:grid-cols-2 md:grid-cols-3`,
`rounded-lg border border-line`, `object-cover`, `text-xs text-fg-subtle` for
captions.
**Copy job:** the caption says what the image is and why it matters. `alt`
describes the intention; placeholders are listed in the Nota.

## Timeline

**When:** a process, a history or a sequence where order is the message.
**Structure:** an ordered list, one entry per moment, with date, title and one
line; vertical line and dots; optional current step.
**Classes/tokens:** `ol`, `border-l border-line pl-4`, `<time datetime>`,
`text-xs font-semibold uppercase tracking-widest text-fg-subtle`, current step
with `border-primary` or `bg-primary-soft`.
**Copy job:** what happened, when, and what changed because of it. Dates are
facts; the sequence must be true, not decorative.

## FAQ

**When:** the reader has real objections or logistics questions that would
otherwise become support tickets.
**Structure:** four to eight question/answer pairs; native `<details>`/
`<summary>`, one open by default only if it is the main objection.
**Classes/tokens:** `border-b border-line`, `py-3`, `text-base font-semibold`,
`text-sm text-fg-muted`, `focus-visible:outline-focus`.
**Copy job:** answer the actual question in two or three sentences; do not hide
the price, the deadline or the limitation behind marketing language.

## Team

**When:** people are part of the offer, the trust or the story.
**Structure:** a grid of people with avatar, name, role and one line of
relevance; a founder note when it adds context.
**Classes/tokens:** `grid gap-4 sm:grid-cols-2 md:grid-cols-3`, avatar with
`rounded-full border border-line`, `text-sm text-fg-muted`, `bg-primary
text-on-primary` for initials.
**Copy job:** name, role and why this person matters here. No invented title,
credential, photo or bio.

## Logos

**When:** real clients, partners or press mentions substantiate the promise.
**Structure:** a compact row or grid of logos, monochrome, with a short label;
optional link to a case.
**Classes/tokens:** inline SVG in `currentColor` or images with proper `alt`,
`text-fg-muted`, `opacity` unchanged, `gap-6`, `flex flex-wrap items-center`.
**Copy job:** the name is the proof; the label says the relationship (“cliente
desde 2024”, “parceiro”). Never show a logo the brand cannot prove.

## CTA

**When:** the reader is convinced and needs one next step; usually the last
section of a landing.
**Structure:** one headline, one line of context, one action; optional owner
and deadline. `band` surface for contrast.
**Classes/tokens:** `bg-band text-on-band`, `text-on-band-muted`,
`bg-highlight text-on-highlight` or `bg-primary text-on-primary`,
`rounded-xl p-6 md:p-10`.
**Copy job:** the action, what happens next, who owns it and by when. One action
only; no second competing offer.

## Contact

**When:** the reader must reach a person, a place or a channel.
**Structure:** a short form (name, contact, message) or a definition list with
address, hours, phone, e-mail and map; a real response promise.
**Classes/tokens:** form controls with `border-line-input`, labels visible,
`text-danger` for errors, `text-link` for mail/phone links.
**Copy job:** the channel, the expected response time and any constraint
(hours, region, language). Every contact detail is a fact.

## Footer

**When:** every page; it closes the page and carries the legal and contact
minimum.
**Structure:** brand lockup, one line of positioning, contact, legal links and
copyright; optional secondary navigation. Keep it to two or three rows.
**Classes/tokens:** `border-t border-line`, `text-xs text-fg-subtle`,
`text-link`, `py-4`, `flex flex-wrap items-center justify-between`.
**Copy job:** who owns the site, how to reach them and the legal identifiers.
No invented company data, registration or address.

## App shell

**When:** an operational surface — topbar, sidebar, page header and a work area.
**Structure:** skip link, topbar with mobile disclosure, sidebar on desktop,
page header, content region; landmarks around each; native `<dialog>` for
modals.
**Classes/tokens:** `sticky top-0 border-b border-line bg-canvas`, sidebar
`border-r border-line bg-surface`, active item `bg-primary-soft
text-on-primary-soft`, page header `border-b border-line pb-4`.
**Copy job:** name the area and the task; navigation labels are short nouns;
breadcrumbs only when the hierarchy is real. No product flavor or fake product
name.

## Stats

**When:** a compact operational summary, usually above a list or a chart.
**Structure:** three or four KPIs in a row, each with label, value, base and
period; one metric may be highlighted, the rest are context.
**Classes/tokens:** `grid grid-cols-2 gap-3 md:grid-cols-4`,
`border-t-2 border-primary` for the highlighted metric, `text-3xl tabular-nums`,
`text-xs text-fg-subtle`.
**Copy job:** the current value, the comparison and the period. A stat without a
base is decoration; a stat without a source is a placeholder.

## Table and list

**When:** records, comparisons or any set where rows share columns.
**Structure:** table with `caption`, `th scope`, numeric alignment and a scroll
wrapper; a list when there are only two fields per item.
**Classes/tokens:** `be-scroll-x`, `be-table min-w-[560px]`, `border-line`,
`tabular-nums`, `hover:bg-surface-muted`; list rows with `border-b border-line`.
**Copy job:** the caption states the cut and the source; columns are short
labels; every row has a stable identifier. Empty and error states belong to the
same surface.

## Filters

**When:** the reader must narrow a list by search, status, date or category.
**Structure:** a `role="search"` form with labeled controls, a submit and a
clear action; show the active filters and the result count.
**Classes/tokens:** `flex flex-wrap items-end gap-2`, controls with
`border-line-input bg-surface`, `h-6`, `text-sm`, active filter chips with
`bg-primary-soft text-on-primary-soft`.
**Copy job:** each label says what it filters, not just “Filtro”; the empty
result explains how to widen the search.

## States

**When:** a list, panel or page can be empty, loading or failed.
**Structure:** one surface per state: empty (what and next action), loading
(skeleton mirroring the layout), error (what failed, what to do, retry). Keep
the same region and heading.
**Classes/tokens:** empty `border-dashed border-line-strong bg-surface`;
loading `role="status" aria-live="polite"` with `bg-surface-muted`; error
`role="alert"` with `bg-danger-soft` and `text-on-danger-soft`.
**Copy job:** empty says why and what to do; loading says what is loading;
error says what failed and how to recover without losing valid data.

## Modal

**When:** a focused decision or a short form that must interrupt the page.
**Structure:** native `<dialog>` with a title, one short explanation, the form
or decision, and a close action; do not nest dialogs.
**Classes/tokens:** `m-auto w-11/12 max-w-md rounded-xl border border-line
bg-surface p-4 shadow-3`, backdrop `backdrop:bg-fg/50`,
`aria-labelledby` pointing at the title.
**Copy job:** the decision in the title, the consequence in one line, the
actions in verb order. Destructive actions name what is lost.

## Form

**When:** creating, editing or requesting something; contact, settings, intake.
**Structure:** one column, grouped fields, visible labels, help text and an
error summary; primary and secondary actions at the end.
**Classes/tokens:** `space-y-3`, `border-line-input bg-surface`, `h-6`,
`text-danger` for errors, `bg-primary text-on-primary`, `bg-surface` secondary.
**Copy job:** the label names the field; the help says the expected format; the
error says how to fix it; the submit says what happens next. Never invent a
required field or a promise of response.
