# Discovery — from a vague idea to one defensible route

Use this file in Phase 1. Discovery is **text-first**: a sentence about the
business, who it serves and where it will live is enough to start. Images in the
working directory are optional input, never a requirement.

## UX rule — proponha, não interrogue

The job of discovery is not to collect decisions; it is to return a system the
user can react to.

- Ask **5–8** short questions, only the ones the user has not already answered.
- Propose the visual system from the answers: palette with roles, type, shape,
  density, theme, icons, imagery and composition. The user accepts, swaps the
  route or adjusts one point.
- **Granularidade sob demanda:** the default flow does not ask about radius,
  spacing or scale. If the user asks to control it ("quero ajustar o radius"),
  open the control and record the choice in `brand.json`.
- The route already carries the proposed system. Keep one short summary (palette,
  type, shape, composition) next to it; there is no third gate. The manual gate
  remains the only mandatory gate.
- `brand.json` is the state. "Ajusta X" updates the manual and the brand-kit,
  restyles the delivered formats in place (theme blocks only, copy preserved),
  then revalidates, without restarting discovery. Full regeneration with
  `--force` only happens when the user explicitly asks for it.
- Never invent a fact to fill a gap. Ask once; if it stays missing, write
  `[placeholder]` and keep going.

Do not generate `brand.json`, `theme.css`, `logo.svg` or any HTML before the
user confirms one route (Gate 1).

## The closed question list (7)

### P1 — Purpose in one sentence
What does the business do, for whom, and why does it matter? If the user gives
three sentences, ask which one is the promise.

### P2 — Persona
Who decides and who uses it? Ask for context of use and what they value. A named
segment is better than "todo mundo"; two or three sentences are enough.

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
type contrast, color proportion and copy energy.

### P7 — Where the brand will live first
Mark all that apply: landing (`onepage`), deck (`deck`), report (`report`), social
(`social`), internal app (`app`). This decides which 2–3 formats Phase 4
proposes. `manual` and `brand-kit` are always the system artifacts, not one of
those choices.

## Optional images in the working directory

If the user dropped images into the working directory, read them as optional
input: `*.png`, `*.jpg`, `*.jpeg`, `*.webp`, `*.svg`, `*.pdf`. Look for palette,
type, density, imagery treatment and composition; do not copy a layout literally.

If an image is **corrupt or unreadable**, ignore that file, say so in **one
line**, and continue **text-only**. Never retry in a loop, never block the job
and never crash. A missing or broken image is not a reason to stop discovery.

## Route template

Propose **2–3 routes**. Mark exactly one as **recomendada** and say why in one
line. Every route uses the same fields so the user can compare:

| Field | What it must contain |
|---|---|
| **Ideia** | One sentence: the visual and verbal bet. |
| **Paleta** | Named colors with their roles: `canvas`, `surface`, `ink`, `primary`, optional `accent` and `support[]`. |
| **Tipografia** | Display + body direction, weights and fallback. |
| **Forma** | Radius profile (`sharp`/`soft`/`round` or custom), unit `4`/`8`, shadows. |
| **Composição** | Direction (`editorial`/`structured`/`poster`/`minimal`), measure and grid. |
| **Ícones** | Family (`fluent`/`lucide`/`phosphor`/`tabler`) and size. |
| **Imagem** | Mode (`photo`/`illustration`/`abstract`/`none`) and treatment. |
| **Por que** | At least two answers from P1–P7 that this route satisfies. |
| **Formatos** | The 2–3 formats that fit first; `brand-kit` is the proof, not a format choice. |
| **Risco** | What could go wrong and how you would correct it. |

A route is not a mood board and not a final theme. It is a defensible choice the
user can approve or reject before any file is generated.

## Worked routes — Omnia Labs

Answers used: P1 traduzir IA em operação real para PMEs que precisam decidir
agora; P2 donos e diretores de PMEs; P3 editorial humanista + técnico; P4 Sábio;
P5 jornal impresso + software de dados; P6 registro 2/5 (claro, não performático);
P7 landing + report.

