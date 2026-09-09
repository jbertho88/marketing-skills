#!/usr/bin/env python3
"""
build_xlsx.py
Create a formatted .xlsx workbook from AI visibility metrics JSON.

Usage:
    python build_xlsx.py metrics.json workbook.xlsx
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from xml.sax.saxutils import escape


def xml(text: str) -> str:
    return text.strip() + "\n"


def escape_text(text: str) -> str:
    return escape(str(text), {'"': "&quot;"})


def excel_rgb(value: str) -> str:
    value = (value or "").strip().upper()
    if len(value) == 6:
        return "FF" + value
    return value


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


def pct(value):
    return round(float(value), 1)


def basename_date(path):
    match = re.search(r"\d{4}-\d{2}-\d{2}", os.path.basename(path or ""))
    return match.group(0) if match else ""


def presentation_bucket(bucket):
    bucket = (bucket or "").strip()
    return "Watch" if bucket in {"", "Monitor"} else bucket


def col_letter(index: int) -> str:
    out = []
    while index > 0:
        index, rem = divmod(index - 1, 26)
        out.append(chr(65 + rem))
    return "".join(reversed(out))


def numeric_value(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        if re.fullmatch(r"-?\d+", stripped):
            return int(stripped)
        if re.fullmatch(r"-?\d+\.\d+", stripped):
            return float(stripped)
    return None


def cell_xml(ref: str, value, style_id: int = 2) -> str:
    number = numeric_value(value)
    if number is not None:
        return f'<c r="{ref}" s="{style_id}"><v>{number}</v></c>'
    text = "" if value is None else str(value)
    preserve = ' xml:space="preserve"' if text[:1].isspace() or text[-1:].isspace() else ""
    return f'<c r="{ref}" s="{style_id}" t="inlineStr"><is><t{preserve}>{escape_text(text)}</t></is></c>'


STYLE_DEFAULT = 0
STYLE_HEADER = 1
STYLE_BODY = 2
STYLE_BUILD = 3
STYLE_RECLAIM = 4
STYLE_VERIFY = 5
STYLE_DEFEND = 6
STYLE_RETIRE = 7
STYLE_POSITIVE = 8
STYLE_WARNING = 9
STYLE_DANGER = 10


def style_id_for_cell(header, value):
    header = str(header or "")
    text = "" if value is None else str(value).strip()
    number = numeric_value(value)
    if header in {"Bucket", "Action bucket"}:
        return {
            "Build": STYLE_BUILD,
            "Reclaim": STYLE_RECLAIM,
            "Verify": STYLE_VERIFY,
            "Defend": STYLE_DEFEND,
            "Retire": STYLE_RETIRE,
            "Watch": STYLE_BODY,
        }.get(text, STYLE_BODY)
    if header in {"Opportunity score", "Cleanup priority", "Defense priority", "Priority", "Citation opportunity score"}:
        if text in {"Protected", "Defense priority"}:
            return STYLE_POSITIVE
        if number is None:
            return STYLE_BODY
        if float(number) >= 70:
            return STYLE_POSITIVE
        if float(number) >= 40:
            return STYLE_WARNING
        return STYLE_DANGER
    if header == "Confidence":
        return {
            "High": STYLE_POSITIVE,
            "Medium": STYLE_WARNING,
            "Low": STYLE_DANGER,
        }.get(text, STYLE_BODY)
    if header == "Effort":
        return {
            "Low": STYLE_POSITIVE,
            "Medium": STYLE_WARNING,
            "High": STYLE_DANGER,
        }.get(text, STYLE_BODY)
    return STYLE_BODY


def auto_widths(headers, rows, caps=None):
    caps = caps or {}
    widths = []
    for index, header in enumerate(headers):
        values = [str(header)]
        for row in rows[:250]:
            value = row[index] if index < len(row) else ""
            values.append(str(value if value is not None else ""))
        max_len = max((max((len(part) for part in value.splitlines()), default=0) for value in values), default=10)
        width = min(caps.get(header, 40), max(10, max_len + 2))
        widths.append(width)
    return widths


def sheet_xml(headers, rows, widths, conditional_specs=None):
    row_count = len(rows) + 1
    col_count = len(headers)
    last_cell = f"{col_letter(col_count)}{row_count}"
    cols_xml = []
    for idx, width in enumerate(widths, 1):
        cols_xml.append(f'<col min="{idx}" max="{idx}" width="{width}" customWidth="1"/>')

    sheet_rows = ['<row r="1">']
    for idx, header in enumerate(headers, 1):
        sheet_rows.append(cell_xml(f"{col_letter(idx)}1", header, style_id=1))
    sheet_rows.append("</row>")
    for row_idx, row in enumerate(rows, 2):
        sheet_rows.append(f'<row r="{row_idx}">')
        for col_idx in range(1, col_count + 1):
            header = headers[col_idx - 1]
            value = row[col_idx - 1] if col_idx - 1 < len(row) else ""
            sheet_rows.append(
                cell_xml(
                    f"{col_letter(col_idx)}{row_idx}",
                    value,
                    style_id=style_id_for_cell(header, value),
                )
            )
        sheet_rows.append("</row>")

    return xml(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
          <dimension ref="A1:{last_cell}"/>
          <sheetViews>
            <sheetView workbookViewId="0">
              <pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>
              <selection pane="bottomLeft" activeCell="A2" sqref="A2"/>
            </sheetView>
          </sheetViews>
          <sheetFormatPr defaultRowHeight="15"/>
          <cols>{''.join(cols_xml)}</cols>
          <sheetData>{''.join(sheet_rows)}</sheetData>
          <autoFilter ref="A1:{last_cell}"/>
        </worksheet>
        """
    )


