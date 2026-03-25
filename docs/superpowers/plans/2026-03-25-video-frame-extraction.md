# Video Frame Extraction — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace AI-generated inline images with actual frames from the source YouTube video, using transcript timestamps to identify relevant visual moments.

**Architecture:** All changes are to prompt/skill files that instruct the LLM pipeline. No new Python scripts or packages. Frame extraction uses yt-dlp + ffmpeg bash commands inline, same pattern as the existing fal.ai workflow. The pipeline is a Claude Code skill (SKILL.md) orchestrated by the LLM step-by-step.

**Tech Stack:** yt-dlp, ffmpeg (both existing dependencies), Pillow (existing), bash

**Spec:** `docs/superpowers/specs/2026-03-25-video-frame-extraction-design.md`

---

### Task 1: Add Visual Moments to extraction prompt

**Files:**
- Modify: `prompts/extract-video-data.md`

- [ ] **Step 1: Add Visual Moments section to extraction rules**

Append the following new section after the existing "Credibility Assessment" section at the end of `prompts/extract-video-data.md`:

```markdown
## Visual Moments

Identify 5-6 timestamps where the video likely shows something visually relevant — equipment, installations, scenery, screens, results — rather than a talking-head segment.

**To identify visual moments, read the raw VTT file** (not just the clean transcript) and look for:

- Topic shifts to physical objects (speaker describing equipment, showing hardware)
- Demonstrative language (speaker directing attention to something visible)
- Location descriptions (speaker describing surroundings, panning views)
- Results on screens (electricity bills, app dashboards, monitoring data)
- Before/after moments

**Skip these — they are likely talking-head segments:**

- Intro/outro sequences
- Segments that are purely verbal explanation with no visual subject
- Long monologues without topic shifts

These cues apply regardless of transcript language (English or Thai) — identify the semantic pattern, not specific keywords.

### Output format

```
Visual Moments:
1. 03:42 — Mountains and trees blocking afternoon sun (speaker pans to show horizon)
2. 07:15 — Inverter mounted on wall (speaker walks to equipment)
3. 09:30 — Electricity bill comparison on screen
4. 12:45 — Panel array on rooftop from ground level
5. 15:20 — Wiring and junction box close-up
```

Use `MM:SS` format for videos under 1 hour, `HH:MM:SS` for longer videos. Include a brief reason in parentheses explaining why you believe this moment is visual.

Present 5-6 candidates. Some may turn out to be duds — the best 2-4 will be selected later during article writing.
```

- [ ] **Step 2: Verify the file reads cleanly**

Read `prompts/extract-video-data.md` and confirm the new section integrates naturally after Credibility Assessment.

- [ ] **Step 3: Commit**

```bash
git add prompts/extract-video-data.md
git commit -m "Add Visual Moments section to extraction prompt"
```

---

### Task 2: Update SKILL.md Step 2 — preserve VTT note

**Files:**
- Modify: `SKILL.md` (lines 43-86, Step 2)

- [ ] **Step 1: Add VTT preservation note to Step 2**

After the closing code fence of the VTT-to-clean-text bash block (line 78), before the Thai fallback paragraph ("If English subtitles aren't available...") on line 80, add this note:

```markdown
**VTT preservation:** The raw VTT file (`/tmp/yt-transcript.en.vtt` or `.th.vtt`) is needed in Step 3 for visual moment identification. Do not delete it after conversion.
```

- [ ] **Step 2: Commit**

```bash
git add SKILL.md
git commit -m "Note VTT file preservation for visual moment extraction"
```

---

### Task 3: Update SKILL.md Step 3 — visual moment identification

**Files:**
- Modify: `SKILL.md` (lines 121-141, Step 3)

- [ ] **Step 1: Add VTT reading and visual moments to Step 3**

In Step 3, after the existing line "Using the rules in `prompts/extract-video-data.md`, extract structured data from the transcript." (line 123), add:

```markdown
Also read the raw VTT file (`/tmp/yt-transcript.en.vtt` or `.th.vtt`) for timestamp data. Using the Visual Moments rules in `prompts/extract-video-data.md`, identify 5-6 visual moments with timestamps.
```

In the proposal output list (lines 125-130), after the "Credibility rating" bullet, add:

```markdown
- **Visual moments**: 5-6 timestamps where the video likely shows relevant visuals (from VTT analysis)
```

- [ ] **Step 2: Commit**

```bash
git add SKILL.md
git commit -m "Step 3: read VTT file and identify visual moments"
```

---

### Task 4: Update SKILL.md Step 5 — add [FRAME] marker type

**Files:**
- Modify: `SKILL.md` (lines 151-167, Step 5)

- [ ] **Step 1: Replace the image markers instruction**

Find the existing image markers line (line 166):
```
**Image markers:** Place `[IMAGE: description]` markers (3-5 total, 1 cover + 2-4 inline).
```

Replace with:
```markdown
**Image markers:** Two types of image marker:
- `[IMAGE: description]` — for fal.ai generation. Always use for the cover image. Use for inline images only when no visual moment matches the section content.
- `[FRAME: MM:SS, description]` — for video frame extraction. Default for inline images when a visual moment from Step 3 matches the section being written. The timestamp must match one of the identified visual moments.

Place 3-5 image markers total (1 cover `[IMAGE]` + 2-4 inline, preferring `[FRAME]` when available).
```

- [ ] **Step 2: Commit**

```bash
git add SKILL.md
git commit -m "Step 5: add [FRAME] marker type for video screenshots"
```

