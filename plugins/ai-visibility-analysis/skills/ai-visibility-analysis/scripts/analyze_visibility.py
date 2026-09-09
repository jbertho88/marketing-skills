#!/usr/bin/env python3
"""
analyze_visibility.py  (lean)
Metrics engine for Moz Pro "AI Visibility" prompt-response exports.

Deliberately simple. It answers four questions from the four exported columns:
  1. Rankings: where does the brand rank on each prompt, in each model?
  2. Topics: how does it do across topics (auto-grouped from the prompts)?
  3. Competition: what is its share of voice and who leads?
  4. Strengths and gaps: which prompts is it winning, which is it losing?

No intent taxonomy, reason codes, attribute extraction, framing, or opportunity
scoring. The agent reading SKILL.md writes the narrative and must keep every
claim bounded to what the responses show (never assert a product does not exist).

Usage:
    python analyze_visibility.py FILE1.csv [FILE2.csv ...] \
        [--model NAME ...] [--topics "listings, citations, reviews"] \
        [--out metrics.json]
Topics are optional; if omitted, the engine groups the prompts automatically.
"""

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict

RANK_HEADER_RE = re.compile(r"^(?P<brand>.+?)\s+brand\s+rank$", re.IGNORECASE)
MODEL_HINTS = [
    (re.compile(r"google[_\s-]*ai[_\s-]*mode|\bai[_\s-]*mode\b|\baio\b", re.I), "Google AI Mode"),
    (re.compile(r"gemini", re.I), "Gemini"),
    (re.compile(r"chat\s*gpt|\bgpt\b|openai", re.I), "ChatGPT"),
    (re.compile(r"perplexity", re.I), "Perplexity"),
    (re.compile(r"copilot|bing", re.I), "Copilot"),
    (re.compile(r"claude", re.I), "Claude"),
]
HOST_HINTS = [(re.compile(r"openai\.com", re.I), "ChatGPT")]

STOP = set("a an and are as at be best by for from how in is it of on or the to vs versus what with "
           "you your do does i me my can good top which where when why need should kind this that "
           "over ear on with without using near under about into onto per".split())

TOPIC_LABEL_NORMALIZATIONS = {
    "rank tracker": "rank tracking",
    "pricing comparison": "pricing and comparison",
    "location businesses": "audiences and segments",
}

REPORT_TOPIC_RULES = [
    ("audiences and segments", re.compile(
        r"agenc(y|ies)\b|consultants?\b|freelancers?\b|enterprise\b|franchises?\b|"
        r"restaurants?\b|dentists?\b|healthcare\b|home services\b|hospitality\b|small businesses?\b|"
        r"multi[\s-]?location\b|service area\b|real estate\b|retail\b|financial services\b|"
        r"travel(ers?)?\b|gamers?\b|creators?\b|professionals?\b|students?\b|kids?\b|"
        r"glasses|big ears|small heads?|big heads?", re.I)),
    ("pricing and comparison", re.compile(
        r"\b(compare|comparison|vs\.?|versus|pricing|price|cost|affordable|budget|worth|"
        r"value|premium|luxury|buying|buy|deals?)\b", re.I)),
    ("noise cancellation and ANC", re.compile(r"\b(noise cancell\w+|anc|ambient)\b", re.I)),
    ("sound quality and audio features", re.compile(
        r"\b(sound|audio|bass|treble|clarity|detail|audiophile|music|fidelity)\b", re.I)),
    ("comfort and fit", re.compile(
        r"\b(comfort|comfortable|fit|wear\w+|glasses|ears?|clamp|ear cups?)\b", re.I)),
    ("travel and commute", re.compile(
        r"\b(travel|commut\w+|office|airplane|flight|plane)\b", re.I)),
    ("calls and work", re.compile(
        r"\b(video calls?|call|microphone|mic|voice|zoom|teams|meet|slack|work|office|productiv\w+)\b", re.I)),
    ("battery and durability", re.compile(
        r"\b(battery|runtime|charging|charge|durab\w+|build quality|lifespan|accessor\w+)\b", re.I)),
    ("ecosystem and connectivity", re.compile(
        r"\b(bluetooth|wireless|multipoint|connect\w+|pair\w+|compatib\w+|ecosystem|"
        r"iphone|android|apple|samsung|windows|mac|usb-c|multi-device)\b", re.I)),
    ("fitness/gaming/lifestyle", re.compile(
        r"\b(fitness|gaming|lifestyle|workouts?|gym|running|sports?|latency)\b", re.I)),
    ("citations and listings", re.compile(
        r"\b(citation(s)?|listing(s)?|business profile|directory|nap)\b", re.I)),
    ("reviews and reputation", re.compile(r"\b(review(s)?|reputation)\b", re.I)),
    ("reporting and dashboards", re.compile(r"\b(dashboard(s)?|report(ing)?|heatmap)\b", re.I)),
    ("rank tracking", re.compile(r"\b(rank|tracking|tracker|serp|map pack)\b", re.I)),
    ("analysis and diagnostics", re.compile(
        r"\b(audit|checker|analysis|analytics|monitoring|visibility|diagnostic(s)?|competitor analysis)\b", re.I)),
    ("platform evaluation", re.compile(r"\b(software|platform(s)?|tool(s)?|suite)\b", re.I)),
]
REPORT_TOPIC_RULE_MAP = dict(REPORT_TOPIC_RULES)
TOPIC_LABEL_RULE_HINTS = [
    (re.compile(r"device|compatib|ecosystem|iphone|android|apple|samsung|windows|mac", re.I), "ecosystem and connectivity"),
    (re.compile(r"fitness|gaming|lifestyle|workouts?|gym|sport", re.I), "fitness/gaming/lifestyle"),
    (re.compile(r"noise|anc", re.I), "noise cancellation and ANC"),
    (re.compile(r"sound|audio|bass|treble|clarity|audiophile", re.I), "sound quality and audio features"),
    (re.compile(r"comfort|wear|glasses|ears?", re.I), "comfort and fit"),
    (re.compile(r"travel|commut|office|plane|flight", re.I), "travel and commute"),
    (re.compile(r"video calls?|call|meeting|zoom|teams|mic|microphone|\bwork\b|office|productiv", re.I), "calls and work"),
    (re.compile(r"battery|durab|charging|build|lifespan|accessor", re.I), "battery and durability"),
    (re.compile(r"wireless|bluetooth|connectiv|pair|multipoint", re.I), "ecosystem and connectivity"),
    (re.compile(r"price|value|premium|budget|afford|luxury|worth|comparison|versus|vs", re.I), "pricing and comparison"),
    (re.compile(r"audien|segment|persona|vertical|industry", re.I), "audiences and segments"),
    (re.compile(r"citation|listing|directory|nap", re.I), "citations and listings"),
    (re.compile(r"review|reputation", re.I), "reviews and reputation"),
    (re.compile(r"report|dashboard|heatmap", re.I), "reporting and dashboards"),
    (re.compile(r"rank|tracking|serp|map pack", re.I), "rank tracking"),
    (re.compile(r"analysis|diagnostic|visibility|audit|checker|monitor", re.I), "analysis and diagnostics"),
    (re.compile(r"platform|software|tool|suite", re.I), "platform evaluation"),
]
TOPIC_MATCH_STOP = {
    "management", "platform", "software", "tool", "business", "general",
    "category", "query", "queries", "segments", "segment", "audiences",
    "use", "case", "cases", "positioning",
}

ATTRIBUTE_PATTERNS = [
    ("noise cancellation", re.compile(r"\b(noise cancell\w+|anc|ambient)\b", re.I)),
    ("sound quality", re.compile(r"\b(sound|audio|bass|treble|clarity|detail|fidelity|audiophile)\b", re.I)),
    ("comfort and fit", re.compile(r"\b(comfort|comfortable|fit|wear\w+|clamp|ear cups?|glasses)\b", re.I)),
    ("battery life", re.compile(r"\b(battery|runtime|charging|charge)\b", re.I)),
    ("calls and microphone", re.compile(r"\b(call|microphone|mic|voice|zoom|teams|slack)\b", re.I)),
    ("travel and commute", re.compile(r"\b(travel|flight|airplane|commut\w+|office)\b", re.I)),
    ("connectivity", re.compile(r"\b(bluetooth|wireless|multipoint|pair\w+|connect\w+|ecosystem|compatib\w+)\b", re.I)),
    ("durability and build", re.compile(r"\b(durab\w+|build quality|lifespan)\b", re.I)),
    ("value and pricing", re.compile(r"\b(value|price|pricing|budget|affordable|premium|luxury|cost)\b", re.I)),
    ("gaming and lifestyle", re.compile(r"\b(gaming|workout|fitness|lifestyle|latency)\b", re.I)),
    ("reviews and reputation", re.compile(r"\b(review(s)?|reputation)\b", re.I)),
    ("listings and citations", re.compile(r"\b(citation(s)?|listing(s)?|directory|business profile|nap)\b", re.I)),
    ("reporting and analytics", re.compile(r"\b(report(ing)?|dashboard(s)?|analytics|visibility|tracking|rank)\b", re.I)),
    ("platform breadth", re.compile(r"\b(platform|software|tool|suite|all[- ]in[- ]one)\b", re.I)),
    ("support and ease of use", re.compile(r"\b(easy|easier|simple|simpler|support|setup|configure|manage)\b", re.I)),
]
FRAMING_PATTERNS = [
    ("best overall", re.compile(r"\bbest overall\b", re.I)),
    ("runner-up", re.compile(r"\brunner[- ]?up\b|\bsecond best\b", re.I)),
    ("specialist pick", re.compile(r"\bbest for\b|\bgreat for\b|\bideal for\b", re.I)),
    ("budget pick", re.compile(r"\bbudget\b|\baffordable\b|\bvalue pick\b", re.I)),
    ("premium pick", re.compile(r"\bpremium\b|\bluxury\b|\bflagship\b", re.I)),
]
POSITIVE_MARKERS = re.compile(
    r"\b(best|great|strong|excellent|good|ideal|top|recommended|comfortable|clear|reliable|effective|"
    r"versatile|impressive|leading)\b", re.I)
NEGATIVE_MARKERS = re.compile(
    r"\b(weaker|worse|trails|lacks|expensive|pricey|shorter|lower|less|not ideal|not best|limited|"
    r"not great|bulkier|heavier|harder|missing|tradeoff)\b", re.I)
