# Video Frame Extraction — Design Spec

Replace AI-generated inline images with actual frames from the source YouTube video. The video creator has already framed and shot relevant visuals (equipment, installations, scenery) — using those frames is more authentic and avoids potentially misleading AI-generated images.

## Decision Record

- **Cover image**: Always fal.ai (1200x630 OG-compatible). Video frames don't crop well to this ratio.
- **Inline images**: Default to video frames when a relevant visual moment exists. Fall back to fal.ai when no frame matches.
- **Frame dimensions**: Always 650x366 inline landscape. No cropping to portrait/square — respect the creator's framing.
- **Fair use**: Editorial screenshots with attribution. Each frame gets a `<figcaption>` linking to the source video and crediting the creator.
- **Approach**: Timestamp-based extraction (Approach A). The LLM identifies visual moments from transcript timestamps, yt-dlp downloads a 5-second window at each timestamp, ffmpeg extracts one frame.

## Pipeline Changes

### Current Flow

```
Step 2 (transcript) → Step 3 (analysis) → Step 5 (write) → Step 6 (generate images) → Step 7 (upload)
```

### New Flow

```
Step 2 (transcript — VTT preserved) → Step 3 (analysis + visual moments from VTT) → Step 5 (write with [FRAME] and [IMAGE] markers) → Step 6a (extract frames) → Step 6b (fal.ai for cover + remaining [IMAGE]) → Step 7 (upload)
```

## Timestamp Availability (Step 2 → Step 3)

The current Step 2 saves the raw VTT file to `/tmp/yt-transcript.en.vtt` and converts it to clean text at `/tmp/yt-transcript-clean.txt` (timestamps stripped). The clean text is what Step 3 currently reads.

**Change required:** Step 3 must read BOTH files:
- `/tmp/yt-transcript-clean.txt` — for data extraction (existing behavior)
- `/tmp/yt-transcript.en.vtt` (or `.th.vtt`) — for timestamp correlation when identifying visual moments

The VTT format uses `HH:MM:SS.mmm` timestamps. The LLM should output visual moment timestamps in `MM:SS` format for videos under 1 hour, and `HH:MM:SS` for longer videos. The yt-dlp `--download-sections` flag accepts both formats.

## Visual Moment Identification (Step 3)

During the existing data extraction, the LLM reads the VTT file and identifies 5-6 timestamps where the video likely shows something visually relevant rather than a talking-head segment.

### What to look for

These cues apply regardless of transcript language (English or Thai) — the LLM should identify the semantic pattern, not match specific keywords:

- Topic shifts to physical objects (speaker describing equipment, showing hardware)
- Demonstrative language (speaker directing attention to something visible)
- Location descriptions (speaker describing surroundings, panning views)
- Results on screens (electricity bills, app dashboards, monitoring data)
- Before/after moments

### What to avoid

- Talking-head segments (speaker sitting at desk, talking to camera)
- Intro/outro sequences
- Segments that are purely verbal explanation with no visual subject

### Output format

Added to the existing Step 3 proposal output:

```
Visual Moments:
1. 03:42 — Mountains and trees blocking afternoon sun (speaker pans to show horizon)
2. 07:15 — Inverter mounted on wall (speaker walks to equipment)
3. 09:30 — Electricity bill comparison on screen
4. 12:45 — Panel array on rooftop from ground level
5. 15:20 — Wiring and junction box close-up
```

The LLM is guessing based on text cues. 5-6 candidates are identified knowing some may be duds. The best 2-4 are selected during article writing.

## Frame Extraction (Step 6a)

### Method

For each visual moment timestamp, download a 5-second window centered on the timestamp and extract a single frame. The buffer accounts for transcript timestamps being approximate — the speaker often says "look at this" a few seconds before or after the camera shows it.

