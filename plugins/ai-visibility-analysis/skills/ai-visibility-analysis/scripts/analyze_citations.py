#!/usr/bin/env python3
"""
analyze_citations.py
Analyze Moz AI Visibility citation export CSVs and produce a cited-page appendix
plus a citation metrics JSON object that can be merged into the main visibility
metrics output.

Usage:
    python analyze_citations.py \
        --brand "Bose" \
        --owned-domains bose.com \
        --citation ChatGPT="chatgpt.csv" \
        --citation Gemini="gemini.csv" \
        --citation "Google AI Mode=google-ai-mode.csv" \
        --out-json citation-metrics.json \
        --out-csv cited-pages.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
    "utm_id",
    "gclid",
    "fbclid",
    "mc_cid",
    "mc_eid",
}

PUBLISHER_REVIEW_DOMAINS = {
    "rtings.com",
    "soundguys.com",
    "techradar.com",
    "tomsguide.com",
    "whathifi.com",
    "cnet.com",
    "theverge.com",
    "wirecutter.com",
    "pcmag.com",
    "reviewed.com",
    "expertreviews.co.uk",
    "trustedreviews.com",
    "mashable.com",
    "popsci.com",
    "telegraph.co.uk",
    "engadget.com",
    "digitaltrends.com",
}

RETAILER_DOMAINS = {
    "bestbuy.com",
    "amazon.com",
    "amazon.co.uk",
    "walmart.com",
    "target.com",
    "crutchfield.com",
    "bhphotovideo.com",
    "costco.com",
    "currys.co.uk",
}

FORUM_DOMAINS = {
    "reddit.com",
    "quora.com",
    "forums.tomsguide.com",
}

VIDEO_SOCIAL_DOMAINS = {
    "youtube.com",
    "youtu.be",
    "tiktok.com",
    "instagram.com",
    "facebook.com",
    "x.com",
    "twitter.com",
}

MARKETPLACE_DOMAINS = {
    "ebay.com",
    "etsy.com",
    "aliexpress.com",
    "eneba.com",
}

GENERIC_BRANDLIKE_ROOTS = {
    "support",
    "help",
    "docs",
    "manual",
    "kb",
    "blog",
    "news",
    "shop",
    "store",
    "community",
    "forum",
}


def slug_title(url_path: str) -> str:
    parts = [part for part in (url_path or "").split("/") if part]
    if not parts:
        return ""
    slug = parts[-1]
    slug = re.sub(r"\.[a-z0-9]{1,5}$", "", slug, flags=re.I)
    slug = re.sub(r"[-_]+", " ", slug)
    slug = re.sub(r"\b\d+\b", "", slug)
    slug = re.sub(r"\s+", " ", slug).strip()
    if not slug:
        return ""
    words = slug.split()
    out = []
    small = {"and", "or", "of", "the", "to", "for", "with", "in", "by"}
    for index, word in enumerate(words):
        lower = word.lower()
        if index > 0 and lower in small:
            out.append(lower)
        else:
            out.append(lower.capitalize())
    return " ".join(out)


def root_domain(hostname: str) -> str:
    host = (hostname or "").lower().strip(".")
    if not host:
        return ""
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    second_level_suffixes = {
        "co.uk", "org.uk", "gov.uk", "ac.uk",
        "com.au", "net.au", "org.au",
        "co.nz", "com.br", "com.mx",
    }
    tail = ".".join(parts[-2:])
    tail3 = ".".join(parts[-3:])
    if tail in second_level_suffixes and len(parts) >= 3:
        return tail3
    if ".".join(parts[-2:]) in second_level_suffixes and len(parts) >= 4:
        return ".".join(parts[-4:])
    return ".".join(parts[-2:])


def normalize_brand_token(brand: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (brand or "").lower())


def parse_int(value, field_name, model_name, warnings):
    text = (value or "").strip()
    if not text:
        return None
    text = text.replace(",", "")
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    warnings.append(f"{model_name}: non-numeric {field_name} value `{value}`.")
    return None


def parse_brand_mention(value: str) -> str:
    text = (value or "").strip().lower()
    counted = re.fullmatch(r"(yes|no)\s*\((\d+)\s*/\s*(\d+)\)", text)
    if counted:
        positive, total = int(counted[2]), int(counted[3])
        if total <= 0 or positive > total:
            return "Unknown"
        if (counted[1] == "no" and positive != 0) or (counted[1] == "yes" and positive == 0):
            return "Unknown"
        return "No" if positive == 0 else "Yes" if positive == total else "Mixed"
    if text in {"yes", "y", "true"}:
        return "Yes"
    if text in {"no", "n", "false"}:
        return "No"
    return "Unknown"


def parse_citation_spec(spec: str) -> tuple[str, str]:
    if "=" not in spec:
        raise ValueError(f"Invalid --citation value `{spec}`. Expected Model=path.")
    model, path = spec.split("=", 1)
    model = model.strip()
    path = path.strip().strip('"')
    if not model or not path:
        raise ValueError(f"Invalid --citation value `{spec}`. Expected Model=path.")
    return model, path


def normalize_url(raw_url: str) -> dict:
    raw = (raw_url or "").strip()
    parsed = urlsplit(raw)
    scheme = (parsed.scheme or "https").lower()
    hostname = (parsed.hostname or "").lower()
    port = f":{parsed.port}" if parsed.port else ""
    netloc = hostname + port
    path = parsed.path or "/"
    if path != "/":
        path = re.sub(r"/+$", "", path) or "/"
    fragment = parsed.fragment or ""
    filtered_pairs = []
    removed_params = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key.lower() in TRACKING_PARAMS:
            removed_params.append(key)
            continue
        filtered_pairs.append((key, value))
    query = urlencode(filtered_pairs, doseq=True)
    canonical_url = urlunsplit((scheme, netloc, path, query, ""))
    page_family_key = urlunsplit((scheme, netloc, path, "", ""))
    return {
        "raw_url": raw,
        "canonical_url": canonical_url,
        "domain": hostname,
        "root_domain": root_domain(hostname),
        "path": path,
        "url_fragment": fragment,
        "has_fragment": bool(fragment),
        "page_family_key": page_family_key,
        "removed_query_params": removed_params,
    }


def page_type_for(domain_name: str, root_name: str, path: str, owned: bool, brand_token: str) -> str:
    joined = f"{domain_name}{path}".lower()
    root_name = (root_name or "").lower()
    editorial_buying = re.search(r"\b(best|guide|buying|vs|versus|compare|comparison|roundup)\b", joined)
    editorial_review = re.search(r"\breview(s)?\b", joined)
    manufacturer_like = re.search(r"/(product|products|shop|store|collections|compare|support/|headphones|earbuds|speakers|monitors|laptops|phones|software)/", path.lower())
    if owned:
        return "brand_owned"
    if root_name in FORUM_DOMAINS or domain_name in FORUM_DOMAINS:
        return "forum_community"
    if root_name in VIDEO_SOCIAL_DOMAINS or domain_name in VIDEO_SOCIAL_DOMAINS:
        return "video_social"
    if root_name in RETAILER_DOMAINS or domain_name in RETAILER_DOMAINS:
        return "retailer"
    if root_name in MARKETPLACE_DOMAINS or domain_name in MARKETPLACE_DOMAINS:
        return "marketplace"
    if any(token in joined for token in ("/support", "/help", "/docs", "/manual", "/faq", "support.", "help.")):
        return "support_docs"
    if root_name in PUBLISHER_REVIEW_DOMAINS or domain_name in PUBLISHER_REVIEW_DOMAINS or editorial_buying or editorial_review:
        if editorial_buying:
            return "publisher_buying_guide"
        return "publisher_review"
    brandish = root_name.split(".")[0]
    if (
        brandish
        and brandish not in GENERIC_BRANDLIKE_ROOTS
        and brand_token not in brandish
        and not re.search(r"(news|review|guide|market|shop|store|forum|community|support)", brandish)
        and manufacturer_like
    ):
        if len(brandish) <= 24:
            return "competitor_owned"
    return "unknown"


def opportunity_type_for(page: dict, total_models: int) -> str:
    spam = page.get("Spam Score")
    brand_status = page["brand_mentioned_status"]
    model_count = page["model_count"]
    if spam is not None and spam > 30:
        return "spam_or_quality_risk"
    if page["owned_domain"]:
        return "owned_page_visibility_asset"
    if page["page_type"] == "competitor_owned" and brand_status in {"No", "Mixed", "Unknown"}:
        return "competitor_citation_threat"
    if brand_status == "No":
        if total_models >= 3 and model_count == total_models:
            return "all_model_inclusion_opportunity"
        if model_count >= 2:
            return "cross_model_inclusion_opportunity"
        return "citation_inclusion_opportunity"
    if brand_status in {"Mixed", "Unknown"}:
        if model_count >= 2:
            return "cross_model_inclusion_opportunity"
        return "citation_inclusion_opportunity"
    if brand_status == "Yes" and page["cited_in_prompts_total_deduped"] >= 2:
        return "citation_amplification_opportunity"
    return "low_priority_or_watch"


def log_score(value: int | None, max_value: int, weight: float) -> float:
    if not value or value <= 0 or max_value <= 0:
        return 0.0
    return weight * (math.log1p(value) / math.log1p(max_value))


def page_type_bonus(page_type: str) -> int:
    return {
        "publisher_review": 5,
        "publisher_buying_guide": 5,
        "retailer": 4,
        "forum_community": 3,
        "video_social": 2,
        "competitor_owned": 2,
    }.get(page_type, 0)


def score_page(page: dict, total_models: int, max_prompt_count: int, max_linking_pages: int) -> int:
    score = 0.0
    brand_status = page["brand_mentioned_status"]
    if brand_status == "No":
        score += 30
    elif brand_status in {"Mixed", "Unknown"}:
        score += 15

    model_count = page["model_count"]
    if total_models >= 2 and model_count == total_models:
        score += 20
    elif model_count >= 2:
        score += 12
    elif model_count == 1:
        score += 4

    score += log_score(page["cited_in_prompts_total_deduped"], max_prompt_count, 15)
    score += log_score(page.get("Linking Pages") or 0, max_linking_pages, 15)

    pa = page.get("PA Score")
    if pa is not None:
        if pa >= 60:
            score += 10
        elif pa >= 45:
            score += 7
        elif pa >= 30:
            score += 4
        else:
            score += 1

    spam = page.get("Spam Score")
    if spam is not None:
        if spam <= 3:
            score += 5
        elif spam <= 10:
            score += 2
        elif spam <= 30:
            score -= 5
        else:
            score -= 15

    score += page_type_bonus(page["page_type"])

    if brand_status == "Yes":
        score -= 10
    if page["owned_domain"]:
        score = max(5, min(score - 15, 45))
    if page["page_type"] == "competitor_owned":
        score -= 3
    return max(0, min(100, int(round(score))))


def confidence_for(page: dict) -> str:
    spam = page.get("Spam Score")
    if spam is not None and spam > 30:
        return "low"
    if page["brand_mentioned_status"] in {"Mixed", "Unknown"}:
        return "medium"
    if page["model_count"] >= 2 and (page.get("PA Score") or 0) >= 45:
        return "high"
    if page["cited_in_prompts_total_deduped"] >= 3:
        return "high"
    return "medium"


def owner_for(page: dict) -> str:
    mapping = {
        "publisher_review": "Digital PR",
        "publisher_buying_guide": "Digital PR",
        "retailer": "Retail / Channel",
        "forum_community": "Content",
        "video_social": "Partnerships",
        "marketplace": "Retail / Channel",
        "support_docs": "SEO",
        "brand_owned": "Content",
        "competitor_owned": "SEO",
        "unknown": "SEO",
    }
    return mapping.get(page["page_type"], "SEO")


def effort_for(page: dict) -> str:
    if page["page_type"] == "competitor_owned":
        return "High"
    if page["page_type"] in {"publisher_review", "publisher_buying_guide", "retailer", "video_social"}:
        return "Medium"
    return "Low"


def citation_topic_phrase(page: dict) -> str:
    topic = (page.get("derived_report_topic") or "").strip()
    if not topic or topic == "Unknown / needs mapping":
        return "the cited theme"
    return topic


def recommended_action_for(page: dict) -> str:
    page_type = page["page_type"]
    opportunity = page["opportunity_type"]
    topic = citation_topic_phrase(page)
    models = ", ".join(page.get("models_cited", [])) or "the analyzed models"
    if opportunity == "spam_or_quality_risk":
        return "Do not prioritize outreach. Keep as a low-confidence or quality-risk citation unless the source becomes strategically important later."
    if opportunity == "owned_page_visibility_asset":
        return "Defend and refresh this cited owned asset so it remains accurate, current, and answer-ready."
    if page_type in {"publisher_review", "publisher_buying_guide"} and page["brand_mentioned_status"] != "Yes":
        return "Pitch or brief the publisher with updated product proof points, comparison angles, and answer-ready language for the relevant buying-guide topic."
    if page_type == "retailer" and page["brand_mentioned_status"] != "Yes":
        return "Update retailer syndication copy, product modules, comparison copy, and review/Q&A content so the brand is represented where models already cite the retailer."
    if page_type == "forum_community":
        return "Monitor discussion themes and consider community-safe education content. Do not treat this as standard outreach."
    if page_type == "competitor_owned":
        return "Monitor as a citation threat. Build owned comparison content and third-party proof to offset competitor-controlled visibility."
    if page["brand_mentioned_status"] == "Yes":
        return "Reinforce the brand mention with fresher proof points, cleaner comparison framing, and updated answer-ready language on the cited page or adjacent assets."
    if page_type == "support_docs":
        return (
            f"Use this support-style source as a fact-pattern check for {topic}, then refresh owned comparison or help content so the brand has clearer evidence in {models}."
        )
    if page_type == "retailer":
        return (
            f"Treat this retailer citation as a merchandising gap for {topic}; improve syndication copy, comparison modules, and review/Q&A language before the next retest."
        )
    return (
        f"Review whether this source is materially shaping {topic} answers in {models}. If it is, prepare a targeted influence brief or adjacent owned proof update before the next retest."
    )


def domain_action_for(summary: dict) -> str:
    top_type = summary.get("top_page_type") or "unknown"
    if summary["owned_domain"]:
        return "Refresh and defend owned cited assets so the pages that already influence AI answers stay current."
    if top_type in {"publisher_review", "publisher_buying_guide"}:
        return "Treat this domain as a publisher outreach target with a focused brief tied to the cited themes and missing brand mentions."
    if top_type == "retailer":
        return "Treat this domain as a retailer or syndication target and improve product modules, comparison copy, and Q&A coverage."
    if top_type == "forum_community":
        return "Treat this domain as a monitoring target and look for recurring education themes rather than direct outreach."
    if top_type == "competitor_owned":
        return "Treat this domain as a competitor-owned citation threat and offset it with owned comparison assets plus third-party proof."
    return "Review the highest-scoring cited pages on this domain and decide whether outreach, syndication, or monitoring is the right influence motion."


def derived_report_topic_for(page: dict) -> tuple[str, str]:
    text = " ".join([
        page.get("page_title", ""),
        page.get("path", "").replace("/", " "),
        page.get("root_domain", ""),
        page.get("page_type", "").replace("_", " "),
    ]).lower()
    patterns = [
        ("pricing and comparison", r"\b(vs|versus|compare|comparison|price|pricing|budget|value|premium|worth)\b"),
        ("noise cancellation and ANC", r"\b(anc|noise cancel|noise[-\s]?cancell)\b"),
        ("sound quality and audio features", r"\b(sound|audio|bass|treble|audiophile|hi[-\s]?fi)\b"),
        ("comfort and fit", r"\b(comfort|fit|wear|ear tip|headband|glasses)\b"),
        ("travel and commute", r"\b(travel|commut|flight|airplane|office)\b"),
        ("calls and work", r"\b(call|calls|microphone|mic|zoom|teams|meeting|work)\b"),
        ("battery and durability", r"\b(battery|runtime|charge|charging|durab|build quality|waterproof|ipx)\b"),
        ("ecosystem and connectivity", r"\b(bluetooth|multipoint|connect|pair|ecosystem|android|iphone|ios|usb)\b"),
        ("fitness/gaming/lifestyle", r"\b(fitness|workout|gym|running|gaming|lifestyle|sleep)\b"),
        ("audiences and segments", r"\b(for\s+[a-z]+|student|enterprise|business|agency|team|kids|travelers?)\b"),
        ("general category queries", r"\b(best|top|review|reviews|buying guide|headphones|earbuds|software|platform|tool|tools)\b"),
    ]
    for topic, pattern in patterns:
        if re.search(pattern, text):
            return topic, "heuristic"
    return "general category queries", "fallback"


def derived_prompt_cluster_for(page: dict, report_topic: str) -> str:
    page_type = page.get("page_type", "")
    if page_type == "competitor_owned":
        return "Competitor comparison surface"
    if page_type == "brand_owned":
        return "Owned content defense"
    if page_type == "retailer":
        return "Retailer and syndication"
    if page_type in {"publisher_review", "publisher_buying_guide"}:
        return "Publisher review coverage"
    if page_type == "forum_community":
        return "Community discussion"
    if page_type == "support_docs":
        return "Support documentation"
    if page_type == "unknown":
        return "General reference surface"
    return report_topic.title()


def action_type_for(page: dict) -> str:
    opportunity = page.get("opportunity_type", "")
    page_type = page.get("page_type", "")
    if opportunity == "owned_page_visibility_asset":
        return "Owned-page defense"
    if opportunity == "competitor_citation_threat" or page_type == "competitor_owned":
        return "Competitor-owned watch"
    if opportunity == "spam_or_quality_risk":
        return "Monitor only"
    if page_type in {"publisher_review", "publisher_buying_guide"}:
        if re.search(r"\b(review|reviews|best|top|buying guide)\b", (page.get("page_title") or "").lower()):
            return "Reviewer brief"
        return "Publisher outreach"
    if page_type in {"retailer", "brand_owned", "support_docs"}:
        return "SERP/content refresh"
    if page_type == "forum_community":
        return "Monitor only"
    return "Publisher outreach"


@dataclass
class CitationRow:
    model: str
    raw_url: str
    canonical_url: str
    domain: str
    root_domain: str
    path: str
    url_fragment: str
    has_fragment: bool
    page_family_key: str
    removed_query_params: list[str]
    cited_in_prompts: int | None
    brand_mentioned: str
    pa_score: int | None
    spam_score: int | None
    linking_pages: int | None


def load_citation_file(model: str, path: str, warnings: list[str], global_warnings: list[str]) -> list[CitationRow]:
    with open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        expected = {
            "Pages",
            "Cited in Prompts",
            "Your brand mentioned",
            "PA Score",
            "Spam Score",
            "Linking Pages",
        }
        header_map = {name.strip().lower(): name for name in fieldnames}
        aliases = {name: header_map.get(name.lower()) for name in expected}
        aliases["Pages"] = header_map.get("pages") or header_map.get("page")
        missing = [name for name in expected if not aliases[name]]
        if missing:
            raise ValueError(f"{path}: missing required columns {missing}.")
        rows = []
        for raw in reader:
            raw = {name: raw.get(actual) for name, actual in aliases.items()}
            url = (raw.get("Pages") or "").strip()
            if not url:
                continue
            info = normalize_url(url)
            rows.append(CitationRow(
                model=model,
                raw_url=info["raw_url"],
                canonical_url=info["canonical_url"],
                domain=info["domain"],
                root_domain=info["root_domain"],
                path=info["path"],
                url_fragment=info["url_fragment"],
                has_fragment=info["has_fragment"],
                page_family_key=info["page_family_key"],
                removed_query_params=info["removed_query_params"],
                cited_in_prompts=parse_int(raw.get("Cited in Prompts"), "Cited in Prompts", model, warnings),
                brand_mentioned=parse_brand_mention(raw.get("Your brand mentioned")),
                pa_score=parse_int(raw.get("PA Score"), "PA Score", model, warnings),
                spam_score=parse_int(raw.get("Spam Score"), "Spam Score", model, warnings),
                linking_pages=parse_int(raw.get("Linking Pages"), "Linking Pages", model, warnings),
            ))
        if not rows:
            warnings.append(f"{model}: citation export is empty.")
        if all(row.brand_mentioned == "Unknown" for row in rows) and rows:
            warnings.append(f"{model}: all rows are missing brand mention values.")
        if len(rows) < 5 and rows:
            warnings.append(f"{model}: suspiciously low citation row count ({len(rows)}).")
        duplicate_rows = sum(1 for row in rows if row.has_fragment)
        if duplicate_rows:
            warnings.append(f"{model}: {duplicate_rows} rows include URL fragments and were normalized for deduplication.")
        if model.lower() == "gemini":
            heavy = Counter(row.page_family_key for row in rows if row.has_fragment)
            if heavy:
                worst_key, worst_count = heavy.most_common(1)[0]
                global_warnings.append(
                    f"Gemini fragment dedupe applied; the heaviest page family produced {worst_count} fragment rows for {worst_key}."
                )
        return rows


def aggregate_model_rows(rows: list[CitationRow]) -> dict[str, dict]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row.model, row.canonical_url)].append(row)
    out = {}
    for (model, canonical_url), items in grouped.items():
        brand_values = {item.brand_mentioned for item in items if item.brand_mentioned != "Unknown"}
        if brand_values == {"Yes"}:
            brand_status = "Yes"
        elif brand_values == {"No"}:
            brand_status = "No"
        elif brand_values:
            brand_status = "Mixed"
        else:
            brand_status = "Unknown"
        out[(model, canonical_url)] = {
            "model": model,
            "canonical_url": canonical_url,
            "raw_urls": [item.raw_url for item in items],
            "domain": items[0].domain,
            "root_domain": items[0].root_domain,
            "path": items[0].path,
            "page_family_key": items[0].page_family_key,
            "cited_in_prompts_max": max(item.cited_in_prompts or 0 for item in items),
            "cited_in_prompts_sum_raw": sum(item.cited_in_prompts or 0 for item in items),
            "raw_duplicate_count": len(items),
            "fragment_count": sum(1 for item in items if item.has_fragment),
            "brand_status": brand_status,
            "brand_values_raw": [item.brand_mentioned for item in items],
            "PA Score": max((item.pa_score for item in items if item.pa_score is not None), default=None),
            "Spam Score": max((item.spam_score for item in items if item.spam_score is not None), default=None),
            "Linking Pages": max((item.linking_pages for item in items if item.linking_pages is not None), default=None),
            "removed_query_params": sorted({param for item in items for param in item.removed_query_params}),
            "url_fragments": [item.url_fragment for item in items if item.url_fragment],
        }
    return out


def model_trend_note(trend: dict) -> str:
    page_mix = trend.get("page_type_mix", {})
    if not page_mix:
        return "No strong citation pattern surfaced in this model."
    top_type = max(page_mix.items(), key=lambda item: item[1])[0]
    duplicate_count = trend.get("duplicate_count", 0)
    if duplicate_count and trend["model"].lower() == "gemini":
        return f"{trend['model']} shows the heaviest fragment-duplicate cleanup and leans most on {top_type.replace('_', ' ')} pages."
    return f"{trend['model']} cites {top_type.replace('_', ' ')} pages most often in this snapshot."


def citation_play_name(page_type: str, opportunity_type: str) -> str:
    if opportunity_type == "all_model_inclusion_opportunity":
        return "Close all-model citation gaps"
    if opportunity_type == "cross_model_inclusion_opportunity":
        return "Close cross-model citation gaps"
    if opportunity_type == "citation_amplification_opportunity":
        return "Defend already-cited brand mentions"
    if opportunity_type == "owned_page_visibility_asset":
        return "Defend cited owned assets"
    if opportunity_type == "competitor_citation_threat":
        return "Monitor competitor-owned citation threats"
    if page_type == "retailer":
        return "Strengthen retailer and syndication proof"
    if page_type in {"publisher_review", "publisher_buying_guide"}:
        return "Earn inclusion on high-authority review pages"
    return "Expand citation influence coverage"


def citation_group_label(page_type: str) -> str:
    mapping = {
        "publisher_review": "publisher review",
        "publisher_buying_guide": "buying-guide",
        "retailer": "retailer",
        "marketplace": "marketplace",
        "forum_community": "community discussion",
        "video_social": "video and social",
        "competitor_owned": "competitor-owned",
        "support_docs": "support-documentation",
        "brand_owned": "owned-page",
        "unknown": "reference-page",
    }
    return mapping.get(page_type, page_type.replace("_", " ") or "reference-page")


def citation_language_angle(page: dict) -> str:
    page_type = page["page_type"]
    if page_type == "retailer":
        return "Answer-ready product proof, comparison copy, and review/Q&A language that helps retailer pages surface the brand cleanly."
    if page_type in {"publisher_review", "publisher_buying_guide"}:
        return "Evidence-led comparison language with product proof points, clear category framing, and reasons the brand deserves inclusion."
    if page_type == "owned_page_visibility_asset":
        return "Refresh answer-ready proof and comparison framing so the cited owned page stays current."
    return "Tighter answer-ready language around the cited theme, grounded in the page type that already influences model answers."


def build_citation_plays(pages: list[dict]) -> list[dict]:
    grouped = {}
    eligible = [page for page in pages if page["opportunity_type"] != "spam_or_quality_risk" and page["citation_opportunity_score"] >= 35]
    for page in eligible:
        key = (page["opportunity_type"], page["page_type"])
        grouped.setdefault(key, {
            "pages": [],
            "models": set(),
            "domains": Counter(),
            "scores": [],
            "owners": Counter(),
            "effort": Counter(),
            "confidence": Counter(),
        })
        group = grouped[key]
        group["pages"].append(page)
        group["models"].update(page["models_cited"])
        group["domains"][page["root_domain"]] += 1
        group["scores"].append(page["citation_opportunity_score"])
        group["owners"][page["owner"]] += 1
        group["effort"][page["effort"]] += 1
        group["confidence"][page["confidence"]] += 1

    plays = []
    for (opportunity_type, page_type), group in grouped.items():
        ranked_pages = sorted(group["pages"], key=lambda item: (-item["citation_opportunity_score"], -item["model_count"], item["canonical_url"]))
        top_page = ranked_pages[0]
        top_domains = [domain for domain, _ in group["domains"].most_common(3)]
        score = min(100, int(round(sum(group["scores"]) / max(1, len(group["scores"])) + min(len(ranked_pages), 4) * 2)))
        page_group = citation_group_label(page_type)
        if len(ranked_pages) == 1:
            why_it_matters = (
                f"One cited page in the {page_group} group influences "
                f"{', '.join(sorted(group['models'])) or 'the analyzed models'}, and the clearest source to review is "
                f"{top_domains[0] if top_domains else top_page['root_domain']}."
            )
        else:
            why_it_matters = (
                f"{len(ranked_pages)} cited pages in the {page_group} group influence "
                f"{', '.join(sorted(group['models'])) or 'the analyzed models'}, and the top opportunities "
                f"center on {', '.join(top_domains[:2]) or top_page['root_domain']}."
            )
        bucket = "Defend" if opportunity_type in {"citation_amplification_opportunity", "owned_page_visibility_asset"} else "Build"
        if opportunity_type == "competitor_citation_threat":
            bucket = "Verify"
        if opportunity_type == "spam_or_quality_risk":
            bucket = "Retire"
        plays.append({
            "play_type": "citation",
            "play_name": citation_play_name(page_type, opportunity_type),
            "bucket": bucket,
            "topic": top_page.get("derived_report_topic", "Citation opportunities"),
            "prompt_cluster": top_page.get("derived_prompt_cluster", page_type.replace("_", " ")),
            "affected_models": sorted(group["models"]),
            "competitor_threat": top_domains if page_type == "competitor_owned" else [],
            "why_it_matters": why_it_matters,
            "recommended_assets": "Publisher brief, product proof sheet, comparison language, syndication copy",
            "recommended_asset_type": "Citation influence brief",
            "example_language_angle": citation_language_angle(top_page),
            "execution_notes": top_page["recommended_action"],
            "action_type": top_page.get("action_type", ""),
            "priority_score": score,
            "opportunity_score": score if bucket in {"Build", "Reclaim", "Verify"} else "",
            "cleanup_priority": score if bucket == "Retire" else "",
            "defense_priority": "Protected" if bucket == "Defend" else "",
            "confidence": group["confidence"].most_common(1)[0][0],
            "effort": group["effort"].most_common(1)[0][0],
            "suggested_owner": group["owners"].most_common(1)[0][0],
            "supporting_label": "Supporting pages",
            "supporting_items": [f"{page['root_domain']} - {page.get('page_title') or page.get('page_type', '').replace('_', ' ')}" for page in ranked_pages[:5]],
            "supporting_prompts": [page["canonical_url"] for page in ranked_pages[:5]],
            "top_domains": top_domains,
            "top_pages": [page["canonical_url"] for page in ranked_pages[:3]],
            "opportunity_type": opportunity_type,
        })
    plays.sort(key=lambda item: (-item["priority_score"], item["play_name"].lower()))
    return plays[:6]


def analyze_citation_files(brand: str, citations: list[tuple[str, str]], owned_domains: list[str] | None = None) -> dict:
    owned_domains = owned_domains or []
    normalized_owned = {domain.lower().strip() for domain in owned_domains if domain.strip()}
    brand_token = normalize_brand_token(brand)

    model_rows = {}
    by_model_warnings = {}
    global_warnings = []
    all_rows = []
    for model, path in citations:
        model_warning_list = []
        rows = load_citation_file(model, path, model_warning_list, global_warnings)
        model_rows[model] = rows
        by_model_warnings[model] = model_warning_list
        all_rows.extend(rows)

    if not citations:
        return {"citation_analysis": {"enabled": False, "reason": "No citation export files provided."}}

    per_model_aggregate = aggregate_model_rows(all_rows)
    canonical_groups = defaultdict(list)
    for key, value in per_model_aggregate.items():
        canonical_groups[value["canonical_url"]].append(value)

    total_models = len(citations)
    pages = []
    for canonical_url, items in canonical_groups.items():
        statuses = {item["brand_status"] for item in items if item["brand_status"] != "Unknown"}
        if statuses == {"Yes"}:
            brand_status = "Yes"
        elif statuses == {"No"}:
            brand_status = "No"
        elif statuses:
            brand_status = "Mixed"
        else:
            brand_status = "Unknown"
        first = items[0]
        root_name = first["root_domain"]
        owned = root_name in normalized_owned or first["domain"] in normalized_owned or (brand_token and brand_token in root_name.replace(".", ""))
        page_type = page_type_for(first["domain"], root_name, first["path"], owned, brand_token)
        page = {
            "canonical_url": canonical_url,
            "raw_url": first["raw_urls"][0],
            "root_domain": root_name,
            "domain": first["domain"],
            "path": first["path"],
            "page_family_key": first["page_family_key"],
            "page_title": slug_title(first["path"]),
            "models_cited": sorted(item["model"] for item in items),
            "model_count": len(items),
            "cited_in_prompts_total_deduped": sum(item["cited_in_prompts_max"] for item in items),
            "cited_in_prompts_by_model": {item["model"]: item["cited_in_prompts_max"] for item in items},
            "cited_in_prompts_sum_raw": sum(item["cited_in_prompts_sum_raw"] for item in items),
            "raw_duplicate_count": sum(item["raw_duplicate_count"] for item in items),
            "fragment_count": sum(item["fragment_count"] for item in items),
            "brand_mentioned_any": any(item["brand_status"] in {"Yes", "Mixed"} for item in items),
            "brand_mentioned_all": all(item["brand_status"] == "Yes" for item in items),
            "brand_mentioned_status": brand_status,
            "PA Score": max((item["PA Score"] for item in items if item["PA Score"] is not None), default=None),
            "Spam Score": max((item["Spam Score"] for item in items if item["Spam Score"] is not None), default=None),
            "Linking Pages": max((item["Linking Pages"] for item in items if item["Linking Pages"] is not None), default=None),
            "owned_domain": owned,
            "page_type": page_type,
            "removed_query_params": sorted({param for item in items for param in item["removed_query_params"]}),
            "url_fragments": [frag for item in items for frag in item["url_fragments"]],
            "notes": "",
        }
        report_topic, mapping_confidence = derived_report_topic_for(page)
        page["derived_report_topic"] = report_topic
        page["derived_prompt_cluster"] = derived_prompt_cluster_for(page, report_topic)
        page["mapping_confidence"] = mapping_confidence
        pages.append(page)

    max_prompt_count = max((page["cited_in_prompts_total_deduped"] for page in pages), default=0)
    max_linking_pages = max((page.get("Linking Pages") or 0 for page in pages), default=0)
    for page in pages:
        page["opportunity_type"] = opportunity_type_for(page, total_models)
        page["citation_opportunity_score"] = score_page(page, total_models, max_prompt_count, max_linking_pages)
        page["recommended_action"] = recommended_action_for(page)
        page["action_type"] = action_type_for(page)
        page["confidence"] = confidence_for(page)
        page["owner"] = owner_for(page)
        page["effort"] = effort_for(page)
        page["source_evidence_reference"] = (
            f"{page['root_domain']} | {page.get('page_title') or page.get('page_type', '').replace('_', ' ')} | "
            f"{page.get('cited_in_prompts_total_deduped', 0)} cited prompts"
        )
        note_bits = []
        if page["fragment_count"]:
            note_bits.append(f"{page['fragment_count']} fragment duplicate(s) normalized.")
        if page["brand_mentioned_status"] == "Mixed":
            note_bits.append("Brand mention status is mixed across duplicates or models; QA recommended.")
        if page.get("Spam Score") is not None and page["Spam Score"] > 30:
            note_bits.append("High spam score.")
        if page["mapping_confidence"] == "fallback":
            note_bits.append("Prompt-cluster linkage is heuristic and needs review.")
        page["notes"] = " ".join(note_bits)

    pages.sort(key=lambda item: (-item["citation_opportunity_score"], -item["model_count"], -item["cited_in_prompts_total_deduped"], item["canonical_url"]))

    domains = []
    pages_by_domain = defaultdict(list)
    for page in pages:
        pages_by_domain[page["root_domain"]].append(page)
    for root_name, domain_pages in pages_by_domain.items():
        page_types = Counter(page["page_type"] for page in domain_pages)
        without_brand = [page for page in domain_pages if page["brand_mentioned_status"] == "No"]
        with_brand = [page for page in domain_pages if page["brand_mentioned_status"] == "Yes"]
        score = int(round(
            min(100, (
                sum(page["citation_opportunity_score"] for page in sorted(domain_pages, key=lambda item: -item["citation_opportunity_score"])[:3]) / max(1, min(len(domain_pages), 3))
                + min(len({model for page in domain_pages for model in page["models_cited"]}) * 5, 15)
                + min((100 * len(without_brand) / max(1, len(domain_pages))) / 4, 25)
            ))
        ))
        owned = any(page["owned_domain"] for page in domain_pages)
        summary = {
            "root_domain": root_name,
            "page_count": sum(page["raw_duplicate_count"] for page in domain_pages),
            "canonical_page_count": len(domain_pages),
            "model_count": len({model for page in domain_pages for model in page["models_cited"]}),
            "models_cited": sorted({model for page in domain_pages for model in page["models_cited"]}),
            "total_cited_prompts_deduped": sum(page["cited_in_prompts_total_deduped"] for page in domain_pages),
            "pages_without_brand": len(without_brand),
            "pages_with_brand": len(with_brand),
            "percent_pages_without_brand": round(100 * len(without_brand) / max(1, len(domain_pages)), 1),
            "avg_PA": round(sum(page["PA Score"] for page in domain_pages if page.get("PA Score") is not None) / max(1, len([page for page in domain_pages if page.get("PA Score") is not None])), 1)
            if any(page.get("PA Score") is not None for page in domain_pages) else None,
            "avg_Spam": round(sum(page["Spam Score"] for page in domain_pages if page.get("Spam Score") is not None) / max(1, len([page for page in domain_pages if page.get("Spam Score") is not None])), 1)
            if any(page.get("Spam Score") is not None for page in domain_pages) else None,
            "total_linking_pages": sum(page.get("Linking Pages") or 0 for page in domain_pages),
            "top_page_type": page_types.most_common(1)[0][0] if page_types else "unknown",
            "owned_domain": owned,
            "domain_opportunity_score": score,
            "recommended_domain_action": "",
            "top_pages": [page["canonical_url"] for page in sorted(domain_pages, key=lambda item: -item["citation_opportunity_score"])[:3]],
        }
        summary["recommended_domain_action"] = domain_action_for(summary)
        domains.append(summary)
    domains.sort(key=lambda item: (-item["domain_opportunity_score"], -item["model_count"], item["root_domain"]))

    model_trends = []
    for model, rows in model_rows.items():
        canonical_for_model = [page for page in pages if model in page["models_cited"]]
        no_brand_pages = [page for page in canonical_for_model if page["brand_mentioned_status"] == "No"]
        yes_pages = [page for page in canonical_for_model if page["brand_mentioned_status"] == "Yes"]
        page_type_mix = Counter(page["page_type"] for page in canonical_for_model)
        top_domains = Counter(page["root_domain"] for page in canonical_for_model).most_common(5)
        top_no_brand_domains = Counter(page["root_domain"] for page in no_brand_pages).most_common(5)
        duplicate_count = sum(page["raw_duplicate_count"] - 1 for page in canonical_for_model if (page["raw_duplicate_count"] - 1) > 0)
        trend = {
            "model": model,
            "raw_rows": len(rows),
            "canonical_pages": len(canonical_for_model),
            "duplicate_count": duplicate_count,
            "fragment_duplicate_count": sum(page["fragment_count"] for page in canonical_for_model),
            "brand_mentioned_page_count": len(yes_pages),
            "no_brand_page_count": len(no_brand_pages),
            "percent_brand_mentioned_pages": round(100 * len(yes_pages) / max(1, len(canonical_for_model)), 1) if canonical_for_model else 0.0,
            "percent_no_brand_pages": round(100 * len(no_brand_pages) / max(1, len(canonical_for_model)), 1) if canonical_for_model else 0.0,
            "top_domains": [domain for domain, _ in top_domains],
            "top_no_brand_opportunity_domains": [domain for domain, _ in top_no_brand_domains],
            "average_PA": round(sum(page["PA Score"] for page in canonical_for_model if page.get("PA Score") is not None) / max(1, len([page for page in canonical_for_model if page.get("PA Score") is not None])), 1)
            if any(page.get("PA Score") is not None for page in canonical_for_model) else None,
            "average_Spam": round(sum(page["Spam Score"] for page in canonical_for_model if page.get("Spam Score") is not None) / max(1, len([page for page in canonical_for_model if page.get("Spam Score") is not None])), 1)
            if any(page.get("Spam Score") is not None for page in canonical_for_model) else None,
            "average_Linking_Pages": round(sum(page.get("Linking Pages") or 0 for page in canonical_for_model) / max(1, len(canonical_for_model)), 1) if canonical_for_model else 0.0,
            "page_type_mix": dict(page_type_mix),
            "notes": "",
        }
        trend["notes"] = model_trend_note(trend)
        model_trends.append(trend)

    pages_all_models = [page for page in pages if page["model_count"] == total_models]
    pages_two_models = [page for page in pages if page["model_count"] == 2]
    pages_one_model = [page for page in pages if page["model_count"] == 1]
    domains_all_models = [domain for domain in domains if domain["model_count"] == total_models]
    breadth_low_brand = [
        domain for domain in domains
        if domain["model_count"] >= 2 and domain["percent_pages_without_brand"] >= 50.0
    ]
    gemini_fragment_duplicates = [
        page for page in pages
        if "Gemini" in page["models_cited"] and page["fragment_count"] > 0
    ]

    summary = {
        "canonical_pages": len(pages),
        "raw_rows_total": len(all_rows),
        "no_brand_pages": len([page for page in pages if page["brand_mentioned_status"] == "No"]),
        "cross_model_no_brand_pages": len([page for page in pages if page["brand_mentioned_status"] == "No" and page["model_count"] >= 2]),
        "all_model_no_brand_pages": len([page for page in pages if page["brand_mentioned_status"] == "No" and page["model_count"] == total_models]),
        "owned_pages_cited": len([page for page in pages if page["owned_domain"]]),
        "top_page_types": dict(Counter(page["page_type"] for page in pages).most_common(5)),
        "top_opportunity_domains": [domain["root_domain"] for domain in domains[:5]],
    }

    citation_plays = build_citation_plays(pages)

    data_quality_warnings = list(global_warnings)
    for model, warnings in by_model_warnings.items():
        data_quality_warnings.extend(warnings)
    for page in pages:
        if page["brand_mentioned_status"] == "Mixed":
            data_quality_warnings.append(f"Mixed brand mention status for {page['canonical_url']}.")
            break

    citation_analysis = {
        "enabled": True,
        "brand": brand,
        "owned_domains": sorted(normalized_owned),
        "models_analyzed": [model for model, _ in citations],
        "summary": summary,
        "page_opportunities": pages,
        "domain_opportunities": domains,
        "cross_model_opportunities": {
            "pages_all_models": pages_all_models[:25],
            "pages_two_models": pages_two_models[:25],
            "pages_one_model": pages_one_model[:25],
            "domains_all_models": domains_all_models[:25],
            "breadth_low_brand_domains": breadth_low_brand[:25],
            "gemini_fragment_duplicates": gemini_fragment_duplicates[:25],
        },
        "model_trends": model_trends,
        "citation_plays": citation_plays,
        "data_quality": {
            "warnings": data_quality_warnings,
            "by_model": by_model_warnings,
        },
    }
    return {"citation_analysis": citation_analysis}


def write_cited_pages_csv(path: str, pages: list[dict]) -> None:
    fieldnames = [
        "canonical_url",
        "raw_url",
        "root_domain",
        "domain",
        "path",
        "page_title",
        "models_cited",
        "model_count",
        "cited_in_prompts_total_deduped",
        "cited_in_prompts_by_model",
        "cited_in_prompts_sum_raw",
        "raw_duplicate_count",
        "fragment_count",
        "brand_mentioned_status",
        "PA Score",
        "Spam Score",
        "Linking Pages",
        "owned_domain",
        "page_type",
        "opportunity_type",
        "citation_opportunity_score",
        "action_type",
        "owner",
        "effort",
        "confidence",
        "recommended_action",
        "derived_report_topic",
        "derived_prompt_cluster",
        "mapping_confidence",
        "source_evidence_reference",
        "notes",
    ]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for page in pages:
            row = dict(page)
            row["models_cited"] = "; ".join(page.get("models_cited", []))
            row["cited_in_prompts_by_model"] = json.dumps(page.get("cited_in_prompts_by_model", {}), ensure_ascii=False)
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def main():
    parser = argparse.ArgumentParser(description="Analyze Moz AI Visibility citation exports.")
    parser.add_argument("--brand", required=True)
    parser.add_argument("--owned-domains", nargs="*", default=[])
    parser.add_argument("--citation", action="append", default=[], help="Model=path for a citation export CSV.")
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-csv", required=True)
    args = parser.parse_args()

    citations = [parse_citation_spec(item) for item in args.citation]
    result = analyze_citation_files(args.brand, citations, owned_domains=args.owned_domains)
    citation_analysis = result["citation_analysis"]
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out_json, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)
    if citation_analysis.get("enabled"):
        write_cited_pages_csv(args.out_csv, citation_analysis["page_opportunities"])
    else:
        with open(args.out_csv, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["message"])
            writer.writerow([citation_analysis.get("reason", "No citation export files provided.")])
    print(f"Wrote {args.out_json} and {args.out_csv}")


if __name__ == "__main__":
    main()
