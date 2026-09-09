---
name: seo-workbook-builder
description: >
  Build a keyword-mapped SEO workbook from Screaming Frog crawl data and search ranking exports.
  Use this skill whenever the user wants to create an SEO workbook, keyword map, content optimization
  spreadsheet, or on-page SEO tracker from crawl data. Triggers include: mentions of "SEO workbook",
  "keyword mapping", "content optimization tracker", "on-page SEO", Screaming Frog exports combined
  with ranking or GSC data, or requests to map keywords to pages for optimization. Also trigger when
  the user has crawl data (internal URLs export) and wants to organize it into an actionable
  optimization workflow with priorities, keyword targets, and status tracking. If the user mentions
  Screaming Frog data and ranking data together, this skill is almost certainly what they need.
---

# SEO Workbook Builder

Build a structured, actionable SEO workbook from website crawl data and search ranking exports. The workbook maps keywords to pages, classifies page types, assigns optimization priorities, and gives the user a ready-to-use tracker for their on-page SEO work.

## Why this skill exists

SEO teams export crawl data from tools like Screaming Frog and ranking data from Google Search Console, but these raw exports aren't actionable on their own. The gap between "I have data" and "I know what to optimize" is where this skill lives. It bridges that gap by combining multiple data sources into a single workbook where every page has a target keyword, a priority level, and a status column to track progress.

## What you need from the user

### Required inputs

1. **Internal URLs export** — A Screaming Frog crawl export (.xlsx) containing at minimum:
   - `Address` (page URLs)
   - `Status Code` (HTTP status)
   - `Title 1` (page titles)
   - `Segments` (Screaming Frog segments, if configured)

2. **Ranking data** — A CSV or XLSX with keyword-to-URL mappings containing at minimum:
   - A keyword/query column
   - A landing page/URL column
   - Click and impression metrics

### Optional but valuable columns (from the crawl export)

These enrich the workbook significantly when present. Screaming Frog can pull them via API integrations:

