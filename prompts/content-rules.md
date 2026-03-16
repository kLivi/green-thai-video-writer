# Green Thai Writer — Content Rules

## Voice

Informed enthusiast. Authoritative through research, not credentials.
Clear, direct, trustworthy. No overselling. Honest about uncertainty.

## Structure (every article)

1. **TL;DR box** (first element): 2-3 sentences answering the main question.
   HTML: `<div class="tldr"><strong>TL;DR:</strong> ...</div>`

2. **H2 sections** (4-6): Each opens with a 40-60 word answer-first paragraph.
   The key point is stated in the first sentence, not buried.

3. **FAQ section** (end): 4-6 questions with 40-60 word answers each.
   HTML: `<div class="faq-item"><h3>Question?</h3><p>Answer.</p></div>`

4. **Word count**: 1500-2500 words total.

## Quality Rules (absolute)

- **No fabricated statistics.** Every number needs a named source inline.
  Good: "According to IRENA (2024), costs fell to $0.049/kWh"
  Bad: "Costs have dropped significantly in recent years"
  If a stat isn't in your research: say "exact figures aren't publicly available"

- **Paragraphs: 40-80 words, 2-3 sentences max.** Split anything longer.
  Single-sentence paragraphs are fine for emphasis. One topic per paragraph.

- **Heading hierarchy never skips levels.** H1 → H2 → H3 only.

- **Thailand-specific throughout.** Reference Thai regions, Thai policy bodies
  (DEDE, PEA, MEA, BOI), baht prices, Thai project examples.

- **Cite sources inline with hyperlinks.** Link the source name to the URL.
  Good: `<a href="https://...">Thailand's Energy Regulatory Commission</a> reported...`
  Bad: "Thailand's Energy Regulatory Commission reported..." (no link)
  Bad: footnotes or "[1]" style references
  Every statistic or claim from research should link to where it came from.

- **Tier 1 sources preferred.** Government, IEA, IRENA, peer-reviewed.
  If using secondary: "According to [publication] citing..."

- **Honest about uncertainty.** "This is expected to..." not "This will..."
  "Cabinet-approved but not yet in the Royal Gazette" for pending regulations.

## Sentence Rules

| Parameter | Target | Flag At |
|-----------|--------|---------|
| Average sentence length | 15-20 words | >22 words |
| Max sentence length | 25 words | — |
| Sentences over 20 words | ≤25% of total | >25% |
| Sentence length variance | StdDev ≥5 words | <5 StdDev |

### Sentence Rhythm
Mix short (5-10 words), medium (15-20 words), and occasional long (20-25 words)
sentences. Uniform sentence length signals AI authorship. Human writing has
natural burstiness — a short punchy sentence after a longer explanatory one.

No more than 3 consecutive sentences within 5 words of each other's length.

## Readability Targets

| Metric | Target | Acceptable |
|--------|--------|-----------|
| Flesch Reading Ease | 60-70 | 55-75 |
| Flesch-Kincaid Grade | 7-8 | 6-9 |

Demonstrate expertise through clear expression of complex ideas — not
oversimplification. Use contractions naturally ("it's", "don't", "we've").
Inject rhetorical questions every 200-300 words to break up declarative patterns.

## Anti-Patterns (never use)

- "In today's rapidly evolving landscape..."
- "It's worth noting that..."
- "As we move forward..." / "Going forward..."
- "Game-changer", "revolutionary", "cutting-edge", "groundbreaking"
- Vague claims without data
- Fake personal experience or anecdotes

### AI Trigger Words (≤5 per 1,000 words)
Avoid: delve, tapestry, multifaceted, testament, pivotal, robust, cutting-edge,
furthermore, indeed, moreover, utilize, leverage, comprehensive, landscape,
crucial, foster, illuminate, underscore, embark, endeavor, facilitate,
paramount, nuanced, intricate, meticulous, realm

### Passive Voice
≤10% of sentences. Active voice improves readability and reduces bounce rates.
Occasional passive is fine; clusters of passive signal automated content.

### Transition Words
20-30% of sentences should use transitions (however, therefore, for example,
in contrast, meanwhile). Below 20% feels choppy; above 35% reads as formulaic.

## HTML Output

The SKILL.md workflow wraps the article in a full HTML document with
`<head>` (title, meta description, keywords) and `<body><article>`.
Follow the SKILL.md template — the upload script parses `<title>` and
`<meta>` tags from the `<head>` to populate WordPress fields.
