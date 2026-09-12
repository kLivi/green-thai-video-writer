---
name: get-video
description: >
  Green Energy Thailand Video Writer — takes a YouTube URL, extracts the
  transcript, analyzes for key data, writes and publishes a WordPress draft
  for greenenergythailand.com. Vetted queue videos run end-to-end automatically;
  manual URLs pause for approval after analysis.
  Adds Thai context (permits, rates, incentives) beyond what the video covers.
  Use when user says "get video", "/get-video", or provides a YouTube URL
  to turn into an article.
user-invocable: true
argument-hint: '"https://youtube.com/watch?v=..."'
allowed-tools:
  - Read
  - Write
  - Bash
  - WebSearch
  - Glob
---

# Green Thai Video Writer

Turn a YouTube video about green energy in Thailand into a published WordPress draft.

## Workflow

### Step 1 — Load context

All commands run from the project root:
```bash
cd /home/unify/Documents/green-energy-thailand/green-thai-video-writer
```

Read these files before starting:
- `/home/unify/Documents/green-energy-thailand/claude-blog/shared/thai-facts.md` — **canonical Thai
  energy facts (REQUIRED)**. Covers confirmed rates, program status, the Royal
  Gazette rule, known bad sources, and preferred sources. If this file is
  missing, STOP the run and report: "Canonical Thai facts file missing —
  aborting to prevent fact drift." Do not guess rates or legal claims.
- `prompts/extract-video-data.md` — data extraction rules
- `prompts/thai-context.md` — Thai enhancement context
- `prompts/video-article-template.md` — article structure
- `prompts/content-rules.md` — writing persona and quality rules
- `prompts/visual-media.md` — image generation rules
- `prompts/chart-rules.md` — SVG chart rules
- `src/config/categories.json` — available pillars and subcategories

### Step 2 — Fetch transcript

Extract the transcript from the YouTube URL using yt-dlp.

**Try auto-generated subtitles first (English, then Thai):**
```bash
yt-dlp --js-runtimes node --write-auto-sub --sub-lang "en,th" --sub-format "vtt" --skip-download -o "/tmp/yt-transcript" "{URL}"
```

If that produces a VTT file, convert it to clean text:
```bash
python3 -c "
import re, sys

with open('/tmp/yt-transcript.en.vtt', 'r') as f:
    content = f.read()

# Remove VTT header and timestamps
lines = content.split('\n')
text_lines = []
seen = set()
for line in lines:
    line = line.strip()
    # Skip headers, timestamps, position tags
    if not line or line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:') or '-->' in line or line.isdigit():
        continue
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', line)
    if clean and clean not in seen:
        seen.add(clean)
        text_lines.append(clean)

transcript = ' '.join(text_lines)
print(transcript)
" > /tmp/yt-transcript-clean.txt
```

**VTT preservation:** The raw VTT file (`/tmp/yt-transcript.en.vtt` or `.th.vtt`) is needed in Step 3 for visual moment identification. Do not delete it after conversion.

If English subtitles aren't available, try Thai (`.th.vtt`) and note that the transcript is in Thai.

**If no subtitles at all**, try extracting audio description or inform the user:
"No transcript available for this video. Options: (1) provide a manual transcript, (2) try a different video."

Read the clean transcript and assess its quality:
- Is it long enough to extract meaningful data? (minimum ~200 words)
- Is it in English or Thai?
- Does it contain technical/financial data?

Also fetch video metadata:
```bash
yt-dlp --js-runtimes node --dump-json --skip-download "{URL}" 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f\"Title: {data.get('title', 'Unknown')}\")
print(f\"Channel: {data.get('channel', data.get('uploader', 'Unknown'))}\")
print(f\"Duration: {data.get('duration_string', 'Unknown')}\")
print(f\"Views: {data.get('view_count', 'Unknown')}\")
print(f\"Upload date: {data.get('upload_date', 'Unknown')}\")
print(f\"Description: {data.get('description', '')[:500]}\")
print(f\"Thumbnail: {data.get('thumbnail', '')}\")
embed = data.get('playable_in_embed', True)
print(f\"Embeddable: {embed}\")
if not embed:
    print('⚠️  VIDEO EMBEDDING DISABLED — use linked thumbnail instead of iframe')
"
```

