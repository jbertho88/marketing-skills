# Page benchmark evidence

Use exact supplied ranking URLs and URL-scope metrics. Attach keyword, locale, date and SERP
source. Group each query separately; a cross-query interpretation follows those observations.
Without a live SERP use “Competitive page benchmark” and omit ranking claims.

Record total referring domains, indirect domains and nofollow domains separately. These populations
may overlap. Do not compute total minus indirect minus nofollow as a clean direct-follow count.
If a verified intersection is available, the complement is T - I - N + overlap. Mutual exclusivity
permits overlap=0 only with documented evidence. The builder accepts indirect_nofollow_overlap
or subsets_mutually_exclusive plus composition_evidence and labels the result “Neither indirect
nor nofollow”. This complement is not necessarily the number of domains with any direct-follow
link: one domain can supply several link types. Leave it unknown without matching definitions,
scope and snapshot. A direct-follow link-level count needs its own verified, deduplicated evidence.

Example: total 54, indirect 53, nofollow 21. The exact complement is unknown without overlap.
Do not call the effective bar 54 links, 1 link, or negative 20 links.

Nofollow is a link attribute, not a guarantee that a domain passes no value. Redirect/canonical
relationships do not inherently make links low quality. Inspect the actual source and destination.

Concentration = referring domains to page / referring domains to site, using comparable snapshots.
It is descriptive; it does not prove deliberate promotion or explain why Google ranks the page.
Page concentration, domain strength and templated scale are competing hypotheses. Also assess
intent, content, internal linking and other missing evidence before recommending an acquisition plan.

Empty last_crawled or http_code=0 can mean unavailable Moz coverage. Represent unknown page
counts with null. A crawled URL with zero means zero observed in that provider snapshot, not zero
links anywhere. Moz crawl status is not Google index status.
