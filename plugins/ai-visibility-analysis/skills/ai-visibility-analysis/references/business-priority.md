# Business priority supplement, version 1

Read this reference when the user wants prompt selection scoring, citation value,
organic-search enrichment, or the Moz launch blog workflow. These are custom
planning heuristics, not official Moz metrics, model ranking factors, or validated
predictions of revenue. Keep the existing engine scores under their original names.

## Prompt taxonomy and review

Keep three independent fields. Never substitute one for another:

- Topic: the subject, such as rank tracking.
- Search intent: informational (learn), commercial (evaluate), transactional
  (take an action), navigational (find a named destination). Use one primary
  intent and an optional secondary intent. Pricing research is often commercial;
  it is not automatically transactional. Record uncertain classifications for review.
- Prompt format: definition/explanation, how-to/troubleshooting,
  recommendation/shortlist, comparison/alternatives, use-case/persona,
  feature/constraint, price/value, or brand/destination. Allow multiple formats.
  These are practical working categories, not a universal GEO taxonomy.
  GEO means generative engine optimization.

The legacy engine's `intent` field mixes these concepts. Preserve it and add the
new fields in the supplement. Suggest labels from the actual prompts, explain
borderline cases, and let the user edit them. A brand-free informational response
can still be useful authority tracking; low brand presence is not a reason by
itself to delete a prompt. Never improve a score by quietly removing losing prompts.

## Prompt value, 0 to 100

Ask for audience, offer, objective, and priority topics. Use existing answers.
Rate each factor 0 to 5, with a short evidence note:

- Relevance R: 0 unrelated; 1 peripheral; 2 adjacent; 3 useful category fit;
  4 direct fit; 5 core audience and offer.
- Decision value D: 0 no identifiable role; 1 remote curiosity; 2 early learning;
  3 problem/solution evaluation; 4 active shortlist; 5 pivotal decision or action
  for the stated objective. Relevant informational prompts can score highly.
- Customer evidence E: 0 explicitly unsupported hypothesis; 1 internal idea;
  2 one customer signal; 3 repeated customer signals; 4 corroboration across
  sales/support/search research; 5 repeatedly observed decision-driving need.
  If evidence was not supplied, leave it blank, not zero. Keyword search volume
  is contextual evidence, never an estimate of AI prompt volume.

P = 100 * (0.50 R/5 + 0.30 D/5 + 0.20 E/5).
When E is unknown, divide the available weighted sum by 0.80; mark provisional
and report 80% component coverage. R and D are required. Zero relevance gates
the score to zero. Suggested bands: 70+ core candidate, 40-69 supporting
candidate, below 40 review. Bands do not automatically approve or retire prompts.

Optional business-weighted visibility = 100 * sum(P for present prompts) /
sum(P for all evaluated prompts). Report per model on the same matched cohort,
alongside unweighted visibility and its numerator/denominator. Zero total weight
means not calculable. Freeze weights and retain baseline prompt membership when
comparing snapshots; report newly added/removed prompts separately.

## Citation evidence before recommendations

Track source-page brand presence and AI-response brand presence independently,
each as Yes/No/Unknown, with source URL, response/prompt ID, and review date.
The export's `Your brand mentioned` field must retain its raw value and must not
be assumed to prove either condition without verified field semantics. Inspect
the page and linked response where possible. If unavailable, route to Verify.

Classify the source by inspecting it: owned product/help page, editorial
listicle/review, comparison, tutorial, research/data, forum/community,
retailer/directory, video/social, competitor-owned, or unknown. URL-based guesses
are provisional. Distinguish the publisher type from the content format.

- Missing from source and answer: assess editorial fit, then propose an inclusion
  pitch supported by verifiable product information.
- Present on source but absent from answer: inspect the cited passage and prompt
  fit. Thin context is a hypothesis, not a proven cause. Correct stale facts and
  improve relevant evidence on owned and third-party pages where appropriate.
- Present in answer without owned citation: retain the mention; review whether
  an owned resource would serve the reader. It is not automatically a failure.
- Owned citation: refresh/defend the asset. Do not send external outreach.
- Competitor-owned citation: analyze the competing asset; do not default to an
  inclusion pitch. Community sources need relevant participation, not link drops.

No outreach is sent by running the analysis. Citation, backlink, and brand
mention are separate outcomes. Updates cannot guarantee future AI inclusion.

