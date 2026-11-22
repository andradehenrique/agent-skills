"""Tests for the v2 brand checker.

Run with the stdlib runner (pytest is not required)::

    python3 skills/brand-engine/tests/test_check_page.py

The fixtures are minimal, hand-written v2 pages: the generated theme tokens,
the logo sprite, one <main> and one <h1>. Each test mutates one thing and
asserts the matching rule fires. The generator (``new_page.py``) is not used
here so the checker contract stays independent of the generator rewrite.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
BRAND = FIXTURES / "forno-e-brasa.brand.json"

sys.path.insert(0, str(SCRIPTS))

try:  # RED phase: the v2 checker does not exist yet.
    import check_page as checking
except ImportError as exc:  # pragma: no cover - only on the first red run
    checking = None  # type: ignore[assignment]
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None

# The twelve generated steps for base 16 / ratio 1.25 (build_theme.py).
TYPE_STEPS = (
    ("xs", 10),
    ("sm", 13),
    ("base", 16),
    ("lg", 20),
    ("xl", 25),
    ("2xl", 31),
    ("3xl", 39),
    ("4xl", 49),
    ("5xl", 61),
    ("6xl", 76),
    ("7xl", 95),
    ("8xl", 119),
)

SPRITE = (
    '<div hidden aria-hidden="true" data-logo-sprite>'
    '<svg><symbol id="be-mark" viewBox="0 0 32 32"><path d="M4 28V14h24v14H4Z"/></symbol></svg>'
    "</div>"
)
BREATHING = (
    "<!-- logo: breathing area / área de respiro = S (var(--b-space-1), 8px) "
    "em todos os lados. -->"
)
SKIP_LINK = '<a href="#conteudo" class="be-skip">Pular para o conteúdo</a>'
THEME_TOGGLE = (
    '<button type="button" data-theme-toggle aria-label="Alternar tema" '
    'aria-pressed="false" class="inline-flex size-6 items-center justify-center '
    'rounded-full border border-line-input bg-surface text-fg-muted '
    'hover:bg-surface-muted hover:text-fg">Tema</button>'
)


def checker():
    assert checking is not None, f"check_page not defined ({IMPORT_ERROR})"
    return checking


def tokens(
    *,
    unit: int = 8,
    dark_block: bool = True,
    gradient: bool = False,
    extra_type: tuple[tuple[str, int], ...] = (),
) -> str:
    lines = [":root {", f"  --b-unit: {unit}px;"]
    for name, size in TYPE_STEPS + extra_type:
        lines.append(f"  --b-text-{name}: {size}px;")
    for step in range(0, 17):
        lines.append(f"  --b-space-{step}: {step * unit}px;")
    lines.append("  --b-radius-md: 8px;")
    lines.append("  --b-shadow-1: 0 1px 2px rgba(0, 0, 0, 0.06);")
    if gradient:
        # Any angle and any stops: v2 has no 45deg / 50-50 requirement.
        lines.append(
            "  --b-gradient: linear-gradient(120deg, #123456 0%, #654321 100%);"
        )
    lines.append("}")
    if dark_block:
        lines.append(
            '[data-theme="dark"] { color-scheme: dark; --b-canvas: #101010; }'
        )
    return "\n".join(lines)


def build(
    content: str = '<p class="mt-4 text-base text-fg-muted">Texto de apoio.</p>',
    *,
    fmt: str = "blank",
    unit: int = 8,
    theme: str = "both",
    toggle: bool = True,
    locked: str = "",
    gradient: bool = False,
    extra_type: tuple[tuple[str, int], ...] = (),
    head_extra: str = "",
    sprite: bool = True,
    breathing: bool = True,
) -> str:
    """Build a clean v2 page around ``content`` inside <main>."""

    assert theme in {"light", "dark", "both"}
    html_attrs = ' data-theme="dark"' if theme == "dark" else ""
    if locked:
        html_attrs += f' data-theme-lock="{locked}"'
    parts = [
        "<!doctype html>",
        f'<html lang="pt-BR"{html_attrs}>',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>Fixture v2</title>",
        "<style>",
        tokens(
            unit=unit,
            dark_block=theme == "both",
            gradient=gradient,
            extra_type=extra_type,
        ),
        "</style>",
        head_extra,
        "</head>",
        f'<body class="min-h-svh bg-canvas font-sans text-fg antialiased" data-format="{fmt}">',
    ]
    if sprite:
        parts.append(SPRITE)
    parts.append(SKIP_LINK)
    if toggle:
        parts.append(THEME_TOGGLE)
    if breathing:
        parts.append(BREATHING)
    parts.extend(
        [
            '<main id="conteudo" class="mx-auto max-w-3xl px-4 py-8">',
            '<h1 class="text-3xl font-semibold">Página</h1>',
            content,
            "</main>",
            "</body>",
            "</html>",
        ]
    )
    return "\n".join(parts)


def write(tmp: str | Path, name: str, html: str) -> str:
    path = Path(tmp) / name
    path.write_text(html, encoding="utf-8")
    return str(path)


def findings(html: str) -> list[str]:
    return checker().check_html(html)


def errors(html: str) -> list[str]:
    return [item for item in findings(html) if item.startswith("ERROR")]


def has(html: str, rule: str, severity: str = "ERROR") -> list[str]:
    return [
        item
        for item in findings(html)
        if item.startswith(severity) and f"[{rule}]" in item
    ]


def assert_rule(html: str, rule: str, severity: str = "ERROR") -> str:
    matches = has(html, rule, severity)
    assert matches, f"expected {severity} [{rule}], got {findings(html)}"
    return matches[0]


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------


def test_accepts_v2_page() -> None:
    clean = build(
        '<div class="rounded-md border border-line bg-surface p-4 text-fg">'
        "Cartão</div>"
    )
    assert findings(clean) == [], findings(clean)


def test_rejects_bare_hex() -> None:
    assert_rule(
        build('<div class="bg-[#A6402F]">x</div>'),
        "tokens",
    )
    assert_rule(build('<div style="color:#A6402F">x</div>'), "tokens")


def test_rejects_palette_utility() -> None:
    assert_rule(build('<div class="bg-blue-600 text-white">x</div>'), "tokens")


def test_rejects_arbitrary_color() -> None:
    assert_rule(build('<div class="bg-[rgb(10,10,10)]">x</div>'), "tokens")


def test_rejects_raw_color_in_style_block() -> None:
    assert_rule(
        build(
            "",
            head_extra="<style>.evil{color:#ff0000;background:rgb(0,255,0)}</style>",
        ),
        "tokens",
    )
    assert_rule(
        build("", head_extra="<style>.evil{background:red}</style>"),
        "tokens",
    )
    assert_rule(
        build("", head_extra="<style>:root{--evil:#ff0000}</style>"),
        "tokens",
    )
    assert_rule(
        build("", head_extra="<style>.button{@apply bg-blue-600 text-white}</style>"),
        "tokens",
    )


def test_generated_theme_style_blocks_are_ignored() -> None:
    # The token definitions themselves contain hex/rgba values.
    html = build(gradient=True)
    assert not has(html, "tokens"), findings(html)


def test_accepts_feedback_and_chart_tokens() -> None:
    content = (
        '<p class="mt-2 bg-success-soft p-2 text-success">Salvo</p>'
        '<p class="mt-2 bg-warning text-on-warning">Atenção</p>'
        '<div class="mt-2 h-4 bg-chart-1">Dado</div>'
        '<div class="mt-2 h-4 bg-chart-8">Dado</div>'
    )
    assert findings(build(content)) == [], findings(build(content))


# ---------------------------------------------------------------------------
# Type scale (inferred from --b-text-*)
# ---------------------------------------------------------------------------


def test_rejects_off_scale_text() -> None:
    assert_rule(build('<p class="text-9xl">Grande</p>'), "type-scale")


def test_accepts_embedded_type_steps() -> None:
    default = build('<p class="text-7xl">Grande</p>')
    assert not has(default, "type-scale"), findings(default)

    embedded = build(
        '<p class="text-9xl">Grande</p>',
        extra_type=(("9xl", 149),),
    )
    assert not has(embedded, "type-scale"), findings(embedded)


def test_rejects_arbitrary_type_size() -> None:
    assert_rule(build('<p class="text-[18px]">x</p>'), "type-scale")


# ---------------------------------------------------------------------------
# Spacing (unit 4/8, inferred from --b-unit)
# ---------------------------------------------------------------------------


def test_accepts_unit_4_spacing() -> None:
    content = '<div class="mt-9 gap-7 p-5">x</div>'
    assert findings(build(content, unit=4)) == [], findings(build(content, unit=4))


def test_rejects_off_unit_spacing() -> None:
    assert_rule(build('<div class="p-[6px]">x</div>', unit=4), "spacing")
    assert_rule(build('<div class="p-5">x</div>'), "spacing")
    assert_rule(build('<div class="p-[20px]">x</div>'), "spacing")

    for unit, length in ((8, "24px"), (4, "20px")):
        clean = build(f'<div class="p-[{length}]">x</div>', unit=unit)
        assert not has(clean, "spacing"), (unit, findings(clean))


# ---------------------------------------------------------------------------
# Gradient (optional, inferred from --b-gradient)
# ---------------------------------------------------------------------------


def test_optional_gradient_absent_ok() -> None:
    assert findings(build()) == [], findings(build())


def test_ad_hoc_gradient_rejected() -> None:
    assert_rule(
        build('<div class="bg-gradient-to-r from-primary to-accent">x</div>'),
        "gradient",
    )
    assert_rule(
        build(
            "",
            head_extra="<style>.x{background-image: linear-gradient(90deg, red, blue)}</style>",
        ),
        "gradient",
    )
    assert_rule(
        build('<div style="background: linear-gradient(90deg, red, blue)">x</div>'),
        "gradient",
    )
    assert_rule(build('<div class="bg-grad-brand">x</div>'), "gradient")


def test_brand_gradient_utility_allowed_when_defined() -> None:
    html = build('<div class="bg-grad-brand p-4">x</div>', gradient=True)
    assert not has(html, "gradient"), findings(html)


# ---------------------------------------------------------------------------
# Theme modes
# ---------------------------------------------------------------------------


def test_dark_only_no_toggle_required() -> None:
    html = build(theme="dark", toggle=False)
    assert not has(html, "structure"), findings(html)


def test_dark_both_requires_toggle() -> None:
    html = build(theme="both", toggle=False)
    assert_rule(html, "structure")

    clean = build(theme="both", toggle=True)
    assert not has(clean, "structure"), findings(clean)


def test_theme_lock_removes_toggle_requirement() -> None:
    html = build(theme="both", toggle=False, locked="light")
    assert not has(html, "structure"), findings(html)


def test_dark_presence_requires_a_token_block() -> None:
    """Base-shell selectors and the Tailwind custom variant are not dark mode."""

    base_shell = (
        "<style>"
        "@custom-variant dark (&:where([data-theme=dark], [data-theme=dark] *));"
        '[data-theme="dark"] [data-theme-toggle] { display: none; }'
        "</style>"
    )
    dark_only = build(theme="dark", toggle=False, head_extra=base_shell)
    assert not has(dark_only, "structure"), findings(dark_only)

    generated_block = (
        '<style>[data-theme="dark"] { color-scheme: dark; '
        "--b-canvas: #101010; --b-fg: #F5F5F5; }</style>"
    )
    both = build(theme="light", toggle=False, head_extra=generated_block)
    assert_rule(both, "structure")


# ---------------------------------------------------------------------------
# Icons and images
# ---------------------------------------------------------------------------


def test_iconify_icon_needs_label_or_hidden() -> None:
    bare = '<iconify-icon icon="fluent:check-24-regular"></iconify-icon>'
    assert_rule(build(bare), "icons")

    hidden = (
        '<iconify-icon icon="fluent:check-24-regular" aria-hidden="true">'
        "</iconify-icon>"
    )
    assert not has(build(hidden), "icons"), findings(build(hidden))

    labelled = (
        '<iconify-icon icon="fluent:check-24-regular" aria-label="Concluído">'
        "</iconify-icon>"
    )
    assert not has(build(labelled), "icons"), findings(build(labelled))


def test_image_alt_required() -> None:
    assert_rule(build('<img src="data:image/png;base64,AA">'), "images")

    decorative = build('<img src="data:image/png;base64,AA" alt="">')
    assert not has(decorative, "images"), findings(decorative)

    described = build('<img src="data:image/png;base64,AA" alt="Forno a lenha">')
    assert not has(described, "images"), findings(described)


# ---------------------------------------------------------------------------
# Formats
# ---------------------------------------------------------------------------

APP_CONTENT = """
<div class="flex min-h-svh">
  <aside class="w-64 border-r border-line bg-surface p-4">
    <nav aria-label="Principal">
      <ul class="space-y-2">
        <li><a href="#conteudo" class="text-fg-muted">Visão geral</a></li>
        <li><a href="#conteudo" class="text-fg-muted">Pedidos</a></li>
      </ul>
    </nav>
  </aside>
  <div class="flex-1">
    <header class="border-b border-line bg-surface p-4">
      <h2 class="text-lg font-semibold">Operação</h2>
      <label for="busca" class="text-fg-muted">Buscar</label>
      <input id="busca" type="text" class="border border-line-input bg-surface p-2 text-fg">
    </header>
    <section class="p-6">
      <h2 class="text-xl font-semibold">Pedidos de hoje</h2>
      <table class="w-full text-left">
        <caption class="text-sm text-fg-muted">Pedidos do dia</caption>
        <thead>
          <tr>
            <th scope="col" class="border-b border-line p-2">Cliente</th>
            <th scope="col" class="border-b border-line p-2">Status</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td class="border-b border-line p-2">Ana</td>
            <td class="border-b border-line p-2">Pronto</td>
          </tr>
        </tbody>
      </table>
      <div class="mt-6 rounded-md border border-line bg-surface p-6 text-center">
        <p class="text-fg-muted">Nenhum pedido pendente.</p>
      </div>
      <img src="data:image/png;base64,AA" alt="" class="mt-4 size-8 rounded-full">
    </section>
  </div>
