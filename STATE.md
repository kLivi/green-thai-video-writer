---
# FORMAT: see /HANDOFF-TEMPLATE.md for schema. Do not remove frontmatter fields.
name: "Green Thai Video Writer"
repo_path: "~/Documents/green-energy-thailand/green-thai-video-writer"
business: "Green Energy Thailand"
status: "live"
updated: 2026-11-26
next: "Refill the queue"
---

# Green Thai Video Writer

Video-to-article pipeline for greenenergythailand.com: YouTube URL → transcript → article → WordPress draft.

## Next Step

1. **Refill the queue** (2026-11-25) 11-22 run found no vetted videos; scheduled runs idle until Keith adds `VETTED:` lines to `queue/video-queue.txt`. blocked-on: keith. closes-when: a scheduled run starts on a vetted video
2. **Resolve orphan drafts 1554 and 2145** (2026-11-25) both failed verification (1554: fal.ai cover auth error Jul 19; 2145: 10-25 run). Regenerate cover and set it, or trash the draft. closes-when: neither is an unresolved WP draft

## Current Focus

Live and automated. Backend is Claude/Max (`--model sonnet`); the Kimi K2.6 block stays commented in the runner as a one-edit revert.

## Key Files & Data Model

- **Invariant:** WordPress is source of truth after publish; never re-upload local HTML over a published post.
- **[source of truth]** `SKILL.md`, `prompts/`, `scripts/`, `queue/video-queue.txt` · **[derived, never hand-edit]** `output/`, `wiki/` (built from `raw/`)
- `../../shared/citation_gate.py` runs inside `wordpress_upload.py` before any WP API call; cannot be flag-disabled. Blocks publish if a cited page lacks its number, or if `sources.json` is missing (`REQUIRE_SOURCES_JSON = True`; an uncited article must emit `{"sources": []}`).
- `scripts/research_gate.py` resolves `internal-verified` sources from `thai-facts.md`'s allowlist and re-slices web quotes verbatim from the fetched page.
- `scripts/verify_publish.py::check_self_citations()` hard-fails a publish that cites its own brand/internal file (shared detector `../../shared/self_citations.py`).
- Video-only claims are attributed in prose, never given an invented URL record.

## How to Run

- **Automated:** task `GetVideo-GreenThailand` runs `/get-video queue` every other Sunday ~10:00 via `~/scripts/get-video-auto.sh` (untracked; exports `CLAUDE_CODE_OAUTH_TOKEN`). Agent writes article + manifest; the shell renders charts, uploads `--verify`, consumes the queue, commits.
- **Manual:** Claude Code in the repo, `/get-video queue` or `/get-video "<url>"`.
- Logs: `~/scheduled-task-logs/get-video/`. `Watchdog-GetVideo` is disabled.

## Known Issues

- ⚠️ A manifest without `queue_line` leaves the queue line unconsumed, so the next run can republish the same video (11-01 post 2166, line 71 marked DONE by hand).
- ⚠️ `research_gate.py` is proven against a fixture; scheduled run logs don't show whether the agent invoked it on real output.

## Backlog

- [ ] **Numeric-claims VERIFY block in SKILL.md** (2026-05-25) 11-15 run had 4 UNSOURCED numbers (advisory). closes-when: SKILL.md carries the block
- [ ] **Category keyword mapping from `categories.json`** (2026-05-25) closes-when: upload reads categories from the file
- [ ] **Install ruff and add to `/commit`** (2026-05-25) closes-when: `/commit` runs ruff
- [ ] **Clean orphaned WP media** (2026-07-19) IDs 425–428 plus Post 720's superseded featured image. closes-when: those media IDs are deleted
- [ ] **Remove dead scripts `scripts/fix_cover.py`, `scripts/generate_images.py`** (2026-09-12) one-off leftovers of the old manual-publish path. closes-when: files gone
- [ ] **Drop commented Kimi revert blocks from all three runners** (2026-08-07) Max backend has clean scheduled runs since. closes-when: no Kimi block in the runners
