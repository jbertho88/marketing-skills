"""Shared evidence, coverage and decision contract for every output."""
import re
from urllib.parse import urlsplit
from collections import Counter

FACTORS = {'relevance':30, 'authority':20, 'traffic_score':15, 'context':15, 'spam_clean':10, 'contact':10}
DECISIONS = ('Pursue', 'Backlog', 'Discard', 'Verify first')
ENTITY_SECTIONS = ('link_gap', 'recently_earned', 'strongest_links', 'competitor_top_pages')

def normalize_domain(value):
    value = str(value or '').strip().lower()
    match = re.search(r'\(([^()]+)\)', value)
    if match:
        value = match.group(1)
    host = urlsplit(value if '://' in value else '//' + value).hostname or ''
    return host.removeprefix('www.').rstrip('.').encode('idna').decode('ascii')

def valid_url(value):
    p = urlsplit(str(value or ''))
    return p.scheme in ('http', 'https') and bool(p.hostname)

def evidence_ready(r):
    return (r.get('evidence_status') == 'Verified link page'
            and valid_url(r.get('linking_page')) and valid_url(r.get('competitor_destination'))
            and bool(r.get('date_verified')) and bool(r.get('verification_source')))

def audit_ready(r):
    return evidence_ready(r) and all(
        isinstance(r.get(k), (int,float)) and not isinstance(r.get(k), bool)
        and 0 <= r[k] <= maximum and bool((r.get('factor_evidence') or {}).get(k))
        for k, maximum in FACTORS.items()) and (
            not r.get('traffic_score') or r.get('traffic') is not None or
            (bool(r.get('traffic_proxy')) and bool(r.get('traffic_source'))))

def decision(r):
    if not audit_ready(r):
        return 'Verify first'
    total = sum(r[k] for k in FACTORS)
    return 'Pursue' if total >= 70 else 'Backlog' if total >= 50 else 'Discard'

def counts(d):
    rows = d.get('scored_targets', [])
    c = dict(Counter(decision(r) for r in rows))
    return {'opportunities':len(rows), 'unique_domains':len({normalize_domain(r['domain']) for r in rows}),
            **{k:c.get(k,0) for k in DECISIONS},
            'unique_pursue_domains':len({normalize_domain(r['domain']) for r in rows if decision(r)=='Pursue'})}

def count_line(d):
    return ' | '.join(f'{k}: {v}' for k,v in counts(d).items())

def coverage_problems(d):
    problems=[]
    competitors={normalize_domain(c['domain']) for c in d.get('competitors',[])}
    for section in ENTITY_SECTIONS:
        c=d.get('coverage',{}).get(section,{})
        expected={normalize_domain(x) for x in c.get('expected',[])}
        completed={normalize_domain(x) for x in c.get('completed',[])}
        omitted={normalize_domain(k):v for k,v in c.get('omitted',{}).items()}
        if not competitors <= expected:
            problems.append(f'{section}: expected omits competitors {sorted(competitors-expected)}')
        if completed-expected or set(omitted)-expected or completed & set(omitted):
            problems.append(f'{section}: invalid completed/omitted entities')
        for entity in expected-completed:
            problems.append(f'{section}: {entity} not completed; {omitted.get(entity) or "no entity reason"}')
        if c.get('partial_reason'):
            problems.append(f'{section}: {c["partial_reason"]}')
        c['coverage_label']=f'{len(expected & completed)}/{len(expected)} entities completed'
    return problems

def direct_follow_complement(r):
    """Complement of union, NOT count of domains with at least one direct-follow link."""
    total, indirect, nofollow = (r.get(k) for k in ('domains_to_page','indirect_domains','nofollow_domains'))
    overlap = r.get('indirect_nofollow_overlap')
    if r.get('subsets_mutually_exclusive') is True:
        overlap=0
    if overlap is None or not r.get('composition_evidence') or any(v is None for v in (total,indirect,nofollow)):
        return None
    if not (0 <= overlap <= min(indirect,nofollow) and max(indirect,nofollow) <= total and indirect+nofollow-overlap <= total):
        raise ValueError('Invalid referring-domain set composition')
    return total-indirect-nofollow+overlap

