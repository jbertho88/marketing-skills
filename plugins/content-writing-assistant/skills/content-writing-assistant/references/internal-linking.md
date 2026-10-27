# Internal linking from a sitemap crawl

You usually fetched the sitemap already at Step 0.5 (the existing-page check). Reuse those files here, and carry any same-query or partial-overlap pages found there into the cannibalisation notes below.

## 1. Find the sitemap

Try in order and stop at the first that works:
1. `https://<domain>/robots.txt` and read any `Sitemap:` lines
2. `https://<domain>/sitemap.xml`
3. `https://<domain>/sitemap_index.xml`
4. Common CMS paths: `/wp-sitemap.xml` (WordPress core), `/sitemap-index.xml`, `/post-sitemap.xml`, `/page-sitemap.xml`

If the result is a sitemap index, open the child sitemaps that plausibly hold content (posts, pages, services, locations, guides). Fetch child sitemap URLs exactly as listed, query string included: Shopify child sitemaps (`sitemap_pages_1.xml?from=...&to=...`) return nothing without it. Product sitemaps are also worth a look when a brief names products or brands, because they show what the client actually stocks. Skip image, video, tag, author and product-variant sitemaps unless the topic needs them.

If no sitemap is reachable, say so and fall back to: the user supplying a URL list or crawl export, or a `site:<domain> <topic>` web search to find candidate pages. Record which fallback you used.

## 2. Collect and filter

Save the URLs (with `lastmod` if present) to a file. Run:

```bash
python scripts/sitemap_filter.py sitemap.xml [child.xml ...] --terms "primary keyword" "secondary term" ... --top 40
```

The script accepts local XML files (download them with whatever fetch method works in your environment) or a plain text file of URLs, scores each URL by how many topic terms appear in its slug, and drops obvious non-content paths (tags, pagination, feeds, author archives, cart, account). Slug matching is only a shortlist. It misses pages with vague slugs, so also scan the full list by eye for sections like `/services/`, `/practice-areas/`, `/guides/`, `/resources/`.

## 3. Choose links by reading, not by slug

For the shortlist (aim for 10 to 20 candidates), fetch each page and confirm:
- It is live, indexable-looking, and actually about what the slug suggests
- What it is: money page (service, product, location), supporting content, or hub/category
- Its own primary topic, so the anchor describes it accurately

Then select:

**Outbound links (from the new article)**
- Always link to the money page named in the content brief, early and in context
- Link to supporting pages wherever a reader would genuinely want the deeper explanation
- Typical density: about one contextual internal link per 150 to 250 words, with judgement. A link must help the reader at that point
- Anchors: descriptive, varied, 2 to 6 words, matching the target page's topic. Mix partial-match, natural phrase and occasional branded anchors. Never use the same exact-match anchor twice, never "click here"
- Do not link the same URL more than once in the body
- Do not link to pages that compete for the same primary keyword as the new article; flag those as **cannibalisation risk** instead

**Inbound recommendations (to the new article)**
- 3 to 8 existing pages that are topically closest and likely to carry authority (hubs, pillar pages, older popular posts, the money page itself if it has a natural "learn more" spot)
- For each: source URL, suggested anchor, where on the page it fits (section or sentence idea)

## 4. Output format

```
### Outbound internal links
| # | Anchor text | Target URL | Placement (section) | Purpose |

### Inbound link recommendations
| # | Source page | Suggested anchor | Where it fits |

### Notes
- Sitemap source: <url or fallback used>, N URLs found, M shortlisted
- Cannibalisation risks: <urls and why>
- Gaps: <topics the site lacks that this article references, candidate future pages>
```

In the article Markdown itself, place the links inline as `[anchor](url)` so the draft is ready to paste.
