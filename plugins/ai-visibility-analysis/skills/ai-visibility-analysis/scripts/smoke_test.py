#!/usr/bin/env python3
"""
smoke_test.py
Run a deterministic integration smoke check for the AI visibility skill.

Usage:
    python smoke_test.py \
        --brand "Moz API" \
        --date 2026-07-07 \
        --topics "local seo api, listings api, reviews api, rank tracking, reporting and dashboards, pricing and comparison" \
        --output-dir ./smoke-output \
        --prompt ChatGPT="chatgpt.csv" \
        --prompt Gemini="gemini.csv" \
        --prompt "Google AI Mode=google.csv" \
        --citation ChatGPT="chatgpt-citations.csv" \
        --citation Gemini="gemini-citations.csv" \
        --citation "Google AI Mode=google-citations.csv" \
        --owned-domain moz.com
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


SCRIPT_DIR = Path(__file__).resolve().parent


def parse_spec(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError(f"Expected Model=path, got {value!r}")
    model, path = value.split("=", 1)
    model = model.strip()
    path = path.strip().strip('"')
    if not model or not path:
        raise argparse.ArgumentTypeError(f"Expected Model=path, got {value!r}")
    return model, path


def run(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "Command failed:\n"
            + " ".join(command)
            + "\nSTDOUT:\n"
            + result.stdout
            + "\nSTDERR:\n"
            + result.stderr
        )


def assert_non_empty(path: Path) -> None:
    if not path.exists():
        raise AssertionError(f"Missing output: {path}")
    if path.stat().st_size <= 0:
        raise AssertionError(f"Empty output: {path}")


def workbook_sheet_names(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as zf:
        xml_text = zf.read("xl/workbook.xml")
    root = ET.fromstring(xml_text)
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    return [sheet.attrib["name"] for sheet in root.findall("x:sheets/x:sheet", ns)]


def read_csv_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an integration smoke test for the AI visibility skill.")
    parser.add_argument("--brand", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--topics", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--prompt", action="append", default=[], type=parse_spec, help="Model=path prompt-response CSV.")
    parser.add_argument("--citation", action="append", default=[], type=parse_spec, help="Model=path citation CSV.")
    parser.add_argument("--owned-domain", action="append", default=[])
    args = parser.parse_args()

    if not args.prompt:
        raise SystemExit("At least one --prompt Model=path input is required.")

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = args.brand.lower().replace(" ", "-")

    metrics_json = output_dir / f"{slug}-metrics-{args.date}.json"
    appendix_csv = output_dir / f"{slug}-prompt-appendix-{args.date}.csv"
    citation_json = output_dir / f"{slug}-citation-metrics-{args.date}.json"
    cited_pages_csv = output_dir / f"{slug}-cited-pages-{args.date}.csv"
    detailed_md = output_dir / f"{slug}-ai-visibility-detailed-report-{args.date}.md"
    executive_md = output_dir / f"{slug}-ai-visibility-executive-summary-{args.date}.md"
    detailed_docx = output_dir / f"{slug}-ai-visibility-detailed-report-{args.date}.docx"
    executive_docx = output_dir / f"{slug}-ai-visibility-executive-summary-{args.date}.docx"
    workbook_xlsx = output_dir / f"{slug}-ai-visibility-{args.date}.xlsx"
    compat_md = output_dir / f"{slug}-compat-detailed-{args.date}.md"

    if args.citation:
        citation_cmd = [sys.executable, str(SCRIPT_DIR / "analyze_citations.py"), "--brand", args.brand]
        if args.owned_domain:
            citation_cmd.extend(["--owned-domains", *args.owned_domain])
        for model, path in args.citation:
            citation_cmd.extend(["--citation", f"{model}={path}"])
        citation_cmd.extend(["--out-json", str(citation_json), "--out-csv", str(cited_pages_csv)])
        run(citation_cmd)

    analyze_cmd = [sys.executable, str(SCRIPT_DIR / "analyze_visibility.py")]
    for _, path in args.prompt:
        analyze_cmd.append(path)
    for model, _ in args.prompt:
        analyze_cmd.extend(["--model", model])
    analyze_cmd.extend(["--topics", args.topics, "--out", str(metrics_json), "--csv", str(appendix_csv)])
    if args.citation:
        analyze_cmd.extend(["--citation-json", str(citation_json)])
    run(analyze_cmd)
    metrics_hash_before_reports = hashlib.sha256(metrics_json.read_bytes()).hexdigest()

    run([
        sys.executable,
        str(SCRIPT_DIR / "build_report.py"),
        str(metrics_json),
        str(detailed_md),
        "--executive",
        str(executive_md),
    ])
    run([sys.executable, str(SCRIPT_DIR / "build_report.py"), str(metrics_json), str(compat_md)])
    run([sys.executable, str(SCRIPT_DIR / "build_docx.py"), str(detailed_md), str(detailed_docx)])
    run([sys.executable, str(SCRIPT_DIR / "build_docx.py"), str(executive_md), str(executive_docx)])
    run([sys.executable, str(SCRIPT_DIR / "build_xlsx.py"), str(metrics_json), str(workbook_xlsx)])
    metrics_hash_after_reports = hashlib.sha256(metrics_json.read_bytes()).hexdigest()

    expected_outputs = [metrics_json, appendix_csv, detailed_md, executive_md, detailed_docx, executive_docx, workbook_xlsx, compat_md]
    if args.citation:
        expected_outputs.extend([citation_json, cited_pages_csv])
    for path in expected_outputs:
        assert_non_empty(path)

    detailed_text = detailed_md.read_text(encoding="utf-8")
    executive_text = executive_md.read_text(encoding="utf-8")
    if len(executive_text) >= len(detailed_text):
        raise AssertionError("Executive summary should be materially shorter than the detailed report.")
    if "Strategic recommendation plays" not in detailed_text:
        raise AssertionError("Detailed report is missing 'Strategic recommendation plays'.")
    if "Citation opportunity analysis" not in detailed_text:
        raise AssertionError("Detailed report is missing 'Citation opportunity analysis'.")
    if "Top 3 strategic plays" not in executive_text:
        raise AssertionError("Executive report is missing 'Top 3 strategic plays'.")
    if "http" in executive_text:
        raise AssertionError("Executive summary should not dump canonical URLs.")
    if metrics_hash_before_reports != metrics_hash_after_reports:
        raise AssertionError("Metrics JSON changed during the prose-rendering stage.")

    verdict_match = re.search(r"## Executive verdict\s+(.+?)\n## ", executive_text, flags=re.S)
    if verdict_match:
        verdict_sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", verdict_match.group(1).strip()) if sentence.strip()]
        streak = 0
        for sentence in verdict_sentences:
            if re.match(r"^(The strongest|The weakest|The biggest)\b", sentence):
                streak += 1
                if streak > 2:
                    raise AssertionError("Executive verdict still uses too many consecutive 'The strongest / weakest / biggest' sentences.")
            else:
                streak = 0

    strategic_reads = re.findall(r"^Strategic read:\s+(.+)$", detailed_text, flags=re.M)
    if len(strategic_reads) >= 3:
        prefixes = {text[:80] for text in strategic_reads[:6]}
        if len(prefixes) <= 1:
            raise AssertionError("Strategic plays still read like the same repeated template.")

    sheet_names = workbook_sheet_names(workbook_xlsx)
    expected_sheets = [
        "Dashboard",
        "Action Plan",
        "Prompt Appendix",
        "Strategic Plays",
        "Model x Topic",
        "Portfolio Cleanup",
        "Data Dictionary",
    ]
    if args.citation:
        expected_sheets.extend([
            "Citation Action Plan",
            "Cited Pages",
            "Citation Domains",
            "Cross-Model Citations",
            "Model Citation Trends",
        ])
    for sheet in expected_sheets:
        if sheet not in sheet_names:
            raise AssertionError(f"Workbook is missing sheet: {sheet}")
    if not sheet_names or sheet_names[0] != "Dashboard":
        raise AssertionError("Dashboard should be the first workbook sheet.")

    appendix_rows = read_csv_rows(appendix_csv)
    if not appendix_rows:
        raise AssertionError("Prompt appendix CSV is empty.")
    if "prompt" not in appendix_rows[0]:
        raise AssertionError("Prompt appendix CSV does not contain prompt-level rows.")

    if args.citation:
        cited_rows = read_csv_rows(cited_pages_csv)
        if not cited_rows:
            raise AssertionError("Cited pages CSV is empty.")
        if "canonical_url" not in cited_rows[0]:
            raise AssertionError("Cited pages CSV is missing canonical_url.")
        actions = [row.get("recommended_action", "").strip() for row in cited_rows if row.get("recommended_action", "").strip()]
        unique_actions = set(actions)
        if len(actions) >= 10 and len(unique_actions) <= 1:
            raise AssertionError("Citation actions are identical across the full cited-pages export.")

    print("Smoke test passed.")


if __name__ == "__main__":
    main()
