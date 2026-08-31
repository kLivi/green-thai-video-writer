# Publish path and verification gate

> Sources: scripts/wordpress_upload.py, 2026-08-09; scripts/verify_publish.py, 2026-07-25; progress.txt, multiple entries 2026-06-21 to 2026-08-09
> Raw: [wordpress_upload.py](../../raw/publishing/2026-08-09-wordpress-upload-script.md); [verify_publish.py](../../raw/publishing/2026-07-25-verify-publish-script.md); [progress.txt — session log](../../raw/pipeline/2026-08-09-progress-txt-session-log.md)
> Updated: 2026-09-01

## Overview

`scripts/wordpress_upload.py` is the only path from a finished `output/{slug}.html` article to a WordPress draft. It parses the HTML, cleans and enriches it, resolves category and schema, uploads images and the post via the WordPress REST API, and — since 2026-06-21, default-on since 2026-07-07 — runs a separate post-publish verification script (`verify_publish.py`) that re-fetches the live post and checks it is actually correct, not merely present.

## `parse_article()` and pre-upload safety nets

`parse_article(html_path)` reads the HTML and, as a safety net, calls the same `render_markers()` used by `render_charts.py` on it before anything else — so no upload path (headless, manual, or a re-run) can reach WordPress with a raw `[CHART: {...}]` marker or an unrenderable chart; see [Deterministic chart rendering](deterministic-chart-rendering.md). It then pulls title, meta description, OG tags, Twitter card, author, date, focus keyword (from the `keywords` meta tag, or derived from the title if absent), pillar/subcategory meta, article type, the schema `<script type="application/ld+json">` block, the cover image (from an `<!-- coverImage: ... --> ` HTML comment, falling back to `og:image`), the `<article>` (or `<body>`) content, every `<img>` tag, and a generated slug.

`assert_no_internal_link_markers()` refuses to upload any article still containing a retired `[INTERNAL-LINK ...]` marker. The mechanism was removed project-wide on 2026-08-07: nothing ever consumed the marker (the separate `get-internal-linking` pipeline derives its own anchors from post title and body text), and both historical strip strategies produced broken prose — deleting the token truncated the host sentence ("see ."), keeping the anchor half left an unlinked phrase stranded mid-paragraph. This pipeline never emitted the marker itself (the check was inherited copy-paste from `claude-blog`), but the guard stays: a marker appearing here would mean the writer improvised one, and that article is defective at its source, not something to silently repair.

## Post-publish verification (`verify_publish.py`, added 2026-06-21)

After a successful upload, `wordpress_upload.py` (when `--verify` is on, which is the default) shells out to `verify_publish.py <post_id>`, which re-fetches the live post from the WordPress REST API (`context=edit`, raw content) and runs nine checks:

1. Every inline `<img src>` is an absolute `http(s)` URL (or `data:`) — not relative.
2. Every inline image URL actually returns HTTP 200 with an `image/*` content type.
3. `featured_media` is set, resolves to a real image, and its filename contains `-featured` (i.e. it's the cover, not an inline-image fallback).
4. Schema JSON-LD is present.
5. No leftover placeholder markers (`[INTERNAL-LINK`, `[IMAGE:`, `[CHART:`, `[FRAME]`, `[PLACEHOLDER`) survive in the published body — deliberately excluding the `<!-- coverImage -->` and `<!-- chart -->` HTML comments, which legitimately survive publish and would otherwise false-positive on every normal post.
6. No `<img>` missing both `src` and `alt`.
7. Word count between 600 and 4000.
8. At least one inline image.
9. A chart is present (soft warning by default; hard failure only with `--require-chart`) — and if one is present, it is rendered and inspected (`check_charts()`), not merely checked for an `<svg>` tag's existence, because presence alone is not correctness (see the post 1590 incident in [Deterministic chart rendering](deterministic-chart-rendering.md)).

Checks 1-3 are hard/critical; a hard-check failure exits 1, fires a Discord failure embed with the WP edit URL, and (via `wordpress_upload.py`) makes the whole publish invocation exit non-zero even though a WordPress draft already exists.

## Why: the post 1052 incident (2026-06-21)

`wordpress_upload.py` filtered image uploads to filenames appearing as `<img>` tags in the article body — but the cover image was referenced only via the `<!-- coverImage --> ` comment, so it was dropped from the upload set, the featured image silently fell back to an inline image, and a manual Kimi-driven recovery re-posted the body with relative `images/` `src` paths, breaking every inline image. Three fixes landed together: (1) the cover filename is now added to the upload set regardless of whether it appears as an `<img>` tag; (2) `verify_publish.py` was built and calibrated against live posts 941, 1040, and 1052; (3) publish was moved into the calling shell script — the agent writes the article plus a `publish-manifest.json` and stops, and `get-video-auto.sh` runs `wordpress_upload.py --verify` and only marks the queue entry done on a verified success, via the new `--verify` flag. Post 1052 itself was hand-repaired (3 inline images re-uploaded, schema JSON-LD injected) and passed all 9 gate checks.

## `--verify` default-on (2026-07-07)

`--verify` started as an opt-in `store_true` flag. It was flipped to default-on (`argparse.BooleanOptionalAction`, default `True`, `--no-verify` to opt out) after the same bare-invocation hole was found and fixed in `claude-blog`: a direct call to `wordpress_upload.py` that omitted `--verify` let post 1243 ship a broken image there. The scheduled runner already always passed `--verify`; the default flip closes the gap for any ad-hoc or direct invocation too.

## The stale-republish duplicate bug (2026-07-11)

"Green Power for Data Centers" published three times (post 1052 legitimately on Jun 21, then near-identical duplicates 1199 on Jun 28 and 1249 on Jul 6, 98% identical to the original). Root cause, found from run logs: the queue head was a 2017 seminar video with no subtitles, so the headless agent got stuck asking an approval-style question nobody could answer unattended, wrote nothing, and the runner's fallback logic ("Manifest missing — falling back to newest HTML") republished the previous week's output file instead. `--verify` had passed each time because it checks integrity, not novelty. The fix added a freshness gate to `~/scripts/get-video-auto.sh` (not git-tracked): both the manifest and any fallback HTML must postdate the run's own start marker, or the runner refuses with "refusing stale republish" and fails loudly rather than republishing. The seminar entry in `queue/video-queue.txt` was marked `SKIP`; posts 1199 and 1249 were trashed and their inbound internal links fixed.

## fal.ai cover-generation auth failure (Jul 19, unresolved as of the handoff)

The Jul 19 scheduled run failed verification on post 1554 (Banpu energy transition): the `fal-ai/bytedance` Seedream endpoint returned an auth error generating the cover, the featured image fell back to an inline frame (`banpu-energy-transition-ceo.webp`), and check 3 above (featured-is-cover) failed. Draft 1554 was still sitting unresolved in WordPress as of the handoff's last update — see [Current state and backlog](../project-status/current-state.md).

## See Also

- [/get-video pipeline](../pipeline/get-video-workflow.md)
- [Deterministic chart rendering](deterministic-chart-rendering.md)
- [Citation gate](citation-gate.md)
- [Category and pillar classification](../pipeline/category-classification.md)