**Embed check:** If `playable_in_embed` is `False`, the video cannot be embedded via iframe. In Step 5, use a linked thumbnail instead:
```html
<div class="video-embed">
  <a href="https://www.youtube.com/watch?v={VIDEO_ID}" target="_blank" rel="noopener">
    <img src="https://i.ytimg.com/vi/{VIDEO_ID}/hqdefault.jpg"
         alt="Watch: {video title} by {channel} on YouTube"
         width="560" height="315" style="display:block; border-radius:8px;" loading="lazy">
  </a>
  <p><a href="https://www.youtube.com/watch?v={VIDEO_ID}" target="_blank" rel="noopener">▶ Watch the full video on YouTube</a> — "{video title}" by {channel} ({duration})</p>
</div>
```

### Step 3 — Extract data and propose article

Using the rules in `prompts/extract-video-data.md`, extract structured data from the transcript.

Also read the raw VTT file (`/tmp/yt-transcript.en.vtt` or `.th.vtt`) for timestamp data. Using the Visual Moments rules in `prompts/extract-video-data.md`, identify 5-6 visual moments with timestamps.

Then, using `src/config/categories.json`, determine:
- **Category**: best matching pillar and subcategory
- **Article title**: following the format in `prompts/video-article-template.md`
- **Article angle**: what unique value this article adds beyond the video
- **Key data points**: the most interesting numbers/facts extracted
- **Credibility rating**: high/medium/low based on extraction rules
- **Visual moments**: 5-6 timestamps where the video likely shows relevant visuals (from VTT analysis)

**If this video came from the vetted queue** (`VETTED:`, `VETTED-RESEARCH:`, or `VETTED-SERIES:`):
- Log the proposal summary (title, category, angle, key data) for the record but **do not pause for approval** — proceed directly to Step 4.

**If this video was provided as a manual URL** (not from the queue):
- Present the proposal and **STOP HERE AND WAIT FOR USER APPROVAL.**
- Do not proceed until the user responds with:
  - **"yes"** or similar → proceed to Step 4
  - **Suggested changes** → revise the proposal and present again
  - **"skip"** → abort this video, report skipped

### Step 4 — Research supplementary context

Based on the article angle, run 2-4 targeted WebSearch queries to fill gaps:
- Current Thai regulations/rates relevant to the project type
- Comparable project costs for context
- Any claims in the video that need verification

Focus on Thailand-specific, recent (2024-2026) sources.

#### Step 4a — Write `output/sources.json` (REQUIRED)

Every factual claim you will cite gets a record here, written as you research.
The publish gate (`shared/verify_citations.py`) fetches each URL and checks the
source really carries the number and the sentence.

**This file is not optional.** An article with no citable statistics must still
emit `{"sources": []}` — omitting it makes "nothing to cite" and "the writer
forgot" indistinguishable, which is how post 1786 shipped a claim its cited
page never made.

**Delete any `output/sources.json` from a previous run first.** The output
directory is reused, and a stale file verifies the previous article.

Schema — every field required, per record:

```json
{"sources": [
  {
    "id": "S1",
    "value": "3.8 million tonnes CO2e",
    "claim": "Thai cement sector emissions cut since 2019",
    "source_name": "Nation Thailand",
    "url": "https://www.nationthailand.com/sustaination/40068611",
    "quote": "the sector has cut more than 3.8 million tonnes of CO2e since 2019",
    "tier": 2,
    "source_type": "web"
  }
]}
```

- `quote` MUST be verbatim from that page and contain the number. No paraphrase;
  no quote for a page you did not open.
- **A figure the video states gets `source_type:"transcript"`** — not a `"web"`
  record borrowed from a page that never carried it. Set `url` to the video
  (timestamped, e.g. `https://youtu.be/abc123?t=412`), `quote` to the transcript
  line containing the number, `tier: 3`. The gate cannot fetch a video, so these
  are never verified against anything — which is exactly why the next rule is not
  optional.