def workbook_xml(sheet_names):
    sheets = []
    for index, name in enumerate(sheet_names, 1):
        sheets.append(
            f'<sheet name="{escape_text(name)}" sheetId="{index}" r:id="rId{index}"/>'
        )
    return xml(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
                  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
          <bookViews><workbookView xWindow="0" yWindow="0" windowWidth="24000" windowHeight="14000"/></bookViews>
          <sheets>{''.join(sheets)}</sheets>
        </workbook>
        """
    )


def workbook_rels_xml(sheet_count):
    rels = []
    for index in range(1, sheet_count + 1):
        rels.append(
            f'<Relationship Id="rId{index}" '
            f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{index}.xml"/>'
        )
    rels.append(
        f'<Relationship Id="rId{sheet_count + 1}" '
        f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        f'Target="styles.xml"/>'
    )
    return xml(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
          {''.join(rels)}
        </Relationships>
        """
    )


def styles_xml():
    return xml(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
          <fonts count="2">
            <font><sz val="11"/><name val="Arial"/><family val="2"/></font>
            <font><b/><sz val="11"/><name val="Arial"/><family val="2"/></font>
          </fonts>
          <fills count="12">
            <fill><patternFill patternType="none"/></fill>
            <fill><patternFill patternType="gray125"/></fill>
            <fill><patternFill patternType="solid"><fgColor rgb="{excel_rgb('D9EEF2')}"/><bgColor indexed="64"/></patternFill></fill>
            <fill><patternFill patternType="solid"><fgColor rgb="{excel_rgb('FFFFFF')}"/><bgColor indexed="64"/></patternFill></fill>
            <fill><patternFill patternType="solid"><fgColor rgb="{excel_rgb('DDEBF7')}"/><bgColor indexed="64"/></patternFill></fill>
            <fill><patternFill patternType="solid"><fgColor rgb="{excel_rgb('FCE4D6')}"/><bgColor indexed="64"/></patternFill></fill>
            <fill><patternFill patternType="solid"><fgColor rgb="{excel_rgb('FFF2CC')}"/><bgColor indexed="64"/></patternFill></fill>
            <fill><patternFill patternType="solid"><fgColor rgb="{excel_rgb('E2F0D9')}"/><bgColor indexed="64"/></patternFill></fill>
            <fill><patternFill patternType="solid"><fgColor rgb="{excel_rgb('EDEDED')}"/><bgColor indexed="64"/></patternFill></fill>
            <fill><patternFill patternType="solid"><fgColor rgb="{excel_rgb('C6EFCE')}"/><bgColor indexed="64"/></patternFill></fill>
            <fill><patternFill patternType="solid"><fgColor rgb="{excel_rgb('FFEB9C')}"/><bgColor indexed="64"/></patternFill></fill>
            <fill><patternFill patternType="solid"><fgColor rgb="{excel_rgb('F4CCCC')}"/><bgColor indexed="64"/></patternFill></fill>
          </fills>
          <borders count="2">
            <border/>
            <border>
              <left style="thin"><color rgb="{excel_rgb('D0D7DE')}"/></left>
              <right style="thin"><color rgb="{excel_rgb('D0D7DE')}"/></right>
              <top style="thin"><color rgb="{excel_rgb('D0D7DE')}"/></top>
              <bottom style="thin"><color rgb="{excel_rgb('D0D7DE')}"/></bottom>
            </border>
          </borders>
          <cellStyleXfs count="1">
            <xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>
          </cellStyleXfs>
          <cellXfs count="11">
            <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
            <xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
              <alignment horizontal="center" vertical="center" wrapText="1"/>
            </xf>
            <xf numFmtId="0" fontId="0" fillId="3" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1">
              <alignment vertical="top" wrapText="1"/>
            </xf>
            <xf numFmtId="0" fontId="0" fillId="4" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
            <xf numFmtId="0" fontId="0" fillId="5" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
            <xf numFmtId="0" fontId="0" fillId="6" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
            <xf numFmtId="0" fontId="0" fillId="7" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
            <xf numFmtId="0" fontId="0" fillId="8" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
            <xf numFmtId="0" fontId="0" fillId="9" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
            <xf numFmtId="0" fontId="0" fillId="10" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
            <xf numFmtId="0" fontId="0" fillId="11" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
          </cellXfs>
          <cellStyles count="1">
            <cellStyle name="Normal" xfId="0" builtinId="0"/>
          </cellStyles>
          <dxfs count="0"/>
        </styleSheet>
        """
    )


def root_rels_xml():
    return xml(
        """
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
          <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
          <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
          <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
        </Relationships>
        """
    )


def content_types_xml(sheet_count):
    overrides = [
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
    ]
    for index in range(1, sheet_count + 1):
        overrides.append(
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
            f'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    return xml(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
          <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
          <Default Extension="xml" ContentType="application/xml"/>
          {''.join(overrides)}
        </Types>
        """
    )


