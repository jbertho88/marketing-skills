# AI Visibility Analysis

Created by: Jonathan Berthold, VP Revenue of Moz

Last updated: September 9, 2026

## What this skill does

This skill analyzes Moz Pro AI Visibility exports and produces:

- Executive summary markdown
- Executive summary DOCX
- Detailed report markdown
- Detailed report DOCX
- Excel workbook
- Prompt appendix CSV
- Cited pages CSV when citation files are included

Use it for any brand where you want to understand AI answer visibility across
ChatGPT, Google AI Mode, Gemini, and Perplexity.

## Before you start

- To collect fresh exports, you need access to a Moz Pro AI Visibility dashboard
  that is collecting data. Existing exports can be analyzed without a live connection.
- Your assistant needs access to the complete skill folder, its scripts, a Python 3
  runtime, and file execution to generate the report package. Instructions alone
  do not provide execution capabilities.
- A Moz API subscription and enabled, authenticated Moz MCP connection are needed
  only for optional live ranking-keyword enrichment, not the base CSV analysis.
- You should analyze one brand at a time.
- You should confirm a fixed topic set before the final run.

## Download the right files from Moz Pro

For a complete four-model analysis with citations, download eight files:

- 4 prompt-response CSVs, one per model.
- 4 cited-pages CSVs, one per model.

One model or a subset of models is also supported. Citation files are optional.
Use the same brand, prompt set, market, language, and collection window wherever
possible. Cross-model win/gap classifications require matched prompts; a prompt
missing from an export is not a brand absence.

### Prompt Responses

For each model, download one prompt-response file:

- ChatGPT
- Google AI Mode
- Gemini
- Perplexity

Steps:

1. Navigate to the `Prompts` tab in Moz Pro AI Visibility.
2. Click `Export`.
3. Download as `CSV`.
4. Make sure `Yes, include prompt responses markdown` is selected.
5. Repeat for ChatGPT, Google AI Mode, Gemini, and Perplexity.
6. Rename each file so the model name is clearly in the filename.

### Citations

For each model, download one cited-pages file:

- ChatGPT
- Google AI Mode
- Gemini
- Perplexity

Steps:

1. Navigate to the `Citations` tab.
2. In the citations table, choose `Cited Pages`.
3. Before exporting, make sure the columns include `Your brand mentioned`.
4. Once the needed columns are enabled, click `Export`.
5. Download as `CSV`.
6. Repeat for ChatGPT, Google AI Mode, Gemini, and Perplexity.
7. Rename each file so the model name is clearly in the filename.

The importer accepts `Page` or legacy `Pages`, and citation headers are
case-insensitive. Include `Cited in Prompts`, `Your Brand Mentioned`, `PA Score`,
`Spam Score`, and `Linking Pages`. Counted values such as `Yes (7/7)` are treated
as Yes; partial values such as `Yes (10/20)` become Mixed. Preserve the original
exports for their exact fractions.

A mention status does not by itself establish brand presence on the source page
or in a particular answer. The analysis checks those observations separately.
The prompt-response `Citations` column may contain a count rather than URLs; a
count cannot establish which pages were cited by an individual prompt.

Export controls may change. The required file contents above are the compatibility
check; verify the current product controls when following the download steps.

## Required workflow rule

This skill should always ask the user to confirm a fixed topic set before the
final analysis run. If the user does not already have one, the skill should
suggest topics from the prompt exports and wait for approval.

## Optional business scoring

Ask for business scoring when you want to prioritize prompts and citation work.
Provide your audience, offer, business objective, and any evidence of customer
needs. The assistant separates search intent (informational, commercial,
transactional, navigational) from prompt format (such as a comparison or shortlist).

- **Prompt Value** combines relevance, decision value, and customer evidence.
- **Citation Value** combines relevance, targeted prompt coverage, model breadth,
  source quality, and optional modeled organic-search reach.
- **Action Priority** combines citation value with a verified improvement opportunity.

These custom planning scores are separate from official Moz metrics and the
skill's original priority scores. Missing inputs are flagged, and partial scores
are provisional. The scoring helper runs on reviewed inputs; it does not invent
customer research or verify source pages automatically.

Scored prompt and citation CSVs are delivered alongside the base report package.
The existing report builders do not automatically add these new scores to Word
or Excel. Ask for report/workbook integration if you want them included there.
See [Business priority methodology](references/business-priority.md) for formulas,
input fields, evidence requirements, and helper commands.

## Optional live Moz MCP enrichment

If you have a Moz API subscription and Moz MCP enabled in your assistant, you can
request ranking-keyword data for shortlisted citation pages without downloading
those keyword exports manually.

The assistant checks the connected tools, your target market, and usage scope;
fetches exact-page ranking keywords; saves the evidence; and uses documented
click-through assumptions to estimate organic-search reach. The default starting
scope is five relevant URLs, at most two pages of 50 keyword rows per URL. It
respects available allowance and authorized limits, and reports partial coverage.
An active subscription does not mean API usage is unlimited or free.

