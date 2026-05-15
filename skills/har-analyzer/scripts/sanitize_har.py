#!/usr/bin/env python3
"""
Sanitize and chunk a .har file for safe LLM analysis.

Why this script exists:
- Raw HARs are huge (binaries, base64 images, multi-MB JSON payloads). Feeding them
  directly to an LLM blows the context window and triggers hallucinations.
- HARs leak secrets (cookies, JWTs in responses, signed S3/WebSocket URLs, PII in
  querystrings). The script redacts these so they never reach an LLM.
- A deterministic pre-pass also computes objective metrics (counts, error rate,
  total transfer, top offenders, missing compression) so the LLM can spend its
  budget on interpretation instead of arithmetic.

Outputs (inside <output_dir>):
  chunk_api.json          - first-party XHR/Fetch entries
  chunk_static.json       - first-party documents/scripts/styles/images/fonts
  chunk_third_party.json  - everything from third-party domains
  summary.json            - deterministic metrics: counts, error rate, top slow,
                            top heavy, compression issues, security findings
"""
import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from urllib.parse import parse_qs, urlencode, urlparse

# ---------------------------------------------------------------------------
# Public Suffix List (compact subset). Used by base_domain() so we don't treat
# "gupy.com.br" as "com.br". For full PSL coverage install `tldextract`; this
# subset covers the suffixes we see in practice for Brazilian/global stacks.
# ---------------------------------------------------------------------------
MULTI_PART_SUFFIXES = {
    "com.br", "net.br", "org.br", "gov.br", "edu.br",
    "co.uk", "org.uk", "gov.uk", "ac.uk",
    "com.au", "co.jp", "co.kr", "co.in", "co.za",
    "com.mx", "com.ar", "com.co",
}

SENSITIVE_HEADERS = {
    "cookie", "set-cookie", "authorization", "proxy-authorization",
    "x-api-key", "x-auth-token", "x-csrf-token",
}

PII_QUERY_KEYS = {
    "email", "e-mail", "cpf", "cnpj", "rg", "phone", "telefone", "celular",
    "password", "senha", "token", "access_token", "id_token", "refresh_token",
    "code", "session", "sessionid", "auth", "apikey", "api_key", "signature",
}

TOKEN_LIKE_KEYS = {
    "access_token", "id_token", "refresh_token", "token", "jwt",
    "bearertoken", "sessiontoken", "authtoken",
}

# JWT pattern: three base64url segments separated by dots (>= 8 chars each)
JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")

TEXT_TRUNCATE_AT = 2000
NON_TEXT_MIME_PREFIXES = ("image/", "video/", "audio/", "font/", "application/pdf",
                          "application/octet-stream", "application/zip",
                          "application/x-protobuf")


def base_domain(host: str) -> str:
    """Return effective registrable domain (handles common multi-part TLDs)."""
    if not host:
        return ""
    parts = host.lower().split(".")
    if len(parts) <= 2:
        return host.lower()
    last_two = ".".join(parts[-2:])
    last_three = ".".join(parts[-3:])
    if last_two in MULTI_PART_SUFFIXES and len(parts) >= 3:
        return last_three
    return last_two


def har_int(value):
    """HAR uses -1 for unknown size/time; normalize for sums and rankings."""
    if value is None:
        return 0
    try:
        v = int(value)
    except (TypeError, ValueError):
        return 0
    return v if v >= 0 else 0


def hostname_from_url(url: str) -> str:
    """Hostname without port (unlike urlparse().netloc). Empty if not HTTP(S)/WS."""
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def slugify_for_dir(name: str) -> str:
    """Produce a filesystem-safe slug from a HAR filename (without extension)."""
    base = os.path.splitext(os.path.basename(name))[0]
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._-")
    return slug or "har"


def redact_string(value: str) -> str:
    """Mask JWTs and long opaque tokens inside any text blob."""
    if not isinstance(value, str) or not value:
        return value
    value = JWT_RE.sub("[REDACTED_JWT]", value)
    # Be conservative with the long-opaque rule: only mask if the surrounding
    # context already looks like a credential. Otherwise we'd nuke hashes that
    # are legit (e.g. CSS sourcemap hashes). We mask only when the string is
    # clearly a credential field (handled elsewhere) – here we just return.
    return value


