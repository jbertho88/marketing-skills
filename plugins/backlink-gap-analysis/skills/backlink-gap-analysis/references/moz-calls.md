# Moz connector — verified call shapes and failure modes

These call shapes were recorded in a prior run. Inspect the currently available tool schema before calling; endpoint behavior may change.
Tool names are prefixed `mcp__moz-mcp-v1-data__`.

## Contents

- [Scope: the parameter that quietly changes every number](#scope)
- [Failure modes worth knowing first](#failure-modes)
- [Domain-level calls](#domain-level-calls)
- [Page-level calls](#page-level-calls)
- [Quota](#quota)
- [Field reference](#field-reference)

---

## Scope

Every `site_query` takes `{"query": "...", "scope": "..."}` where scope is one of `domain`,
`subdomain`, `subfolder`, `url`.

Root-domain and subdomain scope return materially different numbers for the same site — one
measured domain returned 132,068 linking root domains at `domain` scope and 128,307 at
`subdomain`. Neither is wrong; mixing them within one comparison is. **Pick `domain` for all
site-level work and hold it**, and use `url` only for the page-level pivots.

For `url` scope, pass the path with the domain and no protocol —
`torontosurgery.com/surgical/liposuction`. The API normalises and echoes back what it resolved in
`site_query.query`; check that echo when results look wrong, because a redirect or a trailing-slash
variant may have resolved somewhere you did not intend.

---

## Failure modes

These cost the most time when hit cold.

**Intersect breaks above 3 targets.** `DataSiteLinkIntersectFetch` returns
`{"error":"Internal error","data":{}}` with 4 or 5 entries in `is_linking_to`. It succeeds
reliably with 2 or 3. Run competitors in pairs or triples, then merge and de-duplicate by domain,
unioning distinct matched competitor IDs per source; do not sum duplicate pair hits. The error is silent about the cause, so without
knowing this you will waste a cycle debugging the payload.

**`DataSiteLinkList` payloads are enormous.** Each link record embeds full `source_site_metrics`
*and* `target_site_metrics` — roughly 60 KB for just 15 links, which will overflow a tool result
and get spilled to a file. Always pass a small `offset.limit` (10–25), and project only the fields
you need:

```python
for l in data["links"]:
    s = l["source_site_metrics"]
    row = {
        "root_domain": s["root_domain"],
        "page":        s["page"],
        "da":          s["domain_authority"],
        "pa":          s["page_authority"],
        "spam":        s["spam_score"],
        "anchor":      l["anchor_text"],
        "first_seen":  l["date_first_seen"],
        "nofollow":    l["nofollow"],
    }
```

**`DataSiteLinkList`'s `options.scope: "domain"` does not de-duplicate.** Despite the description
suggesting one link per source domain, a single call returned 15 links all from the same root
domain. De-duplicate client-side, or pass `subdomains_limited_to_one`. Worth knowing because 15
rows that look like 15 domains can badly overstate a page's reach.

**HTTP status is not a health check.** `http_code` of 429 or 403 in `site_metrics` means the site
rate-limits or blocks Moz's crawler, not that it is down. A `http_code` of 0, 1, or 15 means the
crawl itself failed. Never report a site as broken on this basis; do note it, because a site that
blocks crawlers may have stale metrics.

**Crawl freshness varies wildly per domain.** Within one five-domain competitor set, `last_crawled`
ranged across seven months. A stale competitor understates its own gap. Capture `last_crawled` in
the baseline table and mention it when a competitor's data is months old.

**Spam Score of `-1`** means not scored, not clean. Treat it as unknown and lean on other signals.

---

## Domain-level calls

### Baseline metrics for several domains at once

```json
{
  "tool": "DataSiteMetricsFetchMultiple",
  "site_queries": [
    {"query": "client.com",     "scope": "domain"},
    {"query": "competitor.com", "scope": "domain"}
  ]
}
```

Returns `results_by_site[].site_metrics`. The fields that matter: `domain_authority`,
`root_domains_to_root_domain` (referring domains), `spam_score`,
`deleted_root_domains_to_root_domain`, `last_crawled`, `link_propensity`.

A high `deleted_root_domains_to_root_domain` relative to the total signals a decaying profile —
one competitor showed 396 deleted of 983 total, which is a genuine finding about their trajectory.

### Ranking keywords (the competitor admission test)

```json
{
  "tool": "DataSiteRankingKeywordList",
  "target_query": {"query": "client.com", "scope": "domain", "locale": "en-CA"},
  "options": {"sort": "volume"},
  "page": {"limit": 25, "n": 0}
}
```

`locale` is required and only accepts `en-US`, `en-GB`, `en-CA`, `en-AU`. Note the pagination key
is `page` with `{limit, n}` — not the `offset` object the link endpoints use.

Returns top-50 rankings only. A competitor ranking below 50 for everything simply returns few rows,
which is itself a signal.

### Link intersect

```json
{
  "tool": "DataSiteLinkIntersectFetch",
  "is_linking_to": [
    {"query": "competitor-a.com", "scope": "domain"},
    {"query": "competitor-b.com", "scope": "domain"},
    {"query": "competitor-c.com", "scope": "domain"}
  ],
  "not_linking_to": [{"query": "client.com", "scope": "domain"}],
  "options": {
    "minimum_matching_targets": 2,
    "scope": "domain",
    "sort": "matching_target_count"
  },
  "offset": {"limit": 50}
}
```

`sort` accepts `matching_target_count`, `source_spam_score`, `source_domain_authority`. Use
`matching_target_count` for the working list.

Each result carries `matching_target_indexes` — **zero-based positions into your `is_linking_to`
array**. Use these to attribute each row to specific competitors, and to spot a competitor that
never appears at all, which means it contributed nothing to the intersect and should probably be
dropped from it.

`matching_source_pages` gives the actual linking URLs and their Page Authority. Read these. The
root domain tells you almost nothing; the URL and its path tell you whether it is an editorial
mention, a directory listing, a forum post, or a hacked subdomain.

### Recently gained linking domains (60 days)

```json
{
  "tool": "DataSiteLinkingDomainFilterRecentlyGained",
  "site_query": {"query": "competitor.com", "scope": "domain"},
  "offset": {"limit": 25, "token": null}
}
```

Note `offset` requires **both** `limit` and `token` here — pass `"token": null` for the first page.
Optional `options: {"begin_date": ..., "end_date": ...}`.

Returns `gained_linking_domains[]` with `site_metrics`, `date_gained`, `targeted_pages`.

Watch `link_propensity` on the source. Values in the hundreds are a link farm: one source had a
propensity of 463 with 29,173 outbound root domains from 63 pages crawled. Nothing legitimate
looks like that.

### Linking domains (strongest links)

```json
{
  "tool": "DataSiteLinkingDomainList",
  "site_query": {"query": "competitor.com", "scope": "domain"},
  "options": {"filters": ["external", "follow"], "sort": "source_domain_authority"},
  "offset": {"limit": 20}
}
```

Filters: `external`, `follow`, `nofollow`, `deleted`, `not_deleted`.

Even with `follow` filtering, check `targeted_pages` against `targeted_nofollow_pages` per row —
they are frequently near-identical, meaning almost every link from that source is nofollow. One
major platform showed 1,880 targeted pages of which 1,851 were nofollow. The DA sort hides this
entirely.

---

## Page-level calls

### Top pages by referring domains

```json
{
  "tool": "DataSiteTopPageList",
  "site_query": {"query": "competitor.com", "scope": "domain"},
  "options": {"filter": "status_200", "sort": "root_domains_to_page"},
  "offset": {"limit": 15}
}
```

`sort` accepts `page_authority`, `root_domains_to_page`, `external_pages_to_page`. **Prefer
`root_domains_to_page`** — Page Authority correlates with site-wide authority and floats the
homepage and navigation-heavy pages to the top, while referring-domain count surfaces the pages
that genuinely attracted independent links.

Skip the homepage row, which is always first and always uninteresting. Read the `title` of
everything below it: link-bait pages name themselves.

### Links to a specific page

```json
{
  "tool": "DataSiteLinkList",
  "site_query": {"query": "competitor.com/some/page", "scope": "url"},
  "options": {"filters": ["external", "follow"], "sort": "source_domain_authority"},
  "offset": {"limit": 15}
}
```

Mind the payload size and the non-de-duplication noted above.

`date_first_seen` clusters are informative: fifteen links all first seen in one calendar year means
a campaign that ran and stopped, not an evergreen asset. That changes whether replicating it is
worth the cost.

### Page-level intersect

Same call as the domain intersect with `scope: "url"` on every target:

```json
{
  "tool": "DataSiteLinkIntersectFetch",
  "is_linking_to": [
    {"query": "competitor-a.com/service-page", "scope": "url"},
    {"query": "competitor-b.com/service-page", "scope": "url"}
  ],
  "not_linking_to": [{"query": "client.com/our-equivalent-page", "scope": "url"}],
  "options": {"minimum_matching_targets": 1, "scope": "domain", "sort": "source_domain_authority"},
  "offset": {"limit": 20}
}
```

`minimum_matching_targets: 1` is correct here. Page-level link counts are one to two orders of
magnitude smaller than domain-level, so requiring 2+ returns almost nothing. Single-digit result
counts are the normal, useful output — not a failed run.

### Anchor text for a page

```json
{
  "tool": "DataSiteAnchorTextList",
  "site_query": {"query": "competitor.com/some/page", "scope": "url"},
  "offset": {"limit": 20}
}
```

Returns `anchor_texts[]` with `text`, `external_root_domains`, `external_pages`. Weight by
`external_root_domains`, not `external_pages` — one site linking forty times is one opinion.

To find who used one specific anchor, `DataSiteLinkFilterAnchorText` takes the same `site_query`
plus `anchor_text`.

---

## Quota

```json
{"tool": "QuotaLookup", "path": "api.limits.data.rows"}
```

Returns `allotted`, `used`, `reset`, `overage`. A full analysis across five competitors with both
domain and page pivots costs on the order of a thousand rows against a typical allotment in the
millions, so quota is rarely the binding constraint — but check it before a large batch run, and
mention the cost if the user is running many clients.

---

## Field reference

Names that are easy to confuse:

| Field | Means |
|---|---|
| `root_domains_to_root_domain` | Referring domains to the whole site — the headline number |
| `root_domains_to_page` | Referring domains to this specific page — the page-level equivalent |
| `deleted_root_domains_to_root_domain` | Referring domains that have gone away; high ratio = decay |
| `link_propensity` | How readily the source links out; hundreds = link farm |
| `pages_to_root_domain` | Individual linking pages, not domains. Much larger; do not confuse |
| `external_pages_to_root_domain` | External linking pages only |
| `page_authority` / `domain_authority` | 1–100 log scale; a 10-point gap near the top is far larger than near the bottom |
| `spam_score` | 0–100 percentage-of-similar-sites-penalised. `-1` = not scored |

## Report contract

Use the v2 findings schema and coverage rules in SKILL.md. Track expected/completed entities,
request limits, cursor exhaustion, errors and actual sampled date bounds. Successful calls for
one competitor do not mark the entire section complete. Resolve recently gained domains into
verified source/destination backlink records before scoring; a source homepage is not a fallback
linking URL. Quota estimates need the actual current allowance and agreed limits.
