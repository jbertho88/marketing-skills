---
name: ai-visibility-analysis
description: >-
  Analyze Moz Pro "AI Visibility" prompt-response exports (CSV with Prompt, AI
  Model Response, Brand Terms Mentioned, and a brand rank column named like
  "Bose Brand Rank") and optionally Moz AI Visibility citation exports, then
  produce executive-summary and detailed markdown and Word reports, plus a
  formatted Excel workbook. Use this whenever the user uploads or mentions a Moz AI
  Visibility export, prompt-response data, "brand rank" data, AI search / AEO /
  GEO visibility data, or asks how a brand is performing in AI answers (ChatGPT,
  Gemini, Google AI Mode, Perplexity) relative to competitors. Trigger this for
  any request to analyze AI visibility, benchmark share of voice in AI answers,
  see how a brand does by topic, or find prompt-level strengths and gaps, even if
  the user does not say "skill" or name Moz. Handle one file or several (one per
  model), auto-detect the tracked brand, work for any product category, and add
  citation analysis only when citation CSVs exist.
---

# AI Visibility Analysis

Created by: Jonathan Berthold, VP Revenue of Moz

Last updated: September 9, 2026

Analyze Moz AI Visibility exports and turn them into an executive-ready
recommendation report:

1. Rankings: where the brand ranks on each prompt, in each model.
2. Topics: how it does across topics, grouped automatically from the prompts.
3. Competition: its share of voice and who leads.
4. Strengths and gaps: which prompts it wins and which it loses.
5. Recommendations: a scored, prompt-level fix list built from the metrics.

Produce a two-tier report package: an executive-summary markdown and Word
document, a detailed markdown and Word document, and a formatted Excel
workbook, plus supporting metrics JSON and prompt appendix CSV. When citation
exports are provided, also produce citation metrics JSON and a cited-pages
appendix CSV, then merge the citation layer into the main metrics JSON before
building the report, Word documents, and workbook. Treat this as a single
snapshot, not a time series.
Save outputs in the current workspace, preferably in a clearly named
`outputs/` folder beside the source CSVs unless the user asks for a different
location.

The executive Word document is for leadership reading. The detailed Word
document is for strategist and analyst review. The Excel workbook is the
execution artifact for action planning, prompt QA, citation follow-up, and
prompt portfolio cleanup.

## Inputs

Accept one or more CSV exports, usually one per model. Expect these columns
(case-insensitive): `Prompt`, `AI Model Response`, `Brand Terms Mentioned`, and
`<Brand> Brand Rank`. Read the tracked brand from that last header.

Optional citation exports are model-specific CSV files, usually one per model,
with these columns: `Page` (or legacy `Pages`), `Cited in Prompts`, `Your brand mentioned`,
`PA Score`, `Spam Score`, and `Linking Pages`.

Citation headers are case-insensitive. Counted values such as `Yes (10/20)`
mean partial coverage and are normalized to Mixed; `Yes (7/7)` becomes Yes.
Preserve the source CSV for the original numerator and denominator. The optional
`Citations` column in prompt-response files can be a count, not a URL map.
Do not infer page-to-prompt links from that number.

Treat rank as authoritative. A blank rank means the brand was not mentioned. The
`Brand Terms Mentioned` column is presence only, never a ranking.

Topics are a required planning input. Always ask the user to confirm a fixed
topic set before running the final analysis. If they do not provide one, suggest
topics first, then ask them to approve or edit that list before continuing.

## Accuracy guardrail

Keep every claim bounded to what the AI responses said, not what exists in the
real market. Never write that a product, feature, or competitor "does not
exist" or that the brand "has no product" for something. State absence as
absence in the data ("not surfaced in any analyzed response"). If a gap might be
a real product gap, recommend verification rather than asserting it.

## Narrative style requirements

