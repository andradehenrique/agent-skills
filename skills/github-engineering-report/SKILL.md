---
name: github-engineering-report
description: Use when the user wants a daily or weekly engineering panorama, repository overview, or PR timeline analysis from GitHub, optionally cross-referenced with Jira tickets. Triggered by prompts about engineering summaries, repository activity, PR timelines, or what happened on a specific day/week.
---

# GitHub Engineering Report

## Overview

Generate self-contained HTML reports from GitHub activity (commits, PRs, issues, reviews, actions, releases) with optional Jira cross-reference. Detects blockers, anomalies, human vs. bot reviews, and produces actionable insights.

## Required Tools

- **GitHub MCP** with `repo` scope
- **Jira MCP** (optional, for ticket cross-reference)

## When to Use

- User asks for "panorama da engenharia", "resumo do dia", "o que aconteceu ontem"
- User mentions a specific repo: "resumo do repo X"
- User asks about a PR: "timeline do PR #234", "análise do PR X"
- User wants "drill-down" de engenharia, atividades do time, destaques do dia

## When NOT to Use

- User asks for code changes, bug fixes, or feature implementation
- User asks for data outside the configured GitHub org/repos
- User asks for metrics of AI tool usage (Cursor, Claude Code) — these are unavailable due to admin permission limitations

## Workflow

### Step 1: Determine Scope and Time Window

From the user's prompt, extract:

**Scope:**
- **Org-wide:** No repo mentioned, or words like "engenharia", "time", "org", "geral"
- **Repo-specific:** Repo name detected (e.g., "auth-service", "frontend")
- **PR-timeline:** PR number mentioned, or word "timeline" + PR reference

**Time Window:**
- **Default:** Last 24 hours (00:00 to 23:59 of previous day)
- **Explicit:** Parse "esta semana", "últimos 7 dias", "desde segunda", "hoje", "ontem"
- **Custom:** ISO dates if provided

### Step 2: Query GitHub Data

Use GitHub MCP to fetch:

1. **list_commits** (since/until, per repo)
2. **list_pull_requests** (state=all, sorted by updated, filter by date)
3. **list_issues** (state=all, filter by created/closed in window)
4. **list_reviews** (for PRs in window)
5. **list_comments** (for PRs in window)
6. **list_workflow_runs** (for repos in window, filter by date)
7. **list_releases** (for repos in window, filter by date)

For **org-wide**, query top 10 repos by recent activity (commits + PRs in window).

For **PR-timeline**, query the specific PR + all reviews + all comments + all commits + all workflow runs for that branch.

### Step 3: Parse and Enrich

- **Extract Jira keys:** Scan PR titles, commit messages, branch names for pattern `[A-Z]+-\d+`
- **Deduplicate keys**, then query Jira MCP (`get_issue`) for each
- **Classify reviewers:** Use `scripts/heuristics.py` — `is_bot(username)` to detect bots (dependabot, github-actions, sonarqube, etc.)

### Step 4: Apply Heuristics

Use `scripts/heuristics.py` for classification:

| Function | Purpose |
|---|---|
| `is_bot()` | Detect bot reviewers |
| `classify_pr()` | Feature / Bugfix / Other |
| `detect_blocked()` | Flag blocked PRs |
| `detect_long_running()` | Flag old PRs |
| `extract_jira_keys()` | Find Jira references |
| `classify_verdict()` | Healthy / Blocked / Long-running |

### Step 5: Generate HTML Report

Generate a **single self-contained HTML file** with inline CSS.

**Sections:**
1. **Header** — Title, scope, date, limitation note about AI usage
2. **KPI Cards** — 11 cards: Eventos, Commits, PRs abertos, PRs merged, Reviews, Comentários, Issues fechadas, Issues abertas, Devs ativos, Actions falha, Releases
3. **Destaques** — Color-coded cards: bloqueados, long-running, humano vs bot, anomalias
4. **PRs em Destaque** — Table with PR #, Repo, Autor, Título, Status, Reviews, Comentários, Duração, Jira links, Tags
5. **Análise de Reviews** — Stats: total, human vs bot, top revisores, direct merges
6. **Cruzamento Jira** — Table (if applicable)
7. **Contribuidores** — List with counts
8. **Timeline** — Chronological events
9. **Footer** — Source note

**CSS Requirements:**
- Self-contained, no external dependencies
- Responsive with max-width 1200px
- Colors: green=merged, red=blocked, yellow=long-running, blue=info, gray=bot
- Use `<details>`/`<summary>` for collapsible sections

### Step 6: Output

- Save HTML to: `github-report-{scope}-{date}.html`
- Present key highlights in text summary
- Offer to open in browser

## Output Format by Mode

### Org-wide
- Top 10 repos, top 5 PRs, Jira summary, top 5 contributors

### Repo-specific
- All KPIs, all PRs, all issues, releases, workflow runs, full timeline

### PR-timeline
- PR metadata + timeline + reviews + comments + Jira + verdict

## Error Handling

- **GitHub MCP error:** Report in header, suggest checking token
- **Jira MCP error:** Skip section, continue
- **No data:** Zeroed KPIs + "Nenhuma atividade detectada"
- **Partial failure:** Note about what couldn't be fetched
- **Rate limited:** Retry once with 5s backoff

## Limitations

- **No AI usage metrics:** Cannot report on Cursor/Claude Code per dev
- **Jira:** Only works if tickets referenced in PRs/commits
- **Private repos:** Require appropriate MCP permissions
- **Large orgs:** Limited to top 10 repos

## Examples

1. "Dá o panorama de ontem na engenharia" → org-wide report
2. "Resumo do repo auth-service" → repo-specific
3. "Timeline do PR #234" → PR deep-dive

---

*Version 1.0 - 2026-06-11*