## Optional citation value, 0 to 100

For each canonical page, collect relevance R (0-5), targeted prompt coverage C
(0-1), observed model breadth B (0-1), evidence quality Q (0-5), and optional
organic reach index T (0-1). Q: 0 demonstrably unreliable; 1 weak/unverifiable;
2 partially supported; 3 attributable and reasonably current; 4 strong primary
evidence; 5 unusually complete, current, transparent evidence. Missing Q is unknown.
Page Authority and Spam Score help review; neither proves truth or AI influence.

C = distinct targeted prompt-model pairs citing the page / all evaluated
targeted prompt-model pairs. Deduplicate each pair. B = models citing this page /
models with comparable citation exports. This modest breadth bonus intentionally
favors recurrence across models; it is partly correlated with C.

Use actual prompt-to-URL links for targeted coverage. Aggregate `Cited in Prompts`
counts cannot be assigned to particular high-value prompts. If only aggregates
exist, leave C blank and report that limitation; retain original counts by model.
If the export is confirmed to cover only the target cohort, deduped model counts
can support an explicitly labeled aggregate estimate, not exact prompt mapping.

V = 100 * (0.40 R/5 + 0.30 C + 0.10 B + 0.10 Q/5 + 0.10 T).
Renormalize over available components, show component coverage, and label partial
scores provisional. R is required and zero R gates V to zero. Compare pages with
equivalent data coverage; do not let missing components silently change rankings.

Optional general action priority A = V * G/5, where verified gap G is 0 (no
relevant improvement), 1 (minor update), 2 (useful enhancement), 3 (material
context/factual gap), 4 (strong inclusion opportunity), or 5 (critical,
well-supported omission or misleading claim). Unknown gap means A is blank.
An absence alone does not establish G=5. Keep effort and confidence as separate
columns. Route owned pages to refresh/defend regardless of score.

## Organic reach enrichment

### Optional live Moz MCP workflow

Offer this step when the user has a Moz API subscription and an enabled,
authenticated Moz MCP connection. If they already requested live enrichment,
proceed within that scope without asking again. Otherwise offer it as an optional
addition to the export-only analysis. A request to edit this skill is not a
request to run enrichment. Do not require a subscription for the base analysis.

1. **Discover capabilities.** Inspect the connected Moz tools and their current
   schemas. The verified tool `DataSiteRankingKeywordList` supports exact-page
   queries with `target_query.scope = "url"`, a URL in `target_query.query`, and
   a supported `target_query.locale`. It returns top-50 ranking keywords with
   rank and monthly volume. Tool namespace prefixes vary by host; discover the
   available name rather than hardcoding the prefix. Do not substitute link
   metrics, keyword suggestions, ranking-keyword counts, or domain totals.
2. **Set the lookup scope.** Use the user's target market and requested page
   shortlist. The schema checked September 7, 2026 supports en-US, en-GB, en-CA,
   and en-AU; recheck at runtime. Ask for the market if it cannot be inferred
   from the analysis brief, never from the assistant's location. Unsupported
   markets should use a compatible export or skip reach enrichment. This tool
   exposes no device or historical snapshot selector; record those as unspecified
   unless the response documents them. Do not pretend to align historical data
   or a device setting the endpoint cannot select.
3. **Bound usage.** Follow any user-specified limits. Otherwise start with five
   relevant canonical citation URLs, up to two result pages of 50 keywords per
   URL (at most ten ranking-list calls and 500 returned rows). State this scope
   before starting. This is a collection limit, not a claim about billable units.
   If available, use `QuotaLookup` for the relevant data quota, currently
   `api.limits.data.rows`, and inspect remaining allowance and overage settings.
   Do not infer free usage from an active subscription. Existing authorization
   covers the stated bounded run; seek an additional budget decision only if
   completion would exceed it or incur unapproved overages. If quota/cost cannot
   be established, disclose that uncertainty before opting into paid lookups.
4. **Fetch and retain evidence.** Query each canonical URL at URL scope, using
   `options.sort = "volume"` when available. Use `page.limit` and `page.n` per
   the live schema and returned pagination information. Stop at exhaustion or
   the collection limit. Cache by URL/locale/retrieval date so citations shared
   across models are fetched once. Save raw responses without credentials and
   normalize the actual returned keyword, rank and volume fields. Do not invent
   response field names. Record truncation and pagination state explicitly.
