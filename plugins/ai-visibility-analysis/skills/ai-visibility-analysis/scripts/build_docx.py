#!/usr/bin/env python3
"""
build_docx.py
Convert the AI Visibility markdown report into a shareable .docx.

Usage:
    python build_docx.py report.md report.docx
"""

from __future__ import annotations

import datetime as dt
import re
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CP_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC_NS = "http://purl.org/dc/elements/1.1/"
DCTERMS_NS = "http://purl.org/dc/terms/"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
VT_NS = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"

ACCENT = "0B7085"
ACCENT_LIGHT = "E3F2F4"
ROW_ALT = "F2F7F8"
MUTED = "6B7280"
INK = "1A1A1A"
BORDER = "D5DDE2"
BODY_SIZE = 11
TABLE_SIZE = 9


def xml(text: str) -> str:
    return text.strip() + "\n"


def escape_text(text: str) -> str:
    return escape(text, {'"': "&quot;"})


def twips(points: int) -> int:
    return points * 20


def half_points(points: int) -> int:
    return int(round(points * 2))


def run_xml(text: str, *, bold: bool = False, italic: bool = False,
            color: str = INK, size: int = BODY_SIZE, code: bool = False) -> str:
    if not text:
        return ""
    preserve = ' xml:space="preserve"' if text[:1].isspace() or text[-1:].isspace() else ""
    props = [
        "<w:rPr>",
        ('<w:rFonts w:ascii="Courier New" w:hAnsi="Courier New" w:cs="Courier New"/>'
         if code else '<w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>'),
        f'<w:sz w:val="{half_points(size)}"/>',
        f'<w:color w:val="{color}"/>',
    ]
    if bold:
        props.append("<w:b/>")
    if italic:
        props.append("<w:i/>")
    if code:
        props.append(f'<w:shd w:val="clear" w:color="auto" w:fill="{ACCENT_LIGHT}"/>')
    props.append("</w:rPr>")
    return "<w:r>" + "".join(props) + f"<w:t{preserve}>{escape_text(text)}</w:t></w:r>"


def split_bold_runs(text: str, *, color: str = INK, size: int = 11,
                    bold_all: bool = False, italic_all: bool = False) -> str:
    runs = []
    parts = re.split(r"(\*\*.+?\*\*|`[^`]+`)", text)
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            runs.append(run_xml(part[2:-2], bold=True or bold_all, italic=italic_all, color=color, size=size))
            continue
        if part.startswith("`") and part.endswith("`"):
            runs.append(run_xml(part[1:-1], bold=bold_all, italic=italic_all, color=INK, size=size, code=True))
            continue
        runs.append(run_xml(part, bold=bold_all, italic=italic_all, color=color, size=size))
    return "".join(runs)


def looks_numeric(text: str) -> bool:
    cleaned = (text or "").strip().lower()
    if not cleaned:
        return False
    cleaned = cleaned.replace(",", "")
    return bool(re.fullmatch(r"(lead or tie|protected|\d+(\.\d+)?(%| pts)?|\(\d+(\.\d+)?\)|\d+% \(\d+(\.\d+)?\))", cleaned))


def paragraph_xml(inner_runs: str, *, style: str | None = None,
                  spacing_after: int | None = None, spacing_before: int | None = None,
                  num_id: int | None = None, align: str | None = None,
                  shaded: str | None = None, divider: bool = False,
                  left_indent: int | None = None, keep_next: bool = False) -> str:
    props = []
    if style:
        props.append(f'<w:pStyle w:val="{style}"/>')
    if num_id is not None:
        props.append(
            "<w:numPr>"
            '<w:ilvl w:val="0"/>'
            f'<w:numId w:val="{num_id}"/>'
            "</w:numPr>"
        )
    if align:
        props.append(f'<w:jc w:val="{align}"/>')
    if keep_next:
        props.append("<w:keepNext/>")
    spacing_bits = []
    if spacing_before is not None:
        spacing_bits.append(f'w:before="{twips(spacing_before)}"')
    if spacing_after is not None:
        spacing_bits.append(f'w:after="{twips(spacing_after)}"')
    if spacing_bits:
        props.append(f"<w:spacing {' '.join(spacing_bits)}/>")
    if shaded:
        props.append(f'<w:shd w:val="clear" w:color="auto" w:fill="{shaded}"/>')
    if left_indent is not None:
        props.append(f'<w:ind w:left="{left_indent}"/>')
    if divider:
        props.append(
            "<w:pBdr>"
            f'<w:top w:val="single" w:sz="8" w:space="1" w:color="{BORDER}"/>'
            "</w:pBdr>"
        )
    ppr = f"<w:pPr>{''.join(props)}</w:pPr>" if props else ""
    return f"<w:p>{ppr}{inner_runs}</w:p>"


