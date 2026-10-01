"""Explicit accept/reopen decisions, preserving baselines and decision history."""
from __future__ import annotations

import json
import re

from . import ticket_implementation as impl, ticket_completion as completion, topic_service as topics
from .tickets import frontmatter


def resolve(repo, ticket=None, topic=None, accept=False, reason=''):
    if not reason.strip():
        raise topics.TopicError('reason: 裁决必须有非空理由')
    repo = topics.safe_repo(repo)
    config = topics.read_config(repo)
    topic, path = impl.select(repo, ticket, topic)
    record = impl.record_path(repo, topic, frontmatter(path)['id'])
    unit = json.loads(record.read_text())
    status = frontmatter(path)['status']
    if accept:
        repo, config, topic, path, unit, record = impl.load_active(repo, ticket, topic)
        if status != 'needs-user':
            raise topics.TopicError('accept 只接受 needs-user')
        if not impl.tests_passed(repo, unit):
            raise topics.TopicError('test: 接受必须有当前完整声明测试通过记录')
        from . import batches
        batches.require_self(repo,unit)
        reviews = unit.get('reviews', [])
        if not reviews and not unit.get('migrated'):
            raise topics.TopicError('accept 缺少审查或迁移阻塞记录')
        latest = reviews[-1] if reviews else {}
        known = [f for f in latest.get('result', {}).get('findings', []) if f['severity'] == 'blocking' or f.get('view') == 'spec-challenge']
        unit['known_issues'] = known
        unit.setdefault('decisions', []).append(dict(action='accept', reason=reason, at=topics.now()))
        if unit.get('batch_id'):
            from . import batches
            batches.require_self(repo,unit)
            plan, batch = batches.active(repo,topic,unit['batch_id'])
            batch['status'] = 'open'
            batch.setdefault('decisions',[]).append(dict(ticket=unit['ticket'],reason=reason,at=topics.now()))
            batches.save(repo,topic,plan)
        notes = reason + '\n\n已知问题：\n' + json.dumps(known, ensure_ascii=False, indent=2)
        return completion.commit_completion(repo, config, topic, path, unit, record, latest, notes, 'accepted')
    if status not in ('implementing', 'needs-user'):
        raise topics.TopicError('reopen 只接受 implementing/needs-user')
    changed = impl.definition(repo, path)
    if changed == unit['definition']:
        raise topics.TopicError('reopen 要求 Ticket 稳定定义或 Spec 变化；状态、认领、勾选不算')
    impl.validate(repo, path, config)
    impl.rule_material(repo, config, frontmatter(path), unit['execution_agent'])
    from .quality_metrics import preserve_history
    preserve_history(unit)
    unit.update(definition=changed, tests=[], reviews=[])
    for key in ('test_run', 'active_review', 'first_review_volume', 'stop_reason'):
        unit.pop(key, None)
    if unit.get('batch_id'):
        from . import batches
        plan, batch = batches.active(repo,topic,unit['batch_id'])
        batch['status']='open'
        batch.pop('stop_reason',None)
        batch.setdefault('decisions',[]).append(dict(action='ticket-reopen',ticket=unit['ticket'],reason=reason,at=topics.now()))
        batches.save(repo,topic,plan)
    unit.pop('self_review',None)
    unit.setdefault('decisions', []).append(dict(action='reopen', reason=reason, at=topics.now()))
    impl.write_json(record, unit)
    path.write_text(re.sub(r'^status:.*$', 'status: implementing', path.read_text(), count=1, flags=re.M))
    return dict(ticket=unit['ticket'], status='implementing', baseline=unit['baseline'], reason=reason)
