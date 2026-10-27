#!/usr/bin/env python3
"""Check a clean article against the mechanical rules in its briefs.

Usage:
  python brief_check.py <slug>-article.md --spec spec.json [--json report.json]
  python brief_check.py --example            # print a starter spec

Reads the clean article file (SEO title / meta description lines, then the article
from its H1). Every spec key is optional; only the checks you configure run, apart
from placeholders, links and duplicate links, which are always reported.

Checks:
  word_count        article words (H1 to end), placeholders excluded
  keywords          count per term vs min/max; flags misses and stuffing
  banned_terms      words or phrases that must not appear (case-insensitive)
  banned_chars      characters that must not appear (e.g. em dash)
  meta              SEO title and meta description character limits
  required_links    URL substrings that must be linked somewhere in the body
  duplicate_links   same URL linked more than once (allowed if allow_duplicate_links)
  spelling          "en-CA" / "en-GB": flags common US spellings
  numbers           "spell_one_to_nine": flags bare digits 1-9 outside measurements
  headings          "no_years": flags years in H2/H3 headings
  placeholders      lists every open placeholder ([[...]], [EXPERT INPUT: ...], etc.)

Exit code 1 if any check fails, so it can gate a run.
"""
import argparse
import json
import re
import sys
from collections import Counter

EXAMPLE = {
    "word_count": {"min": 1080, "max": 1320},
    "keywords": [
        {"term": "window air seal comparison", "min": 2},
        {"term": "best window seal technology canada", "min": 1, "max": 2},
        {"term": "best gas bbq", "variants": ["best gas grill"], "min": 3, "max": 4},
    ],
    "banned_terms": ["lifetime warranty", "krypton", "guaranteed"],
    "banned_chars": ["\u2014"],
    "meta": {"title_max": 60, "description_min": 150, "description_max": 160},
    "required_links": ["/vinyl-windows.html", "/faq.html"],
    "allow_duplicate_links": False,
    "spelling": "en-CA",
    "numbers": "spell_one_to_nine",
    "headings": {"no_years": True},
}

US_SPELLINGS = [
    "color", "colors", "colored", "flavor", "flavors", "favorite", "favorites", "neighbor",
    "neighbors", "neighborhood", "honor", "labor", "behavior", "center", "centers", "theater",
    "fiber", "fiberglass", "gray", "mold", "aluminum-free", "catalog", "traveling", "canceled",
    "jewelry", "defense", "offense", "practicing",
]
PLACEHOLDER = re.compile(r"\[\[[^\]]+\]\]|\[(?:EXPERT INPUT|VERIFY|PLACEHOLDER|QUOTE)[^\]]*\]", re.I)
LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+|/[^)\s]*)\)")


def load_article(path):
    text = open(path, encoding="utf-8").read()
    meta = {}
    for key, pat in [("title", r"\*\*(?:SEO title|Meta title|Title tag)[^*]*:\*\*\s*(.+)"),
                     ("description", r"\*\*Meta description[^*]*:\*\*\s*(.+)")]:
        m = re.search(pat, text, re.I)
        if m:
            meta[key] = m.group(1).strip()
    m = re.search(r"^# .+$", text, re.M)
    body = text[m.start():] if m else text
    return text, body, meta


def plain_words(body):
    t = PLACEHOLDER.sub(" ", body)
    t = LINK.sub(lambda m: m.group(1), t)
    t = re.sub(r"`[^`]*`", " ", t)
    t = re.sub(r"^\s*\|?[-:| ]+\|?\s*$", " ", t, flags=re.M)  # table rules
    t = re.sub(r"[#*_>|]", " ", t)
    return t


def count_phrase(low_text, phrase):
    words = [re.escape(w) for w in re.split(r"[\s\-]+", phrase.lower()) if w]
    # Between words, tolerate spaces, hyphens, punctuation and trademark symbols
    # ("DraftLOCK™ vs. standard window"), plus an optional small connector word.
    sep = r"[\s\-.,:;\u2122\u00ae\u00a9]+(?:(?:in|the|a|of|for)\s+)?"
    pat = r"\b" + sep.join(words) + r"(?![a-z0-9])"
    return len(re.findall(pat, low_text))


