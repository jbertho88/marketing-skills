# Refresh mode

Use when the user wants an existing, live page improved rather than a new page written. The rest of the skill still applies; this file lists what changes at each step.

The guiding rule: **a page that already ranks or earns links has assets worth protecting.** Diagnose first, change what the evidence supports, keep what works. A full rewrite is a decision to justify, not a default.

## Inputs

| Input | Required | Notes |
|---|---|---|
| Live URL | Yes | The page to refresh |
| Target keyword | Yes | From the brief, or inferred from title/H1 and confirmed with the user |
| Reason for refresh | Preferred | Traffic or ranking drop, outdated info, new competitors, rebrand, merge with another page |
| Performance data | Preferred | Search Console export (queries, clicks, impressions, average position) for the URL, ideally before and after any drop; analytics landing-page data |
| Brand brief | Strongly preferred | Same as new-article mode |

Ask for performance data at intake. Without it, the diagnosis rests on the SERP alone; say so.

## Additions by step

**Intake (Step 0)**
- Confirm the primary keyword and why the page is being refreshed
- Ask whether the URL may change. Default: it does not. Changing a URL needs a 301 redirect and puts existing rankings and links at risk

**Baseline capture (new, before Step 1)**
Fetch the live page and record, so nothing is lost:
- URL, title tag, meta description, H1, full H2/H3 outline, approximate word count
- Author, published and updated dates, schema types (`scripts/page_structure.py` if HTML is reachable)
- Every internal and external link in the body, with anchor text
- Media present: images, alt text, video, tables
- Heading anchor IDs (`#section-name`) others may link to

**Keyword data (Step 1)**
- If a connector can list the keywords this URL currently ranks for (for example Moz ranking keywords, Ahrefs organic keywords, Semrush organic positions), pull them. If Search Console data was supplied, use its queries instead or as well
- Mark the queries already earning clicks or ranking on page one as **protected terms**. The refresh must keep covering them

**SERP (Step 2)**
- Note where the page currently sits for the primary keyword, if visible
- Note what changed on the SERP if known: new formats, new competitor types, a featured snippet or AI overview the page lost

**Diagnosis (new, after Step 3)**
Compare the existing page with the floor and gaps, then answer:
1. **Intent match**: does the page type still match what the SERP rewards?
2. **Floor coverage**: which floor subtopics are missing or thin?
3. **Gaps**: which gap opportunities could this page own?
4. **Accuracy and age**: outdated facts, prices, laws, screenshots, dead links, retired products
5. **Helpful content**: run the 12 self-assessment questions from `helpful-content.md` on the current page and record the noes
6. **Trust signals**: author, credentials, sourcing, reviewer, versus the SERP's trust bar
7. **Structure and UX**: buried answer, missing TOC, walls of text, weak headings
8. **Likely causes of decline**: list as hypotheses with evidence. Content is one cause among many; links, site-wide changes, algorithm updates and SERP feature changes also move rankings, and this analysis cannot prove which applied

**Change plan (new, before Step 4)**
Classify every existing section:

| Action | Meaning |
|---|---|
| Keep | Working, accurate, on-intent. Light copyedit at most |
| Update | Right section, stale or inaccurate details |
| Expand | Right section, too thin versus the floor |
| Rewrite | Right topic, wrong treatment (buried answer, filler, off-voice) |
| Cut | Off-intent, redundant, or harmful to quality. Say where any protected term it covered will now live |
| Merge | Duplicates another section or another page (flag cannibalisation) |
| Add | New section for a floor gap or a differentiating gap |

Protect by default: the URL, sections that cover protected terms, content and anchors that external pages link to, and heading IDs. If cutting any of these is right, explain why.

If the user is present, share the change plan before rewriting. For a page with meaningful traffic, this is worth the pause.

**Writing (Step 6)**
- Produce the full revised article, not a diff, so it can be pasted straight in
- Preserve the existing voice where it already meets the brand brief; do not change tone for its own sake
- Keep the protected terms covered, in headings where they already were

**Internal links (Step 5)**
- Audit the existing outbound internal links: broken, redirected, off-topic or over-optimised anchors get fixed
- Add new outbound links from the sitemap crawl and new inbound recommendations as usual

**Dates and schema (Step 9)**
- Update `dateModified` and the visible "Updated" date **only** if the changes are substantive (new or corrected information, new sections), never for a copyedit. Google lists date-only changes to look fresh as a warning sign
- Keep `datePublished` unchanged
- Optionally draft a one-line "What changed" note for the top or bottom of the page; useful for YMYL and data pages

**Measurement (new, in the deliverable)**
Record a baseline from the supplied data (clicks, impressions, average position, top queries) and suggest re-checks at about 4 and 8 weeks after publishing. Ranking movement after a refresh is observational; do not attribute it solely to the content changes.

## Extra deliverable sections (insert after the SERP report)

```
## Page diagnosis
- Verdict (2 to 3 sentences): what is wrong, what is worth keeping, how big the change is
- Protected terms: <queries the page already earns>
- Findings 1 to 8 (above), each with evidence
- Helpful content self-assessment of the current page: <table>

## Change log
| # | Section (original) | Action | Reason | Protected terms affected | New location |
|---|---|---|---|---|---|

## Measurement baseline
| Metric | Baseline | Source | Re-check dates |
```
