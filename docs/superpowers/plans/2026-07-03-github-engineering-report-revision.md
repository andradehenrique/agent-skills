# github-engineering-report Revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Revisar a skill `github-engineering-report` para corpo 100% em inglês, output localizado, sem dependência de Jira, com template HTML whitelabel e evals ≥ 90% pass rate contra a org Dokploy.

**Architecture:** A skill passa a ter quatro unidades: `SKILL.md` (orquestração), `scripts/heuristics.py` (classificação determinística), `assets/report-template.html` (template whitelabel localizável) e `evals/evals.json` (casos de teste). O fluxo de execução extrai escopo e time window, consulta o GitHub MCP, aplica heurísticas, preenche o template e entrega HTML + resumo no idioma do usuário.

**Tech Stack:** Markdown (SKILL.md), Python 3 (heurísticas), HTML/CSS (template), JSON (evals), GitHub CLI `gh`, GitHub MCP, skill-creator tooling.

## Global Constraints

- Corpo da skill (`SKILL.md`, scripts, assets, evals) deve estar em inglês.
- Output ao usuário (HTML, resumos, labels) deve estar no idioma detectado no prompt do usuário (inglês ou português nesta revisão).
- Nenhuma referência a Jira pode permanecer na skill.
- O HTML gerado deve ser self-contained (CSS inline, sem dependências externas).
- Template deve ser responsivo com max-width 1200px.
- Pass rate mínimo dos evals: 90%.
- Worktree/isolation: usar branch ou worktree separado se o repo estiver em desenvolvimento ativo.
- Commits frequentes e pequenos.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `docs/skill-authoring-standard.md` | Padrão do repositório atualizado com regra de idioma e práticas skill-creator |
| `skills/github-engineering-report/SKILL.md` | Orquestração da skill: frontmatter, regras, fluxo, contrato, fallbacks |
| `skills/github-engineering-report/scripts/heuristics.py` | Funções puras de classificação de PRs, reviews e contribuidores |
| `skills/github-engineering-report/assets/report-template.html` | Template HTML base whitelabel com placeholders localizáveis |
| `skills/github-engineering-report/evals/evals.json` | Definição dos 4 evals com prompts, expected outputs e assertions |
| `github-engineering-report-workspace/` | Resultados dos evals, snapshots, grading, benchmark e feedback |

---

## Task 1: Preparação do ambiente e inspeção da org Dokploy

**Files:**
- Read: `docs/superpowers/specs/2026-07-03-github-engineering-report-revision-design.md`
- Create: `github-engineering-report-workspace/dokploy-inspection.json`

**Interfaces:**
- Consumes: design spec
- Produces: `dokploy-inspection.json` com repos ativos, PRs recentes e número de PR para eval 3

- [ ] **Step 1: Verificar autenticação do `gh`**

Run:
```bash
gh auth status
```
Expected: Saída indicando usuário logado e token válido.

- [ ] **Step 2: Listar repos da org Dokploy**

Run:
```bash
gh repo list Dokploy --limit 50 --json name,description,pushedAt > github-engineering-report-workspace/dokploy-inspection.json
```
Expected: Arquivo JSON criado com lista de repos.

- [ ] **Step 3: Identificar repo principal e PRs recentes**

Run:
```bash
gh pr list -R Dokploy/dokploy --state all --limit 20 --json number,title,state,createdAt,mergedAt,author >> github-engineering-report-workspace/dokploy-inspection.json
```
Expected: PRs recentes do repo `Dokploy/dokploy` anexados ao arquivo de inspeção.

- [ ] **Step 4: Selecionar número de PR para eval 3**

Abrir `github-engineering-report-workspace/dokploy-inspection.json` e escolher um PR merged ou aberto com atividade recente. Registrar o número escolhido (ex: `123`) em `github-engineering-report-workspace/selected-pr.txt`.

- [ ] **Step 5: Commit**

```bash
git add github-engineering-report-workspace/dokploy-inspection.json github-engineering-report-workspace/selected-pr.txt
git commit -m "chore: inspect Dokploy org for eval setup"
```

---

## Task 2: Atualizar `docs/skill-authoring-standard.md`

**Files:**
- Modify: `docs/skill-authoring-standard.md`

**Interfaces:**
- Consumes: design spec seção 9
- Produces: documento de padrão atualizado

