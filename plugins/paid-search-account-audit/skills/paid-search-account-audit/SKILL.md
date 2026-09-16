---
name: paid-search-account-audit
description: "Run a paid search account audit end to end, from report exports to a decision doc. Diagnose why cost per conversion moved by splitting it into a CPC half and a conversion rate half, score every keyword against CPA targets, check landing page alignment, and mine wasted search terms. Use whenever someone asks for a Google Ads or Microsoft Ads audit, a PPC or paid search audit, or an account review; asks why cost per lead, CPA, CAC or cost per conversion is rising or missing target; asks which keywords to pause, rein in, or scale, where paid budget is being wasted, which search terms to add as negatives, or whether keywords point at the right landing pages; hands over campaign, keyword, search term, or landing page exports from either platform; or asks how brand, non-brand, and competitor spend compare. Works for any vertical, currency, or date range."
---

# Paid search account audit

*Author: Jonathan Berthold (JB), VP of Revenue, Moz. Created September 16, 2026. Version 1.0.*

Turns four report exports into three deliverables: a monthly performance workbook, an action workbook where every keyword is scored and every wasted search term is listed, and a written analysis that leads with decisions.

The method is built around one idea: **cost per conversion is not one number, it is two.** Cost per conversion equals average CPC divided by the click-to-conversion rate. Every diagnosis in this skill starts by splitting a rising CPA into the cost half and the quality half, because the fix is completely different depending on which one moved.

Do not skip Step 1. The intake is the skill. Conversion columns in a real account almost never mean what their names suggest, and a wrong funnel mapping poisons every number downstream.

---

## Step 1: Intake

Ask before touching any data. Use AskUserQuestion, batched, not one question per turn.

### 1a. What the account sells and how it is segmented

- What business lines, products or regions does the account cover? How are they encoded in campaign names?
- What are the naming conventions? Get the literal substrings. Typical patterns: brand vs non-brand vs competitor, product token, geo tier, match type, legacy agency prefixes.
- Warn them up front: **legacy tokens in campaign names lie.** Names like `under150cac` or `q3-target-200` are frozen at the moment the campaign was created. Ask which naming elements are still true and which are fossils, and ignore the fossils.
- Date range, and whether any month is partial. A partial final month must never be compared to full months without saying so.

### 1b. The conversion funnel (the critical one)

Never infer this. Ask the user to describe each conversion column they want counted, and for each one get:

| Field | Why it matters |
|---|---|
| Exact column name in the export | Exports rename things. Get the literal string. |
| Funnel stage: top, mid, or bottom | Decides which cost-per metric it drives and what the rates are between stages. |
| Target cost for that stage | Drives the whole keyword rubric. |
| Reporting lag, in days | Decides which recent-month numbers are real and which are still filling in. |
| Overlap with other columns | The trap below. |

**Top of funnel** is what the campaign optimizes to: lead, free trial, demo request, account created, signup.
**Mid funnel** is qualification: MQL to SQL, activation, trial to first value.
**Bottom of funnel** is money: paid signup, closed won, first invoice.

**The overlap trap.** Ask explicitly: does any conversion column contain another? Accounts routinely carry a "Paid Signups" column that is the sum of two other columns already in the export. Summing all of them double counts. Get the user to state which columns are additive and which are composites, and record it.

**The lag asymmetry.** Ask which stages lag and which do not. This one distinction changes the entire read of a recent month. If the top-of-funnel conversion has no lag and its cost spiked, that is a live campaign problem to fix this week. If only the downstream stage lags, the recent CAC is understated and should be labelled as such, not diagnosed. Say this back to the user in the final doc.

**Secondary rates worth computing** once stages are mapped: stage-to-stage conversion rate, same period and lagged. Show both when the lag is real, and say which one you trust.

### 1c. Targets and overrides

- Target cost per top-of-funnel conversion, per business line. If they do not have one, offer the year-to-date actual as the target and say you are doing so.
- Target cost per bottom-of-funnel conversion (the real CAC target). Ask for this even if they only volunteer the top-of-funnel number.
- Ask whether the bottom-of-funnel target **overrides** the top-of-funnel one. This matters more than it sounds. A keyword can look terrible on cost per lead and be excellent on cost per customer, because the people searching it skip the trial and just buy. Default rule, confirm it with the user:
  - At or under the CAC target: Scale, whatever the top-of-funnel cost says.
  - Between the CAC target and 1.25x it: Watch and analyse. This overrides a 3x top-of-funnel flag.
  - Above 1.25x the CAC target: score on top-of-funnel cost as normal, but name the CAC in the rationale.

