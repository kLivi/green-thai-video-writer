#!/usr/bin/env python3
"""One-off: post 1052 was published via the broken manual path (update_post.py),
which skipped schema generation. Generate the JSON-LD from the article metadata
and inject it into the live post. Also delete the orphan inline media (1049-51)
that the original broken upload left unreferenced (superseded by 1057-59).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wordpress_upload import (
    get_wp_config, WordPressClient, parse_article,
    generate_schema_json_ld, _derive_focus_keyword,
)

POST_ID = 1052
COVER_MEDIA_ID = 1053
CATEGORY = "Policy, Economics & Thailand Context"
ORPHAN_MEDIA = [1049, 1050, 1051]
HTML = Path(__file__).resolve().parent.parent / "output" / "thailand-data-centers-green-power.html"


def main() -> int:
    url, username, app_password = get_wp_config()
    client = WordPressClient(url, username, app_password)
    if not client.test_connection():
        return 1

    # Live post (source of truth for slug/date/content).
    post = client.session.get(f"{client.api_url}/posts/{POST_ID}", params={"context": "edit"}, timeout=30).json()
    raw = post["content"]["raw"]
    if 'application/ld+json' in raw:
        print("Schema already present — skipping injection.")
    else:
        cover_url = client.session.get(f"{client.api_url}/media/{COVER_MEDIA_ID}", timeout=20).json().get("source_url", "")
        meta = parse_article(HTML)
        meta["slug"] = post["slug"]
        meta["date"] = post["date"][:10]
        meta["content_html"] = raw  # use the LIVE body for word count + FAQ extraction
        meta.setdefault("focus_keyword", _derive_focus_keyword(meta.get("title", "")))
        schema = generate_schema_json_ld(meta, site_url="https://greenenergythailand.com",
                                         category=CATEGORY, cover_url=cover_url)
        block = f'\n<script type="application/ld+json">\n{schema}\n</script>\n'
        new_content = raw + block
        r = client.session.post(f"{client.api_url}/posts/{POST_ID}", json={"content": new_content}, timeout=60)
        if r.status_code not in (200, 201):
            print(f"Schema update failed: {r.status_code} {r.text[:300]}")
            return 1
        print(f"Injected schema JSON-LD into post {POST_ID} ({len(schema)} chars).")

    # Delete confirmed-orphan inline media.
    for mid in ORPHAN_MEDIA:
        r = client.session.delete(f"{client.api_url}/media/{mid}", params={"force": "true"}, timeout=30)
        if r.status_code == 200:
            print(f"Deleted orphan media {mid}.")
        else:
            print(f"Delete media {mid} failed: {r.status_code} {r.text[:150]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
