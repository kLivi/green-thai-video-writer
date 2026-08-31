# Green Thai Video Writer — /get-video pipeline

> Sources: SKILL.md, 2026-08-09; CLAUDE.md, 2026-05-01
> Raw: [SKILL.md — /get-video workflow definition](../../raw/pipeline/2026-08-09-skill-md-get-video-workflow.md); [CLAUDE.md — project overview](../../raw/pipeline/2026-05-01-claude-md-project-overview.md)
> Updated: 2026-09-01

## Overview

`green-thai-video-writer` turns a YouTube video about green energy in Thailand into a published WordPress draft on greenenergythailand.com. The `/get-video` command runs an 8-step pipeline: fetch transcript → extract data and propose an article → research supplementary Thai context → write the article → render charts → source/insert images → publish → report. Videos pulled from the vetted queue run end-to-end with no human in the loop; a manually supplied URL pauses for approval after Step 3.

## Step-by-step

1. **Load context** — reads the canonical Thai facts file (`claude-blog/shared/thai-facts.md`), the `prompts/` rule files, and `src/config/categories.json` before doing anything else. If the Thai-facts file is missing, the run aborts rather than guessing rates or legal claims.
2. **Fetch transcript** — `yt-dlp` pulls auto-generated subtitles (English first, then Thai) via `--write-auto-sub`, converted to clean text with a small Python VTT-stripping script. The raw VTT is kept (not deleted) because Step 3 re-reads its timestamps. Video metadata (title, channel, duration, views, upload date, embeddability) is pulled separately with `--dump-json`. If `playable_in_embed` is `False`, the article uses a linked thumbnail instead of an iframe embed.
3. **Extract data and propose** — following `prompts/extract-video-data.md`, extracts structured data plus 5-6 timestamped "visual moments" from the VTT. Determines category (pillar + subcategory from `categories.json`), title, angle, key data points, and a credibility rating. A queue video (`VETTED:`, `VETTED-RESEARCH:`, `VETTED-SERIES:`) logs this proposal and proceeds straight to Step 4; a manual URL stops and waits for the user to say yes, request changes, or skip.
4. **Research supplementary context** — 2-4 `WebSearch` queries to fill gaps (current Thai regulations/rates, comparable project costs, claim verification), scoped to Thailand-specific, recent (2024-2026) sources.
   - **Step 4a — `output/sources.json`** — every citable claim must get a record here as research happens: `id`, `value`, `claim`, `source_name`, `url`, a verbatim `quote` containing the number, `tier` (1 = primary/official, 2 = established press/industry, 3 = other), and `source_type` (`"web"`, or `"thai-facts"` for claims sourced to the canonical facts file). A claim sourced only to the video is attributed in prose, not given a fake URL record. An article with nothing to cite must still emit `{"sources": []}` — added 2026-08-09 after post 1786 shipped an unsupported claim because "nothing to cite" and "the writer forgot" were indistinguishable. Any stale `sources.json` from a prior run must be deleted first, since `output/` is reused.
5. **Write the article** — per `prompts/content-rules.md` and `prompts/video-article-template.md`: TL;DR box first, YouTube embed after it, answer-first H2s, video attribution in prose, Thai-context enhancement, inline-cited external stats, an FAQ section, 1500-2500 words. Internal links point to specific `/posts/{slug}/` pages, never category archives (most internal linking is added later by a separate pipeline). The article must naturally use at least one of the chosen pillar's `pillar_phrases` from `categories.json`.
   - **Image markers**: `[IMAGE: description]` for fal.ai generation (always the cover; used inline only when no visual moment matches); `[FRAME: MM:SS, description]` for video-frame extraction, the default for inline images when a Step 3 visual moment fits. 3-5 markers total (1 cover + 2-4 inline).
   - **Chart markers**: `[CHART: {...}]` JSON markers, 0-2 per article, per `prompts/chart-rules.md`. The agent emits the marker and stops — see [Deterministic chart rendering](../publishing/deterministic-chart-rendering.md) for why.
   - Output is a full HTML document (`<head>` with title/description/keywords/author/date/article-type, `<body><article>`) written to `output/{slug}.html`, because `wordpress_upload.py` requires that shape.
