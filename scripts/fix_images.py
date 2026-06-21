#!/usr/bin/env python3
"""Repair post 1052: images were published with relative `images/*.webp` src
(via the buggy update_post.py) and never uploaded to the WP Media Library, so
they render broken on the live site.

This script:
  1. Pulls the LIVE post content (context=edit) — WordPress is source of truth.
  2. Uploads the featured + 3 inline images to the Media Library.
  3. Rewrites each relative `images/<name>` src in the live content to its WP URL.
  4. Sets featured_media to the -featured image.
  5. Updates post 1052 in place (preserves any WP edits / internal links).

Idempotent-ish: if an image filename already exists in Media, WP creates a
suffixed copy, so run once. Dry-run with --dry-run.
"""
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

# Reuse the vetted helpers from the main uploader.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from wordpress_upload import get_wp_config, WordPressClient

POST_ID = 1052
IMAGES_DIR = Path(__file__).resolve().parent.parent / "output" / "images"
FEATURED_SUFFIX = "-featured"


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    url, username, app_password = get_wp_config()
    client = WordPressClient(url, username, app_password, dry_run=dry_run)

    print("[1/5] Authenticating...")
    if not client.test_connection():
        return 1

    print(f"\n[2/5] Fetching live post {POST_ID} (context=edit)...")
    resp = client.session.get(
        f"{client.api_url}/posts/{POST_ID}",
        params={"context": "edit"},
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"  Failed to fetch post: {resp.status_code} {resp.text[:200]}")
        return 1
    post = resp.json()
    content = post["content"]["raw"]
    current_featured = post.get("featured_media", 0)
    print(f"  Got {len(content)} chars raw. Current featured_media: {current_featured}")

    # Build alt-text lookup from the inline <img> tags in the live content.
    soup = BeautifulSoup(content, "html.parser")
    alt_lookup = {}
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if src:
            alt_lookup[Path(src).name] = img.get("alt", "")

    # Sanity: which relative image refs are actually in the body?
    referenced = set(re.findall(r'src=["\']images/([^"\']+)["\']', content))
    print(f"  Inline images referenced (relative): {sorted(referenced) or 'NONE'}")

    # Featured image (id 1053) is already uploaded + set — leave it alone to
    # avoid creating a duplicate Media entry. Only the inline body images broke.
    print("\n[3/5] Uploading inline images to Media Library...")
    rewrites = {}  # relative path fragment -> WP url
    for img_file in sorted(IMAGES_DIR.glob("thailand-data-centers-green-power-*.webp")):
        name = img_file.name
        if img_file.stem.endswith(FEATURED_SUFFIX):
            continue  # already the featured image
        if name not in referenced:
            print(f"  Skip (not referenced): {name}")
            continue

        alt = alt_lookup.get(name, img_file.stem.replace("-", " ").title())
        print(f"  Uploading: {name} (alt: {alt[:50]})")
        media = client.upload_image(img_file, alt_text=alt, description=alt)
        if not media:
            print(f"  !! Upload failed for {name}")
            return 1
        media_url = media.get("source_url", "")
        print(f"    -> ID {media['id']}  {media_url[-60:]}")
        rewrites[f"images/{name}"] = media_url

    print("\n[4/5] Rewriting inline src -> WP media URLs...")
    new_content = content
    for old, new in rewrites.items():
        if old in new_content:
            new_content = new_content.replace(old, new)
            print(f"  {old} -> ...{new[-50:]}")
        else:
            print(f"  WARN: '{old}' not found in content")

    payload = {"content": new_content}

    if dry_run:
        print("\n[DRY RUN] No update sent.")
        return 0

    print(f"\n[5/5] Updating post {POST_ID}...")
    upd = client.session.post(
        f"{client.api_url}/posts/{POST_ID}",
        json=payload,
        timeout=60,
    )
    if upd.status_code in (200, 201):
        print(f"  Updated post {POST_ID}. Inline images rewritten: {len(rewrites)}")
        return 0
    print(f"  Update failed: {upd.status_code} {upd.text[:300]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