NEGATIVE_CONTEXT_TOKENS = {
    "weaker", "worse", "trails", "lacks", "expensive", "pricey", "shorter",
    "lower", "less", "limited", "bulkier", "heavier", "harder", "missing",
    "tradeoff", "however", "but", "not", "ideal", "best", "great",
}
TOPIC_PRIORITY_RULES = [
    ("battery and durability", re.compile(r"\b(battery|runtime|charging|charge|durab\w+|build quality|lifespan|accessor\w+)\b", re.I)),
    ("fitness/gaming/lifestyle", re.compile(r"\b(workouts?|gym|fitness|gaming|lifestyle|running|sports?|latency)\b", re.I)),
    ("pricing and comparison", re.compile(r"\b(luxury|premium|price|value|budget|affordable|worth|cost|pricing|comparison|compare|vs\.?|versus)\b", re.I)),
    ("calls and work", re.compile(r"\b(video calls?|call|microphone|mic|voice|zoom|teams|meet|slack|work|productiv\w+)\b", re.I)),
    ("ecosystem and connectivity", re.compile(r"\b(bluetooth range|multipoint|bluetooth|wireless|connect\w+|pair\w+|compatib\w+|ecosystem|iphone|android|apple|samsung|windows|mac)\b", re.I)),
    ("sound quality and audio features", re.compile(r"\b(audiophile|sound quality|bass|treble|clarity|detail|fidelity|audio)\b", re.I)),
    ("noise cancellation and ANC", re.compile(r"\b(noise cancell\w+|anc|ambient)\b", re.I)),
    ("comfort and fit", re.compile(r"\b(comfort|comfortable|fit|wear\w+|clamp|ear cups?|glasses|ears?)\b", re.I)),
    ("travel and commute", re.compile(r"\b(travel|flight|airplane|commut\w+|office)\b", re.I)),
]
PLAY_NAME_PATTERNS = [
    ("defend comfort and anc leadership", re.compile(r"\b(noise cancell\w+|anc|comfort|fit|wear)\b", re.I)),
    ("reclaim sound-quality authority", re.compile(r"\b(sound|audio|bass|treble|clarity|detail|fidelity|audiophile)\b", re.I)),
    ("build comparison coverage", re.compile(r"\b(compare|comparison|vs\.?|versus|alternatives?|price|pricing|premium|luxury|budget|value)\b", re.I)),
    ("verify lifestyle-fit opportunities", re.compile(r"\b(workouts?|gym|fitness|gaming|lifestyle|travel|commut\w+)\b", re.I)),
    ("expand work and call proof", re.compile(r"\b(video calls?|call|microphone|mic|voice|zoom|teams|meet|slack|work|productiv\w+)\b", re.I)),
    ("strengthen battery and durability proof", re.compile(r"\b(battery|runtime|charging|charge|durab\w+|build quality|lifespan)\b", re.I)),
    ("close bluetooth feature gaps", re.compile(r"\b(bluetooth|wireless|multipoint|connect\w+|pair\w+|compatib\w+|ecosystem)\b", re.I)),
]

GAP_LABELS = {
    "none_defend": "Current strength to defend",
    "tracking_cleanup_candidate": "Cleanup or consolidate",
    "no_recommendation_surface": "Low-value or no-surface query",
    "likely_product_fit_question": "Needs product-fit verification",
    "cross_model_inclusion_gap": "Visible in some models only",
    "lost_slot": "Missing where competitors appear",
    "systemic_absence": "Missing across models",
    "present_but_buried": "Present, but not prominent",
    "weak_topic_coverage": "Weak theme coverage",
}

GAP_SUMMARIES = {
    "none_defend": "This prompt is already a durable strength and should be protected.",
    "tracking_cleanup_candidate": "This prompt overlaps another tracked prompt or should be cleaned up.",
    "no_recommendation_surface": "No tracked brand surfaces here, so this may be a low-value coverage target.",
    "likely_product_fit_question": "The query may reflect a product-fit question rather than a straightforward content gap.",
    "cross_model_inclusion_gap": "The brand appears in at least one model, but drops out in others.",
    "lost_slot": "Competitors surface here while the brand does not.",
    "systemic_absence": "The brand is absent across every analyzed model for this prompt.",
    "present_but_buried": "The brand appears, but not in a strong leading slot.",
    "weak_topic_coverage": "This prompt sits in a theme where overall brand coverage is weak.",
}

FIX_LABELS = {
    "defend_existing_strength": "Defend existing strength",
    "refresh_existing_page": "Refresh existing page",
    "prompt_tracking_cleanup": "Cleanup prompt tracking",
    "manual_review": "Manual review",
    "comparison_content": "Build comparison content",
    "use_case_page": "Build use-case page",
    "feature_or_attribute_page": "Build feature or feature-page content",
    "pricing_content": "Build pricing or value content",
    "vertical_or_segment_page": "Build segment or vertical page",
    "product_positioning_review": "Verify product fit",
}

REASON_LABELS = {
    "category_leader_preferred": "A category leader is preferred",
    "competitor_preferred": "A competitor is preferred",
    "attribute_association_gap": "Feature association is weak",
    "product_fit_unclear": "Product fit is unclear",
    "pricing_positioning_gap": "Pricing or value positioning is weak",
    "enterprise_positioning_gap": "Enterprise positioning is weak",
    "use_case_positioning_gap": "Audience or use-case positioning is weak",
    "brand_present_but_not_primary": "The brand appears, but not as a leading answer",
    "no_brand_surface": "No tracked brand surfaces here",
    "duplicate_or_near_duplicate_prompt": "This prompt overlaps another tracked prompt",
    "unclear_needs_manual_review": "Needs manual review",
}


# --------------------------------------------------------------------------- #
# Small text helpers (only used for grouping prompts into topics)
# --------------------------------------------------------------------------- #
def norm_prompt(p):
    return re.sub(r"\s+", " ", (p or "").strip().lower())


def tokenize(text):
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if t not in STOP and len(t) > 2]


def stem(w):
    for suf in ("ability", "ation", "able", "ness", "ing", "ed", "ies", "ly", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)]
    return w


def tok_match(a, b):
    a, b = stem(a), stem(b)
    if a == b:
        return True
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    return len(short) >= 4 and long.startswith(short)


def normalize_topic_label(label):
    return TOPIC_LABEL_NORMALIZATIONS.get(label, label)


def dedupe_preserve_order(items):
    out = []
    seen = set()
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def titleish_label(text):
    text = (text or "").replace("/", " / ").replace("-", " ")
    small = {"and", "or", "of", "the", "to", "for", "with", "in"}
    out = []
    for i, word in enumerate(text.split()):
        lower = word.lower()
        if i > 0 and lower in small:
            out.append(lower)
        else:
            out.append(lower.capitalize())
    return " ".join(out)


def labels_similar(a, b):
    atoks = tokenize(a)
    btoks = tokenize(b)
    if not atoks or not btoks:
        return False
    matched_a = sum(1 for tok in atoks if any(tok_match(tok, other) for other in btoks))
    matched_b = sum(1 for tok in btoks if any(tok_match(tok, other) for other in atoks))
    return (
        matched_a / len(atoks) >= 0.67 and matched_b / len(btoks) >= 0.67
    ) or (
        tok_match(atoks[0], btoks[0]) and max(matched_a, matched_b) >= 1
    )


# --------------------------------------------------------------------------- #
# CSV loading
# --------------------------------------------------------------------------- #
def find_col(fieldnames, *candidates):
    low = {f.lower().strip(): f for f in fieldnames}
    for c in candidates:
        if c.lower() in low:
            return low[c.lower()]
    return None


def detect_brand(fieldnames):
    for f in fieldnames:
        m = RANK_HEADER_RE.match(f.strip())
        if m:
            return m.group("brand").strip(), f
    return None, None


def detect_model(path, rows, model_col):
    fname = os.path.basename(path)
    if model_col:
        vals = {(r.get(model_col) or "").strip() for r in rows if (r.get(model_col) or "").strip()}
        if len(vals) == 1:
            return next(iter(vals))
    for rx, label in MODEL_HINTS:
        if rx.search(fname):
            return label
    blob = " ".join((r.get("__response__") or "")[:2000] for r in rows[:5])
    for rx, label in HOST_HINTS:
        if rx.search(blob):
            return label
    return f"UNKNOWN:{fname}"


def parse_rank(val):
    val = (val or "").strip()
    if not val:
        return None
    m = re.search(r"\d+", val)
    return int(m.group()) if m else None


def split_terms(val):
    return [t.strip() for t in (val or "").split(",") if t.strip()]


def load_file(path, forced_model=None):
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        brand, rank_col = detect_brand(fieldnames)
        if not brand:
            raise ValueError(f"{path}: no '<Brand> Brand Rank' column found. Headers: {fieldnames}")
        prompt_col = find_col(fieldnames, "Prompt", "Query")
        resp_col = find_col(fieldnames, "AI Model Response", "Response", "Answer")
        terms_col = find_col(fieldnames, "Brand Terms Mentioned", "Brands Mentioned", "Brand Terms")
        model_col = find_col(fieldnames, "Model", "AI Model", "Engine", "Source")
        rows = []
        for raw in reader:
            rows.append({
                "prompt": (raw.get(prompt_col) or "").strip(),
                "__response__": raw.get(resp_col) or "",
                "terms": split_terms(raw.get(terms_col)),
                "rank": parse_rank(raw.get(rank_col)),
                "__model_cell__": (raw.get(model_col) or "").strip() if model_col else "",
            })
    model = forced_model or detect_model(
        path, [{**r, model_col: r["__model_cell__"]} for r in rows] if model_col else rows, model_col)
    return brand, model, rows


# --------------------------------------------------------------------------- #
# Topics: use what the user gave, else auto-group the prompts
# --------------------------------------------------------------------------- #
def auto_topics(prompts, k=6):
    """Group prompts by their distinctive terms. Category-level terms (present in
    a large share of prompts) are the umbrella and excluded; remaining salient
    terms seed topics, labelled with their most common two-word phrase."""
    n = len(prompts) or 1
    df = Counter()
    surface = defaultdict(Counter)
    bigrams = defaultdict(Counter)
    per_prompt = []
    for p in prompts:
        toks = tokenize(p)
        stems = set()
        for t in toks:
            s = stem(t)
            stems.add(s)
            surface[s][t] += 1
        per_prompt.append(stems)
        for s in stems:
            df[s] += 1
        for a, b in zip(toks, toks[1:]):
            bigrams[stem(a)][f"{a} {b}"] += 1
            bigrams[stem(b)][f"{a} {b}"] += 1
    umbrella = {s for s, c in df.items() if c >= max(3, 0.40 * n)}
    block = {"under", "best", "top", "good"}  # structural only; domain nouns like
    # "software" are handled by the umbrella-frequency filter, not a hardcoded list

    def eligible(s2):
        return s2 not in umbrella and s2 not in block and len(s2) >= 3 and not s2.isdigit()
    cand = sorted([(s, c) for s, c in df.items() if eligible(s) and c >= 2],
                  key=lambda x: -x[1])
    topics, labels = {}, set()
    for s, _ in cand:
        if len(topics) >= k:
            break
        members = {i for i, st in enumerate(per_prompt) if s in st}
        if len(members) < 2:
            continue
        if any(len(members & set(v)) / max(1, len(members)) > 0.7 for v in topics.values()):
            continue
        label = None
        for cl, _ in bigrams.get(s, Counter()).most_common():
            words = cl.split()
            if len(words) == 2 and all(stem(w) not in umbrella and stem(w) not in block for w in words):
                label = cl
                break
        if not label:
            label = surface[s].most_common(1)[0][0]
        if label in labels:
            continue
        labels.add(label)
        topics[label] = members
    if len(topics) < 2 and n >= 4:
        # Small prompt sets rarely repeat terms; relax to single-prompt clusters
        # so topic coverage stays populated (thin, but better than empty).
        relaxed = sorted([(s2, c) for s2, c in df.items() if eligible(s2)],
                         key=lambda x: -x[1])
        for s2, _ in relaxed:
            if len(topics) >= min(k, 5):
                break
            members = {i for i, st in enumerate(per_prompt) if s2 in st}
            if not members:
                continue
            label = None
            for cl, _ in bigrams.get(s2, Counter()).most_common():
                words = cl.split()
                if len(words) == 2 and all(stem(w) not in umbrella and stem(w) not in block for w in words):
                    label = cl
                    break
            if not label:
                label = surface[s2].most_common(1)[0][0]
            if label in labels:
                continue
            labels.add(label)
            topics[label] = members
    out = {}
    for raw_label in topics:
        label = normalize_topic_label(raw_label)
        toks = {s for w in tokenize(label) for s in [stem(w)]} | {stem(label.split()[0])}
        out.setdefault(label, set()).update(toks)
    return out


def merge_topic_specs(topic_specs):
    merged = {}
    for label, toks in topic_specs.items():
        target = None
        for existing in merged:
            if labels_similar(label, existing):
                target = existing
                break
        if target is None:
            merged[label] = set(toks)
        else:
            merged[target].update(toks)
    return merged


