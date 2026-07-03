# Design Spec: Revisão da Skill `github-engineering-report`

> Data: 2026-07-03
> Status: Aprovado para implementação
> Escopo: Revisão específica da skill `github-engineering-report`

---

## 1. Visão geral e escopo

### Objetivo
Revisar a skill `github-engineering-report` para que:
- Seu corpo (`SKILL.md`, scripts, referências) esteja **100% em inglês**
- A resposta ao usuário e os textos da UI gerados estejam no **idioma da conversa do usuário**
- Toda dependência de **Jira seja removida**
- A skill esteja alinhada ao `docs/skill-authoring-standard.md` atualizado
- Seja validada por evals contra a org `https://github.com/Dokploy` com **pass rate ≥ 90%**

### Escopo incluído
- Reescrita de `skills/github-engineering-report/SKILL.md`
- Atualização de `skills/github-engineering-report/scripts/heuristics.py`
- Remoção de `skills/github-engineering-report/docs/2026-06-11-design.md` após mesclar conteúdo útil
- Criação de `skills/github-engineering-report/assets/report-template.html`
- Expansão de `skills/github-engineering-report/evals/evals.json`
- Atualização de `docs/skill-authoring-standard.md`
- Execução de evals com a metodologia `skill-creator` (baseline vs. nova skill)

### Fora de escopo
- Novas features (Slack, CSV export, charts históricos)
- Integrações além do GitHub MCP
- Cache de relatórios
- Suporte a idiomas além de inglês e português nesta revisão

---

## 2. Abordagem escolhida

**Abordagem C — Eval-First.**

Os 4 evals serão criados e executados primeiro contra a **skill atual** para estabelecer uma baseline objetiva. Depois a skill será reescrita e os mesmos evals serão executados novamente. Itera-se até atingir ≥ 90% de pass rate.

**Por que essa abordagem:**
- Alinhada às boas práticas da `skill-creator`
- Fornece métrica objetiva de melhoria
- Permite comparar old vs. new de forma rigorosa

---

## 3. Arquitetura e componentes

A skill será composta por quatro unidades bem definidas:

### 3.1 `SKILL.md` — orquestração
Responsável por:
- Frontmatter com descrição otimizada para trigger
- Definição de escopo e time window
- Regras de idioma (`CRITICAL LANGUAGE RULE`)
- Hard-gates de uso
- Fluxo de execução em 6 passos
- Contrato de output
- Fallbacks e tratamento de erros

### 3.2 `scripts/heuristics.py` — classificação determinística
Funções puras que recebem dados brutos do GitHub e retornam classificações:
- `is_bot(username)` — detecta revisores bot
- `classify_pr(title, branch)` — feature / bugfix / other
- `detect_blocked(pr, reviews, comments)` — flag de bloqueio
- `detect_long_running(pr)` — flag de PR antigo
- `classify_verdict(pr, reviews)` — Healthy / Blocked / Long-running

### 3.3 `assets/report-template.html` — template whitelabel
Template HTML base com:
- Estrutura semântica fixa
- CSS inline, self-contained, responsivo
- Paleta neutra com cores semânticas
- Placeholders para labels localizáveis
- Uso de `<details>`/`<summary>` para seções colapsáveis

### 3.4 `evals/evals.json` — casos de teste
Quatro prompts cobrindo org-wide, repo-specific, PR-timeline e localização para português.

---

## 4. Fluxo de dados

```
Prompt do usuário
  ↓
[Scope Extractor] → org-wide / repo-specific / PR-timeline
  ↓
[Time Window] → start_date, end_date (default: últimas 24h)
  ↓
[GitHub MCP]
  - list_commits
  - list_pull_requests
  - list_issues
  - list_reviews
  - list_comments
  - list_workflow_runs
  - list_releases
  ↓
[heuristics.py]
  - is_bot, classify_pr, detect_blocked, detect_long_running, classify_verdict
  ↓
[HTML Generator]
  - Lê assets/report-template.html
  - Preenche placeholders com dados e labels no idioma do usuário
  ↓
Arquivo HTML self-contained + resumo textual (no idioma do usuário)
```

**Regras de idioma:**
- A interface interna (nomes de funções, variáveis, reasoning do agente) é em inglês.
- O output ao usuário (títulos, labels, resumo) é detectado a partir do prompt do usuário.
- Nesta revisão, suportamos inglês e português.

---

## 5. Estrutura dos evals

Os 4 evals serão executados primeiro contra a **skill atual** (baseline) e depois contra a **skill revisada**.

| # | ID | Nome | Prompt | Assertions principais |
|---|----|------|--------|----------------------|
| 1 | 1 | `org-wide-en` | "Give me yesterday's engineering panorama for the Dokploy org" | HTML criado; contém "Dokploy"; tem KPI cards; lista top repos |
| 2 | 2 | `repo-specific-en` | "Summarize this week's activity in the Dokploy/dokploy repo" | HTML referencia repo; contém tabela de PRs; contém timeline |
| 3 | 3 | `pr-timeline-en` | "Show me the timeline of PR #<NUMBER> in Dokploy/dokploy" | PR number presente; verdict válido; seção de reviews presente |
| 4 | 4 | `localization-pt` | "Dá o panorama de ontem na engenharia do Dokploy" | HTML e resumo em português; labels localizadas |

