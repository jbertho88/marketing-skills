#!/usr/bin/env python3
"""
suggest_topics.py
Suggest a fixed topic set from one or more AI Visibility CSV exports.

Usage:
    python suggest_topics.py FILE1.csv [FILE2.csv ...] [--max-topics 10] [--out topics.json]
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from analyze_visibility import (
    add_fallback_topic_specs,
    auto_topics,
    load_file,
    merge_topic_specs,
    prompt_topics,
)


def build_suggestions(files, max_topics):
    prompts = []
    seen = set()
    brands = set()
    for path in files:
        brand, _model, rows = load_file(path)
        brands.add(brand)
        for row in rows:
            prompt = row["prompt"]
            norm = prompt.strip().lower()
            if norm not in seen:
                seen.add(norm)
                prompts.append(prompt)

    topic_specs = auto_topics(prompts, k=max_topics)
    topic_specs = merge_topic_specs(topic_specs)
    topic_specs = add_fallback_topic_specs(
        prompts,
        topic_specs,
        max_topics=max(max_topics, 10),
        min_prompts=3,
    )

    topic_examples = defaultdict(list)
    for prompt in prompts:
        topics = prompt_topics(prompt, topic_specs)
        for topic in topics:
            if len(topic_examples[topic]) < 5:
                topic_examples[topic].append(prompt)

    suggestions = []
    for topic in topic_specs:
        assigned = [prompt for prompt in prompts if topic in prompt_topics(prompt, {topic: topic_specs[topic]})]
        suggestions.append({
            "topic": topic,
            "prompt_count": len(assigned),
            "examples": topic_examples.get(topic, [])[:5],
        })
    suggestions.sort(key=lambda item: (-item["prompt_count"], item["topic"]))
    return {
        "brands": sorted(brands),
        "prompt_count": len(prompts),
        "suggested_topics": suggestions,
    }


def main():
    parser = argparse.ArgumentParser(description="Suggest fixed topics for AI Visibility analysis")
    parser.add_argument("files", nargs="+")
    parser.add_argument("--max-topics", type=int, default=10)
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    result = build_suggestions(args.files, args.max_topics)
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Brands: {', '.join(result['brands'])} | prompts: {result['prompt_count']}")
    print("Suggested topics:")
    for item in result["suggested_topics"]:
        examples = "; ".join(item["examples"][:3])
        print(f"- {item['topic']} ({item['prompt_count']} prompts)")
        if examples:
            print(f"  e.g. {examples}")
    if args.out:
        print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
