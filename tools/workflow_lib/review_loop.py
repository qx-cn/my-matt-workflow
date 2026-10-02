"""Review budgets and stop signals measured on immutable content snapshots."""
from __future__ import annotations

import difflib
import json
from pathlib import Path
import re

from . import topic_service as topics


def stop(unit, path, record, reason):
    from .ticket_implementation import write_json
    unit['stop_reason'] = reason
    unit['needs_user_count'] = unit.get('needs_user_count', 0) + 1
    if path:
        path.write_text(re.sub(r'^status:.*$', 'status: needs-user', path.read_text(), count=1, flags=re.M))
    else:
        unit['status'] = 'needs-user'
    write_json(record, unit)


def files(manifest, side='current'):
    return {c['path']: Path(c[side]['snapshot_path']).read_bytes() if c[side] else b''
            for c in manifest['changes']}


def delta(old, new):
    """Ranges use half-open line offsets; insertions are boundary points."""
    changes = []
    for name in sorted(old.keys() | new.keys()):
        left, right = old.get(name, b''), new.get(name, b'')
        if left == right:
            continue
        matcher = difflib.SequenceMatcher(None, left.splitlines(), right.splitlines(), autojunk=False)
        for tag, a, b, c, d in matcher.get_opcodes():
            if tag != 'equal':
                changes.append(dict(path=name, old=[a, b], new=[c, d]))
    return changes


def overlap(a, b):
    if a[0] == a[1] or b[0] == b[1]:
        return max(a[0], b[0]) <= min(a[1], b[1])
    return max(a[0], b[0]) < min(a[1], b[1])


def inside(findings, repair):
    for finding in findings:
        if finding.get('severity') != 'blocking':
            continue
        match = re.fullmatch(r'(.+):(\d+)(?:-(\d+))?', finding.get('location', ''))
        if match:
            span = [int(match[2]) - 1, int(match[3] or match[2])]
            if any(r['path'] == match[1] and overlap(span, r['new']) for r in repair):
                return True
    return False


def volume(manifest):
    return sum((r['old'][1] - r['old'][0]) + (r['new'][1] - r['new'][0])
               for r in delta(files(manifest, 'base'), files(manifest)))


def repair_for(unit, manifest):
    previous = unit.get('reviews', [])
    # The last entry is the newly opened review; only a preceding blocking
    # result followed by a content change is a repair.
    if len(previous) < 2 or previous[-2].get('status') != 'findings':
        return []
    prior = json.loads(Path(previous[-2]['manifest']).read_text())
    # Include unchanged paths from either review when comparing two finals.
    old, new = files(prior), files(manifest)
    prior_base, current_base = files(prior, 'base'), files(manifest, 'base')
    for name in old.keys() | new.keys():
        old.setdefault(name, current_base.get(name, b''))
        new.setdefault(name, prior_base.get(name, b''))
    return delta(old, new)


def check_contradictions(unit, result):
    known = {f['id'] for r in unit.get('reviews', [])[:-1] for f in r.get('result', {}).get('findings', [])}
    for finding in result['findings']:
        if finding.get('contradicts') and finding['contradicts'] not in known:
            raise topics.TopicError('contradicts: 必须指向之前某轮的既有问题')


def signals(unit, manifest, result, repair):
    if any(f.get('view') == 'spec-challenge' for f in result['findings']):
        return 'Spec 与现有系统冲突：请用户决定修订 Spec、接受风险或按原 Spec 继续'
    if result['status'] in ('blocked-by-design', 'inconclusive'):
        return result['status']
    if any(f.get('contradicts') for f in result['findings']):
        return '前后矛盾：contradicts 指向之前的问题'
    # Line overlap and diff volume describe geometry, not causal progress.
    # They remain available in repair/first_review_volume for review evidence,
    # but only semantic contradictions, design/evidence stops and budgets gate.
    if manifest['round'] == 4 and any(f['severity'] == 'blocking' for f in result['findings']):
        return '轮数耗尽：第 4 轮仍有阻断问题'
    return None


def geometric_stop(reason):
    return isinstance(reason,str) and reason.startswith(('同一处连续修改：','同一根因：连续复审阻断落在前次修复内','体积膨胀：'))


def recover_geometry(unit, validate_pass, path=None):
    """Release only an obsolete geometric stop with current valid evidence."""
    if not geometric_stop(unit.get('stop_reason')):return False
    candidate=dict(unit,status='reviewing')
    try:
        validate_pass(candidate)
    except (topics.TopicError,OSError,ValueError,KeyError):return False
    unit.setdefault('recoveries',[]).append(dict(reason=unit['stop_reason'],at=topics.now(),
        action='release-obsolete-geometric-stop',content_id=unit['reviews'][-1]['content_id']))
    unit.pop('stop_reason',None)
    if path:
        path.write_text(re.sub(r'^status:.*$','status: implementing',path.read_text(),count=1,flags=re.M))
    else:
        unit['status']='reviewing'
    return True
