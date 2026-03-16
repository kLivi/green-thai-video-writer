# Video Article Template

Articles based on YouTube videos follow this structure. The goal is to add organized value to the video — not just transcribe it.

## Article Structure

### Title Format
`[Project Type] in [Location]: [Key Finding or Result]`
Examples:
- "Off-Grid Solar in Phuket: Real Costs After 2 Years"
- "5 kW Rooftop Solar in Bangkok: ฿180K Installation Walkthrough"
- "Floating Solar at Sirindhorn Dam: Thailand's 45 MW Flagship"

### Required Sections

1. **TL;DR box** — 2-3 sentences: what the video shows, the key numbers, and the main takeaway.

2. **Video Embed** — YouTube embed iframe right after TL;DR:
   ```html
   <div class="video-embed">
     <iframe width="560" height="315" src="https://www.youtube-nocookie.com/embed/{VIDEO_ID}" 
       title="{video title}" frameborder="0" 
       allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
       allowfullscreen loading="lazy"></iframe>
   </div>
   ```

3. **Project Overview** (H2) — Who, where, what type, why they did it. Set the scene.

4. **Technical Specifications** (H2) — System size, equipment, design choices. Table format if enough data:
   ```html
   <table>
     <tr><th>Component</th><th>Details</th></tr>
     <tr><td>System Size</td><td>5 kWp</td></tr>
     ...
   </table>
   ```

5. **Cost Breakdown** (H2) — Costs from the video + Thai context (typical ranges, how this compares).
   Include [CHART] marker if there's enough financial data for visualization.

6. **Results & Performance** (H2) — What happened after installation. Actual output, savings, issues.

7. **Challenges & Lessons Learned** (H2) — Problems encountered, solutions found. This is often the most valuable section.

8. **Thai Context** (H2) — Relevant permits, regulations, incentives that apply to this project type. Sourced from prompts/thai-context.md. Only include if it adds genuine value.

9. **Key Takeaways** (H2) — 3-5 bullet points summarizing the most actionable information.

10. **FAQ** (H2) — 4-6 questions a reader would ask after watching. Include questions the video doesn't fully answer.

### Section Rules
- Not every section is required — skip sections where the video provides no relevant data
- "Cost Breakdown" without any cost data = skip it
- "Results & Performance" without results = skip it
- Minimum: TL;DR + Video Embed + Project Overview + 2 other H2 sections + Key Takeaways + FAQ

### Video Timestamps
Where possible, reference specific timestamps so readers can jump to relevant parts:
```html
<p>At <a href="https://youtube.com/watch?v={ID}&t={seconds}">2:15</a>, they show the inverter setup...</p>
```

### Attribution
- Always credit the channel and video
- Link to the original video
- Don't claim the experience as your own — use "the video shows", "according to [channel]", "[creator] explains that..."
