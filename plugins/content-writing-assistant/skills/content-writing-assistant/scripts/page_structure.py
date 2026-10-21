#!/usr/bin/env python3
"""Extract countable structure from saved HTML pages of ranking results.

Usage:
  python page_structure.py page1.html [page2.html ...] [--json out.json]

Requires beautifulsoup4 (pip install beautifulsoup4). Works on local HTML files only,
so fetch pages first with whatever method your environment allows. Outputs title, H1,
H2/H3 outline, approximate main-content word count, image/table/video/list counts,
FAQ and TOC hints, author hints, and JSON-LD schema types. Judgement calls (angle,
originality of images, quality) are left to the reader.
"""
import argparse
import json
import re
import sys

try:
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("beautifulsoup4 is required: pip install beautifulsoup4")


def main_node(soup):
    for sel in ["article", "main", "[role=main]", "#content", ".entry-content", ".post-content"]:
        n = soup.select_one(sel)
        if n and len(n.get_text(" ", strip=True).split()) > 200:
            return n
    return soup.body or soup


def schema_types(soup):
    types = set()
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(s.string or "")
        except Exception:  # noqa: BLE001
            continue
        stack = [data]
        while stack:
            d = stack.pop()
            if isinstance(d, list):
                stack.extend(d)
            elif isinstance(d, dict):
                t = d.get("@type")
                if isinstance(t, list):
                    types.update(map(str, t))
                elif t:
                    types.add(str(t))
                stack.extend(v for v in d.values() if isinstance(v, (dict, list)))
    return sorted(types)


def analyze(path):
    with open(path, "rb") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    for t in soup(["script", "style", "noscript"]):
        if t.get("type") != "application/ld+json":
            t.decompose()
    types = schema_types(soup)
    for t in soup(["nav", "header", "footer", "aside", "form"]):
        t.decompose()
    main = main_node(soup)
    text = main.get_text(" ", strip=True)
    outline = [f"{h.name.upper()}: {h.get_text(' ', strip=True)}" for h in main.find_all(["h2", "h3"])]
    iframes = [i.get("src", "") for i in main.find_all("iframe")]
    lower = text.lower()
    return {
        "file": path,
        "title": soup.title.get_text(strip=True) if soup.title else None,
        "h1": [h.get_text(" ", strip=True) for h in soup.find_all("h1")],
        "word_count_approx": len(text.split()),
        "h2_count": sum(1 for o in outline if o.startswith("H2")),
        "outline": outline,
        "images": len(main.find_all("img")),
        "images_missing_alt": sum(1 for i in main.find_all("img") if not i.get("alt")),
        "tables": len(main.find_all("table")),
        "lists": len(main.find_all(["ul", "ol"])),
        "videos": len(main.find_all("video")) + sum(1 for s in iframes if re.search(r"youtube|vimeo|wistia", s)),
        "faq_hint": bool(re.search(r"frequently asked|\bfaqs?\b", lower)),
        "toc_hint": bool(re.search(r"table of contents|in this article|jump to", lower)),
        "author_hint": bool(soup.select_one("[rel=author], .author, .byline, [itemprop=author]")),
        "schema_types": types,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--json")
    args = ap.parse_args()
    results = []
    for p in args.files:
        try:
            results.append(analyze(p))
        except Exception as e:  # noqa: BLE001
            results.append({"file": p, "error": str(e)})
    for r in results:
        if "error" in r:
            print(f"{r['file']}: ERROR {r['error']} (record as unknown, not zero)")
            continue
        print(f"\n== {r['file']}\n{r['title']}\nH1: {r['h1']}\n~{r['word_count_approx']} words, "
              f"{r['h2_count']} H2s, {r['images']} imgs ({r['images_missing_alt']} no alt), "
              f"{r['tables']} tables, {r['videos']} videos, FAQ={r['faq_hint']}, TOC={r['toc_hint']}, "
              f"author={r['author_hint']}\nSchema: {', '.join(r['schema_types']) or 'none'}")
        for line in r["outline"]:
            print("   ", line)
    if args.json:
        with open(args.json, "w") as f:
            json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