def run(article_path, spec):
    text, body, meta = load_article(article_path)
    plain = plain_words(body)
    low = " ".join(plain.lower().split())
    results = []

    def add(name, ok, detail, level="FAIL"):
        results.append({"check": name, "status": "PASS" if ok else level, "detail": detail})

    wc = len(plain.split())
    if "word_count" in spec:
        lo, hi = spec["word_count"].get("min"), spec["word_count"].get("max")
        ok = (lo is None or wc >= lo) and (hi is None or wc <= hi)
        add("word_count", ok, f"{wc} words (range {lo}-{hi})")
    else:
        add("word_count", True, f"{wc} words (no range set)")

    for kw in spec.get("keywords", []):
        terms = [kw["term"]] + kw.get("variants", [])
        n = sum(count_phrase(low, t) for t in terms)
        lo, hi = kw.get("min", 0), kw.get("max")
        label = " / ".join(terms)
        if n < lo:
            add(f"keyword: {label}", False, f"{n} uses, need at least {lo}")
        elif hi is not None and n > hi:
            add(f"keyword: {label}", False, f"{n} uses, max {hi} (stuffing risk; headings or brief-mandated questions may account for some)", "WARN")
        elif hi is None and lo and n > max(lo * 3, lo + 4):
            add(f"keyword: {label}", False, f"{n} uses vs minimum {lo}: check for stuffing", "WARN")
        else:
            add(f"keyword: {label}", True, f"{n} uses (target {lo}-{hi if hi is not None else 'n/a'})")

    for term in spec.get("banned_terms", []):
        n = count_phrase(text.lower(), term)
        add(f"banned term: {term}", n == 0, f"{n} hits")
    for ch in spec.get("banned_chars", []):
        n = text.count(ch)
        add(f"banned char: {ch!r}", n == 0, f"{n} hits")

    m = spec.get("meta", {})
    for key, lo_k, hi_k in [("title", "title_min", "title_max"), ("description", "description_min", "description_max")]:
        if lo_k in m or hi_k in m:
            v = meta.get(key)
            if v is None:
                add(f"meta {key}", False, "not found (expected a '**SEO title:**' / '**Meta description:**' line)")
                continue
            lo, hi = m.get(lo_k), m.get(hi_k)
            ok = (lo is None or len(v) >= lo) and (hi is None or len(v) <= hi)
            add(f"meta {key}", ok, f"{len(v)} chars (range {lo}-{hi})")

    links = [u for _, u in LINK.findall(body)]
    for need in spec.get("required_links", []):
        add(f"required link: {need}", any(need in u for u in links), "present" if any(need in u for u in links) else "missing")
    dupes = {u: c for u, c in Counter(links).items() if c > 1}
    if dupes and not spec.get("allow_duplicate_links", False):
        add("duplicate links", False, "; ".join(f"{u} x{c}" for u, c in dupes.items()), "WARN")
    else:
        add("duplicate links", True, f"{len(links)} links, {len(set(links))} unique")

    if spec.get("spelling") in ("en-CA", "en-GB"):
        hits = sorted({w for w in US_SPELLINGS if re.search(rf"\b{re.escape(w)}\b", low)})
        add(f"spelling ({spec['spelling']})", not hits, ", ".join(hits) if hits else "no common US spellings", "WARN")

    if spec.get("numbers") == "spell_one_to_nine":
        bare = re.findall(r"(?<![\w.,/½¼¾$#-])\b([1-9])\b(?![\w.,/%″½¼¾-]| ?(?:in|cm|mm|m|ft|L/s|kg|lb|%|″|\"))", plain)
        add("numbers one to nine spelled out", not bare, f"{len(bare)} bare digits: {bare[:10]}" if bare else "none", "WARN")

    if spec.get("headings", {}).get("no_years"):
        heads = [h for h in re.findall(r"^#{2,3} (.+)$", body, re.M) if re.search(r"\b(19|20)\d\d\b", h)]
        add("headings without years", not heads, "; ".join(heads) if heads else "none")

    ph = PLACEHOLDER.findall(text)
    results.append({"check": "open placeholders", "status": "INFO", "detail": f"{len(ph)}: " + " | ".join(p[:70] for p in ph)})
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("article", nargs="?")
    ap.add_argument("--spec")
    ap.add_argument("--json")
    ap.add_argument("--example", action="store_true")
    a = ap.parse_args()
    if a.example:
        print(json.dumps(EXAMPLE, indent=2))
        return
    if not a.article:
        ap.error("article path required")
    spec = json.load(open(a.spec, encoding="utf-8")) if a.spec else {}
    res = run(a.article, spec)
    width = max(len(r["check"]) for r in res)
    for r in res:
        print(f"{r['status']:<5} {r['check']:<{width}}  {r['detail']}")
    if a.json:
        json.dump(res, open(a.json, "w"), indent=2, ensure_ascii=False)
    fails = sum(r["status"] == "FAIL" for r in res)
    warns = sum(r["status"] == "WARN" for r in res)
    print(f"\n{fails} fail, {warns} warn")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
