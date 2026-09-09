# Methodology: how each metric is defined

The analysis uses only the four exported columns (Prompt, AI Model Response,
Brand Terms Mentioned, and the "<Brand> Brand Rank" column) plus optional topics.
Keep these definitions consistent so numbers are comparable run to run.

## Output package

- Executive summary: selective, leadership-oriented, and intentionally short.
- Detailed report: the full strategic analysis with topic, model, response, and
  citation reads.
- Excel workbook: the operational command center for action planning, QA, and
  owner-level execution tracking.
- CSV exports: evidence files for prompt-level rows and cited-page rows.
- Do not add unsupported market claims beyond what the provided exports show
  unless the user explicitly asks for extra analysis.

## Source of truth

- Rank comes only from the `<Brand> Brand Rank` column. Lower is better (1 is the
  top slot). A blank rank means the brand was not mentioned in that response.
- Do not infer rank from the order of `Brand Terms Mentioned`. That column is a
  presence list, not a ranking.
- Each brand is counted at most once per prompt.

## Core metrics

- Visibility rate = prompts where the brand is mentioned / total prompts.
- Average rank = mean rank across prompts where the brand appears, so absences do
  not drag it down. Read it next to visibility rate, never alone.
- Rank distribution = how many prompts land at rank 1, 2, 3, 4+.
- Share of voice = a brand's appearances / total brand appearances across the
  field, as a percent. The brand's share versus the leader's is the cleanest
  competitive read, reported as `leader` and `leader_gap_pts`.
- Head-to-head (per competitor): `co_mentioned` (both present), `we_win_slot` (we
  present, they absent), `we_lose_slot` (they present, we absent), and their total
  mentions. A rival with high mentions and a high `we_lose_slot` is the benchmark
  to beat.

## Topics

The engine accepts optional topics; the skill workflow requires a user-confirmed
topic set for final reporting. Prompts are matched to supplied topics by
stemmed token overlap (so "citation" matches "citations"). If not, the engine
auto-groups the prompts: it takes the distinctive terms across the prompt set,
drops the category umbrella terms (those in a large share of prompts), and labels
each cluster with its most common two-word phrase (listing management, rank
tracking, noise cancelling). A prompt can map to more than one topic. Per topic
it reports prompts, visibility rate, average rank, and a weak-or-absent count.

## Strengths and gaps

- Strengths: prompts where the brand is present, sorted best rank first.
- Weak-present: prompts where it appears at rank 3 or lower.
- Lost slots: prompts where it is absent but a competitor is present. Contested
  queries it is losing.
- No-brand: prompts where it is absent and no competitor was named either.
  Usually informational; not necessarily worth chasing.

## Cross-model (2+ files)

- Anchor wins: prompts where the brand ranks 1 or 2 in every model. Observed snapshot strengths, not proof of durability.
- Inconsistent: present in some models, absent in others. Candidates for investigation; presence in one model does not prove a
  particular winning asset or an easier fix.
- Systemic gaps: absent in every model. Require diagnosis before deciding to refresh, create, or pursue third-party work.

## Recommendation layer

Built on top of the metrics; it never changes them. A prompt is flagged when any
of these hold: the brand is absent in a model, ranks 3 or lower, is inconsistent
across models, sits in a topic with under 50% visibility, is losing to the
category leader, or is a near-duplicate of another tracked prompt. Anchor wins
are also emitted as Defend entries so the action matrix is complete.

Each recommendation carries: topics, intent, funnel stage, per-model ranks and
status (strong = rank 1 to 2, weak_present = 3+, absent, not_tracked), competitor
winners, one primary gap type, reason codes, one fix type, a plain recommended
action, a priority score, confidence, effort, and an action bucket.

Intent types: head_term, comparison, use_case, persona, feature_attribute,
pricing, enterprise, local_business, informational, support_or_how_to. Funnel
stage follows intent (comparison and pricing are decision; use_case, persona,
feature_attribute, local_business are consideration; head_term and informational
are awareness; support_or_how_to is post_purchase).

Gap types, in precedence order: tracking_cleanup_candidate (near-duplicate),
no_recommendation_surface (no brand anywhere, informational),
likely_product_fit_question, cross_model_inclusion_gap (present somewhere,
absent elsewhere), lost_slot / systemic_absence (absent while rivals present;
systemic when absent in every model), present_but_buried (rank 3+),
weak_topic_coverage.

Reason codes: category_leader_preferred, competitor_preferred,
attribute_association_gap, product_fit_unclear, pricing_positioning_gap,
enterprise_positioning_gap, use_case_positioning_gap,
brand_present_but_not_primary, no_brand_surface,
duplicate_or_near_duplicate_prompt, unclear_needs_manual_review.

Fix types and their effort: defend_existing_strength (low),
refresh_existing_page (low), prompt_tracking_cleanup (low), manual_review (low),
comparison_content (medium), use_case_page (medium), feature_or_attribute_page
(medium), pricing_content (medium), vertical_or_segment_page (medium),
product_positioning_review (high). Buckets: Defend (defend_existing_strength),
Reclaim (refresh_existing_page), Build (the new-content fixes), Verify
(product_positioning_review, manual_review), Retire (prompt_tracking_cleanup).

