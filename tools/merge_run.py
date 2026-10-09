#!/usr/bin/env python3
"""Merge a new Max crawl run into spider-run.json. Union sources by id, dedupe findings by source+title,
never regress, secret-scan, write. Usage: merge_run.py <new-run.json> [spider-run.json]"""
import json, re, sys, datetime
new_p = sys.argv[1]; master_p = sys.argv[2] if len(sys.argv) > 2 else 'spider-run.json'
TYPES = {'idea', 'outcome', 'skill', 'practice', 'error', 'question', 'task'}
SECRETS = [r"sk-ant-[A-Za-z0-9_-]{20,}", r"ghp_[A-Za-z0-9]{30,}", r"github_pat_[A-Za-z0-9_]{30,}", r"AKIA[0-9A-Z]{16}",
           r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", r"\b\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}\b", r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}"]
add = json.load(open(new_p, encoding='utf-8'))
assert isinstance(add.get('run'), dict) and isinstance(add.get('sources'), list) and isinstance(add.get('findings'), list), 'bad run shape'
raw = json.dumps(add, ensure_ascii=False)
hits = [p for p in SECRETS if re.search(p, raw)]
if hits: sys.exit(f'REFUSED: secret/email/phone pattern in new run: {hits}')
add['findings'] = [f for f in add['findings'] if f.get('type') in TYPES]
try: base = json.load(open(master_p, encoding='utf-8'))
except FileNotFoundError: base = None
if base is None:
    out = add
else:
    S = {s['id']: s for s in base['sources']}
    for s in add['sources']:
        o = S.get(s['id'])
        if not o or str(s.get('date', '')) >= str(o.get('date', '')): S[s['id']] = {**(o or {}), **s}
    key = lambda f: (f.get('source', ''), str(f.get('title', '')).lower()[:80])
    F = {key(f): f for f in base['findings']}
    for f in add['findings']:
        o = F.get(key(f)); F[key(f)] = {**o, **f, 'id': o['id']} if o else f
    findings = [{**f, 'id': f'f-{i+1:04d}'} for i, f in enumerate(F.values())]
    sources = list(S.values())
    for s in sources: s['findings'] = sum(1 for f in findings if f.get('source') == s['id'])
    frm = [x for x in (base['run'].get('merged_from') or [base['run']['id']]) + (add['run'].get('merged_from') or [add['run']['id']]) if x]
    frm = list(dict.fromkeys(frm))
    new_src = [s['id'] for s in add['sources'] if s['id'] not in {b['id'] for b in base['sources']}]
    out = {'run': {'id': 'merged:' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                   'started': base['run'].get('started') or add['run'].get('started'), 'finished': add['run'].get('finished'),
                   'sources_attempted': len(sources), 'sources_read': len(sources),
                   'sources_skipped': (base['run'].get('sources_skipped') or 0) + (add['run'].get('sources_skipped') or 0),
                   'scope': ' + '.join(x for x in [base['run'].get('scope'), add['run'].get('scope')] if x),
                   'merged_from': frm, 'new_sources': new_src}, 'sources': sources, 'findings': findings}
json.dump(out, open(master_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f"merged: {len(out['sources'])} sources ({len(out['run'].get('new_sources', []))} new) · {len(out['findings'])} findings · runs {len(out['run'].get('merged_from', [out['run']['id']]))}")
