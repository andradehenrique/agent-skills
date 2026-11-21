"""Contract tests for the brand-engine v2 references.

The references are the executable documentation the skill points to: they must
resolve from ``SKILL.md``, stay lean, and describe the v2 contract that
``build_theme.py`` and ``new_page.py`` actually implement. Run with the stdlib
runner (``python3 skills/brand-engine/tests/test_references.py``).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
REFS = ROOT / "references"
REFERENCE_NAMES = ("discovery", "tokens", "formats", "voice", "logo")
ROUTE_FIELDS = (
    "Ideia",
    "Paleta",
    "Tipografia",
    "Forma",
    "Composição",
    "Ícones",
    "Imagem",
    "Por que",
    "Formatos",
    "Risco",
)
FORMATS = (
    "manual",
    "brand-kit",
    "onepage",
    "report",
    "deck",
    "social",
    "app",
    "blank",
)


def read_ref(name: str) -> str:
    path = REFS / f"{name}.md"
    assert path.is_file(), f"missing reference: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


def has_toc(text: str) -> bool:
    heading = re.search(r"(?mi)^##\s+(Contents|Indice|Índice|Sumário)\b", text)
    return bool(heading) and len(re.findall(r"\]\(#", text)) >= 2


def test_all_skill_doc_links_resolve() -> None:
    skill = SKILL.read_text(encoding="utf-8")
    for name in REFERENCE_NAMES:
        path = REFS / f"{name}.md"
        assert path.is_file(), f"missing reference: skills/brand-engine/references/{name}.md"
        assert f"references/{name}.md" in skill, (
            f"SKILL.md must point to references/{name}.md"
        )

    for document in [SKILL, *sorted(REFS.glob("*.md"))]:
        text = document.read_text(encoding="utf-8")
        for raw in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
            target = raw.strip().split()[0].strip("<>")
            if target.startswith(("http://", "https://", "mailto:", "tel:", "#")):
                continue
            target = target.split("#", 1)[0]
            if not target:
                continue
            resolved = (document.parent / target).resolve()
            assert resolved.exists(), f"{document.name} links to missing {target}"


def test_each_reference_is_under_300_lines_or_has_toc() -> None:
    for name in REFERENCE_NAMES:
        text = read_ref(name)
        lines = len(text.splitlines())
        assert lines < 300 or has_toc(text), (
            f"{name}.md has {lines} lines; keep it under 300 or add a TOC"
        )


def test_discovery_has_questions_and_routes() -> None:
    text = read_ref("discovery")
    lowered = text.lower()

    questions = re.findall(r"(?m)^### P\d+\b", text)
    routes = re.findall(r"(?m)^### Rota [A-Z]\b", text)
    assert 5 <= len(questions) <= 8, f"expected 5-8 questions, found {len(questions)}"
    assert 2 <= len(routes) <= 3, f"expected 2-3 routes, found {len(routes)}"

    for field in ROUTE_FIELDS:
        assert text.count(f"**{field}:**") == len(routes), (
            f"each route needs **{field}:** "
            f"({text.count(f'**{field}:**')} found for {len(routes)} routes)"
        )

    assert re.search(r"(?i)recomendad", text), "one route must be marked recommended"
    assert "granularidade sob demanda" in lowered, (
        "discovery.md must state the granularity-on-demand rule"
    )
    assert "proponha, não interrogue" in lowered, (
        "discovery.md must state the propose-don't-interrogate UX rule"
    )
    assert "text-first" in lowered or "texto primeiro" in lowered, (
        "discovery must stay text-first"
    )
    assert "workdir" in lowered or "working directory" in lowered, (
        "discovery must read optional images from the working directory"
    )
    assert "gate" in lowered and ("rota" in lowered), (
        "discovery must keep the route confirmation gate"
    )


def test_tokens_documents_v2_schema() -> None:
    text = read_ref("tokens")
    lowered = text.lower()

    for role in ("canvas", "surface", "ink", "primary", "accent", "support"):
        assert role in text, f"tokens.md must document the {role!r} colour role"
    assert "opcional" in lowered, "accent/support must be documented as optional"

    assert '"version": 2' in text, "the schema example must use version 2"
    assert '"design": {' in text, "the schema must nest colors/type/shape under design"
    assert "voice" in lowered and "opcional" in lowered, (
        "voice must be documented as an optional top-level block"
    )

    for token in ("--b-fg", "--b-primary", "--b-chart-1", "--b-chart-8"):
        assert token in text, f"tokens.md must document {token}"
    for role in ("success", "warning", "danger", "info"):
        assert f"--b-{role}" in text, f"tokens.md must document --b-{role}"
    for token in ("--b-success-soft", "--b-success-solid", "--b-on-success",
                  "--b-on-success-soft", "--b-<role>-soft", "--b-<role>-solid",
                  "--b-on-<role>"):
        assert token in text, f"tokens.md must document {token}"

    assert '"feedback": "auto"' in text and '"charts": "auto"' in text, (
        "feedback and charts must default to auto"
    )
    for profile in ("sharp", "soft", "round"):
        assert profile in text, f"radius profile {profile!r} must be documented"
    for values in ("0/0/2/4/4", "4/8/12/16/24", "8/12/16/24/9999"):
        assert values in text, f"radius profile values {values} must be documented"
    assert "4 ou 8" in text or ("unit" in lowered and "4" in text and "8" in text), (
        "unit must accept 4 or 8"
    )
    assert "--b-unit" in text and "--b-space-16" in text, (
        "spacing tokens must follow the unit"
    )
    assert '"gradient": null' in text and "opcional" in lowered, (
        "gradient must be documented as optional"
    )
    assert '[data-theme="dark"]' in text, "dark mode must be documented as optional"

    for fragment in (
        "@theme",
        "@custom-variant dark",
        "--spacing",
        "bg-grad-brand",
        "bg-surface",
        "text-fg",
        "Tailwind v4",
    ):
        assert fragment in text, f"tokens.md must document the Tailwind mapping {fragment!r}"

    for fragment in (
        "build_theme(brand_path, out_dir, force=False)",
        "ThemeBuild(theme_css, tailwind_theme_css)",
        "load_brand(brand_path)",
        "render_theme(brand)",
        "resolve_brand_path(brand_flag=None, cwd=None)",
        "contrast_ratio(foreground, background)",
        "BrandError",
        "--b-color-<slug>",
        "primary-hover",
        "line-input",
    ):
        assert fragment in text, f"tokens.md must document {fragment!r}"

    assert "3:1" in text and "4.5:1" in text and "7:1" in text, (
        "the contrast guarantees must be stated"
    )
    assert "slug" in lowered and ("case-insensitive" in lowered or "casefold" in lowered), (
        "colour references must accept the case-insensitive slug"
    )


def test_formats_has_all_formats() -> None:
    text = read_ref("formats")
    lowered = text.lower()

    for fmt in FORMATS:
        assert re.search(rf"(?m)^## {re.escape(fmt)}\b", text), (
            f"formats.md needs a ## {fmt} section"
        )

    assert "ponto de partida" in lowered, "the skeleton must be a starting point"
    assert "starter page" in lowered, "the generator output must be named a starter page"
    assert "molde" in lowered, "formats.md must say the skeleton is not a mold"
    assert re.search(r"(?i)sem\s+n[úu]mero\s+fixo\s+de\s+slides", text), (
        "deck must not impose a fixed slide count"
    )
    assert not re.search(r"(?i)\b(seis|six|6)\s+slides?\b", text), (
        "formats.md must not keep the fixed six-slide rule"
    )

    for direction in ("editorial", "structured", "poster", "minimal"):
        assert direction in lowered, f"composition direction {direction!r} must appear"
    assert "composition" in lowered and "direção" in lowered, (
        "composition.direction must guide section, grid and rhythm choices"
    )

    for term in ("topbar", "sidebar", "dialog", "skip link"):
        assert term in lowered, f"app details must include {term}"
    for term in ("logo", "cores", "mini cases", "prova"):
        assert term in lowered, f"brand-kit details must include {term}"
    for term in ("cartaz", "convite", "menu"):
        assert term in lowered, f"blank details must include {term}"

    for term in ("1280", "1080", "375"):
        assert term in text, f"formats.md must state the {term} stage/viewport"
    for job in ("vende", "explica", "apresenta", "interrompe", "opera"):
        assert job in lowered, f"the format map must state that the format {job}"
    assert "mockup" in lowered, "social must be described as a mockup, not an export"
    assert "[placeholder" in text and "Nota" in text, (
        "unresolved copy must stay a placeholder and be listed in the Nota"
    )


def test_voice_is_brand_agnostic() -> None:
    text = read_ref("voice")
    lowered = text.lower()

    assert re.search(r"(?i)agn[óo]stic", text), (
        "voice.md must present a brand-agnostic tone framework"
    )
    assert re.search(r"(?i)derivad\w*\s+dos\s+atributos", text), (
        "tones must be derived from the approved attributes"
    )

    tones = re.findall(r"(?m)^### Tom \d+\b", text)
    assert 3 <= len(tones) <= 4, f"expected 3-4 tones, found {len(tones)}"
    for token in ("SOMOS", "NÃO SOMOS", "Certo", "Errado"):
        assert token in text, f"voice.md must use the label {token}"
    assert text.count("**Direcionamento:**") == len(tones), (
        "each tone needs a Direcionamento line"
    )

    contexts = ("consultoria", "app de saúde", "museu", "perfum", "pizzaria")
    found = [context for context in contexts if context in lowered]
    assert len(found) >= 4, (
        "examples must span different contexts, "
        f"found {len(found)} of {len(contexts)}"
    )
    assert lowered.count("forno & brasa") <= 1, (
        "voice.md cannot depend on a single brand for every example"
    )

    for token in ("emoji", "inclusiv", "estrangeir", "2ª pessoa"):
        assert token in lowered, f"voice.md must state the {token} rule"
    assert re.search(r"(?m)^\|.*Canal.*Tom", text), (
        "voice.md needs a channel -> tone table"
    )

    assert "[placeholder" in text, "missing copy must stay a [placeholder]"
    assert re.search(r"(?i)\b(nota|note)\b", text), (
        "unresolved copy must be listed in the delivery note"
    )
    assert re.search(r"(?i)(invent|fabrica)", text), (
        "voice.md must forbid invented facts"
    )


def test_logo_keeps_cascade() -> None:
    text = read_ref("logo")
    lowered = text.lower()

    positions = {}
    for variant in ("C", "B", "A"):
        match = re.search(rf"(?m)^### {variant}\b", text)
        assert match, f"logo.md needs a ### {variant} section"
        positions[variant] = match.start()
    assert positions["C"] < positions["B"] < positions["A"], (
        "the cascade must be documented C -> B -> A"
    )

    assert "16px" in text, "logo.md must keep the 16px test"
    assert "currentColor" in text, "the symbol must use currentColor"
    assert "--b-space-1" in text, "the breathing area must use --b-space-1"
    assert re.search(r"\bS\b", text), "logo.md must name the breathing unit S"
    assert re.search(r"(?i)(unidade de espa[çc]amento|spacing unit)", text), (
        "breathing area S must follow the configured unit (4 or 8)"
    )
    assert re.search(r"(?i)light.*dark|claro.*escuro", text), (
        "the logo must be tested on light and dark"
    )
    assert "monogram" in lowered and "wordmark" in lowered
    assert re.search(r"degrade|degrada", lowered), (
        "a detailed idea must explicitly degrade"
    )
    assert "bg-primary" in text and "text-on-primary" in text, (
        "a monogram tile must use bg-primary + text-on-primary"
    )
    assert "detailed" in lowered or "illustrativ" in lowered or "ilustrad" in lowered, (
        "logo.md must cover the detailed illustrative idea"
    )


def test_references_have_no_v1_or_product_flavor() -> None:
    for name in REFERENCE_NAMES:
        text = read_ref(name)
        lowered = text.lower()
        for banned in ("--flavor", "data-flavor", "gc-", "gupy"):
            assert banned not in lowered, f"{name}.md still mentions {banned!r}"
        assert not re.search(r'(?i)"version"\s*:\s*1\b', text), (
            f"{name}.md still documents the v1 version value"
        )
        assert not re.search(r"(?i)version:\s*1\b", text), (
            f"{name}.md still documents the v1 version value"
        )
        assert "allowed_pairs" not in lowered, f"{name}.md still documents allowed_pairs"
        assert "colors.secondary" not in lowered, f"{name}.md still has v1 colour keys"
        assert "colors.primary" not in lowered, f"{name}.md still has v1 colour keys"

    assert '"version": 2' in read_ref("tokens"), "tokens.md must pin the v2 contract"


if __name__ == "__main__":
    failures = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
            else:
                print(f"PASS {name}")
    raise SystemExit(1 if failures else 0)