- Write like a senior growth strategist, not a data export.
- Lead with implication, then evidence.
- Use concise paragraphs.
- Avoid repeating the same sentence structure across plays.
- Avoid generic phrases like `direct answer blocks` unless paired with a concrete example.
- Prefer `what this means` over `what the metric is`.
- Keep the executive summary selective and confident.
- Keep the detailed report analytical but readable.
- Never invent claims beyond the data.
- Use softer language when sample sizes are small or confidence is low.

## Workflow

### 1. Locate files and label models

Support ChatGPT, Gemini, Google AI Mode, and Perplexity independently. Include
only supplied models; missing model data is not brand absence. A newly supported
model still needs its own export.

Find the CSV exports in the current workspace or in the files the user
provided, one per model. Derive the model label from an explicit user label,
then an in-file Model column, then the filename, then image hosts. ChatGPT
auto-detects reliably; Gemini and Google AI Mode can share hosts, so if a label
is ambiguous or returns `UNKNOWN:...`, ask the user to confirm, then pass
`--model`.

Use the Python launcher that exists in the environment (`python`, `py -3`, or
equivalent). If Windows only exposes the Microsoft Store alias and not a real
Python runtime, use WSL `python3` instead and translate file paths to
`/mnt/<drive>/...`. Run commands from the skill directory or use absolute script
paths.

Before comparing models, verify the same brand, snapshot/date range, market,
language, and prompt cohort. Resolve mixed-model files and duplicate model labels
before running. Label unmatched prompts as not tracked; do not interpret them as
absence. Use the intersection of tracked prompts for like-for-like comparisons
and disclose its size. Preserve full-cohort results separately.

### 2. Confirm the topic set

Always ask the user for custom topics before the final run. If they do not have
a ready-made taxonomy, generate suggestions from the prompts and ask them to
approve or edit the list:

```bash
python scripts/suggest_topics.py <file1.csv> [<file2.csv> ...] \
    --max-topics 10
```

If WSL is the only available Python runtime, invoke the helper through
`wsl.exe bash -lc "python3 /mnt/.../suggest_topics.py ..."` and pass WSL paths.

Use the suggestions as a draft taxonomy, not as final truth. Present the list to
the user and get confirmation before analysis. Do not skip this step.

### 3. Run the engine

```bash
python scripts/analyze_visibility.py <file1.csv> [<file2.csv> ...] \
    [--model "ChatGPT" --model "Gemini" --model "Google AI Mode" --model "Perplexity"] \
    --topics "listings, citations, reviews, rank tracking" \
    --out outputs/<brand>-metrics-<date>.json \
    --csv outputs/<brand>-prompt-appendix-<date>.csv
```

Pass the user-confirmed topic list explicitly. Read the JSON output rather than
inferring metrics from the CSV by hand.

If citation CSVs exist, run the optional citation layer first:

```bash
python scripts/analyze_citations.py \
    --brand "<Brand>" \
    --owned-domains example.com \
    --citation ChatGPT="path/to/chatgpt-citations.csv" \
    --citation Gemini="path/to/gemini-citations.csv" \
    --citation "Google AI Mode=path/to/google-ai-mode-citations.csv" \
    --citation Perplexity="path/to/perplexity-citations.csv" \
    --out-json outputs/<brand>-citation-metrics-<date>.json \
    --out-csv outputs/<brand>-cited-pages-<date>.csv
```

Then pass the citation JSON into the main prompt-response run:

```bash
python scripts/analyze_visibility.py <file1.csv> [<file2.csv> ...] \
    [--model "ChatGPT" --model "Gemini" --model "Google AI Mode" --model "Perplexity"] \
    --topics "listings, citations, reviews, rank tracking" \
    --citation-json outputs/<brand>-citation-metrics-<date>.json \
    --out outputs/<brand>-metrics-<date>.json \
    --csv outputs/<brand>-prompt-appendix-<date>.csv
```

If WSL is the only available Python runtime, invoke the script through
`wsl.exe bash -lc "python3 /mnt/.../analyze_visibility.py ..."` and pass WSL
paths for both the inputs and the outputs.

