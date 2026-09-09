# Running from CSV exports

The live Moz connector is the spine of this analysis. A CSV export is for two situations: the
connector is unavailable, or you want to widen coverage on a run that has already happened.

Any backlink tool's export works, provided it carries the fields below. Index coverage genuinely
differs between tools, so a second source usually adds rows rather than contradicting the first.
What matters is not which tool the CSV came from but whether the columns you need are actually in
it, filled in, and mean what you think they mean.

## What the export has to contain

Per competitor and for the client:

| Export | What it must carry | Needed for |
|---|---|---|
| Referring domains | One row per referring domain, with an authority score | Stages 1, 2, 4 |
| New links, last 60 days | Date first seen, follow status, deduped to one row per domain | Stage 4 recently earned |
| Backlink gap / link intersect | Domains linking to competitors with a per-competitor count | Stage 3 |
| Top pages by referring domains | Page URL and its referring-domain count | Stage 6 P1 |
| Anchors | Anchor text with referring-domain and page counts | Stage 6 P3 |
| Organic keywords | Top 25 by volume, any source | Stage 2 admission test |

If a tool offers a gap or intersect export that takes the client plus several competitors in one
run, use it: it produces the "they link, you don't" view directly and is the fastest first pass.
Where no such export exists, compute the gap from referring-domain exports (see below).

Two columns are optional and often absent: a trust-style score and a topical trust score, which
map to the workbook's `tf` and `topical_tf`. **Leave them null when your export does not carry
them.** A trust column silently filled with an authority score is worse than an empty one, because
it looks like a second independent signal and is not.

## Column mapping

Header text drifts between tool versions, plan tiers and locales. Match case-insensitively on a
substring, and **fall back to asking rather than guessing** — a mis-mapped authority column
corrupts every score downstream and does so invisibly.

| Canonical field | Header variants seen in the wild |
|---|---|
| `domain` | Domain, Root Domain, Source url, Referring page URL, SourceURL |
| `da` | Domain Authority, DA, Domain Rating, DR, Authority Score, AS |
| `pa` | Page Authority, PA, URL Rating, UR, Page Score |
| `spam` | Spam Score, Toxicity Score |
| `tf` | Trust Flow, TrustFlow |
| `topical_tf` | Topical Trust Flow, TopicalTrustFlow_Value |
| `traffic` | Traffic, Domain traffic, Organic traffic |
| `first_seen` | First seen, date_first_seen, FirstIndexedDate |
| `anchor` | Anchor, Anchor text, anchor_text, AnchorText |
| `nofollow` | Nofollow, NoFollow, FlagNoFollow, Type |
| `linking_page` | Referring page URL, Source url, source page, SourceURL |
| `target_page` | Target URL, Target url, target page, TargetURL |

**Authority scores from different tools are not interchangeable.** They are all 0–100 and they are
all computed differently, so the same domain scores differently depending on where the number came
from. Record which source each number came from, keep them in separate columns, and never average
across them. A volume-style flow metric is not an authority equivalent at all; if an export offers
both a volume flow and a trust flow, the trust one is the quality signal.

## Normalising

Before merging anything:

1. **Strip to root domain** for domain-level work — lowercase, drop protocol, drop `www.`, drop
   trailing slash, keep the public suffix intact (`bbc.co.uk`, not `co.uk`).
2. **Keep the full URL** in a separate column. The path is what tells you whether a row is
   editorial, a directory listing, or a hacked subdomain, and it is the first thing discarded by
   careless normalisation.
3. **De-duplicate by root domain**, keeping the highest-authority row and recording how many
   competitors that domain linked to.
4. **Parse dates to ISO** (`YYYY-MM-DD`). Exports vary by account locale, so check whether
   `03/04/2026` means March or April before assuming.
5. **Normalise nofollow to boolean.** Exports variously use `nofollow`, `NoFollow`, `1`/`0`,
   `TRUE`/`FALSE`, or a `Type` column containing `Nofollow` among other flags.

## Computing the gap from exports

When you have referring-domain exports but no intersect export, compute it directly. Set the
authority and URL header names to whatever your export actually uses:

```python
import pandas as pd

DOMAIN_COL, AUTH_COL, PAGE_COL = "Domain", "Domain Authority", "Referring page URL"

from integrity import normalize_domain as root  # scripts/ on Python path

client = {root(d) for d in pd.read_csv("client_rds.csv")[DOMAIN_COL]}

counts, best = {}, {}
for path in competitor_files:
    df = pd.read_csv(path)
    for d in {root(x) for x in df[DOMAIN_COL]}:        # set() = one vote per competitor
        counts[d] = counts.get(d, 0) + 1
    for _, r in df.iterrows():
        d = root(r[DOMAIN_COL])
        if d not in best or r[AUTH_COL] > best[d]["da"]:
            best[d] = {"da": r[AUTH_COL], "linking_page": r.get(PAGE_COL)}

gap = [
    {"domain": d, "n_competitors": n, **best[d]}
    for d, n in counts.items()
    if d not in client
]
```

The `set()` per competitor file matters: without it a competitor with forty links from one domain
counts as forty, and that domain floats to the top of a list it does not deserve.

Note there is no `n >= 2` filter. A domain linking to only one competitor can still be the most
valuable row in the run; the matching count is a scoring input, not a gate.

## Merging live Moz with CSVs

Run the live Moz analysis as the spine, then left-join CSV data on root domain to fill gaps.
Where the two disagree on whether a link exists, believe the union — index coverage genuinely
differs between tools, and a domain present in one index and absent from the other is usually real
rather than an error.

Record the source per row so a reviewer can tell where a number came from. When two sources both
carry an authority score for a domain, keep both columns rather than picking one; a large
divergence between them is itself a signal worth a second look.

## Evidence and opportunity preservation

The domain-level example above is a discovery seed only, not the scored opportunity set. Preserve
every distinct source URL/destination pair for scoring; do not collapse multiple articles into one
highest-DA row. Carry verified source URL, competitor destination, link attributes, anchor, source
export and verification date. A domain-only export becomes Verify first until source-page evidence
is resolved. Follow findings.schema.json and the per-entity coverage contract in SKILL.md.
