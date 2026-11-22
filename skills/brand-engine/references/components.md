# Components — 21 patterns for composing pages

Copy, cut and recombine these patterns. They are a vocabulary, not a finished
library: the page's job decides which pattern earns its place. Tokens only —
every color, radius, shadow and spacing value comes from the generated
`theme.css` / `tailwind-theme.css`. Never write a hex, a palette utility or a
second dark variant: the tokens switch, so each pattern works in light and dark
without duplicated markup. Accessible names, roles and WCAG 2.2 AA are part of
the pattern, not an afterthought.

## Actions

**When:** every page; one primary action per view, at most one secondary.

```html
<a href="#contato"
   class="inline-flex h-6 items-center gap-1 rounded-md bg-primary px-3 text-sm font-semibold text-on-primary no-underline hover:bg-primary-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus">
  Falar com a gente
  <iconify-icon icon="fluent:arrow-right-24-regular" aria-hidden="true" class="text-base"></iconify-icon>
</a>
<button type="button"
        class="inline-flex h-6 items-center rounded-md border border-line-input bg-surface px-3 text-sm font-semibold text-fg hover:bg-surface-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus">
  Ver detalhes
</button>
```

**Rules:** `bg-primary` always pairs with `text-on-primary` and
`hover:bg-primary-hover`; never hand-pick a hover color. On an optional brand
band, text and links use `text-on-band` / `text-on-band-muted`. Controls use
`border-line-input`, not `border-line`. A link navigates; a `<button>` acts.
**A11y:** visible focus ring, 24×24px minimum target, action text states the
outcome. Icon-only actions need `aria-label`.

## Badges and chips

**When:** status, category, filter or an attribute list — not decoration.

```html
<span class="inline-flex items-center gap-1 rounded-full bg-success-soft px-2 py-1 text-xs font-medium text-on-success-soft">
  <iconify-icon icon="fluent:checkmark-circle-24-regular" aria-hidden="true"></iconify-icon>
  Ativo
</span>
<span class="inline-flex items-center rounded-full border border-line px-2 py-1 text-xs text-fg-muted">
  Categoria
</span>
```

**Rules:** the sentence carries the meaning; color is reinforcement. Use
`*-soft` with `on-*-soft` for feedback badges, `primary-soft` with
`on-primary-soft` for brand chips. **A11y:** never color-only; keep the text
label inside the badge. A removable chip is a `<button>` with an accessible
name (`aria-label="Remover Categoria"`).

## Cards

**When:** a set of comparable items, each with its own heading.

```html
<article class="rounded-lg border border-line bg-surface p-4">
  <h3 class="text-lg font-semibold">[placeholder — título do item]</h3>
  <p class="mt-2 text-sm text-fg-muted">[placeholder — duas linhas de sustentação.]</p>
</article>
```

**Rules:** a card is a group, not a click target by itself; if the whole card is
clickable, use one real link inside and make it cover the card without trapping
selection. Same heading level within a grid. Avoid shadow plus border plus
tinted fill at once. **A11y:** headings give the grid a navigable outline.

## KPI

**When:** a number is the argument; proof, summary or a dashboard stat.

```html
<dl class="grid grid-cols-2 gap-x-4 gap-y-6 md:grid-cols-4">
  <div class="border-t-2 border-primary pt-2">
    <dt class="text-sm text-fg-muted">[placeholder — indicador]</dt>
    <dd class="mt-1 text-3xl font-semibold tabular-nums">[00%]</dd>
    <p class="mt-1 text-xs text-fg-subtle">[placeholder — base e período]</p>
  </div>
</dl>
```

**Rules:** every number needs a label, a comparison base and a date; otherwise
it is decoration. Use `tabular-nums` so columns align. `dl`/`dt`/`dd` is the
semantic pairing. **A11y:** never put the unit in a `::before`; keep it in the
text so screen readers announce it.

## Callout

**When:** one piece of context that changes the decision — not a second
paragraph.

```html
<div role="note" class="flex items-start gap-2 rounded-lg bg-info-soft p-3">
  <iconify-icon icon="fluent:info-24-regular" aria-hidden="true" class="mt-1 text-base text-info"></iconify-icon>
  <p class="text-sm text-fg">[placeholder — o que muda a leitura do bloco.]</p>
</div>
```

**Rules:** feedback colors are for state; use `info` for context, `success` for
confirmation, `warning` for risk, `danger` for failure. Pair `*-soft` with
`text-on-*-soft` for the heading and `text-fg` for the body. **A11y:**
`role="note"` when the callout is supplementary; `role="alert"` only for a
live error.

## Table

**When:** comparison across rows and columns; a report, a list of records.