def redact_headers(headers):
    out = []
    for h in headers or []:
        name = (h.get("name") or "").lower()
        if name in SENSITIVE_HEADERS:
            out.append({"name": h["name"], "value": "[REDACTED]"})
        else:
            out.append({"name": h.get("name"), "value": redact_string(h.get("value", ""))})
    return out


def redact_querystring(qs):
    out = []
    pii_hits = []
    for q in qs or []:
        name = (q.get("name") or "").lower()
        val = q.get("value", "")
        if name in PII_QUERY_KEYS or name in TOKEN_LIKE_KEYS:
            pii_hits.append(q.get("name"))
            out.append({"name": q.get("name"), "value": "[REDACTED]"})
        else:
            out.append({"name": q.get("name"), "value": redact_string(val)})
    return out, pii_hits


def redact_url(url: str):
    """Redact PII query params directly in the URL string for display."""
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query, keep_blank_values=True)
    except Exception:
        return url, []
    pii_hits = []
    pairs = []
    for k, vals in qs.items():
        kl = k.lower()
        if kl in PII_QUERY_KEYS or kl in TOKEN_LIKE_KEYS:
            pii_hits.append(k)
            for _ in vals:
                pairs.append((k, "[REDACTED]"))
        else:
            for v in vals:
                pairs.append((k, redact_string(v) if isinstance(v, str) else v))
    new_query = urlencode(pairs, doseq=True) if pairs else parsed.query
    rebuilt = parsed._replace(query=new_query).geturl()
    return rebuilt, pii_hits


def redact_post_data(raw):
    """Sanitize postData.text and postData.params (form fields often hold passwords)."""
    if not raw:
        return None
    out = dict(raw)
    if "text" in out:
        out["text"] = truncate(redact_response_text(out.get("text") or ""))
    params = out.get("params")
    if isinstance(params, list):
        new_params = []
        for p in params:
            if not isinstance(p, dict):
                new_params.append(p)
                continue
            name = (p.get("name") or "").lower()
            if name in PII_QUERY_KEYS or name in TOKEN_LIKE_KEYS:
                new_params.append({**p, "value": "[REDACTED]"})
            else:
                new_params.append({**p, "value": redact_string(p.get("value", ""))})
        out["params"] = new_params
    return out


def redact_response_text(text: str) -> str:
    """Mask JWTs and obvious credential JSON keys inside response bodies."""
    if not text:
        return text
    text = JWT_RE.sub("[REDACTED_JWT]", text)
    # Mask values for common credential keys when they appear in JSON-like text.
    pattern = re.compile(
        r'("(' + "|".join(TOKEN_LIKE_KEYS) + r')"\s*:\s*")([^"]+)(")',
        flags=re.IGNORECASE,
    )
    text = pattern.sub(lambda m: m.group(1) + "[REDACTED]" + m.group(4), text)
    return text


def truncate(text: str, limit: int = TEXT_TRUNCATE_AT) -> str:
    if text is None:
        return text
    if len(text) > limit:
        return text[:limit] + "... [TRUNCATED]"
    return text


def is_non_text_mime(mime: str) -> bool:
    if not mime:
        return False
    mime = mime.lower()
    return any(mime.startswith(p) for p in NON_TEXT_MIME_PREFIXES)


def get_header(headers, name):
    if not headers:
        return None
    name_l = name.lower()
    for h in headers:
        if (h.get("name") or "").lower() == name_l:
            return h.get("value")
    return None


def infer_resource_type(entry, mime: str) -> str:
    res_type = (entry.get("_resourceType") or "").lower()
    if res_type:
        return res_type
    mime_l = (mime or "").lower()
    if "json" in mime_l:
        return "xhr"
    if "javascript" in mime_l:
        return "script"
    if "css" in mime_l:
        return "stylesheet"
    if mime_l.startswith("image/"):
        return "image"
    if mime_l.startswith("font/") or "woff" in mime_l:
        return "font"
    if mime_l.startswith("text/html"):
        return "document"
    return "other"


