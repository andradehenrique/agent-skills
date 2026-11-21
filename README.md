# AI Agent Skills

A collection of domain-specific skills and instructions for AI coding assistants and autonomous agents.

## What is a Skill?

A skill is a markdown file with `name` and `description` YAML frontmatter that defines a specific workflow, set of rules, or domain knowledge for an AI agent. When an AI agent is equipped with skills, it can autonomously determine when to read and apply those instructions based on your natural language requests.

**Use cases for skills:**
- Enforcing project-specific formatting or architectural guidelines
- Defining step-by-step diagnostic or brainstorming workflows
- Standardizing complex tasks (e.g., rewriting resumes, code review protocols)

## Available Skills

| Skill Name | Description |
|------------|-------------|
| [career-profile-optimizer](./skills/career-profile-optimizer/SKILL.md) | Iteratively rewrites work experiences for LinkedIn and ATS/PDF, then generates optimized LinkedIn headline and about section for a target role/seniority. |
| [har-analyzer](./skills/har-analyzer/SKILL.md) | Audits .har (HTTP Archive) files to produce an executive report on performance, API failures, security, and third-party impact. |
| [github-engineering-report](./skills/github-engineering-report/SKILL.md) | Generates daily/weekly engineering panoramas from GitHub data with PR analysis, human vs. bot review detection, and optional Jira cross-reference. |
| [message-rewriter](./skills/message-rewriter/SKILL.md) | Turns a rough draft into a ready-to-paste Slack message or code review comment, picking the tone from the detected intent: Direct (BLUF, Conventional Comments), Collaborative (condensed NVC) or Full NVC for real conflict. |
| [brand-engine](./skills/brand-engine/SKILL.md) | Turns a vague brand idea, a loose color, a missing logo, or reference screenshots into a defensible identity: 2–3 route options, a mandatory HTML brand manual approval gate, then landing, deck, report, or social HTML with semantic tokens and light/dark. Iterative: the manual is approved before any template and revisions repeat the gate. Not for .pptx, PDF, Word or e-mail export, social image export, production React components, or a complete e-commerce build. |

## Per-Skill Details

To keep this repository scalable as more skills are added, the root README stays concise.

For each skill, use the skill folder as the source of truth:
- `SKILL.md`: trigger conditions, flow, and boundaries
- `docs/`: design documents and specifications
- `scripts/`: supporting Python/JavaScript utilities
- `evals/`: test cases and evaluation prompts

For `github-engineering-report`, see:
- [skills/github-engineering-report/SKILL.md](./skills/github-engineering-report/SKILL.md)
- [skills/github-engineering-report/docs/2026-06-11-design.md](./skills/github-engineering-report/docs/2026-06-11-design.md)

### message-rewriter

Paste your draft in your own words, with the channel if you know it, and get back one header line (intent, tone, channel) and the message in a code block, in the draft's language.

```
/message-rewriter comment on the PR: this query hits the DB 3 times, it's slow, should be a join
```

- **Tones:** Direct for most technical messages. Collaborative for disagreeing, saying no, following up or pointing out a mistake. Full NVC only for real conflict or behavior feedback.
- **Humanizer:** messages of 4 or more sentences go through the [`humanizer`](https://github.com/blader/humanizer) skill before final formatting, if it is installed. Short messages, or any message when the humanizer is missing, use a built-in checklist, and the skill never blocks. You can force either path ("use the humanizer" / "skip the humanizer").
- **Iterative:** ask for "shorter", "softer" or "more direct" and it adjusts the last version.
- **Never sends anything.** It only writes text.
- **When not to use:** long documents (PR descriptions, tickets, RFCs), plain translation, or legal/HR communication.

References: [techniques and intent map](./skills/message-rewriter/references/techniques.md), [examples (pt-BR)](./skills/message-rewriter/references/examples.md).

## Installation

You can install these skills directly into your local agent environment using the `npx skills add` command. 

### Install all skills from this repository
To install ALL skills available in this repository at once:

```bash
npx skills add andradehenrique/agent-skills
```

### Install a specific skill
If you prefer to install only a single specific skill:

```bash
npx skills add andradehenrique/agent-skills/skills/<skill-name>
```

## How to Create a New Skill

1. Create a new directory under `skills/` for your skill (e.g., `skills/my-new-skill/`).
2. Create a `SKILL.md` file inside that directory.
3. Add the required YAML frontmatter:

```markdown
---
name: my-new-skill
description: Use when the user asks for [trigger condition].
---

# Your Skill Instructions Here
...
```

4. Test the skill by invoking it with an AI agent.

For this repository quality baseline, follow the guide in [docs/skill-authoring-standard.md](./docs/skill-authoring-standard.md).

## Contributing

Contributions are welcome! If you have a proven prompt, workflow, or set of instructions that makes your AI agent more effective, feel free to open a Pull Request adding it to the `skills/` directory following the structure above.