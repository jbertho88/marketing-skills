#!/usr/bin/env python3
"""Build the backlink gap workbook from a findings JSON file.

Usage
-----
    python build_workbook.py findings.json --out "Client_Backlink_Gap_2026-08-21.xlsx"
    python build_workbook.py --print-schema
    python build_workbook.py --example > findings.json

Design notes
------------
Score and Decision are written as live Excel formulas, never as Python-computed numbers, so an
analyst who disagrees with a relevance call can edit the factor cell and watch the decision
change. The Summary tab counts off those same formulas for the same reason.

Only Excel-2007-era functions are used (SUM, COUNTIF, COUNTA, IF, IFERROR). Newer array
functions such as FILTER/UNIQUE/SORT cannot be evaluated by the LibreOffice recalculation step
and would ship as #NAME? errors.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from integrity import (normalize_domain, evidence_ready, audit_ready, decision, counts, count_line,
                       coverage_problems, prepare, validate_plan, validate_partial_reasons)
from typing import Any

try:
    from openpyxl import Workbook
    from openpyxl.formatting.rule import CellIsRule
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
except ImportError:  # pragma: no cover
    sys.exit("openpyxl is required:  pip install openpyxl")

FONT = "Arial"

# ---------------------------------------------------------------- palette
INK = "1F2A36"
HEAD_BG = "17497A"
HEAD_FG = "FFFFFF"
BAND = "F2F5F8"
INPUT_BG = "FFF6D8"      # cells a human is expected to edit
GO_BG, GO_FG = "E4F1EA", "1F6B45"
HOLD_BG, HOLD_FG = "F6EEDD", "8A5A0C"
NO_BG, NO_FG = "F8E7E4", "A33529"
FLAG_BG = "F8E7E4"

THIN = Side(style="thin", color="D2D9DE")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

# ---------------------------------------------------------------- sheet specs
# (json_key, sheet_title, [(header, json_field, width, kind), ...])
# kind: t=text  n=number  d=date  u=url-ish text  s=score-input
SHEETS: list[tuple[str, str, list[tuple[str, str, int, str]]]] = [
    ("serp_benchmark", "S1. SERP Link Benchmark", [
        ("Pos", "position", 6, "n"),
        ("Ranking URL", "url", 54, "u"),
        ("Domain", "domain", 26, "t"),
        ("DA", "da", 7, "n"),
        ("PA", "pa", 7, "n"),
        ("Domains -> page", "domains_to_page", 16, "n"),
        ("Links -> page", "links_to_page", 14, "n"),
        ("of which indirect", "indirect_domains", 17, "n"),
        ("of which nofollow", "nofollow_domains", 17, "n"),
        ("Domains -> site", "domains_to_site", 16, "n"),
        ("Concentration", None, 14, "n"),        # formula
        ("Indexed?", "indexed", 11, "t"),
        ("Mechanic", "mechanic", 20, "t"),
        ("Read", "read", 46, "t"),
    ]),
    ("serp_competitors", "1. SERP Competitors", [
        ("Target Keyword", "keyword", 30, "t"),
        ("Target Page", "target_page", 38, "u"),
        ("Ranking domains (top 10)", "ranking_domains", 52, "t"),
        ("Client position", "client_rank", 14, "n"),
        ("Recurring? (SERP competitor)", "recurring", 30, "t"),
        ("Overlap with client top-25", "overlap", 22, "n"),
        ("Verdict", "verdict", 16, "t"),
        ("Note", "note", 40, "t"),
    ]),
    ("link_gap", "2. Link Gap", [
        ("Domain", "domain", 30, "t"),
        ("Linking page", "linking_page", 52, "u"),
        ("Links to (competitors)", "competitors", 30, "t"),
        ("# Competitors linking", "n_competitors", 18, "n"),
        ("DA", "da", 7, "n"),
        ("Spam", "spam", 8, "n"),
        ("TF", "tf", 7, "n"),
        ("Topical TF", "topical_tf", 11, "n"),
        ("Traffic", "traffic", 11, "n"),
        ("First Seen", "first_seen", 12, "d"),
        ("Note", "note", 40, "t"),
    ]),
    ("recently_earned", "3. Recently Earned (60d)", [
        ("Domain", "domain", 30, "t"),
        ("Competitor", "competitor", 26, "t"),
        ("DA", "da", 7, "n"),
        ("Spam", "spam", 8, "n"),
        ("Traffic", "traffic", 11, "n"),
        ("Date gained", "date_gained", 12, "d"),
        ("Also in gap list?", "in_gap", 16, "t"),
        ("Apparent mechanism", "mechanism", 40, "t"),
        ("Note", "note", 36, "t"),
    ]),
    ("strongest_links", "4. Strongest Links", [
        ("Domain", "domain", 30, "t"),
        ("Competitor", "competitor", 26, "t"),
        ("DA", "da", 7, "n"),
        ("Spam", "spam", 8, "n"),
        ("Follow links", "follow_pages", 12, "n"),
        ("Nofollow links", "nofollow_pages", 14, "n"),
        ("Achievable?", "achievable", 13, "t"),
        ("Route in", "route_in", 40, "t"),
    ]),
    ("competitor_top_pages", "P1. Competitor Top Pages", [
        ("Competitor", "competitor", 24, "t"),
        ("Page", "page", 54, "u"),
        ("Title", "title", 44, "t"),
        ("PA", "pa", 7, "n"),
        ("Referring domains", "rds", 17, "n"),
        ("What earns the links", "what_earns_links", 40, "t"),
        ("Dominant anchor", "dominant_anchor", 28, "t"),
        ("Links first seen", "first_seen_range", 18, "t"),
        ("Replicable?", "replicable", 13, "t"),
        ("Tactic", "tactic", 26, "t"),
    ]),
    ("page_gap", "P2. Page-Level Gap", [
        ("Keyword", "keyword", 28, "t"),
        ("Client page", "client_page", 46, "u"),
        ("Client rank", "client_rank", 12, "n"),
        ("Competitor page", "competitor_page", 46, "u"),
        ("Competitor rank", "competitor_rank", 15, "n"),
        ("Linking domain", "domain", 28, "t"),
        ("Linking page", "linking_page", 50, "u"),
        ("DA", "da", 7, "n"),
        ("Spam", "spam", 8, "n"),
        ("Note", "note", 36, "t"),
    ]),
    ("anchor_profile", "P3. Anchor Profile", [
        ("Page", "page", 50, "u"),
        ("Owner", "owner", 14, "t"),
        ("Anchor text", "anchor", 40, "t"),
        ("Class", "anchor_class", 15, "t"),
        ("Referring domains", "root_domains", 17, "n"),
        ("Linking pages", "pages", 14, "n"),
        ("Note", "note", 32, "t"),
    ]),
]

# ------------------------------------------------------------- spam solicitation
# Seller-source detection is heuristic; corroborate intent, payment and ownership separately.

SALES_PHRASES = (
    "pbn", "buy backlink", "buy backlinks", "backlinks buy", "premium pbn", "pbn network",
    "dofollow backlink", "high quality dofollow", "link building service", "mass linking",
    "backlink sales", "rank first page", "boost your google ranking", "seo services",
    "backlinks online cheap", "rank with backlinks", "keyword-ranking",
)
SALES_DOMAIN_BITS = (
    "backlink", "seo-anomaly", "linkbuilding", "buyrank", "quickseolinks", "rankvance",
    "seolinks", "pbn",
)
PROPENSITY_FLOOR = 50.0      # legitimate sites sit far below 1.0
PROPENSITY_CERTAIN = 200.0   # high-priority heuristic, not proof


def classify_spam_solicitation(row: dict) -> tuple[bool, list[str]]:
    """Return (is_solicitation, reasons). Analyst can force with row['spam_solicitation']."""
    forced = row.get("spam_solicitation")
    if forced is False:
        return False, []

    reasons: list[str] = []
    hay = " ".join(str(row.get(k) or "") for k in
                   ("anchor", "title", "note", "mechanism", "evidence", "linking_page",
                    "what_earns_links", "route_in")).lower()
    dom = str(row.get("domain") or "").lower()

    hits = [p for p in SALES_PHRASES if p in hay]
    if hits:
        reasons.append("seller's own copy: " + ", ".join(f'"{h}"' for h in hits[:3]))
    bits = [b for b in SALES_DOMAIN_BITS if b in dom]
    if bits:
        reasons.append("domain contains " + ", ".join(bits))

    prop = row.get("link_propensity")
    certain_prop = False
    if isinstance(prop, (int, float)) and prop >= PROPENSITY_FLOOR:
        reasons.append(f"link propensity {prop:,.0f}")
        certain_prop = prop >= PROPENSITY_CERTAIN

    outb = row.get("outbound_root_domains")
    if isinstance(outb, (int, float)) and outb >= 1_000_000:
        reasons.append(f"{outb:,.0f} outbound root domains")

    # A strong signal stands alone; two weak ones together also suffice. Sales language in the
    # anchor, a vendor-shaped domain, or a link propensity nothing legitimate reaches are each
    # strong. A note quoting the seller's own "PBN" copy is the analyst having already made the
    # call in prose.
    # An analyst call stands on its own, but still carries whatever the data independently shows,
    # so the appendix never reads as bare assertion.
    if forced is True:
        return True, reasons or ["marked by analyst"]

    strong = bool(hits or bits or certain_prop)
    return strong or len(reasons) >= 2, reasons


# Next-step tabs. Built after 5. Scored Targets, because they sequence what that sheet scores.
PLAN_SHEETS: list[tuple[str, str, list[tuple[str, str, int, str]]]] = [
    ("outreach_plan", "6. Outreach Plan", [
        ("Wave", "wave", 22, "t"),
        ("#", "rank", 5, "n"),
        ("Domain", "domain", 28, "t"),
        ("Play", "play", 26, "t"),
        ("DA", "da", 6, "n"),
        ("Angle - what we say", "angle", 60, "t"),
        
        ("Route in", "route_in", 40, "t"),
        ("Owner", "owner", 14, "s"),
        ("Status", "status", 14, "s"),
        ("Contacted", "contacted", 12, "s"),
        ("Outcome", "outcome", 16, "s"),
    ]),
    ("listicle_targets", "7. Listicle Targets", [
        ("Publisher", "publisher", 26, "t"),
        ("The page", "page", 54, "u"),
        ("What it lists", "lists", 30, "t"),
        ("Competitors on it", "competitors_listed", 34, "t"),
        ("Client on it?", "client_listed", 12, "t"),
        ("DA", "da", 6, "n"),
        ("Route in", "route_in", 36, "t"),
        ("Pitch angle", "angle", 52, "t"),
        
        ("Owner", "owner", 14, "s"),
        ("Status", "status", 14, "s"),
    ]),
    ("asset_roadmap", "8. Asset Roadmap", [
        ("Asset", "asset", 34, "t"),
        ("Type", "type", 22, "t"),
        ("What it is", "what", 60, "t"),
        ("Why - evidence from this run", "evidence", 60, "t"),
        ("Who would link to it", "who_links", 44, "t"),
        ("Unlocks", "unlocks", 30, "t"),
        ("Effort", "effort", 18, "t"),
        ("When", "sequence", 20, "t"),
        ("Owner", "owner", 14, "s"),
        ("Status", "status", 14, "s"),
    ]),
]


APPENDIX_SHEETS: list[tuple[str, str, list[tuple[str, str, int, str]]]] = [
    ("spam_solicitation", "A1. Spam Solicitation", [
        ("Domain", "domain", 30, "t"),
        ("Seen linking to", "hits", 40, "t"),
        ("Where seen", "where_seen", 26, "t"),
        ("Read", "verdict", 34, "t"),
        ("DA", "da", 7, "n"),
        ("Spam", "spam", 8, "n"),
        ("Link propensity", "link_propensity", 15, "n"),
        ("Nofollow?", "nofollow", 11, "t"),
        ("Date seen", "date_seen", 12, "d"),
        ("Signature matched", "signature", 44, "t"),
        ("Evidence", "evidence", 52, "t"),
    ]),
]


SCORED_COLS: list[tuple[str, str, int, str]] = [
    ("Domain", "domain", 30, "t"),
    ("Source", "source", 14, "t"),
    ("Target Page", "target_page", 40, "u"),
    ("Tactic", "tactic", 26, "t"),
    ("DA", "da", 7, "n"),
    ("Spam", "spam", 8, "n"),
    ("Traffic", "traffic", 11, "n"),
    ("Relevance (0-30)", "relevance", 16, "s"),
    ("Authority (0-20)", "authority", 16, "s"),
    ("Traffic (0-15)", "traffic_score", 15, "s"),
    ("Context (0-15)", "context", 15, "s"),
    ("Spam-clean (0-10)", "spam_clean", 17, "s"),
    ("Contact (0-10)", "contact", 15, "s"),
    ("Score", None, 9, "n"),          # formula
    ("Decision", None, 12, "t"),      # formula
    ("Note", "note", 40, "t"),
]
SCORED_COLS.insert(1, ("Linking page", "linking_page", 52, "u"))
SCORED_COLS += [(label, field, 32, "t") for label, field in [
    ("Opportunity ID", "opportunity_id"), ("Evidence status", "evidence_status"),
    ("Evidence gate", "evidence_gate"), ("Page PA", "pa"), ("Follow / nofollow", "link_type"),
    ("Anchor", "anchor"), ("Competitor destination", "competitor_destination"),
    ("Last crawled", "last_crawled"), ("Date verified", "date_verified"),
    ("Verification source", "verification_source"), ("Competitors linked", "n_competitors"),
    ("Traffic proxy", "traffic_proxy"), ("Traffic source", "traffic_source"),
    ("Link propensity", "link_propensity"), ("Placement", "placement"), ("Contact route", "route_in"),
    ("Execution decision", "execution_decision"), ("Override reason", "override_reason"),
    ("Earned-link destination", "earned_link_destination"),
    ("Commercial page supported", "commercial_page_supported")]]
SCORED_COLS += [(k + " evidence", k + "_evidence", 44, "t") for k in
               ("relevance", "authority", "traffic_score", "context", "spam_clean", "contact")]
for key, title, cols in SHEETS:
    if key in ("recently_earned", "link_gap", "strongest_links"):
        present={c[1] for c in cols}
        cols += [(label, field, 38, "t") for label, field in [
            ("Linking page", "linking_page"), ("Anchor", "anchor"),
            ("Competitor destination", "competitor_destination"),
            ("Evidence status", "evidence_status"), ("Date verified", "date_verified"),
            ("Verification source", "verification_source"),
            ("Evidence decision", "evidence_decision")] if field not in present]
    if key == "serp_benchmark":
        cols += [("Keyword", "keyword", 28, "t"),
                 ("Neither indirect nor nofollow (known overlap only)", "neither_indirect_nor_nofollow", 25, "n")]
for key, title, cols in PLAN_SHEETS:
    cols += [(label, field, 35, "t") for label, field in [
        ("Opportunity ID", "opportunity_id"), ("Score decision", "score_decision"),
        ("Execution decision", "execution_decision"), ("Override reason", "override_reason"),
        ("Earned-link destination", "earned_link_destination"),
        ("Commercial page supported", "commercial_page_supported"),
        ("Proof point IDs", "proof_point_ids"), ("Proof point note", "proof_point_note")]]

SCORED_SHEET = "5. Scored Targets"
def scored_column(header):
    return get_column_letter(next(i for i,c in enumerate(SCORED_COLS,1) if c[0]==header))
FIRST_FACTOR, LAST_FACTOR = scored_column("Relevance (0-30)"), scored_column("Contact (0-10)")
SCORE_COL, DECISION_COL = scored_column("Score"), scored_column("Decision")
GATE_COL = scored_column("Evidence gate")


# ---------------------------------------------------------------- helpers
def style_header(ws, ncols: int, row: int = 1) -> None:
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = Font(name=FONT, bold=True, size=10, color=HEAD_FG)
        cell.fill = PatternFill("solid", fgColor=HEAD_BG)
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        cell.border = BORDER
    ws.row_dimensions[row].height = 30


def write_table(ws, cols, rows: list[dict], start_row: int = 1) -> int:
    """Write a header row plus data. Returns the last data row index (0 if none)."""
    for i, (header, *_rest) in enumerate(cols, start=1):
        ws.cell(row=start_row, column=i, value=header)
    style_header(ws, len(cols), start_row)

    for i, (_h, _f, width, _k) in enumerate(cols, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width

    r = start_row
    for j, item in enumerate(rows):
        r = start_row + 1 + j
        for i, (_header, field, _w, kind) in enumerate(cols, start=1):
            val = item.get(field) if field else None
            if isinstance(val, (list, tuple)):
                val = ", ".join(str(v) for v in val)
            cell = ws.cell(row=r, column=i, value=val)
            cell.font = Font(name=FONT, size=10, color=INK)
            cell.border = BORDER
            cell.alignment = Alignment(
                vertical="top",
                wrap_text=kind in ("t", "u"),
                horizontal="right" if kind in ("n", "s") else "left",
            )
            if kind == "s":
                cell.fill = PatternFill("solid", fgColor=INPUT_BG)
            elif j % 2 == 1:
                cell.fill = PatternFill("solid", fgColor=BAND)

    ws.freeze_panes = ws.cell(row=start_row + 1, column=1)
    if rows:
        ws.auto_filter.ref = f"A{start_row}:{get_column_letter(len(cols))}{r}"
    return r if rows else 0


def note_row(ws, row: int, ncols: int, text: str) -> None:
    ws.cell(row=row, column=1, value=text).font = Font(
        name=FONT, size=9, italic=True, color="6E7D89"
    )
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=max(ncols, 2))


# ---------------------------------------------------------------- tabs
def build_instructions(wb, d: dict) -> None:
    ws = wb.create_sheet("Instructions")
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 74

    r = 1
    ws.cell(row=r, column=1, value="Backlink Gap Analysis").font = Font(
        name=FONT, bold=True, size=16, color=INK
    )
    r += 2

    meta = [
        ("Client", d.get("client", "")),
        ("Market / locale", d.get("market", "")),
        ("Run date", d.get("run_date", "")),
        ("Data source", d.get("data_source", "Moz Link Explorer")),
        ("Analyst", d.get("analyst", "")),
    ]
    cb = d.get("client_baseline") or {}
    if cb:
        meta.append(
            ("Client baseline",
             f"DA {cb.get('da','?')} · {cb.get('rds','?')} referring domains "
             f"· Spam {cb.get('spam','?')}")
        )
    for k, v in meta:
        ws.cell(row=r, column=1, value=k).font = Font(name=FONT, bold=True, size=10, color=INK)
        ws.cell(row=r, column=2, value=v).font = Font(name=FONT, size=10, color=INK)
        r += 1

    # --- competitor verdicts
    comps = d.get("competitors") or []
    if comps:
        r += 1
        ws.cell(row=r, column=1, value="Competitor set").font = Font(
            name=FONT, bold=True, size=12, color=INK
        )
        r += 1
        hdr = ["Domain", "DA", "Ref domains", "Spam", "Overlap", "Verdict", "Note"]
        for i, h in enumerate(hdr, start=1):
            ws.cell(row=r, column=i, value=h)
        style_header(ws, len(hdr), r)
        for i, w in enumerate([30, 7, 13, 8, 10, 16, 52], start=1):
            ws.column_dimensions[get_column_letter(i)].width = max(
                ws.column_dimensions[get_column_letter(i)].width or 0, w
            )
        for c in comps:
            r += 1
            vals = [c.get("domain"), c.get("da"), c.get("rds"), c.get("spam"),
                    c.get("overlap"), c.get("verdict"), c.get("note")]
            for i, v in enumerate(vals, start=1):
                cell = ws.cell(row=r, column=i, value=v)
                cell.font = Font(name=FONT, size=10, color=INK)
                cell.border = BORDER
                cell.alignment = Alignment(vertical="top", wrap_text=i == 7)
            verdict = str(c.get("verdict", "")).lower()
            vc = ws.cell(row=r, column=6)
            if "challenge" in verdict or "drop" in verdict or "exclude" in verdict:
                vc.fill = PatternFill("solid", fgColor=NO_BG)
                vc.font = Font(name=FONT, size=10, bold=True, color=NO_FG)
            elif "partial" in verdict:
                vc.fill = PatternFill("solid", fgColor=HOLD_BG)
                vc.font = Font(name=FONT, size=10, bold=True, color=HOLD_FG)
            elif verdict:
                vc.fill = PatternFill("solid", fgColor=GO_BG)
                vc.font = Font(name=FONT, size=10, bold=True, color=GO_FG)
        r += 1

    # --- coverage
    cov = d.get("coverage") or {}
    if cov:
        r += 1
        ws.cell(row=r, column=1, value="Coverage").font = Font(
            name=FONT, bold=True, size=12, color=INK
        )
        r += 1
        for k in COVERAGE_SHOWN:
            c = cov.get(k) or {}
            if k in ("spam_solicitation", "outreach_plan", "listicle_targets") and not c:
                continue
            ok = bool(c.get("pulled"))
            ws.cell(row=r, column=1, value=k).font = Font(name=FONT, size=10, color=INK)
            n = c.get("rows")
            txt = ("pulled" + (f" · {n} rows" if n is not None else "")) if ok \
                  else f"NOT PULLED · {c.get('reason','no reason given')}"
            cell = ws.cell(row=r, column=2, value=(c.get("coverage_label", "") + " · " + txt + " · " + str(c.get("omitted", {}))))
            cell.font = Font(name=FONT, size=10, bold=not ok,
                             color=INK if ok else NO_FG)
            if not ok:
                cell.fill = PatternFill("solid", fgColor=NO_BG)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            r += 1

    # --- flags
    flags = d.get("flags") or []
    if flags:
        r += 1
        ws.cell(row=r, column=1, value="Flags").font = Font(
            name=FONT, bold=True, size=12, color=INK
        )
        r += 1
        for f in flags:
            ws.cell(row=r, column=1, value=f.get("type", "flag")).font = Font(
                name=FONT, bold=True, size=10, color=NO_FG
            )
            ws.cell(row=r, column=1).fill = PatternFill("solid", fgColor=FLAG_BG)
            detail = f.get("detail", "")
            if f.get("domains"):
                detail += "  [" + ", ".join(f["domains"][:12]) + "]"
            c = ws.cell(row=r, column=2, value=detail)
            c.font = Font(name=FONT, size=10, color=INK)
            c.alignment = Alignment(wrap_text=True, vertical="top")
            r += 1

    # --- legend
    r += 1
    ws.cell(row=r, column=1, value="How to use this workbook").font = Font(
        name=FONT, bold=True, size=12, color=INK
    )
    r += 1
    legend = [
        ("Yellow cells", "The six score factors on '5. Scored Targets'. These are the only "
                         "cells meant to be edited by hand."),
        ("Score / Decision", "Formulas. Score sums the six factors; Decision applies "
                             "Evidence gate first, then Pursue >= 70, Backlog 50-69, Discard < 50. Do not overwrite."),
        ("Scoring rule", "Relevance 30 · Authority 20 · Traffic 15 · Context 15 · "
                         "Spam-clean 10 · Contactability 10."),
        ("Threshold rule", "If a run yields too few Pursue targets, widen the competitor set "
                           "or the keyword clusters. Never lower the threshold."),
        ("Seller-source appendix", "Heuristic candidates only. Hit patterns do not prove payment, intent or ownership."),
        ("Tabs 1-5", "The core gap analysis: competitor set, link gap, recently earned, "
                     "strongest links, scored targets."),
        ("Tabs P1-P3", "Page-level extension: what earns links, which page-specific gaps exist, "
                       "and the anchor profile per money page."),
        ("Hand-off", "Filter '5. Scored Targets' to Pursue and paste into the outreach "
                     "tracker's Pipeline tab."),
    ]
    for k, v in legend:
        ws.cell(row=r, column=1, value=k).font = Font(name=FONT, bold=True, size=10, color=INK)
        c = ws.cell(row=r, column=2, value=v)
        c.font = Font(name=FONT, size=10, color=INK)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        r += 1

    if d.get("assumptions"):
        r += 1
        ws.cell(row=r, column=1, value="Assumptions").font = Font(
            name=FONT, bold=True, size=12, color=INK
        )
        r += 1
        for a in d["assumptions"]:
            c = ws.cell(row=r, column=2, value=f"• {a}")
            c.font = Font(name=FONT, size=10, color=INK)
            c.alignment = Alignment(wrap_text=True, vertical="top")
            r += 1


FACTORS = ("relevance", "authority", "traffic_score", "context", "spam_clean", "contact")


def row_score(r: dict) -> int:
    """Total for a scored row.

    Normally the sum of the six factors. A row carrying an explicit "score" and no factors is a
    total imported from somewhere else - a prior run, a CSV, a published brief - and is used as
    given. Mixing the two silently would hide which is which, so the workbook writes an imported
    score as a literal instead of a formula and says so on the sheet.
    """
    if any(r.get(k) is not None for k in FACTORS):
        return sum((r.get(k) or 0) for k in FACTORS)
    v = r.get("score")
    return int(v) if isinstance(v, (int, float)) else 0


def score_imported(r: dict) -> bool:
    return not any(r.get(k) is not None for k in FACTORS) and isinstance(
        r.get("score"), (int, float))


def build_scored(wb, rows: list[dict]) -> int:
    ws = wb.create_sheet(SCORED_SHEET)
    last = write_table(ws, SCORED_COLS, rows)

    for i, r in enumerate(rows):
        row = 2 + i
        sc = ws[f"{SCORE_COL}{row}"]
        sc.value = (row_score(r) if score_imported(r)
                    else f"=SUM({FIRST_FACTOR}{row}:{LAST_FACTOR}{row})")
        sc.font = Font(name=FONT, bold=True, size=10, color=INK)
        sc.border = BORDER
        sc.alignment = Alignment(horizontal="right")

        dc = ws[f"{DECISION_COL}{row}"]
        dc.value = (
            f'=IF({GATE_COL}{row}<>"Ready","Verify first",IF({SCORE_COL}{row}>=70,"Pursue",'
            f'IF({SCORE_COL}{row}>=50,"Backlog","Discard")))'
        )
        dc.font = Font(name=FONT, bold=True, size=10, color=INK)
        dc.border = BORDER
        dc.alignment = Alignment(horizontal="center")

    if rows:
        rng = f"{DECISION_COL}2:{DECISION_COL}{last}"
        for txt, bg, fg in (("Pursue", GO_BG, GO_FG),
                            ("Backlog", HOLD_BG, HOLD_FG),
                            ("Discard", NO_BG, NO_FG)):
            ws.conditional_formatting.add(rng, CellIsRule(
                operator="equal", formula=[f'"{txt}"'],
                fill=PatternFill("solid", bgColor=bg),
                font=Font(name=FONT, bold=True, color=fg),
            ))
        imported = sum(1 for r in rows if score_imported(r))
        msg = ("Yellow cells are the only hand-edited cells. Score and Decision recalculate "
               "from them. Score the linking page, not the root domain.")
        if imported:
            msg += (f"  {imported} row(s) carry an imported total with no factor breakdown; "
                    "those Score cells are literals, not formulas. Re-score them by hand to "
                    "make them auditable.")
        note_row(ws, last + 2, len(SCORED_COLS), msg)
    return last


def build_summary(wb, d: dict, scored_last: int) -> None:
    ws = wb.create_sheet("Summary")
    ws.column_dimensions["A"].width = 36
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 62

    ws.cell(row=1, column=1, value="Summary").font = Font(
        name=FONT, bold=True, size=14, color=INK
    )

    for i, h in enumerate(["Metric", "Value", "Notes"], start=1):
        ws.cell(row=3, column=i, value=h)
    style_header(ws, 3, 3)

    q = f"'{SCORED_SHEET}'"
    if scored_last >= 2:
        dec = f"{q}!{DECISION_COL}2:{DECISION_COL}{scored_last}"
        src = f"{q}!{scored_column('Source')}2:{scored_column('Source')}{scored_last}"
        total = f'=COUNTA({q}!A2:A{scored_last})'
        rows = [
            ("Total opportunities scored", total, ""),
            ("Verify first", f'=COUNTIF({dec},"Verify first")', "Resolve evidence before outreach"),
            ("Pursue", f'=COUNTIF({dec},"Pursue")', "Hand-off list for outreach"),
            ("Backlog", f'=COUNTIF({dec},"Backlog")', "Revisit next quarter"),
            ("Discard", f'=COUNTIF({dec},"Discard")', ""),
            ("Gap targets", f'=COUNTIF({src},"gap")', "From tab 2"),
            ("Recently-earned targets", f'=COUNTIF({src},"recent")', "From tab 3"),
            ("Strongest-link targets", f'=COUNTIF({src},"strong")', "From tab 4"),
            ("Page-level targets", f'=COUNTIF({src},"page")', "From tabs P1-P2"),
        ]
    else:
        rows = [("Total opportunities scored", 0, "No scored rows supplied")]

    rows += [("Unique domains", counts(d)["unique_domains"], "Build-time snapshot; rebuild after edits"),
             ("Unique Pursue domains", counts(d)["unique_pursue_domains"], "Build-time snapshot; rebuild after edits")]
    r = 3
    for label, val, note in rows:
        r += 1
        ws.cell(row=r, column=1, value=label).font = Font(name=FONT, size=10, color=INK)
        c = ws.cell(row=r, column=2, value=val)
        c.font = Font(name=FONT, bold=True, size=10, color=INK)
        c.alignment = Alignment(horizontal="right")
        ws.cell(row=r, column=3, value=note).font = Font(name=FONT, size=10, color="6E7D89")
        for i in (1, 2, 3):
            ws.cell(row=r, column=i).border = BORDER

    r += 2
    for label, key in (("Raw intersect rows reviewed", "raw_rows_reviewed"),
                       ("Real targets after filtering", "real_targets")):
        if d.get(key) is not None:
            ws.cell(row=r, column=1, value=label).font = Font(name=FONT, size=10, color=INK)
            ws.cell(row=r, column=2, value=d[key]).font = Font(
                name=FONT, bold=True, size=10, color=INK
            )
            r += 1

    if d.get("patterns"):
        r += 1
        ws.cell(row=r, column=1, value="Patterns to build a quarter around").font = Font(
            name=FONT, bold=True, size=12, color=INK
        )
        for p in d["patterns"]:
            r += 1
            ws.cell(row=r, column=1, value=p.get("pattern", "")).font = Font(
                name=FONT, bold=True, size=10, color=INK
            )
            c = ws.cell(row=r, column=3, value=p.get("rationale", ""))
            c.font = Font(name=FONT, size=10, color=INK)
            c.alignment = Alignment(wrap_text=True, vertical="top")

    r += 2
    note_row(ws, r, 3,
             "Hand-off: filter '5. Scored Targets' to Pursue and paste into the outreach "
             "tracker's Pipeline tab.")



# ---------------------------------------------------------------- markdown summary
def _t(rows, cols, headers):
    """Tiny markdown table builder. cols is a list of (key, formatter)."""
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        cells = []
        for key, fmt in cols:
            v = r.get(key)
            cell = fmt(v) if fmt else ("" if v is None else str(v))
            cells.append(str(cell).replace("|", "\\|").replace("\n", " "))
        out.append("| " + " | ".join(cells) + " |")
    return out


def _num(v):
    if v is None:
        return "—"
    return f"{v:,}" if isinstance(v, int) else str(v)


def write_summary(d: dict, path: str, xlsx_name: str) -> str:
    """Write the findings as a markdown brief.

    Generated from the same JSON and reconciled with workbook counts after export. The section
    order follows the reporting order in SKILL.md: verdict first, method never — whoever reads
    this wants to know what to do, not how the data was gathered.
    """
    L: list[str] = []
    client = d.get("client", "client")
    L += [f"# Backlink gap analysis — {client}", ""]

    meta = [x for x in [
        d.get("run_date"), d.get("market"), d.get("data_source"),
        f"workbook: {xlsx_name}",
    ] if x]
    L += ["*" + " · ".join(meta) + "*", ""]

    # ---- 1. the verdict
    bench = d.get("serp_benchmark") or []
    if bench:
        L += ["## " + ("SERP observations by query" if d.get("live_serp", {}).get("supplied") else "Competitive page benchmark"), ""]
        mech = {}
        for r in bench:
            m = ((r.get("keyword") or "Benchmark") + ": " + r["mechanic"]) if r.get("mechanic") else None
            if m:
                mech.setdefault(m, []).append(r.get("domain") or r.get("url"))
        if mech:
            for m, doms in mech.items():
                L.append(f"- **{m}** — {', '.join(str(x) for x in doms)}")
            L.append("")
        if len(mech) > 1:
            L += ["These patterns are hypotheses; link metrics alone do not establish ranking causes.", ""]

        def _conc(r):
            a, b = r.get("domains_to_page"), r.get("domains_to_site")
            if not a or not b:
                return "—"
            return f"{a / b:.0%}"

        L += _t(
            [dict(r, _c=_conc(r)) for r in bench],
            [("url", lambda v: f"`{v}`" if v else ""), ("da", _num), ("pa", _num),
             ("domains_to_page", _num), ("indirect_domains", _num),
             ("nofollow_domains", _num), ("domains_to_site", _num),
             ("_c", None), ("mechanic", None)],
            ["Ranking page", "DA", "PA", "Domains → page", "— indirect", "— nofollow",
             "Domains → site", "Concentration", "Mechanic"],
        )
        L.append("")
        for r in bench:
            if r.get("read"):
                L.append(f"- **{r.get('domain') or r.get('url')}** — {r['read']}")
        L.append("")

    # ---- 2. flags, high before low
    flags = d.get("flags") or []
    if flags:
        L += ["## Flags", ""]
        for f in flags:
            name = str(f.get("type", "flag")).replace("_", " ").strip().upper()
            L.append(f"**{name}.** {f.get('detail','')}")
            if f.get("domains"):
                shown = ", ".join(f"`{x}`" for x in f["domains"][:12])
                more = "" if len(f["domains"]) <= 12 else f" (+{len(f['domains']) - 12} more)"
                L.append(f"  <br>Domains: {shown}{more}")
            L.append("")

    # ---- 3. what is working now
    vendors = spam_vendor_domains(d)
    rec_all = [r for r in (d.get("recently_earned") or []) if r.get("mechanism")]
    rec = [r for r in rec_all if str(r.get("domain") or "").lower() not in vendors]
    rec_v = len(rec_all) - len(rec)
    if rec_all:
        L += ["## Recently observed links (see entity coverage and sampled dates)", ""]
        if rec:
            L += _t(rec[:12],
                    [("domain", lambda v: f"`{v}`"), ("competitor", None), ("da", _num),
                     ("spam", _num), ("date_gained", None), ("mechanism", None)],
                    ["Domain", "Competitor", "DA", "Spam", "Gained", "Mechanism"])
            L.append("")
        else:
            L += ["No observed rows in the sampled window survive the vendor filter.", ""]
        if rec_v:
            L += [f"*{rec_v} of the {len(rec_all)} domains gained in this window came from "
                  "link sellers rather than from anything earned. They are held in the appendix "
                  "and in the workbook's tab 3, and excluded here so this table reads as what "
                  "was actually earned.*", ""]

    # ---- 4. patterns
    pats = d.get("patterns") or []
    if pats:
        L += ["## Patterns worth a quarter", ""]
        for i, p in enumerate(pats, 1):
            L.append(f"{i}. **{p.get('pattern','')}** — {p.get('rationale','')}")
        L.append("")

    # ---- 4b. next steps: the launching-off pad
    plan = d.get("outreach_plan") or []
    listicles = d.get("listicle_targets") or []
    assets = d.get("asset_roadmap") or []
    if plan or listicles or assets:
        L += ["## Next steps", "",
              "The scored list says who is worth approaching. This says what happens on Monday. "
              "Waves are ordered by **speed to link**, not by score: the highest-scoring row on "
              "the sheet is usually the slowest to land, so the fast work starts now and the "
              "slow work runs underneath it for the whole quarter.", ""]

    if plan:
        for wave in (WAVE_1, WAVE_2, WAVE_3):
            rows = [r for r in plan if r.get("wave") == wave]
            if not rows:
                continue
            L += [f"### {wave} — {len(rows)} target{'' if len(rows) == 1 else 's'}", ""]
            L += _t(rows[:20],
                    [("domain", lambda v: f"`{v}`"), ("play", None), ("da", _num),
                     ("angle", None),
                     ("earned_link_destination", lambda v: f"`{v}`" if v else ""),
                     ("commercial_page_supported", None), ("execution_decision", None), ("override_reason", None)],
                    ["Target", "Play", "DA", "Angle", "Earned-link destination", "Commercial page supported", "Execution", "Override reason"])
            if len(rows) > 20:
                L.append("")
                L.append(f"*(+{len(rows) - 20} more on the workbook's '6. Outreach Plan' tab.)*")
            L.append("")
        if any(r.get("_derived") for r in plan):
            L += ["*Angles above are carried from the scoring notes and have not been written "
                  "for outreach yet. Sharpen them on the '6. Outreach Plan' tab before this goes "
                  "to a client.*", ""]

    if listicles:
        L += [f"### Listicles to get onto — {len(listicles)}", "",
              "A potential route to a relevant link. Verify that the page exists, "
              "is relevant to the client and lists the competitors. "
              "Nothing has to be built; somebody has to ask.", ""]
        L += _t(listicles[:20],
                [("publisher", lambda v: f"`{v}`"),
                 ("page", lambda v: f"`{v}`" if v else "*confirm the URL*"),
                 ("competitors_listed", lambda v: v or "—"), ("da", _num),
                 ("route_in", lambda v: v or "—")],
                ["Publisher", "The page", "Competitors on it", "DA", "Route in"])
        if len(listicles) > 20:
            L.append("")
            L.append(f"*(+{len(listicles) - 20} more on the workbook's '7. Listicle Targets' tab.)*")
        L.append("")

    if assets:
        L += [f"### Assets to build — {len(assets)}", "",
              "Each one is justified by something this run actually found. An asset with no "
              "evidence column is a guess, and guesses do not go on a client's roadmap.", ""]
        for a in assets:
            head = f"**{a.get('asset','')}**"
            if a.get("type"):
                head += f" — *{a['type']}*"
            if a.get("effort") or a.get("sequence"):
                bits = [x for x in (a.get("sequence"), a.get("effort")) if x]
                head += f" ({' · '.join(bits)})"
            L.append(head)
            if a.get("what"):
                L.append(f"  <br>{a['what']}")
            if a.get("evidence"):
                L.append(f"  <br>**Why:** {a['evidence']}")
            if a.get("who_links"):
                L.append(f"  <br>**Who would link:** {a['who_links']}")
            if a.get("unlocks"):
                L.append(f"  <br>**Unlocks:** {a['unlocks']}")
            L.append("")

    # ---- 5. the hand-off list
    scored = d.get("scored_targets") or []
    if scored:
        def total(r):
            return row_score(r)
        ranked = sorted(scored, key=total, reverse=True)
        pursue = [r for r in ranked if decision(r) == "Pursue"]
        backlog = [r for r in ranked if decision(r) == "Backlog"]
        discard = [r for r in ranked if decision(r) == "Discard"]

        L += ["## Hand-off list", ""]
        if pursue:
            L += [f"### Pursue — {len(pursue)}", ""]
            L += _t([dict(r, _s=f"**{total(r)}**") for r in pursue],
                    [("domain", lambda v: f"`{v}`"), ("_s", None), ("da", _num),
                     ("spam", _num), ("tactic", None),
                     ("target_page", lambda v: f"`{v}`" if v else ""), ("note", None)],
                    ["Domain", "Score", "DA", "Spam", "Tactic", "Target page", "Why"])
            L.append("")
        if backlog:
            L += [f"### Backlog — {len(backlog)}", ""]
            L += ["- `%s` (%s) — %s" % (r.get("domain"), total(r), r.get("tactic") or "")
                  for r in backlog] + [""]
        if discard:
            L += [f"### Discard — {len(discard)}", "",
                  "Kept on the sheet so the decision is auditable, not silently dropped.", ""]
            L += ["- `%s` (%s) — %s" % (r.get("domain"), total(r), r.get("note") or "")
                  for r in discard] + [""]

        verify = [r for r in ranked if decision(r) == "Verify first"]
        if verify:
            L += [f"### Verify first — {len(verify)}", ""] + [
                f"- {r['domain']}: resolve linking-page and scoring evidence before outreach" for r in verify] + [""]
        L += ["**Counts.** "
              f"{len(scored)} scored → {len(pursue)} Pursue, {len(backlog)} Backlog, "
              f"{len(discard)} Discard, {len(verify)} Verify first."]
        if d.get("raw_rows_reviewed") and d.get("real_targets") is not None:
            L[-1] += (f" {d['real_targets']} filtered opportunities from "
                      f"{d['raw_rows_reviewed']} raw rows reviewed.")
        L.append("")

    # ---- 5b. spam solicitation: count in the body, detail in the appendix
    spam_sol = d.get("spam_solicitation") or []
    if spam_sol:
        L += [f"**Seller-source candidates:** {len(spam_sol)} unique domains quarantined. "
              "Client or competitor coverage suggests possible solicitation; payment, ownership and intent are unverified.", ""]

    # ---- 6. coverage and assumptions
    cov = d.get("coverage") or {}
    if cov:
        missing = [(k, v) for k, v in cov.items() if not (v or {}).get("pulled")]
        L += ["## Coverage", ""]
        if missing:
            for k, v in missing:
                L.append(f"- **{k}** — NOT PULLED. {v.get('reason','no reason given')}")
        else:
            L.append("- Section requests recorded; entity completion shown below.")
        L.append("")

    for k,c in cov.items():
        if c.get("coverage_label"):
            L.append(f"- {k}: {c['coverage_label']}; omissions: {c.get('omitted', {})}; {c.get('partial_reason', '')}")
    if d.get("assumptions"):
        L += ["## Assumptions", ""] + [f"- {a}" for a in d["assumptions"]] + [""]

    # ---- appendix
    if spam_sol:
        appeared = sorted({SECTION_LABEL.get(x, x) for r in spam_sol
                           for x in (r.get("_sections") or [])})
        L += ["---", "", "## Appendix — seller-source candidates", "",
              "Detection is heuristic. Hit patterns alone do not establish purchase, solicitation or common ownership. Review the evidence; do not replicate suspect placements.", ""]
        if appeared:
            L += [f"Where they turned up in this run: {', '.join(appeared)}.", ""]
        L += _t([dict(r, _w=", ".join(SECTION_LABEL.get(x, x) for x in (r.get("_sections") or [])))
                 for r in spam_sol[:40]],
                [("domain", lambda v: f"`{v}`"), ("hits", None), ("verdict", None),
                 ("_w", None), ("da", _num), ("spam", _num),
                 ("link_propensity", lambda v: "—" if v is None else f"{v:,.0f}"),
                 ("nofollow", lambda v: v if v not in (None, "") else "—"),
                 ("signature", None)],
                ["Domain", "Seen linking to", "Read", "Where seen", "DA", "Spam",
                 "Propensity", "Nofollow", "Signature"])
        if len(spam_sol) > 40:
            L.append(f"")
            L.append(f"*(+{len(spam_sol) - 40} further domains in the workbook's A1 tab.)*")
        L.append("")

    L += ["---", "",
          "*Figures from the Moz API on the run date above. Link data moves — re-pull before "
          "quoting these numbers to a client.*", ""]

    from reporting import executive_markdown
    L[4:4] = executive_markdown(d)
    text = "\n".join(L)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


# ---------------------------------------------------------------- main
REQUIRED = ["serp_benchmark", "link_gap", "recently_earned", "strongest_links",
            "competitor_top_pages", "page_gap", "anchor_profile", "scored_targets",
            "asset_roadmap"]

# Shown in the workbook's coverage block. spam_solicitation is derived by the sweep, so the
# analyst is not asked to declare it, but the run still reports what it found.
COVERAGE_SHOWN = REQUIRED + ["outreach_plan", "listicle_targets", "spam_solicitation"]


def check_coverage(d: dict) -> list[str]:
    """Every required section must be pulled, or carry a stated reason. A blank tab reads as
    'nothing here' when it usually means 'nobody looked' — this is what stops that shipping."""
    cov = d.get("coverage") or {}
    problems = []
    for k in REQUIRED:
        c = cov.get(k)
        if c is None:
            problems.append(f"{k}: no coverage entry (set pulled true/false)")
        elif not c.get("pulled") and not c.get("reason"):
            problems.append(f"{k}: pulled=false with no reason given")
    return problems + coverage_problems(d)


SECTION_LABEL = {
    "scored_targets": "target list", "link_gap": "link gap",
    "recently_earned": "recently earned", "strongest_links": "strongest links",
    "anchor_profile": "anchors", "competitor_top_pages": "top pages",
    "page_gap": "page gap", "analyst": "flagged by analyst",
}

SWEEP_SECTIONS = ("scored_targets", "link_gap", "recently_earned", "strongest_links",
                  "anchor_profile", "competitor_top_pages", "page_gap")


def _row_sites(row: dict, client: str) -> list[str]:
    """Which analysed sites this row says the domain was seen linking to."""
    out: list[str] = []
    c = row.get("competitors")
    if isinstance(c, list):
        out += [str(x).strip() for x in c if x]
    for k in ("competitor", "site"):
        v = row.get(k)
        if v and isinstance(v, str):
            out.append(v.strip())
    if str(row.get("owner") or "").lower() == "client" and client:
        out.append(client)
    seen, uniq = set(), []
    for x in out:
        low = normalize_domain(x)
        if low and low not in seen:
            seen.add(low)
            uniq.append(low)
    return uniq


def _seller_verdict(sites: list[str], client: str, n_sites: int) -> str:
    """Conservative hypothesis from normalized observed hit coverage."""
    low = {normalize_domain(x) for x in sites if normalize_domain(x)}
    if normalize_domain(client) in low:
        return "Possible solicitation - hit the client; payment unverified"
    if len(low) >= max(3, n_sites - 1):
        return "Possible solicitation - widespread; payment unverified"
    return "Seller source - payment and intent unverified"



def quarantine_spam(d: dict) -> list[dict]:
    """Sweep every findings section for link-vendor solicitation.

    Counts it everywhere it appears (that is the number the client asks about), records
    which analysed sites each vendor hit, writes it to the appendix, and removes it from
    scored_targets only. Raw evidence tabs keep their rows; the strategy does not.
    """
    client = normalize_domain(d.get("client_domain") or d.get("client"))
    index: dict[str, dict] = {}
    order: list[str] = []

    def note(domain: str, row: dict, why: list[str], section: str) -> None:
        key = normalize_domain(domain)
        if key not in index:
            index[key] = {"domain": domain, "_sites": [], "_why": [], "_sections": [],
                          "da": None, "spam": None, "link_propensity": None,
                          "nofollow": None, "date_seen": None, "evidence": ""}
            order.append(key)
        e = index[key]
        for site in _row_sites(row, client):
            if site.lower() not in {x.lower() for x in e["_sites"]}:
                e["_sites"].append(site)
        for w in why:
            head = str(w).split(":")[0].split(" ")[0].lower()
            same = [i for i, x in enumerate(e["_why"])
                    if str(x).split(":")[0].split(" ")[0].lower() == head]
            if not same:
                e["_why"].append(w)
            elif len(str(w)) > len(str(e["_why"][same[0]])):
                e["_why"][same[0]] = w  # keep the most specific phrasing of each signal
        if section not in e["_sections"]:
            e["_sections"].append(section)
        for src, dst in (("da", "da"), ("spam", "spam"),
                         ("link_propensity", "link_propensity"), ("nofollow", "nofollow")):
            if e[dst] in (None, "") and row.get(src) not in (None, ""):
                e[dst] = row.get(src)
        if not e["date_seen"]:
            e["date_seen"] = row.get("date_seen") or row.get("date_gained") or ""
        if not e["evidence"]:
            e["evidence"] = row.get("note") or row.get("anchor") or row.get("route_in") or ""

    for pre in (d.get("spam_solicitation") or []):
        dom = str(pre.get("domain") or "").strip()
        if not dom:
            continue
        _, pre_why = classify_spam_solicitation(dict(pre, spam_solicitation=None))
        note(dom, pre, [x for x in [pre.get("signature")] if x] + pre_why, "analyst")
        if pre.get("hits"):
            e = index[normalize_domain(dom)]
            for site in str(pre["hits"]).replace(";", ",").split(","):
                if site.strip() and site.strip().lower() not in {x.lower() for x in e["_sites"]}:
                    e["_sites"].append(site.strip())

    moved: list[dict] = []
    for section in SWEEP_SECTIONS:
        rows = d.get(section) or []
        keep = []
        for r in rows:
            dom = str(r.get("domain") or "").strip()
            is_spam, why = classify_spam_solicitation(r)
            if is_spam and dom:
                note(dom, r, why, section)
                if section == "scored_targets":
                    moved.append(r)
                    continue
            keep.append(r)
        if section == "scored_targets":
            d["scored_targets"] = keep

    n_sites = len(d.get("competitors") or []) + 1
    appendix = []
    for key in order:
        e = index[key]
        appendix.append({
            "verdict": _seller_verdict(e["_sites"], client, n_sites),
            "domain": e["domain"],
            "hits": ", ".join(e["_sites"]) or "not attributed",
            "da": e["da"], "spam": e["spam"],
            "link_propensity": e["link_propensity"],
            "nofollow": e["nofollow"], "date_seen": e["date_seen"],
            "signature": "; ".join(e["_why"]),
            "evidence": e["evidence"],
            "where_seen": ", ".join(SECTION_LABEL.get(x, x) for x in e["_sections"]),
            "_sections": e["_sections"],
            "_sites": e["_sites"],
        })
    d["spam_solicitation"] = appendix
    cov = d.setdefault("coverage", {})
    entry = cov.setdefault("spam_solicitation", {})
    entry["pulled"] = True
    entry["rows"] = len(appendix)
    entry.setdefault("reason", "")
    return moved


def spam_vendor_domains(d: dict) -> set[str]:
    """Lowercased vendor domains, for suppressing them from summary narrative tables."""
    return {str(r.get("domain") or "").lower() for r in (d.get("spam_solicitation") or [])
            if r.get("domain")}


# ------------------------------------------------------------------ next steps
# The gap analysis ends with a scored list. The next question is always "so what do we do on
# Monday", and a list sorted by score does not answer it: the highest-scoring row is often
# the slowest one to land. These waves order by SPEED TO LINK instead, so the fast unglamorous
# work starts immediately while the slow relationship work runs underneath it.

WAVE_1 = "Wave 1 - this week"
WAVE_2 = "Wave 2 - weeks 2-6"
WAVE_3 = "Wave 3 - the quarter"

# Matched against the tactic string, first hit wins. Order matters.
WAVE_RULES: list[tuple[str, str]] = [
    # Wave 1: a published route in, no asset, no relationship, no gatekeeper.
    ("directory", WAVE_1), ("listing", WAVE_1), ("profile claim", WAVE_1),
    ("profile creation", WAVE_1), ("submission form", WAVE_1), ("citation", WAVE_1),
    ("membership", WAVE_1), ("association", WAVE_1), ("professional body", WAVE_1),
    ("reclamation", WAVE_1), ("unlinked mention", WAVE_1), ("broken link", WAVE_1),
    # Wave 2: needs a pitch or a piece of writing, but no new asset and no news cycle.
    ("listicle", WAVE_2), ("roundup", WAVE_2), ("curated", WAVE_2), ("resource page", WAVE_2),
    ("contributed", WAVE_2), ("guest", WAVE_2), ("local press", WAVE_2), ("local blog", WAVE_2),
    ("community", WAVE_2), ("expert-contributor", WAVE_2), ("inclusion", WAVE_2),
    # Wave 3: relationships, news cycles, or something that has to be built first.
    ("digital pr", WAVE_3), ("expert sourcing", WAVE_3), ("expert source", WAVE_3),
    ("press pitch", WAVE_3), ("awards", WAVE_3), ("rankings", WAVE_3), ("data study", WAVE_3),
    ("scholarship", WAVE_3), ("calculator", WAVE_3), ("asset", WAVE_3), ("trend", WAVE_3),
    ("news hook", WAVE_3), ("seasonal", WAVE_3),
]

LISTICLE_HINTS = ("listicle", "roundup", "best of", "best-of", "curated", "top-doctor",
                  "top doctor", "citation inclusion", "list inclusion")


def wave_for(tactic: str) -> str:
    """Speed to link, from the tactic. Unknown tactics land in Wave 2, the middle."""
    t = (tactic or "").lower()
    for needle, wave in WAVE_RULES:
        if needle in t:
            return wave
    return WAVE_2


def _score_of(r: dict) -> int:
    return row_score(r)


def derive_outreach_plan(d: dict) -> int:
    """Bootstrap the plan from Pursue rows when the analyst has not written one.

    A derived plan is a starting point, not a deliverable: it carries the target, the play, the
    wave and the landing page, and leaves the angle as whatever the scoring note said. The
    analyst is expected to sharpen the angle column. Rows the analyst supplied are never touched.
    """
    if d.get("outreach_plan"):
        return 0
    pursue = [r for r in (d.get("scored_targets") or []) if r.get("execution_decision") in ("Pursue now", "Hygiene quick win")]
    if not pursue:
        return 0
    rows = []
    for r in sorted(pursue, key=_score_of, reverse=True):
        tactic = r.get("tactic") or ""
        rows.append({
            "wave": wave_for(tactic),
            "opportunity_id": r["opportunity_id"],
            "earned_link_destination": r.get("earned_link_destination", ""),
            "commercial_page_supported": r.get("commercial_page_supported", ""),
            "commercial_support_reason": r.get("commercial_support_reason", ""),
            "link_target_page": r.get("linking_page", ""),
            "domain": r.get("domain"),
            "play": tactic,
            "da": r.get("da"),
            "angle": r.get("note") or "",
            "link_target": r.get("earned_link_destination") or "",
            "route_in": r.get("route_in") or "",
            "_derived": True,
        })
    # A hand-written listicle row is more considered than a derived plan row, so where the two
    # cover the same publisher the hand-written angle and destination win.
    by_pub = {str(x.get("publisher") or "").lower(): x
              for x in (d.get("listicle_targets") or []) if not x.get("_derived")}
    for x in rows:
        hand = by_pub.get(str(x.get("domain") or "").lower())
        if hand:
            x["angle"] = hand.get("angle") or x["angle"]
            x["link_target"] = hand.get("link_target") or x["link_target"]
            x["route_in"] = hand.get("route_in") or x["route_in"]

    order = {WAVE_1: 0, WAVE_2: 1, WAVE_3: 2}
    rows.sort(key=lambda x: order.get(x["wave"], 1))
    for i, x in enumerate(rows, 1):
        x["rank"] = i
    d["outreach_plan"] = rows
    cov = d.setdefault("coverage", {}).setdefault("outreach_plan", {})
    cov["pulled"] = True
    cov["rows"] = len(rows)
    cov["reason"] = "derived from Pursue rows; angles not yet written by the analyst"
    return len(rows)


def derive_listicles(d: dict) -> int:
    """Pull the listicle and roundup plays out of the plan into their own sheet.

    They deserve separation because they are the one play that needs no asset, no relationship
    and no news cycle: the page already exists, it already ranks for the client's terms, and it
    already lists the competitors. Getting added to it is the shortest path to a relevant link.
    """
    if d.get("listicle_targets"):
        return 0
    rows = []
    for r in (d.get("outreach_plan") or []):
        # Match the PLAY only. Matching the angle or route text catches any row whose note
        # happens to contain the word "best", which is most of them.
        hay = str(r.get("play") or "").lower()
        if any(h in hay for h in LISTICLE_HINTS):
            rows.append({
                "publisher": r.get("domain"),
                "page": r.get("link_target_page") or "",
                "opportunity_id": r.get("opportunity_id"),
                "earned_link_destination": r.get("earned_link_destination"),
                "commercial_page_supported": r.get("commercial_page_supported"),
                "lists": r.get("play") or "",
                "competitors_listed": r.get("competitors_listed") or "",
                "client_listed": "Unknown - verify",
                "da": r.get("da"),
                "route_in": r.get("route_in") or "",
                "angle": r.get("angle") or "",
                "link_target": r.get("link_target") or "",
                "_derived": True,
            })
    if not rows:
        return 0
    d["listicle_targets"] = rows
    cov = d.setdefault("coverage", {}).setdefault("listicle_targets", {})
    cov["pulled"] = True
    cov["rows"] = len(rows)
    cov["reason"] = "derived from the outreach plan; publisher pages not yet confirmed by hand"
    return len(rows)


def build(d: dict, out: str) -> str:
    wb = Workbook()
    wb.remove(wb.active)

    build_instructions(wb, d)
    cov = d.get("coverage") or {}
    for key, title, cols in SHEETS:
        ws = wb.create_sheet(title)
        rows = d.get(key) or []
        last = write_table(ws, cols, rows)

        if key == "serp_benchmark" and rows:
            for i in range(len(rows)):
                r = 2 + i
                c = ws.cell(row=r, column=11)
                c.value = f'=IF(F{r}="","",IFERROR(F{r}/J{r},""))'
                c.number_format = "0%"
                c.font = Font(name=FONT, bold=True, size=10, color=INK)
                c.border = BORDER
                c.alignment = Alignment(horizontal="right")
            note_row(ws, last + 2, len(cols),
                     "Concentration = domains to page / domains to site. Check Indexed before "
                     "trusting a zero: an unindexed URL returns zeros identical to a real zero. "
                     "Read indirect and nofollow alongside the headline count.")

        if not rows:
            c = (cov.get(key) or {})
            if c.get("pulled"):
                note_row(ws, 2, len(cols),
                         f"Pulled, returned no rows. That is a finding — state it in the report.")
            else:
                note_row(ws, 2, len(cols),
                         f"NOT PULLED. Reason: {c.get('reason','none given')}")
        elif key == "competitor_top_pages":
            note_row(ws, last + 2, len(cols),
                     "Uniform anchor text plus clustered first-seen dates means a structured "
                     "campaign, not organic interest — which is what makes it replicable.")
        elif key == "page_gap":
            note_row(ws, last + 2, len(cols),
                     "Page-level link counts are far smaller than domain-level. Single-digit "
                     "row counts here are normal, not a failed run.")

    scored_last = build_scored(wb, d.get("scored_targets") or [])

    for key, title, cols in PLAN_SHEETS:
        ws = wb.create_sheet(title)
        rows = d.get(key) or []
        last = write_table(ws, cols, rows)
        if not rows:
            c = (cov.get(key) or {})
            note_row(ws, 2, len(cols),
                     "Pulled, returned no rows. That is a finding — state it in the report."
                     if c.get("pulled") else
                     f"NOT PULLED. Reason: {c.get('reason','none given')}")
        elif key == "outreach_plan":
            note_row(ws, last + 2, len(cols),
                     "Waves are ordered by speed to link, not by value. Wave 1 needs no asset and "
                     "no relationship, so it starts on day one; Wave 3 runs underneath it for the "
                     "whole quarter. Owner, Status, Contacted and Outcome are yours to fill in.")
        elif key == "asset_roadmap":
            note_row(ws, last + 2, len(cols),
                     "Every asset here is justified by something in this run. If you cannot name "
                     "the evidence column for an asset, it does not belong on this sheet.")

    build_summary(wb, d, scored_last)

    for key, title, cols in APPENDIX_SHEETS:
        ws = wb.create_sheet(title)
        rows = d.get(key) or []
        last = write_table(ws, cols, rows)
        if rows:
            note_row(ws, last + 2, len(cols),
                     "Heuristically detected seller-source candidates; payment and intent unverified. "
                     "Counted here and excluded from the scored list — do not pursue, do not "
                     "replicate, and do not panic-disavow on this basis alone.")
        else:
            note_row(ws, 2, len(cols),
                     (d.get("coverage", {}).get(key) or {}).get("pulled")
                     and "Checked, none found. Worth stating in the report."
                     or "NOT CHECKED.")

    from reporting import add_executive
    add_executive(wb, d)
    wb.save(out)
    return out


def recalc(path: str) -> str:
    """Run the xlsx skill's recalc.py if we can find it, so formulas carry cached values."""
    candidates = [
        os.environ.get("XLSX_SKILL_RECALC", ""),
        "/root/.claude/skills/synced/xlsx/scripts/recalc.py",
        os.path.expanduser("~/.claude/skills/synced/xlsx/scripts/recalc.py"),
        os.path.expanduser("~/.claude/skills/xlsx/scripts/recalc.py"),
    ]
    script = next((c for c in candidates if c and os.path.exists(c)), None)
    if not script or not shutil.which("soffice"):
        return "skipped (recalc.py or LibreOffice not found; formulas still valid in Excel)"
    try:
        p = subprocess.run([sys.executable, script, path, "60"],
                           capture_output=True, text=True, timeout=180)
        return (p.stdout or p.stderr or "").strip()[:400]
    except Exception as e:  # pragma: no cover
        return f"skipped ({e})"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("findings", nargs="?", help="Path to findings JSON")
    ap.add_argument("--out", default="backlink_gap_workbook.xlsx")
    ap.add_argument("--print-schema", action="store_true")
    ap.add_argument("--example", action="store_true",
                    help="Print a filled example findings JSON to stdout")
    ap.add_argument("--no-recalc", action="store_true")
    ap.add_argument("--summary", help="Path for the markdown brief "
                                      "(default: <out>_summary.md)")
    ap.add_argument("--allow-partial", action="store_true",
                    help="Build a labeled partial run with explicit entity reasons and partial_reason")
    a = ap.parse_args()

    if a.print_schema:
        print(Path(__file__).with_name("findings.schema.json").read_text(encoding="utf-8"))
        return
    if a.example:
        print(Path(__file__).with_name("example_findings.json").read_text(encoding="utf-8"))
        return
    if not a.findings:
        ap.error("findings JSON required (or use --print-schema / --example)")

    with open(a.findings, encoding="utf-8-sig") as f:
        data: dict[str, Any] = json.load(f)

    from schema_validate import validate
    validate(data, json.loads(Path(__file__).with_name("findings.schema.json").read_text(encoding="utf-8")))
    prepare(data)
    problems = check_coverage(data)
    if problems and not a.allow_partial:
        sys.exit("Refusing to build — incomplete coverage:\n  " + "\n  ".join(problems) +
                 "\n\nEvery section must record whether it was pulled. Pass --allow-partial "
                 "for an explicitly labeled partial build with entity reasons and top-level partial_reason.")
    if problems and not data.get("partial_reason"):
        sys.exit("Partial builds require a top-level partial_reason")
    if problems:
        validate_partial_reasons(data)
        data.setdefault("flags", []).append({"type":"partial coverage", "detail":"; ".join(problems)})
        data["run_status"]="PARTIAL"
        print("WARNING - shipping partial run:\n  " + "\n  ".join(problems))

    moved = quarantine_spam(data)
    n_plan = derive_outreach_plan(data)
    n_list = derive_listicles(data)
    validate_plan(data)
    if n_plan:
        print(f"Outreach plan: derived {n_plan} row(s) from Pursue targets. Sharpen the Angle "
              "column before this goes to a client.")
    if n_list:
        print(f"Listicle targets: pulled {n_list} row(s) out of the plan. Confirm the actual "
              "publisher pages by hand.")
    found = data.get("spam_solicitation") or []
    if found:
        print(f"Spam solicitation: {len(found)} domain(s) found across the run "
              f"→ A1 appendix; {len(moved)} removed from scored targets"
              + (f" ({', '.join(str(m.get('domain')) for m in moved[:6])}"
                 f"{', …' if len(moved) > 6 else ''})" if moved else ""))

    out = build(data, a.out)
    msg = "not run (--no-recalc)" if a.no_recalc else recalc(out)

    md = a.summary or os.path.splitext(out)[0] + "_summary.md"
    write_summary(data, md, os.path.basename(out))

    from reporting import assert_outputs
    assert_outputs(data, out, md, SCORED_COLS)
    counts = {k: len(data.get(k) or []) for k, _t, _c in SHEETS}
    counts["scored_targets"] = len(data.get("scored_targets") or [])
    for k, _t, _c in PLAN_SHEETS:
        counts[k] = len(data.get(k) or [])
    counts["spam_solicitation"] = len(data.get("spam_solicitation") or [])
    print(f"Wrote {out}")
    print("Rows: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    print(f"Recalc: {msg}")
    print(f"Summary: {md}")


if __name__ == "__main__":
    main()


