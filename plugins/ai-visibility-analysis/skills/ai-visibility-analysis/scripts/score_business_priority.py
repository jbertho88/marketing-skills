"""Compute auditable optional business scores from human-reviewed CSV inputs."""
import argparse
import csv
import math


def number(row, key, upper, required=False):
    raw = '' if row.get(key) is None else str(row.get(key)).strip()
    if not raw:
        if required:
            raise ValueError(f'{key} is required')
        return None
    value = float(raw)
    if not math.isfinite(value) or not 0 <= value <= upper:
        raise ValueError(f'{key} must be between 0 and {upper}')
    return value / upper


def weighted(parts):
    coverage = sum(weight for value, weight in parts if value is not None)
    score = sum(value * weight for value, weight in parts if value is not None)
    return 100 * score / coverage, round(100 * coverage)


def score_row(mode, row):
    relevance = number(row, 'relevance', 5, True)
    if mode == 'prompts':
        score, coverage = weighted([
            (relevance, .5), (number(row, 'decision_value', 5, True), .3),
            (number(row, 'customer_evidence', 5), .2)])
        return {'prompt_value': round(score if relevance else 0, 1),
                'component_coverage_pct': coverage,
                'score_status': 'complete' if coverage == 100 else 'provisional',
                'score_version': 'business-v1'}
    score, coverage = weighted([
        (relevance, .4), (number(row, 'targeted_coverage', 1), .3),
        (number(row, 'model_breadth', 1), .1),
        (number(row, 'quality', 5), .1), (number(row, 'organic_reach', 1), .1)])
    score = score if relevance else 0
    gap = number(row, 'gap', 5)
    return {'citation_value': round(score, 1),
            'action_priority': round(score * gap, 1) if gap is not None else '',
            'component_coverage_pct': coverage,
            'score_status': 'complete' if coverage == 100 else 'provisional',
            'score_version': 'business-v1'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prompts', 'citations'])
    parser.add_argument('input')
    parser.add_argument('output')
    args = parser.parse_args()
    with open(args.input, encoding='utf-8-sig', newline='') as source:
        reader = csv.DictReader(source)
        fields = reader.fieldnames or []
        identity = 'prompt' if args.mode == 'prompts' else 'canonical_url'
        required = {identity, 'relevance'}
        if args.mode == 'prompts':
            required.add('decision_value')
        if not required.issubset(fields):
            parser.error('Missing columns: ' + ', '.join(sorted(required - set(fields))))
        output = []
        seen = set()
        for line, row in enumerate(reader, 2):
            try:
                key = (row.get(identity) or '').strip()
                if not key or key in seen:
                    raise ValueError(f'{identity} must be nonblank and unique')
                seen.add(key)
                output.append({**row, **score_row(args.mode, row)})
            except ValueError as exc:
                parser.error(f'Row {line}: {exc}')
    if not output:
        parser.error('No input rows')
    new_fields = [field for field in output[0] if field not in fields]
    with open(args.output, 'w', encoding='utf-8-sig', newline='') as target:
        writer = csv.DictWriter(target, fieldnames=fields + new_fields)
        writer.writeheader()
        writer.writerows(output)
    print(f'Scored {len(output)} {args.mode}; output: {args.output}')


if __name__ == '__main__':
    main()