- [ ] **Step 1: Adicionar seção `Language Rule` após `Mandatory Reliability Rules`**

Edit `docs/skill-authoring-standard.md` e adicionar:
```markdown
### 6. Language Rule (CRITICAL)

Every skill in this repository must follow this rule:

- The skill body (`SKILL.md`), bundled scripts, references, and internal reasoning must be written in English.
- All user-facing text — including HTML labels, report titles, spoken summaries, and error messages — must be in the same language as the user's prompt.
- If the skill generates files with localized labels, use placeholders or a lookup mechanism so the output language can be determined at runtime.
- Example rule to include in every `SKILL.md`:
  ```markdown
  ## CRITICAL LANGUAGE RULE
  The skill body, scripts, and internal reasoning are in English.
  All user-facing text must match the language of the user's prompt.
  ```
```

- [ ] **Step 2: Adicionar seções de boas práticas da skill-creator**

Adicionar após a seção de `Output Contract Checklist`:
```markdown
## Bundled Resources

Skills may include:
- `scripts/` — deterministic/repetitive tasks
- `references/` — heavy documentation loaded on demand
- `assets/` — templates, icons, fonts

## Progressive Disclosure

- Metadata (name + description): ~100 words, always in context
- SKILL.md body: <500 lines ideal
- Bundled resources: loaded on demand

## Eval-Driven Development

- Define evals in `evals/evals.json`
- Include prompts, expected outputs, input files, expectations, and assertions
- Use `<skill-name>-workspace/iteration-N/` for iteration artifacts
```

- [ ] **Step 3: Atualizar `Publication Checklist`**

Adicionar ao checklist:
```markdown
6. Language consistency
- [ ] Skill body is in English
- [ ] User-facing output matches the user's language
- [ ] No mixed-language labels in generated artifacts
```

- [ ] **Step 4: Verificar que não há português no doc**

Run:
```bash
grep -n "Visão\|Escopo\|Objetivo\|Regras\|Fluxo" docs/skill-authoring-standard.md || echo "No Portuguese headers found"
```
Expected: `No Portuguese headers found`

- [ ] **Step 5: Commit**

```bash
git add docs/skill-authoring-standard.md
git commit -m "docs: update skill-authoring-standard with language rule and skill-creator practices"
```

---

## Task 3: Criar template HTML base

**Files:**
- Create: `skills/github-engineering-report/assets/report-template.html`

**Interfaces:**
- Consumes: design spec seção 6
- Produces: template HTML com placeholders localizáveis

- [ ] **Step 1: Criar diretório de assets**

Run:
```bash
mkdir -p skills/github-engineering-report/assets
```

- [ ] **Step 2: Escrever template HTML base**