</div>
"""

BRAND_KIT_CONTENT = """
<section class="mt-8">
  <h2 class="text-2xl font-semibold">Paleta</h2>
  <ul class="mt-4 grid grid-cols-2 gap-4">
    <li class="rounded-md border border-line bg-surface p-4"><span class="text-fg">Primária</span></li>
    <li class="rounded-md border border-line bg-primary-soft p-4"><span class="text-on-primary-soft">Primária suave</span></li>
    <li class="rounded-md border border-line bg-success-soft p-4"><span class="text-success">Sucesso</span></li>
    <li class="rounded-md border border-line bg-info-soft p-4"><span class="text-info">Informação</span></li>
  </ul>
</section>
<section class="mt-8">
  <h2 class="text-2xl font-semibold">Dados</h2>
  <div class="mt-4 flex gap-2">
    <div class="h-4 w-16 bg-chart-1"></div>
    <div class="h-4 w-16 bg-chart-2"></div>
    <div class="h-4 w-16 bg-chart-3"></div>
  </div>
</section>
<section class="mt-8">
  <h2 class="text-2xl font-semibold">Tipografia</h2>
  <p class="mt-4 text-7xl font-semibold">Aa</p>
  <p class="mt-2 text-base text-fg-muted">Texto de leitura.</p>
