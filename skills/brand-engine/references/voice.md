# Voice — an attribute-led tone framework, zero invented facts

Voice is what the brand sounds like everywhere; tone is the dial for the moment.
This framework is **brand-agnostic**: it starts from the approved attributes and
the optional `voice` block in `brand.json`, not from a fixed set of adjectives.
The same voice must survive landing, deck, report, social and app without the
same paragraph being pasted into all of them.

## Base: attributes become decisions

Read `attributes` and `voice` from `brand.json` (and the manual once approved):

```json
"attributes": ["claro", "humano", "preciso", "sem jargão"],
"voice": {
  "summary": "Explica antes de vender; mostra o método.",
  "principles": ["conclusão primeiro", "número com base", "zero jargão"],
  "avoid": ["hype", "promessa sem dono"],
  "person": "você",
  "emoji": "none"
}
```

Os tons são derivados dos atributos aprovados: each attribute must become a
visible choice, not a self-description.

| Attribute | Becomes | Does not become |
|---|---|---|
| claro | conclusion first, one idea per sentence, no jargon | the word “claro” in the copy |
| humano | a concrete noun and a verb, direct address | exclamation marks or cuteness |
| preciso | a number with base and period, a named source | the adjective “preciso” |
| contido | fewer words, more white space | coldness or distance |
| caloroso | welcome without ceremony, specific detail | hype or forced intimacy |
| provocador | one point of view, a mental image | aggression or clickbait |

If `voice` is absent, derive the summary from the attributes and record it in
the manual. Never import another brand's voice; the example lines below are
illustrations, not templates to paste.

## Four tones

### Tom 1 — Direto

**Direcionamento:** when the reader must act or decide. Default for CTAs,
recommendations and anything with a deadline.
**SOMOS:** claros, específicos, no imperative.
**NÃO SOMOS:** secos, monossilábicos, grosseiros.
**Certo:** “Agende o diagnóstico. Retorno em [placeholder — prazo].”
**Errado:** “Gostaríamos de convidá-lo a considerar a possibilidade de
eventualmente entrar em contato.”

### Tom 2 — Caloroso

**Direcionamento:** when the reader needs to feel welcome or reassured. Default
for a hero, an onboarding screen and a customer-facing explanation.
**SOMOS:** próximos, generosos, concretos.
**NÃO SOMOS:** efusivos, piegas, cheios de exclamações.
**Certo:** “Seu resultado chegou. Explicamos cada linha antes de você decidir.”
**Errado:** “Que notícia incrível!!! Você vai amar!!!”

### Tom 3 — Especialista

**Direcionamento:** when the reader needs to trust the method or the number.
Default for report, deck and the manual.
**SOMOS:** precisos, explicativos, honestos sobre limites.
**NÃO SOMOS:** arrogantes, cheios de jargão, donos da verdade.
**Certo:** “Amostra de [placeholder — n]; margem de erro de [placeholder —
pontos].”
**Errado:** “Metodologia proprietária e disruptiva, líder absoluta de mercado.”

### Tom 4 — Provocador

**Direcionamento:** when the job is to interrupt a feed and earn one second. Only
for social; never for report, manual, app or a support message.
**SOMOS:** curtos, com uma imagem mental, com ponto de vista.
**NÃO SOMOS:** agressivos, genéricos, caçadores de like.
**Certo:** “A mostra fecha domingo. O acervo, não.”
**Errado:** “ÚLTIMA CHANCE!!! 🔥🔥 Não perca essa promoção imperdível!!!”

## Examples across contexts

| Contexto | Atributo que lidera | Linha |
|---|---|---|
| Consultoria B2B | claro | “Diagnóstico em [placeholder] semanas. Sem jargão, com dono e prazo.” |
| App de saúde | cuidado | “Seu exame chegou. O próximo passo está explicado em uma frase.” |
| Museu | curiosidade | “Uma sala, seis décadas. A entrada é [placeholder].” |
| Perfumaria | contenção | “Uma nota por vez. Nada além do que você sente.” |
| Pizzaria | calor | “A massa começou ontem. O forno acende às [placeholder].” |
| ONG | urgência | “Faltam [placeholder] famílias. A doação leva um minuto.” |

Use the table to check range, not to copy lines. The same brand should sound
recognizable in all six contexts even when the tone changes.

## Person