Create `skills/github-engineering-report/assets/report-template.html`:
```html
<!DOCTYPE html>
<html lang="{{LANG}}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{REPORT_TITLE}}</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; color: #222; }
    .container { max-width: 1200px; margin: 0 auto; background: #fff; padding: 24px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    h1 { margin-top: 0; }
    .meta { color: #666; margin-bottom: 16px; }
    .kpi { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 24px; }
    .kpi .card { background: #f9f9f9; border-radius: 6px; padding: 12px; text-align: center; }
    .kpi .card .label { display: block; font-size: 0.85em; color: #555; }
    .kpi .card .value { display: block; font-size: 1.6em; font-weight: bold; }
    .tag { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; }
    .tag.merged { background: #d4edda; color: #155724; }
    .tag.blocked { background: #f8d7da; color: #721c24; }
    .tag.long-running { background: #fff3cd; color: #856404; }
    .tag.bot { background: #e2e3e5; color: #383d41; }
    table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    th, td { text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }
    details { margin-bottom: 16px; }
    summary { font-weight: bold; cursor: pointer; }
  </style>
</head>
<body>
  <div class="container">
    <h1>{{REPORT_TITLE}}</h1>
    <div class="meta">{{SCOPE_LABEL}}: {{SCOPE_VALUE}} | {{DATE_LABEL}}: {{DATE_VALUE}}</div>

    <details open>
      <summary>{{KPI_TITLE}}</summary>
      <div class="kpi">
        <div class="card"><span class="label">{{KPI_EVENTS}}</span><span class="value">{{EVENTS_COUNT}}</span></div>
        <div class="card"><span class="label">{{KPI_COMMITS}}</span><span class="value">{{COMMITS_COUNT}}</span></div>
        <div class="card"><span class="label">{{KPI_PRS_OPENED}}</span><span class="value">{{PRS_OPENED_COUNT}}</span></div>
        <div class="card"><span class="label">{{KPI_PRS_MERGED}}</span><span class="value">{{PRS_MERGED_COUNT}}</span></div>
        <div class="card"><span class="label">{{KPI_REVIEWS}}</span><span class="value">{{REVIEWS_COUNT}}</span></div>
        <div class="card"><span class="label">{{KPI_COMMENTS}}</span><span class="value">{{COMMENTS_COUNT}}</span></div>
        <div class="card"><span class="label">{{KPI_ISSUES_CLOSED}}</span><span class="value">{{ISSUES_CLOSED_COUNT}}</span></div>
        <div class="card"><span class="label">{{KPI_ISSUES_OPENED}}</span><span class="value">{{ISSUES_OPENED_COUNT}}</span></div>
        <div class="card"><span class="label">{{KPI_ACTIVE_DEVS}}</span><span class="value">{{ACTIVE_DEVS_COUNT}}</span></div>
        <div class="card"><span class="label">{{KPI_FAILED_ACTIONS}}</span><span class="value">{{FAILED_ACTIONS_COUNT}}</span></div>
        <div class="card"><span class="label">{{KPI_RELEASES}}</span><span class="value">{{RELEASES_COUNT}}</span></div>
      </div>
    </details>

    <details open>
      <summary>{{HIGHLIGHTS_TITLE}}</summary>
      {{HIGHLIGHTS_CONTENT}}
    </details>

    <details open>
      <summary>{{PRS_TITLE}}</summary>
      {{PRS_CONTENT}}
    </details>

    <details>
      <summary>{{REVIEWS_TITLE}}</summary>
      {{REVIEWS_CONTENT}}
    </details>

    <details>
      <summary>{{CONTRIBUTORS_TITLE}}</summary>
      {{CONTRIBUTORS_CONTENT}}
    </details>

    <details>
      <summary>{{TIMELINE_TITLE}}</summary>
      {{TIMELINE_CONTENT}}
    </details>

    <footer>
      <p>{{SOURCE_NOTE}}</p>
    </footer>
  </div>
</body>
</html>
```

- [ ] **Step 3: Validar que o template é self-contained**

Run:
```bash
grep -n "http://\|https://\|<link\|@import" skills/github-engineering-report/assets/report-template.html || echo "No external dependencies found"
```
Expected: `No external dependencies found`

- [ ] **Step 4: Commit**

```bash
git add skills/github-engineering-report/assets/report-template.html
git commit -m "feat(github-engineering-report): add whitelabel HTML report template"
```

---

## Task 4: Atualizar `scripts/heuristics.py`

**Files:**
- Modify: `skills/github-engineering-report/scripts/heuristics.py`

**Interfaces:**
- Consumes: design spec seção 3.2
- Produces: heurísticas em inglês, sem referências a Jira

- [ ] **Step 1: Revisar comentários e docstrings para inglês**

Edit `skills/github-engineering-report/scripts/heuristics.py`. Atualizar todas as docstrings e comentários para inglês. Manter nomes de funções em inglês (já estão).

- [ ] **Step 2: Remover referências a Jira**

Confirmar que `extract_jira_keys` não é mais chamada pela skill. Como Jira foi removido do escopo, a função pode permanecer no script (não quebra nada) ou ser removida. Para manter o script focado, removê-la.

Expected final functions in file:
- `is_bot(username)`
- `classify_pr(title, branch)`
- `detect_blocked(pr, reviews, comments)`
- `detect_long_running(pr)`
- `classify_verdict(pr, reviews)`

- [ ] **Step 3: Adicionar teste rápido das heurísticas**

Create temporary test script `test_heuristics.py`:
```python
import sys
sys.path.insert(0, "skills/github-engineering-report")
from scripts.heuristics import is_bot, classify_pr

assert is_bot("dependabot[bot]") is True
assert is_bot("alice") is False
assert classify_pr("feat: add auth", "feature/auth") == "feature"
assert classify_pr("fix: login bug", "fix/login") == "bugfix"

print("Heuristics OK")
```

Run:
```bash
python test_heuristics.py
```
Expected: `Heuristics OK`

