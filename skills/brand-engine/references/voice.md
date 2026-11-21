# Voice — four tones, one person, zero invented facts

Voice is what the brand sounds like everywhere; tone is the dial for the moment.
Read the approved attributes from `brand.json` and the manual, then choose one
tone per section. The same voice must survive landing, deck, report and social
without the same paragraph being pasted into all four.

## Voice foundation

- Start from the approved attributes (for Forno & Brasa: rústico, caloroso,
  direto, artesanal). Each attribute must show up as a choice, not an adjective.
- Prefer a concrete noun and a verb to three adjectives.
- One idea per sentence. If a sentence has two "e", split it.
- Short is not the same as cold: cut words, keep warmth.
- Read the manual's **SOMOS / NÃO SOMOS** and **Certo / Errado** before writing.
  Each tone below repeats that frame.

## Four tones

### Tom 1 — Direto

**Direcionamento:** when the reader must act or decide, say the thing first.
Default for CTAs, recommendations and anything with a deadline.
**SOMOS:** claros, específicos, no imperative.
**NÃO SOMOS:** secos, monossilábicos, grosseiros.
**Certo:** "Peça a pizza de hoje. O forno acende às [placeholder]."
**Errado:** "Gostaríamos de convidá-lo a considerar a possibilidade de
eventualmente fazer um pedido."

### Tom 2 — Caloroso

**Direcionamento:** when the reader needs to feel welcome or reassured. Default
for the hero, proof and customer-facing explanation at Forno & Brasa.
**SOMOS:** próximos, generosos, concretos.
**NÃO SOMOS:** efusivos, piegas, cheios de exclamações.
**Certo:** "A massa descansou desde ontem. Hoje ela encontra o fogo."
**Errado:** "Nossa massa é super premium e incrível!!!"

### Tom 3 — Especialista

**Direcionamento:** when the reader needs to trust the method or the number.
Default for report, deck and the manual.
**SOMOS:** precisos, explicativos, honestos sobre limites.
**NÃO SOMOS:** arrogantes, cheios de jargão, donos da verdade.
**Certo:** "Fermentação de [placeholder] horas; forno a [placeholder] °C."
**Errado:** "A melhor pizza artesanal do mercado, com tecnologia exclusiva."

### Tom 4 — Provocador

**Direcionamento:** when the job is to interrupt a feed and earn one second.
Only for social; never for report, manual or a support message.
**SOMOS:** curtos, com uma imagem mental, com ponto de vista.
**NÃO SOMOS:** agressivos, genéricos, caçadores de like.
**Certo:** "Hoje o forno manda."
**Errado:** "SEXTOU! 🍕🔥 Não perca essa promoção imperdível!!!"

## Person

- Default to **2ª pessoa (você)** when talking to the audience. Use **nós** for
  what the brand commits to. Avoid "a gente" unless the brand's approved voice
  uses it.
- Imperative for actions: "Peça", "Leia", "Escolha". No "o cliente deve..." when
  you are talking to the client.
- Keep the user's regional register. Do not switch to "tu" or formal "senhor"
  unless the user writes that way or the manual says so.
- Do not use a gendered generic ("os usuários", "o colaborador") when "as
  pessoas", "a equipe" or the concrete role works.

## Emoji

- Manual, report and deck: **no emoji**.
- Social: at most one per post, and only when the user used emoji or explicitly
  approved it. Never use an emoji as a logo, icon, bullet or replacement for a
  word.
- No decorative strings ("🚀✨💡") and no emoji in a heading or table header.

## Inclusive language

- Write for the people in the persona without flattening them. Avoid gendered
  job titles and default-male examples.
- Avoid ableist idioms and violent metaphors ("cego", "surdo", "aleijado",
  "matar a demanda").
- Respect the names and pronouns people use; never "correct" them in copy.
- Describe people by what they do, not by a stereotype of who they are.
- A joke at the expense of a group is not a tone; cut it.

## Foreign words

- Write in the user's language; pt-BR is the default. Estrangeirismos are a
  last resort, not a style choice.
- Keep brand names, product names and technical terms the audience already uses.
- Do not use decorative English for style ("premium experience", "delivery"
  when "entrega" is clearer, "meeting" when "reunião" works).
- If a loanword is genuinely the clearest term, use it once and be consistent.
  Never mix "delivery" and "entrega" in the same page.

## Copy sem fatos — placeholder + Nota

No invented facts. This includes numbers, dates, years in business, addresses,
hours, prices, client names, awards, certifications, testimonials, comparisons
("a melhor", "número 1") and causes.

1. If the fact is essential, ask once.
2. If it is still missing, write `[placeholder — what is needed]` in the copy.
3. List every placeholder in the delivery note (**Nota**) with what must be
   filled before publishing.

Bad: "Há 20 anos no bairro, a melhor pizza da cidade."
Good: "Massa de fermentação longa, assada na lenha. [placeholder — tempo de
forno, horário e bairro]."
Nota: "Preencher tempo de forno, horário e bairro antes de publicar."

Every number needs a base and period ("[placeholder] pedidos no fim de semana
de [placeholder], contra [placeholder] na semana anterior"). Pantone values are
approximations and must be labeled as such.
## Channel → tone

Adapted from `message-rewriter`'s channel/intent/tone/structure frame. The
channel here is the format, not Slack or a PR.

| Canal / formato | Intenção | Tom | Estrutura |
|---|---|---|---|
| onepage hero e CTA | vender | Direto | promessa em uma frase; CTA imperativo; no máximo duas frases. |
| onepage prova e razões | tranquilizar | Caloroso | prova antes do benefício; duas linhas por razão. |
| report capa e resumo | explicar | Especialista | conclusão primeiro; cada número com base e período. |
| report recomendações | decidir | Direto | ação + dono + prazo. |
| deck capa e seção | apresentar | Especialista | título que afirma algo; no máximo três pontos. |
| deck número e citação | provar | Caloroso | número com base; citação real e autorizada. |
| social feed e story | interromper | Provocador | uma ideia por quadro; headline curta; um CTA. |
| manual | governar | Caloroso/Especialista | normativo, com exemplo certo/errado. |
| e-mail ou Slack | fora de escopo | — | use a skill `message-rewriter`. |

When two tones seem possible, pick the lighter one that still does the job.
Escalate only when the content is a real conflict, a public correction or a
message that will be read defensively.

## Voice checklist

- [ ] Tone chosen from the table and kept for the whole section.
- [ ] 2ª pessoa for the audience; "nós" only for brand commitments.
- [ ] No emoji outside social; at most one there, with approval.
- [ ] Inclusive language; no gendered generic or ableist idiom.
- [ ] No decorative foreign word; one term per concept.
- [ ] No invented fact; every gap is `[placeholder]` + listed in the Nota.
- [ ] The same text was not pasted from another format.