### 1d. Which reports to pull

Give the user this list verbatim. All four are needed. Tell them to export as CSV.

**Google Ads.** Reports, then Predefined reports or a custom table.

| # | Report | Rows | Segments | Columns |
|---|---|---|---|---|
| 1 | Campaign x Month x Country | Campaign | Month, Country/Territory (user location) | Cost, Impressions, Clicks, CTR, Avg CPC, Impr. share, plus **every conversion column by name** |
| 2 | Keyword x Month | Search keyword, Match type, Status, Campaign, Ad group | Month | Cost, Clicks, Impressions, Avg CPC, Quality Score, plus every conversion column |
| 3 | Search terms x Month | Search term, Match type, Campaign, Ad group | Month | Cost, Clicks, Impressions, plus every conversion column |
| 4 | Landing page x Campaign x Month | Landing page (or Final URL), Campaign | Month | Cost, Clicks, plus every conversion column |

**Microsoft Ads.** Reports, then the named report, then add the columns.

| # | Microsoft equivalent | Notes |
|---|---|---|
| 1 | Campaign report, with Geographical location and Time (Month) | Use "Location (user location)", not "Location of interest" |
| 2 | Keyword report, Time = Month | Include Match type, Keyword status, Ad group |
| 3 | Search query report, Time = Month | Microsoft calls it Search query, not Search term |
| 4 | Destination URL report or Website URL (publisher) report, Time = Month | Microsoft splits final URL reporting; ask which one their tracking uses |

**Column instruction to pass along, both platforms:** add every conversion action as its own named column, not just the rolled-up "Conversions" total. A single Conversions column blends stages and makes the whole analysis impossible. If the platform forces a single column, they need one export per conversion action.

**The duplicate export trap.** If a report offers both a count and a rate for the same conversion (for example "Accounts Created" and "Account Rate"), the rate version is useless for cost-per analysis. When two exports have near-identical names, open both and check which carries counts. Pick the counts file, and say in the method notes which one you used.

---

## Step 2: Load and validate

Data usually lives on the user's machine. Work there with `device_bash` rather than staging files into the cloud. Stage only when a step needs a library or a renderer that is not available locally.

Write one shared loader module so all four files parse identically:

```python
def load(path, skip=2):
    # Ads exports carry 2 junk rows above the header
    df = pd.read_csv(path, skiprows=skip, thousands=',')
    # strip % from rate columns, coerce '--' and ' --' to NaN
    # coerce currency strings to float
    return df
```

Known parsing traps, handle all of them:

- Two junk rows above the header (Google), one or three (Microsoft, varies by report).
- `--` and `" --"` used for null.
- Thousands separators inside numeric strings.
- Percent columns arriving as `"4.31%"` strings.
- A totals row at the bottom of some exports. Drop it, then validate that your computed total matches it.

**Then reconcile.** Sum cost in all four files. They will not match exactly (search terms and landing pages under-report against campaign totals), but they should be within a few percent. If one is off by more than that, you have a filter or a date-range mismatch and must fix it before analysing. Record the reconciliation in the method notes.

Derive helper columns once, from campaign name, using the conventions from Step 1a: product or business line, bid type (competitor first, then non-brand, then brand, since campaign names often contain more than one token), geo tier.

---

## Step 3: Diagnose the trend

This is where the skill earns its keep.

For each business line, by month: spend, clicks, avg CPC, each conversion count, cost per conversion at each stage, click-to-conversion rate, stage-to-stage rates.

Then decompose. For any period where cost per conversion moved, compute:

```
CPA = CPC / (conversions / clicks)
```

Change in CPA splits into a CPC component and a conversion rate component. State them separately and in the same sentence:

> "Between [period A] and [period B], average CPC fell [X]% while the click-to-conversion rate fell [Y]%, so cost per conversion rose [Z]%. This is not a bidding problem."

Then find what moved the rate. The usual suspects, check each:

1. **A single expensive keyword.** Sort keywords by share of spend. If one term is 20%+ of a business line's spend, chart its CPC by month on its own.
2. **Volume added at a bad rate.** Find campaigns or themes that added large click volume with a conversion rate far below account average. Cheap clicks that do not convert raise blended CPA while lowering blended CPC, which is exactly the fingerprint above.
3. **Landing page mix shift.** Compute the share of clicks going to primary conversion pages by month. A drop here is a routing change, not an auction change.
4. **A routing break.** Look for a campaign whose landing page distribution changes abruptly between two months. The tell is a page that took hundreds of clicks last month and near zero this month, with spend unchanged.
5. **Seasonality or mix.** Check geo and device mix before blaming anything structural.

