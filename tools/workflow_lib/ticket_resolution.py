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
        latest = unit.get('reviews', [])[-1]
        known = [f for f in latest.get('result', {}).get('findings', []) if f['severity'] == 'blocking']
        unit['known_issues'] = known
        unit.setdefault('decisions', []).append(dict(action='accept', reason=reason, at=topics.now()))
        notes = reason + '\n\n已知问题：\n' + json.dumps(known, ensure_ascii=False, indent=2)
        return completion.commit_completion(repo, config, topic, path, unit, record, latest, notes, 'accepted')
    if status not in ('implementing', 'needs-user'):
        raise topics.TopicError('reopen 只接受 implementing/needs-user')
    changed = impl.definition(repo, path)
    if changed == unit['definition']:
        raise topics.TopicError('reopen 要求 Ticket 稳定定义或 Spec 变化；状态、认领、勾选不算')
    impl.validate(repo, path, config)
    impl.rule_material(repo, config, frontmatter(path), unit['execution_agent'])
    unit.update(definition=changed, tests=[], reviews=[])
    for key in ('test_run', 'active_review', 'first_review_volume', 'stop_reason'):
        unit.pop(key, None)
    unit.setdefault('decisions', []).append(dict(action='reopen', reason=reason, at=topics.now()))
    impl.write_json(record, unit)
    path.write_text(re.sub(r'^status:.*$', 'status: implementing', path.read_text(), count=1, flags=re.M))
    return dict(ticket=unit['ticket'], status='implementing', baseline=unit['baseline'], reason=reason)
