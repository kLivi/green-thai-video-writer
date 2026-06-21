#!/usr/bin/env python3
"""Post-publish verification gate for the green-thai-video-writer pipeline.

Fetches the just-published post from the WordPress REST API (context=edit, raw
content) and asserts it is actually CORRECT — not merely that a draft exists.
The scheduled runner's old success check only grepped the agent output for
"Post ID:", which let post 1052 through with broken (relative-src) inline images
and an initially-wrong featured image. This gate closes that hole.

Exit codes:
  0  all hard checks passed (warnings allowed)
  1  one or more hard checks failed  (a Discord failure embed is posted)
  2  could not run (auth/fetch error)

Usage:
  python3 scripts/verify_publish.py <post_id>
  python3 scripts/verify_publish.py <post_id> --require-chart
  python3 scripts/verify_publish.py <post_id> --no-discord
"""
import argparse
import re
import sys
from pathlib import Path

import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Reuse the vetted helpers from the main uploader (same pattern as fix_images.py).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from wordpress_upload import get_wp_config, WordPressClient, _notify_failure  # noqa: E402

MIN_WORDS = 600
MAX_WORDS = 4000
MIN_INLINE_IMAGES = 1

# Unrendered markers whose presence in the live body means the agent shipped a
# half-rendered article. NOTE: deliberately excludes the <!-- coverImage --> and
# <!-- chart --> HTML comments — those legitimately survive into published posts
# (clean_content strips the cover <img>, not the comment), so flagging them would
# false-positive on every normal post (verified against live posts 941/1040).
PLACEHOLDER_PATTERNS = [
    r"\[INTERNAL-LINK",
    r"\[IMAGE:",
    r"\[CHART:",
    r"\[FRAME\]",
    r"\[PLACEHOLDER",
]


class Check:
    def __init__(self, name, ok, detail="", severity="fail"):
        self.name = name
        self.ok = ok
        self.detail = detail
        self.severity = severity  # "fail" (hard) | "warn" (soft)

    def __str__(self):
        mark = "PASS" if self.ok else ("WARN" if self.severity == "warn" else "FAIL")
        tail = f"  — {self.detail}" if self.detail else ""
        return f"  [{mark}] {self.name}{tail}"


def _is_http(url: str) -> bool:
    return isinstance(url, str) and url.startswith(("http://", "https://"))


def _url_is_image(session, url: str) -> tuple[bool, str]:
    """True if url returns HTTP 200 with an image/* content-type."""
    try:
        r = session.get(url, timeout=20, stream=True, allow_redirects=True)
        ct = r.headers.get("Content-Type", "")
        r.close()
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}"
        if not ct.startswith("image/"):
            return False, f"content-type {ct or '(none)'}"
        return True, ""
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}"