6. **Charts (5b) — do nothing** — the agent must leave every `[CHART: {...}]` marker untouched; `scripts/render_charts.py` substitutes deterministically before upload. It may run `render_charts.py --check` to validate markers without writing.
7. **Video frames and AI images (6a/6b)** — for each `[FRAME]` marker: download a 5-second clip centered on the timestamp with `yt-dlp --download-sections`, extract 5 candidate frames/second with `ffmpeg`, hand-pick the best, resize to 650×366 and save as WebP (`output/images/{slug}-{descriptor}.webp`); if no candidate is usable, the marker converts to `[IMAGE]`. For each `[IMAGE]` marker: write a fal.ai Seedream v4.5 prompt (<25 words, Thailand/natural-lighting/candid/realistic suffix, one subject per image, no text-in-image, max 1-2 people-images), submit all jobs, poll every 5 seconds, download, resize per a dimension table (cover 1200×630, inline landscape 650×366, portrait 450×600, square 550×550), save as WebP. Every `[FRAME]` figure requires a linked `<figcaption>` crediting the source video; the cover gets an HTML comment `<!-- coverImage: images/{slug}-featured.webp -->`.
8. **Publish** — `python3 scripts/wordpress_upload.py output/{slug}.html --images output/images --category "{pillar}"`. See [Publish path and verification gate](../publishing/publish-verification-gate.md) for what that script actually does.
9. **Report** — WordPress post ID and edit URL, title/slug, word count, category, video URL/channel, image and chart counts, credibility rating, and any quality concerns.

## Queue processing

`/get-video queue` pulls the first unprocessed line matching `^VETTED(-RESEARCH|-SERIES)?: ` from `queue/video-queue.txt`.

- `VETTED: <url>` — standard processing.
- `VETTED-RESEARCH: <url>` — a short source video; Step 3 research is supplemented with additional search, aiming for 3-5 supplementary sources.
- `VETTED-SERIES: <url1>|<url2>|...` — multiple URLs, pipe-separated; transcripts for every part are fetched and synthesized into one article.

A `#`-prefixed comment line immediately after a `VETTED` line is a note for that video (corrections, research hints) and must be read before processing. On completion the line is rewritten in place preserving the original prefix (`sed -i "s|^${LINE}$|DONE: ${LINE#*: }|"`); on skip it becomes `SKIP: `.

## Error handling

- No transcript at all → tell the user, offer a manually supplied transcript.
- Transcript under ~200 words → warn that the article may be thin; proceed only if approved.
- WordPress upload fails → retry with `--dry-run` first, check `.env` credentials.
- Image generation fails → drop that image marker; the article can publish without it.
- `IMAGE_API_KEY` unset → skip image generation entirely, publish text-only, note it in the report.
- Video judged off-topic (not green energy / not Thailand) → flagged at the Step 3 proposal for the user to decide.

## Environment

Credentials live in a shared `.env` (`~/Documents/green-energy-thailand/.env`, sibling to the other GET pipelines), loaded via `~/Documents/green-energy-thailand/shared/env_loader.py`. Keys consumed: `IMAGE_API_KEY` (fal.ai), `WORDPRESS_URL`, `WORDPRESS_USERNAME`, `WORDPRESS_APP_PASSWORD`, `DISCORD_WEBHOOK_URL`. Runs on Python 3.12+ with requests, beautifulsoup4, pillow, yt-dlp. This project is one of three sibling "GET" pipelines alongside `green-thai-idea-writer` and `claude-blog` (the reference implementation), all targeting greenenergythailand.com.

## See Also

- [Category and pillar classification](category-classification.md)
- [Deterministic chart rendering](../publishing/deterministic-chart-rendering.md)
- [Citation gate](../publishing/citation-gate.md)
- [Publish path and verification gate](../publishing/publish-verification-gate.md)
- [Current state and backlog](../project-status/current-state.md)