## Priority scoring (0 to 100)

Points: 20 for commercial or comparison intent; 20 for priority-topic fit,
awarded only when the user supplied topics (auto-grouped runs skip this factor
and the remaining components are rescaled so scores stay on 0 to 100); up to 20
for cross-model gap size (share of models where the brand is absent while it
ranks elsewhere, halved if its best rank is 3+); 15 for rank proximity (rank 3
earns 15, rank 4+ earns 10, absent-here-but-present-elsewhere earns 8); 15 for
competitor threat (category leader present) or 8 (any competitor); 10 for fit
confidence (high 10, medium 5, low 0). Penalties: minus 15 when product fit is
unclear, minus 15 when no brand appears in any model. Scores floor at 0 and cap
at 100. Confidence is high when the brand already ranks 1 to 2 somewhere or sits
at rank 3, low when fit is unclear or no brand surfaces, else medium. Treat the
score as triage, not truth; the agent sanity-checks the top items.

## Near-duplicate prompts

Two prompts are near-duplicates when their stemmed token sets overlap at Jaccard
0.8 or higher. The threshold is deliberately strict: it catches true phrasing
variants ("best local seo audit tools" vs "local seo audit tools") while keeping
distinct intents that share vocabulary ("bulk listing management" vs "best
listing management") apart. The longer prompt is flagged with duplicate_of
pointing at the shorter canonical one and routed to the Retire bucket. The agent
still sanity-checks flags before recommending consolidation.

## Universal by design

Nothing in the pipeline is specific to an industry. Intent classification uses
structural patterns (question openers, "vs", "for X", "with X", superlatives,
price markers) rather than product vocabularies; topics are clustered from the
tracked prompts themselves; duplicates are token overlap; and the recommendation
rules operate on ranks, presence, and intent only. The same code handles
headphones, local SEO software, keyboards, CRMs, or any other category with no
configuration. On small prompt sets (under about 20), auto-grouped topics fall
back to thin single-prompt clusters so coverage stays populated; treat those
reads as light.

## Category-agnostic by design

Nothing in the analysis is specific to a product category. Attributes are not
extracted from a fixed lexicon, and there is no category detection. The topics
come from the prompts themselves, so the same code handles headphones, local SEO
software, keyboards, or anything else with no configuration.

## Accuracy: data-bounded claims

The export shows what AI answers said, not what exists. The report must never
claim a product, feature, or competitor "does not exist." State absence as
absence in the data ("not surfaced in any analyzed response"), and when a gap
might be a real product gap, recommend verifying rather than asserting it.

## Citation analysis module

Citation analysis is optional and runs only when model-specific citation export
CSVs are provided. Those files use these fields: `Page` (or legacy `Pages`), `Cited in Prompts`,
`Your brand mentioned`, `PA Score`, `Spam Score`, and `Linking Pages`.

### URL normalization and deduplication

- Normalize each URL by lowercasing scheme and hostname, removing fragments, and
  removing common tracking parameters such as `utm_*`, `gclid`, `fbclid`,
  `mc_cid`, and `mc_eid`.
- Preserve the raw URL for QA.
- Create both `canonical_url` and a softer `page_family_key`.
- Deduplicate primarily on `canonical_url`.
- Gemini can overcount fragment links to the same page, so duplicate rows within
  the same model collapse to one canonical page. The model-level deduped prompt
  count uses `max(Cited in Prompts)` to avoid fragment inflation, while the raw
  summed count is preserved separately for QA.

### Citation opportunity logic

- `brand_mentioned_status` rolls up to `Yes`, `No`, `Mixed`, or `Unknown`.
- `No` receives a high legacy engine score, but is only a verification
  candidate until the export field meaning and source/answer evidence are checked.
- Cross-model no-brand pages are recurring sources in the observed snapshot.
  Relevance, source quality and verified brand context determine actionability.
- Owned cited pages are defense assets, not external outreach priorities.
- High-spam pages are quality risks and should not be prioritized just because
  they are cited.

### Citation opportunity score

The citation opportunity score runs 0 to 100 and blends:

- brand absence or mixed status
- model breadth
- deduped cited-prompt count
- linking pages
- PA Score
- Spam Score
- page type bonus

The score is intentionally constrained so raw link counts cannot dominate the
whole decision. A heavily linked page that already mentions the brand should not
automatically outrank a cross-model no-brand inclusion gap.

### Citation outputs

When enabled, the citation module adds:

- page-level opportunities
- domain-level opportunities
- cross-model citation overlap views
- model-level citation trends
- citation data quality warnings
- citation-oriented strategic plays

Treat this layer as influence mapping, not just an outreach list.

## Optional business scoring

See [Business priority](business-priority.md) for the separate prompt-value and
citation-value supplement, evidence requirements, formulas and missing-data rules.
It does not replace the engine scores above.