- **Say in the prose that it came from the video.** A number a company states on
  camera is evidence of what was said, not of what is true, and the reader never
  sees `sources.json`. Every transcript-sourced figure needs its attribution in
  the same sentence — "in the video, Bangchak says…", "according to the
  presentation…", or the speaker's name. The publish gate prints
  `[warn] UNATTRIBUTED_VIDEO_CLAIM | <value> | <sentence>` for each one that
  reads as plain fact. Supplementary WebSearch figures (Step 4) are different:
  those are checked against real pages and need no such hedge.
- `source_type`: `"web"`, `"internal-verified"` for claims from
  `claude-blog/shared/thai-facts.md` (then `url` may be empty), `"derived"`
  for a number you worked out yourself, or `"transcript"` (above). For
  `internal-verified` records, write `source_name:""` and `url:""` — you do
  not choose these. `research_gate.py --finalize` (Step 4b, next) resolves the
  real citing authority from the structured allowlist in
  `claude-blog/shared/thai-facts.md` (the `value | source_name | url` rows)
  and fills both in. A value with no allowlist row is dropped rather than
  published under a name you invented, so do not try to supply one — and
  never put the filename `thai-facts.md` in `source_name`; that leak reached
  five live articles before this gate existed. **You do not have the last
  word on `quote` either.** `research_gate.py --finalize` re-fetches the page
  and replaces your text with the sentence it finds carrying the value,
  verbatim from the bytes. Write the closest sentence you can — it still
  drives the pre-finalize check — but do not polish it to read better.
  (`internal-verified`/`derived`/`transcript` records have no page to
  re-fetch, so their `quote` is never rewritten.)

#### Step 4b — Research-Time Citation Gate (REQUIRED)

Run the same deterministic gate claude-blog uses, while you are still in the
loop to fix a failure — not a subagent-only step. It re-checks every web
number against the page, resolves `internal-verified` source_name/url from
the `thai-facts.md` allowlist, and re-slices every web `quote` verbatim out of
the page it just fetched. `derived` and `transcript` records pass through
unchanged (no page to check). Ported from claude-blog's
`scripts/research_gate.py` 2026-09-12 to close the class of leaks documented
above.

1. **Run CHECK:**
   ```bash
   python3 scripts/research_gate.py output/sources.json --thai-facts /home/unify/Documents/green-energy-thailand/claude-blog/shared/thai-facts.md
   ```
   Exit 0 → all citations pass, proceed to Step 5.
2. Exit 10 → the script prints one `RESOURCE_NEEDED: {cid} | {value} | {source} | {url}`
   line per failing stat (its cited page does not actually contain the number).
   For each, re-source that specific stat — find an alternate authoritative
   source whose fetched page genuinely contains the number, and rewrite that
   entry in `output/sources.json` (same fields: `id, value, claim, source_name,
   url, quote, tier, source_type`). Up to **3 attempts per stat**.
3. Re-run CHECK after each re-source pass. Repeat the loop.
4. **Bounded:** a per-article ceiling of **12 total re-source attempts** across
   all stats. Stop looping when CHECK passes, OR the ceiling is hit, OR a full
   pass makes no progress (no stat improved).
5. When stopping with failures still present, run FINALIZE:
   ```bash
   python3 scripts/research_gate.py output/sources.json --finalize --thai-facts /home/unify/Documents/green-energy-thailand/claude-blog/shared/thai-facts.md
   ```
   - Exit 0 → the failing stats were dropped (≥4 valid citations remain), and
     `internal-verified`/`quote` corrections were written. Proceed to Step 5
     with the rewritten `sources.json`.
   - Exit 20 → **HOLD.** Dropping would leave fewer than 4 valid citations. Stop
     the whole run with a non-zero failure — do NOT proceed to writing. In
     headless mode this surfaces as a pipeline failure the runner turns into a
     Discord alert, and the queue row stays `Ready` for retry.
6. **Sole citation authority:** after this step, `output/sources.json` is the
   ONLY source for citations. The writer must NEVER cite a stat from memory
   that is no longer in the file.

### Step 5 — Write article

Using `prompts/content-rules.md` and `prompts/video-article-template.md`:

