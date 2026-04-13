# Green Thai Video Writer

Video-to-article pipeline for greenenergythailand.com. Takes a YouTube URL, extracts transcript, analyzes for key data, gets user approval on the article angle, then writes and publishes a WordPress draft.

## Commands

- `/get-video "https://youtube.com/watch?v=..."` — Process a single video URL
- `/get-video queue` — Process next vetted URL from `queue/video-queue.txt`

## Tech Stack

- Content rules: `prompts/content-rules.md`
- Video data extraction: `prompts/extract-video-data.md`
- Thai context enrichment: `prompts/thai-context.md`
- Image generation: fal.ai Seedream v4.5 via `prompts/visual-media.md`
- Image processing: Pillow resize + WebP (see `scripts/wordpress_upload.py`)
- Chart generation: SVG builder via `prompts/chart-rules.md` + `scripts/build_chart.py`
- Research: Brave Search API
- **Thai legal claims**: Laws not published in Royal Gazette get a disclaimer

## Handoff

Session state lives at: `/home/unify/Documents/Brain/green-energy-thailand/green-thai-video-writer/handoff.md`

## Environment

- `.env` symlinked from idea-writer (shared credentials)
- `IMAGE_API_KEY` — fal.ai API key
- `WORDPRESS_URL`, `WORDPRESS_USERNAME`, `WORDPRESS_APP_PASSWORD` — WordPress REST API
- `BRAVE_SEARCH_API_KEY` — for supplementary research
- Python 3.12+ with requests, beautifulsoup4, pillow, yt-dlp

## Project Context

Part of the green-thai blog ecosystem:
- Idea Writer: `/home/unify/Documents/green-energy-thailand/green-thai-idea-writer/`
- Claude Blog (reference): `/home/unify/Documents/green-energy-thailand/claude-blog/`
- Target site: greenenergythailand.com