**Isolating a break.** When you suspect a break, find the control. If one campaign's routing changed and a structurally similar campaign did not, and the untouched one held or improved, that argues for a campaign-level change rather than a site-wide problem. Name the control in the writeup. This is the difference between a finding and a guess.

---

## Step 4: Segment analysis

Cut spend and cost per conversion by:

- Business line x bid type (brand, non-brand, competitor)
- Geo tier, and individual countries above a spend floor
- Campaign, sorted by spend
- Match type

**The arbitrage check.** For each business line, compare cost per conversion across bid types, then state the trade in plain money: "[Expensive segment] spent $[cost] and bought [n] conversions. At [cheap segment]'s cost per conversion of $[c], the same money buys [n2]." That framing lands where a ratio does not. Caveat it honestly: the cheaper segment is usually capped by demand, so the trade is never fully available. Say that too.

**Country leaks.** Flag any country with spend above the target cost per conversion and zero conversions. Roll the long tail into one line with a total.

---

## Step 5: Landing page alignment

The hypothesis to test: keywords are being sent to broad pages when a more specific page exists, or when none exists at all.

1. **Build a keyword theme taxonomy.** Regex, ordered, most specific first. Derive themes from the account's own keyword list rather than inventing them: pull the top terms by spend, cluster by topic, and write a pattern per cluster. Mark generic themes (the category term itself, pricing, anything that applies everywhere) separately, because they cannot be used to judge a mismatch.
2. **Tag every landing page with themes.** Longest URL path match wins. Ask the user for a page list if the URLs are not self-describing. Their list is more reliable than parsing slugs.
3. **Profile each campaign:** its dominant landing page, that page's share of campaign clicks, and the union of themes across all its pages.
4. **Classify every keyword:**

| Status | Test | Meaning |
|---|---|---|
| Aligned | Specific theme is in the dominant page's themes | Routing is right |
| Partial | Theme is served somewhere in the campaign, but not by the dominant page | Split into its own ad group pointed at that page |
| Mismatch | No page in the campaign covers the theme | Re-route, clone, or build |
| Brand, no product theme | Brand query with no product theme | Routing choice, not a match problem |
| Generic | Only generic themes present | Cannot be judged from the keyword alone |

5. **Make the fix specific.** For every Mismatch, look up the best performing page for that theme, first within the business line, then anywhere in the account. Three fix shapes:
   - Page exists in this business line: "re-route the keyword to X, or clone X into this campaign."
   - Page exists only for another business line: "the nearest page is X, which belongs to Y. This line needs its own."
   - No page anywhere: "build one or pause the keyword." Total the spend sitting on themes with no page. That number is usually the strongest single finding in the analysis.
6. **Find starved pages:** themes where a good page exists but gets a small share of the relevant clicks.

### The honesty check, mandatory

Before presenting alignment as a driver, test whether it actually predicts efficiency. Group by alignment status within bid type and compare cost per conversion.

It often will not. Aligned keywords frequently cost more per conversion than Partial ones, because alignment tracks how a campaign was built rather than how well its keywords convert. Report the result either way. Alignment is a **case-finding tool** that points at specific fixable routes, not a KPI that correlates with cost. Saying so protects every other finding in the document. Overselling one weak correlation is how a good audit loses its audience.

---

## Step 6: Score every keyword

Standard practice: pause a keyword once it has spent 2x to 3x the target cost per conversion with no conversion. Apply it, then layer the overrides.

**Base tiers**, using the top-of-funnel target T for that business line:

Zero conversions:

| Spend | Tier | Action |
|---|---|---|
| >= 3T | 1. Pause now | Pause |
| >= 2T | 2. Pause | Pause |
| >= 1T | 3. Review | Review, then pause |
| < 1T | 4. Watch | Monitor, not actionable on spend alone |

Converting:

| Cost per conversion | Tier | Action |
|---|---|---|
| > 3T | 1. Rein in now | Cut bid, tighten match, or fix the landing page |
| > 2T | 2. Rein in | Cut bid or tighten match |
| > 1T | 3. Hold | No change, above target but within tolerance |
| <= T | 4. Scale | Raise bid or budget |

**Override 1: the downstream CAC rule** (from Step 1c). Applies only where bottom-of-funnel data exists at keyword level. It fires before the base tiers and can rescue a keyword that looks terrible on cost per lead. Always name both numbers in the rationale so the reader can disagree with you.