- `Meta Description 1` — For on-page optimization reference
- `Clicks`, `Impressions`, `CTR`, `Position` — GSC data (via Screaming Frog's GSC integration)
- `Moz Page Authority` — Page-level authority score (via Moz API)
- `Moz External Pages to Page` — Inbound link count
- `Moz Root Domains to Page` — Linking domain count
- `Extract embeddings from page content` — OpenAI embeddings (via Screaming Frog's AI integration)

### If columns are missing

Don't fail — adapt. If the crawl export doesn't have GSC columns, the workbook just won't have those metrics. If there are no Moz columns, skip PA/inbound links. If there are no embeddings, skip the Embeddings sheet. The core workflow (URL + keyword mapping + priority + status) works with just URLs, titles, and ranking data.

## Step-by-step workflow

### Step 1: Discover and map columns

Read the crawl export and ranking data. Print the column names and shape of each file. Map whatever columns exist to the workbook schema:

| Source column | Workbook column | Required? |
|---|---|---|
| Address | Page URL | Yes |
| Status Code | HTTP Status Code | Yes |
| Title 1 | Page Title | Yes |
| Segments | Page Type (after cleaning) | No — use URL patterns if missing |
| Meta Description 1 | Meta Description | No |
| Clicks | GSC Clicks | No |
| Impressions | GSC Impressions | No |
| CTR | GSC CTR | No |
| Position | GSC Avg Pos. | No |
| Moz Page Authority | PA | No |
| Moz External Pages to Page | Inbound Links | No |
| Moz Root Domains to Page | Linking Domains | No |
| Extract embeddings from page content | Embedding | No |

If the user's files use different column names, match by intent rather than exact string. For instance, "URL" or "Page" likely maps to Address. Ask the user if anything is ambiguous.

### Step 2: Classify page types

The goal is to turn raw segments or URLs into human-readable content categories (Blog, Product Page, Help Center, Guide, etc.) that drive priority assignment and sheet organization.

**If the crawl has Segments:**
Screaming Frog segments are comma-separated and often mix content types with technical labels. Strip the technical noise first:

- Remove segments like: `Crawl Depth > N`, `Errors - 3XX Redirects`, `Errors - 4XX`, `Top 500`, or any segment that describes crawl behavior rather than content type
- Keep segments that describe what the page *is*: Blog, Help Hub, Learn Center, Products, Guides, etc.

After cleaning, classify each page. Use both the cleaned segment AND the URL path to disambiguate. For example, a page with no segment but a `/blog/` URL path is a Blog page.

**If there are no segments:**
Classify purely from URL patterns. Common patterns:

- `/blog/` → Blog
- `/help/`, `/support/` → Help/Support
- `/learn/`, `/resources/`, `/education/` → Learning Center
- `/products/`, `/features/`, `/pricing/` → Product Page
- `/tools/`, `/free-*/`, `/checker/`, `/analyzer/` → Freemium Tool
- `/guide/`, `/beginners-guide/`, `/how-to/` → Guide
- `/about/`, `/team/`, `/careers/` → About
- `/community/`, `/forum/`, `/users/`, `/q/` → Community

These patterns vary by site. Inspect the URL structure first, then build the classification. The user knows their site best — show them the page type distribution and ask if anything looks off before proceeding.

**Page Type distribution check:**
After classification, print a count of each page type. This serves two purposes: it lets the user catch misclassifications, and it reveals the site's content architecture at a glance.

### Step 3: Map keywords to pages

This is the core value of the workbook — connecting each page to the keyword it should target.

**From ranking data:**
For each URL in the ranking data, score its keywords using a weighted formula that balances traffic value with ranking potential:

```
keyword_score = (clicks * 3) + (impressions * 0.1) + ((100 - avg_position) * 5)
```

The weighting logic: clicks matter most because they represent actual traffic. Impressions indicate opportunity. Position quality (inverted) rewards keywords where the page is already close to page 1 — these are the low-hanging fruit for optimization.

Assign:
- **Primary Keyword**: Highest-scoring keyword for the URL
- **Secondary Keywords**: Next 2-3 keywords by score (comma-separated)
- **Total Keywords Ranking**: Count of all keywords the URL ranks for

**Fallback for pages without ranking data:**
Many pages won't appear in the ranking data (new pages, low-traffic pages, pages that haven't been indexed). For these, extract a keyword phrase from the page title by stripping the site name suffix (e.g., " - Moz", " | Company Name") and using what remains. It's not a real keyword target, but it gives the user something to work with.

### Step 4: Assign priority

Priority determines which pages the SEO team should optimize first. Use sensible defaults based on page type and business impact:

- **High**: Homepage, Product pages, Freemium tools, Pricing — these drive conversions directly
- **Medium**: Blog, Learning center, Guides, Help/support, Webinars, Case studies — these drive organic traffic and support the funnel
- **Low**: Community/UGC, About pages, Legal, Login, Press, API docs — important but not optimization priorities

These defaults work for most B2B SaaS and content-heavy sites. The user can override any assignment in the spreadsheet after the fact, so don't overthink edge cases — just get the broad strokes right.

### Step 5: Set optimization status

Every page starts as **Backlog**. The workbook includes a dropdown with four states:

- **Backlog** — Not yet reviewed
- **To Optimize** — Reviewed, needs work
- **In Progress** — Currently being optimized
- **Optimized** — Done

This gives the user a kanban-style workflow inside the spreadsheet.

### Step 6: Build the workbook

The output is a single .xlsx file with these sheets:

**Summary** — Dashboard with key metrics: total pages, pages with ranking keywords, total keywords ranking, priority breakdown, and a page type table showing count, total clicks, and average PA per type.

**Per-page-type sheets** — One sheet for each primary page type (Homepage, Product Pages, Freemium Tools, Learning Center, Help Hub, Guides, Blog, etc.). Each contains only the pages of that type, sorted by GSC Clicks descending. This lets the user focus on one content area at a time.

**All Pages** — The complete dataset across all page types, sorted by clicks. This is the master reference.

**Embeddings** (if embedding data exists) — Page URL, Page Type, Primary Keyword, and the embedding vector. Separated from the main sheets because embedding strings are large and would clutter the working sheets. Truncate to 200 characters in the cell with "..." suffix.

### Formatting standards

- **Font**: Arial throughout (11pt headers, 10pt data)
- **Header row**: Dark navy background (#1B2A4A), white bold text, centered, frozen
- **Auto-filters**: On every data sheet
- **Column widths**: Set explicitly — URLs get 45, titles/descriptions get 50, metrics get 12-14
- **Number formats**: CTR as percentage (0.00%), position as decimal (0.0), clicks/impressions with thousand separators (#,##0)
- **Priority coloring**: Green fill for High, Yellow for Medium, Red for Low
- **Alternating row shading**: Light blue-grey (#F7F9FC) on even rows for readability
- **Data validation**: Dropdown lists on Priority (High/Medium/Low) and Optimization Status (Backlog/To Optimize/In Progress/Optimized) columns
- **URL styling**: Blue underlined font (#1155CC) for clickable appearance
- **Tab colors**: Distinct color per sheet for visual navigation

### Final steps

After building the workbook:

1. Run the LibreOffice recalc script if there are any formulas
2. Check for `#NAME?` errors caused by keyword strings containing `#` characters — escape or rewrite them
3. Verify the file opens without errors
4. Save to the user's workspace folder

## Common pitfalls

- **Duplicate column names**: If both "HTTP Status Code" and "Optimization Status" are shortened to "Status" during processing, they'll collide. Keep them distinct throughout.
- **Unicode in sheet names**: Emoji variation selectors (`\ufe0f`) cause Excel on Windows to refuse to open the file. Strip them from any sheet names that use emoji.
- **Large files**: The blog sheet alone might have 10K+ rows. Use openpyxl's normal mode (not write_only) since you need formatting, but be aware that the file can get large. Embedding vectors especially — truncate them in the display sheet.
- **Keyword strings with formula characters**: Keywords containing `=`, `+`, `-`, or `#` at the start can be misinterpreted as formulas. Prefix with a single quote if needed, or ensure they're written as string type.

## What NOT to do

- Don't calculate metrics in Python and hardcode them — use Excel formulas where possible so the workbook stays dynamic
- Don't include the Embedding column in the main data sheets — it's noise for the user doing optimization work
- Don't over-engineer the page type classification — the user will review and adjust. Get it 80% right and move on
- Don't skip the data validation dropdowns — they're what make this a *workflow tool* instead of just a data dump