```bash
# Extract 5-second window around 03:42 (03:40 to 03:45)
yt-dlp --js-runtimes node -f "bestvideo[height<=1080]" --download-sections "*03:40-03:45" -o "/tmp/frame_0342.mp4" "{URL}"
# Extract the middle frame
ffmpeg -i /tmp/frame_0342.mp4 -vf "select=eq(n\,75)" -frames:v 1 -q:v 2 /tmp/frame_0342.jpg
```

### Quality check

After extracting all frames, the LLM views them (Claude Code can read images). If a frame is unusable (blurry, dark, just a talking head despite transcript cues), it gets dropped and the corresponding `[FRAME]` marker is replaced with an `[IMAGE]` marker for fal.ai generation.

### Resize and convert

All frames use inline landscape dimensions (650x366), respecting the creator's original 16:9 framing:

```python
from PIL import Image
img = Image.open('/tmp/frame_0342.jpg')
img = img.resize((650, 366), Image.Resampling.LANCZOS)
img.save('output/images/{slug}-mountains.webp', 'WEBP', quality=82)
```

### Naming

Same convention as current: `{slug}-{descriptor}.webp`. The LLM derives the short descriptor during article writing [LLM step] — e.g., "Mountains and trees blocking afternoon sun" becomes `mountains`.

### Attribution HTML

```html
<figure>
  <img src="images/{slug}-mountains.webp"
       alt="Mountains and trees near the installation that block afternoon sunlight"
       width="650" height="366" loading="lazy">
  <figcaption>Screenshot from <a href="{youtube_url}" target="_blank" rel="noopener">"{video title}"</a> by {channel}</figcaption>
</figure>
```

The `<figcaption>` with linked attribution is required on every video frame. This is the key difference from fal.ai images and strengthens the fair use basis.

## Article Writing Integration (Step 5)

### Two marker types

- `[IMAGE: description]` — fal.ai generated. Used for cover image and any concept not visible in the video.
- `[FRAME: 03:42, Mountains and trees blocking afternoon sun]` — video frame at that timestamp.

### Decision logic

The visual moments list from Step 3 is available during writing. For each article section, the LLM checks whether a visual moment matches the content being discussed. If yes, `[FRAME]`. If no (e.g., a section about Thai government policy), `[IMAGE]` or skip.

### Rules

- Cover image is always `[IMAGE]` (fal.ai, 1200x630)
- Inline images default to `[FRAME]` when a relevant visual moment exists
- `[IMAGE]` is fallback for sections with no matching visual moment
- Total inline images: 2-4 per article (frames + fal.ai combined, not counted separately)

### Fallback triggers

fal.ai generates an image instead when:
- Frame extraction fails (yt-dlp error, timestamp issue)
- The extracted frame is unusable (LLM views it and rejects it)
- No visual moment matches a section that needs an image

## What Doesn't Change

- Step 2 (transcript fetch) — VTT file already saved to /tmp, no modification needed
- Cover image workflow — always fal.ai
- Chart generation (Step 5b) — untouched
- WordPress upload — frames are .webp files in output/images/, same as fal.ai
- Compression pipeline — same Pillow + WebP quality 82
- Naming convention — same {slug}-{descriptor}.webp

## Files Modified

| File | Change |
|------|--------|
| `prompts/extract-video-data.md` | Add Visual Moments section with identification rules and output format |
| `SKILL.md` Step 2 | Note that VTT file must be preserved for Step 3 |
| `SKILL.md` Step 3 | Read VTT file alongside clean transcript; add visual moment identification |
| `SKILL.md` Step 5 | Document `[FRAME]` marker alongside `[IMAGE]` |
| `SKILL.md` Step 6 | Split into 6a (frame extraction + quality check) and 6b (fal.ai for cover + remaining `[IMAGE]`) |
| `prompts/visual-media.md` | Add video frame section: dimensions, attribution format, fallback rules |

## New Dependencies

- `ffmpeg` — for extracting frames from downloaded video segments. Likely already installed (yt-dlp uses it).
- No new Python packages.
- No new scripts — frame extraction uses inline bash commands like the existing fal.ai workflow.
