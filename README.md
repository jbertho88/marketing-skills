# Marketing Skills

Marketing skills I actually use, packaged as a Claude Code plugin marketplace. Four so far, more as I clean them up.

These are not prompt templates. Each one is a full skill: instructions, reference docs, and where it helps, Python that builds the deliverable. You point them at real exports and you get back a report or a workbook you can put in front of a client.

## Install

```
/plugin marketplace add jbertho88/marketing-skills
/plugin install backlink-gap-analysis@marketing-skills
```

Swap the plugin name for whichever you want. Install all of them if you want the full set.

To see what is on offer first:

```
/plugin marketplace add jbertho88/marketing-skills
/plugin
```

Not on Claude Code? Every skill is a plain folder under `plugins/<name>/skills/<name>/`. Copy it into whatever skills directory your tool uses. The per-skill READMEs cover platform specifics.

## SEO and AI search

Where most of my work lives.

### ai-visibility-analysis

Moz AI Visibility exports in, executive-ready recommendation out.

It reads prompt-response CSVs (one per model is fine) and optional citation exports, then reports where the brand ranks per prompt, how it performs by topic, its share of voice against competitors, and the prompt-level gaps worth fixing. Ships a markdown executive summary, a detailed report, a Word version, and a formatted Excel workbook.

Auto-detects the tracked brand. Works for any product category. Covers ChatGPT, Gemini, Google AI Mode, and Perplexity.

### backlink-gap-analysis

Starts at the SERP, not at a tool export.

Benchmarks how many domains link to each ranking page, finds the domains and pages linking to competitors but not to you, works out what actually earned those links, scores every opportunity, and hands back a workbook plus a sequenced outreach plan. Runs live on the Moz connector or ingests a CSV from any backlink tool with the right columns.

It is deliberately careful about causation. Link metrics generate hypotheses. They do not prove why a page ranks, and the skill says so in the output rather than letting you pretend otherwise.

### seo-workbook-builder

Screaming Frog crawl plus ranking data, out the other side as a keyword-mapped workbook.

Maps a target keyword to every page, classifies page types, assigns optimization priority, and adds a status column so the work is trackable. This is the gap between "I have data" and "I know what to optimize."

## Paid search

### paid-search-account-audit

A full Google Ads or Microsoft Ads account audit from four report exports.

It turns on one idea: cost per conversion is not one number, it is two. CPA equals average CPC divided by the click-to-conversion rate, so every diagnosis starts by splitting a rising CPA into the cost half and the quality half. The fix is completely different depending on which one moved.

From there it scores every keyword into pause, rein in, hold, or scale tiers against your target, checks whether keywords are pointed at the right landing pages, and mines wasted search terms into themed negative lists. Downstream CAC overrides cost per lead, brand terms never get a blind pause, and broad keywords get their search terms checked before anyone pauses the container. Out comes a performance workbook, an action workbook with live formulas, and a written analysis that leads with decisions.

The intake is the skill and it is not optional. Conversion columns in a real account almost never mean what their names suggest, and a wrong funnel mapping poisons every number downstream.

## Requirements

Python 3.10+. The workbook and Word builders want `openpyxl` and `python-docx`; the paid search audit also uses `pandas`. The backlink and AI visibility skills work best with a Moz API subscription and the Moz MCP connector enabled, but both accept CSV exports instead. The paid search audit can optionally pull keyword intent from the same connector and skips that step cleanly without it.

## Contributing

Issues and PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. Use them, fork them, adapt them for your own stack.

Built by [Jonathan Berthold](https://jonathanberthold.com), VP Revenue at Moz.
