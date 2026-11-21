#!/usr/bin/env python3
"""Build an axe-core copy of a brand-engine page to audit rendered contrast.

The delivered page is never modified. The copy loads axe-core (cdnjs), waits
1.5s for the Tailwind browser CDN and webfonts, then runs the WCAG 2.2 A/AA
plus best-practice rules in every available theme and writes the result to
the top of the page (``<pre id="axe-out">``) and to the console.

Themes are fixed when the copy is generated: a page locked with
``data-theme-lock`` is audited once; a page with both themes is audited in
light and dark.

Usage:
  python3 scripts/axe_copy.py pagina.html            # writes pagina.axe.html
  python3 scripts/axe_copy.py pagina.html --out /tmp/x.html

Open the copy in a browser (ideally over http://, not file://), read #axe-out,
and delete the copy when done.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

AXE = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"]

RUNNER = r"""
<script src="%s"></script>
<script>
(async function () {
  await new Promise(function (r) { setTimeout(r, 1500); });   // Tailwind CDN + fonts
  var root = document.documentElement, res = {};
  var opts = { runOnly: { type: "tag", values: %s }, resultTypes: ["violations"] };
  var themes = %s;
  for (var k = 0; k < themes.length; k++) {
    root.setAttribute("data-theme", themes[k]);
    await new Promise(function (r) { setTimeout(r, 400); });
    var r = await axe.run(document, opts);
    res[themes[k]] = r.violations.map(function (v) {
      return v.impact + " " + v.id + " (" + v.nodes.length + "): " + v.help + " -> " + v.nodes.slice(0, 3).map(function (n) {
        var d = n.any[0] && n.any[0].data;
        return n.target.join(" ") + (d && d.contrastRatio ? " [" + d.contrastRatio + ":1 " + d.fgColor + " sobre " + d.bgColor + "]" : "");
      }).join(" | ");
    });
  }
  var total = Object.keys(res).reduce(function (s, t) { return s + res[t].length; }, 0);
  var pre = document.createElement("pre");
  pre.id = "axe-out";   // report: #axe-out
  pre.style.cssText = "white-space:pre-wrap;font:12px/1.4 ui-monospace,monospace;padding:12px;margin:0;background:#fff;color:#000;border-bottom:2px solid #000";
  pre.textContent = "AXE " + (total ? total + " violação(ões)" : "ok") + " [" + themes.join(", ") + "]\n" + JSON.stringify(res, null, 1);
  document.body.prepend(pre);
  console.log(pre.textContent);
})();
</script>
"""

_HTML_TAG = re.compile(r"<html\b([^>]*)>", re.IGNORECASE | re.DOTALL)
_ATTRIBUTE = re.compile(
    r"""([\w:-]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?"""
)


def _html_attributes(html: str) -> dict[str, str]:
    """Attributes on the root ``<html>`` element, lowercased by name."""
    match = _HTML_TAG.search(html)
    if not match:
        return {}
    attributes: dict[str, str] = {}
    for found in _ATTRIBUTE.finditer(match.group(1)):
        name = found.group(1).lower()
        value = found.group(2)
        if value is None:
            value = found.group(3)
        if value is None:
            value = found.group(4)
        attributes[name] = value or ""
    return attributes


def themes_for(html: str) -> list[str]:
    """Themes the copy should audit, decided from the page shell."""
    attributes = _html_attributes(html)
    if "data-theme-lock" in attributes:
        lock = attributes["data-theme-lock"].strip().lower()
        if lock in ("light", "dark"):
            return [lock]
        current = attributes.get("data-theme", "").strip().lower()
        return [current] if current in ("light", "dark") else ["light"]
    return ["light", "dark"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("page", help="HTML page to copy")
    parser.add_argument("--out", help="output path (default: <page>.axe.html)")
    args = parser.parse_args(argv)

    source = pathlib.Path(args.page)
    if not source.is_file():
        print(f"error: page not found: {source}", file=sys.stderr)
        return 1

    out = pathlib.Path(args.out) if args.out else source.with_suffix(".axe.html")
    html = source.read_text(encoding="utf-8")
    runner = RUNNER % (AXE, json.dumps(TAGS), json.dumps(themes_for(html)))

    if "</body>" in html:
        html = html.replace("</body>", runner + "</body>", 1)
    elif "</html>" in html:
        html = html.replace("</html>", runner + "</html>", 1)
    else:
        html += runner

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"ok: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