def core_xml():
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return xml(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
                           xmlns:dc="http://purl.org/dc/elements/1.1/"
                           xmlns:dcterms="http://purl.org/dc/terms/"
                           xmlns:dcmitype="http://purl.org/dc/dcmitype/"
                           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
          <dc:title>AI Visibility Workbook</dc:title>
          <dc:creator>Codex</dc:creator>
          <cp:lastModifiedBy>Codex</cp:lastModifiedBy>
          <dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>
          <dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>
        </cp:coreProperties>
        """
    )


def app_xml(sheet_names):
    titles = "".join(f"<vt:lpstr>{escape_text(name)}</vt:lpstr>" for name in sheet_names)
    return xml(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
                    xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
          <Application>Codex</Application>
          <HeadingPairs>
            <vt:vector size="2" baseType="variant">
              <vt:variant><vt:lpstr>Worksheets</vt:lpstr></vt:variant>
              <vt:variant><vt:i4>{len(sheet_names)}</vt:i4></vt:variant>
            </vt:vector>
          </HeadingPairs>
          <TitlesOfParts>
            <vt:vector size="{len(sheet_names)}" baseType="lpstr">
              {titles}
            </vt:vector>
          </TitlesOfParts>
        </Properties>
        """
    )


def model_topic_rows(metrics):
    source = metrics["topic_mapping"]["report_topics_source"]
    topics = metrics.get("report_topics") or metrics["topics"]
    recs = metrics["recommendations"]
    bucket_by_topic = defaultdict(Counter)
    topic_field = "report_topic" if source == "fallback" else "primary_topic"
    for rec in recs:
        topic = rec.get(topic_field) or rec.get("report_topic") or rec.get("primary_topic") or "general category queries"
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
            rows.append([
                titleish(topic),
                model["model"],
                coverage["prompts"],
                pct(coverage["visibility_rate_pct"]),
                coverage["average_rank"] if coverage["average_rank"] is not None else "",
                coverage["weak_or_absent"],
                presentation_bucket(bucket_by_topic[topic].most_common(1)[0][0] if bucket_by_topic[topic] else "Watch"),
            ])
    return rows


def dashboard_rows(metrics):
    per_model = metrics.get("per_model", [])
    visibility_values = [item["totals"]["visibility_rate_pct"] for item in per_model]
    strongest_model = max(per_model, key=lambda item: item["totals"]["visibility_rate_pct"])["model"] if per_model else ""
    weakest_model = min(per_model, key=lambda item: item["totals"]["visibility_rate_pct"])["model"] if per_model else ""
    topic_source = metrics.get("topic_mapping", {}).get("report_topics_source", "")
    weakest_topic = ""
    weakest_score = None
    for topic in metrics.get("report_topics") or metrics.get("topics", []):
        total_weight = 0
        weighted_vis = 0.0
        for model in per_model:
            coverage = (
                model["report_topic_coverage"].get(topic, {})
                if topic_source == "fallback"
                else model["topic_coverage"].get(topic, {})
            )
            prompts = coverage.get("prompts", 0)
            if prompts <= 0:
                continue
            total_weight += prompts
            weighted_vis += coverage["visibility_rate_pct"] * prompts
        if total_weight:
            score = weighted_vis / total_weight
            if weakest_score is None or score < weakest_score:
                weakest_score = score
                weakest_topic = topic
    plays = metrics.get("strategic_plays", [])
    top_play = plays[0] if plays else {}
    competitor = metrics.get("competitor_analysis", [{}])[0].get("brand", "") if metrics.get("competitor_analysis") else ""
    citation = metrics.get("citation_analysis", {})
    citation_summary = citation.get("summary", {})
    recommended_next = top_play.get("execution_notes") or top_play.get("play_name") or ""
    if not recommended_next and citation.get("page_opportunities"):
        recommended_next = citation["page_opportunities"][0].get("recommended_action", "")
    return [
        ["Brand", metrics.get("brand", "")],
        ["Snapshot date", basename_date(metrics.get("appendix_csv", ""))],
        ["Models analyzed", ", ".join(metrics.get("models_analyzed", []))],
        ["Prompts per model", per_model[0]["totals"]["prompts"] if per_model else ""],
        ["Overall visibility", round(sum(visibility_values) / max(1, len(visibility_values)), 1) if visibility_values else ""],
        ["Top competitor", competitor],
        ["Strongest model", strongest_model],
        ["Weakest model/topic", f"{weakest_model} / {titleish(weakest_topic)}" if weakest_topic else weakest_model],
        ["Highest-priority play", top_play.get("play_name", "")],
        ["Top citation opportunity domain", citation_summary.get("top_opportunity_domains", [""])[0] if citation_summary.get("top_opportunity_domains") else ""],
        ["No-brand cited pages", citation_summary.get("no_brand_pages", "") if citation.get("enabled") else ""],
        ["Cross-model no-brand pages", citation_summary.get("cross_model_no_brand_pages", "") if citation.get("enabled") else ""],
        ["Recommended next action", recommended_next],
    ]


