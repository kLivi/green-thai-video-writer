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