5. **Estimate organic reach.** Apply the formula below to unique returned
   keyword rows, using a documented CTR curve or explicitly labeled scenario
   assumptions. If CTR assumptions are missing, deliver the ranking data first
   and identify what is needed for the estimate. Use low/base/high volume values
   if returned; do not silently treat a volume range as an exact count. Even a
   fully paginated response covers Moz's indexed top-50 rankings, not all page
   traffic. Label estimates as based on returned ranking keywords; flag capped
   result sets as partial coverage. A zero-row result is no indexed evidence,
   not proof of zero visits.
6. **Join and score.** Save `moz-ranking-keywords.csv` with URL, keyword, rank,
   volume inputs, locale, retrieval time, and provenance; save
   `citation-organic-reach.csv` with URL, low/base/high estimates, CTR source,
   keyword count, completeness, and error/missing-data status. Normalize the
   base estimate into T using the formula below, join by canonical URL to the
   reviewed citation sidecar, then run the existing business scoring helper.
   Keep different coverage levels visible in rankings. Live ranking data does
   not fill the missing prompt-to-citation mapping or verify brand context.
7. **Fall back gracefully.** If authentication, endpoint access, quota, supported
   locale, or necessary fields are unavailable, finish the base analysis and
   accept a Moz exact-page ranking-keyword CSV instead. Report the specific
   limitation. Respect rate-limit retry guidance and retry a transient failure
   at most once within the collection budget; stop on authentication/quota
   failures rather than looping. Do not ask users to paste API secrets into chat.

This is an assistant-orchestrated MCP step, not a new feature of the bundled
Python engines. Report whether live enrichment ran, its collection limits,
successful and failed URL counts, and where the evidence files are saved.
Call the result **modeled organic-search reach**, including when all ranking
inputs were fetched live. It is never measured traffic or AI referral traffic.

Use Moz ranking-keyword data for the exact cited page when available. Verify
current account/tool capabilities before specifying UI controls or API calls.
Record canonical and raw URL, retrieval date, country, device, engine, keyword,
rank, monthly search volume, volume range if applicable, and the source of the
click-through-rate (CTR) assumptions. Do not treat domain totals as page traffic.

Estimated monthly organic visits = sum(monthly keyword volume * assumed CTR at
that rank), deduped by URL/keyword/market/device/snapshot. Show a low/base/high
scenario when volume or CTR is uncertain. This is modeled organic-search reach,
not observed page traffic, AI referral traffic, incremental visits, or revenue.
Avoid double counting duplicate rows. Search-result features and overlapping
queries limit precision. Missing rankings are missing data, not zero traffic.

T = log(1 + page base estimate) / log(1 + maximum base estimate in the same
comparison cohort), bounded 0-1. If every measured estimate is zero, T=0. Freeze
the normalization cohort/reference maximum for repeat comparisons. Save the raw
estimate so a cohort-relative index is never mistaken for traffic.

## Execution and deliverables

The base engines do not calculate these new business scores or fetch Moz ranking
data. Use the supplied `scripts/score_business_priority.py` on reviewed sidecar
CSV inputs. It computes P, V and A only; weighted visibility and traffic scenarios
must be separately calculated from evidence and verified. Do not invent inputs.

Prompt CSV: `prompt,relevance,decision_value,customer_evidence` plus optional
topic, search_intent, prompt_format, evidence_note and reviewer fields.
Citation CSV: `canonical_url,relevance,targeted_coverage,model_breadth,quality,organic_reach,gap`
plus optional source/answer presence, evidence URLs, snapshot, owner and effort.
Blank optional factors mean unknown. Numeric zero means measured/rated zero.

Run `python scripts/score_business_priority.py prompts reviewed-prompts.csv scored-prompts.csv`
or `python scripts/score_business_priority.py citations reviewed-citations.csv scored-citations.csv`.

Preserve all input fields and score components. Deliver scored CSVs beside the
original report/workbook and link them from the report. When the user requests
integration, add clearly named Business Prompt Scores / Citation Value sheets
and a methodology note using appropriate document/spreadsheet tooling. Existing
report builders do not automatically embed the supplement. Do not promise that
they do. Partial evidence should produce a useful base report plus a specific
missing-data list, not fabricated enriched scores.