def action_plan_rows(metrics):
    rows = []
    bucket_order = {"Build": 0, "Reclaim": 1, "Verify": 2, "Defend": 3, "Retire": 4}
    recs = sorted(
        metrics["recommendations"],
        key=lambda rec: (
            bucket_order.get(rec["action_bucket"], 9),
            -float(rec.get("opportunity_score") or rec.get("cleanup_priority") or rec.get("priority_score") or 0),
            rec["prompt"].lower(),
        ),
    )
    for rec in recs:
        rows.append([
            rec["prompt"],
            presentation_bucket(rec["action_bucket"]),
            rec.get("recommended_play", ""),
            titleish(rec.get("report_topic") or rec.get("primary_topic") or ""),
            titleish(rec.get("prompt_cluster") or ""),
            ", ".join(rec.get("affected_models", [])),
            ", ".join(rec.get("competitor_winners", [])),
            rec.get("opportunity_score", ""),
            rec.get("cleanup_priority", ""),
            rec.get("defense_priority", ""),
            titleish(rec.get("confidence", "")),
            titleish(rec.get("effort", "")),
            rec.get("primary_owner", rec.get("suggested_owner", "")),
            rec.get("action_type", ""),
            rec.get("recommended_asset_type", ""),
            rec.get("next_step", ""),
            rec.get("status", ""),
            rec.get("due_date", ""),
            rec.get("source_evidence_reference", ""),
            rec.get("recommended_action", ""),
        ])
    return rows


def strategic_play_rows(metrics):
    rows = []
    group_label = {
        "Build": "Strategic growth",
        "Reclaim": "Strategic growth",
        "Verify": "Strategic growth",
        "Retire": "Portfolio cleanup",
        "Defend": "Defense",
    }
    for play in metrics.get("strategic_plays", []):
        supporting = play.get("supporting_items") or play.get("supporting_prompts", [])
        group = "Citation influence" if play.get("play_type") == "citation" else group_label.get(play["bucket"], play["bucket"])
        rows.append([
            play["play_name"],
            group,
            presentation_bucket(play["bucket"]),
            titleish(play.get("play_type", "prompt")),
            titleish(play.get("topic", "")),
            titleish(play.get("prompt_cluster", "")),
            ", ".join(play.get("affected_models", [])),
            ", ".join(play.get("competitor_threat", [])),
            play.get("opportunity_score", ""),
            play.get("cleanup_priority", ""),
            play.get("defense_priority", ""),
            titleish(play.get("confidence", "")),
            titleish(play.get("effort", "")),
            play.get("suggested_owner", ""),
            play.get("action_type", ""),
            play.get("recommended_asset_type", ""),
            play.get("recommended_assets", ""),
            play.get("why_it_matters", ""),
            play.get("execution_notes", ""),
            play.get("example_language_angle", ""),
            ", ".join(supporting),
        ])
    return rows


def portfolio_cleanup_rows(metrics):
    rows = []
    cleanup = [
        rec for rec in metrics["recommendations"]
        if rec["action_bucket"] == "Retire" or rec.get("duplicate_of")
    ]
    cleanup.sort(
        key=lambda rec: (
            -(float(rec.get("cleanup_priority") or 0)),
            rec["prompt"].lower(),
        )
    )
    for rec in cleanup:
        rows.append([
            rec["prompt"],
            titleish(rec.get("report_topic") or rec.get("primary_topic") or ""),
            titleish(rec.get("prompt_cluster") or ""),
            rec.get("cleanup_priority", ""),
            rec.get("duplicate_of", ""),
            rec.get("action_type", ""),
            rec.get("next_step", ""),
            rec.get("recommended_action", ""),
            titleish(rec.get("confidence", "")),
            titleish(rec.get("effort", "")),
            rec.get("primary_owner", rec.get("suggested_owner", "")),
            rec.get("source_evidence_reference", ""),
            ", ".join(rec.get("competitor_winners", [])),
        ])
    return rows


def prompt_appendix_rows(metrics):
    records = metrics.get("appendix_records", [])
    models = metrics.get("models_analyzed", [])
    rows = []
    for record in records:
        base = [
            record.get("prompt", ""),
            record.get("primary_topic", ""),
            record.get("report_topic", ""),
            record.get("topics", ""),
            record.get("configured_topics", ""),
            record.get("fallback_topics", ""),
            record.get("prompt_cluster", ""),
            record.get("persona_use_case_cluster", ""),
            record.get("intent", ""),
            record.get("funnel_stage", ""),
            record.get("gap_type", ""),
            record.get("gap_type_code", ""),
            record.get("gap_summary", ""),
            record.get("recommended_play", ""),
            record.get("fix_type_code", ""),
            record.get("recommended_asset_type", ""),
            record.get("next_step", ""),
            record.get("action_type", ""),
            presentation_bucket(record.get("action_bucket", "")),
            record.get("priority_score", ""),
            record.get("opportunity_score", ""),
            record.get("cleanup_priority", ""),
            record.get("defense_priority", ""),
            record.get("confidence", ""),
            record.get("effort", ""),
            record.get("primary_owner", record.get("suggested_owner", "")),
            record.get("status", ""),
            record.get("due_date", ""),
            record.get("source_evidence_reference", ""),
            record.get("competitor_winners", ""),
            record.get("reason_summary", ""),
            record.get("recommended_action", ""),
            record.get("recommended_assets", ""),
        ]
        for model in models:
            base.append(record.get(f"rank_{model}", ""))
        for model in models:
            base.append(record.get(f"status_{model}", ""))
        rows.append(base)
    return rows