---

### Task 5: Update SKILL.md Step 6 — split into 6a (frames) and 6b (fal.ai)

**Files:**
- Modify: `SKILL.md` (lines 214-295, Step 6)

- [ ] **Step 1: Insert new Step 6a before existing Step 6**

Before the existing "### Step 6 — Generate images" (line 214), insert the new frame extraction step:

```markdown
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
```

- [ ] **Step 2: Rename existing Step 6 to Step 6b**

Change the heading of the existing Step 6 from:
```
### Step 6 — Generate images
```
to:
```
### Step 6b — Generate AI images (cover + fallback)
```

Update the first line from:
```
Generate AI images for each `[IMAGE: ...]` marker using fal.ai Seedream v4.5.
```
to:
```
Generate AI images for remaining `[IMAGE: ...]` markers (cover image + any sections without a video frame) using fal.ai Seedream v4.5.
```

- [ ] **Step 3: Update sub-step labels**

Rename the existing sub-steps:
- `6a: Generate prompts` → `6b-i: Generate prompts`
- `6b: Submit to fal.ai` → `6b-ii: Submit to fal.ai`
- `6c: Poll and download` → `6b-iii: Poll and download`
- `6d: Resize and convert to WebP` → `6b-iv: Resize and convert to WebP`
- `6e: Replace markers in HTML` → `6b-v: Replace markers in HTML`

- [ ] **Step 4: Commit**

```bash
git add SKILL.md
git commit -m "Step 6: split into 6a (frame extraction) and 6b (fal.ai)"
```

---

### Task 6: Update visual-media.md — add video frame section

**Files:**
- Modify: `prompts/visual-media.md`

- [ ] **Step 1: Add Video Frame section**

Insert between the `---` separator (line 55) and the `## Image Generation` heading (line 57) in `prompts/visual-media.md`:

```markdown
## Video Frame Extraction

When the article is based on a YouTube video (video-writer pipeline), inline images should default to actual frames from the source video rather than AI-generated images. This is more authentic — the video creator has already framed relevant shots of equipment, installations, and scenery.

### When to use video frames vs fal.ai

| Image Type | Source | Rationale |
|-----------|--------|-----------|
| Cover/featured (1200×630) | fal.ai | Video frames don't crop well to OG ratio |
| Inline — topic shown in video | Video frame | Authentic, creator-framed |
| Inline — topic NOT in video | fal.ai | No relevant frame available |

### Frame dimensions

All video frames use **650×366** (inline landscape) only. Do not crop to portrait or square — respect the creator's original 16:9 framing.

### Attribution (required)

Every video frame MUST include a `<figcaption>` with linked attribution:

```html
<figure>
  <img src="images/{slug}-{descriptor}.webp"
       alt="Descriptive alt text — full sentence, 10-125 chars"
       width="650" height="366" loading="lazy">
  <figcaption>Screenshot from <a href="{youtube_url}" target="_blank" rel="noopener">"{video title}"</a> by {channel}</figcaption>
</figure>
```

This strengthens the fair use basis (editorial commentary with attribution). fal.ai images do NOT get this figcaption — only video frames.

### Fallback to fal.ai

If frame extraction fails or the extracted frame is unusable (blurry, dark, talking head), replace the `[FRAME]` marker with an `[IMAGE]` marker and generate via fal.ai as normal.
```

- [ ] **Step 2: Commit**

```bash
git add prompts/visual-media.md
git commit -m "Add video frame extraction rules to visual-media prompt"
```

---

### Task 7: Update quality checklist in SKILL.md

**Files:**
- Modify: `SKILL.md` (lines 358-373, Quality Checklist)

- [ ] **Step 1: Add frame-specific checklist items**

In the Quality Checklist at the end of SKILL.md, after the existing line `- [ ] Alt text on every image`, add:

```markdown
- [ ] Video frames have `<figcaption>` with linked attribution to source video
- [ ] Video frames are 650×366 (no portrait/square crops)
```

- [ ] **Step 2: Commit**

```bash
git add SKILL.md
git commit -m "Add video frame checks to quality checklist"
```

---

### Task 8: Verify ffmpeg availability

**Files:** None (verification only)

- [ ] **Step 1: Check ffmpeg is installed**

```bash
ffmpeg -version 2>&1 | head -1
```

Expected: version string like `ffmpeg version 6.x ...`. If not found, install via `sudo apt install ffmpeg`.

- [ ] **Step 2: Check yt-dlp --download-sections support**

```bash
yt-dlp --help | grep download-sections
```

Expected: `--download-sections` flag is listed. This confirms the installed yt-dlp version supports partial downloads.

---

### Task 9: End-to-end smoke test

**Files:** None (manual verification)

- [ ] **Step 1: Run `/get-video` on a test video**

Pick one of the vetted videos from `queue/video-queue.txt` and run the pipeline:

```bash
/get-video queue
```

Verify:
- Step 3 output includes a "Visual Moments" section with 5-6 timestamped entries
- Step 5 article contains `[FRAME: ...]` markers (not just `[IMAGE: ...]`)
- Step 6a extracts frames and the LLM views candidates before selecting
- Final HTML has `<figcaption>` attribution on video frame images
- Cover image is still fal.ai generated
- WordPress draft uploads successfully with both frame and fal.ai images

- [ ] **Step 2: Commit any queue changes**

```bash
git add queue/video-queue.txt
git commit -m "Mark smoke test video as DONE in queue"
```
