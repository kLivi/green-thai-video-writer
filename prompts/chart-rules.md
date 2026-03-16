# Chart Generation Rules — Inline SVG Data Visualization

Generate dark-mode-compatible inline SVG charts when article data supports it.

## When to Create Charts

Place a `[CHART]` marker when research data has:
- 3+ comparable metrics (e.g., cost per kWh across battery types)
- Trend data over time (e.g., solar capacity growth 2020-2026)
- Before/after comparisons (e.g., pre- vs post-subsidy costs)
- Parts of a whole (e.g., Thailand's energy mix breakdown)

Target 1-2 charts per article. Not every article needs one — skip charts if
the data doesn't warrant visualization.

## Chart Type Selection

Select based on the data pattern. Never repeat a chart type within one post.

| Data Pattern | Best Chart Type |
|-------------|-----------------|
| Before/after comparison | Grouped bar chart |
| Ranked factors / correlations | Lollipop chart |
| Parts of whole / market share | Donut chart |
| Trend over time | Line chart |
| Percentage improvement | Horizontal bar chart |
| Distribution / range | Area chart |
| Multi-dimensional scoring | Radar chart |

## Styling Rules (Non-Negotiable)

All charts must work on both dark and light backgrounds:

```
Text elements:     fill="currentColor"
Grid lines:        stroke="currentColor" opacity="0.08"
Axis lines:        stroke="currentColor" opacity="0.3"
Background:        transparent (no fill on root SVG)
Subtitle text:     fill="currentColor" opacity="0.45"
Source text:        fill="currentColor" opacity="0.35"
Label text:        fill="currentColor" opacity="0.8"
```

### Color Palette

| Color | Hex | Use Case |
|-------|-----|----------|
| Orange | `#f97316` | Primary / highest value |
| Sky Blue | `#38bdf8` | Secondary / comparison |
| Purple | `#a78bfa` | Tertiary / special category |
| Green | `#22c55e` | Quaternary / positive indicator |

For text inside colored elements: `fill="white"` with `font-weight="800"`.

## SVG Shell

```html
<figure>
  <svg
    viewBox="0 0 560 380"
    style="max-width: 100%; height: auto; font-family: 'Inter', system-ui, sans-serif"
    role="img"
    aria-label="Chart description with key data point"
  >
    <title>Chart Title</title>
    <desc>Description for screen readers with all key data points and source</desc>

    <!-- Chart content -->

    <text x="280" y="372" text-anchor="middle" font-size="10" fill="currentColor" opacity="0.35">
      Source: Source Name (Year)
    </text>
  </svg>
</figure>
```

## Chart Type Construction

### Horizontal Bar Chart

Best for: percentage improvements, single-metric comparisons.

1. Define chart area: x=80, y=40, width=440, height=280
2. Calculate bar height: `chartHeight / dataCount - gap` (gap=8)
3. Calculate bar width: `(value / maxValue) * chartWidth`
4. Position bars: `y = chartY + index * (barHeight + gap)`
5. Label on left (right-aligned at x=75): category name
6. Value label at end of bar: percentage or number
7. Source text at bottom center

### Grouped Bar Chart

Best for: before/after, A vs B comparisons.

1. Define groups along Y axis, bars within each group
2. Use 2 colors (primary + secondary) for the two series
3. Add legend at top: colored square + label for each series
4. Gap between groups > gap within groups

### Donut Chart

Best for: parts of whole, market share.

1. Center: cx=280, cy=180, outer radius=140, inner radius=80
2. Calculate arc segments using cumulative angles
3. Each segment: `<path d="M... A... L... A... Z" fill="color" />`
4. Center text: total or key label
5. Legend below chart with color squares + labels + values

### Line Chart

Best for: trends over time.

1. X axis: time periods, evenly spaced
2. Y axis: value range with 4-5 grid lines
3. Draw grid lines: `stroke="currentColor" opacity="0.08"`
4. Plot data points: `<circle cx=... cy=... r="4" fill="color" />`
5. Connect with: `<polyline points="..." fill="none" stroke="color" stroke-width="2" />`
6. Optional: area fill below line with `opacity="0.1"`

### Lollipop Chart

Best for: ranked factors, correlations.

1. Horizontal orientation (like bar chart but with circles)
2. Thin line from axis to data point: `stroke="currentColor" opacity="0.15" stroke-width="1"`
3. Circle at data point: `r="6"` with fill color
4. Value label next to circle
5. Categories on Y axis (left-aligned)

### Area Chart

Best for: distribution, cumulative data.

1. Same as line chart but with filled area below
2. Area fill: `<path d="M... L... L... Z" fill="color" opacity="0.15" />`
3. Line on top: `stroke="color" stroke-width="2" fill="none"`
4. Grid lines behind the area

### Radar Chart

Best for: multi-dimensional scoring (5-7 axes).

1. Center: cx=280, cy=190
2. Draw concentric polygons for grid (3-4 levels)
3. Calculate axis endpoints at equal angles
4. Plot data points on each axis proportional to value
5. Connect data points with filled polygon: `fill="color" opacity="0.2" stroke="color"`
6. Label each axis at the outer edge

## Quality Checklist

- [ ] No hardcoded text colors (all use `currentColor`)
- [ ] No white/light backgrounds (transparent or none)
- [ ] Source attribution text present at bottom
- [ ] `role="img"` and `aria-label` present on `<svg>`
- [ ] `<title>` and `<desc>` present inside `<svg>`
- [ ] Chart type not already used in this post
- [ ] Data values match the source data exactly
- [ ] Color palette uses only approved colors
- [ ] ViewBox is `0 0 560 380`
