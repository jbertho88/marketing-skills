#!/usr/bin/env python3
"""Shortlist internal-link candidates from sitemap files.

Usage:
  python sitemap_filter.py sitemap.xml [more.xml|urls.txt ...] --terms "kw one" "kw two" [--top 40] [--csv out.csv]

Accepts sitemap XML (urlset or sitemapindex) or plain text files with one URL per line.
Scores each URL by how many topic-term tokens appear in its path, drops non-content
paths, and prints a ranked shortlist. If a file is a sitemap index, the child sitemap
URLs are printed so you can fetch them next.
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
    ap.add_argument("--terms", nargs="+", required=True)
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