**Observações:**
- O número do PR para o eval 3 será descoberto na fase de preparação via `gh pr list -R Dokploy/dokploy`.
- Cada eval terá `eval_metadata.json` com prompt e assertions.
- Cada execução terá runs `old_skill/` (baseline) e `with_skill/` (nova skill).
- Um grader subagent produzirá `grading.json` para cada run.

---

## 6. Template HTML base

### Localização
```
skills/github-engineering-report/assets/report-template.html
```

### Características
- **Estrutura fixa:** header, KPI cards, highlights, PR table, review analysis, contributors, timeline, footer
- **CSS inline:** self-contained, sem dependências externas
- **Responsivo:** max-width 1200px, mobile-friendly
- **Paleta neutra:**
  - Cinza para bots
  - Verde para merged
  - Vermelho para blocked
  - Amarelo para long-running
  - Azul para info
- **Localizável:** placeholders para labels em diferentes idiomas
- **Colapsável:** uso de `<details>`/`<summary>` para seções longas

### Placeholders exemplo
```html
<h1>{{REPORT_TITLE}}</h1>
<span class="scope">{{SCOPE_LABEL}}: {{SCOPE_VALUE}}</span>
<div class="kpi">
  <div class="card">
    <span class="label">{{KPI_EVENTS}}</span>
    <span class="value">{{EVENTS_COUNT}}</span>
  </div>
  ...
</div>
```

---

## 7. Tratamento de erros e fallback

| Cenário | Comportamento |
|---------|---------------|
| GitHub MCP não configurado | Reportar erro no início da resposta textual; não tentar gerar HTML |
| GitHub MCP retorna erro de autenticação | Informar no header do HTML + sugerir verificar token |
| Repo inexistente ou sem acesso | HTML gerado com nota de erro; KPIs zerados |
| Sem PRs/issues/commits no período | HTML gerado normalmente com KPIs zerados e mensagem "No activity detected" |
| Rate limit | Retry uma vez com backoff de 5s; se persistir, notar parcialidade |
| Erro no template | Fallback para HTML mínimo gerado inline |

**Princípio:** A skill nunca deve falhar silenciosamente. Sempre comunica o que aconteceu ao usuário no idioma da conversa.

---

## 8. Testes e validação

### Fase 1 — Baseline
1. Snapshot da skill atual em `github-engineering-report-workspace/skill-snapshot/`
2. Executar os 4 evals contra a skill atual
3. Capturar pass rate, tempo e tokens

### Fase 2 — Nova skill
1. Executar os mesmos 4 evals contra a skill revisada
2. Usar grader subagent para avaliar assertions
3. Gerar `benchmark.json` comparando baseline vs. nova skill

### Fase 3 — Iteração
1. Se pass rate < 90%, ajustar `SKILL.md`, template ou heurísticas
2. Repetir até atingir ≥ 90% ou estagnação

### Validação adicional
- Verificar que `SKILL.md` não contém português (exceto exemplos de input)
- Verificar que não há referências a Jira
- Verificar que HTML gerado é self-contained

---

## 9. Atualização do `docs/skill-authoring-standard.md`

O documento de padrão será atualizado para incluir:

1. **Language Rule obrigatória**
   - Corpo da skill em inglês
   - Output ao usuário no idioma detectado
   - Labels e textos de UI localizáveis

2. **Estrutura de skill alinhada à skill-creator**
   - Frontmatter, Overview, Hard Gates, Execution Flow, Output Contract, Validation, Fallback, Boundaries

3. **Bundled Resources**
   - `scripts/`, `references/`, `assets/`

4. **Progressive Disclosure**
   - Metadata (~100 palavras)
   - SKILL.md body (<500 linhas)
   - Bundled resources (sob demanda)

5. **Eval-Driven Development**
   - `evals/evals.json` com prompts, expected outputs, files, expectations, assertions
   - Workspace de iteração

6. **Description Optimization**
   - Descrição trigger-oriented e "pushy"

7. **Publication Checklist**
   - Incluir item de verificação de idioma

---

## 10. Critérios de aceite

Para considerar a revisão concluída:

- [ ] `SKILL.md` 100% em inglês (exceto exemplos de input do usuário)
- [ ] `CRITICAL LANGUAGE RULE` explicitada e seguida nos outputs
- [ ] Nenhuma referência a Jira no corpo da skill, heurísticas ou evals
- [ ] Template HTML whitelabel criado em `assets/report-template.html`
- [ ] 4 evals definidos em `evals/evals.json`
- [ ] Pass rate ≥ 90% na comparação com baseline
- [ ] Eval em português valida localização do output
- [ ] `docs/skill-authoring-standard.md` atualizado
- [ ] `docs/2026-06-11-design.md` removido após mesclar conteúdo útil
- [ ] Nenhum token/secret commitado acidentalmente

---

## 11. Decisões de design

| Decisão | Justificativa |
|---------|---------------|
| Remover Jira | Não há Jira disponível no ambiente; manter criaria dependência morta |
| Corpo em inglês / output localizado | Alinhado ao padrão do repositório e ao `skill-authoring-standard.md` |
| Template HTML whitelabel | Padroniza os 3 modos de relatório e facilita manutenção do CSS |
| Eval-first | Fornece baseline objetiva e segue metodologia skill-creator |
| 4 evals | Cobrem os 3 modos de relatório + teste de localização sem excesso |
| ≥ 90% pass rate | Garante qualidade alta antes de merge |

---

## 12. Próximos passos

1. Invocar a skill `writing-plans` para criar o plano de implementação detalhado
2. Executar o plano de implementação
3. Iterar com base nos resultados dos evals
