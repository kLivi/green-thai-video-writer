# Project overview

YouTube-to-WordPress article pipeline for greenenergythailand.com. Takes a YouTube URL, extracts the transcript via yt-dlp, analyzes for key data, proposes an article angle for user approval, enhances with Thai context (permits, rates, incentives), generates images and charts, then publishes as a WordPress draft with full SEO metadata.

## Tech stack

- **Language**: Python 3.12+
- **Upload script**: requests, BeautifulSoup 4, Pillow (WordPress REST API + RankMath API)
- **Transcript**: yt-dlp CLI (auto-generated subtitles)
- **Image generation**: fal.ai Seedream v4.5 API
- **Image processing**: Pillow (resize + WebP conversion)
- **Charts**: Inline SVG (dark-mode compatible, currentColor)
- **SEO**: RankMath REST API, JSON-LD schema (@graph with BlogPosting, FAQPage, BreadcrumbList)
- **Orchestrator**: Claude Code skill (SKILL.md)
- **CMS**: WordPress (Cloudways) via REST API

## Git Status

Working Directory: /home/unify/Documents/green-energy-thailand/green-thai-video-writer
Current Branch: master
Remote: origin → https://github.com/kLivi/green-thai-video-writer.git

### What Versions to Keep
✅ CURRENT/KEEP: master branch — all changes pushed
✅ CURRENT/KEEP: .env symlink → ../green-thai-idea-writer/.env (shared credentials)
❌ OLD/IGNORE: SPEC.md — describes a TypeScript project that was never built (project is a Claude Code skill + Python script)

## Current status

**Pipeline working end-to-end.** First article published as WP draft (Post ID 434). Pipeline: transcript extraction → data analysis → user approval gate → article writing → image generation → chart generation → WordPress upload with RankMath SEO, schema JSON-LD, and category assignment.

**Codebase audit completed (2026-03-16):**
- Dependencies updated: `html.unescape()` replaces manual decoder, `Image.Resampling.LANCZOS` replaces old constant
- content-rules.md HTML Output section aligned with SKILL.md and upload script
- 4 minor findings documented but not yet addressed (step counter, SSL warnings, frameborder, stale SPEC.md)

**First article published:**
- Video: "Thailand: Renewable Energy Revolution" (ADB Partnerships) → WP draft ID 434
- Category: Policy, Economics & Thailand Context → National Energy Goals & Plans
- 4 images, 2 SVG charts, ~2,100 words

## Active step

1. Process more videos from the queue (`queue/video-queue.txt`) or `get-yt-vid-ideas.csv`
2. Simplify `wordpress_upload.py` — category keyword mapping is long; consider loading from `categories.json` instead of hardcoding
3. Install a Python linter (ruff) and add to `/commit` quality checks
4. Clean up orphaned media in WP from failed upload attempts (IDs 425–428)
5. Fix remaining audit findings: step counter mismatch, scoped SSL warning suppression, deprecated `frameborder` attribute

## How to Use

```
/get-video "https://youtube.com/watch?v=..."
```

Or process the next video in the queue:
```
/get-video queue
```

### Approval Flow

After transcript extraction and data analysis, the skill presents a proposal:
- Proposed title and angle
- Key data points extracted
- Category mapping
- Outline

**You must approve before the article is written.** You can approve, suggest changes, or skip.

## Installation

Already done. To reinstall after changes:

```bash
cd /home/unify/Documents/green-energy-thailand/green-thai-video-writer
./install.sh
# Restart Claude Code
```

## File Structure

```
green-thai-video-writer/
├── SKILL.md              # Main skill — orchestrates the full pipeline
├── CLAUDE.md             # Project rules and context
├── prompts/
│   ├── content-rules.md      # Writing persona and quality (shared w/ idea-writer)
│   ├── visual-media.md       # Image generation rules (shared w/ idea-writer)
│   ├── chart-rules.md        # SVG chart rules (shared w/ idea-writer)
│   ├── extract-video-data.md # Video transcript data extraction
│   ├── thai-context.md       # Thai-specific enhancement context
│   └── video-article-template.md  # Article structure for video content
├── scripts/
│   └── wordpress_upload.py   # WP REST API upload (shared w/ idea-writer)
├── src/config/
│   └── categories.json       # 8 pillars + subcategories (matches live WP taxonomy)
├── queue/
│   └── video-queue.txt       # URLs to process (batch mode)
├── output/                   # Generated articles and images
│   └── images/               # WebP images for current article
├── .gg/commands/
│   └── commit.md             # /commit command — quality checks + AI commit message
├── .env -> ../green-thai-idea-writer/.env  # Shared credentials (symlink)
├── install.sh                # Deploy skill to ~/.claude/skills/
├── curated-videos.md         # Hand-picked videos by topic
├── get-yt-vid-ideas.csv      # 218 video URLs (raw pool)
└── SPEC.md                   # Original spec (historical — describes unbuilt TS project)
```

## Video Sources

- **Curated list**: `curated-videos.md` — ~10 hand-picked videos across 5 categories
- **Full pool**: `get-yt-vid-ideas.csv` — 218 URLs across 9 topics
- **Manual**: paste any YouTube URL directly

## Related Projects

- `~/Documents/green-energy-thailand/green-thai-idea-writer/` — Pipeline 1 (idea → article)
- `~/Documents/green-energy-thailand/claude-blog/` — Reference implementation
- Target site: greenenergythailand.com


