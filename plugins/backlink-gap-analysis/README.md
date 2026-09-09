# Backlink gap analysis

Created by: Jonathan Berthold, VP Revenue of Moz

Last updated: September 9, 2026

Find the pages linking to your competitors, understand what earned those links,
and turn the evidence into a prioritized plan for your own site. This skill
combines page-level benchmarking, competitor research, opportunity scoring, and
an outreach and content plan in one analysis.

## What you can use it for

- **Evaluate a specific search opportunity.** Compare the backlinks to your target
  page with those pointing to the pages ranking for the same keyword.
- **Find missing links.** Identify sites and articles linking to competitors but
  not to your site or target page.
- **Learn what attracts links.** Examine competitor studies, tools, guides, and
  other frequently linked assets.
- **Prioritize your next actions.** Separate credible outreach opportunities from
  items that need verification, longer-term work, or no action.
- **Build a follow-up plan.** Connect the findings to publisher outreach, asset
  creation, relevant internal links, and a 30/60/90-day measurement plan.

## Before you start

### Connect Moz

This skill requires a connection through either the **Moz API MCP server** or a
**direct connection to the Moz API** for live research. Set up and authenticate
one of these connections in the environment where you will run the skill.

- **Moz API MCP:** Follow the [MCP server setup guide](https://moz.com/api/docs/guides/mcp-servers).
  MCP is the connection that lets your AI assistant call Moz's data tools.
- **Direct Moz API connection:** Follow the [Getting Started guide](https://moz.com/api/docs/guides/getting-started).
  Your assistant's environment needs a working integration that can make the
  required API requests; entering a website URL does not establish that connection.

API access and usage depend on your account and available quota. Before collecting
billable data, the assistant checks the available allowance and agrees a research
scope with you. It reports limits and incomplete coverage rather than silently
claiming a full analysis. Do not paste API secrets into your prompts or reports.

Existing backlink exports can also supply or supplement the analysis when live
access is unavailable. See **Working with exports** below for the evidence needed.

### Make the complete skill available

Give your assistant access to the full `backlink-gap-analysis` folder, including
`SKILL.md`, `references`, and `scripts`. It needs file access and code execution
to produce the workbook. Pasting the instructions alone does not provide those
capabilities or connect Moz.

The packaged workbook builder requires Python 3.10 or later and `openpyxl`.
These are setup requirements for the execution environment; you do not need to
write Python to request an analysis. Ask your assistant to check the environment
before it starts.

## What to provide

| Input | What to include | Why it matters |
|---|---|---|
| Client website | Your domain, such as `example.com`. | Identifies which links you already have. |
| Target page | The exact page you want to support. Say if it is proposed rather than published. | Enables page-level comparison and useful destination recommendations. |
| Competitors | The domains and, when available, exact competing pages. | Defines who the analysis compares and mines for opportunities. |
| Keywords | One keyword or a clearly grouped set of related queries. | Keeps the research aligned with a specific search opportunity. |
| Market | Country, language, and relevant location. | Prevents unrelated markets from being treated as one search result set. |
| Search results, if available | Ranking URLs, positions, collection date, source, and location. | Supports a verified search engine results page (SERP) benchmark. |
| Business context | Audience, objective, relevant products, and constraints. | Helps judge whether a link or asset is worth pursuing. |
| Approved proof points, if available | Verifiable product facts, differentiators, studies, or customer examples with sources. | Supports accurate outreach angles without inventing claims. |
| Research limits | Competitor count, recent-link window, and any API usage limit. | Defines an achievable collection scope. |

If you do not have current search results, the skill can still perform a
competitive page or domain benchmark. It will label that scope and will not
invent live rankings. Historical ranking-index data is not a current SERP.

## How to prompt the skill

You can describe the task in plain language. Name the skill, identify the client,
and explain what decision you want the analysis to support. Replace the bracketed
fields in the examples below.

### Quick start

```text
Use the backlink-gap-analysis skill to analyze [client domain] against
[competitor domains]. Our target page is [URL], our target keyword is [keyword],
and our market is [country and language].

Our goal is [business objective]. Use my connected Moz API access. Check the
available quota and agree the collection scope with me before billable research.

Find relevant pages linking to competitors but not us, investigate what earns
those links, and produce the workbook, summary brief, and prioritized action plan.
Flag missing evidence and incomplete coverage clearly.
```

### Analyze the pages ranking for a keyword

```text
Use the backlink-gap-analysis skill for [keyword] in [market]. Our page is [URL].
I have attached the ranking URLs and positions collected on [date] from [source].

Compare links to the exact ranking pages as well as domain-level strength.
Identify relevant linking pages we are missing, explain the evidence behind the
main gaps, and recommend the first actions worth taking. Keep recommendations
for each keyword separate if the file includes multiple search results.
```

### Find assets worth creating

```text
Use the backlink-gap-analysis skill to investigate the most-linked assets on
[competitor domains] for [client domain] and [topic].

Inspect actual linking pages to explain why studies, tools, or resources attract
citations. Recommend assets we could credibly create using these approved proof
points: [facts and sources]. Show where an editor would naturally link and which
commercial page that asset would support through relevant internal links.
```

### Turn an existing analysis into an execution plan

```text
Use the attached backlink analysis and findings file to plan our next 60 days.
Start with verified opportunities. Group multiple articles from the same publisher
into a coordinated contact relationship where appropriate.

For each priority, give me the source page, proposed destination, evidence-backed
angle, contact route, owner, next step, and measurement approach. Separate work
we can pursue now from verification tasks and longer-term asset development.
Draft recommendations only; do not send outreach.
```

### Run with a limited allowance

```text
Use the backlink-gap-analysis skill for [client], [target page], and [competitors].
My research limit is [limit]. Check quota and propose a bounded collection plan.

Prioritize [the stages or questions that matter most]. If the allowance cannot
cover everything, identify what will be omitted and produce a clearly labeled
partial report with the reasons. Do not exceed the agreed scope.
```

## What happens during the analysis

1. **Define the comparison.** Confirm the client, target pages, competitors,
   keywords, market, and collection scope.
2. **Benchmark the pages.** Compare referring domains, backlinks, and page and
   domain metrics. A referring domain is a website linking to a page; multiple
   links from one domain are not multiple unique domains.
3. **Find the gaps.** Identify sources linking to competitors but not the client,
   preserving actual linking pages wherever the evidence allows.
4. **Inspect recent links and strong sources.** Review recently observed links,
   competitor assets, and the editorial context behind the links.
5. **Compare page gaps and anchor text.** Examine the clickable text used in links
   without prescribing an arbitrary exact-match anchor target.
6. **Score opportunities.** Evaluate evidence, fit, source quality, placement,
   visibility, and a practical route to the publisher.
7. **Build the plan.** Separate immediate work from verification, deferred items,
   and longer-term assets. Explain coverage limits and suggested measurement.

The analysis does not prove that backlinks caused a ranking position, guarantee
ranking gains, or establish that a competitor bought links.

## What you receive

### An Excel workbook

The workbook is the working file for investigation and execution. It includes
summary and instructions views, page and competitor benchmarks, link gaps,
recently earned links, strongest links, competitor top pages, page-level gaps,
anchor profiles, a scored opportunity list, and execution planning.

Where supported by the evidence, opportunity records preserve the actual linking
URL, competitor destination, anchor text, link attributes, verification date,
matched competitors, factor scores and rationales, contact route, and next action.
Distinct opportunities and unique publisher domains are counted separately.

Missing data stays explicit. A domain-only discovery is not presented as a
verified editorial placement. Stages constrained by missing exports, access, or
quota are disclosed rather than filled with plausible-looking findings.

### A written summary brief

The Markdown brief explains the main constraint as a qualified hypothesis, the
evidence supporting it, immediate priorities, proposed strategic assets, activities
to avoid, and the next review steps. Markdown is a plain-text document you can
read or adapt in your preferred editor.

### A reusable findings file

The `.findings.json` file preserves the structured analysis, sources, decisions,
and coverage information. Keep it with the workbook: the assistant can use it
to revise or rebuild the package without reconstructing the analysis from screenshots.

The standard package contains **Excel, Markdown, and JSON**. Word, PDF, presentation
slides, or screenshot images are additional deliverables to request explicitly.

## How to interpret the scores and decisions

The opportunity score has six components, totaling 100 possible points:

| Component | Maximum points | What it considers |
|---|---:|---|
| Relevance | 30 | Fit between the linking page, your audience, and your topic. |
| Authority | 20 | Page and domain evidence relative to the observed competitors. |
| Traffic or sourced visibility proxy | 15 | Measured traffic or an explicitly sourced substitute, with context. |
| Placement context | 15 | Whether the link is a relevant editorial citation, listing, profile, or another placement. |
| Spam and quality review | 10 | Metrics and inspected page evidence, including unresolved concerns. |
| Contact route | 10 | A real, usable route to a suitable editor or submission process. |

A score of **70 or more** maps to Pursue, **50–69** to Backlog, and **below 50**
to Discard, but only after the required link evidence and all six factor
rationales are present. Missing evidence results in **Verify first**, even if
an imported score is high. These are planning thresholds, not predictions of
traffic or ranking improvements.

The execution plan translates those decisions into:

- **Pursue now:** An evidenced opportunity ready for the next action.
- **Verify:** Missing facts, source-page evidence, or another unresolved requirement.
- **Hold:** Deferred or unsuitable work, with a reason where relevant.
- **Hygiene quick win:** A verified maintenance opportunity, with a recorded reason
  if it differs from the default score-derived action.

Review the rationale as well as the number. A high authority metric alone does
not establish relevance, traffic, or the quality of a particular linking page.
See [Scoring methodology](references/scoring.md) for the full rules.

## Working with exports

If you are supplying data, include files for the client and each intended
competitor. Depending on the scope, useful exports include referring domains,
backlinks or link intersect, recently observed links, most-linked pages, anchors,
and ranking keywords.

For a scored placement, preserve the **actual linking page URL and destination
URL**, the source and verification date, and available anchor, follow status,
page metrics, and contact evidence. A list of domains alone can identify research
leads but cannot complete placement verification.

Tell the assistant which tool produced each file, when it was exported, and any
filters or row limits. Metrics from different providers must retain their source;
similarly named authority scores are not interchangeable. Do not relabel one
provider's metric as Moz Domain Authority or Page Authority.

For column guidance, see [CSV inputs](references/csv-ingest.md). The stricter
coverage and evidence rules in [SKILL.md](SKILL.md) govern final reporting.

## How to use the results

1. Read the summary and coverage notes first. Check whether the scope is complete
   or partial before treating the list as comprehensive.
2. Review the scored opportunities and evidence. Resolve Verify items before
   moving them into outreach.
3. Select a manageable set of actions and assign owners. Use approved facts in
   any proposed pitch, not unsupported product claims.
4. Separate the page an editor would naturally cite from the commercial page
   that benefits through relevant internal links.
5. Review progress at 30, 60, and 90 days using agreed goals, baselines, and sources.
   Track placements, unique linking domains, asset links, and relevant search
   outcomes without attributing every ranking change to the link work.
6. Rerun the gap analysis when appropriate. Keep previous scope and dates visible
   so changes in collection are not mistaken for changes in performance.

If you change the underlying findings, ask the assistant to rebuild the workbook
and brief together. Some summary sections are snapshots and will not automatically
refresh after manual spreadsheet edits.

## Common questions

**Do I need to know how to code?**
No. Provide the inputs and a clear request. Your assistant's environment needs
API access and file execution to do the work.

**What if I do not know my search competitors?**
Provide your target keyword, market, and any current search results you have.
Ask the assistant to distinguish search competitors from business competitors
and to explain the comparison set before research.

**What does a partial report mean?**
Some agreed entities, stages, or result pages could not be covered. The report
should name what is missing and why. An empty successful result is different
from a failed request or an omitted competitor.

**Does the skill send outreach or buy links?**
Running the analysis produces recommendations and a plan. It does not authorize
sending messages. The skill does not recommend purchased placements.

**Can I request a smaller follow-up instead of rerunning everything?**
Yes. Identify the existing workbook or findings file and the exact question,
competitor, page, or stage to revisit. State whether fresh API research is needed.

## Further reference

- [Full skill workflow](SKILL.md)
- [Live Moz call guidance](references/moz-calls.md)
- [Page benchmark methodology](references/serp-benchmark.md)
- [Opportunity scoring](references/scoring.md)
- [CSV input guidance](references/csv-ingest.md)
