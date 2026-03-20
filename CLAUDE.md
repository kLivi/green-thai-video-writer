# Green Thai Video Writer

Video-to-article pipeline for greenenergythailand.com. Takes a YouTube URL, extracts transcript, analyzes for key data, gets user approval on the article angle, then writes and publishes a WordPress draft.

## Commands

- `/get-video "https://youtube.com/watch?v=..."` — Process a single video URL
- `/get-video queue` — Process next vetted URL from `queue/video-queue.txt`

## Key Rules

- **Anti-fabrication**: Never fabricate personal experience or statistics. Use `[UNIQUE INSIGHT]` for novel data analysis. Every number needs a named source.
- **Approval gate**: Manual URLs pause after Step 3 for user approval. Vetted queue videos (`VETTED:`/`VETTED-RESEARCH:`/`VETTED-SERIES:`) skip the gate and run end-to-end.
- **Thai context**: Enhance with Thai-specific info (permits, MEA/PEA, rates, incentives) not present in the video.
- **Thai legal claims**: Laws not published in Royal Gazette get a disclaimer.
- **Image style**: "natural lighting, candid photo, realistic" — NOT professional/cinematic.
- **Image naming**: `{slug}-{descriptor}.webp` — cover uses `featured`.
- **Compression**: Pillow resize → WebP quality 82. Cover: 1200x630, inline: 650x366 / 450x600 / 550x550.
- **Charts**: SVG with currentColor (dark-mode safe), transparent bg, source attribution.
- **HTML output**: Full HTML document with `<head>` (title, meta) and `<body><article>`. NOT markdown with frontmatter.

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
