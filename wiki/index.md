# Knowledge Base Index

## pipeline

The `/get-video` workflow itself: transcript extraction through article writing, and the category taxonomy it classifies against.

| Article | Summary | Updated |
|---------|---------|---------|
| [/get-video pipeline](pipeline/get-video-workflow.md) | The 8-step YouTube-to-WordPress-draft workflow, queue processing, and error handling | 2026-09-01 |
| [Category and pillar classification](pipeline/category-classification.md) | The 8-pillar/subcategory taxonomy, keyword-based auto-derivation, and the 2026-06-19 building-materials gap fix | 2026-09-01 |

## publishing

How a finished article HTML file becomes a verified WordPress draft: chart rendering, citation checking, upload, and post-publish verification.

| Article | Summary | Updated |
|---------|---------|---------|
| [Deterministic chart rendering](publishing/deterministic-chart-rendering.md) | Why `[CHART: {...}]` markers are substituted in code, not by the writing agent, after two transcription bugs shipped broken charts | 2026-09-01 |
| [Citation gate](publishing/citation-gate.md) | The shared pre-upload citation verifier, added 2026-08-09 after post 1786 shipped an unsupported claim | 2026-09-01 |
| [Publish path and verification gate](publishing/publish-verification-gate.md) | `wordpress_upload.py`'s parse/clean/upload path, the 9-check `verify_publish.py` gate, and the incidents (post 1052, stale-republish, fal.ai auth) that built it | 2026-09-01 |

## project-status

Current operating state and open work.

| Article | Summary | Updated |
|---------|---------|---------|
| [Current state and backlog](project-status/current-state.md) | Live headless Sunday runs, immediate next steps (sources.json validation, fal.ai cover fix), and the backlog | 2026-09-01 |
