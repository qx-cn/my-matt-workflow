"""Evidence-bound technical corrections without a new review series or budget."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
import shlex

from . import topic_service as topics, ticket_implementation as impl
from .tickets import frontmatter
from .fs_safety import exclusive_lock, strict_relative_path, FilesystemSafetyError


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def latest_result(unit):
    return next((r for r in reversed(unit.get('reviews', [])) if r.get('result')), {})


def review_findings(unit):
    entry = latest_result(unit)
    resolved = {(r['unit_id'], r['finding_id']) for r in unit.get('technical_resolutions', [])}
    return [f for f in entry.get('result', {}).get('findings', [])
            if (entry['unit_id'], f['id']) not in resolved]


def review_rounds(unit):
    reviews = unit.get('reviews', [])
    # A real user reopen starts a new series. Missing legacy counters without
    # that decision cannot silently refund observed historical attempts.
    if not reviews and unit.get('past_reviews') and not any(
            d.get('action') in ('reopen', 'branch-reopen') for d in unit.get('decisions', [])):
        reviews = unit['past_reviews']
    observed = max(len({r.get('unit_id', str(i)) for i, r in enumerate(reviews)}),
                   max((r.get('round', 0) for r in reviews), default=0))
    return max(observed, unit.get('refresh_budget_floor', 0))


def review_series(unit, default):
    if unit.get('reviews'):
        return unit['reviews'][0].get('review_series', unit['reviews'][0]['unit_id'])
    return unit.get('refresh_review_series', default)


def read_notes(repo, notes_file):
    if not notes_file or not Path(notes_file).is_file():
        raise topics.TopicError('refresh: 必须提供 --notes-file 技术依据 JSON 文件')
    notes = json.loads(Path(notes_file).read_text())
    fields = {'kind', 'adjustment', 'unchanged_behavior', 'unchanged_acceptance', 'evidence', 'findings'}
    if not isinstance(notes, dict) or set(notes) != fields or notes.get('kind') != 'technical':
        raise topics.TopicError('refresh: 技术依据必须包含 kind=technical、adjustment、unchanged_behavior、unchanged_acceptance、evidence、findings')
    for key in ('adjustment', 'unchanged_behavior', 'unchanged_acceptance'):
        if not isinstance(notes[key], str) or not notes[key].strip():
            raise topics.TopicError('refresh: 缺少非空技术依据 '+key)
    if not isinstance(notes['evidence'], list) or not notes['evidence']:
        raise topics.TopicError('refresh: 必须提供可定位 evidence')
    observed = []
    for item in notes['evidence']:
        if not isinstance(item, dict) or set(item) != {'path', 'detail'} or not isinstance(item['detail'], str) or not item['detail'].strip():
            raise topics.TopicError('refresh: evidence 必须包含 path 和非空 detail')
        path = strict_relative_path(repo, item['path'])
        if not path.is_file() or not path.read_bytes():
            raise topics.TopicError('refresh: evidence 文件不存在或为空 '+str(item['path']))
        observed.append(dict(item, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    if not isinstance(notes['findings'], list):
        raise topics.TopicError('refresh: findings 必须为列表；无发现处置时使用 []')
    seen = set()
    for item in notes['findings']:
        if not isinstance(item, dict) or set(item) != {'unit_id', 'finding_id', 'basis'} or any(
                not isinstance(v, str) or not v.strip() for v in item.values()):
            raise topics.TopicError('refresh: findings 必须包含非空 unit_id、finding_id、basis')
        key = (item['unit_id'], item['finding_id'])
        if key in seen:
            raise topics.TopicError('refresh: 重复 finding 身份')
        seen.add(key)
    return notes, observed


def _nodes(repo, topic):
    from . import branch_review
    root = topics.topic_path(repo, topic)
    originals = {p: p.read_bytes() for pattern in ('*.json', 'implementations/*.json', 'batches/*.json', 'tickets/*.md', 'specs/*.md')
                 for p in root.glob(pattern) if p.is_file()}
    tickets = impl.records(repo, topic)
    plan_file = root / 'batches.json'
    plan = json.loads(originals[plan_file]) if plan_file in originals else None
    nodes = {}
    active_tickets = set()
    if plan:
        for index, batch in enumerate(plan['batches']):
            path = root / 'batches' / (batch['id']+'.json')
            batch = json.loads(originals[path]) if path in originals else batch
            plan['batches'][index] = batch
            if batch['status'] == 'closed' or not batch.get('baseline'):
                continue
            active_tickets.update(batch['tickets'])
            subset = {t: tickets[t] for t in batch['tickets']}
            old = batch.get('definition') or {t: json.loads(impl.record_path(repo, topic, t).read_text())['definition']
                                             for t in subset if impl.record_path(repo, topic, t).exists()}
            nodes['batch:'+batch['id']] = dict(unit=batch, path=path, current=branch_review.definition(repo, subset), old=old, ticket_path=None)
    for identifier, (path, value) in tickets.items():
        record = impl.record_path(repo, topic, identifier)
        if not record.exists() or (value['status'] == 'complete' and identifier not in active_tickets):
            continue
        unit = json.loads(originals[record])
        nodes['ticket:'+identifier] = dict(unit=unit, path=record, current=impl.definition(repo, path),
                                         old=unit['definition'], ticket_path=path)
    branch_file = root / 'branch-review.json'
    if branch_file.exists():
        unit = json.loads(originals[branch_file])
        nodes['branch'] = dict(unit=unit, path=branch_file, current=branch_review.definition(repo, tickets),
                               old=unit.get('definition'), ticket_path=None)
    return tickets, nodes, plan, plan_file, originals


def _challenges(nodes):
    from .batches import pending_self_findings
    result = {}
    for name, node in nodes.items():
        unit = node['unit']
        if name.startswith('ticket:') and unit.get('outcome') == 'accepted':
            continue  # Completed acceptance is a user decision, not a pending challenge.
        for f in review_findings(unit):
            if f.get('view') == 'spec-challenge':
                entry = latest_result(unit)
                result[(entry['unit_id'], f['id'])] = (name, f)
        if name.startswith('ticket:'):
            for f, _ in pending_self_findings(unit).values():
                if f.get('view') == 'spec-challenge':
                    result[('self:'+unit['ticket'], f['id'])] = (name, f)
    return result


def _invalidate(unit, current, receipt):
    # Preserve self observations, but retain current reviews in the same series.
    latest = unit.get('self_review')
    if latest and latest not in unit.setdefault('self_reviews', []):
        unit['self_reviews'].append(copy.deepcopy(latest))
    unit['refresh_budget_floor'] = review_rounds(unit)
    observed = unit.get('reviews') or unit.get('past_reviews', [])
    if observed and review_rounds(unit):
        unit['refresh_review_series'] = review_series(unit, observed[-1].get('review_series', observed[-1].get('unit_id')))
    unit['definition'] = current
    # Histories/receipts remain immutable; only their eligibility is invalidated.
    archived = {key: copy.deepcopy(unit[key]) for key in ('test_run', 'active_review', 'self_review', 'acceptance') if key in unit}
    unit.setdefault('invalidated_evidence', []).append(dict(at=receipt['at'], fingerprint=receipt['fingerprint'], records=archived))
    for key in ('test_run', 'active_review', 'self_review', 'acceptance'):
        unit.pop(key, None)
    unit['evidence_invalidated_at'] = receipt['at']
    unit['refresh_epoch'] = receipt['fingerprint']
    unit.setdefault('technical_refreshes', []).append(receipt)


def _other_stops(nodes):
    from .review_loop import geometric_stop
    stopped = []
    for name, node in nodes.items():
        unit = node['unit']
        status = frontmatter(node['ticket_path'])['status'] if node['ticket_path'] else unit.get('status')
        result = latest_result(unit).get('result', {})
        findings = result.get('findings', [])
        reason = unit.get('stop_reason', '')
        if status == 'needs-user' and (result.get('status') == 'inconclusive' or
                any(f.get('contradicts') for f in findings) or
                result.get('status') == 'blocked-by-design' and not any(f.get('view') == 'spec-challenge' for f in findings) or
                reason and not reason.startswith('Spec 与现有系统冲突：') and not geometric_stop(reason)):
            stopped.append(name)
    return stopped


def _restore_state(node, pending, selected_any, other_stops):
    unit = node['unit']
    status = frontmatter(node['ticket_path'])['status'] if node['ticket_path'] else unit.get('status')
    reason = unit.get('stop_reason', '')
    if review_rounds(unit) >= 4:
        unit['stop_reason'] = '轮数耗尽：技术刷新保留已开 4 轮；不能自动重开'
        return 'needs-user'
    if status != 'needs-user':
        return status
    latest = latest_result(unit)
    # Evidence/contradiction stops remain even when a technical fact is corrected.
    findings = latest.get('result', {}).get('findings', [])
    hard_result = latest.get('result', {}).get('status')
    unrelated_stop = hard_result == 'inconclusive' or any(f.get('contradicts') for f in findings)
    if hard_result == 'blocked-by-design' and not any(f.get('view') == 'spec-challenge' for f in findings):
        unrelated_stop = True
    spec_stop = reason.startswith('Spec 与现有系统冲突：') or (
        not reason and (not latest or any(f.get('view') == 'spec-challenge' for f in findings)))
    if pending or other_stops or unrelated_stop or not selected_any or not spec_stop:
        return status
    unit.pop('stop_reason', None)
    return 'implementing' if node['ticket_path'] else 'open' if 'id' in unit else 'implementing'


def _write_transaction(root, updates, originals):
    for path in originals:
        strict_relative_path(root, path.relative_to(root))
        current = path.read_bytes() if path.exists() else None
        if current != originals[path]:
            raise topics.TopicError('refresh: 状态在读取后变化，请重新核实')
    written = []
    try:
        for path, data in updates.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(path.suffix+'.refresh-tmp')
            temporary.write_bytes(data)
            temporary.replace(path)
            written.append(path)
    except BaseException:
        for path in reversed(written):
            if originals[path] is None:
                path.unlink(missing_ok=True)
            else:
                temporary = path.with_suffix(path.suffix+'.refresh-tmp')
                temporary.write_bytes(originals[path])
                temporary.replace(path)
        raise


def refresh(repo, topic=None, ticket=None, branch=False, batch=False, reason='', notes_file=None):
    try:
        return _refresh(repo, topic, ticket, branch, batch, reason, notes_file)
    except FilesystemSafetyError as exc:
        raise topics.TopicError('refresh: '+str(exc)) from exc


def _refresh(repo, topic=None, ticket=None, branch=False, batch=False, reason='', notes_file=None):
    if not isinstance(reason, str) or not reason.strip():
        raise topics.TopicError('refresh: 必须提供非空 --reason 技术调整理由')
    repo = topics.safe_repo(repo)
    if ticket:
        topic, path = impl.select(repo, ticket, topic)
        if frontmatter(path)['status'] not in ('implementing', 'needs-user'):
            raise topics.TopicError('refresh: Ticket 必须处于 implementing/needs-user')
    else:
        topic = topics.select_topic(repo, topic)
    root = topics.topic_path(repo, topic)
    if topics.topic_path(repo, topic, True).exists() or not root.is_dir():
        raise topics.TopicError('refresh: Topic 不存在或已归档')
    notes, observed = read_notes(repo, notes_file)
    with exclusive_lock(root, 'technical-refresh'):
        tickets, nodes, plan, plan_file, originals = _nodes(repo, topic)
        if branch and plan and not any(name.startswith('batch:') for name in nodes):
            raise topics.TopicError('refresh: 全部批次已收口；完成历史由补偿工作承接')
        key = 'ticket:'+ticket if ticket else 'branch' if branch else next(
            (name for name in nodes if name.startswith('batch:')), '')
        if key not in nodes:
            raise topics.TopicError('refresh: 缺少已开始的实施/审查记录')
        scope = {key}
        if ticket:
            scope.update(name for name, node in nodes.items() if not name.startswith('ticket:') and ticket in node['current'])
        else:
            identifiers = set(nodes[key]['current'])
            scope.update('ticket:'+t for t in identifiers if 'ticket:'+t in nodes)
            scope.update(name for name, node in nodes.items() if name == 'branch' or
                         name.startswith('batch:') and set(node['current']) & identifiers)
        snapshot = {name: node['current'] for name, node in nodes.items() if name in scope}
        fingerprint = digest(dict(reason=reason, notes=notes, evidence=observed, definitions=snapshot, content_id=topics.content_id(repo)))
        selected = nodes[key]['unit']
        last = selected.get('technical_refreshes', [])[-1:]
        if last and last[0].get('fingerprint') == fingerprint and all(
                nodes[name]['current'] == nodes[name]['old'] for name in scope):
            return dict(topic=topic, refresh='unchanged', target=key, rounds_used=review_rounds(selected))
        challenges = _challenges({name: node for name, node in nodes.items() if name in scope})
        chosen = []
        for item in notes['findings']:
            identity = (item['unit_id'], item['finding_id'])
            if identity not in challenges:
                raise topics.TopicError('refresh: finding 身份不存在或不是待处置 Spec 挑战 '+str(identity))
            owner, finding = challenges[identity]
            if finding.get('contradicts'):
                raise topics.TopicError('refresh: 语义矛盾必须由用户裁决')
            chosen.append((owner, item))
        changed = {name for name in scope if nodes[name]['current'] != nodes[name]['old']}
        if not changed and not chosen:
            raise topics.TopicError('refresh: 没有实际定义变化或技术性发现处置')
        for name in scope:
            if name.startswith('ticket:'):
                impl.validate(repo, nodes[name]['ticket_path'])
        receipt = dict(fingerprint=fingerprint, action='technical-refresh', reason=reason,
                       notes=notes, evidence=observed, content_id=topics.content_id(repo), at=topics.now())
        touched = changed | {key} | {owner for owner, _ in chosen}
        # Review and test eligibility in enclosing objects also depends on corrected
        # discoveries, even when the Ticket's stable definition did not change.
        if chosen:
            touched |= {name for name in scope if not name.startswith('ticket:')}
        for name in touched:
            originals.setdefault(nodes[name]['path'], None)
        for name in touched:
            unit = nodes[name]['unit']
            test_files = [root / ('batch-tests-'+unit['id']+'.json')] if name.startswith('batch:') else [root/'topic-tests.json'] if name == 'branch' else []
            event = dict(receipt, prior_definition=nodes[name]['old'], definition=nodes[name]['current'],
                         prior_status=frontmatter(nodes[name]['ticket_path'])['status'] if nodes[name]['ticket_path'] else unit.get('status'),
                         prior_stop_reason=unit.get('stop_reason'),
                         prior_full_tests={p.name: json.loads(originals[p]) for p in test_files if p in originals})
            _invalidate(unit, nodes[name]['current'], event)
        for owner, item in chosen:
            unit = nodes[owner]['unit']
            resolution = dict(item, action='technical-correction', evidence=observed, reason=reason, at=receipt['at'])
            unit.setdefault('technical_resolutions', []).append(resolution)
            if item['unit_id'].startswith('self:'):
                unit.setdefault('self_reviews', []).append(dict(at=receipt['at'], findings=[], resolutions=[
                    dict(id=item['finding_id'], **resolution)]))
        pending = _challenges({name: node for name, node in nodes.items() if name in scope})
        other_stops = _other_stops({name: node for name, node in nodes.items() if name in scope})
        updates = {}
        for name in touched:
            node = nodes[name]
            before = node['unit'].get('status')
            status = _restore_state(node, pending, bool(chosen), other_stops)
            if node['ticket_path']:
                path = node['ticket_path']
                original = originals[path]
                if frontmatter(path)['status'] != 'complete':
                    text = re.sub(r'^status:.*$', 'status: '+status, original.decode(), count=1, flags=re.M)
                    if text.encode() != original:
                        updates[path] = text.encode()
            elif status:
                node['unit']['status'] = status
            if name in touched or before != node['unit'].get('status'):
                updates[node['path']] = (json.dumps(node['unit'], ensure_ascii=False, indent=2)+'\n').encode()
        if plan:
            # Update mirrors in the plan with exactly the objects persisted above.
            for index, current in enumerate(plan['batches']):
                if 'batch:'+current['id'] in nodes:
                    plan['batches'][index] = nodes['batch:'+current['id']]['unit']
            updates[plan_file] = (json.dumps(plan, ensure_ascii=False, indent=2)+'\n').encode()
        if topics.content_id(repo) != receipt['content_id'] or read_notes(repo, notes_file) != (notes, observed):
            raise topics.TopicError('refresh: 内容在准备期间变化，请重新核实')
        _write_transaction(root, updates, originals)
        stopped=[dict(target=name,reason=nodes[name]['unit'].get('stop_reason')) for name in touched
                 if (frontmatter(nodes[name]['ticket_path'])['status'] if nodes[name]['ticket_path'] else nodes[name]['unit'].get('status'))=='needs-user']
        return dict(topic=topic, refresh='applied', target=key, rounds_used=review_rounds(selected),
                    rounds_remaining=max(0, 4-review_rounds(selected)), resolved=notes['findings'],
                    stops_remaining=stopped, evidence_invalidated=True, next_command=(
                        'workflow.py implement test --repo '+shlex.quote(str(repo))+' --ticket '+ticket if ticket
                        else 'workflow.py batch test --repo '+shlex.quote(str(repo))+' --topic '+topic if batch or plan
                        else 'workflow.py topic test --repo '+shlex.quote(str(repo))+' --topic '+topic))
