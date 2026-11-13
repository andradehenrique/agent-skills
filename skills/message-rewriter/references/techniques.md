# Techniques and intent map

## Contents

1. Core techniques
2. Intent → tone → structure map
3. Conventional Comments in detail
4. NVC: condensed vs full
5. Phrasing swaps that reduce friction

---

## 1. Core techniques

**BLUF (Bottom Line Up Front).** The conclusion or ask goes in the first sentence, followed by only the context needed to act. It comes from military writing and is common in technical and executive writing. It is the default for Slack.

**No Hello / complete async message** ([nohello.net](https://nohello.net)). The greeting, context and question go together, so the reader can answer without a second exchange.

**Conventional Comments** ([conventionalcomments.org](https://conventionalcomments.org)). The format is `<label> [decorations]: <subject>`, plus optional discussion. It makes the comment type explicit and says whether it blocks the merge. It is the default for PRs.

**Google's code review guide** ([eng-practices](https://google.github.io/eng-practices/review/reviewer/comments.html)). The relevant points:
- Comment on the code, never on the developer.
- Explain why, so the author learns and can push back on solid ground.
- Mark severity (`Nit:` for optional) so the author can prioritize.
- The reviewer points out the problem and does not need to write the whole fix.
- Praise what is good, with the reason, when it is genuine.

**NVC (Nonviolent Communication, Marshall Rosenberg).** Observation without judgment, then feeling, then need, then a concrete and negotiable request. It works for conflict but is too long for daily use, hence the condensed version below.

**SBI (Situation-Behavior-Impact, Center for Creative Leadership).** For feedback on behavior: a specific situation, the observable behavior, then the impact. It is shorter than NVC and fits feedback about something a person did, not about code.

---

## 2. Intent map

Signals are written as generic cues. Recognize their equivalents in any language.

| Intent | Signals in the draft | Default tone | Structure |
|---|---|---|---|
| Ask for help / question | "anyone knows", "how do I", "?" | Direct | Question, then what was already tried (one line), then context or link |
| Ask for review / approval | "take a look", "approve", PR link | Direct | Ask and link, then scope or size, then deadline if any |
| Status / heads-up | "deployed", "done", "will be late" | Direct | Current state, then impact, then next step |
| Report bug / incident | "broke", "error", "500", stack trace | Direct | What breaks and where, then impact (who, how much), then evidence, then ask |
| Technical suggestion (PR) | "I'd rather", "could" | Direct | `suggestion:` with what and why |
| Nit / style (PR) | naming, formatting, preference | Direct | `nitpick (non-blocking):` on one line |
| Blocking problem (PR) | bug, security, regression | Direct | `issue (blocking):` with what happens and how to reproduce, or why |
| Clarifying question (PR) | "didn't get it", "why" | Direct | `question:` with genuine curiosity |
| Praise | "looks good", "nice" | Direct | `praise:` with what specifically and why |
| Disagree with a decision | "I disagree", "this is wrong" | Collaborative | Acknowledge the goal, state the disagreement with a fact, offer an alternative, open the discussion |
| Say no / decline | "can't", "won't make it" | Collaborative | A clear no, a short reason, then what is possible instead |
| Follow up on a deadline | "any news?", "where is", "you said" | Collaborative | Reference to the agreement, why it matters now, then an ask with a date |
| Point out someone's mistake | "X shipped it wrong", "broke because of" | Collaborative | Fact without a culprit, impact, then ask or next step. Consider a DM. |
| Ask another team | "team X needs to", "we depend on" | Collaborative | Ask, why, deadline or impact, then an offer to help |
| Escalate to leadership | "need to raise", "it's stuck" | Collaborative | Problem and impact in one sentence, what was tried, then the decision or help needed |
| Feedback on behavior | "every time you", "you always" | Full NVC (or SBI) | Specific situation, behavior, impact or feeling, then request |
| Escalated conflict / frustration | irritation, irony, "!!!", "absurd" | Full NVC | Observation, feeling, need, request. Suggest a synchronous talk. |
| Reply to criticism received | defensive draft about feedback on own work | Collaborative | Thank them for the concrete point, agree or disagree with a fact, then next step |

If the draft is frustrated but the recipient is a public channel and the topic is technical, use Collaborative for the public message and suggest in the Note that the rest goes to a DM.

---

## 3. Conventional Comments

Format: `<label> [(decorations)]: <subject>`, optionally followed by one discussion line.

Labels:
- `praise:` highlights something good. Be specific.
- `nitpick:` a trivial preference. Always non-blocking.
- `suggestion:` proposes an improvement. Say what and why.
- `issue:` a concrete problem. Pair it with a `suggestion` if you have a fix.
- `todo:` a small, necessary change.
- `question:` a genuine question. It may become an issue depending on the answer.
- `thought:` an idea that came up. Non-blocking.
- `chore:` a process task before acceptance (run a migration, update the changelog).
- `note:` information for the reader. Always non-blocking.

Decorations: `(blocking)`, `(non-blocking)`, `(if-minor)` (resolve it if it is small). Use `blocking` only when the problem really prevents the merge.

Keep labels in English even when the rest of the comment is in another language. That is the recognized standard.

---

## 4. NVC: condensed vs full

**Condensed (Collaborative tone)** drops the feeling and keeps the rest:
> "Yesterday's deploy shipped without the migration (observation), and checkout was down for 20 min (impact). Can we add the migration to the release checklist? (request)"

**Full (Full NVC tone)** has all four steps, in natural language, without labels:
> "For the last three sprints, front-end tasks reached the board on Wednesday. I'm worried, because that leaves two days for dev and QA, and we need more slack to avoid pushing bugs to production. Would you be up for discussing in refinement whether we can bring that to Monday?"

Watch out for these:
- A feeling is about the speaker ("I'm worried", "I got frustrated"). It is never a judgment in disguise: "I felt disrespected" accuses the other person.
- An observation is what a camera would record. "You don't care about quality" is a judgment. "This PR came in without tests" is an observation.
- A request is concrete, doable and negotiable. "Be more careful" is not a request. "Can we run the tests before asking for review?" is one.

---

## 5. Phrasing swaps that reduce friction

| Avoid | Prefer |
|---|---|
| "Why did you do X?" | "What was the reason for X? I'm asking because Y." |
| "You forgot to..." | "... is missing" |
| "This is wrong." | "This returns `null` when the list is empty." |
| "Obviously / clearly / just" | (remove it) |
| "You should" | "What do you think about" / "I suggest" |
| "I already said this" | "Picking up what we agreed on [date/link]:" |
| "ASAP" / "urgent!!!" | "I need this by [time] because [reason]." |
| "Sorry to bother you, I know you're busy, but..." | (go straight to the ask) |
| "Can anyone help me?" | The full question, with context. |
