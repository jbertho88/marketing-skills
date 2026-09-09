"""Executive reporting and post-build reconciliation for the controlled formula set."""
import json
import re
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import xml.etree.ElementTree as ET
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, PatternFill, Alignment
from integrity import counts, count_line, decision

METRICS = ('Links earned', 'Unique referring domains earned', 'Editorial placements / inclusions',
           'Links to linkable assets', 'Internal links supporting commercial pages',
           'Non-brand rankings / impressions', 'Gap rerun')

def executive_markdown(d):
    e=d.get('executive_summary',{})
    lines=['## Executive summary', '', '**Run status:** '+d.get('run_status','Complete within declared scope'),
           '**Primary constraint:** '+e.get('primary_constraint','Not established from supplied evidence'),
           '**Confidence:** '+e.get('confidence','Not assessed')+' — '+e.get('confidence_reason','Review data coverage'),
           '**Opportunity counts:** '+count_line(d), '']
    for k in ('immediate','next_60_days','strategic','avoid'):
        lines.append(f"- {k.replace('_',' ')}: {e.get(k,'Not specified')}")
    lines += ['', '### 30/60/90-day measurement', '', '| Metric | Baseline | Day 30 | Day 60 | Day 90 | Owner / source |',
              '|---|---|---|---|---|---|']
    supplied={r['metric']:r for r in d.get('measurement',[])}
    for metric in METRICS:
        r=supplied.get(metric,{})
        values=[metric]+[str(r.get(k,'Not supplied')) for k in ('baseline','day_30','day_60','day_90')]+[str(r.get('owner','TBD'))+' / '+str(r.get('source','TBD'))]
        lines.append('| '+' | '.join(v.replace('|','\\|').replace('\n',' ') for v in values)+' |')
    lines += ['', 'Set baseline, owner, source and review dates before execution. Ranking movement is observational; do not attribute it solely to links.', '']
    return lines

def add_executive(wb,d):
    ws=wb.create_sheet('Executive Summary',0)
    lines=executive_markdown(d)
    lines=lines[:lines.index('### 30/60/90-day measurement')]
    for i,line in enumerate(lines,1):
        ws.cell(i,1,line)
        ws.cell(i,1).alignment=Alignment(wrap_text=True,vertical='top')
        ws.row_dimensions[i].height=32 if len(line)>100 else 24
    ws.column_dimensions['A'].width=145
    ws['A1'].font=Font(name='Arial',size=18,bold=True,color='17497A')
    ws.freeze_panes='A2'
    measure=wb.create_sheet('30-60-90 Measurement',1)
    measure.append(['Metric','Baseline','Day 30','Day 60','Day 90','Owner','Source / review dates'])
    supplied={r['metric']:r for r in d.get('measurement',[])}
    for metric in METRICS:
        r=supplied.get(metric,{})
        measure.append([metric]+[str(r.get(k,'Not supplied')) for k in ('baseline','day_30','day_60','day_90','owner','source')])
    for col in range(1,8):
        measure.column_dimensions[get_column_letter(col)].width=38 if col==1 else 28
    for row in measure:
        for c in row:
            c.alignment=Alignment(wrap_text=True,vertical='top')
    measure.freeze_panes='B2'
    audit=wb.create_sheet('Build Counts')
    audit.append(['Metric','Build-time count (rebuild after edits)'])
    for k,v in counts(d).items():
        audit.append([k,v])
    audit.column_dimensions['A'].width=30
    audit.column_dimensions['B'].width=45