```html
<div class="be-scroll-x rounded-lg border border-line bg-surface">
  <table class="be-table min-w-[560px]">
    <caption>Indicadores por período — [placeholder — recorte e fonte].</caption>
    <thead>
      <tr><th scope="col">Indicador</th><th scope="col" class="text-right">Valor</th></tr>
    </thead>
    <tbody>
      <tr><td class="font-medium">[placeholder — item]</td><td class="text-right tabular-nums">[00]</td></tr>
    </tbody>
  </table>
</div>
```

**Rules:** `<caption>` states the cut; every column has `<th scope="col">`;
numbers are right-aligned and `tabular-nums`; no nested scrolling on mobile
without `.be-scroll-x`. **A11y:** real table markup, never a grid of divs;
`<th scope="row">` when the row label matters.

## Definition list

**When:** label/value pairs — metadata, specs, a summary of terms.

```html
<dl class="grid gap-3 sm:grid-cols-2">
  <div class="border-t border-line pt-2">
    <dt class="text-xs font-semibold uppercase tracking-widest text-fg-subtle">Prazo</dt>
    <dd class="mt-1 text-sm">[placeholder — valor]</dd>
  </div>
</dl>
```

**Rules:** one term per definition; keep the term short and the value concrete.
Use for facts, not for prose. **A11y:** `dl` groups each `dt` with its `dd`;
avoid using it as a visual grid when headings would be clearer.

## Tabs

**When:** sibling views of the same object; never for page navigation.

```html
<div role="tablist" aria-label="[placeholder — nome das seções]" class="flex gap-1 border-b border-line">
  <button type="button" role="tab" id="tab-a" aria-selected="true" aria-controls="panel-a"
          class="border-b-2 border-primary px-3 py-2 text-sm font-semibold text-fg">Resumo</button>
  <button type="button" role="tab" id="tab-b" aria-selected="false" aria-controls="panel-b" tabindex="-1"
          class="border-b-2 border-transparent px-3 py-2 text-sm text-fg-muted">Detalhes</button>
</div>
<section role="tabpanel" id="panel-a" aria-labelledby="tab-a" class="pt-3">…</section>
<section role="tabpanel" id="panel-b" aria-labelledby="tab-b" class="pt-3" hidden>…</section>
```

**Rules:** one selected tab; the inactive panel is hidden, not removed from the
DOM without warning. With no JavaScript, use anchor links to real sections
instead. **A11y:** `tablist`/`tab`/`tabpanel`, arrow-key navigation, `tabindex`
roving, and a visible focus ring.

## Progress

**When:** a known-duration task or a completion ratio.

```html
<label for="envio" class="text-sm font-medium">Envio</label>
<progress id="envio" max="100" value="64" class="h-2 w-full accent-primary">64%</progress>
<p class="mt-1 text-xs text-fg-subtle">64% — [placeholder — etapa atual].</p>
```

**Rules:** use native `<progress>`; when a custom bar is unavoidable, expose
`role="progressbar"` with `aria-valuemin`, `aria-valuemax` and `aria-valuenow`.
Never animate a bar that has no real progress source. **A11y:** the numeric
value is also text; color alone does not carry completion.

## CSS bars

**When:** a small ranked comparison where Chart.js would be overkill.

```html
<figure class="rounded-lg border border-line bg-surface p-4">
  <figcaption class="text-sm font-medium">[placeholder — unidade e recorte]</figcaption>
  <ul class="mt-3 space-y-2">
    <li class="grid grid-cols-[8rem_1fr_auto] items-center gap-2 text-sm">
      <span class="text-fg-muted">[placeholder — série A]</span>
      <span class="h-2 rounded-full bg-chart-1" style="width: 78%" aria-hidden="true"></span>
      <span class="tabular-nums">78%</span>
    </li>
  </ul>
</figure>
```

**Rules:** bars are data marks; use `bg-chart-*`, 3:1 against `surface`.
Highlight one series with `chart-1`; the rest use `chart-2`…`chart-8` or
`surface-muted`. Keep a direct label on every bar. **A11y:** the label and value
are text; the bar itself is `aria-hidden="true"`.

## Donut

**When:** a simple part-of-whole with two or three slices.

```html
<figure class="flex items-center gap-4">
  <svg viewBox="0 0 36 36" class="size-24 -rotate-90" aria-hidden="true">
    <circle cx="18" cy="18" r="15.9" fill="none" stroke="var(--b-surface-muted)" stroke-width="4"></circle>
    <circle cx="18" cy="18" r="15.9" fill="none" stroke="var(--b-chart-1)" stroke-width="4"
            stroke-dasharray="64 36" stroke-linecap="round"></circle>
  </svg>
  <figcaption class="text-sm"><strong class="tabular-nums">64%</strong> — [placeholder — categoria].</figcaption>
</figure>
```