Per model, the output includes totals and visibility rate, average rank and rank
distribution, share of voice, leader and leader gap, head-to-head per
competitor, configured topic coverage, fallback report-topic coverage, response
trend summaries, competitor roles, and prompt lists. With 2+ files it adds a
`cross_model` block. It also adds `category_leader`, `topic_mapping`,
`competitor_analysis`, `response_trends`, `strategic_plays`, `appendix_records`, and
`recommendations`: one object per flagged prompt (absent, rank 3+,
cross-model inconsistent, weak-topic, losing to the leader, or a near-duplicate)
with topics, report topic, prompt cluster, persona or use-case cluster, intent,
funnel stage, model ranks and status, competitor winners, gap type, reason
codes, fix type, recommended action, recommended assets, priority score
(0 to 100), confidence, effort, owner, and an action bucket
(Defend / Reclaim / Build / Verify / Retire). The full prompt-level appendix is
written to the `--csv` path; link to it instead of embedding it in the report.

Read definitions and scoring details in `references/methodology.md`.

Treat the engine's recommendations as heuristics. Sanity-check the top items
against the actual prompts before presenting them, and apply the accuracy
guardrail: a `likely_product_fit_question` means verify, never assert a product
gap.

### 4. Build the report, then the Word and Excel versions

Prefer the bundled report builder so the output stays marketer-friendly,
executive-ready, and uses human labels instead of raw machine codes. Run:

```bash
python scripts/build_report.py outputs/<brand>-metrics-<date>.json \
    outputs/<brand>-ai-visibility-detailed-report-<date>.md \
    --executive outputs/<brand>-ai-visibility-executive-summary-<date>.md
```

Then build the Word versions:

```bash
python scripts/build_docx.py outputs/<brand>-ai-visibility-executive-summary-<date>.md \
    outputs/<brand>-ai-visibility-executive-summary-<date>.docx

python scripts/build_docx.py outputs/<brand>-ai-visibility-detailed-report-<date>.md \
    outputs/<brand>-ai-visibility-detailed-report-<date>.docx
```

Then build the workbook:

```bash
python scripts/build_xlsx.py outputs/<brand>-metrics-<date>.json \
    outputs/<brand>-ai-visibility-<date>.xlsx
```

Keep the markdown to the converter's supported subset: one H1 title, an italic
subtitle line, H2 and H3 sections, pipe tables, bullet and numbered lists,
inline `code`, and inline **bold**. Present the executive `.docx` first, then
the detailed `.docx`, then the `.xlsx`, then the markdown files, then the
appendix CSV and metrics JSON.

`build_docx.py` and `build_xlsx.py` are self-contained and use only the Python
standard library, so they should run in plain Python 3 without extra packages.
If native Windows Python is not usable, run the converters through WSL
`python3` with `/mnt/...` paths.

If you write or revise the report manually, never expose raw internal enums such
as `cross_model_inclusion_gap` or `tracking_cleanup_candidate` in client-facing
tables. Use the human labels from the metrics output, such as `Visible in some
models only`, `Present, but not prominent`, or `Cleanup or consolidate`.

Build the report, Word document, and Excel workbook sequentially, not in
parallel. The markdown, `.docx`, and `.xlsx` all depend on the final metrics
JSON. Citation sections and sheets should appear only when the merged metrics
JSON contains an enabled `citation_analysis` object.

### 5. Optional business scoring and citation verification

When requested, read [Business priority](references/business-priority.md) for
separate search-intent and prompt-format labels, prompt value scoring, verified
citation actions, and optional Moz organic-search enrichment. Use its scoring
helper on reviewed inputs and deliver the supplementary CSVs. These are custom
planning scores, separate from the engine's existing priority metrics; base
report builders do not automatically incorporate them.

