# Output Contract

This file defines required generation and validation behavior for `career-profile-optimizer`.

## Mode Defaults

- `optimization priority`: `balanced` (unless user chooses LinkedIn-first or ATS-first)
- `language-mode`: `monolingual` (unless user enables bilingual)
- `audit-mode`: `off` (unless user enables on)
- `resume-export`: `off` (unless user enables on)

## Per-Experience Outputs (Phase 2)

Always generate:
1. LinkedIn Version
- Detailed, narrative style, role-focused context

2. ATS/PDF Resume Version
- 4-5 concise bullets, impact-focused

### Incomplete Data Fallback

- Ask once for concrete values or estimate ranges.
- If user still has no numbers, proceed with qualitative impact wording.
- If user approves ranges, label them as estimates.
- Never fabricate data.

## Language-Mode Contract

### Monolingual
- Output only in user's language.

### Bilingual
- Determine bilingual pair using this rule:
  - If user's primary language is NOT English:
    - Primary: user's language
    - Secondary: English
  - If user's primary language IS English:
    - Primary: English
    - Secondary: user-selected target language
- If primary is English and user does not choose a secondary language, ask explicitly before generating bilingual output.
- Keep parity of facts, dates, metrics, scope, and claims across both languages.
- Do not add claims in English that do not exist in primary language.
- Do not add claims in secondary language that do not exist in primary language.

## Recommended Skills Contract

Recommend exactly 5 skills for each experience.

### Required Template (for each skill)
- `Skill: <name>` (Translate "Skill" to the user's language)
- `Evidence: <responsibility/tool/result explicitly mentioned by user>` (Translate "Evidence" to the user's language)
- `Why it improves discoverability: <short role-aligned rationale>` (Translate "Why it improves discoverability" to the user's language)

### Low-Detail Micro-Template
Use when user context remains weak after clarification:
- Keep same 3 fields.
- Explicitly state known vs unknown evidence.
- Keep rationale role-aligned and non-generic.
- Avoid repeated rationale text across the 5 skills.

### Evidence Rubric (internal)
- `0` weak: no concrete evidence
- `1` partial: some evidence, incomplete context/impact
- `2` strong: direct evidence clearly linked

### Rubric Gate
- No recommended skill with score `0`
- At least 3 of 5 skills with score `2`
- If gate fails, run one corrective pass:
  1. Replace weak skills with better-supported alternatives
  2. If still weak, ask 1 focused follow-up question
  3. If user cannot add detail, keep best-supported set and mark partial evidence
- Keep rubric scores internal unless user asks.

## Closing Outputs (Phase 3)

After all experiences are approved:
1. LinkedIn Headline
- 120 to 220 characters

2. About / Summary
- 900 to 1,600 characters

### Bilingual closing behavior
- Monolingual: one headline + one about in user's language
- Bilingual: headline and about in both languages with factual parity and selected language pair

## Mandatory Final Validation Pass

Before presenting final output:
1. Headline length within 120-220 (revise once if needed)
2. About length within 900-1,600 (revise once if needed)
3. All numbers user-provided or estimate-labeled
4. Text respects selected priority mode
5. Recommended skills pass rubric gate
6. If bilingual mode on:
- no metric/date/title mismatch
- no extra one-language-only claims
- equivalent positioning in both languages

## Priority Mode Behavior

### LinkedIn-first
- Richer narrative context and positioning emphasis

### ATS-first
- Denser keyword and impact signaling with concise phrasing

### Balanced
- Preserve parity between narrative quality and ATS signal strength

## Audit-Mode Contract

### audit-mode off
- Return polished outputs only

### audit-mode on
- Return polished outputs plus `Audit Checklist`

### Mandatory `Audit Checklist` Format
1. `Format Validation`
- Headline character count and status
- About character count and status

2. `Data Validation`
- Metrics used + origin (user-provided or estimate-labeled)
- Confirmation of no fabricated data

3. `Priority Validation`
- Selected priority mode
- Brief note on wording/structure alignment

4. `Language Validation`
- Selected language mode
- If bilingual: selected language pair and parity confirmation across languages

5. `Recommended Skills Validation`
- 5 recommended skills with evidence summary
- Rubric summary (score-2 count, confirmation of no score-0)

6. `Corrective Actions`
- Replacements, follow-up questions, or estimate labeling used
- If none: `No corrective actions required`

## Resume Export Contract

### resume-export off
- End interaction after Phase 3. No final document compilation required.

### resume-export on
- Execute **Phase 4: Full Resume Assembly** after Phase 3.
- Generate a pure, semantic HTML code block representing the complete ATS-friendly resume.
- **Template Requirement**: You MUST use the exact HTML structure provided in `skills/career-profile-optimizer/resume-template.html`. Do NOT invent new structure, `<style>` tags, inline CSS, or wrapping `<div>` elements. Keep it purely structural (`<h1>`, `<h2>`, `<h3>`, `<ul>`, `<p>`).
- **Format Requirements**: Fill out the bracketed information from the specific template based on the data inferred or collected. You MUST translate the section headers ("Professional Summary", "Experience", "Education", "Skills", "Languages") strictly to the actual language being used for the content of the resume, preserving cohesion. If optional fields (Target Roles/Headline, external Links, Languages) are not provided by the user, omit their corresponding `<p>` or `<h2>`/`<ul>` tags entirely. Ensure external Links are grouped with a maximum of 2 links per `<p>` tag.
- **Bilingual Mode**: If `language-mode` is `bilingual`, you MUST generate **two distinct independent HTML blocks** (one block for the primary language and another block for the secondary language) applying the template twice. Translate headers appropriately for each block.
- **Instructions**: You MUST output clear instructions for the user telling them to:
  1. Copy the generated HTML block.
  2. Save it locally as an `.html` file (e.g., `resume.html`) and open it in a web browser, OR alternatively, paste the code into an online HTML viewer like the W3Schools Tryit Editor (https://www.w3schools.com/html/tryit.asp?filename=tryhtml_intro).
  3. Press "Ctrl+A" and "Ctrl+C" to select and copy the rendered content from the browser page or viewer.
  4. Paste the content into a blank Word document or Google Docs to retain perfect heading/list hierarchy for ATS parsing.
