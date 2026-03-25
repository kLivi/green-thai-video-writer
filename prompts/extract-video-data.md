# Video Data Extraction

Extract structured data from a YouTube video transcript about green energy in Thailand.

## Required Fields

From the transcript, identify and extract:

### Project Info
- **Channel name**: Who made the video
- **Location**: Where in Thailand (province, city, or region). If not Thailand, note the country.
- **Project type**: Solar rooftop, off-grid solar, floating solar, wind farm, EV charging, biogas, etc.
- **System size**: kW, kWp, MW — whatever units are mentioned

### Financial Data
- **Equipment cost**: Panels, inverters, batteries, other hardware
- **Labor/installation cost**: If mentioned separately
- **Total cost**: If stated
- **Currency**: THB or other
- **Savings reported**: Monthly/annual electricity savings
- **Payback period**: If mentioned or calculable

### Technical Details
- **Equipment list**: Panel brand/model, inverter, battery, mounting, etc.
- **Design choices**: Why they chose specific equipment or configuration
- **Grid connection**: On-grid, off-grid, hybrid? MEA or PEA?

### Results & Experience
- **Performance results**: Actual output, efficiency, savings achieved
- **Challenges encountered**: Problems during installation or operation
- **Solutions found**: How problems were resolved
- **Timeline**: How long the project took

### Key Quotes
- Extract 3-5 notable quotes with approximate timestamps
- Focus on: cost revelations, surprising results, practical advice, lessons learned

## Output Format

Present the extracted data as a structured summary with clear headings. Mark any field as "Not mentioned" if the transcript doesn't cover it. Flag any numbers that seem uncertain or ambiguous.

## Credibility Assessment

Rate the video's data reliability:
- **High**: First-hand experience, shows receipts/bills, specific numbers with context
- **Medium**: General knowledge, some specific claims but unverified
- **Low**: Vague claims, promotional content, no supporting evidence

Note: Many Thai-language videos mix Thai and English technical terms. Extract data regardless of language.

## Visual Moments

Identify 5-6 timestamps where the video likely shows something visually relevant — equipment, installations, scenery, screens, results — rather than a talking-head segment.

**To identify visual moments, read the raw VTT file** (not just the clean transcript) and look for:

- Topic shifts to physical objects (speaker describing equipment, showing hardware)
- Demonstrative language (speaker directing attention to something visible)
- Location descriptions (speaker describing surroundings, panning views)
- Results on screens (electricity bills, app dashboards, monitoring data)
- Before/after moments

**Skip these — they are likely talking-head segments:**

- Intro/outro sequences
- Segments that are purely verbal explanation with no visual subject
- Long monologues without topic shifts

These cues apply regardless of transcript language (English or Thai) — identify the semantic pattern, not specific keywords.

### Output format

```
Visual Moments:
1. 03:42 — Mountains and trees blocking afternoon sun (speaker pans to show horizon)
2. 07:15 — Inverter mounted on wall (speaker walks to equipment)
3. 09:30 — Electricity bill comparison on screen
4. 12:45 — Panel array on rooftop from ground level
5. 15:20 — Wiring and junction box close-up
```

Use `MM:SS` format for videos under 1 hour, `HH:MM:SS` for longer videos. Include a brief reason in parentheses explaining why you believe this moment is visual.

Present 5-6 candidates. Some may turn out to be duds — the best 2-4 will be selected later during article writing.