def add_fallback_topic_specs(prompts, topic_specs, max_topics=10, min_prompts=3):
    specs = dict(topic_specs)
    for label, rx in REPORT_TOPIC_RULES:
        if len(specs) >= max_topics:
            break
        if label in specs:
            continue
        count = sum(1 for prompt in prompts if rx.search(prompt))
        if count < min_prompts:
            continue
        specs[label] = {stem(w) for w in tokenize(label)} or {label.lower()}
    return merge_topic_specs(specs)


def parse_user_topics(raw):
    specs = {}
    for name in [t.strip() for t in re.split(r"[,;\n]", raw) if t.strip()]:
        label = normalize_topic_label(name)
        specs[label] = {stem(w) for w in tokenize(label)} or {label.lower()}
    return specs


def topic_prompt_rule(label):
    if label in REPORT_TOPIC_RULE_MAP:
        return REPORT_TOPIC_RULE_MAP[label]
    for rx, canonical in TOPIC_LABEL_RULE_HINTS:
        if rx.search(label):
            return REPORT_TOPIC_RULE_MAP[canonical]
    for canonical, rule in REPORT_TOPIC_RULES:
        if labels_similar(label, canonical):
            return rule
    return None


def topic_matches_prompt(topic, toks, ptoks, text):
    matched = False
    if toks:
        core = [tok for tok in toks if tok not in TOPIC_MATCH_STOP]
        if not core:
            core = list(toks)
        match_count = sum(1 for tok in core if any(tok_match(tok, pt) for pt in ptoks))
        needed = 1 if len(core) <= 1 else (len(core) + 1) // 2
        matched = match_count >= needed
    if not matched:
        rule = topic_prompt_rule(topic)
        if rule is not None:
            matched = bool(rule.search(text))
    return matched


def build_report_topic_specs(prompts, min_prompts=2):
    specs = {}
    for label, rx in REPORT_TOPIC_RULES:
        count = sum(1 for prompt in prompts if rx.search(prompt))
        if count >= min_prompts:
            specs[label] = {stem(w) for w in tokenize(label)} or {label.lower()}
    specs["general category queries"] = {"general", "category", "queries"}
    return specs


def prompt_topics(prompt, topic_specs, add_general_fallback=True):
    text = (prompt or "").lower()
    ptoks = set(tokenize(prompt))
    out = []
    for topic, toks in topic_specs.items():
        if topic_matches_prompt(topic, toks, ptoks, text):
            out.append(topic)
    if not out and add_general_fallback:
        for topic, rx in REPORT_TOPIC_RULES:
            if rx.search(text):
                out.append(topic)
        if not out:
            out.append("general category queries")
    return dedupe_preserve_order(out)


