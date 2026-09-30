"""Current-evidence Ticket completion and Git/metadata commit recovery."""
from __future__ import annotations

import json
from pathlib import Path
import re

from . import ticket_implementation as impl, ticket_review as review, topic_service as topics
from .tickets import frontmatter


def metric(unit, outcome, verdict):
    findings = [f for r in unit.get('reviews', []) for f in r.get('result', {}).get('findings', [])]
    return {'kind': 'ticket', 'topic': unit['topic'], 'ticket': unit['ticket'], 'level': 'standard',
            'started_at': unit['started_at'], 'finished_at': topics.now(), 'outcome': outcome,
            'test_runs': len({t.get('run_id', t.get('finished_at')) for t in unit['tests']}),
            'review_rounds': len(unit.get('reviews', [])),
            'findings': {s: sum(f.get('severity') == s for f in findings) for s in ('blocking', 'advisory')},
            'repair_rounds': sum(r.get('status') == 'findings' for r in unit.get('reviews', [])),
            'needs_user_count': unit.get('needs_user_count', 0), 'command_errors': None,
            'reviewer_provenance': verdict['reviewer']['provenance'], 'tests_configured': True}


def finish(repo, ticket=None, topic=None, notes_file=None):
    repo, config, topic, path, unit, record = impl.load_active(repo, ticket, topic)
    value = frontmatter(path)
    if value['status'] != 'implementing':
        raise topics.TopicError('finish 只接受 implementing')
    if not impl.tests_passed(repo, unit):
        raise topics.TopicError('test: 当前内容没有完整声明测试通过记录；请重新测试')
    verdict = review.require_pass(repo, config, topic, path, unit)
    if re.search(r'^\s*- \[ \]', path.read_text(), re.M):
        raise topics.TopicError('acceptance: 验收复选框必须全部勾选')
    repairs = any(r.get('status') == 'findings' for r in unit.get('reviews', []))
    if repairs and not notes_file:
        raise topics.TopicError('notes_file: 经历修复必须提供修复思路')
    notes = Path(notes_file).read_text() if notes_file else ''
    if repairs and not notes.strip():
        raise topics.TopicError('notes_file: 修复思路不能为空')
    topics.preflight_commit(repo, config)
    private = config['agent_directory_mode'] == 'private'
    dirty = topics.content_dirty(repo)
    if dirty and unit.get('commit'):
        raise topics.TopicError('Ticket 已做代码提交；新增内容请另建 Ticket')
    message = f"{unit['ticket']}: {value['title']}" + ('\n\n' + notes if notes.strip() else '')
    # In private mode retain the successful code commit before metadata commit.
    # A metadata hook failure may retry without producing another code commit.
    if private and dirty:
        topics.git(repo, 'add', '--all', '--', '.', ':(top,exclude).agent')
        topics.git(repo, 'commit', '-m', message)
        unit['commit'] = topics.git(repo, 'rev-parse', 'HEAD').stdout.decode().strip()
        impl.write_json(record, unit)
    metrics = repo / '.agent/metrics.jsonl'
    before = {p: p.read_bytes() if p.exists() else None for p in (path, record, metrics)}
    try:
        path.write_text(re.sub(r'^claimed_by:.*$', 'claimed_by:',
                              re.sub(r'^status:.*$', 'status: complete', path.read_text(), flags=re.M), flags=re.M))
        unit['outcome'] = 'complete'
        impl.write_json(record, unit)
        with metrics.open('a') as stream:
            stream.write(json.dumps(metric(unit, 'complete', verdict), ensure_ascii=False) + '\n')
        if private:
            topics.git(repo / '.agent', 'add', '--force', '--all', '--', '.')
            topics.git(repo / '.agent', 'commit', '-m', message)
        else:
            topics.git(repo, 'add', '--force', '--all', '--', '.agent')
            if dirty:
                topics.git(repo, 'add', '--all', '--', '.', ':(top,exclude).agent')
            topics.git(repo, 'commit', '--only', '-m', message, '--', '.' if dirty else '.agent')
    except (topics.TopicError, OSError):
        for p, data in before.items():
            if data is None:
                p.unlink(missing_ok=True)
            else:
                p.write_bytes(data)
        raise
    return {'ticket': unit['ticket'], 'topic': topic, 'status': 'complete',
            'commit': unit.get('commit') or (topics.git(repo, 'rev-parse', 'HEAD').stdout.decode().strip() if dirty else None),
            'next_command': impl.next_start_command(repo, topic)}
