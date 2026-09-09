#!/usr/bin/env python3
"""
build_report.py
Render an executive-ready markdown report from AI visibility metrics JSON.

Usage:
    python build_report.py metrics.json report.md
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


def pct(value):
    return f"{float(value):.1f}%"


def titleish(text):
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


def md_table(headers, rows):
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def basename_date(path):
    match = re.search(r"\d{4}-\d{2}-\d{2}", os.path.basename(path or ""))
    return match.group(0) if match else ""


def list_labels(rows, limit=3):
    labels = [titleish(row["label"]) for row in rows[:limit] if row.get("label")]
    return ", ".join(labels) if labels else "No strong recurring pattern yet"


def list_values(items, limit=3):
    vals = [titleish(item) for item in items[:limit] if item]
    return ", ".join(vals) if vals else "None highlighted"


def stable_pick(options, *keys):
    if not options:
        return ""
    seed = "|".join(str(key or "") for key in keys)
    total = sum(ord(ch) for ch in seed)
    return options[total % len(options)]


PROMPT_WORD_STOP = {
    "a", "an", "and", "are", "as", "at", "be", "best", "by", "can", "compare", "comparison",
    "do", "does", "for", "from", "good", "how", "i", "in", "is", "it", "my", "of", "on", "or",
    "should", "the", "this", "to", "top", "vs", "versus", "what", "when", "which", "why", "with",
}
CATEGORY_HINT_WORDS = {
    "software", "tool", "tools", "platform", "platforms", "headphone", "headphones",
    "earbud", "earbuds", "listing", "listings", "management", "tracker", "tracking",
    "seo", "device", "devices", "service", "services", "solution", "solutions",
}

PHRASE_BANKS = {
    "Build": [
        "Create the missing proof layer",
        "Establish a clearer claim",
        "Give AI systems stronger evidence to include the brand",
    ],
    "Reclaim": [
        "Tighten an area where the brand should already be visible",
        "Refresh the answer pattern",
        "Recover weak-but-winnable prompt coverage",
    ],
    "Defend": [
        "Protect the narrative the brand already owns",
        "Keep proof points consistent across owned, retailer, and reviewer surfaces",
        "Hold the inclusion pattern that is already working",
    ],
    "Verify": [
        "Validate whether this is a real opportunity or noisy tracking",
        "Review manually before investing",
        "Pressure-test whether the gap deserves activation",
    ],
    "Retire": [
        "Remove from the core scorecard unless it serves a deliberate authority-tracking role",
        "Consolidate into the cleaner parent prompt",
        "Reduce tracking noise so the scorecard stays decision-useful",
    ],
    "Watch": [
        "Monitor without overcommitting resources",
        "Keep this on watch rather than turning it into a full campaign",
        "Track the pattern, but wait for stronger evidence before scaling",
    ],
    "citation": [
        "Influence the sources AI systems already trust",
        "Separate realistic outreach targets from monitor-only citations",
        "Brief publishers with answer-ready comparison language",
    ],
}


def role_label(role):
    mapping = {
        "category_leader": "Category leader",
        "category_all_rounder": "Category all-rounder",
        "sound_quality_specialist": "Sound-quality specialist",
        "value_or_budget_challenger": "Value / budget challenger",
        "enterprise_or_platform_competitor": "Enterprise platform competitor",
        "reviews_reputation_specialist": "Reviews / reputation specialist",
        "local_seo_platform_benchmark": "Local SEO platform benchmark",
        "lifestyle_or_use_case_competitor": "Lifestyle / use-case competitor",
        "niche_specialist": "Niche specialist",
    }
    return mapping.get(role or "", titleish((role or "").replace("_", " ")))


def human_intent(label):
    mapping = {
        "support_or_how_to": "support/how-to",
        "feature_attribute": "feature/attribute",
        "use_case": "use-case",
        "local_business": "local business",
        "head_term": "head term",
        "persona": "persona",
    }
    return mapping.get(label, titleish(label))


def brand_position(model, brand):
    sov = model["share_of_voice_pct"]
    brand_sov = float(sov.get(brand, 0.0))
    max_sov = max((float(v) for v in sov.values()), default=0.0)
    leaders = sorted([name for name, value in sov.items() if abs(float(value) - max_sov) < 0.05], key=str.lower)
    if brand in leaders and len(leaders) == 1:
        return "lead", leaders[0], 0.0
    if brand in leaders:
        others = [name for name in leaders if name != brand]
        return "tie", " / ".join([brand] + others), 0.0
    leader = leaders[0] if leaders else model["leader"]
    gap = round(max_sov - brand_sov, 1)
    return "trail", leader, gap


def model_topic_rows(metrics):
    brand = metrics["brand"]
    source = metrics["topic_mapping"]["report_topics_source"]
    topics = metrics.get("report_topics") or metrics["topics"]
    recs = metrics["recommendations"]
    bucket_by_topic = defaultdict(Counter)
    topic_field = "report_topic" if source == "fallback" else "primary_topic"
    for rec in recs:
        topic = rec.get(topic_field) or rec.get("primary_topic") or "general category queries"
        bucket_by_topic[topic][rec["action_bucket"]] += 1

    rows = []
    for topic in topics:
        for model in metrics["per_model"]:
            coverage = (
                model["report_topic_coverage"].get(topic, {})
                if source == "fallback"
                else model["topic_coverage"].get(topic, {})
            )
            if coverage.get("prompts", 0) <= 0:
                continue
            avg_rank = coverage["average_rank"] if coverage["average_rank"] is not None else "-"
            action_bucket = bucket_by_topic[topic].most_common(1)[0][0] if bucket_by_topic[topic] else "Watch"
            rows.append([
                titleish(topic),
                model["model"],
                coverage["prompts"],
                f"{pct(coverage['visibility_rate_pct'])} ({avg_rank})",
                coverage["weak_or_absent"],
                action_bucket,
            ])
    return rows


def topic_strengths(metrics):
    source = metrics["topic_mapping"]["report_topics_source"]
    scores = []
    for topic in metrics.get("report_topics") or metrics["topics"]:
        weighted_vis = 0.0
        total_prompts = 0
        for model in metrics["per_model"]:
            cov = (
                model["report_topic_coverage"].get(topic, {})
                if source == "fallback"
                else model["topic_coverage"].get(topic, {})
            )
            prompts = cov.get("prompts", 0)
            if prompts <= 0:
                continue
            weighted_vis += cov["visibility_rate_pct"] * prompts
            total_prompts += prompts
        if total_prompts > 0:
            scores.append((topic, weighted_vis / total_prompts, total_prompts))
    if not scores:
        return None, None
    scores.sort(key=lambda item: (-item[1], -item[2], item[0]))
    strongest = scores[0]
    weakest = sorted(scores, key=lambda item: (item[1], -item[2], item[0]))[0]
    return strongest, weakest


def aggregate_records(records, models, field, limit=None):
    groups = defaultdict(lambda: {
        "prompts": 0,
        "slot_total": 0,
        "slot_present": 0,
        "ranks": [],
        "weak_or_absent_prompts": 0,
    })
    for record in records:
        key = record.get(field) or "Unclassified"
        group = groups[key]
        group["prompts"] += 1
        prompt_has_weak = False
        for model in models:
            status = record.get(f"status_{model}", "")
            rank = record.get(f"rank_{model}", "")
            if status:
                group["slot_total"] += 1
                if status in {"strong", "weak_present"}:
                    group["slot_present"] += 1
                if status in {"absent", "weak_present"}:
                    prompt_has_weak = True
            if rank not in ("", None):
                group["ranks"].append(float(rank))
        if prompt_has_weak:
            group["weak_or_absent_prompts"] += 1
    rows = []
    for key, values in groups.items():
        if values["prompts"] <= 0:
            continue
        avg_rank = round(sum(values["ranks"]) / len(values["ranks"]), 2) if values["ranks"] else "-"
        visibility = 100 * values["slot_present"] / values["slot_total"] if values["slot_total"] else 0.0
        rows.append({
            "label": key,
            "prompts": values["prompts"],
            "visibility": visibility,
            "avg_rank": avg_rank,
            "weak_or_absent": values["weak_or_absent_prompts"],
        })
    rows.sort(key=lambda item: (-item["prompts"], item["visibility"], item["label"].lower()))
    return rows[:limit] if limit else rows


def confidence_effort_rows(recs):
    confidence = Counter(rec["confidence"] for rec in recs if rec["priority_score"] > 0)
    effort = Counter(rec["effort"] for rec in recs if rec["priority_score"] > 0)
    return (
        [[titleish(label), count] for label, count in confidence.most_common()],
        [[titleish(label), count] for label, count in effort.most_common()],
    )


def bucket_summary_rows(recs):
    grouped = defaultdict(list)
    for rec in recs:
        grouped[rec["action_bucket"]].append(rec)
    rows = []
    for bucket in ["Defend", "Reclaim", "Build", "Verify", "Retire"]:
        items = grouped.get(bucket, [])
        avg_score = round(sum(item["priority_score"] for item in items if item["priority_score"] > 0) / max(1, len([i for i in items if i["priority_score"] > 0])), 1) if items else "-"
        typical_effort = Counter(item["effort"] for item in items if item.get("effort")).most_common(1)
        rows.append([
            bucket,
            len(items),
            avg_score,
            typical_effort[0][0] if typical_effort else "-",
        ])
    return rows


def executive_next_moves(recs):
    defend = next((rec for rec in recs if rec["action_bucket"] == "Defend"), None)
    reclaim_build = next((rec for rec in recs if rec["action_bucket"] in {"Reclaim", "Build"} and rec["priority_score"] > 0), None)
    portfolio = next((rec for rec in recs if rec["action_bucket"] == "Retire"), None)
    moves = []
    if defend:
        moves.append(("Defend", defend["recommended_action"]))
    if reclaim_build:
        moves.append((reclaim_build["action_bucket"], reclaim_build["recommended_action"]))
    if portfolio:
        moves.append(("Portfolio", portfolio["recommended_action"]))
    return moves


def score_display(play):
    if play["bucket"] == "Defend":
        return play.get("defense_priority") or "Protected"
    if play["bucket"] == "Retire":
        return play.get("cleanup_priority") or play.get("priority_score", "")
    return play.get("opportunity_score") or play.get("priority_score", "")


def bucket_matrix_rows(recs):
    grouped = defaultdict(list)
    for rec in recs:
        grouped[rec["action_bucket"]].append(rec)
    rows = []
    for bucket in ["Defend", "Reclaim", "Build", "Verify", "Retire"]:
        items = grouped.get(bucket, [])
        scored = [item for item in items if item["priority_score"] not in ("", None)]
        if bucket in {"Build", "Reclaim", "Verify"}:
            score_label = round(sum(item.get("opportunity_score", 0) or 0 for item in items if item.get("opportunity_score") not in ("", None)) / max(1, len([i for i in items if i.get("opportunity_score") not in ("", None)])), 1) if items else "-"
        elif bucket == "Defend":
            score_label = "Protected"
        else:
            cleanup_vals = [item.get("cleanup_priority", 0) or 0 for item in items if item.get("cleanup_priority") not in ("", None)]
            score_label = round(sum(cleanup_vals) / len(cleanup_vals), 1) if cleanup_vals else "-"
        typical_effort = Counter(item["effort"] for item in items if item.get("effort")).most_common(1)
        rows.append([bucket, len(items), score_label, typical_effort[0][0] if typical_effort else "-"])
    return rows


def strongest_defend_move(metrics, recs):
    source = metrics["topic_mapping"]["report_topics_source"]
    per_model = metrics["per_model"]
    defend_recs = [rec for rec in recs if rec["action_bucket"] == "Defend"]
    if not defend_recs:
        return None
    scores = []
    for topic in metrics.get("report_topics") or metrics["topics"]:
        weighted_vis = 0.0
        total_prompts = 0
        for model in per_model:
            cov = model["report_topic_coverage"].get(topic, {}) if source == "fallback" else model["topic_coverage"].get(topic, {})
            prompts = cov.get("prompts", 0)
            if prompts <= 0:
                continue
            weighted_vis += cov["visibility_rate_pct"] * prompts
            total_prompts += prompts
        if total_prompts:
            scores.append((topic, weighted_vis / total_prompts))
    scores.sort(key=lambda item: (-item[1], item[0]))
    topic = scores[0][0] if scores else (defend_recs[0].get("report_topic") or defend_recs[0].get("primary_topic"))
    return f"Defend {titleish(topic)} by keeping proof points, retailer copy, and reviewer briefs aligned around the strongest high-visibility narrative."


def portfolio_next_move(recs):
    cleanup = [rec for rec in recs if rec["action_bucket"] == "Retire"]
    if not cleanup:
        return None
    top = max(cleanup, key=lambda item: item.get("cleanup_priority", 0) or 0)
    target = titleish(top.get("prompt_cluster") or top.get("report_topic") or top["prompt"])
    next_step = (top.get("next_step") or "").strip()
    if next_step == "Consolidate prompt tracking":
        return f"Consolidate {target} prompt tracking first."
    if next_step:
        return f"{next_step} for {target} first."
    return f"Review {target} cleanup first."


def growth_next_move(plays):
    growth = [play for play in plays if play["bucket"] in {"Build", "Reclaim", "Verify"}]
    if not growth:
        return None
    top = growth[0]
    return f"{top['play_name']}: {top['execution_notes']}"


def asset_display(asset_type, supporting_assets):
    asset_type = (asset_type or "").strip()
    supporting_assets = (supporting_assets or "").strip()
    if asset_type and supporting_assets:
        lowered_assets = supporting_assets.lower()
        lowered_type = asset_type.lower()
        if lowered_assets.startswith(lowered_type):
            supporting_assets = supporting_assets[len(asset_type):].lstrip(" ,;|")
            if supporting_assets:
                supporting_assets = supporting_assets[0].lower() + supporting_assets[1:]
        if supporting_assets:
            return f"Asset type: {asset_type}. Supporting assets: {supporting_assets}"
        return f"Asset type: {asset_type}."
    if asset_type:
        return f"Asset type: {asset_type}."
    if supporting_assets:
        return f"Supporting assets: {supporting_assets}"
    return "No asset recommendation highlighted."


def citation_page_type_label(page_type):
    mapping = {
        "publisher_review": "Publisher review",
        "publisher_buying_guide": "Buying guide",
        "retailer": "Retailer",
        "marketplace": "Marketplace",
        "forum_community": "Community / forum",
        "video_social": "Video / social",
        "competitor_owned": "Competitor-owned page",
        "support_docs": "Support docs",
        "brand_owned": "Owned page",
        "unknown": "Reference page",
        "": "Reference page",
    }
    return mapping.get(page_type or "", titleish((page_type or "").replace("_", " ")))


def cleanup_reason_text(rec):
    gap = rec.get("gap_type")
    if gap == "tracking_cleanup_candidate":
        return "This overlaps another tracked prompt and adds limited decision-making value on its own."
    if gap == "no_recommendation_surface":
        return "The tracked brand never surfaced in the analyzed responses, so this behaves like low-signal authority tracking rather than a scorecard query."
    return rec.get("gap_summary") or "This prompt contributes limited signal in the current scorecard."


def cleanup_action_text(rec):
    if rec.get("duplicate_of"):
        return f"Merge it into `{rec['duplicate_of']}` and remove the duplicate from the core scorecard."
    cluster = titleish(rec.get("prompt_cluster") or rec.get("report_topic") or rec["prompt"])
    return f"Remove it from the core scorecard. Only keep it if you want broad authority tracking for {cluster}."


def infer_subject_phrase(records):
    counts = Counter()
    prompt_tokens = []
    for record in records:
        prompt = (record.get("prompt") or "").lower()
        tokens = re.findall(r"[a-z0-9]+", prompt)
        prompt_tokens.append(tokens)
        seen = set()
        for n in range(2, 5):
            for index in range(len(tokens) - n + 1):
                gram = tokens[index:index + n]
                if gram[0] in PROMPT_WORD_STOP:
                    continue
                if all(token in PROMPT_WORD_STOP for token in gram):
                    continue
                phrase = " ".join(gram)
                if phrase not in seen:
                    counts[phrase] += 1
                    seen.add(phrase)
    if not counts:
        return "the category"
    def phrase_score(item):
        phrase, count = item
        tokens = phrase.split()
        hint_bonus = 1 if any(token in CATEGORY_HINT_WORDS for token in tokens) else 0
        tail_bonus = 1 if tokens[-1] in CATEGORY_HINT_WORDS or (tokens[-1].endswith("s") and len(tokens[-1]) > 4) else 0
        return (count, hint_bonus, tail_bonus, len(tokens), phrase)
    phrase, _ = max(counts.items(), key=phrase_score)
    base_tokens = phrase.split()
    extensions = Counter()
    for tokens in prompt_tokens:
        for index in range(len(tokens) - len(base_tokens)):
            if tokens[index:index + len(base_tokens)] == base_tokens:
                extended = " ".join(tokens[index:index + len(base_tokens) + 1])
                extensions[extended] += 1
    if extensions:
        candidate, candidate_count = max(extensions.items(), key=phrase_score)
        if candidate_count >= 2:
            phrase = candidate
    return phrase


def topic_query_label(topic):
    normalized = re.sub(r"\s+", " ", (topic or "").strip().lower())
    mapping = {
        "sound quality and audio features": "sound quality",
        "battery and durability": "battery life and durability",
        "buying durability and accessories": "battery life and durability",
        "pricing and comparison": "value and premium tradeoffs",
        "price value and premium positioning": "value and premium tradeoffs",
        "ecosystem and connectivity": "bluetooth connectivity",
        "wireless bluetooth and connectivity": "bluetooth connectivity",
        "calls and work": "video calls and work",
        "travel and commute": "travel and commuting",
        "comfort and fit": "comfort and fit",
        "noise cancellation and anc": "noise cancellation",
        "listing management": "listing management",
        "citation management": "citation management",
        "rank tracking": "rank tracking",
        "marketing platforms": "platform breadth",
        "reporting and dashboards": "reporting and dashboards",
        "analysis and diagnostics": "diagnostics and audits",
        "reviews and reputation": "review management",
        "audiences and segments": "audience fit",
    }
    text = mapping.get(normalized, normalized.replace("/", " and ").replace("-", " "))
    return re.sub(r"\s+", " ", text)


def add_prompt_suggestions(records, recs, weak_intents, missing_topics, weakest_topic):
    existing = {re.sub(r"\s+", " ", (record.get("prompt") or "").strip().lower()) for record in records}
    subject = infer_subject_phrase(records)
    candidate_topics = []
    for rec in sorted(
        [item for item in recs if item["action_bucket"] in {"Build", "Reclaim", "Verify"}],
        key=lambda item: (-item["priority_score"], item["prompt"].lower()),
    ):
        topic = rec.get("report_topic") or rec.get("primary_topic")
        if topic and topic not in candidate_topics:
            candidate_topics.append(topic)
    for item in missing_topics:
        topic = item.get("topic")
        if topic and topic not in candidate_topics:
            candidate_topics.append(topic)
    if weakest_topic and weakest_topic[0] not in candidate_topics:
        candidate_topics.append(weakest_topic[0])
    if not candidate_topics:
        candidate_topics.append("comparison")

    templates = []
    weak_labels = [row["label"] for row in weak_intents]
    if "comparison" in weak_labels:
        templates.extend([
            "best {subject} for {topic}",
            "{subject} vs competitors on {topic}",
        ])
    if "support_or_how_to" in weak_labels:
        templates.extend([
            "how to choose {subject} for {topic}",
            "what to check before buying {subject} for {topic}",
        ])
    if not templates:
        templates.extend([
            "best {subject} for {topic}",
            "{subject} comparison for {topic}",
            "how to choose {subject} for {topic}",
        ])

    suggestions = []
    for topic in candidate_topics:
        topic_text = topic_query_label(topic)
        for template in templates:
            prompt = template.format(subject=subject, topic=topic_text)
            prompt = re.sub(r"\s+", " ", prompt).strip()
            norm = prompt.lower()
            if norm in existing:
                continue
            if prompt not in suggestions:
                suggestions.append(prompt)
            if len(suggestions) >= 4:
                return suggestions
    return suggestions[:4]


def model_response_sentence(model_name, trends, brand):
    tracked = trends["tracked_brand"]
    positive = list_labels(tracked.get("positive_attributes", []), 3)
    framing = list_labels(tracked.get("framing", []), 2)
    comp = trends.get("competitors", [])
    if comp:
        top_comp = comp[0]
        comp_name = top_comp["brand"]
        comp_reasons = list_labels(top_comp.get("win_reasons", []), 2)
        return (
            f"In {model_name}, the brand is most often associated with {positive}, and the recurring framing leans toward {framing}. "
            f"The clearest competing narrative comes from {comp_name}, which tends to win when the answer leans on {comp_reasons}."
        )
    return f"In {model_name}, the brand is most often associated with {positive}, with {framing} framing appearing most often."


def executive_narrative(metrics):
    brand = metrics["brand"]
    per_model = metrics["per_model"]
    positions = [brand_position(model, brand) for model in per_model]
    lead_models = [model["model"] for model, pos in zip(per_model, positions) if pos[0] in {"lead", "tie"}]
    trailing = [(model["model"], pos[1], pos[2]) for model, pos in zip(per_model, positions) if pos[0] == "trail"]
    vis_values = [model["totals"]["visibility_rate_pct"] for model in per_model]
    vis_range = max(vis_values) - min(vis_values) if vis_values else 0.0
    if vis_range >= 10:
        range_phrase = "varies meaningfully by model"
    elif vis_range >= 5:
        range_phrase = "shows a modest model spread"
    else:
        range_phrase = "is fairly stable across models"
    lead_text = (
        f"{brand} leads or ties on share of voice in {', '.join(lead_models)}."
        if lead_models else
        f"{brand} does not lead any analyzed model yet."
    )
    trail_text = (
        " ".join(
            f"{model} is led by {leader} by {gap:.1f} points."
            for model, leader, gap in trailing[:2]
        ) if trailing else ""
    )
    return f"{brand} {range_phrase}. {lead_text} {trail_text}".strip()


def render_brand_position_summary(metrics):
    brand = metrics["brand"]
    per_model = metrics["per_model"]
    positions = [brand_position(model, brand) for model in per_model]
    lead_models = [model["model"] for model, pos in zip(per_model, positions) if pos[0] in {"lead", "tie"}]
    if len(lead_models) == len(per_model) and lead_models:
        return f"{brand} is already leading or tied across the analyzed models, so the near-term job is to defend that position and widen the proof base around what is already working."
    if lead_models:
        return f"{brand} has uneven AI visibility today: it already holds meaningful ground in {', '.join(lead_models)}, but that strength does not yet travel consistently across the full model set."
    return f"{brand} has a real visibility gap to close, but it is not a blanket category failure. The current snapshot shows specific footholds the brand can build from rather than a uniformly weak position."


def render_competitor_pressure_summary(metrics):
    competitors = metrics.get("competitor_analysis", [])[:2]
    if not competitors:
        return "Competitor pressure is limited in this snapshot, so the focus should stay on protecting current inclusion patterns and tightening weak spots."
    first = competitors[0]
    if len(competitors) > 1:
        second = competitors[1]
        return (
            f"The strongest pressure comes from {first['brand']}, which behaves like a {role_label(first['role']).lower()} and wins most often on "
            f"{list_values(first.get('strongest_topics', []), 2)}. {second['brand']} adds a second layer of pressure, especially around "
            f"{list_values(second.get('strongest_topics', []), 2)}."
        )
    return (
        f"The clearest competitive pressure comes from {first['brand']}, which behaves like a {role_label(first['role']).lower()} and is strongest on "
        f"{list_values(first.get('strongest_topics', []), 2)}."
    )


def render_executive_verdict(metrics):
    brand = metrics["brand"]
    per_model = metrics["per_model"]
    strongest_model = strongest_model_name(per_model)
    weakest_model = weakest_model_name(per_model)
    strongest_topic, weakest_topic = topic_strengths(metrics)
    plays = metrics.get("strategic_plays", [])
    growth_plays = [play for play in plays if play.get("bucket") in {"Build", "Reclaim", "Verify"} and play.get("play_type") != "citation"]
    top_play = highest_priority_play(growth_plays) or highest_priority_play(plays)
    prompt_count = per_model[0]["totals"]["prompts"] if per_model else 0
    softness = "The sample is still directional, so the read should be treated as a strategic signal rather than a final market verdict. " if prompt_count < 20 else ""
    sentence_one = render_brand_position_summary(metrics)
    sentence_two = (
        f"{softness}{strongest_model} is the clearest foothold today, while {weakest_model} shows where competitors are shaping the category narrative more consistently."
    ).strip()
    sentence_three = render_competitor_pressure_summary(metrics)
    if top_play:
        priority_focus = titleish(top_play.get("topic") or top_play.get("prompt_cluster") or "priority coverage")
        sentence_four = (
            f"The highest-priority move is to strengthen {priority_focus} coverage so AI systems have clearer, more repeatable reasons to include {brand}."
        )
    elif weakest_topic:
        sentence_four = f"The highest-priority move is to tighten the answer pattern around {titleish(weakest_topic[0])}, where the current inclusion signal is thinnest."
    elif strongest_topic:
        sentence_four = f"The near-term priority is to defend {titleish(strongest_topic[0])} and turn that strength into a more repeatable cross-model inclusion pattern."
    else:
        sentence_four = f"The next move is to tighten the strongest owned proof points and make the inclusion pattern easier for AI systems to repeat."
    return " ".join([sentence_one, sentence_two, sentence_three, sentence_four]).strip()


def render_citation_strategy_summary(citation_metrics):
    summary = citation_metrics.get("summary", {})
    if not citation_metrics.get("enabled"):
        return "Citation analysis was not enabled for this snapshot."
    top_domains = summary.get("top_opportunity_domains", [])[:3]
    domain_text = ", ".join(top_domains) if top_domains else "the highest-scoring domains in the export"
    cross_model_gaps = summary.get("cross_model_no_brand_pages", 0)
    all_model_gaps = summary.get("all_model_no_brand_pages", 0)
    no_brand_pages = summary.get("no_brand_pages", 0)
    return (
        f"Citation opportunities should be treated as an influence map, not a raw outreach list. This snapshot surfaces {no_brand_pages} no-brand cited pages, "
        f"including {cross_model_gaps} that recur across multiple models and {all_model_gaps} that show up in every analyzed model. "
        f"The most practical targets sit on domains such as {domain_text}, where answer-shaping pages already influence AI outputs and could plausibly be strengthened, briefed, or countered."
    )


def render_roadmap_narrative(metrics):
    plays = metrics.get("strategic_plays", [])
    growth_plays = [play for play in plays if play.get("bucket") in {"Build", "Reclaim", "Verify"} and play.get("play_type") != "citation"]
    citation = metrics.get("citation_analysis", {})
    top_play = highest_priority_play(growth_plays)
    citation_pages = citation.get("page_opportunities", []) if citation.get("enabled") else []
    top_citation = citation_pages[0] if citation_pages else None
    cleanup_move = portfolio_next_move(metrics["recommendations"]) or "Prune low-value prompts and tighten the tracking framework before the next read."
    thirty = (
        f"Fix the clearest owned-content and messaging gaps around {titleish(top_play.get('topic') or top_play.get('prompt_cluster') or 'the top opportunity')}."
        if top_play else
        "Fix the clearest owned-content and messaging gaps in the strongest opportunity area."
    )
    sixty = (
        f"Extend the same proof points into third-party and partner surfaces, starting with {top_citation.get('root_domain', 'the most credible citation targets')}."
        if top_citation else
        "Extend the same proof points into third-party and partner surfaces where the brand still lacks reinforcement."
    )
    ninety = f"Retest, prune low-value prompts, and turn winning patterns into a repeatable prompt-tracking framework. Start with: {cleanup_move}"
    return [thirty, sixty, ninety]


def render_play_narrative(play):
    bucket = presentation_bucket(play.get("bucket", ""))
    action_phrase = stable_pick(
        PHRASE_BANKS.get("citation" if play.get("play_type") == "citation" else bucket, PHRASE_BANKS["Watch"]),
        bucket,
        play.get("confidence"),
        play.get("priority_score"),
        play.get("play_name"),
    )
    action_sentence = action_phrase.rstrip(".") + "."
    cluster = titleish(play.get("prompt_cluster", "")).lower() or "this prompt cluster"
    topic = titleish(play.get("topic", "")).lower() or cluster
    threats = ", ".join(play.get("competitor_threat", []))
    models = ", ".join(play.get("affected_models", [])) or "the analyzed models"
    why_it_matters = (play.get("why_it_matters", "") or "").strip()
    if why_it_matters and not why_it_matters.endswith("."):
        why_it_matters += "."
    if play.get("play_type") == "citation":
        source_text = ", ".join(play.get("top_domains", [])[:2]) or "the cited pages"
        strategic_read = (
            f"{why_it_matters} AI systems are already leaning on sources tied to {topic}, so this is a source-influence issue rather than a pure awareness problem. "
            f"The clearest pressure sits in {models}, with pages on {source_text} helping shape the answer set. {action_sentence}"
        )
        recommended_move = f"Recommended move: {play.get('execution_notes', '')}"
        proof = [
            f"Influence motion: {play.get('action_type', 'Citation influence')}",
            f"Priority models: {models}",
        ]
        if play.get("top_domains"):
            proof.append(f"Priority sources: {', '.join(play.get('top_domains', [])[:3])}")
        return {"strategic_read": strategic_read, "recommended_move": recommended_move, "proof_to_include": proof}
    focus = f"{titleish(cluster)} is the clearest place to tighten proof, comparison framing, and inclusion signals."
    if threats:
        competitive_pressure = f"Competitors such as {threats} are showing a more repeatable answer pattern in {models}."
    else:
        competitive_pressure = (
            f"The current answer set is still inconsistent in {models}, so this is more about sharpening the case for inclusion "
            f"than displacing one obvious rival."
        )
    strategic_read = (
        f"{why_it_matters} {focus} {competitive_pressure} {action_sentence}"
    )
    recommended_move = f"Recommended move: {play.get('execution_notes', '')}"
    proof = [
        f"Model focus: {models}",
        f"Competitive pressure: {threats or 'No single competitor dominates this gap'}",
    ]
    if play.get("recommended_asset_type"):
        proof.append(f"Primary asset: {play.get('recommended_asset_type')}")
    if play.get("example_language_angle"):
        proof.append(f"Answer-ready angle: {play.get('example_language_angle')}")
    return {"strategic_read": strategic_read, "recommended_move": recommended_move, "proof_to_include": proof[:4]}


def play_supporting_label(play):
    return play.get("supporting_label") or ("Supporting prompts" if play.get("play_type") != "citation" else "Supporting pages")


def play_supporting_items(play):
    items = play.get("supporting_items")
    if items:
        return items
    return play.get("supporting_prompts", [])


def citation_summary_sentence(citation, brand):
    summary = citation.get("summary", {})
    all_model_gaps = summary.get("all_model_no_brand_pages", 0)
    cross_model_gaps = summary.get("cross_model_no_brand_pages", 0)
    no_brand_pages = summary.get("no_brand_pages", 0)
    canonical_pages = summary.get("canonical_pages", 0)
    top_domains = summary.get("top_opportunity_domains", [])[:3]
    domain_text = ", ".join(top_domains) if top_domains else "no standout domains yet"
    return (
        f"Cited pages that do not mention {brand} are influence opportunities: the models already trust those pages enough to cite them, "
        f"but the pages are not reinforcing the brand. This snapshot includes {canonical_pages} canonical cited pages, "
        f"{no_brand_pages} pages with no brand mention, {cross_model_gaps} cross-model no-brand pages, and {all_model_gaps} all-model gaps. "
        f"The strongest publisher or domain targets are {domain_text}."
    )


def citation_page_rows(citation, limit=10, require_cross_model=False):
    rows = []
    for page in citation.get("page_opportunities", []):
        if page.get("brand_mentioned_status") == "Yes":
            continue
        if require_cross_model and page.get("model_count", 0) < 2:
            continue
        rows.append([
            page.get("root_domain", ""),
            page.get("model_count", 0),
            ", ".join(page.get("models_cited", [])),
            page.get("cited_in_prompts_total_deduped", 0),
            page.get("citation_opportunity_score", 0),
            page.get("canonical_url", ""),
        ])
        if len(rows) >= limit:
            break
    return rows


def citation_domain_rows(citation, limit=10):
    rows = []
    for domain in citation.get("domain_opportunities", [])[:limit]:
        rows.append([
            domain.get("root_domain", ""),
            domain.get("model_count", 0),
            domain.get("percent_pages_without_brand", 0.0),
            domain.get("domain_opportunity_score", 0),
            titleish((domain.get("top_page_type") or "").replace("_", " ")),
            domain.get("recommended_domain_action", ""),
        ])
    return rows


def citation_model_rows(citation):
    rows = []
    for trend in citation.get("model_trends", []):
        rows.append([
            trend.get("model", ""),
            trend.get("canonical_pages", 0),
            trend.get("raw_rows", 0),
            trend.get("duplicate_count", 0),
            pct(trend.get("percent_no_brand_pages", 0.0)),
            ", ".join(trend.get("top_no_brand_opportunity_domains", [])[:3]) or "None highlighted",
        ])
    return rows


def citation_quality_bullets(citation):
    warnings = citation.get("data_quality", {}).get("warnings", [])
    return warnings[:5]


def presentation_bucket(bucket):
    bucket = (bucket or "").strip()
    return "Watch" if bucket in {"", "Monitor"} else bucket


def model_scorecard_rows(metrics):
    brand = metrics["brand"]
    rows = []
    for model in metrics["per_model"]:
        position, leader_name, gap = brand_position(model, brand)
        rows.append([
            model["model"],
            pct(model["totals"]["visibility_rate_pct"]),
            model["rank"]["average"],
            pct(model["share_of_voice_pct"].get(brand, 0.0)),
            leader_name,
            "Lead or tie" if position in {"lead", "tie"} else f"{gap:.1f} pts",
        ])
    return rows


def play_heading(play, index=None):
    if index is None:
        return play.get("play_name", "Strategic play")
    return f"PLAY {index}: {play.get('play_name', 'Strategic play')}"


def play_score_prefix(play):
    if play.get("bucket") == "Defend":
        return "Defense priority"
    if play.get("bucket") == "Retire":
        return "Cleanup priority"
    return "Opportunity score"


def supporting_examples_text(play, limit=4):
    items = play_supporting_items(play)[:limit]
    return ", ".join(items) if items else "None highlighted"


def play_card_lines(play, *, index=None, include_cluster=False):
    narrative = render_play_narrative(play)
    lines = [
        f"### {play_heading(play, index)}",
        (
            f"{play_score_prefix(play)}: {score_display(play)} | Bucket: {presentation_bucket(play.get('bucket', ''))} | "
            f"Owner: {play.get('suggested_owner', '')} | Effort: {titleish(play.get('effort', ''))} | "
            f"Confidence: {titleish(play.get('confidence', ''))}"
        ),
        f"Threat: {', '.join(play.get('competitor_threat', [])) or 'None highlighted'}",
        f"Affected models: {', '.join(play.get('affected_models', [])) or 'All analyzed models'}",
    ]
    if include_cluster:
        lines.append(f"Prompt cluster: {titleish(play.get('prompt_cluster', ''))}")
    lines.extend([
        f"Strategic read: {narrative['strategic_read']}",
        f"Recommended move: {narrative['recommended_move'].replace('Recommended move: ', '')}",
        f"Proof to include: {' | '.join(narrative['proof_to_include']) if narrative['proof_to_include'] else asset_display(play.get('recommended_asset_type', ''), play.get('recommended_assets', ''))}",
        f"{play_supporting_label(play)}: {supporting_examples_text(play)}",
        "",
    ])
    return lines


def strongest_model_name(per_model):
    return max(per_model, key=lambda item: item["totals"]["visibility_rate_pct"])["model"]


def weakest_model_name(per_model):
    return min(per_model, key=lambda item: item["totals"]["visibility_rate_pct"])["model"]


def highest_priority_play(plays):
    return plays[0] if plays else None


def citation_exec_rows(citation, limit=5):
    rows = []
    for page in citation.get("page_opportunities", []):
        if page.get("citation_opportunity_score", 0) <= 0:
            continue
        rows.append([
            page.get("root_domain", ""),
            page.get("page_title") or citation_page_type_label(page.get("page_type", "")),
            citation_page_type_label(page.get("page_type", "")),
            ", ".join(page.get("models_cited", [])),
            page.get("citation_opportunity_score", 0),
            page.get("action_type", ""),
            page.get("recommended_action", ""),
        ])
        if len(rows) >= limit:
            break
    return rows


def citation_detailed_rows(citation, limit=10):
    rows = []
    for page in citation.get("page_opportunities", []):
        if page.get("citation_opportunity_score", 0) <= 0:
            continue
        rows.append([
            page.get("root_domain", ""),
            page.get("page_title") or citation_page_type_label(page.get("page_type", "")),
            citation_page_type_label(page.get("page_type", "")),
            titleish(page.get("derived_report_topic", "")),
            ", ".join(page.get("models_cited", [])),
            page.get("brand_mentioned_status", ""),
            page.get("citation_opportunity_score", 0),
            page.get("action_type", ""),
        ])
        if len(rows) >= limit:
            break
    return rows


def ownership_bullets(metrics):
    brand = metrics["brand"]
    per_model = metrics["per_model"]
    strongest_topic, _ = topic_strengths(metrics)
    leads = [model["model"] for model in per_model if brand_position(model, brand)[0] in {"lead", "tie"}]
    bullets = []
    if leads:
        bullets.append(f"{brand} leads or ties on share of voice in {', '.join(leads)}.")
    bullets.append(f"Strongest model: {strongest_model_name(per_model)}.")
    if strongest_topic:
        bullets.append(f"Strongest topic: {titleish(strongest_topic[0])} at {strongest_topic[1]:.1f}% weighted visibility.")
    tracked = metrics["response_trends"]["overall"]["tracked_brand"]
    bullets.append(
        f"Response language most often links the brand to {list_labels(tracked.get('positive_attributes', []), 3)} "
        f"with {list_labels(tracked.get('framing', []), 2)} framing."
    )
    defend_play = next((play for play in metrics.get("strategic_plays", []) if play.get("bucket") == "Defend"), None)
    if defend_play:
        bullets.append(f"Existing strength worth protecting: {defend_play['play_name']}.")
    return bullets[:5]


def competitor_win_bullets(metrics):
    bullets = []
    for item in metrics.get("competitor_analysis", [])[:5]:
        bullets.append(
            f"{item['brand']} is a {role_label(item['role']).lower()} and wins most often on "
            f"{list_values(item.get('strongest_topics', []), 3)}."
        )
    return bullets


def model_read_lines(metrics):
    brand = metrics["brand"]
    lines = []
    for model in metrics["per_model"]:
        pos, leader_name, gap = brand_position(model, brand)
        verdict = (
            f"{brand} leads this model."
            if pos == "lead"
            else f"{brand} is tied for the lead in this model."
            if pos == "tie"
            else f"{leader_name} leads this model by {gap:.1f} points of share of voice."
        )
        topic_cov = [item for item in model["report_topic_coverage"].items() if item[1]["prompts"] > 0]
        strengths = sorted(topic_cov, key=lambda item: (-item[1]["visibility_rate_pct"], item[0]))[:2]
        weaknesses = sorted(topic_cov, key=lambda item: (item[1]["visibility_rate_pct"], -item[1]["prompts"], item[0]))[:2]
        lines.append(
            f"{model['model']} has {pct(model['totals']['visibility_rate_pct'])} visibility, an average rank of "
            f"{model['rank']['average']}, and {pct(model['share_of_voice_pct'].get(brand, 0.0))} share of voice. {verdict}"
        )
        lines.append(f"- Leader and gap: {leader_name} | {'Lead or tie' if pos in {'lead', 'tie'} else f'{gap:.1f} points behind'}.")
        lines.append(f"- Top strengths: {list_values([topic for topic, _ in strengths], 2)}.")
        lines.append(f"- Top weaknesses: {list_values([topic for topic, _ in weaknesses], 2)}.")
        lines.append(f"- Response pattern: {model_response_sentence(model['model'], metrics['response_trends']['by_model'][model['model']], brand)}")
    return lines


def cleanup_inputs(metrics):
    recs = metrics["recommendations"]
    records = metrics.get("appendix_records", [])
    topic_mapping = metrics.get("topic_mapping", {})
    _, weakest_topic = topic_strengths(metrics)
    intent_rows = aggregate_records(records, metrics["models_analyzed"], "intent")
    retire_recs = sorted(
        [rec for rec in recs if rec["action_bucket"] == "Retire"],
        key=lambda rec: (-(rec.get("cleanup_priority", 0) or 0), rec["prompt"].lower()),
    )
    duplicates = [rec for rec in retire_recs if rec.get("duplicate_of")]
    no_surface = [rec for rec in retire_recs if not rec.get("duplicate_of")]
    weak_intents = [row for row in intent_rows if row["visibility"] < 50.0][:3]
    missing_topics = [row for row in topic_mapping.get("underrepresented_topics", []) if row["prompt_count"] == 0][:4]
    add_suggestions = add_prompt_suggestions(records, recs, weak_intents, missing_topics, weakest_topic)
    return {
        "intent_rows": intent_rows,
        "retire_recs": retire_recs,
        "duplicates": duplicates,
        "no_surface": no_surface,
        "weak_intents": weak_intents,
        "missing_topics": missing_topics,
        "add_suggestions": add_suggestions,
        "weakest_topic": weakest_topic,
    }


def priority_action_plan_lines(metrics, growth_plays, citation_plays, cleanup):
    lines = ["### Strategic growth plays", ""]
    if growth_plays:
        for index, play in enumerate(growth_plays[:3], 1):
            lines.extend(play_card_lines(play, index=index))
    else:
        lines.append("No growth plays surfaced in this snapshot.")
        lines.append("")
    lines.extend(["### Citation plays", ""])
    if citation_plays:
        for index, play in enumerate(citation_plays[:3], 1):
            lines.extend(play_card_lines(play, index=index))
    else:
        lines.append("No citation plays were generated for this snapshot.")
        lines.append("")
    lines.extend(["### Portfolio cleanup actions", ""])
    if cleanup["retire_recs"]:
        for rec in cleanup["retire_recs"][:3]:
            lines.append(f"- Remove or de-prioritize `{rec['prompt']}`: {cleanup_action_text(rec)}")
    else:
        lines.append("- No immediate retire actions surfaced.")
    for prompt in cleanup["add_suggestions"][:2]:
        lines.append(f"- Add next: `{prompt}`")
    lines.append("")
    return lines


def render_executive_summary(metrics):
    brand = metrics["brand"]
    models = metrics["models_analyzed"]
    per_model = metrics["per_model"]
    snapshot_date = basename_date(metrics["appendix_csv"])
    plays = metrics.get("strategic_plays", [])
    citation = metrics.get("citation_analysis", {})
    strongest_topic, weakest_topic = topic_strengths(metrics)
    growth_plays = [play for play in plays if play.get("bucket") in {"Build", "Reclaim", "Verify"} and play.get("play_type") != "citation"]
    top_play = highest_priority_play(growth_plays) or highest_priority_play(plays)
    competitor_analysis = metrics.get("competitor_analysis") or []
    top_competitor = competitor_analysis[0].get("brand", "No clear competitor") if competitor_analysis else "No clear competitor"
    strongest_model = strongest_model_name(per_model)
    weakest_model = weakest_model_name(per_model)

    lines = [
        f"# {brand} AI Visibility Executive Summary",
        f"*{', '.join(models)} - {per_model[0]['totals']['prompts']} prompts per model - snapshot {snapshot_date}*",
        "",
        "## Executive verdict",
    ]
    verdict = render_executive_verdict(metrics)
    lines.extend([
        verdict.strip(),
        "",
        "## Visibility scorecard",
        md_table(["Model", "Visibility", "Avg rank", "Share of voice", "Leader", "Gap"], model_scorecard_rows(metrics)),
        "",
        "## What the brand owns today",
    ])
    for bullet in ownership_bullets(metrics):
        lines.append(f"- {bullet}")
    lines.extend(["", "## Where competitors are winning"])
    for bullet in competitor_win_bullets(metrics)[:5]:
        lines.append(f"- {bullet}")
    lines.extend(["", "## Top 3 strategic plays", ""])
    if growth_plays:
        for index, play in enumerate(growth_plays[:3], 1):
            lines.extend(play_card_lines(play, index=index))
    else:
        lines.extend(["No strategic growth plays surfaced in this snapshot.", ""])
    lines.append("## Citation influence opportunities")
    if citation.get("enabled"):
        lines.extend([
            render_citation_strategy_summary(citation),
            "",
        ])
        citation_rows = citation_exec_rows(citation, limit=5)
        if citation_rows:
            lines.append(md_table(
                ["Domain", "Page", "Type", "Models", "Score", "Action type", "Recommended action"],
                citation_rows,
            ))
        else:
            lines.append("No citation opportunities met the reporting threshold.")
    else:
        lines.append("Citation analysis was not enabled for this snapshot.")
    roadmap = render_roadmap_narrative(metrics)
    lines.extend([
        "",
        "## 30/60/90-day roadmap",
        f"1. 30 days: {roadmap[0]}",
        f"2. 60 days: {roadmap[1]}",
        f"3. 90 days: {roadmap[2]}",
        "",
        "## Methodology note",
        f"This summary covers {len(models)} models ({', '.join(models)}), {per_model[0]['totals']['prompts']} prompts per model, and a snapshot date of {snapshot_date}."
        + (" Citation normalization dedupes canonical URLs and fragments before scoring." if citation.get("enabled") else ""),
        "",
    ])
    return "\n".join(lines)


def render_detailed_report(metrics):
    brand = metrics["brand"]
    models = metrics["models_analyzed"]
    per_model = metrics["per_model"]
    appendix_name = os.path.basename(metrics["appendix_csv"])
    snapshot_date = basename_date(metrics["appendix_csv"])
    records = metrics.get("appendix_records", [])
    recs = metrics["recommendations"]
    plays = metrics.get("strategic_plays", [])
    citation = metrics.get("citation_analysis", {})
    topic_mapping = metrics.get("topic_mapping", {})
    strongest_topic, weakest_topic = topic_strengths(metrics)
    growth_plays = [play for play in plays if play.get("bucket") in {"Build", "Reclaim", "Verify"} and play.get("play_type") != "citation"]
    citation_plays = [play for play in plays if play.get("play_type") == "citation"]
    cleanup_plays = [play for play in plays if play.get("bucket") == "Retire"]
    top_play = highest_priority_play(growth_plays) or highest_priority_play(plays)
    cleanup = cleanup_inputs(metrics)

    lines = [
        f"# {brand} AI Visibility Detailed Report",
        f"*{', '.join(models)} - {per_model[0]['totals']['prompts']} prompts per model - snapshot {snapshot_date}*",
        "",
        "## Executive snapshot",
        executive_narrative(metrics),
        "",
        md_table(["Model", "Visibility", "Avg rank", "Share of voice", "Leader", "Gap"], model_scorecard_rows(metrics)),
        "",
        f"- Category leader: {metrics.get('category_leader') or per_model[0]['leader']}.",
        f"- Strongest model: {strongest_model_name(per_model)}.",
        f"- Weakest model: {weakest_model_name(per_model)}.",
    ]
    if strongest_topic:
        lines.append(f"- Biggest topic strength: {titleish(strongest_topic[0])} ({strongest_topic[1]:.1f}% weighted visibility).")
    if weakest_topic:
        lines.append(f"- Biggest topic weakness: {titleish(weakest_topic[0])} ({weakest_topic[1]:.1f}% weighted visibility).")
    if top_play:
        lines.append(f"- Highest-priority action: {top_play['play_name']} ({score_display(top_play)}).")
    lines.extend([
        "",
        "## Priority action plan",
        "",
    ])
    lines.extend(priority_action_plan_lines(metrics, growth_plays, citation_plays, cleanup))
    lines.extend(["## Strategic recommendation plays", ""])
    if growth_plays:
        lines.extend(["### Strategic growth plays", ""])
        for index, play in enumerate(growth_plays[:4], 1):
            lines.extend(play_card_lines(play, index=index, include_cluster=True))
    if cleanup_plays:
        lines.extend(["### Portfolio cleanup plays", ""])
        for index, play in enumerate(cleanup_plays[:3], 1):
            lines.extend(play_card_lines(play, index=index, include_cluster=True))
    if citation_plays:
        lines.extend(["### Citation plays", ""])
        for index, play in enumerate(citation_plays[:3], 1):
            lines.extend(play_card_lines(play, index=index, include_cluster=True))
    support_rows = [rec for rec in recs if rec["priority_score"] > 0][:10]
    if support_rows:
        lines.extend([
            "### Top prompt-level tasks",
            md_table(
                ["Prompt", "Play", "Gap", "Score"],
                [[rec["prompt"], rec.get("recommended_play", ""), rec["gap_label"], rec["priority_score"]] for rec in support_rows],
            ),
            "",
        ])
    lines.append("## Model-by-model performance")
    lines.extend(model_read_lines(metrics))
    lines.extend(["", "## Competitive landscape"])
    competitor_rows = [
        [
            item["brand"],
            pct(item["avg_share_of_voice_pct"]),
            role_label(item["role"]),
            list_values(item.get("strongest_topics", []), 3),
            list_values(item.get("threat_prompts", []), 2),
        ]
        for item in metrics.get("competitor_analysis", [])[:6]
    ]
    if competitor_rows:
        lines.append(md_table(["Competitor", "Avg SoV", "Role", "Strongest topics", "Threat prompts"], competitor_rows))
        lines.append("")
        for item in metrics.get("competitor_analysis", [])[:4]:
            lines.append(
                f"- {item['brand']} acts as a {role_label(item['role']).lower()}, showing the most strength in "
                f"{list_values(item.get('strongest_topics', []), 3)} and creating pressure on "
                f"{list_values(item.get('threat_prompts', []), 2)}."
            )
    else:
        lines.append("No major competitor pattern was detected beyond the tracked brand.")
    lines.extend(["", "## Topic/category performance"])
    if topic_mapping.get("warning"):
        lines.extend([topic_mapping["warning"], ""])
    if topic_mapping.get("tracked_topics"):
        lines.extend([
            "### Tracked topics with matched prompts",
            md_table(["Topic", "Matched prompts"], [[titleish(item["topic"]), item["prompt_count"]] for item in topic_mapping["tracked_topics"]]),
            "",
        ])
    if topic_mapping.get("underrepresented_topics"):
        lines.extend([
            "### Underrepresented or untracked topics",
            md_table(
                ["Topic", "Matched prompts", "Read"],
                [
                    [titleish(item["topic"]), item["prompt_count"], ("No matched prompts" if item["prompt_count"] == 0 else "Sparse mapping")]
                    for item in topic_mapping["underrepresented_topics"]
                ],
            ),
            "",
        ])
    topic_rows = model_topic_rows(metrics)
    if topic_rows:
        lines.extend([
            "### Topic x model performance",
            md_table(["Topic", "Model", "Prompts", "Visibility / rank", "Weak/absent", "Action bucket"], topic_rows),
            "",
        ])
    lines.extend(["## Funnel, intent, and persona/use-case performance", "### Performance by funnel stage"])
    funnel_rows = aggregate_records(records, models, "funnel_stage")
    lines.extend([
        md_table(
            ["Funnel stage", "Prompts", "Visibility", "Avg rank", "Weak/absent prompts"],
            [[titleish(row["label"]), row["prompts"], pct(row["visibility"]), row["avg_rank"], row["weak_or_absent"]] for row in funnel_rows],
        ),
        "",
        "### Performance by intent",
    ])
    intent_rows = cleanup["intent_rows"]
    lines.extend([
        md_table(
            ["Intent", "Prompts", "Visibility", "Avg rank", "Weak/absent prompts"],
            [[titleish(row["label"]), row["prompts"], pct(row["visibility"]), row["avg_rank"], row["weak_or_absent"]] for row in intent_rows],
        ),
        "",
    ])
    persona_rows = [row for row in aggregate_records(records, models, "persona_use_case_cluster", limit=8) if row["label"] != "general category queries"]
    if persona_rows:
        lines.extend([
            "### Performance by persona or use-case cluster",
            md_table(
                ["Cluster", "Prompts", "Visibility", "Avg rank", "Weak/absent prompts"],
                [[titleish(row["label"]), row["prompts"], pct(row["visibility"]), row["avg_rank"], row["weak_or_absent"]] for row in persona_rows],
            ),
            "",
        ])
    lines.append("## Model response trends")
    overall_trends = metrics["response_trends"]["overall"]
    overall_competitors = overall_trends.get("competitors", [])[:4]
    lines.extend([
        md_table(
            ["Brand", "Positive associations", "Weaknesses / objections", "Common framing"],
            [[
                brand,
                list_labels(overall_trends["tracked_brand"].get("positive_attributes", []), 3),
                list_labels(overall_trends["tracked_brand"].get("negative_attributes", []), 2),
                list_labels(overall_trends["tracked_brand"].get("framing", []), 2),
            ]] + [[
                item["brand"],
                list_labels(item.get("positive_attributes", []), 3),
                list_labels(item.get("negative_attributes", []), 2),
                list_labels(item.get("framing", []), 2),
            ] for item in overall_competitors]
        ),
        "",
    ])
    for model in models:
        lines.append(f"- {model}: {model_response_sentence(model, metrics['response_trends']['by_model'][model], brand)}")
    lines.extend(["", "## Citation opportunity analysis"])
    if citation.get("enabled"):
        lines.extend([render_citation_strategy_summary(citation), "", "### Citation visibility summary"])
        lines.extend([
            md_table(["Model", "Canonical pages", "Raw rows", "Duplicates", "No-brand pages", "Top no-brand domains"], citation_model_rows(citation)),
            "",
        ])
        detailed_rows = citation_detailed_rows(citation, limit=10)
        if detailed_rows:
            lines.extend([
                "### Top cited pages without brand mention",
                md_table(
                    ["Domain", "Page", "Type", "Topic", "Models", "Brand mention", "Score", "Action type"],
                    detailed_rows,
                ),
                "",
            ])
        cross_rows = [row for row in detailed_rows if "," in row[4]][:10]
        if cross_rows:
            lines.extend([
                "### Cross-model citation opportunities",
                md_table(
                    ["Domain", "Page", "Type", "Topic", "Models", "Brand mention", "Score", "Action type"],
                    cross_rows,
                ),
                "",
            ])
        domain_rows = citation_domain_rows(citation, limit=10)
        if domain_rows:
            lines.extend([
                "### Domain / publisher opportunity scorecard",
                md_table(
                    ["Domain", "Models", "% no-brand pages", "Score", "Top page type", "Recommended action"],
                    domain_rows,
                ),
                "",
            ])
        lines.extend(["### Model citation trends"])
        for trend in citation.get("model_trends", []):
            lines.append(
                f"- {trend['model']}: {trend['notes']} Top no-brand opportunity domains: "
                f"{', '.join(trend.get('top_no_brand_opportunity_domains', [])[:3]) or 'None highlighted'}."
            )
        lines.extend(["", "### Recommended citation actions"])
        for page in citation.get("page_opportunities", [])[:5]:
            if page.get("citation_opportunity_score", 0) <= 0:
                continue
            lines.append(f"- {page['root_domain']} ({page['citation_opportunity_score']} | {page.get('action_type', '')}): {page['recommended_action']}")
        quality_notes = citation_quality_bullets(citation)
        if quality_notes:
            lines.extend(["", "### Citation data quality notes"])
            for note in quality_notes:
                lines.append(f"- {note}")
        lines.append("")
    else:
        lines.extend(["Citation analysis was not enabled for this snapshot.", ""])
    lines.extend(["## Prompt portfolio cleanup", "### Add: missing high-intent prompts to track"])
    if cleanup["add_suggestions"]:
        for prompt in cleanup["add_suggestions"]:
            lines.append(f"- `{prompt}`")
    else:
        lines.append("- No additional prompt expansion surfaced beyond the current tracked set.")
    lines.extend(["", "### Consolidate: near-duplicate prompt clusters"])
    if cleanup["duplicates"]:
        for rec in cleanup["duplicates"][:5]:
            lines.append(f"- `{rec['prompt']}` -> `{rec['duplicate_of']}`: {cleanup_action_text(rec)}")
    else:
        lines.append("- No near-duplicate prompt pairs need consolidation right now.")
    lines.extend(["", "### Keep: authority prompts worth tracking deliberately"])
    if cleanup["no_surface"]:
        for rec in cleanup["no_surface"][:5]:
            lines.append(f"- `{rec['prompt']}`: Keep only if this supports a deliberate authority or education goal.")
    else:
        lines.append("- No authority-only prompt set surfaced in this snapshot.")
    lines.extend(["", "### Retire: low-value or no-surface prompts"])
    if cleanup["no_surface"]:
        for rec in cleanup["no_surface"][:5]:
            lines.append(f"- `{rec['prompt']}`: {cleanup_reason_text(rec)} Action: {cleanup_action_text(rec)}")
    else:
        lines.append("- No immediate scorecard removals surfaced in this snapshot.")
    lines.extend(["", "### Rebalance by funnel, intent, and topic"])
    if cleanup["weak_intents"]:
        lines.append(f"- Intent groups to strengthen first: {', '.join(human_intent(item['label']) for item in cleanup['weak_intents'])}.")
    if cleanup["missing_topics"]:
        lines.append(f"- Underrepresented topics to map or expand: {', '.join(titleish(item['topic']) for item in cleanup['missing_topics'])}.")
    if cleanup["weakest_topic"]:
        lines.append(f"- Weakest tracked topic to review first: {titleish(cleanup['weakest_topic'][0])}.")
    lines.extend([
        "",
        "## Defend / Reclaim / Build / Verify / Retire matrix",
        md_table(["Bucket", "Prompts", "Score status", "Typical effort"], bucket_matrix_rows(recs)),
        "",
        "### Action bucket summary",
        md_table(
            ["Bucket", "Prompts"],
            [[bucket, len([rec for rec in recs if presentation_bucket(rec["action_bucket"]) == bucket])] for bucket in ["Defend", "Reclaim", "Build", "Verify", "Retire", "Watch"]],
        ),
        "",
    ])
    confidence_rows, effort_rows = confidence_effort_rows(recs)
    lines.extend([
        "### Confidence breakdown",
        md_table(["Confidence", "Recommendations"], confidence_rows),
        "",
        "### Effort breakdown",
        md_table(["Effort", "Recommendations"], effort_rows),
        "",
        "## Appendix reference",
        f"Use `{appendix_name}` for the full prompt-level appendix, including topics, report topics, prompt clusters, funnel stage, intent, recommendation play, and per-model status.",
        "",
        "## Methodology and data quality notes",
        f"- Models analyzed: {', '.join(models)}.",
        f"- Prompt count per model: {per_model[0]['totals']['prompts']}.",
        f"- Snapshot date: {snapshot_date}.",
        f"- Topic mapping source: {topic_mapping.get('report_topics_source', 'unknown')}.",
    ])
    if citation.get("enabled"):
        lines.append("- Citation normalization dedupes canonical URLs, fragments, and duplicate raw rows before scoring.")
        for note in citation_quality_bullets(citation):
            lines.append(f"- Citation QA note: {note}")
    else:
        lines.append("- Citation analysis was not enabled, so this snapshot makes no source-level claims.")
    lines.append("")
    return "\n".join(lines)


def build_report(metrics):
    return render_detailed_report(metrics)


def parse_args():
    parser = argparse.ArgumentParser(description="Render executive and detailed AI visibility markdown reports.")
    parser.add_argument("metrics_json")
    parser.add_argument("report_md", nargs="?", help="Backward-compatible positional detailed markdown output path.")
    parser.add_argument("--detailed", help="Explicit detailed markdown output path.")
    parser.add_argument("--executive", help="Executive summary markdown output path.")
    args = parser.parse_args()
    detailed_path = args.detailed or args.report_md
    if args.detailed and args.report_md and args.detailed != args.report_md:
        parser.error("Use either the positional detailed output path or --detailed, not both with different values.")
    if not detailed_path and not args.executive:
        parser.error("At least one output path is required: positional detailed output, --detailed, or --executive.")
    return args, detailed_path


def main():
    args, detailed_path = parse_args()
    metrics_path = Path(args.metrics_json)
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    written = []
    if detailed_path:
        out_path = Path(detailed_path)
        out_path.write_text(render_detailed_report(metrics), encoding="utf-8")
        written.append(str(out_path))
    if args.executive:
        executive_path = Path(args.executive)
        executive_path.write_text(render_executive_summary(metrics), encoding="utf-8")
        written.append(str(executive_path))
    print("Wrote " + " and ".join(written))


if __name__ == "__main__":
    main()
