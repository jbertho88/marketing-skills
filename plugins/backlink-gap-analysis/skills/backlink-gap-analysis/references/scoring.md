# Auditable opportunity scoring

Relevance 30, authority 20, traffic_score 15, context 15, spam_clean 10, contact 10.
Pursue >=70; Backlog 50–69; Discard <50. Scores prioritize work; they do not predict ranking gains.

Before these thresholds apply, require evidence_status="Verified link page", actual linking_page
and competitor_destination HTTP(S) URLs, date_verified and verification_source. The verifier must
have observed that source linking to that destination through an API backlink record, export or
page inspection. A guessed homepage is not verified. A homepage can qualify when it is the actual
linking page. Preserve link_type, anchor, last_crawled, PA, placement and n_competitors when available.
Missing evidence yields Verify first even with an imported score. Imported totals remain visible
but cannot qualify as Pursue until all six factors are independently supported.

Every factor needs factor_evidence keyed by its field name and an in-range numeric score.
Use these analyst rubrics consistently and state the inputs/rationale; they are not hidden formulas:

| Factor | Evidence and calibration |
|---|---|
| relevance | Read linking page: 0 unrelated; 10 adjacent; 20 category relevant; 30 directly relevant editorial context. Explain intermediate values. |
| authority | DA and linking-page PA with source/date. 0 unknown; 5 weak observed profile; 10 moderate; 15 strong; 20 exceptional for the observed peer set. Show peer context; DA alone cannot establish page strength. |
| traffic_score | Show traffic or traffic_proxy and traffic_source. 0 unknown; 5 limited measured visibility; 10 meaningful peer visibility; 15 leading peer visibility. Specify units, period and peer comparison. Never infer traffic from DA. |
| context | placement and link_type: 0 unavailable/suspect; 5 profile/bio; 10 relevant curated listing; 15 relevant in-body editorial citation. Explain intermediate calls. |
| spam_clean | Spam Score, propensity and observed page evidence: 0 unresolved/high concern; 5 mixed; 10 no material concern in inspected evidence. Missing Spam Score is unknown, not clean. |
| contact | Actual route_in and evidence: 0 unknown; 5 published general route; 10 relevant named editor or suitable active submission route. Explain intermediate calls. |

Zero with an explicit unknown rationale is valid conservative scoring. Missing factor rationales
are not valid. A positive traffic score without traffic or a named sourced proxy is Verify first.
Record manual execution overrides separately; preserve score_decision and override_reason. Default
execution: Pursue→Pursue now; Backlog/Discard→Hold; Verify first→Verify. Only verified/auditable
rows can be pursued or hygiene quick wins. Each plan row refers to its scorecard opportunity_id.

## Filters and seller candidates

Use spam scores and propensity for triage, not accusations. Inspect actual pages before deciding
whether UGC, shared hosting, shorteners, redirects or syndicated pages are useful. Do not discard
an editorial publisher solely because it uses a hosted platform. The packaged seller classifier
uses sales phrases, domain patterns and propensity; retain its reasons for review. Explicit
spam_solicitation=false overrides should have a written analyst reason.

Normalize hosts before comparing client and seller coverage. Preserve meaningful subdomains and
use explicit client_domain or observed entity aliases. A seller-shaped source with one competitor
hit does not establish payment; broad or client hits suggest possible solicitation only. Do not
claim PBN ownership from backlink patterns. Keep suspect rows in raw tabs and quarantine them
from execution, with counts in the appendix. Never recommend purchased placements or a disavow
solely from this analysis.

## Anchors and asset patterns

Classify brand, exact match, partial match, URL and generic anchors. Compare descriptive sampled
distributions across comparable page types and queries with source, date, numerator, denominator
and sample limits. Anchor-level domain counts can overlap: do not sum them into unique domains.
There is no universal healthy/safe exact-match percentage. Outliers invite inspection, not a
conclusion of manipulation or an outreach anchor target.

Studies, free tools, guides and resources can suggest replicable asset strategies when actual
linking pages show why they were cited. Date clustering is provider observation, not proof of a
campaign's start/end. Earn citations to the natural asset; track its internal support to commercial
pages separately. Product claims used in pitches must reference approved proof points.
