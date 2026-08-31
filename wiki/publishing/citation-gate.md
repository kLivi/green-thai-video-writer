# Citation gate

> Sources: shared/citation_gate.py, 2026-08-09; scripts/wordpress_upload.py, 2026-08-09; progress.txt, 2026-08-09 entry
> Raw: [shared citation_gate.py](../../raw/publishing/2026-08-09-citation-gate-shared-script.md); [wordpress_upload.py](../../raw/publishing/2026-08-09-wordpress-upload-script.md); [progress.txt — session log](../../raw/pipeline/2026-08-09-progress-txt-session-log.md)
> Updated: 2026-09-01

## Overview

`run_citation_gate()` verifies every cited statistic in an article's `output/sources.json` before `wordpress_upload.py` makes any WordPress API call, and it cannot be disabled by a flag. It lives in `../../shared/citation_gate.py` — one file shared by all three "GET" pipelines (`claude-blog`, `green-thai-idea-writer`, `green-thai-video-writer`) — alongside `verify_citations.py`, which does the actual per-citation fetch-and-check.

## Why it was added (2026-08-09)

The gate originally existed only inside `claude-blog`'s own `wordpress_upload.py`. Neither `green-thai-idea-writer` nor this pipeline (`green-thai-video-writer`) had it — each carried its own copy of the upload script and never inherited the check — so their headless runs could publish unverified citations. That gap is how post 1786 shipped a claim its cited source did not actually make. The fix pulled the gate into a shared module so a future fix to either half lands in all three pipelines at once, and wired it into this pipeline's `wordpress_upload.py` the same day, alongside adding Step 4a to `SKILL.md` (writing `output/sources.json` during research).

## Mechanism

`run_citation_gate(html_file, require_sources=..., notify=..., log_blocks=...)` looks for `sources.json` next to the article's HTML file. If `require_sources=False` (this pipeline's current setting — `REQUIRE_SOURCES_JSON = False` in `wordpress_upload.py`) and the file is missing, it prints a "gate not yet mandatory here" message and returns without blocking. When `sources.json` is present, the gate fetches each cited URL and checks that the page actually carries the claimed number; it also warns (without hard-failing) when the recorded `quote` field isn't found verbatim on the page. A hard citation failure exits the process with a dedicated code (`CITATION_FAIL_EXIT = 3`, distinct from a generic `exit 1`) so a calling shell script can treat it as "do not retry" and must not consume the queue entry. The canonical Thai facts file it checks `"thai-facts"`-typed claims against lives at `claude-blog/shared/thai-facts.md` — a path referenced from all three pipelines' `CLAUDE.md` files, deliberately left there when the Python moved to `shared/` so the documented path stayed valid.

## Current gap

`REQUIRE_SOURCES_JSON` is still `False` in this pipeline's `wordpress_upload.py` as of 2026-08-09 — a missing `sources.json` only warns, it does not block. The Next Step recorded in the handoff is to run `/get-video` once on a queued video, confirm it actually writes a valid `output/sources.json`, and only then flip `REQUIRE_SOURCES_JSON = True`.

## See Also

- [/get-video pipeline](../pipeline/get-video-workflow.md) — Step 4a, where `sources.json` is written
- [Publish path and verification gate](publish-verification-gate.md)
- [Current state and backlog](../project-status/current-state.md)