- [ ] **Step 4: Remover teste temporário e commit**

```bash
rm test_heuristics.py
git add skills/github-engineering-report/scripts/heuristics.py
git commit -m "refactor(github-engineering-report): translate heuristics to English and remove Jira refs"
```

---

## Task 5: Reescrever `SKILL.md`

**Files:**
- Modify: `skills/github-engineering-report/SKILL.md`
- Read: `docs/skill-authoring-standard.md` (atualizado)
- Read: `skills/github-engineering-report/docs/2026-06-11-design.md` (para mesclar)
- Delete: `skills/github-engineering-report/docs/2026-06-11-design.md`

**Interfaces:**
- Consumes: design spec, skill-authoring-standard, design doc legado
- Produces: SKILL.md reescrito em inglês

- [ ] **Step 1: Mesclar conteúdo útil do design doc legado**

Ler `skills/github-engineering-report/docs/2026-06-11-design.md` e extrair informações ainda relevantes (ex: detalhes de heurísticas, estrutura do HTML, edge cases) que não estejam no SKILL.md atual.

- [ ] **Step 2: Reescrever SKILL.md em inglês**

Edit `skills/github-engineering-report/SKILL.md` com a estrutura:
```markdown
---
name: github-engineering-report
description: |
  Use when the user asks for an engineering panorama, daily/weekly engineering summary,
  repository activity report, or PR timeline analysis from GitHub. Trigger this skill
  whenever the user mentions engineering summaries, repo activity, what happened today/yesterday,
  PR timelines, team activity, or engineering highlights — even if they do not explicitly
  ask for a "report".
---

# GitHub Engineering Report

## Overview
Generate self-contained HTML reports from GitHub activity...

## Required Tools
- GitHub MCP with `repo` scope

## HARD-GATE: When to Use / When NOT to Use
...

## CRITICAL LANGUAGE RULE
The skill body, scripts, and internal reasoning are in English.
All user-facing text (HTML titles, section labels, summaries, spoken responses)
must be in the same language as the user's prompt.

## Execution Flow
### Step 1: Determine Scope and Time Window
### Step 2: Query GitHub Data
### Step 3: Parse and Enrich
### Step 4: Apply Heuristics
### Step 5: Generate HTML Report
### Step 6: Output

## Output Contract
...

## Validation Checklist
...

## Failure and Fallback Handling
...

## Boundaries
...

## Examples
...
```

**Regras de conteúdo:**
- Remover toda referência a Jira
- Descrever uso do `assets/report-template.html`
- Manter 3 modos: org-wide, repo-specific, PR-timeline
- Incluir regra de idioma
- Incluir hard-gates
- Incluir fallbacks

- [ ] **Step 3: Verificar que SKILL.md não contém português (exceto exemplos de input)**

Run:
```bash
grep -n "panorama\|resumo\|destaques\|análise\|contém\|exemplo" skills/github-engineering-report/SKILL.md || echo "No Portuguese words found"
```
Expected: `No Portuguese words found` (ou apenas dentro de examples de input do usuário)

- [ ] **Step 4: Remover design doc legado**

```bash
rm skills/github-engineering-report/docs/2026-06-11-design.md
```

- [ ] **Step 5: Commit**

```bash
git add skills/github-engineering-report/SKILL.md
git commit -m "feat(github-engineering-report): rewrite SKILL.md in English, remove Jira, add language rule"
```

---

## Task 6: Criar evals

**Files:**
- Modify: `skills/github-engineering-report/evals/evals.json`
- Read: `github-engineering-report-workspace/selected-pr.txt`

**Interfaces:**
- Consumes: número do PR selecionado na Task 1
- Produces: evals.json com 4 evals e assertions

- [ ] **Step 1: Ler número do PR selecionado**

Run:
```bash
cat github-engineering-report-workspace/selected-pr.txt
```
Expected: Número do PR (ex: `123`)

- [ ] **Step 2: Escrever evals.json**