The current ranking tool covers indexed top-50 rankings. Even complete results
are not all traffic to a page. Missing results are not proof of zero traffic.
Estimates remain **modeled organic-search reach**, not observed visits, AI referral
traffic, or revenue. Fetching ranking data does not supply missing prompt-to-page
citation links.

If access or necessary data is unavailable, provide an exact-page ranking-keyword
CSV or continue without the reach component. Never paste API secrets into chat.

Optional addition to your analysis request:

```text
I have a Moz API subscription and Moz MCP enabled. Enrich my top five relevant
citation pages with exact-page ranking keywords for [target market], within my
available allowance. Save the source data, show the estimation assumptions and
coverage limits, and use modeled organic reach in the optional citation scoring.
```

## Install and use by platform

### Codex

Installation path:

- Put the skill folder in `<your-codex-skills-dir>/ai-visibility-analysis`

How to use:

1. Make sure the skill folder is available in your local Codex skills directory.
2. Put the Moz export CSVs in the workspace.
3. Invoke the skill explicitly and point Codex at the skill path.
4. Ask Codex to confirm the fixed topic set before the final run.

Recommended prompt:

```text
Use $ai-visibility-analysis at <your-codex-skills-dir>/ai-visibility-analysis to analyze these Moz AI Visibility exports. First ask me to confirm a fixed topic set for the prompt-response CSVs. If I do not provide one, suggest topics from the prompts and wait for approval before running the final analysis. If citation export CSVs are also present, run the optional citation analysis layer and merge it into the final report and workbook.
```

### Claude

How to install/use:

1. Make the complete skill folder, including scripts and references, available
   to your Claude environment. Ensure file execution is enabled; pasting guidance
   alone is not sufficient to run the report builders.
2. Add the Moz export CSVs to the working folder or project files.
3. Instruct Claude to ask for a fixed topic set before running the final analysis.
4. If citation files exist, instruct Claude to include the citation layer.

Recommended prompt:

```text
Analyze these Moz AI Visibility exports using the workflow in this skill. Before running the final analysis, ask me to confirm a fixed topic set for the prompt-response CSVs. If I do not provide one, suggest a topic list from the prompts and wait for approval. If citation export CSVs are also present, run the optional citation analysis layer and merge it into the final report and workbook. Then generate the metrics JSON, prompt appendix CSV, executive summary MD/DOCX, detailed report MD/DOCX, and Excel workbook.
```

### Cursor

How to install/use:

1. Add the skill folder to your project context, agent rules, or workspace instructions.
2. Place the Moz export CSVs in the project or workspace.
3. Ask Cursor to inspect the files and request a fixed topic set before the final run.
4. If citation files exist, tell Cursor to run the citation layer too.

Recommended prompt:

```text
Use the AI Visibility Analysis workflow in this project. First ask me to confirm a fixed topic set for the uploaded Moz AI Visibility prompt-response CSV exports. If I do not provide one, suggest a topic list from the prompts and wait for approval before you run the final analysis. If citation export CSVs are also present, run the optional citation layer and merge it into the final report and workbook.
```

## Expected output set

- `*-metrics-<date>.json`
- `*-prompt-appendix-<date>.csv`
- `*-ai-visibility-executive-summary-<date>.md`
- `*-ai-visibility-executive-summary-<date>.docx`
- `*-ai-visibility-detailed-report-<date>.md`
- `*-ai-visibility-detailed-report-<date>.docx`
- `*-ai-visibility-<date>.xlsx`
- `*-citation-metrics-<date>.json` when citation files exist
- `*-cited-pages-<date>.csv` when citation files exist

When live enrichment runs, also expect `moz-ranking-keywords.csv` and
`citation-organic-reach.csv`. Requested business scoring produces additional
scored CSVs with component coverage and score status. These supplements do not
replace the original metrics or appendices.

## Quality expectations

- Topics should be explicit and user-confirmed.
- Every prompt in the appendix should have a topic.
- Client-facing outputs should never expose raw internal labels like `cross_model_inclusion_gap`.
- Recommendations should read like marketer guidance, not machine output.
- The executive report should be selective and leadership-friendly.
- The detailed report should preserve the deeper analyst read.
- The Excel workbook should open cleanly with no corruption warnings.
- Citation recommendations should distinguish verified evidence from hypotheses.
- Source-page presence and AI-answer presence should be recorded separately.
- Comparisons should disclose matched prompt counts and missing model data.
- Rank and share of voice describe the exported fields and tracked competitive
  set, not necessarily every brand named in the answer.
- Snapshot differences do not establish that an edit caused a visibility change.
- Citation analysis should behave like influence mapping, not just a source dump.

## Notes

- If Windows Python is not available, use WSL `python3`.
- Gemini citation exports can contain fragment-heavy duplicate URLs, so canonical deduplication matters.
- The Excel workbook is the execution artifact.
