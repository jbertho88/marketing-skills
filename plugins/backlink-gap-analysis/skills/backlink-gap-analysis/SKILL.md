---
name: backlink-gap-analysis
description: "Run a backlink gap analysis end to end, starting from the SERP: benchmark how many domains link to each ranking PAGE, find the domains and pages linking to competitors but not the client, work out what earns those links, score every opportunity, and deliver a workbook plus a sequenced outreach plan. Use whenever someone asks for a backlink gap analysis, link gap, link intersect, competitor backlink analysis, link prospecting, or 'who links to my competitors but not us'; hands over a keyword plus the URLs ranking for it; asks what it takes to rank on a SERP, how many links a competitor's page has, what earns links in a niche, which competitor pages pull the most links, or about anchor text profiles; gives a client domain plus competitors and wants link opportunities or a scored target list; or asks what to do next after a gap analysis: the outreach plan, which listicles to target, what assets to build. Runs live on the Moz connector, and can ingest a CSV export from any backlink tool with the right columns."
---

# Backlink gap analysis

Created by: Jonathan Berthold, VP Revenue of Moz

Last updated: September 9, 2026

Deliver a competitive backlink diagnosis and an executable earned-link plan. Start with exact
ranking pages when the user supplies a live, location-specific SERP. Without that evidence, run
a competitive page/domain benchmark and label the limitation. Link metrics suggest hypotheses;
they do not establish ranking causes or guarantee results.

## Inputs and quota

Collect client domain and target URL, competitor domains, keyword/query clusters, market, and
optional live SERP URLs with positions, source, date and locale. Keep keywords separate in the
benchmark. Moz's ranking index is not a supplied live SERP. Record `live_serp.supplied=false`
when absent; do not invent positions.

Ask optionally for approved differentiators, product facts and customer examples. Store only
approved claims in `approved_proof_points` with id, claim, source and approved_by. Reference IDs
in action rows. Backlink data does not prove product superiority, directory counts, sync times or
customer outcomes. Without approved facts, write “Insert verified client differentiation here”.

For live Moz calls read [references/moz-calls.md](references/moz-calls.md); for supplied exports
read [references/csv-ingest.md](references/csv-ingest.md). Before billable acquisition inspect
QuotaLookup, confirm the user's actual remaining allowance and agree the scope. Do not hardcode
plan prices or monthly allowances. The former estimate_quota.py references have been removed:
there is no packaged estimator. Estimate endpoint limits and pagination transparently; billing
may differ from visible rows. Recheck quota during constrained runs. No acquisition calls are
needed when only editing this skill or building reports from supplied data.

## Coverage contract

Attempt each applicable stage. Section `pulled` means a request was made, not that every entity
was covered. For link_gap, recently_earned, strongest_links and competitor_top_pages, declare
`expected`, `completed`, and `omitted` (entity → specific reason). Expected includes every declared
competitor, even intentionally excluded competitors. Add the client when sampled in that stage.
An entity is completed only after its agreed scope was processed; an empty successful response
can count, an error or quota cutoff cannot. Record date bounds, limits, pages/cursors and source
in coverage notes. Use `partial_reason` when a time window or pagination is incomplete.

All required sections need coverage entries. Page-oriented stages should additionally track exact
URLs/queries in expected/completed/omitted; distinguish unknown, no results and not requested.
The builder fails incomplete competitor coverage by default. A deliberate partial report requires
`--allow-partial`, a top-level `partial_reason`, and explicit entity omission reasons. It must
display PARTIAL, entity fractions and limitations; never say every competitor was analyzed.

## Stages

1. **Benchmark pages.** Pull URL-scope PA, referring domains, links, indirect/nofollow counts,
   domain DA and referring domains. Record crawl status and keyword. Read
   [references/serp-benchmark.md](references/serp-benchmark.md). Unknown index coverage is null,
   not zero. Label page concentration, domain strength or templated scale as hypotheses.
2. **Choose competitors.** Keep SERP evidence separate from the mining set. Explain exclusions,
   adjacent markets and query clusters. Keyword overlap can challenge a domain-only set; it is
   not a universal pass/fail cutoff. Spam Score is a triage signal, not proof of misconduct.
3. **Intersect.** Use minimum_matching_targets=1. Pair requests when endpoint limits require it;
   merge by normalized source and union distinct matched competitors, never sum duplicate hits.
   Run page-level intersect where exact competing URLs exist. Resolve linking pages.
