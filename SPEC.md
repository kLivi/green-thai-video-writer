# Green Thai Video Writer

Pipeline 2: YouTube URL ? Transcript ? Analysis ? Enhanced Article ? WordPress Draft

## Purpose

Take a YouTube video about green energy projects in Thailand, extract the transcript, analyze it for key data, enhance with Thai context, and publish as a WordPress draft that adds organized value to the video content.

## Usage

```
/blog video "https://youtube.com/watch?v=..."
```

Or add URL to `queue/video-queue.txt` for batch processing.

## File Structure

```
green-thai-video-writer/
+-- src/
¦   +-- commands/
¦   ¦   +-- video.ts             # /blog video command
¦   +-- lib/
¦   ¦   +-- video/
¦   ¦   ¦   +-- transcript.ts    # yt-dlp or YouTube API
¦   ¦   ¦   +-- extractor.ts     # Pull specs, costs, location, results
¦   ¦   ¦   +-- analyzer.ts      # Identify project type, key data
¦   ¦   +-- content/
¦   ¦   ¦   +-- template.ts      # Video article structure
¦   ¦   ¦   +-- enhancer.ts      # Add Thai context (permits, rates)
¦   ¦   ¦   +-- charts.ts        # SVG from extracted data
¦   ¦   ¦   +-- writer.ts        # Assemble article
¦   ¦   +-- media/
¦   ¦   ¦   +-- thumbnail.ts     # Get or generate featured image
¦   ¦   ¦   +-- charts.ts        # SVG generation
¦   ¦   +-- wordpress/
¦   ¦       +-- publisher.ts
¦   +-- types/
¦   ¦   +-- index.ts
¦   +-- config/
¦       +-- categories.json
¦       +-- wordpress.ts
+-- prompts/
¦   +-- extract-data.txt         # Prompt: pull structured data from transcript
¦   +-- analyze-project.txt      # Prompt: identify type, assess credibility
¦   +-- write-article.txt        # Prompt: video case study format
+-- queue/
¦   +-- video-queue.txt          # URLs to process
+-- package.json
+-- tsconfig.json
+-- README.md                    # This file
```

## Article Template

```markdown
# [Channel Name]: [Project Type] in [Location]

[Video embed]

## Project Overview
Who, where, what type of project

## Technical Specifications
System size, equipment, design choices

## Financial Analysis
Costs from video + Thai context (typical permit costs, labor rates)
Payback calculation if data allows
[SVG chart: projected savings]

## Challenges & Solutions
Problems encountered, how solved

## Key Takeaways
3-5 bullet points

## Video Highlights
- [00:34] System specs
- [02:15] Cost breakdown
- [05:40] Results after 1 year
```

## Key Components

### transcript.ts
- Input: YouTube URL
- Output: Full transcript text
- Use yt-dlp or YouTube API

### extractor.ts
- Input: Transcript text
- Output: Structured data object:
  ```typescript
  {
    channelName: string,
    location: string,
    projectType: string,
    systemSize?: string,
    costs: { equipment?: number, labor?: number, total?: number },
    equipment: string[],
    challenges: string[],
    results: string,
    keyQuotes: { timestamp: string, text: string }[]
  }
  ```

### enhancer.ts
- Add Thai context not in video:
  - Typical permit costs for this project type
  - MEA/PEA grid connection requirements
  - Local incentives available
  - Labor rate comparisons

### charts.ts
- Generate SVG charts if video contains data:
  - Payback period projection
  - Savings over time
  - Cost breakdown comparison

### thumbnail.ts
- Get YouTube thumbnail or generate featured image via fal.ai

## Workflow

1. Fetch transcript from YouTube URL
2. Extract structured data (specs, costs, location, results)
3. Analyze project type and assess credibility
4. Map to category (Solar Installation, Case Studies, etc.)
5. Enhance with Thai context (permits, rates, incentives)
6. Generate charts from extracted data (if applicable)
7. Write article following template
8. Publish to WP as draft with video embed and category set

## Images

- **Featured image:** YouTube thumbnail or generated cover image
- **Body images:** Optional - add diagrams if video mentions specs worth visualizing
- **Charts:** SVG generation for payback/savings data

## Example Videos to Process

- Solar installations on Thai homes
- Energy-efficient house builds in Thailand
- DIY solar projects with cost breakdowns
- Before/after energy consumption comparisons

## Dependencies

```json
{
  "dependencies": {
    "axios": "^1.6.0",
    "@fal-ai/client": "^latest",
    "yt-dlp-wrap": "^latest"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "@types/node": "^20.0.0"
  }
}
```

## Shared Config

Same `categories.json` and `wordpress.ts` as Idea Writer (extract from content-queue.csv).

## Future Enhancements

- Scraper to auto-discover videos
- Batch processing from queue file
- Auto-embed with timestamp links