- Follow the proposed outline exactly
- Open with TL;DR box
- Embed the YouTube video after TL;DR
- Answer-first H2 openings
- Clearly attribute information to the video ("According to [channel]...", "The video shows...")
- Enhance with Thai context from `prompts/thai-context.md` and Step 4 research
- Cite all external statistics inline with source name, year, and hyperlink
- **A number you work out yourself is not a cited stat.** Summing two figures,
  converting a currency, or computing a percentage change or per-unit price
  produces a number no source page states — citing a source's URL next to it
  attributes to that source a figure it never gave. Either drop the
  arithmetic, or append a `source_type:"derived"` record (Step 4a) whose
  `claim` states the computation, and cite that record's source name instead.
  The pre-upload gate flags any number in the body no record accounts for.
- Include FAQ section
- Target 1500-2500 words
- **Internal links:** When you add an in-article internal link, point it to a specific post at `/posts/{slug}/` — never to a `/category/` archive page. (Most internal links are added automatically by the linking pipeline after publish; only add one inline when it genuinely helps the reader.)
- **Pillar phrase requirement:** The article MUST use at least one of the pillar's `pillar_phrases` from `src/config/categories.json` naturally in the body text. This enables the internal linking pipeline to create upward links to the pillar page. Check the chosen pillar's phrases and weave one in — e.g., for a Solar Energy article, use "solar energy" or "solar power" at least once.

**Image markers:** Two types of image marker:
- `[IMAGE: description]` — for fal.ai generation. Always use for the cover image. Use for inline images only when no visual moment matches the section content.
- `[FRAME: MM:SS, description]` — for video frame extraction. Default for inline images when a visual moment from Step 3 matches the section being written. The timestamp must match one of the identified visual moments.

Place 3-5 image markers total (1 cover `[IMAGE]` + 2-4 inline, preferring `[FRAME]` when available).
**Chart markers:** Place `[CHART: {...}]` JSON markers where data supports visualization
(0-2 per article). Format and chart-type selection: `prompts/chart-rules.md`. Emit the
marker only — never write or paste SVG.

Output the full article HTML:
```bash
mkdir -p output
# Write to output/{slug}.html
```

Wrap in a full HTML document (required by wordpress_upload.py):
```html
<!DOCTYPE html>
<html>
<head>
  <title>{title}</title>
  <meta name="description" content="{meta_description}">
  <meta name="keywords" content="{focus_keyword}">
  <meta name="author" content="Green Energy Thailand">
  <meta name="date" content="{YYYY-MM-DD}">
  <meta name="article-type" content="support">
</head>
<body>
<article>
<h1>{title}</h1>
{article_html}
</article>
</body>
</html>
```

### Step 5b — Charts: leave the markers alone

**Do nothing in this step.** Leave every `[CHART: {...}]` marker exactly as you
wrote it in Step 5.

Do NOT run `build_chart.py`. Do NOT parse the marker JSON. Do NOT paste SVG into
the article. `scripts/render_charts.py` does the substitution deterministically
before upload, and rasterizes each chart to confirm it draws. A chart that fails
to build or renders wrong stops the publish.

This step used to be the agent's and it kept corrupting charts — most recently a
`</text>` hand-copied as `</title>`, which shipped idea-writer post 1590 as an
empty box. Marker format and chart-type selection: `prompts/chart-rules.md`.

To check your markers before the pipeline does:

```bash
python3 scripts/render_charts.py output/<slug>.html --check
```

### Step 6a — Extract video frames

For each `[FRAME: MM:SS, description]` marker in the article, extract candidate frames from the source video.

#### 6a-i: Download 5-second clips

For each `[FRAME]` marker, download a 5-second window centered on the timestamp:

```bash
# Example for timestamp 03:42 — download 03:40 to 03:45
yt-dlp --js-runtimes node -f "bestvideo[height<=1080]" --download-sections "*03:40-03:45" -o "/tmp/frame_0342.mp4" "{URL}"
```

Process all `[FRAME]` markers before moving to the next substep.

#### 6a-ii: Extract candidate frames

For each downloaded clip, extract 5 candidate frames (one per second):

```bash
ffmpeg -i /tmp/frame_0342.mp4 -vf "fps=1" -q:v 2 /tmp/frame_0342_%d.jpg
```

#### 6a-iii: Select best frames

View all candidate frames for each visual moment (use the Read tool on each `.jpg` file). Pick the best one per moment — sharpest, most relevant to the topic, best composition.

