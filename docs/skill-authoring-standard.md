# Skill Authoring Standard

This document defines the minimum quality bar for skills in this repository.

## Goal

Create skills that are:
- Discoverable by trigger
- Safe against fabricated details
- Predictable in execution flow
- Consistent with repository documentation

## Required Skill Structure

Each skill should include:
1. YAML frontmatter with `name` and `description`
2. Clear overview and scope
3. Hard gates for non-negotiable constraints
4. Step-by-step execution flow
5. Explicit output contract
6. Validation or consistency checks
7. Stop conditions and transition logic

## Frontmatter Rules

- `name`: lowercase with hyphens
- `description`: trigger-oriented and starts with "Use when..."
- Description should explain when to invoke, not summarize workflow internals

## Mandatory Reliability Rules

Every skill must define:

1. No fabrication policy
- Do not invent facts, metrics, dates, or user data
- Define fallback behavior when user information is incomplete

2. Missing data fallback
- Ask clarification questions first
- If data remains unavailable, define accepted non-numeric or estimate-labeled output behavior

3. Stop condition
- Define exact criteria to move from one phase to the next
- Define behavior when user does not respond

4. Approval loop
- Define if user approval is required per phase or per output

## Output Contract Checklist

Document outputs explicitly:
- What is generated
- Format and style expectations
- Length guidance when relevant
- Consistency requirements across outputs

## README Alignment Rules

For every skill added or updated:
1. README skill description must match the real outputs
2. README should mention iterative behavior if the skill is multi-step
3. README should state when not to use the skill

## Publication Checklist

Before publishing changes:

1. Trigger quality
- Description clearly indicates use cases and activation context

2. Flow clarity
- Phases and transitions are explicit

3. Anti-hallucination
- No-fabrication and fallback rules exist

4. Output quality
- Output contract and validation checks exist

5. Documentation sync
- README and skill content are consistent

## Suggested Template

Use this minimal structure for new skills:

- Frontmatter
- Overview
- Hard Gates
- Execution Flow
- Output Contract
- Validation Checklist
- Failure and Fallback Handling
- Boundaries (When not to use)