def parse_table(lines: list[str], start: int) -> tuple[list[list[str]], int]:
    rows = []
    index = start
    while index < len(lines) and lines[index].lstrip().startswith("|"):
        rows.append(lines[index].strip())
        index += 1
    cells = []
    for row in rows:
        parts = [cell.strip() for cell in row.strip("|").split("|")]
        cells.append(parts)
    cells = [row for row in cells if not all(re.fullmatch(r":?-{2,}:?", cell or "-") for cell in row)]
    return cells, index


def cell_xml(text: str, *, header: bool = False, font_size: int = TABLE_SIZE,
             shaded: str | None = None, align: str | None = None) -> str:
    tc_pr = [
        "<w:tcPr>",
        '<w:tcW w:w="0" w:type="auto"/>',
        '<w:tcMar><w:top w:w="40" w:type="dxa"/><w:bottom w:w="40" w:type="dxa"/><w:left w:w="90" w:type="dxa"/><w:right w:w="90" w:type="dxa"/></w:tcMar>',
    ]
    if header:
        tc_pr.append(f'<w:shd w:val="clear" w:color="auto" w:fill="{ACCENT}"/>')
    elif shaded:
        tc_pr.append(f'<w:shd w:val="clear" w:color="auto" w:fill="{shaded}"/>')
    tc_pr.append("</w:tcPr>")
    para = paragraph_xml(
        split_bold_runs(text, size=font_size, bold_all=header, color=("FFFFFF" if header else INK)),
        spacing_after=0,
        align=align,
    )
    return f"<w:tc>{''.join(tc_pr)}{para}</w:tc>"


def table_xml(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    max_cols = max(len(row) for row in rows)
    col_width = 9600 // max(1, max_cols)
    font_size = 8 if max_cols >= 6 else TABLE_SIZE
    grid = "".join(f'<w:gridCol w:w="{col_width}"/>' for _ in range(max_cols))
    body = [
        "<w:tbl>",
        (
            "<w:tblPr>"
            '<w:tblW w:w="0" w:type="auto"/>'
            '<w:jc w:val="left"/>'
            '<w:tblLayout w:type="autofit"/>'
            '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" '
            'w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/>'
            f'<w:tblBorders><w:top w:val="single" w:sz="4" w:space="0" w:color="{BORDER}"/>'
            f'<w:left w:val="single" w:sz="4" w:space="0" w:color="{BORDER}"/>'
            f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="{BORDER}"/>'
            f'<w:right w:val="single" w:sz="4" w:space="0" w:color="{BORDER}"/>'
            f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="{BORDER}"/>'
            f'<w:insideV w:val="single" w:sz="4" w:space="0" w:color="{BORDER}"/></w:tblBorders>'
            '<w:tblCellMar><w:top w:w="40" w:type="dxa"/><w:bottom w:w="40" w:type="dxa"/><w:left w:w="90" w:type="dxa"/><w:right w:w="90" w:type="dxa"/></w:tblCellMar>'
            "</w:tblPr>"
        ),
        f"<w:tblGrid>{grid}</w:tblGrid>",
    ]
    for row_index, row in enumerate(rows):
        header = row_index == 0
        if header:
            body.append('<w:tr><w:trPr><w:tblHeader w:val="true"/></w:trPr>')
        else:
            body.append("<w:tr>")
        row_shade = ROW_ALT if row_index % 2 == 0 and not header else None
        for cell in row + [""] * (max_cols - len(row)):
            align = "right" if looks_numeric(cell) else None
            body.append(cell_xml(cell, header=header, font_size=font_size, shaded=row_shade, align=align))
        body.append("</w:tr>")
    body.append("</w:tbl>")
    return "".join(body)


def cover_block_xml(title: str, subtitle: str) -> list[str]:
    return [
        paragraph_xml(
            split_bold_runs(title, color=ACCENT, size=24, bold_all=True),
            style="Title",
            spacing_after=2,
        ),
        paragraph_xml(
            run_xml(subtitle, italic=True, color=MUTED, size=10.5),
            style="Subtitle",
            spacing_after=14,
            divider=True,
        ),
    ]


def parse_metadata(lines: list[str]) -> tuple[str, str, list[str]]:
    title = ""
    subtitle = ""
    body_start = 0
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:]
            body_start = index + 1
            if body_start < len(lines) and lines[body_start].strip().startswith("*") and lines[body_start].strip().endswith("*"):
                subtitle = lines[body_start].strip().strip("*")
                body_start += 1
            break
    return title, subtitle, lines[body_start:]