def clean_response_text(text):
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text or "")
    text = re.sub(r"\[[^\]]+\]\([^)]+\)", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[#*_>`]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def sentence_chunks(text):
    return [
        chunk.strip(" -:;,.")
        for chunk in re.split(r"[\r\n]+|(?<=[.!?])\s+", text or "")
        if chunk and chunk.strip(" -:;,.")
    ]


def brand_mentioned(text, brand):
    return bool(re.search(rf"\b{re.escape(brand)}\b", text or "", re.I))


def counter_rows(counter, limit=4):
    return [{"label": label, "count": count} for label, count in counter.most_common(limit)]


def extract_use_case_cluster(prompt):
    prompt = (prompt or "").strip().lower()
    m = re.search(r"\bfor\s+([a-z0-9][a-z0-9\s/-]{2,40})", prompt)
    if m:
        phrase = re.sub(r"\b(the|a|an)\b", " ", m.group(1))
        phrase = re.sub(r"\s+", " ", phrase).strip(" ?.-")
        if phrase:
            return phrase
    for label, rx in REPORT_TOPIC_RULES:
        if rx.search(prompt):
            return label
    return "general category queries"


def choose_priority_topic(prompt, topics):
    topic_set = set(topics or [])
    text = prompt or ""
    for canonical, rx in TOPIC_PRIORITY_RULES:
        if rx.search(text):
            for topic in topics or []:
                rule = topic_prompt_rule(topic)
                if topic == canonical or (rule and rule.pattern == REPORT_TOPIC_RULE_MAP.get(canonical, re.compile("$^")).pattern):
                    return topic
            if canonical in topic_set:
                return canonical
    return (topics or ["general category queries"])[0]


def infer_prompt_cluster(prompt, topics=None, fallback_topics=None):
    preferred = []
    for source_list in (topics or [], fallback_topics or []):
        for source in source_list if isinstance(source_list, list) else [source_list]:
            if source and source != "general category queries" and source not in preferred:
                preferred.append(source)
    if preferred:
        return choose_priority_topic(prompt, preferred)
    use_case = extract_use_case_cluster(prompt)
    if use_case != "general category queries":
        return use_case
    intent = classify_intent(prompt)
    if intent == "comparison":
        return "comparison and alternatives"
    if intent == "pricing":
        return "price and value"
    return "general category queries"


def extract_response_trends(rows, brand, competitors):
    tracked = [brand] + [comp for comp in competitors if comp.lower() != brand.lower()]
    per_brand = {
        name: {
            "positive": Counter(),
            "negative": Counter(),
            "framing": Counter(),
        }
        for name in tracked
    }
    for row in rows:
        text = clean_response_text(row.get("__response__") or "")
        if not text:
            continue
        for chunk in sentence_chunks(text):
            mentions = [name for name in tracked if brand_mentioned(chunk, name)]
            if not mentions:
                continue
            attrs = [label for label, rx in ATTRIBUTE_PATTERNS if rx.search(chunk)]
            framings = [label for label, rx in FRAMING_PATTERNS if rx.search(chunk)]
            has_positive = bool(framings) or bool(POSITIVE_MARKERS.search(chunk))
            has_negative = bool(NEGATIVE_MARKERS.search(chunk))
            chunk_tokens = re.findall(r"[a-z0-9']+", chunk.lower())
            for name in mentions:
                if framings:
                    per_brand[name]["framing"].update(framings)
                if attrs:
                    if has_positive or not has_negative:
                        per_brand[name]["positive"].update(attrs)
                    if has_negative:
                        for attr in attrs:
                            attr_tokens = re.findall(r"[a-z0-9']+", attr.lower())
                            attr_positions = [i for i, tok in enumerate(chunk_tokens) if tok in attr_tokens]
                            negative_positions = [i for i, tok in enumerate(chunk_tokens) if tok in NEGATIVE_CONTEXT_TOKENS]
                            if attr_positions and negative_positions and any(abs(a - n) <= 5 for a in attr_positions for n in negative_positions):
                                per_brand[name]["negative"][attr] += 1
                elif has_positive:
                    per_brand[name]["positive"]["general recommendation"] += 1
                elif has_negative:
                    per_brand[name]["negative"]["general tradeoffs"] += 1
    tracked_brand = {
        "positive_attributes": counter_rows(per_brand[brand]["positive"]),
        "negative_attributes": counter_rows(per_brand[brand]["negative"]),
        "framing": counter_rows(per_brand[brand]["framing"]),
        "include_reasons": counter_rows(per_brand[brand]["positive"]),
    }
    competitor_rows = []
    for name in competitors:
        competitor_rows.append({
            "brand": name,
            "positive_attributes": counter_rows(per_brand[name]["positive"]),
            "negative_attributes": counter_rows(per_brand[name]["negative"]),
            "framing": counter_rows(per_brand[name]["framing"]),
            "win_reasons": counter_rows(per_brand[name]["positive"]),
        })
    return {
        "tracked_brand": tracked_brand,
        "competitors": competitor_rows,
    }


# --------------------------------------------------------------------------- #
# Per-model analysis
# --------------------------------------------------------------------------- #
def analyze_one(brand, model, rows, topic_specs, report_topic_specs):
    total = len(rows)
    for r in rows:
        r["configured_topics"] = prompt_topics(r["prompt"], topic_specs, add_general_fallback=False)
        r["fallback_topics"] = prompt_topics(r["prompt"], report_topic_specs, add_general_fallback=True)
        r["topics"] = r["configured_topics"] or r["fallback_topics"]
        r["prompt_cluster"] = infer_prompt_cluster(r["prompt"], r["configured_topics"], r["fallback_topics"])
        r["persona_use_case_cluster"] = extract_use_case_cluster(r["prompt"])
        r["__response_clean__"] = clean_response_text(r.get("__response__") or "")

    present = [r for r in rows if r["rank"] is not None]
    absent = [r for r in rows if r["rank"] is None]
    ranks = [r["rank"] for r in present]
    avg_rank = round(sum(ranks) / len(ranks), 2) if ranks else None
    rank_dist = Counter(ranks)

    # Share of voice
    mention_counts = Counter()
    total_app = 0
    for r in rows:
        seen = set(r["terms"]) | ({brand} if r["rank"] is not None else set())
        for b in seen:
            mention_counts[b] += 1
            total_app += 1
    sov = {b: round(100 * c / total_app, 1) if total_app else 0.0 for b, c in mention_counts.items()}
    leader = max(sov, key=sov.get) if sov else None
    leader_gap = round(sov.get(leader, 0) - sov.get(brand, 0), 1) if leader else 0.0

    competitors = [b for b in mention_counts if b.lower() != brand.lower()]
    h2h = {}
    for c in competitors:
        both = bo = co = 0
        for r in rows:
            us = r["rank"] is not None
            them = any(t.lower() == c.lower() for t in r["terms"])
            if us and them:
                both += 1
            elif us:
                bo += 1
            elif them:
                co += 1
        h2h[c] = {"co_mentioned": both, "we_win_slot": bo, "we_lose_slot": co,
                  "their_mentions": mention_counts[c]}

    # Topic coverage for configured topics
    topic_coverage = {}
    for topic in topic_specs:
        matched = [r for r in rows if topic in r["configured_topics"]]
        if not matched:
            topic_coverage[topic] = {"prompts": 0, "visibility_rate_pct": 0.0,
                                     "average_rank": None, "weak_or_absent": 0}
            continue
        mp = [r for r in matched if r["rank"] is not None]
        mr = [r["rank"] for r in mp]
        topic_coverage[topic] = {
            "prompts": len(matched),
            "visibility_rate_pct": round(100 * len(mp) / len(matched), 1),
            "average_rank": round(sum(mr) / len(mr), 2) if mr else None,
            "weak_or_absent": len([r for r in matched if r["rank"] is None or r["rank"] >= 3]),
        }

    report_topic_coverage = {}
    for topic in report_topic_specs:
        matched = [r for r in rows if topic in r["fallback_topics"]]
        if not matched:
            report_topic_coverage[topic] = {"prompts": 0, "visibility_rate_pct": 0.0,
                                            "average_rank": None, "weak_or_absent": 0}
            continue
        mp = [r for r in matched if r["rank"] is not None]
        mr = [r["rank"] for r in mp]
        report_topic_coverage[topic] = {
            "prompts": len(matched),
            "visibility_rate_pct": round(100 * len(mp) / len(matched), 1),
            "average_rank": round(sum(mr) / len(mr), 2) if mr else None,
            "weak_or_absent": len([r for r in matched if r["rank"] is None or r["rank"] >= 3]),
        }

    def view(r, with_rank=True):
        v = {"prompt": r["prompt"], "topics": r["topics"],
             "competitors": [t for t in r["terms"] if t.lower() != brand.lower()]}
        if with_rank:
            v["rank"] = r["rank"]
        return v

    strengths = [view(r) for r in sorted(present, key=lambda r: (r["rank"], r["prompt"].lower()))]
    weak_present = [view(r) for r in sorted(present, key=lambda r: (-r["rank"], r["prompt"].lower()))
                    if r["rank"] >= 3]
    lost_slots = [view(r, with_rank=False)
                  for r in sorted(absent, key=lambda r: r["prompt"].lower())
                  if [t for t in r["terms"] if t.lower() != brand.lower()]]
    no_brand = [r["prompt"] for r in sorted(absent, key=lambda r: r["prompt"].lower())
                if not [t for t in r["terms"] if t.lower() != brand.lower()]]
    prompt_details = []
    for r in rows:
        competitors = [t for t in r["terms"] if t.lower() != brand.lower()]
        if r["rank"] is None:
            status = "absent"
        elif r["rank"] <= 2:
            status = "strong"
        else:
            status = "weak_present"
        prompt_details.append({
            "prompt": r["prompt"],
            "topics": r["topics"],
            "configured_topics": r["configured_topics"],
            "fallback_topics": r["fallback_topics"],
            "competitors": competitors,
            "rank": r["rank"],
            "status": status,
            "prompt_cluster": r["prompt_cluster"],
            "persona_use_case_cluster": r["persona_use_case_cluster"],
        })

    top_competitors = [
        name for name, _ in sorted(
            ((name, mentions) for name, mentions in mention_counts.items() if name.lower() != brand.lower()),
            key=lambda item: (-item[1], item[0].lower()),
        )[:4]
    ]
    response_trends = extract_response_trends(rows, brand, top_competitors)

    return {
        "model": model, "brand": brand,
        "totals": {
            "prompts": total, "mentioned": len(present), "absent": len(absent),
            "visibility_rate_pct": round(100 * len(present) / total, 1) if total else 0.0,
        },
        "rank": {"average": avg_rank, "distribution": {str(k): rank_dist[k] for k in sorted(rank_dist)}},
        "share_of_voice_pct": dict(sorted(sov.items(), key=lambda kv: -kv[1])),
        "leader": leader, "leader_gap_pts": leader_gap,
        "head_to_head": dict(sorted(h2h.items(), key=lambda kv: -kv[1]["their_mentions"])),
        "topic_coverage": topic_coverage,
        "report_topic_coverage": report_topic_coverage,
        "strengths": strengths,
        "weak_present_prompts": weak_present,
        "lost_slot_prompts": lost_slots,
        "no_brand_prompts": no_brand,
        "prompt_details": prompt_details,
        "response_trends": response_trends,
        "all_tracked_prompts": [r["prompt"] for r in rows],
    }


def cross_model(per_model):
    if len(per_model) < 2:
        return None
    models = [m["model"] for m in per_model]
    table = defaultdict(dict)
    display = {}
    for m in per_model:
        ranks = {norm_prompt(p): None for p in m["all_tracked_prompts"]}
        for r in m["strengths"] + m["weak_present_prompts"]:
            ranks[norm_prompt(r["prompt"])] = r["rank"]
        for p in m["all_tracked_prompts"]:
            np = norm_prompt(p)
            display.setdefault(np, p)
            table[np][m["model"]] = ranks.get(np)
    anchor, inconsistent, systemic = [], [], []
    for np, bym in table.items():
        covered = {mm: bym.get(mm) for mm in models if mm in bym}
        if len(covered) != len(models):
            continue  # Cross-model classifications require the matched cohort.
        present_ranks = [v for v in covered.values() if v is not None]
        if covered and all(v is not None and v <= 2 for v in covered.values()):
            anchor.append({"prompt": display[np], "ranks": covered})
        elif present_ranks and any(v is None for v in covered.values()):
            inconsistent.append({"prompt": display[np], "ranks": covered})
        elif covered and all(v is None for v in covered.values()):
            systemic.append({"prompt": display[np], "ranks": covered})
    return {
        "models": models,
        "per_model_summary": {m["model"]: {
            "visibility_rate_pct": m["totals"]["visibility_rate_pct"],
            "average_rank": m["rank"]["average"],
            "share_of_voice_pct": m["share_of_voice_pct"].get(m["brand"], 0.0),
            "leader": m["leader"], "leader_gap_pts": m["leader_gap_pts"],
        } for m in per_model},
        "anchor_wins": sorted(anchor, key=lambda x: x["prompt"].lower()),
        "inconsistent": sorted(inconsistent, key=lambda x: x["prompt"].lower()),
        "systemic_gaps": sorted(systemic, key=lambda x: x["prompt"].lower()),
    }


def summarize_topic_mapping(per_model, topic_specs, report_topic_specs, user_topics_given):
    prompt_map = {}
    for model in per_model:
        for detail in model["prompt_details"]:
            np = norm_prompt(detail["prompt"])
            prompt_map.setdefault(np, {
                "prompt": detail["prompt"],
                "configured_topics": set(),
                "fallback_topics": set(),
            })
            prompt_map[np]["configured_topics"].update(detail.get("configured_topics", []))
            prompt_map[np]["fallback_topics"].update(detail.get("fallback_topics", []))

    configured_counts = Counter()
    fallback_counts = Counter()
    matched_prompt_count = 0
    for record in prompt_map.values():
        if record["configured_topics"]:
            matched_prompt_count += 1
        configured_counts.update(record["configured_topics"])
        fallback_counts.update(record["fallback_topics"])

    total_prompts = len(prompt_map) or 1
    tracked_topics = [
        {"topic": topic, "prompt_count": configured_counts.get(topic, 0)}
        for topic in topic_specs
        if configured_counts.get(topic, 0) > 0
    ]
    underrepresented = [
        {"topic": topic, "prompt_count": configured_counts.get(topic, 0)}
        for topic in topic_specs
        if configured_counts.get(topic, 0) == 0 or configured_counts.get(topic, 0) < 2
    ]
    zero_match_topics = [row["topic"] for row in underrepresented if row["prompt_count"] == 0]
    coverage_pct = round(100 * matched_prompt_count / total_prompts, 1)
    needs_refinement = bool(
        user_topics_given and (
            coverage_pct < 60.0
            or len(tracked_topics) < max(2, min(4, len(topic_specs)))
            or len(zero_match_topics) >= max(1, len(topic_specs) // 3)
        )
    )
    report_topics_source = "fallback" if needs_refinement else "configured"
    warning = ""
    if needs_refinement:
        warning = (
            "The user-supplied topics mapped sparsely to the prompt set, so the report uses richer fallback "
            "prompt clusters for the main topic read. The original topic list is still shown as tracked vs "
            "underrepresented so the taxonomy can be refined for the next run."
        )
    return {
        "configured_prompt_coverage_pct": coverage_pct,
        "matched_prompt_count": matched_prompt_count,
        "unmatched_prompt_count": total_prompts - matched_prompt_count,
        "tracked_topics": tracked_topics,
        "underrepresented_topics": underrepresented,
        "zero_match_topics": zero_match_topics,
        "report_topics_source": report_topics_source,
        "needs_refinement": needs_refinement,
        "warning": warning,
        "fallback_topic_counts": dict(fallback_counts),
        "configured_topic_counts": dict(configured_counts),
        "report_topics": [
            topic for topic in (
                report_topic_specs if report_topics_source == "fallback" else topic_specs
            )
            if (
                fallback_counts.get(topic, 0) > 0
                if report_topics_source == "fallback"
                else configured_counts.get(topic, 0) > 0
            )
        ],
    }


def build_response_trend_summary(per_model, brand):
    tracked_positive = Counter()
    tracked_negative = Counter()
    tracked_framing = Counter()
    competitor_map = defaultdict(lambda: {
        "positive": Counter(),
        "negative": Counter(),
        "framing": Counter(),
    })
    by_model = {}
    for model in per_model:
        trends = model["response_trends"]
        tracked = trends["tracked_brand"]
        tracked_positive.update({row["label"]: row["count"] for row in tracked["positive_attributes"]})
        tracked_negative.update({row["label"]: row["count"] for row in tracked["negative_attributes"]})
        tracked_framing.update({row["label"]: row["count"] for row in tracked["framing"]})
        for comp in trends["competitors"]:
            competitor_map[comp["brand"]]["positive"].update({row["label"]: row["count"] for row in comp["positive_attributes"]})
            competitor_map[comp["brand"]]["negative"].update({row["label"]: row["count"] for row in comp["negative_attributes"]})
            competitor_map[comp["brand"]]["framing"].update({row["label"]: row["count"] for row in comp["framing"]})
        by_model[model["model"]] = trends
    overall_competitors = []
    for name, counters in sorted(competitor_map.items(), key=lambda item: (-sum(item[1]["positive"].values()), item[0].lower())):
        overall_competitors.append({
            "brand": name,
            "positive_attributes": counter_rows(counters["positive"]),
            "negative_attributes": counter_rows(counters["negative"]),
            "framing": counter_rows(counters["framing"]),
            "win_reasons": counter_rows(counters["positive"]),
        })
    return {
        "overall": {
            "tracked_brand": {
                "brand": brand,
                "positive_attributes": counter_rows(tracked_positive),
                "negative_attributes": counter_rows(tracked_negative),
                "framing": counter_rows(tracked_framing),
                "include_reasons": counter_rows(tracked_positive),
            },
            "competitors": overall_competitors,
        },
        "by_model": by_model,
    }


def classify_competitor_role(intent_counts, topic_counts, avg_sov=0.0):
    local_platform_signal = (
        topic_counts.get("citations and listings", 0)
        + topic_counts.get("rank tracking", 0)
        + topic_counts.get("reporting and dashboards", 0)
        + topic_counts.get("analysis and diagnostics", 0)
        + topic_counts.get("platform evaluation", 0)
    )
    scores = {
        "category_all_rounder": (
            intent_counts.get("head_term", 0)
            + intent_counts.get("comparison", 0)
            + topic_counts.get("general category queries", 0)
            + topic_counts.get("pricing and comparison", 0)
        ),
        "sound_quality_specialist": topic_counts.get("sound quality and audio features", 0) + intent_counts.get("feature_attribute", 0),
        "value_or_budget_challenger": topic_counts.get("pricing and comparison", 0) + intent_counts.get("pricing", 0),
        "enterprise_or_platform_competitor": (
            intent_counts.get("enterprise", 0)
            + topic_counts.get("platform evaluation", 0)
            + topic_counts.get("reporting and dashboards", 0)
            + topic_counts.get("rank tracking", 0)
        ),
        "reviews_reputation_specialist": topic_counts.get("reviews and reputation", 0) + topic_counts.get("review management", 0),
        "lifestyle_or_use_case_competitor": (
            intent_counts.get("use_case", 0)
            + intent_counts.get("persona", 0)
            + topic_counts.get("fitness/gaming/lifestyle", 0)
            + topic_counts.get("travel and commute", 0)
            + topic_counts.get("calls and work", 0)
            + topic_counts.get("audiences and segments", 0)
        ),
        "niche_specialist": (
            topic_counts.get("noise cancellation and ANC", 0)
            + topic_counts.get("comfort and fit", 0)
            + topic_counts.get("battery and durability", 0)
            + topic_counts.get("ecosystem and connectivity", 0)
            + topic_counts.get("reviews and reputation", 0)
        ),
    }
    role, score = max(scores.items(), key=lambda item: item[1])
    if role == "sound_quality_specialist":
        feature_span = sum(
            topic_counts.get(topic, 0) for topic in (
                "noise cancellation and ANC",
                "sound quality and audio features",
                "battery and durability",
                "ecosystem and connectivity",
                "comfort and fit",
            )
        ),
        if feature_span >= max(6, topic_counts.get("sound quality and audio features", 0) * 2) and avg_sov >= 20:
            return "category_all_rounder"
    if role == "niche_specialist" and avg_sov >= 25 and (
        topic_counts.get("sound quality and audio features", 0) + topic_counts.get("pricing and comparison", 0)
    ) >= 8:
        return "category_all_rounder"
    if avg_sov >= 30 and local_platform_signal >= 12:
        return "local_seo_platform_benchmark"
    return role if score > 0 else "niche_specialist"


def build_competitor_analysis(per_model, brand):
    avg_sov = Counter()
    seen = defaultdict(lambda: {
        "topics": Counter(),
        "clusters": Counter(),
        "intents": Counter(),
        "threat_prompts": [],
        "models": Counter(),
    })
    for model in per_model:
        for name, value in model["share_of_voice_pct"].items():
            if name.lower() != brand.lower():
                avg_sov[name] += value
        for detail in model["prompt_details"]:
            prompt = detail["prompt"]
            intent = classify_intent(prompt)
            for comp in detail.get("competitors", []):
                record = seen[comp]
                record["intents"][intent] += 1
                record["clusters"][detail.get("prompt_cluster") or "general category queries"] += 1
                record["models"][model["model"]] += 1
                for topic in detail.get("fallback_topics", []):
                    record["topics"][topic] += 1
                if detail.get("rank") is None or detail.get("status") == "weak_present":
                    record["threat_prompts"].append(prompt)
    competitors = []
    denom = max(1, len(per_model))
    for name, sov in avg_sov.items():
        record = seen.get(name)
        if not record:
            continue
        role = classify_competitor_role(record["intents"], record["topics"], round(sov / denom, 1))
        competitors.append({
            "brand": name,
            "avg_share_of_voice_pct": round(sov / denom, 1),
            "role": role,
            "strongest_topics": [topic for topic, _ in record["topics"].most_common(3)],
            "threat_prompts": dedupe_preserve_order(record["threat_prompts"])[:4],
            "models": [model for model, _ in record["models"].most_common()],
        })
    competitors.sort(key=lambda item: (-item["avg_share_of_voice_pct"], item["brand"].lower()))
    return competitors


ASSET_PACKAGES = {
    "refresh_existing_page": "refresh PDP or feature copy, retailer syndication copy, and reviewer briefing notes",
    "comparison_content": "comparison page, analyst or reviewer brief, and retailer comparison module",
    "use_case_page": "use-case landing section, FAQ blocks, and publisher briefing memo",
    "feature_or_attribute_page": "feature proof section, product detail refresh, and third-party review brief",
    "pricing_content": "value messaging page, comparison chart, and pricing-proof talking points",
    "vertical_or_segment_page": "audience brief, landing section, and partner or publisher outreach note",
    "product_positioning_review": "market validation brief and query-fit review before activation",
    "prompt_tracking_cleanup": "prompt portfolio cleanup and revised tracking taxonomy",
    "manual_review": "manual query review and response-language audit",
    "defend_existing_strength": "PDP maintenance, retailer copy QA, and reviewer proof refresh",
}
ASSET_TYPE_BY_FIX = {
    "refresh_existing_page": "Content refresh",
    "comparison_content": "Comparison page",
    "use_case_page": "Use-case page",
    "feature_or_attribute_page": "Feature proof section",
    "pricing_content": "Value messaging page",
    "vertical_or_segment_page": "Vertical page",
    "product_positioning_review": "Positioning review",
    "prompt_tracking_cleanup": "Prompt cleanup",
    "manual_review": "Manual review",
    "defend_existing_strength": "Proof refresh",
}
NEXT_STEP_BY_FIX = {
    "refresh_existing_page": "Refresh answer-ready copy",
    "comparison_content": "Build comparison brief",
    "use_case_page": "Draft use-case brief",
    "feature_or_attribute_page": "Add feature proof",
    "pricing_content": "Sharpen value story",
    "vertical_or_segment_page": "Create segment brief",
    "product_positioning_review": "Validate query fit",
    "prompt_tracking_cleanup": "Consolidate prompt tracking",
    "manual_review": "Review query manually",
    "defend_existing_strength": "Refresh proof points",
}
OWNER_BY_FIX = {
    "refresh_existing_page": "Content",
    "comparison_content": "PMM",
    "use_case_page": "Content",
    "feature_or_attribute_page": "Product Marketing",
    "pricing_content": "PMM",
    "vertical_or_segment_page": "PMM",
    "product_positioning_review": "Insights",
    "prompt_tracking_cleanup": "Insights",
    "manual_review": "Insights",
    "defend_existing_strength": "Product Marketing",
}
ACTION_TYPE_BY_FIX = {
    "refresh_existing_page": "Content refresh",
    "comparison_content": "Comparison content build",
    "use_case_page": "Use-case content build",
    "feature_or_attribute_page": "Feature proof build",
    "pricing_content": "Value messaging build",
    "vertical_or_segment_page": "Audience / segment build",
    "product_positioning_review": "Positioning validation",
    "prompt_tracking_cleanup": "Prompt portfolio cleanup",
    "manual_review": "Manual review",
    "defend_existing_strength": "Defense maintenance",
}


def normalized_topic_family(label):
    normalized = norm_prompt(label or "")
    mappings = {
        "wireless bluetooth and connectivity": "ecosystem and connectivity",
        "device compatibility and ecosystem fit": "ecosystem and connectivity",
        "fitness gaming and lifestyle use cases": "fitness/gaming/lifestyle",
        "price value and premium positioning": "pricing and comparison",
        "buying durability and accessories": "battery and durability",
        "travel commuting and office use": "travel and commute",
        "calls work and productivity": "calls and work",
        "comfort fit and wearability": "comfort and fit",
    }
    return mappings.get(normalized, normalized)


def play_campaign_name(bucket, topic, cluster, competitors, prompts=None):
    text = " ".join(filter(None, [topic, cluster]))
    topic_norm = normalized_topic_family(topic or "")
    cluster_norm = norm_prompt(cluster or "")
    for name, rx in PLAY_NAME_PATTERNS:
        if rx.search(text):
            if name == "defend comfort and anc leadership":
                mapping = {
                    "Defend": "Defend comfort and ANC leadership",
                    "Reclaim": "Reclaim comfort and ANC consideration",
                    "Build": "Build comfort and ANC proof",
                    "Verify": "Verify comfort and ANC opportunity",
                    "Retire": "Consolidate comfort and ANC tracking",
                }
                return mapping.get(bucket, "Defend comfort and ANC leadership")
            if name == "reclaim sound-quality authority":
                mapping = {
                    "Defend": "Defend sound-quality authority",
                    "Reclaim": "Reclaim sound-quality authority",
                    "Build": "Build sound-quality authority",
                    "Verify": "Verify sound-quality opportunity",
                    "Retire": "Consolidate sound-quality tracking",
                }
                return mapping.get(bucket, "Build sound-quality authority")
            if name == "build comparison coverage":
                if "listing management" in cluster_norm:
                    if topic_norm == "audiences and segments":
                        return "Expand vertical listing management coverage"
                    if topic_norm == "pricing and comparison":
                        return "Build listing comparison coverage" if bucket == "Build" else "Reclaim listing comparison coverage"
                    return "Build listing management coverage" if bucket == "Build" else "Reclaim listing management coverage"
                return {
                    "Build": "Build comparison coverage",
                    "Reclaim": "Reclaim comparison coverage",
                    "Verify": "Verify comparison opportunity",
                    "Defend": "Defend comparison authority",
                    "Retire": "Consolidate comparison tracking",
                }.get(bucket, "Build comparison coverage")
            if name == "verify lifestyle-fit opportunities":
                return {
                    "Build": "Build lifestyle-fit coverage",
                    "Reclaim": "Reclaim lifestyle-fit coverage",
                    "Verify": "Verify lifestyle-fit opportunities",
                    "Defend": "Defend lifestyle-fit coverage",
                    "Retire": "Consolidate lifestyle-fit tracking",
                }.get(bucket, "Verify lifestyle-fit opportunities")
            if name == "expand work and call proof":
                return {
                    "Build": "Build work and call proof",
                    "Reclaim": "Expand work and call proof",
                    "Verify": "Verify work and call opportunity",
                    "Defend": "Defend work and call proof",
                    "Retire": "Consolidate work and call tracking",
                }.get(bucket, "Expand work and call proof")
            if name == "strengthen battery and durability proof":
                return {
                    "Build": "Strengthen battery and durability proof",
                    "Reclaim": "Reclaim battery and durability proof",
                    "Verify": "Verify battery and durability opportunity",
                    "Defend": "Defend battery and durability proof",
                    "Retire": "Consolidate battery and durability tracking",
                }.get(bucket, "Strengthen battery and durability proof")
            if name == "close bluetooth feature gaps":
                return {
                    "Build": "Build bluetooth feature proof",
                    "Reclaim": "Close bluetooth feature gaps",
                    "Verify": "Verify bluetooth feature opportunity",
                    "Defend": "Defend bluetooth feature proof",
                    "Retire": "Consolidate bluetooth feature tracking",
                }.get(bucket, "Close bluetooth feature gaps")
            base = name
            for prefix in ("defend ", "reclaim ", "build ", "verify "):
                if base.startswith(prefix):
                    base = base[len(prefix):]
                    break
            if bucket == "Defend":
                return "Defend " + base
            if bucket == "Reclaim":
                return "Reclaim " + base
            if bucket == "Build":
                return "Build " + base
            if bucket == "Verify":
                return "Verify " + base
            return "Consolidate " + base
    fallback = cluster if cluster != "general category queries" else topic
    if bucket == "Defend":
        return f"Defend {fallback}"
    if bucket == "Reclaim":
        return f"Reclaim {fallback}"
    if bucket == "Build":
        return f"Build {fallback} coverage"
    if bucket == "Verify":
        return f"Verify {fallback} opportunity"
    return f"Consolidate {fallback} tracking"


def example_language_angle(topic, cluster, rival):
    subject = cluster if cluster != "general category queries" else topic
    rival_text = rival or "leading competitors"
    return (
        f"Use direct answer language that names the {subject} question, explains the proof points buyers care about, "
        f"and states how the offering compares with {rival_text} on the deciding tradeoffs."
    )


def score_fields(bucket, score):
    if bucket == "Retire":
        return "", score, ""
    if bucket == "Defend":
        return "", "", "Protected"
    return score, "", ""


def marketing_action_text(prompt, fix, gap, best, absent_models, rival, cluster, topic):
    where = ", ".join(absent_models) if absent_models else "weaker models"
    cluster_text = cluster if cluster != "general category queries" else topic or "this query set"
    if fix == "defend_existing_strength":
        return (
            f"Protect this winning {cluster_text} narrative by keeping PDP copy, retailer syndication, and reviewer "
            f"proof points aligned so the current 1-2 ranking holds."
        )
    if fix == "refresh_existing_page":
        return (
            f"Update the existing {cluster_text} content with clearer answer-ready summaries, product-specific proof points, "
            f"and third-party review talking points so the brand surfaces more consistently in {where}."
        )
    if fix == "comparison_content":
        return (
            f"Create or refresh comparison language for {cluster_text}, including brand-vs-{rival or 'competitor'} "
            f"tradeoffs, reviewer-ready proof points, and retailer comparison copy."
        )
    if fix == "pricing_content":
        return (
            f"Build a sharper value story for {cluster_text}, including pricing context, premium tradeoffs, and "
            f"comparison-ready proof for reviewers and commerce partners."
        )
    if fix == "use_case_page":
        return (
            f"Create a use-case brief for {cluster_text} and push the same answer-ready messaging into owned content, "
            f"retailer modules, and third-party review outreach."
        )
    if fix == "vertical_or_segment_page":
        return (
            f"Develop an audience-specific narrative for {cluster_text}, then seed it into vertical landing content, "
            f"partner copy, and relevant publisher briefs."
        )
    if fix == "feature_or_attribute_page":
        return (
            f"Create or refresh a {cluster_text} proof set that explains how the product performs, what tradeoffs matter, "
            f"and how it compares with {rival or 'leading competitors'} across owned and third-party review surfaces."
        )
    if fix == "product_positioning_review":
        return (
            f"Verify whether {cluster_text} is a deliberate market position before investing; if it is, brief the claim "
            f"clearly for both owned copy and external reviewers."
        )
    if fix == "prompt_tracking_cleanup":
        if gap == "tracking_cleanup_candidate":
            return f"Consolidate this overlapping {cluster_text} prompt into the cleaner canonical query so reporting is more decision-useful."
        return f"Keep this {cluster_text} prompt only if it serves a deliberate authority role; otherwise retire it from the tracked set."
    return f"Review the {cluster_text} prompt manually and decide whether the next move is message development, product proof, or tracking cleanup."


def strategic_play_name(bucket, cluster, topic=None):
    topic_norm = norm_prompt(topic or "")
    cluster_norm = norm_prompt(cluster or "")
    target = topic or cluster
    if topic_norm == "general category queries" and cluster_norm and cluster_norm != "general category queries":
        target = cluster
    elif topic and cluster and topic_norm != cluster_norm and cluster_norm != "general category queries":
        target = f"{topic}: {cluster}"
    if bucket == "Defend":
        return f"Defend {target}"
    if bucket == "Reclaim":
        return f"Recover {target}"
    if bucket == "Build":
        return f"Build authority in {target}"
    if bucket == "Verify":
        return f"Verify fit for {target}"
    return f"Clean up {target}"


def rec_merge_key(rec):
    family = normalized_topic_family(rec.get("report_topic") or rec.get("primary_topic") or "")
    cluster = norm_prompt(rec.get("prompt_cluster") or "")
    for name, rx in PLAY_NAME_PATTERNS:
        if rx.search(" ".join(filter(None, [family, cluster, rec.get("prompt", "")]))):
            return rec["action_bucket"], name
    if family and family != "general category queries":
        return rec["action_bucket"], family
    return rec["action_bucket"], cluster or norm_prompt(rec.get("prompt", ""))


def duplicate_play_name_variant(play):
    bucket = play["bucket"]
    topic = normalized_topic_family(play.get("topic") or "")
    cluster = norm_prompt(play.get("prompt_cluster") or "")
    prompts_text = " ".join(play.get("supporting_prompts") or []).lower()
    if "listing management" in cluster:
        if topic == "audiences and segments" or any(term in prompts_text for term in ["agenc", "franchise", "law firm", "dealership", "fitness studio"]):
            return "Expand vertical listing management coverage"
        if topic == "pricing and comparison" or any(term in prompts_text for term in ["pricing", "compare", "comparison", "vs", "versus", "affordable"]):
            return "Build listing comparison coverage" if bucket == "Build" else "Reclaim listing comparison coverage"
        return "Build listing management authority" if bucket == "Build" else "Reclaim listing management authority"
    if "marketing platforms" in cluster:
        if topic == "platform evaluation":
            if bucket == "Retire":
                return "Consolidate platform evaluation tracking"
            if bucket == "Build":
                return "Build platform evaluation coverage"
            return "Reclaim platform evaluation coverage"
        if topic == "reporting and dashboards":
            if bucket == "Retire":
                return "Consolidate reporting platform tracking"
            if bucket == "Build":
                return "Build reporting platform coverage"
            return "Reclaim reporting platform coverage"
        if topic == "analysis and diagnostics":
            if bucket == "Retire":
                return "Consolidate diagnostic platform tracking"
            if bucket == "Build":
                return "Build diagnostic platform coverage"
            return "Reclaim diagnostic platform coverage"
    qualifier = titleish_label(play.get("topic") or play.get("prompt_cluster") or "this cluster")
    if bucket == "Build":
        return f"Build {qualifier} coverage"
    if bucket == "Reclaim":
        return f"Reclaim {qualifier} coverage"
    if bucket == "Verify":
        return f"Verify {qualifier} opportunity"
    if bucket == "Defend":
        return f"Defend {qualifier}"
    return f"Consolidate {qualifier} tracking"


def prompt_based_play_qualifier(play):
    prompts_text = " ".join(play.get("supporting_prompts") or []).lower()
    qualifiers = [
        ("agenc", "for agencies"),
        ("franchise", "for franchises"),
        ("law firm", "for law firms"),
        ("dealership", "for dealerships"),
        ("fitness studio", "for fitness studios"),
        ("restaurant", "for restaurants"),
        ("audit", "for audits"),
        ("dashboard", "for dashboards"),
        ("review", "for reviews"),
        ("comparison", "for comparisons"),
        ("pricing", "for pricing"),
        ("bluetooth", "for bluetooth questions"),
        ("multipoint", "for multipoint questions"),
    ]
    for token, qualifier in qualifiers:
        if token in prompts_text:
            return qualifier
    return f"for {titleish_label(play.get('prompt_cluster') or play.get('topic') or 'this cluster')}"



# --------------------------------------------------------------------------- #
# Recommendation layer (sits on top of the metrics above; does not change them)
# --------------------------------------------------------------------------- #
INTENT_TESTS = [
    ("support_or_how_to", re.compile(r"^how (do|to|can)|troubleshoot|set ?up|configure|fix |cancel |"
                                     r"reset |connect |install ", re.I)),
    ("informational", re.compile(r"^(what is|what are(?!\s+the\s+best)|what does|why|are|is|do(es)?|can|"
                                 r"should|when|how (much|many|often|long))\b", re.I)),
    ("comparison", re.compile(r"\bvs\b|\bvs\.|\bversus\b|\bcompare|difference between|alternatives? to", re.I)),
    ("pricing", re.compile(r"pricing|price|cost|affordable|cheap|budget|under \$?\d|per (month|location|user|seat)|"
                           r"free (plan|trial|tier)|worth (it|the)|deals?\b", re.I)),
    ("enterprise", re.compile(r"enterprise|large (business|compan|organization|team)|at scale|corporations?", re.I)),
    ("local_business", re.compile(r"small business|local business|near me|franchises?|multi[\s-]?location|"
                                  r"single location", re.I)),
    # Persona: "for <people>". A modest, cross-industry people list; anything else
    # after "for" falls through to use_case below.
    ("persona", re.compile(r"\bfor\s+(beginners?|professionals?|experts?|agencies|marketers?|freelancers?|"
                           r"developers?|designers?|students?|teachers?|seniors?|kids?|children|teams?|"
                           r"families|women|men|travel?lers?|gamers?|creators?|founders?|owners?)\b|"
                           r"glasses|big ears|small heads?|big heads?", re.I)),
    # Use case: structural. "for <activity>" (gerunds and remaining "for X"),
    # covering any industry without a vocabulary list.
    ("use_case", re.compile(r"\bfor\s+\w+ing\b|\bfor\s+(work|home|school|the office|business use|travel|"
                            r"everyday use)|airplane|flight|\bfor\s+[a-z]", re.I)),
    # Feature or attribute: structural. "with (the) best X", "with X", "that has X",
    # or an explicit capability ask ("with best battery", "with API access").
    ("feature_attribute", re.compile(r"\bwith\s+(the\s+)?(best|good|great|long|strong)?\s*\w+|"
                                     r"\bthat\s+(has|have|offers?|includes?)\b|"
                                     r"^(most\s+\w+|(?!best\b|good\b)[a-z]+est)\b", re.I)),
    ("head_term", re.compile(r"^(best|top|good)\b", re.I)),
]
COMMERCIAL_INTENTS = {"head_term", "comparison", "use_case", "persona", "feature_attribute",
                      "pricing", "enterprise", "local_business"}
FUNNEL = {"head_term": "awareness", "comparison": "decision", "pricing": "decision",
          "enterprise": "decision", "use_case": "consideration", "persona": "consideration",
          "feature_attribute": "consideration", "local_business": "consideration",
          "informational": "awareness", "support_or_how_to": "post_purchase"}
EFFORT = {"defend_existing_strength": "low", "refresh_existing_page": "low",
          "prompt_tracking_cleanup": "low", "manual_review": "low",
          "comparison_content": "medium", "use_case_page": "medium",
          "feature_or_attribute_page": "medium", "pricing_content": "medium",
          "vertical_or_segment_page": "medium", "product_positioning_review": "high"}
BUILD_FIX_BY_INTENT = {"comparison": "comparison_content", "pricing": "pricing_content",
                       "use_case": "use_case_page", "persona": "vertical_or_segment_page",
                       "enterprise": "vertical_or_segment_page", "local_business": "vertical_or_segment_page",
                       "feature_attribute": "feature_or_attribute_page", "head_term": "comparison_content"}
MATRIX = {"defend_existing_strength": "Defend", "refresh_existing_page": "Reclaim",
          "comparison_content": "Build", "use_case_page": "Build", "pricing_content": "Build",
          "feature_or_attribute_page": "Build", "vertical_or_segment_page": "Build",
          "product_positioning_review": "Verify", "manual_review": "Verify",
          "prompt_tracking_cleanup": "Retire"}


def classify_intent(prompt):
    for label, rx in INTENT_TESTS:
        if rx.search(prompt):
            return label
    return "informational"


def near_duplicates(prompts):
    """Pairs of prompts whose stemmed token sets overlap at Jaccard >= 0.8.
    The 0.8 threshold keeps distinct intents that share vocabulary ("bulk listing
    management" vs "best listing management") apart while catching true phrasing
    variants ("best local seo audit tools" vs "local seo audit tools").
    Returns {normalized_prompt: canonical_prompt}."""
    toks = {p: {stem(t) for t in tokenize(p)} for p in prompts}
    dup = {}
    plist = list(prompts)
    for i, a in enumerate(plist):
        for b in plist[i + 1:]:
            ta, tb = toks[a], toks[b]
            if not ta or not tb:
                continue
            j = len(ta & tb) / len(ta | tb)
            if j >= 0.8:
                canon, other = (a, b) if len(a) <= len(b) else (b, a)
                dup[norm_prompt(other)] = canon
    return dup


def build_recommendations(per_model, topic_specs, user_topics_given):
    """One recommendation object per flagged prompt, plus Defend entries for
    anchor wins so the action matrix is complete. Metrics are untouched."""
    brand = per_model[0]["brand"]
    models = [m["model"] for m in per_model]
    n_models = len(models)

    # prompt -> per-model rank / competitors / topics
    ranks = defaultdict(dict)
    comps = defaultdict(set)
    topics_by_prompt = {}
    fallback_topics_by_prompt = {}
    prompt_clusters = {}
    persona_clusters = {}
    display = {}
    for m in per_model:
        for detail in m["prompt_details"]:
            np = norm_prompt(detail["prompt"])
            display.setdefault(np, detail["prompt"])
            ranks[np][m["model"]] = detail["rank"]
            comps[np].update(detail.get("competitors", []))
            topics_by_prompt.setdefault(np, [])
            fallback_topics_by_prompt.setdefault(np, [])
            for topic in detail.get("topics", []):
                if topic not in topics_by_prompt[np]:
                    topics_by_prompt[np].append(topic)
            for topic in detail.get("fallback_topics", []):
                if topic not in fallback_topics_by_prompt[np]:
                    fallback_topics_by_prompt[np].append(topic)
            prompt_clusters[np] = detail.get("prompt_cluster") or "general category queries"
            persona_clusters[np] = detail.get("persona_use_case_cluster") or "general category queries"

    # leader = top non-brand share of voice across models (numeric, averaged)
    sov_sum = Counter()
    for m in per_model:
        for b, v in m["share_of_voice_pct"].items():
            sov_sum[b] += v
    leader = next((b for b, _ in sov_sum.most_common() if b.lower() != brand.lower()), None)

    # weak topics per model (visibility < 50%)
    weak_topics = {m["model"]: {t for t, v in m["topic_coverage"].items()
                                if v["prompts"] > 0 and v["visibility_rate_pct"] < 50.0}
                   for m in per_model}

    dups = near_duplicates(list(display.values()))

    recs = []
    for np, by_model in ranks.items():
        prompt = display[np]
        rvals = [by_model.get(mm) for mm in models]
        present = [v for v in rvals if v is not None]
        best = min(present) if present else None
        strong_somewhere = best is not None and best <= 2
        absent_models = [mm for mm in models if mm in by_model and by_model[mm] is None]
        present_models = [mm for mm in models if by_model.get(mm) is not None]
        competitors = sorted(comps.get(np, set()))
        intent = classify_intent(prompt)
        ptopics = topics_by_prompt.get(np, [])
        fallback_topics = fallback_topics_by_prompt.get(np, [])
        report_topic = choose_priority_topic(prompt, fallback_topics) if fallback_topics else ""
        prompt_cluster = prompt_clusters.get(np) or report_topic or "general category queries"
        persona_cluster = persona_clusters.get(np) or "general category queries"
        in_weak_topic = any(t in weak_topics[mm] for mm in models for t in ptopics)
        leader_present = leader in competitors
        is_dup = np in dups
        no_brand_anywhere = not present and not competitors
        weak_models = [mm for mm in models if by_model.get(mm) is not None and by_model.get(mm) >= 3]
        affected_models = dedupe_preserve_order(absent_models + weak_models)

        anchor = present and all(v is not None and v <= 2 for v in
                                 [by_model.get(mm) for mm in models if mm in by_model])

        flagged = (bool(absent_models) or (best is not None and best >= 3)
                   or in_weak_topic or (leader_present and (best is None or best > 1)) or is_dup)
        if not flagged and not anchor:
            continue

        status = {}
        for mm in models:
            if mm not in by_model:
                status[mm] = "not_tracked"
            elif by_model[mm] is None:
                status[mm] = "absent"
            elif by_model[mm] <= 2:
                status[mm] = "strong"
            else:
                status[mm] = "weak_present"

        # ---- gap type (primary, by precedence) ----
        if anchor:
            gap = "none_defend"
        elif is_dup:
            gap = "tracking_cleanup_candidate"
        elif no_brand_anywhere and intent not in COMMERCIAL_INTENTS:
            gap = "no_recommendation_surface"
        elif not present and competitors and intent in ("enterprise",) and leader_present:
            gap = "likely_product_fit_question"
        elif present and absent_models:
            gap = "cross_model_inclusion_gap"
        elif not present and competitors:
            gap = "lost_slot" if n_models == 1 else "systemic_absence"
        elif best is not None and best >= 3:
            gap = "present_but_buried"
        elif in_weak_topic:
            gap = "weak_topic_coverage"
        else:
            gap = "present_but_buried" if best and best >= 3 else "weak_topic_coverage"

        # ---- reason codes ----
        codes = []
        if leader_present:
            codes.append("category_leader_preferred")
        elif competitors:
            codes.append("competitor_preferred")
        if gap == "likely_product_fit_question":
            codes.append("product_fit_unclear")
        if intent == "pricing" and (best is None or best >= 3):
            codes.append("pricing_positioning_gap")
        if intent == "enterprise" and (best is None or best >= 3):
            codes.append("enterprise_positioning_gap")
        if intent in ("use_case", "persona", "local_business") and (best is None or best >= 3):
            codes.append("use_case_positioning_gap")
        if intent == "feature_attribute" and (best is None or best >= 3):
            codes.append("attribute_association_gap")
        if best is not None and best >= 2 and not anchor:
            codes.append("brand_present_but_not_primary")
        if no_brand_anywhere:
            codes.append("no_brand_surface")
        if is_dup:
            codes.append("duplicate_or_near_duplicate_prompt")
        if not codes:
            codes.append("unclear_needs_manual_review")

        # ---- fix type ----
        if anchor:
            fix = "defend_existing_strength"
        elif gap == "tracking_cleanup_candidate" or gap == "no_recommendation_surface":
            fix = "prompt_tracking_cleanup"
        elif gap == "likely_product_fit_question":
            fix = "product_positioning_review"
        elif gap in ("cross_model_inclusion_gap", "present_but_buried", "weak_topic_coverage") and strong_somewhere:
            fix = "comparison_content" if intent == "comparison" else "refresh_existing_page"
        elif gap in ("lost_slot", "systemic_absence") or (best is not None and best >= 3):
            fix = BUILD_FIX_BY_INTENT.get(intent, "manual_review")
        else:
            fix = "manual_review"

        # ---- confidence ----
        if "product_fit_unclear" in codes or "no_brand_surface" in codes or fix == "manual_review":
            confidence = "low"
        elif strong_somewhere or (best is not None and best == 3):
            confidence = "high"
        else:
            confidence = "medium"

        # ---- priority score ----
        raw = 0
        raw += 20 if intent in COMMERCIAL_INTENTS else 0
        if user_topics_given:
            raw += 20 if ptopics else 0
        if present and absent_models and n_models > 1:
            factor = len(absent_models) / (n_models - 1)
            raw += 20 * factor * (1.0 if strong_somewhere else 0.5)
        if best == 3:
            raw += 15
        elif best is not None and best >= 4:
            raw += 10
        elif not present and present_models == [] and any(v is not None for v in rvals):
            raw += 8
        elif not present and n_models > 1 and any(ranks[np].get(mm) is not None for mm in models):
            raw += 8
        raw += 15 if leader_present else (8 if competitors else 0)
        raw += {"high": 10, "medium": 5, "low": 0}[confidence]
        if "product_fit_unclear" in codes:
            raw -= 15
        if no_brand_anywhere:
            raw -= 15
        max_raw = 100 if user_topics_given else 80
        score = max(0, min(100, round(raw * 100 / max_raw)))
        if anchor:
            score = 0  # defend entries are not ranked against gaps

        # ---- recommended action ----
        rival = leader if leader_present else (competitors[0] if competitors else None)
        action = marketing_action_text(prompt, fix, gap, best, absent_models, rival, prompt_cluster, report_topic)
        bucket = MATRIX[fix]
        opportunity_score, cleanup_priority, defense_priority = score_fields(bucket, score)

        recs.append({
            "prompt": prompt,
            "topics": ptopics,
            "primary_topic": ptopics[0] if ptopics else "",
            "fallback_topics": fallback_topics,
            "report_topic": report_topic or (fallback_topics[0] if fallback_topics else ""),
            "prompt_cluster": prompt_cluster,
            "persona_use_case_cluster": persona_cluster,
            "intent": intent,
            "funnel_stage": FUNNEL[intent],
            "model_ranks": {mm: by_model.get(mm) for mm in models},
            "model_status": status,
            "affected_models": affected_models,
            "competitor_winners": competitors,
            "gap_type": gap,
            "gap_label": GAP_LABELS.get(gap, gap.replace("_", " ").title()),
            "gap_summary": GAP_SUMMARIES.get(gap, ""),
            "reason_codes": codes,
            "reason_labels": [REASON_LABELS.get(code, code.replace("_", " ")) for code in codes],
            "reason_summary": "; ".join(REASON_LABELS.get(code, code.replace("_", " ")) for code in codes),
            "fix_type": fix,
            "fix_label": FIX_LABELS.get(fix, fix.replace("_", " ").title()),
            "recommended_action": action,
            "recommended_assets": ASSET_PACKAGES.get(fix, "manual review"),
            "recommended_asset_type": ASSET_TYPE_BY_FIX.get(fix, "Manual review"),
            "next_step": NEXT_STEP_BY_FIX.get(fix, "Review next step"),
            "action_type": ACTION_TYPE_BY_FIX.get(fix, "Manual review"),
            "suggested_owner": OWNER_BY_FIX.get(fix, "Insights"),
            "primary_owner": OWNER_BY_FIX.get(fix, "Insights"),
            "priority_score": score,
            "opportunity_score": opportunity_score,
            "cleanup_priority": cleanup_priority,
            "defense_priority": defense_priority,
            "confidence": confidence,
            "effort": EFFORT[fix],
            "action_bucket": bucket,
            "duplicate_of": dups.get(np),
            "status": "",
            "due_date": "",
            "source_evidence_reference": f"Prompt: {prompt}",
        })

    recs.sort(key=lambda r: (-r["priority_score"], r["prompt"].lower()))
    return recs, leader


def build_strategic_plays(recs):
    grouped = {}
    for rec in [item for item in recs if item["priority_score"] > 0]:
        cluster = rec.get("prompt_cluster") or rec.get("report_topic") or "general category queries"
        topic = rec.get("report_topic") or rec.get("primary_topic") or "general category queries"
        key = rec_merge_key(rec)
        grouped.setdefault(key, {
            "bucket": rec["action_bucket"],
            "topic": topic,
            "prompt_cluster": cluster,
            "prompts": [],
            "models": set(),
            "competitors": Counter(),
            "scores": [],
            "confidence": Counter(),
            "effort": Counter(),
            "fixes": Counter(),
            "owners": Counter(),
            "families": Counter(),
        })
        group = grouped[key]
        group["prompts"].append(rec["prompt"])
        group["models"].update(rec.get("affected_models", []))
        group["competitors"].update(rec.get("competitor_winners", []))
        group["scores"].append(rec["priority_score"])
        group["confidence"][rec["confidence"]] += 1
        group["effort"][rec["effort"]] += 1
        group["fixes"][rec["fix_type"]] += 1
        group["owners"][rec["suggested_owner"]] += 1
        group["families"][normalized_topic_family(topic)] += 1

    plays = []
    for _, group in grouped.items():
        primary_fix = group["fixes"].most_common(1)[0][0]
        top_rivals = [name for name, _ in group["competitors"].most_common(2)]
        avg_score = sum(group["scores"]) / len(group["scores"])
        score = min(100, round(avg_score + min(len(group["prompts"]), 4) * 3))
        cluster = group["prompt_cluster"]
        bucket = group["bucket"]
        dominant_family = group["families"].most_common(1)[0][0] if group["families"] else normalized_topic_family(group["topic"])
        topic = group["topic"]
        if dominant_family and dominant_family != "general category queries":
            topic = dominant_family
        prompt_count = len(group["prompts"])
        if prompt_count == 1:
            why = (
                f"One tracked prompt sits in the {cluster} cluster, and the brand is weakest in "
                f"{', '.join(sorted(group['models'])) or 'the tracked models'}."
            )
        else:
            why = (
                f"{prompt_count} tracked prompts point to {cluster}, where the brand is weakest in "
                f"{', '.join(sorted(group['models'])) or 'the tracked models'}."
            )
        if top_rivals:
            why += f" The primary competitor threat is {', '.join(top_rivals)}."
        opportunity_score, cleanup_priority, defense_priority = score_fields(bucket, score)
        plays.append({
            "play_name": play_campaign_name(bucket, topic, cluster, top_rivals, group["prompts"]),
            "bucket": bucket,
            "topic": topic,
            "prompt_cluster": cluster,
            "affected_models": sorted(group["models"]),
            "competitor_threat": top_rivals,
            "why_it_matters": why,
            "recommended_assets": ASSET_PACKAGES.get(primary_fix, "manual review"),
            "recommended_asset_type": ASSET_TYPE_BY_FIX.get(primary_fix, "Manual review"),
            "example_language_angle": example_language_angle(topic, cluster, top_rivals[0] if top_rivals else None),
            "execution_notes": marketing_action_text(
                group["prompts"][0],
                primary_fix,
                "",
                None,
                sorted(group["models"]),
                top_rivals[0] if top_rivals else None,
                cluster,
                topic,
            ),
            "priority_score": score,
            "opportunity_score": opportunity_score,
            "cleanup_priority": cleanup_priority,
            "defense_priority": defense_priority,
            "confidence": group["confidence"].most_common(1)[0][0],
            "effort": group["effort"].most_common(1)[0][0],
            "suggested_owner": group["owners"].most_common(1)[0][0],
            "supporting_prompts": dedupe_preserve_order(group["prompts"])[:6],
        })
    counts = Counter(play["play_name"] for play in plays)
    for play in plays:
        if counts[play["play_name"]] > 1:
            play["play_name"] = duplicate_play_name_variant(play)
    counts = Counter(play["play_name"] for play in plays)
    for play in plays:
        if counts[play["play_name"]] > 1:
            qualifier = prompt_based_play_qualifier(play)
            play["play_name"] = f"{play['play_name']} {qualifier}"
    plays.sort(key=lambda item: (-item["priority_score"], item["play_name"].lower()))
    return plays


def build_appendix_records(recs, per_model):
    models = [m["model"] for m in per_model]
    rec_by = {norm_prompt(r["prompt"]): r for r in recs}
    detail_by_prompt = {}
    all_prompts = []
    seen = set()
    for m in per_model:
        for detail in m["prompt_details"]:
            p = detail["prompt"]
            np = norm_prompt(p)
            if np not in seen:
                seen.add(np)
                all_prompts.append(p)
                detail_by_prompt[np] = {
                    "prompt": p,
                    "topics": list(detail.get("topics", [])),
                    "configured_topics": list(detail.get("configured_topics", [])),
                    "fallback_topics": list(detail.get("fallback_topics", [])),
                    "competitors": set(detail.get("competitors", [])),
                    "model_ranks": {},
                    "model_status": {},
                    "prompt_cluster": detail.get("prompt_cluster") or "general category queries",
                    "persona_use_case_cluster": detail.get("persona_use_case_cluster") or "general category queries",
                }
            for topic in detail.get("topics", []):
                if topic not in detail_by_prompt[np]["topics"]:
                    detail_by_prompt[np]["topics"].append(topic)
            for topic in detail.get("configured_topics", []):
                if topic not in detail_by_prompt[np]["configured_topics"]:
                    detail_by_prompt[np]["configured_topics"].append(topic)
            for topic in detail.get("fallback_topics", []):
                if topic not in detail_by_prompt[np]["fallback_topics"]:
                    detail_by_prompt[np]["fallback_topics"].append(topic)
            detail_by_prompt[np]["competitors"].update(detail.get("competitors", []))
            detail_by_prompt[np]["model_ranks"][m["model"]] = detail.get("rank")
            detail_by_prompt[np]["model_status"][m["model"]] = detail.get("status")
    records = []
    for p in sorted(all_prompts, key=lambda x: x.lower()):
        base = detail_by_prompt[norm_prompt(p)]
        r = rec_by.get(norm_prompt(p))
        intent = r["intent"] if r else classify_intent(p)
        record = {
            "prompt": p,
            "primary_topic": (r.get("primary_topic", "") if r else (base["topics"][0] if base["topics"] else "")),
            "report_topic": r.get("report_topic", "") if r else (base["fallback_topics"][0] if base["fallback_topics"] else ""),
            "topics": "; ".join(r["topics"]) if r else "; ".join(base["topics"]),
            "configured_topics": "; ".join(base["configured_topics"]),
            "fallback_topics": "; ".join(base["fallback_topics"]),
            "prompt_cluster": r.get("prompt_cluster", "") if r else base["prompt_cluster"],
            "persona_use_case_cluster": r.get("persona_use_case_cluster", "") if r else base["persona_use_case_cluster"],
            "intent": intent,
            "funnel_stage": FUNNEL[intent],
            "gap_type": r.get("gap_label", "") if r else "",
            "gap_type_code": r["gap_type"] if r else "",
            "gap_summary": r.get("gap_summary", "") if r else "",
            "recommended_play": r.get("recommended_play", "") if r else "",
            "fix_type_code": r["fix_type"] if r else "",
            "recommended_action": r.get("recommended_action", "") if r else "",
            "recommended_assets": r.get("recommended_assets", "") if r else "",
            "recommended_asset_type": r.get("recommended_asset_type", "") if r else "",
            "next_step": r.get("next_step", "") if r else "",
            "action_type": r.get("action_type", "") if r else "Watch / monitor",
            "priority_score": r.get("priority_score", "") if r else "",
            "opportunity_score": r.get("opportunity_score", "") if r else "",
            "cleanup_priority": r.get("cleanup_priority", "") if r else "",
            "defense_priority": r.get("defense_priority", "") if r else "",
            "confidence": r.get("confidence", "") if r else "",
            "effort": r.get("effort", "") if r else "",
            "action_bucket": r.get("action_bucket", "") if r else "Watch",
            "competitor_winners": "; ".join(r["competitor_winners"]) if r else "; ".join(sorted(base["competitors"])),
            "reason_summary": r.get("reason_summary", "") if r else "",
            "reason_codes": "; ".join(r["reason_codes"]) if r else "",
            "suggested_owner": r.get("suggested_owner", "") if r else "Insights",
            "primary_owner": r.get("primary_owner", "") if r else "Insights",
            "status": r.get("status", "") if r else "",
            "due_date": r.get("due_date", "") if r else "",
            "source_evidence_reference": r.get("source_evidence_reference", f"Prompt: {p}") if r else f"Prompt: {p}",
        }
        for mm in models:
            record[f"rank_{mm}"] = r["model_ranks"].get(mm, "") if r else base["model_ranks"].get(mm, "")
            record[f"status_{mm}"] = r["model_status"].get(mm, "") if r else base["model_status"].get(mm, "")
        records.append(record)
    return records


def write_appendix_csv(path, records, per_model):
    models = [m["model"] for m in per_model]
    header = ([
        "prompt", "primary_topic", "report_topic", "topics", "configured_topics", "fallback_topics",
        "prompt_cluster", "persona_use_case_cluster", "intent", "funnel_stage",
        "gap_type", "gap_type_code", "gap_summary", "recommended_play", "fix_type_code",
        "recommended_action", "recommended_assets", "recommended_asset_type", "next_step", "action_type",
        "priority_score", "opportunity_score", "cleanup_priority", "defense_priority",
        "confidence", "effort", "action_bucket", "competitor_winners", "reason_summary",
        "reason_codes", "suggested_owner", "primary_owner", "status", "due_date", "source_evidence_reference",
    ] + [f"rank_{mm}" for mm in models] + [f"status_{mm}" for mm in models])
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for record in records:
            w.writerow(record)


def load_citation_analysis(citation_json_path):
    if not citation_json_path:
        return {"enabled": False, "reason": "No citation export files provided."}
    with open(citation_json_path, encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, dict) and "citation_analysis" in payload:
        citation = payload["citation_analysis"]
    else:
        citation = payload
    if not isinstance(citation, dict):
        return {"enabled": False, "reason": "Citation analysis payload was not a JSON object."}
    citation.setdefault("enabled", False)
    return citation


def main():
    ap = argparse.ArgumentParser(description="Moz AI Visibility metrics engine (lean)")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--model", action="append", default=[])
    ap.add_argument("--topics", default="", help="Comma-separated topics. Omit to auto-group.")
    ap.add_argument("--auto-topics", type=int, default=8)
    ap.add_argument("--out", default="metrics.json")
    ap.add_argument("--csv", default="", help="Appendix CSV path (default: alongside --out).")
    ap.add_argument("--citation-json", default="", help="Optional citation analysis JSON produced by analyze_citations.py.")
    args = ap.parse_args()

    loaded, brands = [], set()
    for i, path in enumerate(args.files):
        forced = args.model[i] if i < len(args.model) else None
        brand, model, rows = load_file(path, forced)
        brands.add(brand)
        loaded.append((brand, model, rows))
    if len(brands) > 1:
        print(f"WARNING: files reference different brands {sorted(brands)}.", file=sys.stderr)

    primary_brand = loaded[0][0]
    all_prompts, seen = [], set()
    for _, _, rows in loaded:
        for r in rows:
            np = norm_prompt(r["prompt"])
            if np not in seen:
                seen.add(np)
                all_prompts.append(r["prompt"])

    if args.topics.strip():
        topic_specs = parse_user_topics(args.topics)
        auto = False
    else:
        topic_specs = auto_topics(all_prompts, k=args.auto_topics)
        topic_specs = merge_topic_specs(topic_specs)
        topic_specs = add_fallback_topic_specs(
            all_prompts,
            topic_specs,
            max_topics=max(args.auto_topics, 10),
            min_prompts=3,
        )
        auto = True

    report_topic_specs = build_report_topic_specs(all_prompts, min_prompts=2)
    per_model = [analyze_one(b, m, rows, topic_specs, report_topic_specs) for (b, m, rows) in loaded]
    cm = cross_model(per_model)
    recs, category_leader = build_recommendations(per_model, topic_specs, not auto)
    topic_mapping = summarize_topic_mapping(per_model, list(topic_specs.keys()), list(report_topic_specs.keys()), not auto)
    strategic_plays = build_strategic_plays(recs)
    citation_analysis = load_citation_analysis(args.citation_json)
    if citation_analysis.get("enabled"):
        strategic_plays.extend(citation_analysis.get("citation_plays", []))
        strategic_plays.sort(key=lambda item: (-item.get("priority_score", 0), item.get("play_name", "").lower()))
    play_by_prompt = {}
    for play in strategic_plays:
        for prompt in play["supporting_prompts"]:
            play_by_prompt.setdefault(norm_prompt(prompt), play["play_name"])
    for rec in recs:
        rec["recommended_play"] = play_by_prompt.get(norm_prompt(rec["prompt"]), "")
    appendix_records = build_appendix_records(recs, per_model)
    response_trends = build_response_trend_summary(per_model, primary_brand)
    competitor_analysis = build_competitor_analysis(per_model, primary_brand)
    csv_path = args.csv or os.path.join(os.path.dirname(os.path.abspath(args.out)) or ".",
                                        "appendix.csv")
    write_appendix_csv(csv_path, appendix_records, per_model)

    result = {
        "brand": primary_brand,
        "models_analyzed": [m["model"] for m in per_model],
        "topics": list(topic_specs.keys()),
        "topics_auto_grouped": auto,
        "report_topics": topic_mapping["report_topics"],
        "topic_mapping": topic_mapping,
        "per_model": per_model,
        "cross_model": cm,
        "category_leader": category_leader,
        "competitor_analysis": competitor_analysis,
        "response_trends": response_trends,
        "strategic_plays": strategic_plays,
        "recommendations": recs,
        "appendix_records": appendix_records,
        "appendix_csv": csv_path,
        "citation_analysis": citation_analysis,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    tag = " (auto-grouped)" if auto else ""
    print(f"Brand: {primary_brand} | topics{tag}: {list(topic_specs.keys())}")
    for m in per_model:
        print(f"\n[{m['model']}] visibility {m['totals']['visibility_rate_pct']}% | "
              f"avg rank {m['rank']['average']} | SoV {m['share_of_voice_pct'].get(primary_brand, 0.0)}% | "
              f"leader {m['leader']} (gap {m['leader_gap_pts']}pts)")
        t = m["totals"]
        print(f"   {t['mentioned']} present, {t['absent']} absent "
              f"({len(m['lost_slot_prompts'])} lost to rivals, {len(m['no_brand_prompts'])} no-brand)")
    if cm:
        print(f"\nCross-model: {len(cm['anchor_wins'])} anchor, {len(cm['inconsistent'])} inconsistent, "
              f"{len(cm['systemic_gaps'])} systemic")
    flagged = [r for r in recs if r["priority_score"] > 0]
    buckets = Counter(r["action_bucket"] for r in recs)
    print(f"\nRecommendations: {len(flagged)} flagged | matrix: " +
          ", ".join(f"{k} {v}" for k, v in buckets.most_common()))
    print("Top 3: " + "; ".join(f"{r['prompt'][:38]} ({r['priority_score']})" for r in flagged[:3]))
    print(f"\nWrote {args.out} and {csv_path}")


if __name__ == "__main__":
    main()