For users with a Moz API subscription and an enabled Moz MCP connection, offer
the optional live exact-page ranking-keyword enrichment in that reference's
Organic reach enrichment section. When requested, discover the live ranking
tool, check the market and usage scope, fetch a bounded citation-page shortlist,
and use the evidence to estimate organic-search reach and enrich citation scores.
Keep the export-only workflow available when access or data is missing. Live
ranking inputs still produce modeled reach, not measured page or AI traffic.

Always verify citation export field semantics before equating brand mention in
an export with brand presence on a source page or in an AI answer. Keep those two
observations separate. Without page/response inspection, label inclusion and
context recommendations as hypotheses requiring verification.

## Report template

Lead with the scorecard. Stay concrete and tight. Use numeric share-of-voice
values in competitor tables; never use qualitative labels like high or mid. If
topics came from a suggested draft, say the user confirmed them before the final
run. Topics in the appendix should never be blank; if the clustering pass is
sparse, use the richer fallback themes to propose a better draft before asking
for confirmation.

```markdown
# {Brand} AI Visibility Report
*{Models} - {N} prompts per model - snapshot {date}*

## Executive snapshot
One-paragraph verdict, then a per-model table: visibility, average rank, share
of voice, leader, and gap. Add flat bullets for category leader, model
strength, biggest topic strength, biggest topic weakness, and highest-priority
action. Do not say visibility "falls off sharply" unless the spread is clearly
large.

## Model-by-model performance
For each model, include visibility, average rank, share of voice, leader and
gap, top strengths, top weaknesses, and a response-pattern summary grounded in
the AI Model Response text.

## Competitive landscape
Use a compact competitor table with numeric share of voice, competitor role,
strongest topics, and threat prompts. Prefer specific roles such as
`category_all_rounder`, `sound_quality_specialist`,
`value_or_budget_challenger`, `enterprise_or_platform_competitor`,
`lifestyle_or_use_case_competitor`, or `niche_specialist`. Follow with short
marketer-readable bullets on what each major competitor threatens.

## Topic/category performance
Split topics into tracked topics with matched prompts and underrepresented or
untracked topics. If user-supplied topics map sparsely, say so clearly and use
richer fallback prompt clusters for the main topic read. Include a topic x model
table with prompt count, visibility, average rank, weak or absent count, and
action bucket. Add compact tables for performance by funnel stage, intent, and
persona or use-case cluster.

Tracked topic counts are not mutually exclusive. A single prompt can match more
than one tracked topic, so the topic counts in this section can add up to more
than the number of unique prompts in the export. Use a primary topic or report
topic later in the report for readability, but do not imply that the underlying
topic matching is one-prompt-to-one-topic.

## Model response trends
Summarize recurring positive attributes, negative attributes, common framing,
reasons competitors win, and reasons the tracked brand is included. Use the AI
Model Response text only. Classify an attribute as negative only when negative
modifiers appear near the brand and attribute in the response language. Make no
source or citation claims.

## Strategic recommendation plays
Lead with grouped strategic plays, not raw prompts. Each play should include:
play name, score, bucket, owner, effort, confidence, competitor threat,
affected models, prompt cluster, why it matters, recommended assets,
recommended actions, language angle, and supporting prompts. Deduplicate
near-identical plays and use human-readable campaign names instead of raw
taxonomy labels. After that, add compact prompt-level tasks as supporting
detail.

Preferred play card format:

PLAY NAME
Score | Bucket | Owner | Effort | Confidence
Threat:
Affected models:
Prompt cluster:
Why it matters:
Recommended assets:
Recommended actions:
Language angle:
Supporting prompts:

Good examples:

- Build sound-quality authority
- Reclaim audiences and segments
- Strengthen battery and durability proof
- Build listing management coverage
- Clean up review-management tracking

Bad examples:

- Build authority in sound quality and audio features: Wireless Bluetooth and connectivity
- Recover calls and work: Wireless Bluetooth and connectivity

## Defend / Reclaim / Build / Verify / Retire matrix
Show bucket counts, score status, typical effort, plus compact confidence and
effort breakdowns. Use this score language consistently:

- For Build, Reclaim, and Verify, show opportunity score.
- For Defend, show defense priority or protected status.
- For Retire, show cleanup priority.
- Do not present Defend rows as `0.0` score opportunities in the Word report.

Phrase Verify items as verification, never as asserted product gaps.

## Prompt portfolio cleanup
Break this into: consolidate duplicate or overlapping prompt clusters, keep
deliberately for authority, retire low-value or no-surface prompts, add missing
high-intent prompts, and rebalance by funnel, intent, and topic.

The cleanup section should be specific and actionable. Separate:

- Add
- Consolidate
- Keep
- Retire

For each cleanup recommendation, include:

- prompt or prompt cluster
- reason
- recommended action
- whether it belongs in the scorecard or only in thought leadership tracking

Cleanup logic should distinguish true visibility gaps from low-signal prompts:

- If the tracked brand is absent but competitors surface, treat that as a real
  visibility gap to fix, not a cleanup candidate.
- If no brands surface at all and the prompt behaves like low-signal authority
  tracking, treat it as a candidate to remove from the core scorecard or keep
  only in authority or thought-leadership tracking.
- Use `Consolidate` only for true duplicate or overlapping prompt clusters, not
  for ordinary weak performance.
- Use `Add` for missing high-intent prompts, weak intent coverage, sparse topic
  coverage, or obvious portfolio imbalance.

## Appendix reference
Point to the appendix CSV file with every tracked prompt, its ranks, status,
report topic, prompt cluster, and recommendation fields.

## Citation opportunity analysis
If citation metrics exist, add a dedicated section with:

- citation visibility summary
- top cited pages without brand mention
- cross-model citation opportunities
- domain or publisher opportunity scorecard
- model citation trends
- recommended citation actions
- citation data quality notes

Keep the DOCX executive-friendly:

- show only the top 10 cited pages
- show only the top 10 domains
- keep detailed cited-page rows in Excel
- avoid giant citation tables in the Word document
```

