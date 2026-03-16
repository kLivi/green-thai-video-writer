# Green Thai Video Writer

**Status:** Live — first article published as WP draft
**Last Updated:** 2026-03-16

## What This Is

Pipeline 2: Takes a YouTube URL → extracts transcript → analyzes for key data → proposes article angle for user approval → enhances with Thai context → writes article → generates images and charts → publishes as WordPress draft.

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

## Next Steps

- Simplify `wordpress_upload.py` — the category keyword mapping is long; consider loading from `categories.json` instead of hardcoding
- Install a Python linter (ruff) and add to `/commit` quality checks
- Clean up orphaned media in WP from failed upload attempts (IDs 425–428)
- Process more videos from the queue or `get-yt-vid-ideas.csv`

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
└── SPEC.md                   # Original spec (reference)
```

## Video Sources

- **Curated list**: `curated-videos.md` — ~10 hand-picked videos across 5 categories
- **Full pool**: `get-yt-vid-ideas.csv` — 218 URLs across 9 topics
- **Manual**: paste any YouTube URL directly

## Related Projects

- `~/Documents/green-energy-thailand/green-thai-idea-writer/` — Pipeline 1 (idea → article)
- `~/Documents/green-energy-thailand/claude-blog/` — Reference implementation
- Target site: greenenergythailand.com

## Changes (2026-03-16)

### wordpress_upload.py
- **Category mapping fixed**: `derive_category()` now returns `(pillar, subcategory)` matching the actual WordPress taxonomy (queried from the live site). Old mapping had wrong names (e.g. "Wind Energy" → corrected to "Wind Power").
- **Never creates categories**: `get_or_create_category()` → renamed to `find_category()`. Only looks up existing categories; warns if not found.
- **RankMath fix**: SEO meta fields removed from WP REST API `post.meta` (RankMath blocks it). Now set via RankMath's own `/wp-json/rankmath/v1/updateMeta` endpoint after post creation.
- **Subcategory support**: Posts now get assigned both the pillar and subcategory IDs.
- **HTML entity decoding**: Category name comparison decodes `&amp;` before matching.

### categories.json
- Updated to match actual WordPress taxonomy names (e.g. "Installation, Permits & Grid Connection" not "Solar Installation & Permits").

### First article published
- Video: "Thailand: Renewable Energy Revolution" (ADB Partnerships) → WP draft ID 434
- Category: Policy, Economics & Thailand Context → National Energy Goals & Plans
- 4 images, 2 SVG charts, ~2,100 words

## Dependencies

- Python 3.12+ with: requests, beautifulsoup4, pillow, yt-dlp
- yt-dlp CLI (for transcript extraction)
- fal.ai API key (for image generation)
- WordPress Application Password (for draft publishing)