- Default to **2ª pessoa (você)** when talking to the audience. Use **nós** for
  what the brand commits to. Avoid “a gente” unless the approved voice uses it.
- Imperative for actions: “Agende”, “Leia”, “Escolha”. No “o cliente deve...”
  when you are talking to the client.
- Keep the user's regional register. Do not switch to “tu” or formal “senhor”
  unless the user writes that way or the manual says so.
- Do not use a gendered generic (“os usuários”, “o colaborador”) when “as
  pessoas”, “a equipe” or the concrete role works.

## Emoji

- Manual, report, deck and app: **no emoji**.
- Social: at most one per post, and only when the user used emoji or explicitly
  approved it. `voice.emoji` is `none` or `social-only`.
- Never use an emoji as a logo, icon, bullet or replacement for a word. No
  decorative strings (“🚀✨💡”) and no emoji in a heading or table header.

## Inclusive language

- Write for the people in the persona without flattening them. Avoid gendered
  job titles and default-male examples.
- Avoid ableist idioms and violent metaphors (“cego”, “surdo”, “matar a
  demanda”).
- Respect the names and pronouns people use; never “correct” them in copy.
- Describe people by what they do, not by a stereotype of who they are.
- A joke at the expense of a group is not a tone; cut it.

## Foreign words

- Write in the user's language; pt-BR is the default. Estrangeirismos are a last
  resort, not a style choice.
- Keep brand names, product names and technical terms the audience already uses.
- Do not use decorative English for style (“premium experience”, “delivery” when
  “entrega” is clearer, “meeting” when “reunião” works).
- If a loanword is genuinely the clearest term, use it once and be consistent.
  Never mix “delivery” and “entrega” in the same page.

## Copy sem fatos — placeholder + Nota

No invented facts. This includes numbers, dates, years in business, addresses,
hours, prices, client names, awards, certifications, testimonials, comparisons
(“a melhor”, “número 1”) and causes.

1. If the fact is essential, ask once.
2. If it is still missing, write `[placeholder — what is needed]` in the copy.
3. List every placeholder in the delivery note (**Nota**) with what must be
   filled before publishing.

Bad: “Há 20 anos no mercado, a melhor clínica da cidade.”
Good: “Consulta em [placeholder — prazo]. [placeholder — especialidade e
convênios].”
Nota: “Preencher prazo, especialidade e convênios antes de publicar.”

Every number needs a base and period (“[placeholder] atendimentos em
[placeholder], contra [placeholder] no período anterior”). Pantone values are
approximations and must be labeled as such. If the user supplies a fact later,
update the copy and remove it from the Nota; never keep both versions.

## Channel → tone

The channel here is the format, not a Slack message or a press release.

| Canal / formato | Intenção | Tom | Estrutura |
|---|---|---|---|
| onepage hero e CTA | vender | Direto | promessa em uma frase; CTA imperativo; no máximo duas frases. |
| onepage prova e razões | tranquilizar | Caloroso | prova antes do benefício; duas linhas por razão. |
| report capa e resumo | explicar | Especialista | conclusão primeiro; cada número com base e período. |
| report recomendações | decidir | Direto | ação + dono + prazo. |
| deck capa e seção | apresentar | Especialista | título que afirma algo; no máximo três pontos. |
| deck número e citação | provar | Caloroso | número com base; citação real e autorizada. |
| social feed e story | interromper | Provocador | uma ideia por quadro; headline curta; um CTA. |
| app estados e formulário | operar | Direto | verbo de ação, erro que explica o próximo passo. |
| manual | governar | Caloroso/Especialista | normativo, com exemplo certo/errado. |
| brand-kit | provar | Especialista | rótulos curtos, sem copy de venda. |

When two tones seem possible, pick the lighter one that still does the job.
Escalate only when the content is a real conflict, a public correction or a
message that will be read defensively.

## Voice checklist

- [ ] The leading attribute was named before drafting.
- [ ] Tone chosen from the table and kept for the whole section.
- [ ] 2ª pessoa for the audience; “nós” only for brand commitments.
- [ ] No emoji outside social; at most one there, with approval.
- [ ] Inclusive language; no gendered generic or ableist idiom.
- [ ] No decorative foreign word; one term per concept.
- [ ] No invented fact; every gap is `[placeholder]` + listed in the Nota.
- [ ] The same text was not pasted from another format.