def prepare(d):
    for section in ('link_gap','recently_earned','strongest_links','page_gap','scored_targets','spam_solicitation'):
        for r in d.get(section,[]):
            if r.get('domain'):
                r['domain']=normalize_domain(r['domain'])
    for r in d.get('serp_benchmark',[]):
        r['neither_indirect_nor_nofollow']=direct_follow_complement(r)
    for r in d.get('recently_earned',[]):
        r['evidence_decision']='Verified evidence' if evidence_ready(r) else 'Verify first'
    seen=set()
    for i,r in enumerate(d.get('scored_targets',[]),1):
        r.setdefault('opportunity_id', f'opp-{i:04}')
        if r['opportunity_id'] in seen:
            raise ValueError('Duplicate opportunity_id')
        seen.add(r['opportunity_id'])
        r['evidence_gate']='Ready' if audit_ready(r) else 'Verify first'
        r['score_decision']=decision(r)
        default={'Pursue':'Pursue now','Backlog':'Hold','Discard':'Hold','Verify first':'Verify'}[decision(r)]
        r.setdefault('execution_decision',default)
        if r['execution_decision'] not in ('Pursue now','Verify','Hold','Hygiene quick win'):
            raise ValueError('Invalid execution decision')
        if r['execution_decision'] != default and not r.get('override_reason'):
            raise ValueError('Execution override requires override_reason')
        if decision(r)=='Verify first' and r['execution_decision'] not in ('Verify','Hold'):
            raise ValueError('Unverified evidence cannot be overridden into outreach')
        for k in FACTORS:
            r[k+'_evidence']=(r.get('factor_evidence') or {}).get(k,'')
    live=d.get('live_serp',{})
    if live.get('supplied') and not all(live.get(k) for k in ('source','date','locale','queries')):
        raise ValueError('Live SERP requires source, date, locale and queries')
    if live.get('supplied'):
        for r in d.get('serp_benchmark',[]):
            if r.get('keyword') not in live['queries'] or not r.get('position'):
                raise ValueError('Live SERP row requires supplied keyword and position')
    for proof in d.get('approved_proof_points',[]):
        if not all(proof.get(k) for k in ('id','claim','source','approved_by')):
            raise ValueError('Proof points require id, claim, source and approved_by')

def validate_plan(d):
    by_id={r['opportunity_id']:r for r in d.get('scored_targets',[])}
    approved={p['id'] for p in d.get('approved_proof_points',[])}
    for section in ('outreach_plan','listicle_targets','asset_roadmap'):
        for r in d.get(section,[]):
            if section=='asset_roadmap' and not r.get('earned_link_destination'):
                raise ValueError('Asset roadmap requires an earned_link_destination; identify proposed URLs as proposed')
            if section in ('asset_roadmap','outreach_plan') and not r.get('commercial_page_supported') and not r.get('commercial_support_reason'):
                raise ValueError('Action requires commercial_page_supported or commercial_support_reason explaining why none applies')
            if set(r.get('proof_point_ids',[]))-approved:
                raise ValueError('Unknown approved proof point')
            if section=='outreach_plan':
                source=by_id.get(r.get('opportunity_id'))
                if source is None:
                    raise ValueError('Outreach plan must reference a scored opportunity_id')
                for field in ('execution_decision','override_reason','score_decision'):
                    if field in r and r[field] != source.get(field):
                        raise ValueError('Plan decision differs from scorecard; set override on scorecard')
                    r[field]=source.get(field,'')
                if r['execution_decision'] in ('Pursue now','Hygiene quick win') and not r.get('earned_link_destination'):
                    raise ValueError('Active outreach requires an earned_link_destination')
            if not approved:
                r.setdefault('proof_point_note','Insert verified client differentiation here')
    active={r['opportunity_id'] for r in d.get('scored_targets',[]) if r['execution_decision'] in ('Pursue now','Hygiene quick win')}
    planned={r.get('opportunity_id') for r in d.get('outreach_plan',[])}
    if active-planned:
        raise ValueError('Active opportunities missing from outreach plan; mark Hold with an override reason or include them')

def validate_partial_reasons(d):
    for section in ENTITY_SECTIONS:
        c=d.get('coverage',{}).get(section,{})
        expected={normalize_domain(x) for x in c.get('expected',[])}
        expected |= {normalize_domain(x['domain']) for x in d.get('competitors',[])}
        completed={normalize_domain(x) for x in c.get('completed',[])}
        omitted={normalize_domain(k):v for k,v in c.get('omitted',{}).items()}
        if any(not omitted.get(x) for x in expected-completed):
            raise ValueError(f'{section}: partial build still requires a reason for each omitted entity')
