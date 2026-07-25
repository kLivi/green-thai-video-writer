# Chart Generation Rules — Inline SVG Data Visualization

## The one rule

**Emit a `[CHART: {...}]` marker. Never write SVG. Never run `build_chart.py`
yourself. Never paste its output.**

A deterministic step (`scripts/render_charts.py`) replaces every marker with a
built chart and rasterizes the result to confirm it actually draws. It runs in
the pipeline before upload, and again as a safety net inside
`wordpress_upload.py`. A chart that fails to build or renders wrong **stops the
publish** — nothing reaches WordPress.

This division exists because the transcription step used to be yours, and it
kept going wrong in ways that were invisible until the article was live:

- **2026-06-30** — a `\[CHART:.*?\]` regex stopped at the first `]` inside
  `"labels":[...]` and left truncated JSON in the post.
- **2026-07-25 (post 1590)** — a hand-copied `<text>` element was closed with
  `</title>`. One token. The chart published as an empty cream box.

Choosing the data and the chart type is judgment, and it is yours. Turning that
choice into markup is mechanical, and it is not.

## When to create a chart

Place a marker when the research supports it:

- 3+ comparable metrics (e.g. cost per kWh across battery types)
- Trend data over time (e.g. solar capacity growth 2020-2026)
- Before/after comparisons (e.g. pre- vs post-subsidy costs)
- Parts of a whole (e.g. Thailand's energy mix breakdown)

Target 1-2 charts per article. Skip charts if the data doesn't warrant one — a
chart of two numbers is worse than a sentence.

## Chart type selection

Never repeat a chart type within one post.

| Data pattern | Type |
|---|---|
| Ranked factors / correlations | `lollipop` |
| Percentage improvement / single-metric comparison | `horizontal-bar` |
| Parts of whole / market share | `donut` |
| Trend over time | `line` |
| Distribution / cumulative | `area` |
| Before/after, A vs B | `grouped-bar` |

## Marker format

One JSON object, inline in the HTML, where the chart should appear:

```html
[CHART: {"type":"horizontal-bar","title":"Battery Cost by Technology","data":{"labels":["Lithium-ion","Sodium-ion","Iron-air"],"values":[139,87,65]},"source":"BloombergNEF 2025"}]
```

**Fields**

| Field | Required | Notes |
|---|---|---|
| `type` | yes | one of the six types above |
| `title` | yes | shown at the top of the card |
| `data` | yes | see below |
| `source` | strongly preferred | rendered as "Source: …" in the footer |
| `unit` | no | short domain label in the amber eyebrow (`"MW"`, `"US$ / MWh"`) |

**Data shapes**

- Most types: `{"labels": [...], "values": [...]}`
- `grouped-bar`: `{"labels": [...], "series": [{"name": "A", "values": [...]}]}`
- `data.highlight` — a label to pick out in amber
- `data.center_text` — center label for `donut` (e.g. `"27.76M tons/yr"`)

Raw numbers only — write `105000`, not `"105,000"` or `"105k"`. The renderer
formats and groups them, and it sizes the bars around the formatted width.

## What the renderer guarantees

You don't control any of this, and shouldn't try to:

- **Editorial data-exhibit card** — cream panel (`#f3f0e8`) with a hairline
  border, so the figure reads as an exhibit set apart from body text.
- **One hue for magnitude** — forest green (`#2d5016`), amber (`#c67b33`) for a
  highlighted item and line/area endpoints. Magnitude charts are not rainbows.
- **Baked charcoal ink** — the site is light-only, and a baked light panel needs
  guaranteed-dark text. (This is deliberate: no `currentColor`, no dark-theme flip.)
- **Lora / IBM Plex Sans / Source Serif** — already loaded on the frontend.
- **Single-line output** — WordPress' `wpautop` injects `<p>` tags at newlines
  inside inline SVG and shatters the graphic. The renderer emits no newlines.
- **Labels that fit** — bar and lollipop value labels reserve their own width,
  so a long number can't be clipped at the card edge.
- **Accessible markup** — `role="img"`, `aria-label`, and `<title>`.

## If a chart fails

The renderer exits non-zero with the offending marker's title and reason, and
the article is not published. Fix the marker — bad chart type, empty `values`,
malformed JSON, a category label so long it overruns the card — and re-run.
Do not work around it by pasting SVG.