def citation_action_plan_rows(metrics):
    citation = metrics.get("citation_analysis", {})
    if not citation.get("enabled"):
        return []
    rows = []
    pages = sorted(
        citation.get("page_opportunities", []),
        key=lambda page: (-float(page.get("citation_opportunity_score") or 0), page.get("canonical_url", "")),
    )
    for page in pages:
        rows.append([
            page.get("citation_opportunity_score", ""),
            page.get("canonical_url", ""),
            page.get("root_domain", ""),
            titleish((page.get("page_type") or "").replace("_", " ")),
            page.get("opportunity_type", ""),
            page.get("model_count", ""),
            ", ".join(page.get("models_cited", [])),
            page.get("cited_in_prompts_total_deduped", ""),
            page.get("brand_mentioned_status", ""),
            page.get("PA Score", ""),
            page.get("Spam Score", ""),
            page.get("Linking Pages", ""),
            page.get("citation_opportunity_score", ""),
            page.get("action_type", ""),
            page.get("recommended_action", ""),
            page.get("owner", ""),
            titleish(page.get("effort", "")),
            titleish(page.get("confidence", "")),
            page.get("status", ""),
            page.get("due_date", ""),
            page.get("source_evidence_reference", ""),
            page.get("notes", ""),
        ])
    return rows


def cited_pages_rows(metrics):
    citation = metrics.get("citation_analysis", {})
    if not citation.get("enabled"):
        return []
    rows = []
    for page in citation.get("page_opportunities", []):
        rows.append([
            page.get("canonical_url", ""),
            page.get("raw_url", ""),
            page.get("root_domain", ""),
            page.get("domain", ""),
            page.get("path", ""),
            page.get("page_title", ""),
            ", ".join(page.get("models_cited", [])),
            page.get("model_count", ""),
            page.get("cited_in_prompts_total_deduped", ""),
            json.dumps(page.get("cited_in_prompts_by_model", {}), ensure_ascii=False),
            page.get("cited_in_prompts_sum_raw", ""),
            page.get("raw_duplicate_count", ""),
            page.get("fragment_count", ""),
            page.get("brand_mentioned_status", ""),
            page.get("PA Score", ""),
            page.get("Spam Score", ""),
            page.get("Linking Pages", ""),
            "Yes" if page.get("owned_domain") else "No",
            titleish((page.get("page_type") or "").replace("_", " ")),
            page.get("opportunity_type", ""),
            page.get("citation_opportunity_score", ""),
            page.get("action_type", ""),
            page.get("owner", ""),
            titleish(page.get("effort", "")),
            titleish(page.get("confidence", "")),
            page.get("recommended_action", ""),
            page.get("derived_report_topic", ""),
            page.get("derived_prompt_cluster", ""),
            page.get("mapping_confidence", ""),
            page.get("source_evidence_reference", ""),
            page.get("notes", ""),
        ])
    return rows


def citation_domain_rows(metrics):
    citation = metrics.get("citation_analysis", {})
    if not citation.get("enabled"):
        return []
    rows = []
    for domain in citation.get("domain_opportunities", []):
        rows.append([
            domain.get("root_domain", ""),
            domain.get("page_count", ""),
            domain.get("canonical_page_count", ""),
            domain.get("model_count", ""),
            ", ".join(domain.get("models_cited", [])),
            domain.get("total_cited_prompts_deduped", ""),
            domain.get("pages_without_brand", ""),
            domain.get("pages_with_brand", ""),
            domain.get("percent_pages_without_brand", ""),
            domain.get("avg_PA", ""),
            domain.get("avg_Spam", ""),
            domain.get("total_linking_pages", ""),
            titleish((domain.get("top_page_type") or "").replace("_", " ")),
            domain.get("domain_opportunity_score", ""),
            domain.get("recommended_domain_action", ""),
            ", ".join(domain.get("top_pages", [])),
        ])
    return rows


def cross_model_citation_rows(metrics):
    citation = metrics.get("citation_analysis", {})
    if not citation.get("enabled"):
        return []
    cross = citation.get("cross_model_opportunities", {})
    rows = []
    for label, pages in [
        ("Cited in all models", cross.get("pages_all_models", [])),
        ("Cited in 2 models", cross.get("pages_two_models", [])),
        ("Cited in 1 model", cross.get("pages_one_model", [])),
    ]:
        for page in pages:
            rows.append([
                label,
                page.get("canonical_url", ""),
                page.get("root_domain", ""),
                ", ".join(page.get("models_cited", [])),
                page.get("brand_mentioned_status", ""),
                page.get("citation_opportunity_score", ""),
                page.get("action_type", ""),
                page.get("recommended_action", ""),
            ])
    return rows