If none of the 5 candidates for a moment are usable (all blurry, all talking head), replace the corresponding `[FRAME]` marker with an `[IMAGE]` marker so fal.ai handles it in Step 6b.

#### 6a-iv: Resize and save

```bash
mkdir -p output/images
python3 -c "
from PIL import Image
img = Image.open('/tmp/frame_0342_3.jpg')  # whichever candidate was selected
img = img.resize((650, 366), Image.Resampling.LANCZOS)
img.save('output/images/{slug}-{descriptor}.webp', 'WEBP', quality=82)
"
```

All video frames use 650×366 (inline landscape). No cropping to portrait or square — respect the creator's original framing.

Naming: `{slug}-{descriptor}.webp` — descriptor derived from the visual moment description (e.g., "Mountains and trees blocking afternoon sun" → `mountains`).

#### 6a-v: Replace [FRAME] markers in HTML

Replace each `[FRAME: ...]` with:
```html
<figure>
  <img src="images/{slug}-{descriptor}.webp"
       alt="Descriptive alt text — full sentence, 10-125 chars"
       width="650" height="366" loading="lazy">
  <figcaption>Screenshot from <a href="{youtube_url}" target="_blank" rel="noopener">"{video title}"</a> by {channel}</figcaption>
</figure>
```

The `<figcaption>` with linked attribution is **required** on every video frame.

If frame extraction fails for any marker (yt-dlp error, ffmpeg error), replace the `[FRAME]` marker with `[IMAGE]` for fal.ai fallback in the next step.

### Step 6b — Generate AI images (cover + fallback)

Generate AI images for remaining `[IMAGE: ...]` markers (cover image + any sections without a video frame) using fal.ai Seedream v4.5.
Follow the rules in `prompts/visual-media.md`.

#### 6b-i: Generate prompts

For each `[IMAGE]` marker, write a generation prompt:
- Describe what a person standing there would actually see and photograph
- Keep under 25 words
- Append `, Thailand, natural lighting, candid photo, realistic`
- One clear subject per image — every image must have completely different content
- No text, labels, or writing in prompts
- Max 1-2 images with people; rest should be objects/environments

Assign dimensions:
| Image | Width | Height | When to Use |
|-------|-------|--------|-------------|
| Cover/featured | 1200 | 630 | First `[IMAGE]` marker |
| Inline landscape | 650 | 366 | Wide scenes |
| Inline portrait | 450 | 600 | Tall subjects |
| Inline square | 550 | 550 | Close-ups |

Vary dimensions across the article. Include at least one portrait.

#### 6b-ii: Submit to fal.ai

```bash
export IMAGE_API_KEY=$(grep IMAGE_API_KEY /home/unify/Documents/green-energy-thailand/green-thai-video-writer/.env | cut -d= -f2)
```

For each prompt:
```bash
curl -s -X POST "https://queue.fal.run/fal-ai/bytedance/seedream/v4.5/text-to-image" \
  -H "Authorization: Key $IMAGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"[prompt]","image_size":{"width":WIDTH,"height":HEIGHT},"num_images":1}'
```

Submit ALL jobs before polling.

#### 6b-iii: Poll and download

Poll each `status_url` every 5 seconds until `COMPLETED`:
```bash
curl -s "$STATUS_URL" -H "Authorization: Key $IMAGE_API_KEY"
```

Retrieve result:
```bash
curl -s "$RESPONSE_URL" -H "Authorization: Key $IMAGE_API_KEY"
```

Image URL in `images[0].url`.

#### 6b-iv: Resize and convert to WebP

```bash
mkdir -p output/images
curl -s "[fal.media URL]" -o /tmp/img_raw.png
python3 -c "
from PIL import Image
img = Image.open('/tmp/img_raw.png')
img = img.resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)
img.save('output/images/{slug}-{descriptor}.webp', 'WEBP', quality=82)
"
```

Naming: `{slug}-featured.webp` for cover, `{slug}-{descriptor}.webp` for inline.

#### 6b-v: Replace markers in HTML

Replace each `[IMAGE: ...]` with:
```html
<figure>
  <img src="images/{slug}-{descriptor}.webp"
       alt="Descriptive alt text — full sentence, 10-125 chars"
       width="WIDTH" height="HEIGHT" loading="lazy">
</figure>
```

