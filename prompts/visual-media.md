# Visual Media Integration -- Images, Charts & Cover Images

## Cover Images & OG Images

Every blog post should have a cover image for social sharing and blog listings.

### Option 1: AI-Generated Cover (fal.ai Seedream)

Generate a cover image via fal.ai Seedream v4.5 using custom dimensions 1200×630:
- OG-compatible dimensions, no resizing needed
- Generate via Phase 5.5 of the blog-write workflow

**Sizing:**
| Use Case | Dimensions | Notes |
|----------|-----------|-------|
| Blog hero/cover | 1200×630 | OG-compatible featured image |
| Open Graph (OG) | 1200×630 | Same as cover |
| Twitter card | 1200×630 | Same as cover |

### Option 2: Generated SVG Cover (via blog-chart)

For branded or data-driven covers, generate via `blog-chart`:
- Text-on-gradient with title and key statistic
- Dark-mode compatible (use `currentColor` where possible)
- Include blog name/author subtle branding
- ViewBox: `0 0 1200 630` for OG compatibility

### Frontmatter Fields

```yaml
---
title: "..."
description: "..."
coverImage: "https://fal.media/files/.../cover.jpg"
coverImageAlt: "Descriptive sentence about the cover image"
ogImage: "https://fal.media/files/.../cover.jpg"  # Same as cover
date: "YYYY-MM-DD"
---
```

- `coverImage`: displayed as hero at the top of the post
- `ogImage`: used for social sharing previews (Open Graph / Twitter Card)
- If only one image, use the same URL for both fields
- Alt text is required for the cover image

### When to Use Each Option

| Scenario | Recommendation |
|----------|---------------|
| General topic | AI-generated cover via fal.ai (1200×630) |
| Data-heavy article | Generated SVG with key stat highlight |
| Brand-focused | Generated SVG with brand colors |
| Tutorial/how-to | Screenshot or AI-generated contextual image |

---

## Image Generation (fal.ai Seedream v4.5)

All blog images are AI-generated using fal.ai's Seedream v4.5 model. Images are
generated in Phase 5.5 of the blog-write workflow, after the article is written.

**Requires:** `IMAGE_API_KEY` environment variable set with your fal.ai API key.

### API Reference

**Submit a generation job:**
```bash
curl -s -X POST "https://queue.fal.run/fal-ai/bytedance/seedream/v4.5/text-to-image" \
  -H "Authorization: Key $IMAGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"...","image_size":{"width":1200,"height":630},"num_images":1}'
```

The response includes `status_url` and `response_url` — use these for polling (do not construct URLs manually).

**Poll for completion:**
```bash
curl -s "$STATUS_URL" \
  -H "Authorization: Key $IMAGE_API_KEY"
```

**Retrieve result:**
```bash
curl -s "$RESPONSE_URL" \
  -H "Authorization: Key $IMAGE_API_KEY"
```

Image URL is in `images[0].url` (hosted at `fal.media`).

### Resize and WebP Conversion (Required)

fal.ai uses custom dimensions to set the aspect ratio but generates at its own
native resolution (typically 3000-4000px wide). Resize to exact target dimensions
and convert to WebP:

```python
from PIL import Image
img = Image.open('raw.png')
img = img.resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)
img.save('output.webp', 'WEBP', quality=82)
```

| Image Type | Dimensions | Format | Quality | Expected Size |
|-----------|-----------|--------|---------|---------------|
| Cover/featured | 1200×630 | WebP | 82 | 80-150 KB |
| Inline landscape | 650×366 | WebP | 82 | 30-80 KB |
| Inline portrait | 450×600 | WebP | 82 | 30-80 KB |
| Inline square | 550×550 | WebP | 82 | 25-70 KB |

Save compressed images in an `images/` directory alongside the article. Use local
paths, not fal.media URLs.