def model_citation_trend_rows(metrics):
    citation = metrics.get("citation_analysis", {})
    if not citation.get("enabled"):
        return []
    rows = []
    for trend in citation.get("model_trends", []):
        rows.append([
            trend.get("model", ""),
            trend.get("canonical_pages", ""),
            trend.get("raw_rows", ""),
            trend.get("duplicate_count", ""),
            trend.get("no_brand_page_count", ""),
            trend.get("brand_mentioned_page_count", ""),
            ", ".join(trend.get("top_domains", [])),
            ", ".join(f"{titleish(k.replace('_', ' '))}: {v}" for k, v in trend.get("page_type_mix", {}).items()),
            trend.get("notes", ""),
        ])
    return rows


def data_dictionary_rows(metrics):
    snapshot = basename_date(metrics.get("appendix_csv", ""))
    rows = [
        ["Snapshot date", "Workbook", f"Snapshot date derived from output filename metadata: {snapshot or 'not found'}."],
        ["action_bucket", "Action Plan / Appendix", "Primary recommendation bucket: Defend, Reclaim, Build, Verify, Retire, or Watch."],
        ["action_type", "Action Plan / Strategic Plays / Citation Action Plan / Appendix", "Execution motion such as content refresh, prompt cleanup, reviewer brief, or owned-page defense."],
        ["opportunity_score", "Action Plan / Strategic Plays / Appendix", "Priority score for Build, Reclaim, and Verify actions. Higher means stronger growth opportunity."],
        ["cleanup_priority", "Portfolio Cleanup / Appendix", "Priority score used for Retire and consolidation actions. Higher means faster cleanup value."],
        ["defense_priority", "Action Plan / Strategic Plays / Appendix", "Text field used for Defend items so the report does not show misleading 0.0 opportunity scores."],
        ["recommended_asset_type", "Action Plan / Strategic Plays / Appendix", "Primary marketing asset format recommended for the action."],
        ["next_step", "Action Plan / Portfolio Cleanup / Appendix", "Short operational next step for the owner."],
        ["status", "Action Plan", "Blank execution-tracking field for the operator to mark progress after the workbook is delivered."],
        ["due_date", "Action Plan / Citation Action Plan / Appendix", "Blank planning field for the operator to add a due date."],
        ["notes", "Action Plan", "Blank operator notes field for follow-up detail, blockers, or QA annotations."],
        ["source_evidence_reference", "Action Plan / Citation Action Plan / Appendix", "Short evidence pointer showing the prompt, page, or source that triggered the action."],
        ["primary_owner", "Action Plan / Portfolio Cleanup / Appendix", "Standardized suggested owner for execution."],
        ["report_topic", "All analysis tabs", "Fallback or refined topic family used for executive reporting when custom topic mapping is sparse."],
        ["prompt_cluster", "All analysis tabs", "Prompt-level cluster used to group related queries into more useful campaign plays."],
        ["persona_use_case_cluster", "Prompt Appendix", "Audience or use-case cluster inferred from prompt language."],
        ["gap_type", "Prompt Appendix", "Human-readable gap label for client-facing review."],
        ["gap_type_code", "Prompt Appendix", "Internal machine-readable gap code for QA and filtering."],
        ["confidence", "Action Plan / Strategic Plays / Portfolio Cleanup / Appendix", "Confidence in the recommendation logic based on observed prompt and response patterns."],
        ["effort", "Action Plan / Strategic Plays / Portfolio Cleanup / Appendix", "Estimated execution effort level for the recommendation."],
    ]
    if metrics.get("citation_analysis", {}).get("enabled"):
        rows.extend([
            ["citation_opportunity_score", "Citation Action Plan / Cited Pages / Cross-Model Citations", "Priority score for cited-page influence opportunities based on brand absence, model breadth, prompt citations, page authority, link signals, spam, and page type."],
            ["opportunity_type", "Citation Action Plan / Cited Pages", "Primary citation classification such as all-model inclusion opportunity, citation amplification opportunity, or competitor citation threat."],
            ["brand_mentioned_status", "Citation Action Plan / Cited Pages / Cross-Model Citations", "Whether the cited page mentions the tracked brand across duplicates and models: Yes, No, Mixed, or Unknown."],
            ["domain_opportunity_score", "Citation Domains", "Aggregate priority score for domains that repeatedly influence AI answers."],
        ])
    return rows


