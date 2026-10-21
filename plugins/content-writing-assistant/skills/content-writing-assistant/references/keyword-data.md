# Keyword data, connector-agnostic

The skill works with whatever SEO data source the session has. Tool names differ by vendor and change over time, so match on **capability**, not on exact names.

## 1. Detect what is available

Look through the session's tools (load deferred tools with a tool search if the environment uses one) for an SEO data connector. Common ones:

| Vendor | What to look for | Example tool names (may vary) |
|---|---|---|
| Moz | Keyword metrics, keyword suggestions, SERP fetch | `DataKeywordMetricsFetch`, `DataKeywordSuggestionList`, `DataKeywordSerpFetch` |
| Ahrefs | Keywords Explorer: overview, matching terms, related terms, questions, SERP overview | tools with "keywords-explorer", "overview", "matching-terms", "serp" in the name |
| Semrush | Keyword overview, related keywords, phrase questions, organic results | tools with "keyword_overview", "related", "phrase", "organic" in the name |
| Other (Similarweb, DataForSEO, SE Ranking, GSC) | Any endpoint returning volume, difficulty, related terms or SERP | read the tool descriptions |

Rules:
- If more than one is connected, pick one as **primary** for volume and difficulty so numbers are internally consistent; use others only to widen suggestions. Say which you used
- Respect quota. A run needs roughly: 1 metrics call for the primary keyword, 1 to 2 suggestion calls, 1 metrics call batched for the shortlisted secondaries, and optionally 1 SERP call
- Set the correct market/locale (country and language from the brief). Volumes for the wrong country are worse than none
- If the connector offers a SERP endpoint, it can serve as the Step 2 fallback ahead of plain web search, but a user-supplied SERP still comes first

If **no** connector is available: derive candidates from the brief, People Also Ask, related searches, and competitor headings. Report volume and difficulty as `unknown`. Never estimate numbers from memory.

## 2. What to pull

- **Primary keyword**: volume, difficulty, click-through or SERP-feature data if offered, search intent label if offered
- **Secondary keywords** (5 to 15): close variants and subtopics with meaningful volume and the same intent. Discard terms with different intent; they belong on a different page
- **Questions** (5 to 10): question-form queries. These map to H2/H3s and FAQ candidates
- **Entities and terms**: recurring concepts across suggestions and competitor pages that a thorough treatment should name

## 3. How it is used

- Secondary terms and questions feed the outline only where they serve the reader at that point
- Do not create a section just because a term has volume. If it is off-intent, list it as a **separate content opportunity** instead
- Keyword difficulty informs the confidence note, not the writing

## 4. Report format

```
### Keyword data
Source: <vendor connector, locale, date | no connector: derived from SERP and brief>
| Keyword | Role | Volume | Difficulty | Intent | Used in |
|---|---|---|---|---|---|
| <primary> | Primary | 1,300 | 42 | Commercial | H1, intro, H2 #2 |
| <term> | Secondary | 210 | 28 | Commercial | H2 #4 |
| <question> | Question | 90 | n/a | Informational | FAQ |

Off-intent terms (separate page candidates): <list>
```
