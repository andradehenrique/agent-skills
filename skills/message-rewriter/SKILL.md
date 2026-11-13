---
name: message-rewriter
description: Use when the user pastes a rough draft in their own words and wants it turned into a message to send to someone, such as a Slack message, DM, thread reply or code review comment. Also use when they ask to "improve", "rewrite", "make it more objective", "soften", "post on Slack", "comment on the PR" or "reply to someone", or when they seem about to message a teammate, even without naming the channel.
metadata:
  version: "1.2.1"
---

# Message Rewriter

**CRITICAL LANGUAGE RULE:** The rewritten message and every label in the output must be in the language of the user's draft. A Portuguese draft gets a Portuguese message. Never translate the draft into English. The only exception is the Conventional Comments labels (`suggestion:`, `issue:`...), which stay in English because that is the recognized standard.

## Overview

The user writes the way they think: fast and unfiltered. You hand back a message ready to paste. It is short, makes clear what the reader is expected to do, and has the tone the situation calls for.

One rule governs the rest: **always be objective, and add only as much care as the risk of friction requires.** Most technical messages need no Nonviolent Communication (NVC). A message that can hurt someone does.

## Hard Gates

<HARD-GATE>
**No fabrication.** Never invent facts, names, dates, numbers, links, deadlines or causes that are not in the draft or the conversation. If something essential is missing, put a `[placeholder]` in the message and point to it in the Note. Never guess.
</HARD-GATE>

<HARD-GATE>
**Preserve meaning.** The rewrite can change tone, order and length. It never changes what is being asked, whether something blocks, who it is addressed to, or the user's position. If the user disagrees, the message still disagrees.
</HARD-GATE>

<HARD-GATE>
**The humanizer is never a blocker.** If the `humanizer` skill is missing, fails or takes the wrong path, use the built-in checklist and deliver anyway. Never ask the user to install anything before answering.
</HARD-GATE>

<HARD-GATE>
**Nothing is sent.** This skill only writes text. Never post to Slack, GitHub or any other service, even if a tool for it is available, unless the user explicitly asks in a separate request.
</HARD-GATE>

## Execution Flow

### Phase 1: Read the request

Extract this from the draft and from anything else the user said:

- **Channel**: PR comment, Slack channel or thread, DM, reply to someone. If it is not stated, infer it from the content: a code line or function suggests a PR, and "everyone" or "team" suggests a channel. If it is still unclear, assume Slack.
- **Recipient**: peer, leadership, another team, a junior person, the person who made the mistake. This changes how much context and care the message needs.
- **Facts**: what is concrete, such as what happened, where, numbers and links.

**Move on when** the channel and intent can be inferred. Ask a question before writing only if no useful version can be produced at all. Otherwise write with placeholders. If the user does not answer a clarifying question, deliver the best version with placeholders.

### Phase 2: Pick the intent and tone

Choose **one** main intent and **one** of the three tones. The full intent map with signals and structures is in `references/techniques.md`. Read it when the case is not obvious.

| Tone | When | Structure |
|---|---|---|
| **Direct** (default, ~80% of cases) | Request, question, status, bug, technical suggestion, routine review. No emotional charge. | BLUF: the ask or conclusion goes in the first sentence, then minimal context. On PRs, use a Conventional Comments prefix. |
| **Collaborative** | Disagreeing with a decision, saying no, pointing out someone's mistake, following up on a deadline, asking outside the agreement, raising a problem with another team or with leadership. | Condensed NVC: observable fact, then impact, then a negotiable request. No feelings sentence. Focus on the code or process, not the person. |
| **Full NVC** | Real conflict, visible frustration in the draft, feedback on behavior, a situation that already escalated, a message that will be read defensively. | Observation, feeling, need, request, written as natural prose without labeling the steps. Still short: 3 to 6 sentences. |

These signals mean the tone should go up a level: words like "again", "always", "never", "I already said", "absurd", irony, blame aimed at someone ("you broke"), a string of exclamation marks, or a target that is a person's behavior rather than the code. When unsure between two tones, pick the lighter one that still does not sound accusatory.

### Phase 3: Draft

These rules apply to every tone:

- **Explicit ask.** The reader must know what to do, by when, and whether it blocks. If there is no ask because the message is informational, say so ("just for context", `note:`).
- **Blocking status is the user's call.** On a PR, use `(blocking)` only when the draft says it blocks or describes a crash, data loss, security hole or regression. If the draft does not settle it (e.g. "missing test"), pick the most likely label **and always add a Note** asking whether it should block the merge. This Note is mandatory: never leave the doubt only in your reasoning.
- **No "no hello".** Greeting, context and question go in the same message. Never end with "can I ask you something?".
- **Code, not person.** Write "this loop allocates on every iteration", not "you wrote a loop that allocates".
- **Real questions, not rhetorical ones.** "What do you think about a Map?" works. "Why didn't you use a Map?" reads as a reprimand.
- **One topic per message.** If the draft mixes two unrelated asks, split it into two messages and say so in the Note.
- **Keep the user's voice.** Keep the same language, formality and technical terms.
- **Cut what does not help the reader**: excessive apologies, qualifiers ("just", "quickly", "maybe perhaps"), generic opening praise, double thanks in advance.