For cover image, add: `<!-- coverImage: images/{slug}-featured.webp -->`

### Step 7 — Publish to WordPress

```bash
cd /home/unify/Documents/green-energy-thailand/green-thai-video-writer
python3 scripts/wordpress_upload.py output/{slug}.html --images output/images --category "{pillar from Step 3}"
```

### Step 8 — Report

Report to the user:
- WordPress post ID and edit URL
- Article title and slug
- Word count
- Category assigned
- Video URL and channel credited
- Number of images generated and uploaded
- Number of charts generated (and their types)
- Number of charts generated
- Credibility rating from Step 3
- Any quality concerns to address before publishing

## Queue Processing

If invoked with `queue` instead of a URL:

```bash
# Find next vetted URL (VETTED:, VETTED-RESEARCH:, or VETTED-SERIES:)
LINE=$(grep -E '^VETTED(-RESEARCH|-SERIES)?: ' queue/video-queue.txt | head -1)
```

Determine the queue type and extract the URL(s):

- **`VETTED: <url>`** — Standard processing. Extract URL: `URL=$(echo "$LINE" | sed 's/^VETTED: //')`
- **`VETTED-RESEARCH: <url>`** — Short source video. Extract URL the same way, but **run additional Brave Search research** in Step 3 to supplement the thin transcript. Aim for 3-5 supplementary sources before writing.
- **`VETTED-SERIES: <url1>|<url2>|...|<urlN>`** — Multi-part series. Extract all URLs: `URLS=$(echo "$LINE" | sed 's/^VETTED-SERIES: //')` then split on `|`. Fetch transcripts for ALL parts and synthesize into a single article.

Process it, then mark as done (preserves the original prefix for history):
```bash
sed -i "s|^${LINE}$|DONE: ${LINE#*: }|" queue/video-queue.txt
```

If skipped by user:
```bash
sed -i "s|^${LINE}$|SKIP: ${LINE#*: }|" queue/video-queue.txt
```

**Queue comments:** Lines starting with `#` immediately after a VETTED line are notes for that video (e.g., corrections, research hints). Read them before processing — they may contain important context like price corrections or source caveats.

## Error Handling

**No transcript available:** Tell the user. Offer to try with a manually provided transcript.

**Transcript too short (<200 words):** Warn the user that the article may be thin. Proceed if they approve.

**WP upload fails:** Try `--dry-run` first. Check `.env` credentials.

**Image generation fails:** Skip that image, remove the marker. Article can publish without images.

**IMAGE_API_KEY not set:** Skip image generation entirely. Publish text-only and note it.

**Video not about green energy/Thailand:** Flag in the proposal (Step 3). Let the user decide.

## Quality Checklist (before publishing)

- [ ] `output/sources.json` exists, is this run's (not a leftover), and covers every cited claim
- [ ] Every `[warn] UNATTRIBUTED_VIDEO_CLAIM` from the gate is resolved — the
      sentence now names the video or the speaker, or the claim is cut
- [ ] Every `quote` is verbatim from the page at its `url` — a named source and a live hyperlink are NOT evidence the page supports the claim
- [ ] No fabricated statistics
- [ ] Every number the citation gate flagged as `[warn] UNSOURCED_NUMBER` is
      either backed by a `derived` record (your own arithmetic), re-sourced, or
      cut — the warning doesn't block, but a still-standing unsourced number
      next to an unrelated citation is exactly how post 1786 shipped
- [ ] Video properly attributed (channel name, link)
- [ ] YouTube embed present
- [ ] TL;DR box present
- [ ] Answer-first H2 openings
- [ ] FAQ section at end
- [ ] Word count 1500-2500
- [ ] Thai context adds genuine value (not padding)
- [ ] Charts left as `[CHART: {...}]` markers (never hand-coded SVG, never pre-substituted)
- [ ] 3-5 images (1 cover + 2-4 inline), all WebP
- [ ] Cover named `{slug}-featured.webp`
- [ ] Alt text on every image
- [ ] Video frames have `<figcaption>` with linked attribution to source video
- [ ] Video frames are 650×366 (no portrait/square crops)
- [ ] No anti-patterns from content-rules.md
