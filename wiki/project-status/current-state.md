# Current state and backlog

> Sources: Obsidian handoff, 2026-08-09; progress.txt, 2026-08-09 entry
> Raw: [Obsidian handoff — current state](../../raw/project-status/2026-08-09-handoff-current-state.md); [progress.txt — session log](../../raw/pipeline/2026-08-09-progress-txt-session-log.md)
> Updated: 2026-09-01

## Overview

As of the 2026-08-09 handoff, `green-thai-video-writer` is status "live": it runs headless on a Windows Task Scheduler trigger into WSL, backend Claude on Max via `CLAUDE_CODE_OAUTH_TOKEN`, pinned `--model sonnet`, scheduled task `GetVideo-GreenThailand` every other Sunday at approximately 10:00 AM. A sibling watchdog task, `Watchdog-GetVideo`, is disabled. The Kimi K2.6 backend block is kept commented out in the runner script as a documented one-edit revert path.

## Immediate next step

Run `/get-video` once on a queued video and confirm it writes a valid `output/sources.json` (Step 4a of the workflow, added 2026-08-09). Once that's proven on a real run, set `REQUIRE_SOURCES_JSON = True` in `scripts/wordpress_upload.py` — today a missing `sources.json` only warns rather than blocking the publish. See [Citation gate](../publishing/citation-gate.md).

## Then

Fix the fal.ai cover-image auth failure that failed the Jul 19 scheduled run and clear the orphan draft it left (post 1554, Banpu energy transition — see [Publish path and verification gate](../publishing/publish-verification-gate.md)). The affected draft should be identified from the Jul 19 entry in `~/scheduled-task-logs/get-video/` or the newest unpublished draft in WP admin; either regenerate its cover and set it, or trash the draft and let the video requeue.

Also still pending confirmation from a real unattended run: the Claude/Max backend line reporting correctly (not Kimi), a "Rendered N chart(s)" line appearing in output, and a normal publish passing cleanly with the `[INTERNAL-LINK]` upload gate in place.

## Backlog

- Add a numeric-claims "VERIFY" block to `SKILL.md` (deferred from a 2026-05-25 plan).
- Load category keyword mapping from `categories.json` rather than the hardcoded `_SUBCATEGORY_KEYWORDS`/`_PILLAR_KEYWORDS` lists in `wordpress_upload.py`.
- Install a `ruff` linter and add it to `/commit`.
- Clean up orphaned WordPress media (IDs 425-428, plus post 720's superseded featured image).
- Remove dead Kimi-leftover scripts `scripts/fix_cover.py` and `scripts/generate_images.py` — artifacts of an earlier manual-publish path, no longer used.
- Drop the commented Kimi-revert blocks from all three GET pipeline runner scripts once the Claude/Max backend has accumulated a few clean scheduled runs.

## Environment notes

Credentials live in the shared `.env` at `~/Documents/green-energy-thailand/.env`, consumed via `~/scripts/get-video-auto.sh` (a Windows/WSL runner script — not tracked in this git repo, disk-only). Local path: `~/Documents/green-energy-thailand/green-thai-video-writer/`. Runs triggered from both Windows Task Scheduler and, indirectly, WSL.

## See Also

- [/get-video pipeline](../pipeline/get-video-workflow.md)
- [Citation gate](../publishing/citation-gate.md)
- [Publish path and verification gate](../publishing/publish-verification-gate.md)