def detect_missing_compression(mime, transfer_size, content_size, content_encoding):
    """Heuristic: text resource > 5KB without gzip/br/deflate is suspicious."""
    if not mime:
        return False
    mime_l = mime.lower()
    is_text = ("javascript" in mime_l or "css" in mime_l or "json" in mime_l
               or "xml" in mime_l or "html" in mime_l or mime_l.startswith("text/"))
    if not is_text:
        return False
    if (content_size or 0) < 5_000:
        return False
    enc = (content_encoding or "").lower()
    if any(x in enc for x in ("gzip", "br", "deflate", "zstd")):
        return False
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def process_har(har_path: str, output_dir: str):
    with open(har_path, "r", encoding="utf-8") as f:
        har = json.load(f)

    entries = har.get("log", {}).get("entries", [])
    if not entries:
        print("No entries found in HAR.", file=sys.stderr)
        sys.exit(1)

    # Infer main domain from the first 'document' request, fallback to most common.
    # Use hostname (no port) so first-party vs third-party matches Chrome/network reality.
    main_host = None
    for e in entries:
        if (e.get("_resourceType") or "").lower() == "document":
            main_host = hostname_from_url(e.get("request", {}).get("url", ""))
            break
    if not main_host:
        hosts = [hostname_from_url(e.get("request", {}).get("url", "")) for e in entries]
        hosts = [h for h in hosts if h]
        if hosts:
            main_host = Counter(hosts).most_common(1)[0][0]
    main_base = base_domain(main_host or "")

    chunk_api, chunk_static, chunk_third_party = [], [], []
    summary = {
        "har_file": os.path.basename(har_path),
        "main_domain": main_host,
        "main_base_domain": main_base,
        "totals": {"requests": 0, "first_party": 0, "third_party": 0,
                   "transfer_bytes": 0, "content_bytes": 0},
        "status_breakdown": Counter(),
        "errors_4xx_5xx": [],
        "top_slowest": [],
        "top_heaviest": [],
        "duplicate_requests": [],
        "missing_compression": [],
        "security_findings": {
            "pii_in_query": [],
            "permissive_cors": [],
            "tokens_in_response": [],
        },
        "third_party_domains": Counter(),
    }

    duplicates_tracker = defaultdict(int)
    by_speed = []
    by_size = []

    for entry in entries:
        req = entry.get("request", {}) or {}
        res = entry.get("response", {}) or {}
        content = res.get("content", {}) or {}
        url = req.get("url", "")
        host = hostname_from_url(url)
        host_base = base_domain(host)
        method = req.get("method", "GET")
        status = res.get("status", 0)
        mime = content.get("mimeType", "")
        content_size = har_int(content.get("size"))
        transfer_size = har_int(entry.get("_transferSize") or res.get("_transferSize"))
        time_ms = har_int(entry.get("time"))
        content_encoding = get_header(res.get("headers"), "content-encoding")
        cors = get_header(res.get("headers"), "access-control-allow-origin")
        res_type = infer_resource_type(entry, mime)
        is_third_party = bool(main_base) and host_base and host_base != main_base

        # ---- Sanitize ----
        clean_req_headers = redact_headers(req.get("headers"))
        clean_res_headers = redact_headers(res.get("headers"))
        clean_qs, qs_pii = redact_querystring(req.get("queryString"))
        clean_url, url_pii = redact_url(url)

        post_data = redact_post_data(req.get("postData"))

        clean_content = {"size": content_size, "mimeType": mime}
        if "text" in content:
            text = content.get("text") or ""
            # Drop binary base64 bodies entirely (they're useless for LLMs).
            if is_non_text_mime(mime) or content.get("encoding") == "base64":
                pass  # omit text
            else:
                clean_text = redact_response_text(text)
                clean_content["text"] = truncate(clean_text)
                # Detect tokens that survived in the response body
                if "[REDACTED_JWT]" in clean_text or "[REDACTED]" in clean_text:
                    summary["security_findings"]["tokens_in_response"].append(
                        {"url": clean_url, "status": status}
                    )

        slim = {
            "method": method,
            "url": clean_url,
            "status": status,
            "statusText": res.get("statusText"),
            "mimeType": mime,
            "resourceType": res_type,
            "host": host,
            "isThirdParty": is_third_party,
            "time_ms": round(float(time_ms), 1) if time_ms else 0.0,
            "transferSize": transfer_size,
            "contentSize": content_size,
            "contentEncoding": content_encoding,
            "requestHeaders": clean_req_headers,
            "responseHeaders": clean_res_headers,
            "queryString": clean_qs,
            "postData": post_data if post_data else None,
            "content": clean_content,
            "timings": entry.get("timings"),
        }

        # ---- Bin ----
        if is_third_party:
            chunk_third_party.append(slim)
            summary["third_party_domains"][host_base] += 1
        elif res_type in ("xhr", "fetch"):
            chunk_api.append(slim)
        else:
            chunk_static.append(slim)

        # ---- Aggregate ----
        summary["totals"]["requests"] += 1
        summary["totals"]["third_party" if is_third_party else "first_party"] += 1
        summary["totals"]["transfer_bytes"] += int(transfer_size or 0)
        summary["totals"]["content_bytes"] += int(content_size or 0)
        bucket = f"{(status // 100)}xx" if status else "0xx"
        summary["status_breakdown"][bucket] += 1

        if status and (400 <= status < 600):
            summary["errors_4xx_5xx"].append({
                "method": method, "url": clean_url, "status": status,
                "statusText": res.get("statusText"), "host": host,
            })

        by_speed.append((time_ms, method, clean_url, status, host))
        by_size.append((content_size or 0, mime, clean_url, host))

        if detect_missing_compression(mime, transfer_size, content_size, content_encoding):
            summary["missing_compression"].append({
                "url": clean_url, "mimeType": mime, "size": content_size,
                "encoding": content_encoding or "(none)",
            })

        if cors and cors.strip() == "*":
            summary["security_findings"]["permissive_cors"].append({
                "url": clean_url, "host": host,
            })

        if qs_pii or url_pii:
            summary["security_findings"]["pii_in_query"].append({
                "url": clean_url, "params": sorted(set(qs_pii + url_pii)),
            })

        # Duplicate detection: same method+URL (after PII redaction)
        duplicates_tracker[(method, clean_url)] += 1

    # ---- Finalize summary ----
    by_speed.sort(reverse=True)
    summary["top_slowest"] = [
        {"time_ms": round(t, 1), "method": m, "url": u, "status": s, "host": h}
        for (t, m, u, s, h) in by_speed[:10]
    ]
    by_size.sort(reverse=True)
    summary["top_heaviest"] = [
        {"size_bytes": sz, "mimeType": mt, "url": u, "host": h}
        for (sz, mt, u, h) in by_size[:10]
    ]
    summary["duplicate_requests"] = [
        {"method": k[0], "url": k[1], "count": v}
        for k, v in sorted(duplicates_tracker.items(), key=lambda x: -x[1])
        if v > 1
    ][:20]
    summary["status_breakdown"] = dict(summary["status_breakdown"])
    summary["third_party_domains"] = dict(
        sorted(summary["third_party_domains"].items(), key=lambda x: -x[1])
    )

    # ---- Write outputs ----
    os.makedirs(output_dir, exist_ok=True)

    def write_json(name, data):
        path = os.path.join(output_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return path, len(data) if isinstance(data, list) else None

    paths = []
    paths.append(write_json("chunk_api.json", chunk_api))
    paths.append(write_json("chunk_static.json", chunk_static))
    paths.append(write_json("chunk_third_party.json", chunk_third_party))
    paths.append(write_json("summary.json", summary))

    print(f"Main domain: {main_host} (base: {main_base})")
    print(f"Output directory: {output_dir}")
    for path, count in paths:
        suffix = f" ({count} entries)" if count is not None else ""
        print(f"  - {os.path.basename(path)}{suffix}")
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Sanitize and chunk a HAR file into LLM-safe pieces."
    )
    parser.add_argument("input_file", help="Path to the .har file")
    parser.add_argument(
        "output_dir",
        nargs="?",
        default=None,
        help="Optional. Directory for chunks. If omitted, a folder named "
             "'<harname>.chunks/' is created next to the .har file.",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.input_file):
        print(f"HAR file not found: {args.input_file}", file=sys.stderr)
        sys.exit(2)

    if args.output_dir:
        out = args.output_dir
    else:
        har_dir = os.path.dirname(os.path.abspath(args.input_file))
        out = os.path.join(har_dir, slugify_for_dir(args.input_file) + ".chunks")

    process_har(args.input_file, out)


if __name__ == "__main__":
    main()