Edit `skills/github-engineering-report/evals/evals.json`:
```json
{
  "skill_name": "github-engineering-report",
  "evals": [
    {
      "id": 1,
      "prompt": "Give me yesterday's engineering panorama for the Dokploy org",
      "expected_output": "Self-contained HTML report with org-wide KPIs, top repos, top PRs, and highlights in English",
      "files": [],
      "expectations": [
        "An HTML file is created",
        "The HTML contains the word 'Dokploy'",
        "The HTML contains KPI cards section",
        "The HTML lists top repositories"
      ],
      "assertions": [
        {"name": "html_created", "type": "file_exists", "pattern": "github-report-*.html"},
        {"name": "contains_dokploy", "type": "regex", "file_pattern": "github-report-*.html", "regex": "Dokploy"},
        {"name": "contains_kpi", "type": "regex", "file_pattern": "github-report-*.html", "regex": "class=\"kpi\""}
      ]
    },
    {
      "id": 2,
      "prompt": "Summarize this week's activity in the Dokploy/dokploy repo",
      "expected_output": "Self-contained HTML report with repo-specific PRs, issues, commits, and timeline in English",
      "files": [],
      "expectations": [
        "An HTML file is created",
        "The HTML references 'Dokploy/dokploy' or 'dokploy'",
        "The HTML contains a PR table",
        "The HTML contains a timeline section"
      ],
      "assertions": [
        {"name": "html_created", "type": "file_exists", "pattern": "github-report-*.html"},
        {"name": "contains_repo", "type": "regex", "file_pattern": "github-report-*.html", "regex": "dokploy"},
        {"name": "contains_prs", "type": "regex", "file_pattern": "github-report-*.html", "regex": "<table"}
      ]
    },
    {
      "id": 3,
      "prompt": "Show me the timeline of PR #<PR_NUMBER> in Dokploy/dokploy",
      "expected_output": "Self-contained HTML report with PR metadata, timeline, reviews, comments, and verdict in English",
      "files": [],
      "expectations": [
        "An HTML file is created",
        "The HTML contains the PR number",
        "The HTML contains a verdict (Healthy/Blocked/Long-running)",
        "The HTML contains a reviews section"
      ],
      "assertions": [
        {"name": "html_created", "type": "file_exists", "pattern": "github-report-*.html"},
        {"name": "contains_pr_number", "type": "regex", "file_pattern": "github-report-*.html", "regex": "#<PR_NUMBER>"},
        {"name": "contains_verdict", "type": "regex", "file_pattern": "github-report-*.html", "regex": "Healthy|Blocked|Long-running"}
      ]
    },
    {
      "id": 4,
      "prompt": "Dá o panorama de ontem na engenharia do Dokploy",
      "expected_output": "Self-contained HTML report and text summary in Portuguese",
      "files": [],
      "expectations": [
        "An HTML file is created",
        "The HTML contains Portuguese labels (e.g., 'Engenharia', 'Commits', 'Pull Requests')",
        "The text summary is in Portuguese"
      ],
      "assertions": [
        {"name": "html_created", "type": "file_exists", "pattern": "github-report-*.html"},
        {"name": "contains_portuguese", "type": "regex", "file_pattern": "github-report-*.html", "regex": "Engenharia|Commits|Pull Requests|Destaques"}
      ]
    }
  ]
}
```

Substituir `<PR_NUMBER>` pelo número real lido no Step 1.

- [ ] **Step 3: Validar JSON**

Run:
```bash
python -m json.tool skills/github-engineering-report/evals/evals.json > /dev/null && echo "Valid JSON"
```
Expected: `Valid JSON`

- [ ] **Step 4: Commit**

```bash
git add skills/github-engineering-report/evals/evals.json
git commit -m "test(github-engineering-report): add 4 evals with assertions"
```

---

## Task 7: Executar baseline da skill atual

> **Nota:** Os evals desta task e da Task 8 devem ser executados por sub agents seguindo a metodologia `skill-creator`. Cada eval requer duas execuções (`with_skill` e `old_skill`) em paralelo, seguidas de grading. A skill `subagent-driven-development` ou `executing-plans` cuidará do dispatch e da coordenação.

**Files:**
- Create: `github-engineering-report-workspace/iteration-1/`
- Read: `skills/github-engineering-report/` (snapshot)

**Interfaces:**
- Consumes: evals.json, skill atual
- Produces: resultados baseline em `github-engineering-report-workspace/iteration-1/`

- [ ] **Step 1: Snapshot da skill atual**

Run:
```bash
cp -r skills/github-engineering-report github-engineering-report-workspace/skill-snapshot
```

- [ ] **Step 2: Criar workspace da iteração 1**

