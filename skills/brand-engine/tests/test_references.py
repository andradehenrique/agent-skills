"""Contract tests for the brand-engine references.

The references are the executable documentation the skill points to: they must
resolve from ``SKILL.md``, stay lean, and describe what Tasks 2-4 actually
implement. Run with pytest
(``python3 -m pytest skills/brand-engine/tests/test_references.py``) or directly
with Python when pytest is unavailable
(``python3 skills/brand-engine/tests/test_references.py``).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
REFS = ROOT / "references"
REFERENCE_NAMES = ("discovery", "tokens", "formats", "voice", "logo")


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


def test_discovery_has_5_to_8_questions_and_2_to_3_routes() -> None:
    text = read_ref("discovery")
    questions = re.findall(r"(?m)^### P\d+\b", text)
    routes = re.findall(r"(?m)^### Rota [A-Z]\b", text)
    assert 5 <= len(questions) <= 8, f"expected 5-8 questions, found {len(questions)}"
    assert 2 <= len(routes) <= 3, f"expected 2-3 routes, found {len(routes)}"

    for field in ("**Ideia:**", "**Paleta:**", "**Tipografia:**", "**Por que:**"):
        assert text.count(field) == len(routes), (
            f"each route needs {field} ({text.count(field)} found for {len(routes)} routes)"
        )

    lowered = text.lower()
    assert "text-first" in lowered or "texto primeiro" in lowered
    assert "workdir" in lowered or "working directory" in lowered


def test_voice_has_somos_nao_somos_plus_right_wrong() -> None:
    text = read_ref("voice")
    tones = re.findall(r"(?m)^### Tom \d+\b", text)
    assert 3 <= len(tones) <= 4, f"expected 3-4 tones, found {len(tones)}"

    for token in ("SOMOS", "NÃO SOMOS", "Certo", "Errado"):
        assert token in text, f"voice.md must use the Sebrae label {token}"
    assert text.count("**Direcionamento:**") == len(tones), (
        "each tone needs a Direcionamento line"
    )

    lowered = text.lower()
    for token in ("emoji", "inclusiv", "estrangeir", "2ª pessoa"):
        assert token in lowered, f"voice.md must state the {token} rule"
    assert re.search(r"(?m)^\|.*Canal.*Tom", text), (
        "voice.md needs a channel -> tone table"
    )
    assert "[placeholder]" in text
    assert re.search(r"(?i)\b(nota|note)\b", text)


def test_logo_defines_cascade_c_to_b_to_a_with_16px_rule() -> None:
    text = read_ref("logo")
    positions = {}
    for variant in ("C", "B", "A"):
        match = re.search(rf"(?m)^### {variant}\b", text)
        assert match, f"logo.md needs a ### {variant} section"
        positions[variant] = match.start()
    assert positions["C"] < positions["B"] < positions["A"], (
        "the cascade must be documented C -> B -> A"
    )

    assert "16px" in text
    assert "currentColor" in text
    assert "--b-space-1" in text
    assert re.search(r"\bS\b", text), "logo.md must name the breathing unit S"
    assert re.search(r"(?i)light.*dark|claro.*escuro", text)
    lowered = text.lower()
    assert "monogram" in lowered and "wordmark" in lowered


def test_corrupt_inspiration_image_falls_back_to_text_only() -> None:
    text = read_ref("discovery")
    lowered = text.lower()
    assert re.search(r"corrupt|unreadable|ileg[ií]vel|corromp", lowered), (
        "discovery.md must handle a corrupt image"
    )
    assert re.search(r"text-only|texto apenas|s[oó] texto|sem imagem", lowered), (
        "a corrupt image must fall back to text-only discovery"
    )
    assert re.search(r"never crash|n[aã]o quebra|nunca quebra|one line|uma linha", lowered), (
        "a corrupt image must be ignored with one line, never crash"
    )


def test_detailed_logo_idea_degrades_to_monogram_or_wordmark() -> None:
    text = read_ref("logo")
    lowered = text.lower()
    assert re.search(r"detailed|illustrative|ilustrad", lowered), (
        "logo.md must cover the detailed illustrative idea"
    )
    assert "16px" in text
    assert re.search(r"degrade|degrada", lowered), (
        "a detailed idea must explicitly degrade"
    )
    assert "monogram" in lowered and "wordmark" in lowered


def test_copy_without_numbers_keeps_placeholder_and_note() -> None:
    voice = read_ref("voice")
    assert "[placeholder]" in voice
    assert re.search(r"(?i)\b(nota|note)\b", voice), (
        "unresolved copy must be listed in the delivery note"
    )
    assert re.search(r"(?i)(invent|fabrica)", voice), (
        "voice.md must forbid invented facts"
    )

    formats = read_ref("formats")
    assert "[placeholder]" in formats
    assert re.search(r"(?i)\b(nota|note)\b", formats)
    assert "Forno & Brasa" in formats


def test_tokens_matches_the_task_2_api_and_limits() -> None:
    text = read_ref("tokens")
    for fragment in (
        "build_theme(brand_path, out_dir, force=False)",
        "ThemeBuild(theme_css, tailwind_theme_css)",
        "load_brand(brand_path)",
        "render_theme(brand)",
        "resolve_brand_path(brand_flag=None, cwd=None)",
        "missing_brand_behavior()",
        "contrast_ratio(foreground, background)",
        "BrandError",
        "--b-color-<slug>",
        "primary-hover",
        "line-input",
        "allowed_pairs",
    ):
        assert fragment in text, f"tokens.md must document {fragment!r}"

    lowered = text.lower()
    assert "slug" in lowered and ("case-insensitive" in lowered or "casefold" in lowered)
    assert "3:1" in text and "4.5:1" in text
    assert "45" in text and ("two stops" in lowered or "dois stops" in lowered)
    assert "8px" in text


def test_formats_cover_six_formats_and_their_jobs() -> None:
    text = read_ref("formats")
    for fmt in ("manual", "onepage", "deck", "report", "social", "blank"):
        assert re.search(rf"(?m)^## {fmt}\b", text), (
            f"formats.md needs a ## {fmt} section"
        )
    lowered = text.lower()
    for job in ("sells", "explains", "presents", "interrupts"):
        assert job in lowered, f"formats.md must state that the format {job}"
    assert "1280" in text and "1080" in text
    assert "caption" in lowered and "scope" in lowered


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