4. **Recently earned.** Sample each expected entity over the agreed window; paginate when needed
   and record actual earliest/latest dates and truncation. First seen means first observed by
   the provider, not necessarily publication or acquisition date. Resolve source linking URL,
   competitor destination, anchor and follow status before scoring. Unresolved rows remain
   visible as Domain only / Needs verification / Link unavailable and Decision=Verify first.
5. **Strongest links.** Inspect each expected competitor's strongest referring sources and
   actual linking pages. Record achievability and route in; distinguish editorial, infrastructure,
   self-service, redirects and suspect sources using page evidence rather than domain alone.
6. **Competitor assets.** Inspect most-linked pages and supporting source pages. Identify studies,
   tools, resources or other assets that plausibly earn citations. Do not infer spend from dates.
7. **Page gaps and anchors.** Compare exact target pages. Show descriptive anchor distributions,
   sample size, units and date. Do not add overlapping referring-domain counts across anchors
   and call that unique domains. No universal healthy exact-match target; no dictated outreach anchors.
8. **Score evidence.** Apply [references/scoring.md](references/scoring.md). Preserve the actual
   linking URL, destination, PA, anchor, link attributes, crawl/verification date, matched competitor
   count, traffic/proxy source, placement, contact route and six factor rationales on the scorecard.
9. **Turn decisions into work.** Give each distinct opportunity a stable opportunity_id. Report
   opportunities and normalized unique domains separately; coordinate multiple publisher URLs as
   one contact relationship where appropriate. Record score_decision, execution_decision and
   override_reason. Every outreach row references a scored opportunity; add hygiene rows to the
   scorecard before planning them. Overrides cannot promote unresolved evidence into outreach.

## Execution and editorial destinations

Use Pursue now, Verify, Hold or Hygiene quick win. Any departure from the score-derived execution
default needs a reason on the scorecard. Omitted Pursue opportunities should be marked Hold with
a reason. The builder derives active rows when no plan is supplied; review angles and routes.
Sequence fast submissions/reclamation, editorial inclusion, then longer research/relationship work.
Never recommend buying placements. Seller detection is heuristic; normalize URL, www, case,
trailing dot and CLIENT(domain) labels before comparison. Keep hosted subdomains distinct.
Use explicit client_domain; do not collapse hosts to the last two labels (co.uk and hosted blogs).
An isolated competitor hit does not prove payment; client hits do not prove solicitation.

Every action and asset distinguishes `earned_link_destination` (what an editor naturally cites)
from `commercial_page_supported` (what the asset supports through relevant internal links).
Research and tools normally earn links to their own URLs; commercial pages can be direct targets
when the editorial context supports that choice. Identify proposed URLs as proposed and record
asset readiness and internal-link implementation. Do not claim a planned asset already exists.

## Build and validate

The packaged [scripts/findings.schema.json](scripts/findings.schema.json) is the JSON contract;
`--print-schema` prints that file. Unknown optional fields are retained. The packaged validator
enforces the schema subset it uses; integrity.py adds coverage, evidence and execution checks.

```bash
python scripts/build_workbook.py --example > findings.json
python scripts/build_workbook.py findings.json --out Client_Backlink_Gap.xlsx
python scripts/build_workbook.py --print-schema
python scripts/test_integrity.py
```

Requires Python 3.10+ and openpyxl. The example is explicitly synthetic and performs no network
calls. Outputs: workbook, markdown brief and normalized `.findings.json`. Summary references are
derived from headers; assertions evaluate the controlled Score/Decision/Summary formulas, write
their cached results, and compare decisions/counts with JSON and markdown. This is not a general
spreadsheet recalculator. `--no-recalc` skips the optional external recalculator but still runs
these assertions. After manual workbook edits, rebuild from updated JSON to refresh static
executive, unique-domain and markdown snapshots. Do not distribute mismatched artifacts.

Lead the report with primary constraint (a qualified hypothesis), confidence and evidence gaps,
opportunity/unique-domain counts, immediate actions, next 60 days, strategic assets and activities
to avoid. Then show benchmark, actions, evidence and appendix. The 30/60/90 block tracks links,
unique domains, placements, links to assets, internal support, non-brand rankings/impressions and
a gap rerun. Assign baseline, owner, data source, review dates and goals from approved inputs;
leave unknowns explicit. Do not invent numeric targets or attribute ranking movement only to links.