**WordPress upload:** When uploading to WordPress via `scripts/wordpress_upload.py`,
local image paths are automatically replaced with WordPress media URLs after
images are uploaded to the Media Library. The cover image (named `*-featured.webp`)
is set as the featured image.

**Naming convention:** `{slug}-{descriptor}.webp`
- Slug: article slug (e.g., `solar-panels-thai`)
- Descriptor: short keyword describing image content
- Cover image: always use `featured` as descriptor
- Inline images: 1-2 word descriptor from image content (e.g., `meter`, `installation`, `rooftop-sunset`)
- Examples: `solar-panels-thai-featured.webp`, `solar-panels-thai-meter.webp`

### Image Dimensions (Custom)

Pass dimensions as an object: `"image_size": {"width": W, "height": H}`

| Image Type | Width | Height | When to Use |
|-----------|-------|--------|-------------|
| Cover/featured | 1200 | 630 | Always — featured/OG image |
| Inline landscape | 650 | 366 | Wide scenes, environments, street views |
| Inline portrait | 450 | 600 | Tall subjects, vertical structures |
| Inline square | 550 | 550 | Close-ups, single objects, detail shots |

Choose inline dimensions based on content context. Vary dimensions across the
article — use different sizes for each inline image. Include at least one portrait
(vertical) image per article.

### Prompt Engineering Guidelines

Describe what would naturally appear in the scene — what a person standing there
would actually see and photograph.

**Location context:** Identify the primary location from the article topic and
include it naturally in each prompt. If a specific image references a different
location (e.g., a foreign project used as a comparison), use that location instead.

**Style — realistic, not polished:**
- Images should look like real photos taken by a normal person, not a
  professional photographer. Think phone camera or casual DSLR, not studio
- No hyperrealism, no cinematic lighting, no HDR look
- Natural daylight, ambient indoor light, or overcast sky — whatever fits
  the scene
- Append `, [location], natural lighting, candid photo, realistic` to each prompt

**Authenticity over aesthetics:**
- Show real, lived-in environments — actual streets, houses, shops, rooftops
  as they really look, not idealized versions
- If the article is about a specific place, show authentic local settings:
  real buildings, real infrastructure, real weather. Not tourist landmarks,
  temples, or resort aesthetics
- Avoid clichés: no golden sunsets framing the subject, no perfectly
  arranged compositions, no stock-photo smiles
- Messy is fine. Wires, dust, wear marks, clutter — these make images
  feel real

**Prompt rules:**
- Describe the scene directly — what's in frame, from what angle
- One clear subject per image
- Every image MUST have completely different content
- Keep prompts under 25 words
- Do not include text, labels, or writing in prompts (renders poorly)

**People:** Max 1-2 images with people across all images per article. The
rest should be objects, environments, or scenes.

### Image Usage Rules

| Rule | Requirement |
|------|-------------|
| Alt text | Required on ALL images — full descriptive sentence |
| Placement | After H2 headings, before body text |
| Distribution | Spread evenly — never cluster images |
| Count | 3-5 images per 2,000-word post |
| Relevance | Must relate to adjacent content |
| Format | WebP (quality 82) — compressed from fal.ai PNG via Pillow |

### Image Density by Content Type

Optimal image frequency varies by post format (THM SEO Agency data):

| Content Type | Image Density | Example (2,000-word post) |
|-------------|---------------|---------------------------|
| Listicles | 1 image per 133 words | ~15 images |
| How-to guides | 1 image per 179 words | ~11 images |
| Long-form analysis | 1 image per 200-250 words | ~8-10 images |
| Case studies | 1 image per 307 words | ~6-7 images |

Articles with an image every 75-100 words get 2x more social shares (BuzzSumo).
Balance density against page weight — use optimized formats (AVIF/WebP) to keep
total image payload under 500KB.

### SVG Impact on Engagement

D.C. Thomson case study results after replacing raster images with contextual SVGs:
- Session duration doubled
- 317% increase in read-to-completion rate
- SVGs are resolution-independent, lightweight, and dark-mode compatible

