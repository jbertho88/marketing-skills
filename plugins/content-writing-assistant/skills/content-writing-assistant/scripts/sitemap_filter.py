#!/usr/bin/env python3
"""Check for an existing page and shortlist internal-link candidates from sitemap files.

Usage:
  python sitemap_filter.py sitemap.xml [more.xml|urls.txt ...] --terms "primary keyword" "other term" \
      [--slug /blog/brief-slug] [--top 40] [--csv out.csv]

Accepts sitemap XML (urlset or sitemapindex) or plain text files with one URL per line.

Existing-page check (Step 0.5), printed first:
  - --slug: exact match for the brief's planned URL path, plus near matches
  - The FIRST --terms value is treated as the primary keyword: URLs whose path contains
    at least 75% of its words are listed as possible same-query pages
  These are candidates only. Open each one and read its title and H1 before deciding.

Link shortlist (Step 5): scores each URL by how many term tokens appear in its path,
drops non-content paths, and prints a ranked list. If a file is a sitemap index, the
child sitemap URLs are printed so you can fetch them next (keep their query strings).
"""
import argparse
import csv
import re
import sys
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
EXCLUDE = re.compile(
    r"/(tag|tags|category/page|page/\d+|feed|author|wp-json|cart|checkout|account|login|"
    r"search|attachment|amp)(/|$)|\?|\.(jpg|jpeg|png|gif|webp|pdf|svg)$",
    re.I,
)
STOP = {"a", "an", "the", "and", "or", "of", "for", "to", "in", "on", "with", "how", "what", "is", "are", "my", "your"}


def tokens(text):
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t and t not in STOP]


def stem(t):
    for suf in ("ing", "ers", "er", "es", "s"):
        if len(t) > len(suf) + 3 and t.endswith(suf):
            return t[: -len(suf)]
    return t


def norm_path(u):
    p = urlparse(u).path if "://" in u else u
    p = "/" + p.strip("/")
    return re.sub(r"\.(html?|php|aspx?)$", "", p.lower())


def slug_tokens(path):
    last = norm_path(path).rsplit("/", 1)[-1]
    return {stem(t) for t in tokens(last)}


def existing_page_report(all_urls, slug, primary):
    print("== Existing-page check")
    found = False
    if slug:
        target = norm_path(slug)
        exact = [u for u in all_urls if norm_path(u) == target or norm_path(u).endswith(target)]
        if exact:
            found = True
            print(f"  EXACT SLUG MATCH for {slug}: the planned URL already exists.")
            for u in exact:
                print(f"    {u}  {all_urls[u]}")
        st = slug_tokens(slug)
        near = []
        for u in all_urls:
            if u in exact or not st:
                continue
            ut = slug_tokens(u)
            if ut and len(st & ut) / len(st | ut) >= 0.6:
                near.append(u)
        if near:
            found = True
            print(f"  Near matches for slug {slug}:")
            for u in near[:10]:
                print(f"    {u}  {all_urls[u]}")
    if primary:
        need = {stem(t) for t in tokens(primary)}
        # Most words of the keyword in the path: URLs often drop a location or year word.
        same = []
        for u in all_urls:
            have = need & {stem(t) for t in tokens(urlparse(u).path)}
            if len(need) and len(have) >= 2 and len(have) / len(need) >= 0.75:
                same.append((len(have), u))
        same = [u for _, u in sorted(same, key=lambda r: (-r[0], r[1]))]
        if same:
            found = True
            print(f"  Paths containing most words of the primary keyword \"{primary}\":")
            for u in same[:15]:
                print(f"    {u}  {all_urls[u]}")
    if not found:
        print("  No existing page found by slug or primary keyword. Still run a site: search.")
    print("  Read each candidate's title and H1 before deciding (see SKILL.md Step 0.5).\n")


def read_file(path):
    """Return (urls_with_lastmod, child_sitemaps)."""
    with open(path, "rb") as f:
        raw = f.read()
    text = raw.decode("utf-8", errors="replace").strip()
    if not text.startswith("<"):
        return [(u.strip(), "") for u in text.splitlines() if u.strip().startswith("http")], []
    root = ET.fromstring(raw)
    urls, children = [], []
    if root.tag.endswith("sitemapindex"):
        for sm in root.iter(f"{NS}sitemap"):
            loc = sm.findtext(f"{NS}loc")
            if loc:
                children.append(loc.strip())
    else:
        for u in root.iter(f"{NS}url"):
            loc = u.findtext(f"{NS}loc")
            if loc:
                urls.append((loc.strip(), (u.findtext(f"{NS}lastmod") or "").strip()))
    return urls, children


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--terms", nargs="+", required=True,
                    help="topic terms; the first one is treated as the primary keyword")
    ap.add_argument("--slug", help="the brief's planned URL path, to check whether it already exists")
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--csv")
    args = ap.parse_args()

    term_tokens = {stem(t) for term in args.terms for t in tokens(term)}
    phrases = [term.lower().replace(" ", "-") for term in args.terms]

    all_urls, children = {}, []
    for p in args.files:
        try:
            u, c = read_file(p)
        except Exception as e:  # noqa: BLE001
            print(f"! could not parse {p}: {e}", file=sys.stderr)
            continue
        children += c
        for url, lastmod in u:
            all_urls[url] = lastmod

    if children:
        print("Sitemap index found. Fetch these child sitemaps next:")
        for c in children:
            print("  ", c)
        print()

    existing_page_report(all_urls, args.slug, args.terms[0])

    scored, excluded = [], 0
    for url, lastmod in all_urls.items():
        path = urlparse(url).path
        if EXCLUDE.search(url):
            excluded += 1
            continue
        ptoks = {stem(t) for t in tokens(path)}
        score = len(ptoks & term_tokens)
        score += sum(2 for ph in phrases if ph in path.lower())
        if score:
            scored.append((score, url, lastmod))

    scored.sort(key=lambda r: (-r[0], r[1]))
    print(f"{len(all_urls)} URLs read, {excluded} excluded as non-content, {len(scored)} matched terms.")
    print("Slug matching misses vague slugs: also scan section paths by eye.\n")
    for score, url, lastmod in scored[: args.top]:
        print(f"{score:>3}  {url}  {lastmod}")

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["score", "url", "lastmod"])
            w.writerows(scored)
        print(f"\nWrote {args.csv}")


if __name__ == "__main__":
    main()
