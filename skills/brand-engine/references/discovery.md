# Discovery — from a vague idea to one defensible route

Use this file in Phase 1. Discovery is **text-first**: a sentence about the
business, who it serves and where it will live is enough to start. Images in the
working directory are optional extra input, never a requirement.

## Rules

- Ask **5–8** questions, only the ones the user has not already answered.
- One batch, short sentences, no jargon. The user can answer "não sei" and you
  propose a default with the assumption written down.
- Closed answers are better than essays: offer the options and let the user pick.
- Do not generate `brand.json`, `theme.css`, `logo.svg` or any HTML before the
  user confirms one route (Gate 1).
- Never invent a fact to fill a gap. Ask once; if it stays missing, write
  `[placeholder]` and keep going.

## The closed question list (7)

### P1 — Purpose in one sentence
What does the business do, for whom, and why does it matter? Answer in one
sentence. If the user gives three, ask which one is the promise.

### P2 — Persona
Who decides and who uses it? Ask for age range, context of use and what they
value. Two or three sentences is enough; a named segment is better than
"todo mundo".

### P3 — Visual territory
Pick up to two: rústico, minimal, editorial, técnico, lúdico, luxo, popular,
esportivo, natural, retrô. Ask what the brand is **not**, too.

### P4 — Archetype
Pick one: Criador, Herói, Sábio, Cuidador, Explorador, Rebelde, Mago, Bobo,
Amante, Governante, Cara comum, Inocente. If the user hesitates, show two
candidates with a one-line difference.

### P5 — Two visual references
Ask for two references (link, print in the working directory, or a brand they
admire) and, for each, what to copy and what to avoid. "Bonito" is not a
reference; ask for the concrete trait: color, type, density, photo, motion.

### P6 — Productive vs. expressive
On a 1–5 scale, where 1 is sober/technical and 5 is bold/performative? This sets
the type contrast, the amount of color and the copy energy.

### P7 — Where the brand will live first
Mark all that apply: landing (`onepage`), deck (`deck`), report (`report`),
social (`social`). This decides which formats Phase 4 proposes first.

## Optional images in the working directory

If the user dropped images into the working directory, read them as optional
input: `*.png`, `*.jpg`, `*.jpeg`, `*.webp`, `*.svg`, `*.pdf`. Look for palette,
type, density and photo treatment; do not copy a layout literally.

If an image is **corrupt or unreadable**, ignore that file, say so in **one
line**, and continue **text-only**. Never retry in a loop, never block the job
and never crash. A missing or broken image is not a reason to stop discovery.

## Route template

Propose **2–3 routes**. Every route has the same fields so the user can compare:

| Field | What it must contain |
|---|---|
| Name | Two or three words the user can say out loud. |
| Idea | One sentence: the visual and verbal bet. |
| Palette | 2–4 named colors and the roles they imply (action, surface, accent). |
| Type | Display + body direction, with a fallback in mind. |
| Why | At least two answers from P1–P7 that this route satisfies. |
| Formats | Which of `onepage`, `deck`, `report`, `social` fit first. |
| Risk | What could go wrong and how you would correct it. |

A route is not a mood board and not a final theme. It is a defensible choice the
user can approve or reject before any file is generated.

## Worked routes — Forno & Brasa

Answers used: P1 pizza de fermentação longa assada na lenha para a mesa de
bairro; P2 famílias e casais de 25–45; P3 rústico contemporâneo + natural;
P4 Criador; P5 barro/fogo + marca editorial; P6 registro 3/5 (caloroso, não
performático); P7 landing + social.

### Rota A — Mesa de Bairro
**Ideia:** pizza de bairro, mesa compartilhada, calor sem cerimônia.
**Paleta:** Brasa `#A6402F` (ação), Terracota `#C97B4A` (apoio quente), Creme
`#F4E9D8` (superfície), Oliva `#5F6B45` (contraste).
**Tipografia:** display serifada de personalidade (Fraunces) + corpo humanista
(Source Sans 3), com fallback Georgia/system-ui.
**Por que:** cumpre P1/P2 (mesa de bairro, família), P3 (rústico contemporâneo)
e P6 (caloroso sem exagero). É a rota de menor risco para um negócio local.
**Formatos:** `onepage` + `social`.
**Risco:** pode ficar genérica se a foto e a copy não mostrarem o forno real.

### Rota B — Forno Vivo
**Ideia:** o fogo é o espetáculo; a marca se comporta como o forno, não como a mesa.
**Paleta:** Brasa `#A6402F`, Creme `#F4E9D8`, carvão como neutro escuro.
**Tipografia:** display condensada de peso alto + corpo neutro; contraste grande
entre título e leitura.
**Por que:** atende P4 (Criador), P5 (fogo como referência) e o topo do P6
(expressivo). Funciona melhor quando o conteúdo é foto e vídeo.
**Formatos:** `social` + `deck`.
**Risco:** cansa em texto longo e pode soar agressiva para P2 (famílias).

### Rota C — Casa de Fermento
**Ideia:** o tempo e a massa são o produto; a marca é calma, precisa e editorial.
**Paleta:** Oliva `#5F6B45`, Creme `#F4E9D8`, Terracota `#C97B4A` como acento.
**Tipografia:** serifada de contraste + sans humanista; entrelinha generosa.
**Por que:** traduz P1 (fermentação longa), P3 (natural) e o lado artesanal de
P2. É a rota que melhor envelhece em relatório e manual.
**Formatos:** `onepage` + `report`.
**Risco:** pode parecer caro ou distante do bairro se o tom não for caloroso.

## Gate 1 — route confirmation

Present the routes and ask the user to pick one. **Prompt-only**: generate
nothing until the answer. If the user rejects all routes, ask **one**
discriminating question (usually P3 or P6) and propose a new set. If the user
does not answer, stop; do not guess a route.

## Discovery checklist

- [ ] 5–8 questions asked; answered ones skipped.
- [ ] Text-first path works with no images at all.
- [ ] Optional workdir images read; corrupt ones ignored with one line.
- [ ] 2–3 routes proposed, each with all template fields.
- [ ] One route explicitly approved before Phase 2.