### Alt Text Guidelines
- Full descriptive sentence including topic keywords naturally
- Describe what the image shows AND its relevance to the content
- 10-125 characters
- No keyword stuffing — natural language only

Good: `Marketing team analyzing AI search traffic data on a dashboard showing citation metrics`
Bad: `SEO AI marketing blog optimization image`

**AI Systems and Images**: AI crawlers read alt text and captions, NOT the images
themselves. Write context-rich alt text that conveys the data or insight the image
represents. For charts, include the key data point in the alt text. For screenshots,
describe what the screenshot demonstrates.

### Embedding Images

**Standard Markdown:**
```markdown
![Descriptive alt text sentence](https://fal.media/files/.../image.jpg)
```

**MDX (Next.js):**
```mdx
![Descriptive alt text sentence](https://fal.media/files/.../image.jpg)
```

For Next.js projects, verify `next.config.ts` includes the fal.ai image domain:
```typescript
images: {
  remotePatterns: [
    { protocol: 'https', hostname: 'fal.media' },
  ],
}
```

**HTML:**
```html
<figure>
  <img src="https://fal.media/files/.../image.jpg"
       alt="Descriptive alt text sentence"
       width="1200" height="630" loading="lazy">
  <figcaption>AI-generated image</figcaption>
</figure>
```

---

## Image Format Optimization

### AVIF as Primary Format

AVIF is the recommended image format for 2026:
- ~50% smaller than JPEG at equivalent quality
- ~20-30% smaller than WebP
- 93.8% global browser support (caniuse, Jan 2026)
- Supports HDR, wide color gamut, and transparency

### `<picture>` Element with Progressive Fallback

Always use the `<picture>` element for format negotiation:

```html
<picture>
  <source srcset="image.avif" type="image/avif">
  <source srcset="image.webp" type="image/webp">
  <img src="image.jpg" alt="Descriptive alt text" width="1200" height="630" loading="lazy">
</picture>
```

This pattern serves AVIF to supporting browsers, falls back to WebP, then JPEG.

### LCP Image Rules

**NEVER** use `loading="lazy"` on hero/LCP (Largest Contentful Paint) images.
Lazy loading the LCP image delays the largest element on the page and directly
harms Core Web Vitals scores.

For hero/above-the-fold images:
```html
<img src="hero.avif" alt="..." width="1200" height="630"
     fetchpriority="high" decoding="async">
```

For below-the-fold images:
```html
<img src="image.avif" alt="..." width="800" height="450"
     loading="lazy" decoding="async">
```

### Dark Mode Image Support

Use `<picture>` with `prefers-color-scheme` media query for theme-aware images:

```html
<picture>
  <source srcset="chart-dark.avif" media="(prefers-color-scheme: dark)" type="image/avif">
  <source srcset="chart-dark.webp" media="(prefers-color-scheme: dark)" type="image/webp">
  <source srcset="chart-light.avif" type="image/avif">
  <source srcset="chart-light.webp" type="image/webp">
  <img src="chart-light.jpg" alt="Descriptive alt text" width="800" height="450">
</picture>
```

CSS variable pattern for inline SVG dark mode:
```css
:root {
  --chart-bg: #ffffff;
  --chart-text: #111827;
  --chart-grid: rgba(0, 0, 0, 0.08);
}

@media (prefers-color-scheme: dark) {
  :root {
    --chart-bg: transparent;
    --chart-text: #f3f4f6;
    --chart-grid: rgba(255, 255, 255, 0.08);
  }
}
```

---

## SVG Chart Integration (Built-In)

Charts are generated by the `blog-chart` sub-skill. The writer identifies chart-worthy
data during the writing process and delegates chart generation internally.

### Chart Type Selection Guide