**Rules:** SVG circles, not an inline `conic-gradient` (the checker rejects
ad-hoc gradients); brand color via `var(--b-chart-*)` or `stroke-chart-*`.
**A11y:** the percentage and category are text; the SVG is `aria-hidden` and the
same data appears in a table or definition list.

## Chart.js

**When:** a trend, area or scatter needs a real scale; a chart is the argument.

```html
<figure class="rounded-lg border border-line bg-surface p-4">
  <canvas id="tendencia" height="240" role="img"
          aria-label="[placeholder — série, unidade e período; os valores estão na tabela acima.]"></canvas>
  <figcaption class="mt-3 text-xs text-fg-subtle">[placeholder — fonte e período.]</figcaption>
</figure>
<script>
  BrandCharts.create("tendencia", {
    type: "line",
    data: { labels: ["[01]", "[02]"], datasets: [{ label: "[placeholder — série]", data: [0, 0], tension: 0.3 }] }
  });
</script>
```

**Rules:** load Chart.js only on pages with a chart; omit colors so
`BrandCharts` fills them from `--b-chart-1..8`, `--b-fg-subtle`, `--b-line` and
`--b-surface`, and let it rebuild on `data-theme`. One series is highlighted;
the rest are context. Use CSS bars or the SVG donut for simple shapes.
**A11y:** `role="img"` plus a meaningful `aria-label` on the canvas, and a table
fallback with the same values.

## Timeline

**When:** a sequence with dates or ordered milestones.

```html
<ol class="space-y-4 border-l border-line pl-4">
  <li>
    <time datetime="2026-01" class="text-xs font-semibold uppercase tracking-widest text-fg-subtle">Jan 2026</time>
    <h3 class="mt-1 text-base font-semibold">[placeholder — marco]</h3>
    <p class="mt-1 text-sm text-fg-muted">[placeholder — o que mudou.]</p>
  </li>
</ol>
```

**Rules:** order is meaning, so use `<ol>`; dates use `<time datetime>`; the
line is `border-line` (decorative). **A11y:** the list announces its length and
position; do not encode the date only in the dot or color.

## Empty state

**When:** a collection has no items, a search returns nothing, a feature is not
configured yet.

```html
<section data-state="empty" aria-labelledby="vazio"
         class="rounded-lg border border-dashed border-line-strong bg-surface p-6 text-center">
  <iconify-icon icon="fluent:document-24-regular" aria-hidden="true" class="text-2xl text-fg-subtle"></iconify-icon>
  <h3 id="vazio" class="mt-2 text-base font-semibold">Nada por aqui ainda</h3>
  <p class="mt-1 text-sm text-fg-muted">[placeholder — o que fazer quando a lista está vazia.]</p>
  <button type="button" class="mt-3 inline-flex h-6 items-center rounded-md bg-primary px-3 text-sm font-semibold text-on-primary hover:bg-primary-hover">Criar o primeiro</button>
</section>
```

**Rules:** say what is empty, why, and the next action; never leave a blank
panel. Distinguish empty from loading and from error. **A11y:** a heading names
the state; the action is reachable by keyboard.

## Skeleton

**When:** content is loading and the layout is already known.

```html
<div role="status" aria-live="polite" class="rounded-lg border border-line bg-surface p-4">
  <span class="sr-only">Carregando…</span>
  <div aria-hidden="true" class="space-y-2">
    <div class="size-6 animate-pulse rounded-full bg-surface-muted motion-reduce:animate-none"></div>
    <div class="h-2 w-24 animate-pulse rounded-full bg-surface-muted motion-reduce:animate-none"></div>
    <div class="h-2 w-full animate-pulse rounded-full bg-surface-muted motion-reduce:animate-none"></div>
  </div>
</div>
```

**Rules:** skeleton blocks mirror the final layout; use `surface-muted`, not a
brand color. Honor `prefers-reduced-motion` (`motion-reduce:animate-none`).
**A11y:** the visual blocks are `aria-hidden`; a `role="status"` wrapper carries
the loading text once, not once per block.

## Form

**When:** collecting or editing input; contact, filters, settings.