def build_sheet_specs(metrics):
    models = metrics.get("models_analyzed", [])
    citation_enabled = metrics.get("citation_analysis", {}).get("enabled")
    action_headers = [
        "Prompt", "Bucket", "Strategic play", "Topic", "Prompt cluster", "Affected models",
        "Competitor threat", "Opportunity score", "Cleanup priority", "Defense priority",
        "Confidence", "Effort", "Owner", "Action type", "Asset type", "Next step", "Status", "Due date", "Source / evidence",
        "Recommended action",
    ]
    appendix_headers = [
        "Prompt", "Primary topic", "Report topic", "Topics", "Configured topics", "Fallback topics",
        "Prompt cluster", "Persona / use-case cluster", "Intent", "Funnel stage", "Gap type",
        "Gap type code", "Gap summary", "Recommended play", "Fix type code", "Recommended asset type",
        "Next step", "Action type", "Action bucket", "Priority score", "Opportunity score", "Cleanup priority",
        "Defense priority", "Confidence", "Effort", "Owner", "Status", "Due date", "Source / evidence", "Competitor winners", "Reason summary",
        "Recommended action", "Recommended assets",
    ] + [f"Rank: {model}" for model in models] + [f"Status: {model}" for model in models]
    strategic_headers = [
        "Play name", "Group", "Bucket", "Play type", "Topic", "Prompt cluster", "Affected models", "Competitor threat",
        "Opportunity score", "Cleanup priority", "Defense priority", "Confidence", "Effort", "Owner", "Action type",
        "Asset type", "Recommended assets", "Why it matters", "Execution notes", "Example language angle",
        "Supporting evidence",
    ]
    model_topic_headers = [
        "Topic", "Model", "Prompt count", "Visibility %", "Avg rank", "Weak / absent count", "Action bucket",
    ]
    cleanup_headers = [
        "Prompt", "Topic", "Prompt cluster", "Cleanup priority", "Duplicate of", "Action type", "Next step",
        "Recommended action", "Confidence", "Effort", "Owner", "Source / evidence", "Competitor winners",
    ]
    dictionary_headers = ["Field", "Used in", "Meaning"]
    sheets = [
        {
            "name": "Dashboard",
            "headers": ["Metric", "Value"],
            "rows": dashboard_rows(metrics),
            "widths": [28, 72],
            "conditional_specs": [],
        },
        {
            "name": "Action Plan",
            "headers": action_headers,
            "rows": action_plan_rows(metrics),
            "widths": auto_widths(action_headers, action_plan_rows(metrics), caps={
                "Prompt": 42, "Strategic play": 32, "Topic": 24, "Prompt cluster": 28,
                "Affected models": 20, "Competitor threat": 24, "Action type": 22, "Asset type": 24,
                "Next step": 32, "Status": 16, "Due date": 14, "Source / evidence": 28, "Recommended action": 52,
            }),
            "conditional_specs": [
                {"col": 2, "type": "bucket"},
                {"col": 8, "type": "score"},
                {"col": 9, "type": "score"},
                {"col": 10, "type": "score"},
                {"col": 11, "type": "confidence"},
                {"col": 12, "type": "effort"},
            ],
        },
        {
            "name": "Prompt Appendix",
            "headers": appendix_headers,
            "rows": prompt_appendix_rows(metrics),
            "widths": auto_widths(appendix_headers, prompt_appendix_rows(metrics), caps={
                "Prompt": 42, "Topics": 28, "Configured topics": 28, "Fallback topics": 30,
                "Prompt cluster": 28, "Persona / use-case cluster": 28, "Gap summary": 36,
                "Reason summary": 36, "Recommended action": 52, "Recommended assets": 36,
                "Recommended play": 32, "Competitor winners": 28, "Next step": 28, "Action type": 22,
                "Source / evidence": 28,
            }),
            "conditional_specs": [
                {"col": 19, "type": "bucket"},
                {"col": 21, "type": "score"},
                {"col": 22, "type": "score"},
                {"col": 23, "type": "score"},
                {"col": 24, "type": "confidence"},
                {"col": 25, "type": "effort"},
            ],
        },
        {
            "name": "Strategic Plays",
            "headers": strategic_headers,
            "rows": strategic_play_rows(metrics),
            "widths": auto_widths(strategic_headers, strategic_play_rows(metrics), caps={
                "Play name": 30, "Topic": 24, "Prompt cluster": 28, "Affected models": 20,
                "Competitor threat": 24, "Action type": 22, "Asset type": 24, "Recommended assets": 34,
                "Why it matters": 44, "Execution notes": 48, "Example language angle": 48,
                "Supporting evidence": 48,
            }),
            "conditional_specs": [
                {"col": 3, "type": "bucket"},
                {"col": 9, "type": "score"},
                {"col": 10, "type": "score"},
                {"col": 11, "type": "score"},
                {"col": 12, "type": "confidence"},
                {"col": 13, "type": "effort"},
            ],
        },
        {
            "name": "Model x Topic",
            "headers": model_topic_headers,
            "rows": model_topic_rows(metrics),
            "widths": auto_widths(model_topic_headers, model_topic_rows(metrics), caps={
                "Topic": 30, "Model": 18, "Action bucket": 16,
            }),
            "conditional_specs": [
                {"col": 7, "type": "bucket"},
                {"col": 4, "type": "score"},
            ],
        },
        {
            "name": "Portfolio Cleanup",
            "headers": cleanup_headers,
            "rows": portfolio_cleanup_rows(metrics),
            "widths": auto_widths(cleanup_headers, portfolio_cleanup_rows(metrics), caps={
                "Prompt": 42, "Topic": 24, "Prompt cluster": 28, "Duplicate of": 42,
                "Next step": 28, "Recommended action": 50, "Source / evidence": 28, "Competitor winners": 24,
            }),
            "conditional_specs": [
                {"col": 4, "type": "score"},
                {"col": 8, "type": "confidence"},
                {"col": 9, "type": "effort"},
            ],
        },
        {
            "name": "Data Dictionary",
            "headers": dictionary_headers,
            "rows": data_dictionary_rows(metrics),
            "widths": [28, 26, 72],
            "conditional_specs": [],
        },
    ]

    if citation_enabled:
        citation_action_headers = [
            "Priority", "Canonical URL", "Root domain", "Page type", "Opportunity type", "Model count",
            "Models cited", "Cited in prompts", "Brand mentioned status", "PA Score", "Spam Score",
            "Linking Pages", "Citation opportunity score", "Action type", "Recommended action", "Owner", "Effort",
            "Confidence", "Status", "Due date", "Source / evidence", "Notes",
        ]
        cited_pages_headers = [
            "Canonical URL", "Raw URL", "Root domain", "Domain", "Path", "Page title", "Models cited",
            "Model count", "Cited in prompts total deduped", "Cited in prompts by model",
            "Cited in prompts raw sum", "Raw duplicate count", "Fragment count", "Brand mentioned status",
            "PA Score", "Spam Score", "Linking Pages", "Owned domain", "Page type", "Opportunity type",
            "Citation opportunity score", "Action type", "Owner", "Effort", "Confidence", "Recommended action",
            "Derived report topic", "Derived prompt cluster", "Mapping confidence", "Source / evidence", "Notes",
        ]
        citation_domain_headers = [
            "Root domain", "Page count", "Canonical page count", "Model count", "Models cited",
            "Total cited prompts", "Pages without brand", "Pages with brand", "% pages without brand",
            "Avg PA", "Avg Spam", "Total linking pages", "Top page type", "Domain opportunity score",
            "Recommended domain action", "Top pages",
        ]
        cross_model_headers = [
            "Cross-model group", "Canonical URL", "Root domain", "Models cited", "Brand mentioned status",
            "Score", "Action type", "Action",
        ]
        model_trend_headers = [
            "Model", "Canonical pages", "Raw rows", "Duplicate count", "No-brand page count",
            "Brand-mentioned page count", "Top domains", "Page type mix", "Notes",
        ]
        sheets.extend([
            {
                "name": "Citation Action Plan",
                "headers": citation_action_headers,
                "rows": citation_action_plan_rows(metrics),
                "widths": auto_widths(citation_action_headers, citation_action_plan_rows(metrics), caps={
                    "Canonical URL": 56, "Root domain": 24, "Action type": 20, "Recommended action": 52, "Source / evidence": 28, "Notes": 34,
                }),
                "conditional_specs": [
                    {"col": 1, "type": "score"},
                    {"col": 13, "type": "score"},
                    {"col": 17, "type": "effort"},
                    {"col": 18, "type": "confidence"},
                ],
            },
            {
                "name": "Cited Pages",
                "headers": cited_pages_headers,
                "rows": cited_pages_rows(metrics),
                "widths": auto_widths(cited_pages_headers, cited_pages_rows(metrics), caps={
                    "Canonical URL": 56, "Raw URL": 56, "Path": 28, "Page title": 32,
                    "Cited in prompts by model": 28, "Recommended action": 52, "Derived report topic": 24,
                    "Derived prompt cluster": 24, "Source / evidence": 28, "Notes": 34,
                }),
                "conditional_specs": [
                    {"col": 21, "type": "score"},
                    {"col": 24, "type": "effort"},
                    {"col": 25, "type": "confidence"},
                ],
            },
            {
                "name": "Citation Domains",
                "headers": citation_domain_headers,
                "rows": citation_domain_rows(metrics),
                "widths": auto_widths(citation_domain_headers, citation_domain_rows(metrics), caps={
                    "Root domain": 26, "Models cited": 22, "Recommended domain action": 56, "Top pages": 56,
                }),
                "conditional_specs": [
                    {"col": 14, "type": "score"},
                ],
            },
            {
                "name": "Cross-Model Citations",
                "headers": cross_model_headers,
                "rows": cross_model_citation_rows(metrics),
                "widths": auto_widths(cross_model_headers, cross_model_citation_rows(metrics), caps={
                    "Canonical URL": 56, "Root domain": 24, "Action": 56,
                }),
                "conditional_specs": [
                    {"col": 6, "type": "score"},
                ],
            },
            {
                "name": "Model Citation Trends",
                "headers": model_trend_headers,
                "rows": model_citation_trend_rows(metrics),
                "widths": auto_widths(model_trend_headers, model_citation_trend_rows(metrics), caps={
                    "Top domains": 34, "Page type mix": 36, "Notes": 48,
                }),
                "conditional_specs": [],
            },
        ])
    return sheets


def write_workbook(out_path: Path, sheet_specs):
    sheet_names = [sheet["name"] for sheet in sheet_specs]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml(len(sheet_specs)))
        zf.writestr("_rels/.rels", root_rels_xml())
        zf.writestr("docProps/core.xml", core_xml())
        zf.writestr("docProps/app.xml", app_xml(sheet_names))
        zf.writestr("xl/workbook.xml", workbook_xml(sheet_names))
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml(len(sheet_specs)))
        zf.writestr("xl/styles.xml", styles_xml())
        for index, sheet in enumerate(sheet_specs, 1):
            zf.writestr(
                f"xl/worksheets/sheet{index}.xml",
                sheet_xml(sheet["headers"], sheet["rows"], sheet["widths"], sheet.get("conditional_specs")),
            )


def main():
    if len(sys.argv) != 3:
        print("Usage: python build_xlsx.py <metrics.json> <report.xlsx>")
        sys.exit(1)
    metrics_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    sheets = build_sheet_specs(metrics)
    write_workbook(out_path, sheets)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
