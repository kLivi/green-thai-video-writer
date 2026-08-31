# Green Thai Video Writer — Obsidian handoff (current state)

> Source: /home/unify/Documents/Brain/green-energy-thailand/green-thai-video-writer/handoff.md
> Collected: 2026-09-01
> Published: 2026-08-09

---
# FORMAT: see /HANDOFF-TEMPLATE.md for schema. Do not remove frontmatter fields.
name: "Green Thai Video Writer"
repo_path: "~/Documents/green-energy-thailand/green-thai-video-writer"
business: "Green Energy Thailand"
status: "live"
updated: "2026-08-09"
---
# Green Thai Video Writer

Video-to-article pipeline for greenenergythailand.com. YouTube URL → transcript → article → WordPress draft.

**Status:** Live — automated headless Sunday runs (Claude/Max, sonnet). Watchdog-GetVideo disabled.
**Last Updated:** 2026-08-09

## Next Step

**Run `/get-video` once on a queued video and confirm it writes a valid `output/sources.json`** (Step 4a, added 2026-08-09). Once proven, set `REQUIRE_SOURCES_JSON = True` in `scripts/wordpress_upload.py` — today a missing file only warns.

Then: fix the fal.ai cover-image auth failure that failed the Jul 19 run and clear the orphan draft it left. Symptom: `fal-ai/bytedance` returns an auth error, the featured image falls back to an inline frame, and the `-featured` cover check fails the publish gate. Identify the affected draft from the Jul 19 entry in `~/scheduled-task-logs/get-video/` (or the newest unpublished draft in WP admin); either regenerate its cover and set it, or trash it and let the video requeue.

Also still pending an unattended run: Claude/Max backend line (not Kimi), "Rendered N chart(s)", and a normal publish with the `[INTERNAL-LINK]` upload gate in place.

## Citation Gate (2026-08-09)

This pipeline had **no** citation verification until now. The shared gate (`../../shared/citation_gate.py`, also used by claude-blog and idea-writer) runs inside `wordpress_upload.py` before any WordPress API call and cannot be flag-disabled. It fetches every URL in `output/sources.json` and blocks the publish if a cited page doesn't carry its number; it also warns when the recorded quote isn't on the page. Note for this pipeline: a claim sourced only to the video is not a web citation — attribute it in prose, don't invent a URL record. Spec: `claude-blog/spec-citation-gate-portability.md`.

## How to Run

**Automated** — scheduled task `GetVideo-GreenThailand` runs `/get-video queue` headlessly every other Sunday ~10:00 AM. Backend is Claude/Max, pinned `--model sonnet`; auth is `CLAUDE_CODE_OAUTH_TOKEN` in the shared `.env`, exported by `~/scripts/get-video-auto.sh` (untracked, disk only). The Kimi K2.6 block is kept commented in that runner as a one-edit revert.
- Manual run: open Claude Code in the repo, run `/get-video queue`
- `Watchdog-GetVideo` is disabled.

## Backlog

- [ ] Add a numeric-claims "VERIFY" block to SKILL.md (deferred from the 2026-05-25 plan)
- [ ] Category keyword mapping — load from `categories.json`
- [ ] Install ruff linter and add to `/commit`
- [ ] Clean up orphaned WP media (IDs 425–428, plus Post 720's superseded featured image)
- [ ] Remove dead Kimi-leftover scripts `scripts/fix_cover.py` + `scripts/generate_images.py` (artifacts of the old manual-publish path)
- [ ] Drop the commented Kimi revert blocks from all three runners once the Max backend has a few clean scheduled runs behind it

## Tech Stack

- **Local path:** `~/Documents/green-energy-thailand/green-thai-video-writer/`
- **Runs on:** both (Windows Task Scheduler triggers WSL)