```html
<form class="space-y-3">
  <div>
    <label for="campo" class="block text-sm font-medium">[placeholder — rótulo]</label>
    <input id="campo" name="campo" type="text" aria-describedby="campo-ajuda"
           class="mt-1 h-6 w-full rounded-md border border-line-input bg-surface px-2 text-sm text-fg">
    <p id="campo-ajuda" class="mt-1 text-xs text-fg-subtle">[placeholder — formato esperado.]</p>
  </div>
  <p id="campo-erro" role="alert" class="text-sm text-danger">[placeholder — o que corrigir.]</p>
  <button type="submit" class="inline-flex h-6 items-center rounded-md bg-primary px-3 text-sm font-semibold text-on-primary hover:bg-primary-hover">Salvar</button>
</form>
```

**Rules:** every control has a visible `<label>`; help text is always visible
and linked with `aria-describedby`; errors use `text-danger` and explain the
fix. Boundaries use `border-line-input`. **A11y:** no placeholder as the only
label, no `outline: none`, error summary announced with `role="alert"`.

## Avatar

**When:** a person or team identity next to a name.

```html
<span class="inline-flex items-center gap-2">
  <img src="https://placehold.co/48x48/E8DFCE/1E1C17?text=AB" alt=""
       width="48" height="48" class="size-6 rounded-full border border-line object-cover">
  <span class="text-sm font-medium">[placeholder — nome]</span>
</span>
```

**Rules:** the name next to the avatar carries the identity, so the image is
decorative (`alt=""`); if the avatar is the only content, give it a meaningful
`alt`. Initials use `bg-primary text-on-primary`. **A11y:** never rely on the
photo to name a person.

## Quote

**When:** a real, authorized testimonial or a pull quote from the text.

```html
<figure class="rounded-xl border border-line bg-surface p-4 md:p-6">
  <blockquote class="text-xl leading-snug md:text-2xl">“[placeholder — citação real, com autorização de uso.]”</blockquote>
  <figcaption class="mt-3 text-sm text-fg-muted">[placeholder — nome · papel · empresa]</figcaption>
</figure>
```

**Rules:** no invented testimonial; a quote without a source is a placeholder.
Keep the quote short enough to read at a glance. **A11y:** `blockquote` plus
`figcaption` associates attribution; quotation marks are typographic, not the
only signal.

## Code

**When:** a command, token, config line or short snippet the reader will copy.

```html
<pre class="be-scroll-x rounded-lg border border-line bg-surface-muted p-3 text-xs"><code class="text-fg">python3 scripts/check_page.py pagina.html</code></pre>
```

**Rules:** inline code uses `<code class="text-link">`; blocks use `<pre><code>`
and scroll on mobile. No syntax-highlight palette: one text color, maybe
`text-fg-muted` for comments. **A11y:** code is text; do not put a copy button
without a name and a keyboard path.

## Frames

**When:** presenting a screenshot, a product shot or a phone mockup.

```html
<figure class="overflow-hidden rounded-xl border border-line bg-surface">
  <div aria-hidden="true" class="flex gap-1 border-b border-line bg-surface-muted px-3 py-2">
    <span class="size-2 rounded-full bg-line-strong"></span>
    <span class="size-2 rounded-full bg-line-strong"></span>
  </div>
  <img src="https://placehold.co/1200x800/FBF8F1/0F5A6B?text=produto"
       alt="[placeholder — o que a tela mostra]" width="1200" height="800"
       class="block h-auto w-full" loading="lazy">
  <figcaption class="border-t border-line p-3 text-xs text-fg-subtle">[placeholder — contexto da captura.]</figcaption>
</figure>
```

**Rules:** the chrome is decoration (`aria-hidden`); the image carries the
meaning. Use `placehold.co` with the brand's canvas/primary colors while the
real asset is missing. **A11y:** `alt` describes the intention, not “imagem”;
the frame adds no focusable controls.

## Icons

**When:** reinforcing a label, marking a state, or a familiar action.

```html
<iconify-icon icon="fluent:checkmark-circle-24-regular" aria-hidden="true" class="text-base text-success"></iconify-icon>
<button type="button" aria-label="Fechar" class="inline-flex size-6 items-center justify-center rounded-md text-fg-muted hover:bg-surface-muted hover:text-fg">
  <iconify-icon icon="fluent:dismiss-24-regular" aria-hidden="true" class="text-base"></iconify-icon>
</button>
<iconify-icon icon="fluent:warning-24-regular" role="img" aria-label="Atenção" class="text-base text-warning"></iconify-icon>
```

**Rules:** icons inherit `currentColor`, so `text-*` and dark work automatically.
The family comes from `design.icons.family`; the generator rewrites the Fluent
names listed in `assets/icons.json`, and raw Iconify names are allowed for
everything else. One family per page. **A11y:** decorative icons are
`aria-hidden="true"`; a meaningful icon needs `role="img"` plus `aria-label` and
should never be the only name of a control. Offline, icons do not render — keep
the text label.