</section>
<section class="mt-8">
  <h2 class="text-2xl font-semibold">Componentes</h2>
  <div class="mt-4 flex gap-2">
    <a href="#conteudo" class="rounded-md bg-primary px-4 py-2 text-on-primary hover:bg-primary-hover">Ação</a>
    <button type="button" class="rounded-md border border-line-input px-4 py-2 text-fg">Secundária</button>
  </div>
  <table class="mt-4 w-full text-left">
    <caption class="text-sm text-fg-muted">Amostra de tabela</caption>
    <thead><tr><th scope="col" class="border-b border-line p-2">Item</th><th scope="col" class="border-b border-line p-2">Valor</th></tr></thead>
    <tbody><tr><td class="border-b border-line p-2">Massa</td><td class="border-b border-line p-2">01</td></tr></tbody>
  </table>
  <div class="mt-4 rounded-md border border-line bg-surface p-6 text-center">
    <iconify-icon icon="fluent:folder-24-regular" aria-hidden="true"></iconify-icon>
    <p class="mt-2 text-fg-muted">Nada por aqui ainda.</p>
  </div>
</section>
"""


def test_app_format_passes() -> None:
    html = build(APP_CONTENT, fmt="app", sprite=False, breathing=False)
    assert findings(html) == [], findings(html)


def test_brand_kit_format_passes() -> None:
    html = build(BRAND_KIT_CONTENT, fmt="brand-kit")
    assert findings(html) == [], findings(html)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "check_page.py"), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_checker_cli_reports_and_exits() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        clean = write(tmp, "clean.html", build())
        result = run_cli(clean)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "ok:" in result.stdout
        assert "Traceback" not in result.stderr

        broken = write(tmp, "broken.html", build('<div class="p-5">x</div>'))
        failed = run_cli(broken)
        assert failed.returncode == 1
        assert "ERROR [spacing]" in failed.stdout
        assert "Traceback" not in failed.stderr

        missing = run_cli(str(Path(tmp) / "nope.html"))
        assert missing.returncode == 2
        assert "Traceback" not in missing.stderr
        assert "check_page:" in missing.stderr

        warns = write(
            tmp,
            "warns.html",
            build(
                '<table><caption>T</caption><thead><tr><th>H</th></tr></thead></table>',
                fmt="report",
            ),
        )
        lenient = run_cli(warns)
        assert lenient.returncode == 0, lenient.stdout + lenient.stderr
        assert "WARN [table]" in lenient.stdout

        strict = run_cli(warns, "--strict")
        assert strict.returncode == 1
        assert "WARN [table]" in strict.stdout


def test_cli_brand_flag_is_optional_and_validates() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        clean = write(tmp, "clean.html", build())

        valid = run_cli(clean, "--brand", str(BRAND))
        assert valid.returncode == 0, valid.stdout + valid.stderr

        invalid = run_cli(clean, "--brand", str(Path(tmp) / "missing.json"))
        assert invalid.returncode == 1
        assert "ERROR [brand]" in invalid.stdout
        assert "Traceback" not in invalid.stderr

        api = checker().check_page(clean, BRAND)
        assert api == [], api


def test_brand_language_must_match_html_lang() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        mismatched = build().replace('lang="pt-BR"', 'lang="en"')
        page = write(tmp, "lang.html", mismatched)
        matches = [item for item in checker().check_page(page, BRAND) if "[language]" in item]
        assert matches, "html lang disagreeing with brand language must be flagged"

        same = write(tmp, "same.html", build())
        assert checker().check_page(same, BRAND) == []


def test_missing_html_lang_is_an_error() -> None:
    assert_rule(build().replace(' lang="pt-BR"', ""), "a11y")


if __name__ == "__main__":
    failures = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
            except Exception as exc:  # noqa: BLE001 - stdlib runner reports every failure
                failures += 1
                print(f"FAIL {name}: {type(exc).__name__}: {exc}")
            else:
                print(f"PASS {name}")
    raise SystemExit(1 if failures else 0)