### Rota A — Método Aberto (recomendada)
**Ideia:** papel e tinta para explicar um método técnico sem hype.
**Paleta:** Papel `#FBF8F1` (canvas), Giz `#FFFFFF` (surface), Tinta `#1E1C17` (ink), Petróleo `#0F5A6B` (primary), Areia `#E8DFCE` (accent), Oliva `#7C8363` (support).
**Tipografia:** Newsreader 600 + Source Sans 3 400; escala 16/1.25, fallback Georgia/system-ui.
**Forma:** radius `soft` (4/8/12/16/24), unit `8`, shadows `soft`.
**Composição:** `editorial`, medida `65ch`, grid `12`.
**Ícones:** Fluent, 16px.
**Imagem:** `abstract` com papel e grão leve; placeholder da marca enquanto não houver foto real.
**Por que:** cumpre P1/P4 (Sábio que explica), P3 (editorial humanista) e P6 (claro, não performático). É a rota de menor risco para uma consultoria.
**Formatos:** `onepage` + `report`.
**Risco:** pode ficar sóbria demais no social; corrigir com um pôster de uma ideia e tipo maior, sem mudar o sistema.

### Rota B — Sinal Técnico
**Ideia:** a marca se comporta como um painel de sinais: contraste alto, dados primeiro.
**Paleta:** Grafite `#15181C` (canvas), Carvão `#20252B` (surface), Gelo `#F2F5F7` (ink), Ciano `#1B7F8C` (primary), Âmbar `#D99A2B` (accent).
**Tipografia:** display sans condensada 700 + corpo mono 400; escala 16/1.2.
**Forma:** radius `sharp` (0/0/2/4/4), unit `4`, shadows `none`.
**Composição:** `structured`, medida `60ch`, grid `16`.
**Ícones:** Lucide, 16px.
**Imagem:** `abstract` com grid e ruído; placeholder da marca.
**Por que:** atende P1 (operação e decisão), P4 (mago/analista) e o topo de P6; funciona quando o conteúdo é número e tabela.
**Formatos:** `report` + `app`.
**Risco:** cansa em leitura longa e pode soar fria para P2; corrigir com medida menor e mais espaço.

### Rota C — Caderno de Campo
**Ideia:** a marca é um caderno de anotações: próximo, datado, com margem para comentário.
**Paleta:** Papel `#F7F3E8` (canvas), Branco `#FFFFFF` (surface), Tinta `#232019` (ink), Musgo `#4F6248` (primary), Ocre `#C58B3C` (accent), Azul `#3D5A80` (support).
**Tipografia:** display serifada 500 + corpo humanista 400; escala 16/1.3.
**Forma:** radius `round` (8/12/16/24/9999), unit `8`, shadows `soft`.
**Composição:** `minimal`, medida `70ch`, grid `12`.
**Ícones:** Phosphor, 20px.
**Imagem:** `illustration` com traço manual; placeholder da marca.
**Por que:** traduz P2 (dono de PME que anota), P3 (humanista) e P5 (caderno); envelhece bem em manual e relatório.
**Formatos:** `onepage` + `social`.
**Risco:** pode parecer informal demais para um contrato B2B; corrigir com tipografia mais contida e menos cor.

## Gate 1 — route confirmation

Present the routes and ask the user to pick one. **Prompt-only**: generate
nothing until the answer. If the user rejects all routes, ask **one**
discriminating question (usually P3 or P6) and propose a new set. If the user
does not answer, stop; do not guess a route.

## Discovery checklist

- [ ] 5–8 questions asked; answered ones skipped.
- [ ] Text-first path works with no images at all.
- [ ] Optional working-directory images read; a corrupt one is ignored with one
      line and never crashes.
- [ ] 2–3 routes proposed, one marked `recomendada`, each with every template
      field.
- [ ] Proposed system summarized (palette roles, type, shape, composition);
      fine-grained controls only on demand.
- [ ] One route explicitly approved before Phase 2.