## Notes

- Analyze one brand per report. If files reference different brands, flag it and
  analyze the intended one.
- Keep both outputs copy-paste clean: standard markdown, no HTML, no em dashes.
- If recommendation copy drifts into generic "build a page" phrasing, rewrite it
  into marketer-actionable language that includes third-party review, retailer,
  partner, or publisher surfaces where appropriate.
- The DOCX should be more executive-friendly than the markdown. It should use an
  executive snapshot near the top, keep model performance readable, keep wide
  data tables compact, render Strategic Recommendation Plays as card-style
  blocks, split Strategic Growth Plays from Portfolio Cleanup Plays, show only
  the top 3-4 growth plays in the main document, push detailed prompt-level work
  to the Excel workbook or appendix reference, and include page numbers plus
  snapshot metadata in the footer. Visually, prefer a clean left-aligned title
  block, strong teal section headers, compact bordered tables with dark header
  rows, alternating row fills, and tighter executive spacing over plain default
  Word styling.
- The Excel workbook should be treated as the execution artifact. Expected
  sheets are `Action Plan`, `Prompt Appendix`, `Strategic Plays`, `Model x
  Topic`, `Portfolio Cleanup`, and `Data Dictionary`. When citation analysis is
  enabled, also add `Citation Action Plan`, `Cited Pages`, `Citation Domains`,
  `Cross-Model Citations`, and `Model Citation Trends`. Verify that the workbook
  opens cleanly and contains all required sheets before delivery.
- Citation normalization matters. Lowercase scheme and hostname, remove
  fragments and common tracking parameters, preserve raw URLs for QA, and
  dedupe Gemini fragment-heavy links to canonical pages before scoring them.
- Treat citation analysis as influence mapping, not just an outreach list. The
  strategic read is which pages and domains shape AI answers, where the brand is
  absent, and which of those sources are actually worth trying to influence.