def run_checks(client: WordPressClient, post: dict, require_chart: bool) -> list[Check]:
    content = (post.get("content") or {}).get("raw", "") or ""
    soup = BeautifulSoup(content, "html.parser")
    imgs = soup.find_all("img")
    inline_srcs = [(img.get("src") or "").strip() for img in imgs]
    results: list[Check] = []

    # 1. No relative/non-http inline img src — the exact 1052 bug. CRITICAL.
    bad = [s or "(empty)" for s in inline_srcs if not _is_http(s) and not s.startswith("data:")]
    results.append(Check(
        "inline img src are absolute http(s) URLs",
        ok=not bad,
        detail="" if not bad else f"{len(bad)} non-http src: {bad[:5]}",
    ))

    # 2. Every inline img resolves to a real image. CRITICAL.
    broken = []
    for s in inline_srcs:
        if not _is_http(s):
            continue  # already counted in check 1
        ok, why = _url_is_image(client.session, s)
        if not ok:
            broken.append(f"{s.split('/')[-1]} ({why})")
    results.append(Check(
        "inline img URLs return 200 image/*",
        ok=not broken,
        detail="" if not broken else f"{len(broken)} broken: {broken[:4]}",
    ))

    # 3. featured_media set, resolves 200, and is the cover (-featured), not an
    #    inline fallback. CRITICAL — directly the 1052 wrong-featured symptom.
    fm_id = post.get("featured_media", 0) or 0
    if not fm_id:
        results.append(Check("featured image set + is the cover", ok=False, detail="featured_media is 0"))
    else:
        try:
            mr = client.session.get(f"{client.api_url}/media/{fm_id}", params={"context": "edit"}, timeout=20)
            media = mr.json() if mr.status_code == 200 else {}
        except Exception:  # noqa: BLE001
            media = {}
        src_url = media.get("source_url", "")
        fname = src_url.split("/")[-1]
        is_cover = "-featured" in fname.lower()
        url_ok, why = (_url_is_image(client.session, src_url) if src_url else (False, "no source_url"))
        ok = bool(src_url) and url_ok and is_cover
        detail = ""
        if not ok:
            if not src_url:
                detail = f"media {fm_id} not found"
            elif not url_ok:
                detail = f"cover url {why}"
            elif not is_cover:
                detail = f"featured is '{fname}' — not a -featured cover (inline fallback?)"
        results.append(Check("featured image set + is the cover", ok=ok, detail=detail))

    # 4. Schema JSON-LD present. HIGH.
    has_schema = bool(re.search(r'type=["\']application/ld\+json["\']', content))
    results.append(Check("schema JSON-LD present", ok=has_schema, detail="" if has_schema else "no ld+json block"))

    # 5. No leftover placeholder/marker text. HIGH.
    found = [p for p in PLACEHOLDER_PATTERNS if re.search(p, content, re.IGNORECASE)]
    results.append(Check("no leftover placeholder markers", ok=not found, detail="" if not found else f"found: {found}"))

    # 6. No empty/alt-less inline img. MEDIUM.
    empties = sum(1 for img in imgs if not (img.get("src") or "").strip() or not (img.get("alt") or "").strip())
    results.append(Check("no empty/alt-less <img>", ok=(empties == 0), detail="" if not empties else f"{empties} img(s) missing src/alt"))

    # 7. Word count sane. MEDIUM.
    wc = len(soup.get_text(separator=" ", strip=True).split())
    results.append(Check("word count in range", ok=(MIN_WORDS <= wc <= MAX_WORDS), detail=f"{wc} words (want {MIN_WORDS}-{MAX_WORDS})"))

    # 8. At least one inline image. MEDIUM.
    results.append(Check("inline image present", ok=(len(imgs) >= MIN_INLINE_IMAGES), detail=f"{len(imgs)} inline <img>"))

    # 9. Chart present — warn by default, hard fail only with --require-chart. LOW.
    has_chart = bool(soup.find("svg")) or "data-chart" in content
    results.append(Check("chart present", ok=has_chart, detail="" if has_chart else "no <svg>/chart markup",
                         severity="fail" if require_chart else "warn"))

    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("post_id", type=int)
    ap.add_argument("--require-chart", action="store_true")
    ap.add_argument("--no-discord", action="store_true")
    args = ap.parse_args()

    url, username, app_password = get_wp_config()
    client = WordPressClient(url, username, app_password, dry_run=False)
    if not client.test_connection():
        print("FATAL: WordPress auth failed", file=sys.stderr)
        return 2

    try:
        resp = client.session.get(f"{client.api_url}/posts/{args.post_id}", params={"context": "edit"}, timeout=30)
        if resp.status_code != 200:
            print(f"FATAL: fetch post {args.post_id} -> HTTP {resp.status_code}", file=sys.stderr)
            return 2
        post = resp.json()
    except Exception as e:  # noqa: BLE001
        print(f"FATAL: {e}", file=sys.stderr)
        return 2

    title = (post.get("title") or {}).get("raw", "")[:70]
    print(f"\nVerifying post {args.post_id} [{post.get('status', '?')}]: {title}")
    results = run_checks(client, post, require_chart=args.require_chart)
    for r in results:
        print(r)

    hard = [r for r in results if not r.ok and r.severity == "fail"]
    warns = [r for r in results if not r.ok and r.severity == "warn"]

    if hard:
        reasons = "; ".join(f"{r.name}: {r.detail or 'failed'}" for r in hard)
        print(f"\nVERIFICATION FAILED — {len(hard)} hard check(s): {reasons}", file=sys.stderr)
        if not args.no_discord:
            edit_url = f"{url}/wp-admin/post.php?post={args.post_id}&action=edit"
            _notify_failure(
                stage="post-publish verification",
                title=f"Post {args.post_id} published but FAILED verification",
                detail=f"{reasons}\n{edit_url}",
            )
        return 1

    print(f"\nVERIFICATION PASSED{f' ({len(warns)} warning(s))' if warns else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
