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
| [career-profile-optimizer](./skills/career-profile-optimizer/SKILL.md) | Guides the user in iteratively rewriting their work experiences, resume, and LinkedIn profile targeting specific roles and seniority metrics. |

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

## Contributing

Contributions are welcome! If you have a proven prompt, workflow, or set of instructions that makes your AI agent more effective, feel free to open a Pull Request adding it to the `skills/` directory following the structure above.