On PRs, follow Conventional Comments (`label [decorations]: subject`, plus an optional discussion line). The labels are described in `references/techniques.md`.

### Phase 4: Humanizer pass

This pass runs after the draft and before the final formatting, so the formatting is not stripped out.

1. **Short message** (every message in the output has 3 sentences or fewer, not counting code blocks): skip the `humanizer` and apply `references/humanizer-fallback.md`. At this size the full skill costs much more context than it fixes. Do not mention the skip in the Note.
2. **Longer message** (any message with 4 or more sentences, usually Full NVC or an escalation), **if the `humanizer` skill is available** (it is in the harness skill list, or a `SKILL.md` exists in `~/.claude/skills/humanizer/`, `~/.agents/skills/humanizer/`, `.claude/skills/humanizer/` or `.agents/skills/humanizer/`): apply it to the draft. Invoke it through the skills tool, or read its `SKILL.md` and follow its rules. Ask it to keep the meaning, the chosen tone, every `[placeholder]` and any Conventional Comments prefix. When several messages are long, run them in a single humanizer pass.
3. **Longer message without the humanizer, or on any error**: apply `references/humanizer-fallback.md` and continue.

The user can override this. "Use the humanizer" forces step 2 on any length, and "skip the humanizer" forces the checklist.

### Phase 5: Format and check

- **Slack** uses mrkdwn: `*bold*`, `_italic_`, `` `code` ``, ``` block ```. Use a list only for 3 or more parallel items. Keep mentions as the user wrote them.
- **GitHub/GitLab** use regular Markdown. Use a ```` ```suggestion ```` block when the comment is a direct line replacement.
- **Length limits**: PR comment, 1 to 3 sentences (more only with a code block). Direct Slack message, up to ~4 lines. Collaborative, up to ~6. Full NVC, up to ~8.

Then run the validation checklist below. Fix anything that fails before answering.

## Output Contract

Reply in exactly this shape. **Translate the header labels and the tone name into the draft's language.** The English template below is only the structure:

```
**Intent:** <e.g. flag blocking bug> · **Tone:** <Direct | Collaborative | Full NVC> · **Channel:** <PR | Slack channel | Slack DM | ...>

<message ready to paste, inside a code block so formatting is preserved>
```

For a Portuguese draft, the header is:

```
**Intenção:** <ex.: apontar bug bloqueante> · **Tom:** <Direto | Colaborativo | CNV completa> · **Canal:** <PR | Slack canal | Slack DM | ...>
```

The optional lines follow the same rule: **Alternativa** and **Nota** in Portuguese, for example.

After the block, add at most two optional lines:

- **Alternative**, only when the tone is genuinely ambiguous: the version in the neighboring tone, also in a code block.
- **Note**: a placeholder the user must fill, a risk you noticed ("this calls the person out in public; consider a DM"), or, only for a long message, "humanizer not found, used the built-in checklist".

Do not explain the technique, list what changed or praise the draft. If the user wants to understand the choice, they will ask.

**Iteration:** no approval is needed before delivering. If the user asks for changes ("shorter", "softer", "more direct", "in English"), apply them to the last version, keep the same output contract, and do not start from the original draft again.

## Validation Checklist

Before answering, reread the message as the recipient would:

- [ ] Is it clear what to do, by when, and whether it blocks? If the draft didn't say whether it blocks, is there a Note asking?
- [ ] Is every fact in the draft or the conversation? Is everything else a `[placeholder]`?
- [ ] Is the user's position (agree, disagree, block, approve) unchanged?
- [ ] Does any sentence read as a personal attack, sarcasm or public blame?
- [ ] Can any sentence go without losing information? Cut it.
- [ ] Is it within the length limit for the channel and tone?
- [ ] Are the message, the header labels, the tone name and the Note all in the draft's language?

## Failure and Fallback Handling

| Situation | Behavior |
|---|---|
| Humanizer missing or failed on a long message | Use `references/humanizer-fallback.md` and add one line to the Note. |
| Short message (3 sentences or fewer) | Use `references/humanizer-fallback.md` without a Note. This is the expected path, not a failure. |
| Draft is ambiguous about blocking or recipient | Write the most likely version with a `[placeholder]` and flag it in the Note. The Note is mandatory, not optional. |
| Draft mixes unrelated topics | Deliver two messages, each with its own header line. |
| Draft contains offensive content or personal attacks | Rewrite around the underlying fact and request. Never keep the attack. Suggest a synchronous conversation in the Note. |
| No usable content (e.g. "write something to John") | Ask one question about what the message needs to say. |

## Boundaries (When Not to Use)

- Long documents: PR descriptions, Jira tickets, RFCs, emails with many sections. Use the dedicated skills.
- Translation only, with no change of tone or structure.
- Generating content from nothing, when there is no draft or clear intent from the user.
- Legal, HR or formal disciplinary communication. Those need human review by the responsible area.

## References

- `references/techniques.md`: techniques (BLUF, Conventional Comments, No Hello, NVC, SBI, Google's code review guide) and the intent map with signals and structures.
- `references/humanizer-fallback.md`: checklist for removing AI-sounding text when `humanizer` is not installed.
- `references/examples.md`: before and after pairs by intent and tone, in pt-BR. Use them to calibrate length and the amount of care.