def build_document_xml(lines: list[str]) -> str:
    title, subtitle, body_lines = parse_metadata(lines)
    body = []
    if title:
        body.extend(cover_block_xml(title, subtitle))

    index = 0
    in_play_card = False
    while index < len(body_lines):
        stripped = body_lines[index].strip()
        if not stripped:
            in_play_card = False
            index += 1
            continue

        if stripped.startswith("## "):
            in_play_card = False
            body.append(
                paragraph_xml(
                    split_bold_runs(stripped[3:], color=ACCENT, size=15, bold_all=True),
                    style="Heading2",
                    spacing_before=16,
                    spacing_after=5,
                    divider=True,
                    keep_next=True,
                )
            )
            index += 1
            continue

        if stripped.startswith("### "):
            body.append(
                paragraph_xml(
                    split_bold_runs(stripped[4:], color=INK, size=12, bold_all=True),
                    style="Heading3",
                    spacing_before=8,
                    spacing_after=3,
                    keep_next=True,
                )
            )
            index += 1
            continue

        if re.match(r"^\*\*(PLAY|CLEANUP)\s+\d+:", stripped, re.I):
            in_play_card = True
            body.append(
                paragraph_xml(
                    split_bold_runs(stripped, color=ACCENT, size=12, bold_all=False),
                    spacing_before=8,
                    spacing_after=2,
                    shaded=ROW_ALT,
                    divider=True,
                    keep_next=True,
                )
            )
            index += 1
            continue

        if stripped.startswith("|"):
            in_play_card = False
            rows, index = parse_table(body_lines, index)
            body.append(table_xml(rows))
            body.append(paragraph_xml(run_xml(" ", size=3), spacing_after=2))
            continue

        if re.match(r"^[-*]\s+", stripped):
            text = re.sub(r"^[-*]\s+", "", stripped)
            body.append(paragraph_xml(split_bold_runs(text), num_id=1, spacing_after=2))
            index += 1
            continue

        if re.match(r"^\d+\.\s+", stripped):
            text = re.sub(r"^\d+\.\s+", "", stripped)
            body.append(paragraph_xml(split_bold_runs(text), num_id=2, spacing_after=2))
            index += 1
            continue

        if in_play_card and re.match(r"^(Opportunity score|Cleanup priority|Defense priority|Threat|Affected models|Prompt cluster|Strategic read|Recommended move|Proof to include|Action type|Supporting prompts|Supporting pages|Supporting evidence):", stripped):
            body.append(
                paragraph_xml(
                    split_bold_runs(stripped),
                    spacing_after=2,
                    left_indent=360,
                )
            )
            index += 1
            continue

        body.append(paragraph_xml(split_bold_runs(stripped), spacing_after=5))
        index += 1

    body.append(
        '<w:sectPr>'
        '<w:footerReference w:type="default" r:id="rId6"/>'
        '<w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="1440" w:right="1200" w:bottom="1440" w:left="1200" '
        'w:header="720" w:footer="720" w:gutter="0"/>'
        '<w:cols w:space="720"/>'
        '<w:docGrid w:linePitch="360"/>'
        '</w:sectPr>'
    )

    return xml(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:document xmlns:w="{W_NS}" xmlns:r="{R_NS}">
          <w:body>
            {''.join(body)}
          </w:body>
        </w:document>
        """
    )


def styles_xml() -> str:
    return xml(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:styles xmlns:w="{W_NS}">
          <w:docDefaults>
            <w:rPrDefault>
              <w:rPr>
                <w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>
                <w:sz w:val="{half_points(BODY_SIZE)}"/>
                <w:color w:val="{INK}"/>
              </w:rPr>
            </w:rPrDefault>
            <w:pPrDefault>
              <w:pPr>
                <w:spacing w:after="100" w:line="276" w:lineRule="auto"/>
              </w:pPr>
            </w:pPrDefault>
          </w:docDefaults>
          <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
            <w:name w:val="Normal"/>
            <w:qFormat/>
          </w:style>
          <w:style w:type="paragraph" w:styleId="Title">
            <w:name w:val="Title"/>
            <w:basedOn w:val="Normal"/>
            <w:qFormat/>
          </w:style>
          <w:style w:type="paragraph" w:styleId="Subtitle">
            <w:name w:val="Subtitle"/>
            <w:basedOn w:val="Normal"/>
            <w:qFormat/>
          </w:style>
          <w:style w:type="paragraph" w:styleId="Heading2">
            <w:name w:val="heading 2"/>
            <w:basedOn w:val="Normal"/>
            <w:uiPriority w:val="9"/>
            <w:qFormat/>
          </w:style>
          <w:style w:type="paragraph" w:styleId="Heading3">
            <w:name w:val="heading 3"/>
            <w:basedOn w:val="Normal"/>
            <w:uiPriority w:val="10"/>
            <w:qFormat/>
          </w:style>
        </w:styles>
        """
    )


