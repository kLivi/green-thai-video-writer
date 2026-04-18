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

### Step 5 — Write article

Using `prompts/content-rules.md` and `prompts/video-article-template.md`:

- Follow the proposed outline exactly
- Open with TL;DR box
- Embed the YouTube video after TL;DR
- Answer-first H2 openings
- Clearly attribute information to the video ("According to [channel]...", "The video shows...")
- Enhance with Thai context from `prompts/thai-context.md` and Step 4 research
- Cite all external statistics inline with source name, year, and hyperlink
- Include FAQ section
- Target 1500-2500 words
- **Pillar phrase requirement:** The article MUST use at least one of the pillar's `pillar_phrases` from `src/config/categories.json` naturally in the body text. This enables the internal linking pipeline to create upward links to the pillar page. Check the chosen pillar's phrases and weave one in — e.g., for a Solar Energy article, use "solar energy" or "solar power" at least once.

**Image markers:** Two types of image marker:
- `[IMAGE: description]` — for fal.ai generation. Always use for the cover image. Use for inline images only when no visual moment matches the section content.
- `[FRAME: MM:SS, description]` — for video frame extraction. Default for inline images when a visual moment from Step 3 matches the section being written. The timestamp must match one of the identified visual moments.

Place 3-5 image markers total (1 cover `[IMAGE]` + 2-4 inline, preferring `[FRAME]` when available).
**Chart markers:** Place `[CHART: ...]` markers where data supports visualization (0-2 per article).

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

### Step 5b — Generate charts

For each `[CHART: ...]` marker, generate an inline SVG chart using `scripts/build_chart.py`.

The `[CHART]` marker format is:
```
[CHART: {chart_type}|{title}|{data_json}|source={source}|subtitle={optional_subtitle}|highlight={optional_label}]
```

Example:
```
[CHART: horizontal-bar|Solar Costs by Year|{"labels":["2020","2021","2022"],"values":[120000,110000,95000]}|source=MEG Study 2023]
```

For each `[CHART]` marker:
1. Parse the marker to extract: chart_type, title, data (JSON), source, subtitle, highlight
2. Run `python scripts/build_chart.py` with:
   - `--type {chart_type}`
   - `--title "{title}"`
   - `--data '{data_json}'`
   - `--source "{source}"` (if provided)
   - `--subtitle "{subtitle}"` (if provided)
   - `--highlight "{label}"` (if provided)
3. Capture the `<figure><svg>...</svg></figure>` output
4. Replace the `[CHART]` marker in the HTML with the generated SVG block

If no `[CHART]` markers exist, skip this step.

Note: The `build_chart.py` script enforces consistent styling (currentColor, transparent background, accessibility). Do not modify the generated SVG.

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

- [ ] No fabricated statistics
- [ ] Video properly attributed (channel name, link)
- [ ] YouTube embed present
- [ ] TL;DR box present
- [ ] Answer-first H2 openings
- [ ] FAQ section at end
- [ ] Word count 1500-2500
- [ ] Thai context adds genuine value (not padding)
- [ ] Charts generated via build_chart.py (not hand-coded SVG)
- [ ] 3-5 images (1 cover + 2-4 inline), all WebP
- [ ] Cover named `{slug}-featured.webp`
- [ ] Alt text on every image
- [ ] Video frames have `<figcaption>` with linked attribution to source video
- [ ] Video frames are 650×366 (no portrait/square crops)
- [ ] No anti-patterns from content-rules.md
