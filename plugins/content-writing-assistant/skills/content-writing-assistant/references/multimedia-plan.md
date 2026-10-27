# Multimedia plan

Every visual must earn its slot by doing something text cannot: show a process, compare options, prove a claim, demonstrate a task, or break up a dense stretch the reader would otherwise skim past.

## Set the bar from the SERP
- Count what the top 3 use: original diagrams, screenshots, photos, tables, charts, video
- If a video carousel or video-heavy results appear, include a video slot
- If competitors rely on stock photos, original visuals are an easy differentiator
- If competitors use a comparison table, the article needs a better one

## Slot types

| Type | Use when | Notes |
|---|---|---|
| Hero image | Always, one | Original or brand photography preferred over stock. Not the place for text-heavy graphics |
| Process diagram / flowchart | Steps, sequences, decision paths | Strong candidate for gap sections |
| Comparison table | Options, plans, criteria | Build as an HTML/Markdown table, not an image, so it can win a snippet |
| Chart | Data the article cites | Must cite the data source in the caption |
| Screenshot / annotated UI | How-to inside a tool | Annotate the action; crop tight |
| Photo | Real people, places, products, proof | Real author or team photos build trust |
| Video | Demonstrations, explanations, SERP shows video intent | Short (1 to 4 min), with transcript or summary below |
| Checklist / downloadable | Practical tasks | Can double as a lead magnet if the CTA calls for it |

Aim for one meaningful visual roughly every 300 to 500 words in long-form, more for how-to content. Fewer good visuals beat many decorative ones.

## For each slot, specify
- **ID and placement**: `[MEDIA-03]` after which heading or paragraph
- **Type**
- **Purpose**: what the reader understands from it
- **Production brief**: what it shows, data or steps it contains, style notes from the brand brief (colours, illustration style), who should produce it (designer, author screenshot, video team)
- **File name**: lowercase, hyphenated, descriptive (`ontario-bail-hearing-process.png`)
- **Alt text**: describes what the image conveys for someone who cannot see it, under about 125 characters, includes a keyword only if it is genuinely what the image shows
- **Caption**: one line, adds information (source, takeaway) rather than repeating alt text
- **Priority**: must-have or nice-to-have

Decorative images get empty alt text and say so.

## Inline markers in the article
Place each slot in the article Markdown as:

```
> [MEDIA-03: Process diagram. The five stages from charge to trial. See multimedia plan.]
```

## Compliance
Respect the brand brief: regulated clients may bar client photos, testimonial imagery, before/after images or outcome graphics. Never recommend using competitor images or unlicensed media. For video, flag consent needs if real people appear.

## Output format

```
### Multimedia plan
| ID | After | Type | Purpose | Brief | File name | Alt text | Caption | Priority |
```