**Override 2: the brand tier.** Branded keywords that land in a pause tier move to `B. Brand - optimize`, sorted above tier 1. Pausing a brand term hands the click to whoever else is bidding on the name. The fix is cost and routing, not a pause. Keep the original rationale and append why it was moved.

**Override 3: investigate search terms.** For phrase and broad keywords sitting in an actionable tier, check whether the underlying search terms deserve a look before pausing. Fire the flag only when at least one holds:

- Other search terms in the same campaign do convert
- The keyword's intent is commercial or transactional
- The keyword theme is on-target for the buyer

When it fires, replace the action with "Investigate search terms before pausing" and list which signals triggered it. A broad keyword is a container, not a keyword. Pausing the container throws away the terms inside it.

**Every row gets a written rationale** with the actual numbers in it. A tier without a reason does not survive contact with the person who owns the campaign.

---

## Step 7: Search intent (optional)

Check whether a keyword intent source is connected. A Moz connector exposing `DataKeywordMetricsFetch` with `include_intent: true` is one; any source that returns an intent class per keyword works. If one is available, pull intent for every keyword above a spend floor, holding locale and device constant, batched. Cache results to a CSV as you go so an interrupted run resumes instead of restarting. Expect 60% to 75% coverage; label the rest unknown rather than dropping it.

Then report cost per conversion and CAC by intent, per business line and per campaign type.

Read the result carefully rather than assuming. Commercial intent is not automatically good. It frequently has the worst CAC, because "best X tools" style queries are dominated by people reading listicles, not buying. Informational spend share is usually the headline: if a large share of spend sits on informational intent at a CAC well above target, that is a budget reallocation, not a bid adjustment.

If no intent source is connected, skip this step silently and note it in the caveats.

---

## Step 8: Negative keyword mining

From the search terms report, per business line, list every term with spend above the target and zero conversions. Sort by spend. Group into obvious negative themes (jobs, free, tutorial, login, competitor support queries, wrong-vertical traffic) and give each group a total, because a themed negative list gets implemented and a flat list of 400 terms does not.

Separately, list converting search terms that are not already keywords. That is the build list.

---

## Step 9: Deliver

Three files.

**1. Performance workbook.** One tab per view: monthly by business line, campaign detail, country, landing page, search term summary, plus a README tab defining every metric and naming the conversion columns behind it.

**2. Action workbook.** Tabs:

- README, with the rubric, the targets, and every override written out
- Summary, spend by tier and business line
- One master keyword tab per business line: every keyword with cost, clicks, conversions at each stage, cost per conversion, multiple of target, tier, action, rationale, LP alignment, LP fix, intent
- Landing page alignment gaps
- Campaign to landing page map
- One negative terms tab per business line

Use real Excel tables, conditional formatting on the multiple-of-target column, and in-row formulas wrapped in IFERROR so the user can change a target and watch the sheet re-tier. Recalculate before delivering so cached values are not blank.

**3. The written analysis.** One file, three parts:

- Part 1, the decision doc: the verdict in three sentences, account at a glance, the findings, the rubric in force, a ranked top 10 actions with spend at stake and expected effect, where to spend more, where to spend less
- Part 2, reference detail: the monthly tables, the segment cuts, the leak lists, the full intent and alignment distributions
- Part 3, method and caveats: which export files were used, the reconciliation, lag treatment, coverage rates, and every place a number is soft

Do not ship two overlapping documents. One file, ordered by decision first and evidence second.

---

## Guardrails

- **Partial months.** Never compare a partial month to full months without labelling it, and never annualise from one.
- **Lag.** Only caveat the stages the user said lag. Do not hedge a no-lag metric, because that lets a live problem hide behind a disclaimer.
- **Zero-conversion keywords with trivial spend** are not findings. Apply the target-multiple floor before listing anything.
- **Correlation.** Before presenting any segment cut as causal, check the counter-example. If it does not hold, say so and downgrade the claim.
- **Naming conventions are not data.** Anything encoded in a campaign name is a claim from whoever named it, often years ago.
- **Round numbers in prose, keep precision in the sheets.**
- **Give every recommendation a dollar figure.** "Reallocate" is not an action. "Move the $[X] sitting on [theme] terms to [the page that matches that theme], or pause them" is.

---

## Credits and version history

**Author:** Jonathan Berthold (JB), VP of Revenue, Moz
**Created:** September 16, 2026
**Version:** 1.0

Every threshold in this skill is a default, not a law. Targets, tier multiples and the CAC override band all come from the intake in Step 1 and should be reset per account. Nothing here assumes a particular advertiser, vertical, currency or date range.

When you change this skill, add a dated line here so the next person knows what moved and why.