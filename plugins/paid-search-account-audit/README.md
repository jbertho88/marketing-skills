# Paid Search Account Audit

Audit a Google Ads or Microsoft Ads account from four report exports and get back a decision doc, not a data dump.

## What it does

The whole method turns on one idea: cost per conversion is not one number, it is two. CPA equals average CPC divided by the click-to-conversion rate. Every diagnosis starts by splitting a rising CPA into the cost half and the quality half, because the fix is completely different depending on which one moved.

From there it:

- Decomposes the CPA trend per business line and names what moved the rate: a single expensive keyword, cheap volume added at a bad rate, a landing page mix shift, a routing break
- Cuts spend and efficiency by business line, bid type, geo, campaign, and match type, and states the arbitrage trade in dollars rather than ratios
- Maps keyword themes to landing pages and classifies every keyword as aligned, partial, mismatch, brand, or generic, with a specific fix per mismatch
- Scores every keyword into pause, rein in, hold, or scale tiers against your CPA target, with a written rationale carrying the actual numbers
- Applies three overrides: downstream CAC beats cost per lead, brand terms never get a blind pause, and broad keywords get their search terms checked before anyone pauses the container
- Mines wasted search terms into themed negative lists, plus a build list of converters that are not keywords yet

## Inputs

Four CSV exports covering the same date range. The skill gives you the exact report and column list for both platforms during intake.

1. Campaign by month by country
2. Keyword by month
3. Search term by month (Microsoft calls it search query)
4. Landing page by campaign by month

Every conversion action needs its own named column. A single rolled-up Conversions column blends funnel stages and makes the analysis impossible.

## Before it runs

The intake is the skill, and it is not optional. It asks how campaigns are named, what each conversion column actually means, which columns are composites of other columns, which stages lag, and what the targets are at the top and bottom of the funnel. Conversion columns in a real account almost never mean what their names suggest, and a wrong funnel mapping poisons every number downstream.

## Outputs

1. **Performance workbook**, one tab per view, plus a README tab defining every metric
2. **Action workbook**, every keyword scored with a tier, an action, and a rationale, with live formulas so you can change a target and watch it re-tier
3. **Written analysis**, one file: the decision doc first, reference detail second, method and caveats third

## Install

```
/plugin marketplace add jbertho88/marketing-skills
/plugin install paid-search-account-audit@marketing-skills
```

Then tell Claude you want a paid search audit and point it at your exports.

## Requirements

Python 3.10+ with `pandas` and `openpyxl`. Search intent scoring in Step 7 is optional and uses a Moz connector if one is available; the skill skips it cleanly when there is not.

## A note on honesty

Step 5 makes the landing page alignment check prove itself before it gets presented as a driver. It often will not, because alignment tracks how a campaign was built rather than how well its keywords convert. The skill reports that result either way. Overselling one weak correlation is how a good audit loses its audience.

## License

MIT