| Data Pattern | Best Chart Type |
|-------------|-----------------|
| Before/after comparison | Grouped bar chart |
| Ranked factors / correlations | Lollipop chart |
| Parts of whole / market share | Donut chart |
| Trend over time | Line chart |
| Percentage improvement | Horizontal bar chart |
| Distribution / range | Area chart |
| Multi-dimensional scoring | Radar chart |

**Diversity is mandatory** — never use the same chart type twice in one post.
Target 2-4 charts per 2,000-word post.

### Dark-Mode Compatible Styling

All charts must work on both dark and light backgrounds:

```
Text elements:     fill="currentColor"
Grid lines:        stroke="currentColor" opacity="0.08"
Axis lines:        stroke="currentColor" opacity="0.3"
Background:        transparent (no fill on root SVG)
Subtitle text:     fill="currentColor" opacity="0.45"
Source text:        fill="currentColor" opacity="0.35"
Label text:         fill="currentColor" opacity="0.8"
```

### Color Palette (works on dark and light)

| Color | Hex | Use Case |
|-------|-----|----------|
| Orange | `#f97316` | Primary / highest value |
| Sky Blue | `#38bdf8` | Secondary / comparison |
| Purple | `#a78bfa` | Tertiary / special category |
| Green | `#22c55e` | Quaternary / positive indicator |

For text inside colored elements: `fill="white"` with `fontWeight="800"`.

### Standard SVG Shell

```xml
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
```

### JSX/MDX Shell (camelCase attributes)

```jsx
<svg
  viewBox="0 0 560 380"
  style={{maxWidth: '100%', height: 'auto', fontFamily: "'Inter', system-ui, sans-serif"}}
  role="img"
  aria-label="Chart description"
>
  <title>Chart Title</title>
  <desc>Description for screen readers</desc>

  {/* Chart content */}

  <text x="280" y="372" textAnchor="middle" fontSize="10" fill="currentColor" opacity="0.35">
    Source: Source Name (Year)
  </text>
</svg>
```

### JSX Attribute Conversion (Required for MDX)

| HTML | JSX |
|------|-----|
| `stroke-width` | `strokeWidth` |
| `stroke-dasharray` | `strokeDasharray` |
| `stroke-linecap` | `strokeLinecap` |
| `text-anchor` | `textAnchor` |
| `font-size` | `fontSize` |
| `font-weight` | `fontWeight` |
| `font-family` | `fontFamily` |
| `class` | `className` |
| `style="..."` | `style={{...}}` |

### Embedding Charts

**Standard HTML:**
```html
<figure>
  <svg viewBox="0 0 560 380" ...>...</svg>
  <figcaption>Source: Source Name, Year</figcaption>
</figure>
```

**MDX:**
```mdx
<figure className="chart-container" style={{margin: '2.5rem 0', textAlign: 'center', padding: '1.5rem', borderRadius: '12px'}}>
  <svg viewBox="0 0 560 380" ...>...</svg>
</figure>
```

### Invoking blog-chart

When generating charts, pass to the `blog-chart` sub-skill:
1. **Chart type** (ensure diversity — never repeat within a post)
2. **Title** for the chart
3. **Exact data values** with sources
4. **Source attribution** (name and year)
5. **Platform format**: html or mdx

The sub-skill returns complete SVG wrapped in a `<figure>`. Verify before embedding:
1. `currentColor` usage (no hardcoded text colors)
2. No white/light backgrounds
3. If MDX: camelCase attributes
4. Source attribution present

### Common Pitfalls

| Mistake | Impact | Fix |
|---------|--------|-----|
| `fill="#111827"` on text | Invisible on dark mode | Use `fill="currentColor"` |
| `rect fill="white"` background | Bright flash on dark mode | Remove or use transparent |
| `stroke-width` in MDX | Compilation error | Use `strokeWidth` |
| `class` in MDX | Compilation error | Use `className` |
| Same chart type twice | Visual monotony | Enforce chart diversity |
| No `role="img"` | Accessibility failure | Always include |
| No source attribution | Trust issue | Always cite data source |
