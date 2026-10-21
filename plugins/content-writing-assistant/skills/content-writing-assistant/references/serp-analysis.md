# SERP analysis

How to turn ten ranking URLs into findings a writer can act on.

## Contents
1. Classify the SERP
2. Per-page extraction
3. Synthesis: floor, gaps, what does not work
4. Report format
5. Pitfalls

## 1. Classify the SERP

Before reading any page, look at the SERP as a whole and record:

- **Intent**: informational, commercial investigation, transactional, local, navigational, or mixed. Mixed SERPs are common; name the split (for example "6 guides, 3 service pages, 1 directory")
- **Dominant page type**: guide, listicle, service page, comparison, tool, forum, video, news
- **SERP features**: featured snippet (and its format: paragraph, list, table), People Also Ask (record the questions), video carousel, image pack, local pack, AI overview, Top stories, forum or "Discussions" block
- **Freshness signal**: are the top results recently updated? Dated titles ("2026")?

Feature implications:

| Feature present | What the article needs |
|---|---|
| Featured snippet (paragraph) | A 40 to 60 word direct answer right under the relevant heading |
| Featured snippet (list or table) | A clean ordered list or HTML table for that exact question |
| People Also Ask | Each relevant PAA question answered under a matching H2/H3 or in FAQ |
| Video carousel | An embedded or planned video slot plus VideoObject schema if real |
| Forums / Discussions | First-hand experience, real scenarios, candid trade-offs |
| AI overview | A tight, quotable answer early, clear entity definitions, cited facts |
| Local pack | Location signals, NAP consistency, link to the location or service page |

## 2. Per-page extraction

For each comparable organic result, capture these fields. Use `scripts/page_structure.py` when the HTML is reachable; otherwise read the fetched page.

**Identity**
- Position, URL, domain, page type, publisher type (brand, publisher, directory, forum)
- Published and updated dates if visible

**Structure**
- Title tag and H1
- Full H2/H3 outline in order
- Word count of main content (approximate is fine; exclude nav and footer)
- Where the core answer first appears (first paragraph, after an intro, buried)
- Presence of TOC, key takeaways box, summary, FAQ, comparison table, steps

**Depth and angle**
- Subtopics covered (normalise these to short labels so you can compare across pages)
- Unique angle or thesis, if any
- Original data, research, examples, case studies, calculators or tools
- Notable entities and terms used (product names, laws, standards, concepts)

**Media**
- Count of images, and how many look original (diagrams, screenshots, photos) vs stock
- Tables, charts, embedded video, audio, interactive elements

**Trust signals**
- Author shown? Name, credentials, bio length, author page link, photo
- Reviewer or fact-checker shown
- Sources cited (count and quality), outbound links to authorities
- Schema types present (Article, FAQPage, HowTo, Person, Review, etc.)

**Conversion**
- CTA type and placement, lead magnet, contact form

**Helpful content read** (see helpful-content.md)
- Original value: yes, partial or no
- First-hand experience shown: yes or no, and how
- Who/how signals: byline, credentials, sourcing, method explained
- Warning signs: padding to length, fake freshness (new date, old content), exaggerated headings, summary of others with nothing added

**Weaknesses**
- Outdated info, thin sections, fluff intro, missing obvious subtopic, poor formatting, aggressive ads, claims the brand brief would not allow

Mark any field you could not determine as `unknown`. A blocked fetch, a paywall or a JavaScript-only page is unknown, not empty.

## 3. Synthesis

Build a **subtopic coverage matrix**: subtopics as rows, pages as columns, a mark where covered. From it:

- **Floor**: subtopics covered by roughly half or more of the comparable pages. The article covers all of these, but often more tightly than competitors
- **Gaps**: subtopics covered by zero to two pages, PAA questions nobody answers well, missing formats (no one has a comparison table, no one has a diagram), missing perspectives (no practitioner experience), stale information you can update
- **Differentiators that seem to work**: patterns more common on the top 3 than on positions 7 to 10. Treat as hypotheses, not causes; ranking is also driven by links, brand and history you cannot see in content
- **What does not work or must not be copied**: patterns on weaker pages, plus anything competitors do that the brand brief forbids (a competitor titling itself "Best X" does not make it acceptable for a regulated client)

Also derive:
- **Length reference**: median and range of comparable word counts, reported as context only. Google has no preferred length and treats writing to a word count as a warning sign, so this number never becomes a target
- **Format verdict**: the page type to write and why
- **Trust bar**: the strongest author/E-E-A-T treatment on the SERP, which the article should meet or beat
- **Helpful content weak spots**: where ranking pages score poorly on original value, experience or sourcing. These are the most defensible gaps

## 4. Report format

Lead with findings, then evidence.

```
## SERP report: "<keyword>"
Source: <user-supplied export from TOOL on DATE | web search approximation on DATE>
Pages analyzed: N of 10 (unfetched: list with reason)

### Verdict
<2 to 4 sentences: intent, format to write, the main gap we are writing to, confidence>

### Floor (must cover)
- <subtopic> (covered by N/M pages)

### Gaps (our edge)
- <gap> : <evidence>

### What works
- <pattern> : <pages showing it>

### What doesn't / do not copy
- <pattern> : <why>

### SERP features
- <feature> : <implication>

### Page table
| # | URL | Type | Words | H2s | Media (orig/stock/video) | Author shown | Original value | Experience | Schema | Notable |
```

Keep the report scannable. The writer will reread it; the client may too.

## 5. Pitfalls

- Averaging competitors into a longer, blander page
- Treating word count or heading count as a ranking cause, or setting a length target from it
- Copying competitor headings verbatim (also a plagiarism risk)
- Ignoring non-article results that reveal intent
- Reporting an unfetched page as having zero words, zero images or no author
- Quoting long passages of competitor copy in the report. Paraphrase and keep any quote short