def numbering_xml() -> str:
    return xml(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:numbering xmlns:w="{W_NS}">
          <w:abstractNum w:abstractNumId="0">
            <w:lvl w:ilvl="0">
              <w:start w:val="1"/>
              <w:numFmt w:val="bullet"/>
              <w:lvlText w:val="•"/>
              <w:lvlJc w:val="left"/>
              <w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr>
            </w:lvl>
          </w:abstractNum>
          <w:abstractNum w:abstractNumId="1">
            <w:lvl w:ilvl="0">
              <w:start w:val="1"/>
              <w:numFmt w:val="decimal"/>
              <w:lvlText w:val="%1."/>
              <w:lvlJc w:val="left"/>
              <w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr>
            </w:lvl>
          </w:abstractNum>
          <w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
          <w:num w:numId="2"><w:abstractNumId w:val="1"/></w:num>
        </w:numbering>
        """
    )


def settings_xml() -> str:
    return xml(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:settings xmlns:w="{W_NS}">
          <w:zoom w:val="bestFit" w:percent="100"/>
        </w:settings>
        """
    )


def web_settings_xml() -> str:
    return xml(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:webSettings xmlns:w="{W_NS}"/>
        """
    )


def font_table_xml() -> str:
    return xml(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:fonts xmlns:w="{W_NS}">
          <w:font w:name="Arial"/>
        </w:fonts>
        """
    )


def footer_xml(subtitle: str) -> str:
    metadata = subtitle or "AI Visibility snapshot"
    page_field = (
        '<w:r><w:rPr><w:color w:val="{color}"/><w:sz w:val="{size}"/></w:rPr><w:t>Page </w:t></w:r>'
        '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        '<w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        '<w:r><w:t>1</w:t></w:r>'
        '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
    ).format(color=MUTED, size=half_points(9))
    return xml(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:ftr xmlns:w="{W_NS}" xmlns:r="{R_NS}">
          <w:p>
            <w:pPr>
              <w:pBdr><w:top w:val="single" w:sz="6" w:space="1" w:color="{BORDER}"/></w:pBdr>
              <w:tabs><w:tab w:val="right" w:pos="9360"/></w:tabs>
            </w:pPr>
            {run_xml(metadata, color=MUTED, size=9)}
            <w:r><w:tab/></w:r>
            {page_field}
          </w:p>
        </w:ftr>
        """
    )


def content_types_xml() -> str:
    return xml(
        """
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
          <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
          <Default Extension="xml" ContentType="application/xml"/>
          <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
          <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
          <Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
          <Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
          <Override PartName="/word/webSettings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.webSettings+xml"/>
          <Override PartName="/word/fontTable.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.fontTable+xml"/>
          <Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
          <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
          <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
        </Types>
        """
    )


def package_rels_xml() -> str:
    return xml(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <Relationships xmlns="{PKG_REL_NS}">
          <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
          <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
          <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
        </Relationships>
        """
    )


def document_rels_xml() -> str:
    return xml(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <Relationships xmlns="{PKG_REL_NS}">
          <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
          <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>
          <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>
          <Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/webSettings" Target="webSettings.xml"/>
          <Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/fontTable" Target="fontTable.xml"/>
          <Relationship Id="rId6" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>
        </Relationships>
        """
    )


def core_xml() -> str:
    timestamp = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    return xml(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <cp:coreProperties xmlns:cp="{CP_NS}" xmlns:dc="{DC_NS}" xmlns:dcterms="{DCTERMS_NS}" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="{XSI_NS}">
          <dc:title>AI Visibility Report</dc:title>
          <dc:creator>Codex</dc:creator>
          <cp:lastModifiedBy>Codex</cp:lastModifiedBy>
          <dcterms:created xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:created>
          <dcterms:modified xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:modified>
        </cp:coreProperties>
        """
    )


def app_xml() -> str:
    return xml(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="{VT_NS}">
          <Application>Codex</Application>
        </Properties>
        """
    )


def build(md_path: Path, out_path: Path) -> None:
    lines = md_path.read_text(encoding="utf-8").splitlines()
    _, subtitle, _ = parse_metadata(lines)
    document = build_document_xml(lines)
    footer = footer_xml(subtitle)

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml())
        zf.writestr("_rels/.rels", package_rels_xml())
        zf.writestr("docProps/core.xml", core_xml())
        zf.writestr("docProps/app.xml", app_xml())
        zf.writestr("word/document.xml", document)
        zf.writestr("word/styles.xml", styles_xml())
        zf.writestr("word/numbering.xml", numbering_xml())
        zf.writestr("word/settings.xml", settings_xml())
        zf.writestr("word/webSettings.xml", web_settings_xml())
        zf.writestr("word/fontTable.xml", font_table_xml())
        zf.writestr("word/footer1.xml", footer)
        zf.writestr("word/_rels/document.xml.rels", document_rels_xml())

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python build_docx.py <report.md> <report.docx>")
        sys.exit(1)
    build(Path(sys.argv[1]), Path(sys.argv[2]))