def assert_outputs(d,xlsx,markdown,cols):
    """Evaluate the actual Summary/Decision formulas, compare, and cache this controlled set.

    Does not claim to be a general Excel calculation engine. Unsupported formulas fail.
    """
    wb=load_workbook(xlsx)
    ws=wb['5. Scored Targets']
    by_header={c.value:c.column_letter for c in ws[1]}
    computed={}
    actual=[]
    for i,r in enumerate(d.get('scored_targets',[]),2):
        sc,dc,gate=(by_header[h]+str(i) for h in ('Score','Decision','Evidence gate'))
        value=ws[sc].value
        if isinstance(value,str) and value.startswith('=SUM('):
            match=re.fullmatch(r'=SUM\(([A-Z]+\d+):([A-Z]+\d+)\)',value)
            if not match:
                raise AssertionError('Unsupported Score formula')
            score=sum(c.value or 0 for row in ws[match[1]+':'+match[2]] for c in row)
        else:
            score=value
        expected=f'=IF({gate}<>"Ready","Verify first",IF({sc}>=70,"Pursue",IF({sc}>=50,"Backlog","Discard")))'
        if ws[dc].value != expected:
            raise AssertionError('Decision formula drift')
        result='Verify first' if ws[gate].value!='Ready' else 'Pursue' if score>=70 else 'Backlog' if score>=50 else 'Discard'
        if result != decision(r):
            raise AssertionError('Workbook / JSON decision mismatch')
        actual.append(result)
        computed[('5. Scored Targets',sc)]=score
        computed[('5. Scored Targets',dc)]=result
    for row in wb['Summary']:
        c=row[1]
        if c.data_type!='f':
            continue
        match=re.fullmatch(r'=COUNTIF\(\'5\. Scored Targets\'!([A-Z]+)2:([A-Z]+)(\d+),"([^"]+)"\)',c.value)
        if match:
            a,b,end,criterion=match.groups()
            if a!=b:
                raise AssertionError('Summary range columns differ')
            values=[computed.get(('5. Scored Targets',a+str(i)),ws[a+str(i)].value) for i in range(2,int(end)+1)]
            value=values.count(criterion)
            if criterion in ('Pursue','Backlog','Discard','Verify first') and (a!=by_header['Decision'] or value!=counts(d)[criterion]):
                raise AssertionError('Summary counts wrong Decision column or values')
        elif c.value.startswith('=COUNTA('):
            value=len(actual)
        else:
            raise AssertionError('Unsupported Summary formula')
        computed[('Summary',c.coordinate)]=value
    if count_line(d) not in Path(markdown).read_text(encoding='utf-8'):
        raise AssertionError('Markdown count mismatch')
    if dict(wb['Build Counts'].iter_rows(min_row=2,values_only=True))!=counts(d):
        raise AssertionError('Workbook snapshot mismatch')
    # Cache only formulas validated above; openpyxl cannot write cached formula results.
    ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    tag='{'+ns['m']+'}'
    with ZipFile(xlsx) as z:
        parts={n:z.read(n) for n in z.namelist()}
    for index,name in enumerate(wb.sheetnames,1):
        key=f'xl/worksheets/sheet{index}.xml'
        root=ET.fromstring(parts[key])
        for cell in root.findall('.//m:c',ns):
            lookup=(name,cell.attrib['r'])
            if lookup not in computed or cell.find('m:f',ns) is None:
                continue
            val=computed[lookup]
            cell.set('t','str' if isinstance(val,str) else 'n')
            v=cell.find('m:v',ns)
            if v is None:
                v=ET.SubElement(cell,tag+'v')
            v.text=str(val)
        parts[key]=ET.tostring(root,encoding='utf-8',xml_declaration=True)
    with ZipFile(xlsx,'w',ZIP_DEFLATED) as z:
        for name,body in parts.items():
            z.writestr(name,body)
    cached=load_workbook(xlsx,data_only=True)
    for (sheet,cell),value in computed.items():
        if cached[sheet][cell].value!=value:
            raise AssertionError('Cached workbook count mismatch')
    # A normalized JSON artifact records the same decisions and counts as both presentations.
    d['summary_counts']=counts(d)
    dest=Path(xlsx).with_suffix('.findings.json')
    dest.write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf-8')
    if json.loads(dest.read_text(encoding='utf-8'))['summary_counts']!=counts(d):
        raise AssertionError('Exported JSON mismatch')
