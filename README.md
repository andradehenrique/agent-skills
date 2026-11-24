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
| [brand-engine](./skills/brand-engine/SKILL.md) | Turns a vague brand idea, a loose color, a missing logo, or reference screenshots into a flexible identity: 2–3 routes with one recommended, a mandatory HTML brand manual approval gate, then a brand-kit and 2–3 formats (landing, deck, report, social, app, blank) built with Tailwind v4, Iconify, Chart.js and placehold.co placeholders, all on semantic tokens with light/dark. The skeleton is a starting point, not a mold. Not for .pptx, PDF, Word or e-mail export, social image export, production React/Vue components, or a complete e-commerce build. |
| [disk-cleanup](./skills/disk-cleanup/SKILL.md) | Scans the machine (Docker, Xcode and simulators, dev caches, node_modules, forgotten worktrees, ~/Library, Claude Code/Cursor/opencode sessions), prints a numbered list with size and risk per item, and removes only what you confirm — item by item, through a script that re-checks every path before touching it. macOS first, with the structure ready for Linux and Windows. |

## Skill Folder Structure

To keep this repository scalable as more skills are added, the root README stays concise. For each skill, the skill folder is the source of truth:
- `SKILL.md`: trigger conditions, flow, and boundaries
- `references/`: long-form material the skill loads on demand
- `docs/`: design documents and specifications
- `scripts/`: supporting Python/JavaScript utilities
- `evals/`: test cases and evaluation prompts

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