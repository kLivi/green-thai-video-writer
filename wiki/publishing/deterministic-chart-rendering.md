# Deterministic chart rendering

> Sources: scripts/render_charts.py, 2026-07-25; progress.txt, 2026-07-25 entry
> Raw: [render_charts.py](../../raw/publishing/2026-07-25-render-charts-script.md); [progress.txt — session log](../../raw/pipeline/2026-08-09-progress-txt-session-log.md)
> Updated: 2026-09-01

## Overview

Chart substitution — turning a writer-emitted `[CHART: {...}]` marker into an inline `<svg>` — happens entirely in code, not in the writing agent. `scripts/render_charts.py` extracts each marker with `json.JSONDecoder().raw_decode()` (which consumes exactly one JSON value and reports where it ended, rather than a regex trying to find a closing bracket), calls `build_chart()` on the parsed spec, inspects the resulting SVG with `chart_inspect.py`, and either substitutes it in place or fails the whole render loudly (exit 1). The agent's only job is to emit the marker; it must never run `build_chart.py` itself, never capture its stdout, and never hand-edit SVG into the article.

## Why: two transcription bugs it replaced

Both incidents happened when a human/LLM step stood between the chart JSON and the published SVG:

- **2026-06-30** — a naive `\[CHART:.*?\]` regex stopped at the first `]` character inside a `"labels":[...]` array, leaving a truncated JSON fragment in the published post.
- **2026-07-25 (post 1590)** — the writing agent hand-transcribed `build_chart.py`'s SVG output and typed `...Fuel Type</title>` where the source emitted `</text>`. That one-token substitution meant the `</title>` never closed the `<text>` element, the HTML parser swallowed the rest of the graphic, and the chart rendered as an empty box.

Both were transcription failures, not chart-logic failures — `render_charts.py` removes the transcription step entirely: markers in, SVG out, no model in the loop. This made the class of bug the 2026-06-30 regex hit structurally impossible, since `raw_decode()` cannot be truncated by a bracket appearing inside a JSON array.

## Mechanism detail

For each marker, `render_markers()` requires the JSON object to contain `type`, `title`, and `data` (missing any raises `ChartMarkerError` naming the offset and the missing field). It calls `build_chart(type, title, data, subtitle=..., source=..., unit=...)`, then immediately inspects the SVG it just built with `chart_inspect.inspect_svg()` — a chart that renders wrong is treated as seriously as one that fails to build, because this is "the last point where stopping is cheap." After substitution, it scans the rendered output for any leftover `[CHART` text; a survivor means the extraction loop missed a marker form the code doesn't handle, and raises rather than letting raw JSON reach WordPress.

This module is ported byte-for-byte from `green-thai-idea-writer`, alongside `chart_inspect.py`. `scripts/build_chart.py` itself was re-synced from the other two pipelines at the same time — this repo's copy had drifted and was missing `_fit_end_x`, a value-label clip fix already present in `claude-blog`'s copy; all three repos' `build_chart.py` are now byte-identical.

## Marker format change (2026-07-25)

This pipeline previously used a pipe-delimited chart marker (`[CHART: type|title|json|source=…]`) that the shared JSON-based renderer cannot parse — reusing `render_charts.py` unmodified would have hard-failed every publish. `SKILL.md` Step 5b and `prompts/chart-rules.md` were rewritten the same day to specify the same JSON marker format used by the other two pipelines, and the skill was reinstalled.

## Where it runs

`wordpress_upload.py` also calls the render step inside `parse_article()` as a safety net, so no upload path can reach WordPress with a raw, unrendered marker or an SVG that failed inspection. The Sunday scheduled runner (`~/scripts/get-video-auto.sh`, not git-tracked) renders charts before the publish step and posts a Discord failure embed + exits non-zero if rendering fails.

## See Also

- [/get-video pipeline](../pipeline/get-video-workflow.md) — Step 5b/6, where the writing agent emits and then ignores chart markers
- [Publish path and verification gate](publish-verification-gate.md) — the post-publish check that a chart actually rendered, not merely that an `<svg>` exists