Run:
```bash
mkdir -p github-engineering-report-workspace/iteration-1/{eval-org-wide,eval-repo-specific,eval-pr-timeline,eval-localization-pt}
```

- [ ] **Step 3: Executar evals contra a skill atual**

Para cada eval, spawn dois sub agents em paralelo:
- `with_skill`: usa `skills/github-engineering-report/` (atual)
- `old_skill`: usa `github-engineering-report-workspace/skill-snapshot/` (mesma coisa, baseline)

Anotar resultados em cada diretório.

Como este plano será executado por subagent-driven-development ou executing-plans, os sub agents devem ser instruídos a:
1. Ler o SKILL.md do caminho especificado
2. Executar o prompt do eval
3. Salvar outputs em `outputs/`
4. Salvar `metrics.json` e `timing.json`

- [ ] **Step 4: Grading das execuções baseline**

Para cada run, spawn grader subagent para avaliar assertions e salvar `grading.json`.

- [ ] **Step 5: Commit dos resultados baseline (opcional)**

```bash
git add github-engineering-report-workspace/iteration-1/
git commit -m "chore(github-engineering-report): add baseline eval results"
```

---

## Task 8: Executar nova skill e iterar

**Files:**
- Read: `skills/github-engineering-report/SKILL.md` (reescrito)
- Create: `github-engineering-report-workspace/iteration-2/` (se necessário)

**Interfaces:**
- Consumes: skill revisada, evals.json
- Produces: benchmark comparando baseline vs nova skill

- [ ] **Step 1: Executar evals contra a skill revisada**

Repetir o processo da Task 7, mas usando a skill revisada para `with_skill` e mantendo `old_skill` como baseline.

- [ ] **Step 2: Agregar benchmark**

Run from the skill-creator directory:
```bash
cd /home/henrique/.agents/skills/skill-creator
python -m scripts.aggregate_benchmark /home/henrique/work/ai/agent-skills/github-engineering-report-workspace/iteration-1 --skill-name github-engineering-report
```
Expected: `benchmark.json` e `benchmark.md` gerados em `github-engineering-report-workspace/iteration-1/`.

- [ ] **Step 3: Verificar pass rate**

Abrir `benchmark.json` e verificar `run_summary.with_skill.pass_rate.mean`.

- [ ] **Step 4: Iterar se necessário**

Se pass rate < 0.90:
1. Identificar quais assertions falharam
2. Ajustar `SKILL.md`, `assets/report-template.html` ou `scripts/heuristics.py`
3. Criar `iteration-2/`
4. Repetir execução
5. Re-agregar benchmark

- [ ] **Step 5: Commit quando atingir ≥ 90%**

```bash
git add github-engineering-report-workspace/iteration-1/benchmark.json github-engineering-report-workspace/iteration-1/benchmark.md
git commit -m "test(github-engineering-report): add benchmark with >=90% pass rate"
```

---

## Task 9: Finalizar e commitar

**Files:**
- All modified files

- [ ] **Step 1: Verificação final de idioma**

Run:
```bash
grep -R "panorama\|resumo\|destaques\|análise\|Jira\|jira" skills/github-engineering-report/SKILL.md skills/github-engineering-report/scripts/ skills/github-engineering-report/evals/ || echo "No issues found"
```
Expected: `No issues found`

- [ ] **Step 2: Verificar que não há secrets**

Run:
```bash
grep -R "ghp_\|github_pat\|token.*=\|password" skills/github-engineering-report/ github-engineering-report-workspace/ || echo "No secrets found"
```
Expected: `No secrets found`

- [ ] **Step 3: Review do git status**

Run:
```bash
git status --short
```
Expected: Lista controlada de arquivos modificados/criados. Nada inesperado.

- [ ] **Step 4: Commit final**

```bash
git add -A
git commit -m "feat(github-engineering-report): complete skill revision with evals and benchmark"
```

---

## Self-Review Checklist

Antes de entregar este plano para execução, verificar:

- [ ] Cada spec requirement tem uma task correspondente
- [ ] Não há placeholders (TBD, TODO, etc.)
- [ ] File paths são exatos
- [ ] Comandos têm expected output
- [ ] Signatures/types são consistentes entre tasks
- [ ] Commits são pequenos e frequentes
- [ ] Cada task termina com um deliverable testável
