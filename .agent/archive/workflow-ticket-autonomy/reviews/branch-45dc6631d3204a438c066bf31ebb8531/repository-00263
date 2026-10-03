"""Explicit v1-to-v2 migration; preview builds a plan without writing files."""
from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
from datetime import datetime

from . import topic_service as topics
from .tickets import TicketError, frontmatter
from . import ticket_implementation as impl

OLD_STATUSES = {'revalidated', 'blocked-by-design', 'revising'}
ACTIVE_STATUSES = {'implementing', 'needs-user', *OLD_STATUSES}


def metadata(path):
    try:
        return frontmatter(path)
    except TicketError:
        return {}


def legacy_topic(path):
    """Completed records and records replaced by v2 implementations are history."""
    issues = []
    for ticket in (path / 'tickets').glob('*.md'):
        value = metadata(ticket)
        if value.get('status') == 'complete':
            if not (path / topics.STATE_FILE).exists() and 'test_commands' not in value:
                issues.append(str(ticket))
            continue
        if 'test_commands' not in value or value.get('status') in OLD_STATUSES:
            issues.append(str(ticket))
        identifier = value.get('id', ticket.stem.removeprefix('tickets-'))
        if not (path / 'implementations' / f'{identifier}.json').exists():
            issues.extend(str(p) for p in (path / 'runs').glob(f'run-{identifier}-spec-r*.json'))
    issues.extend(str(p) for p in (path / 'contexts').glob('*.md'))
    issues.extend(str(p) for p in (path / 'adr').glob('*.md'))
    return issues


def require_topic(path):
    if path.parent.name == 'work' and legacy_topic(path):
        raise topics.TopicError(f'Topic {path.name} 需要迁移；请运行 migrate')


def raw_config(repo):
    lines = (repo / '.agent/matt-workflow.md').read_text().splitlines()
    if not lines or lines[0] != '---' or '---' not in lines[1:]:
        raise topics.TopicError('无法自动迁移：配置缺少 frontmatter')
    value = {}
    for line in lines[1:lines.index('---', 1)]:
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        key, separator, raw = line.partition(':')
        key, raw = key.strip(), raw.strip()
        if not separator or key in value:
            raise topics.TopicError(f'无法自动迁移：配置字段 {key}')
        try:
            value[key] = json.loads(raw)
        except ValueError:
            value[key] = raw
        if key in topics.STRING_KEYS and not isinstance(value[key], (str, list, dict)):
            value[key] = raw
    return value


def render_metadata(value, body):
    return '---\n' + '\n'.join(f'{key}: {json.dumps(item, ensure_ascii=False)}' for key, item in value.items()) + '\n---\n' + body


def body(path):
    text = path.read_text()
    lines = text.splitlines(keepends=True)
    if lines and lines[0].strip() == '---' and any(line.strip() == '---' for line in lines[1:]):
        end = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == '---')
        return ''.join(lines[end + 1:])
    return text


def baseline(repo, root, identifier):
    records = []
    for path in sorted((root / 'runs').glob(f'run-{identifier}-spec-r*.json')):
        value = json.loads(path.read_text())
        context = value.get('context', {})
        sha = context.get('base_sha')
        if not sha or topics.git(repo, 'cat-file', '-e', f'{sha}^{{commit}}', check=False).returncode:
            raise topics.TopicError(f'{identifier} 旧记录缺少可验证基线，无法自动迁移')
        records.append((value.get('events', [{}])[0].get('at', ''), sha,
                        context.get('ticket', {}).get('execution_agent')))
    if not records:
        raise topics.TopicError(f'{identifier} 无旧基线；无法自动迁移')
    return sorted(records)[0][1:]


def convert_topic(repo, root, config):
    writes, active = {}, []
    paths = sorted((root / 'tickets').glob('*.md'))
    values = [metadata(path) for path in paths]
    if sum(value.get('status') in ACTIVE_STATUSES for value in values) > 1:
        raise topics.TopicError('迁移后违反 I-T3；整个 Topic 无法自动迁移')
    if values and all(value.get('status') == 'complete' for value in values):
        archive = topics.topic_path(repo, root.name, True)
        if archive.exists():
            raise topics.TopicError('归档重名；无法自动迁移')
        return writes, active, True
    if values and not topics.full_tests(config):
        raise topics.TopicError('standard Topic 全量测试集合为空；无法自动迁移')
    for spec in (root / 'specs').glob('*.md'):
        if not metadata(spec):
            match = re.fullmatch(rf'specs-{re.escape(root.name)}-([0-9]+)', spec.stem)
            if not match or int(match[1]) == 0:
                raise topics.TopicError(f'Spec revision 无法唯一推断：{spec.name}')
            writes[spec] = render_metadata({'spec_id': root.name, 'revision': int(match[1]), 'supersedes': '', 'status': 'current'}, body(spec))
    for path, value in zip(paths, values):
        if value.get('status') == 'complete':
            continue
        current = impl.record_path(repo, root.name, value.get('id', ''))
        if value.get('status') in {'implementing', 'needs-user'} and current.is_file() and 'test_commands' in value:
            continue
        match = re.fullmatch(rf'tickets-{re.escape(root.name)}-([0-9]{{2}})', path.stem)
        if not match:
            raise topics.TopicError(f'Ticket 文件名无法唯一推断：{path.name}')
        value.setdefault('id', path.stem.removeprefix('tickets-'))
        title = re.search(r'^#\s+(.+)$', body(path), re.M)
        if title:
            value.setdefault('title', title[1])
        value.setdefault('sequence', int(match[1]))
        if 'test_commands' not in value:
            commands = topics.full_tests(config)
            if not commands:
                raise topics.TopicError(f'{path.name} 全量测试集合为空；无法自动迁移')
            value['test_commands'] = commands
        # Do not guess rule scope, dependency edges, or Spec ownership.
        required = ('ticket_kind', 'spec_id', 'spec_revision', 'spec_ref', 'blocked_by',
                    'execution_agent')
        missing = [key for key in required if key not in value]
        if missing:
            raise topics.TopicError(f'{path.name} 无法唯一推断字段：{missing}')
        spec = repo / str(value['spec_ref'])
        if not spec.is_file() or not spec.resolve().is_relative_to(root / 'specs'):
            raise topics.TopicError(f'{path.name} Spec 归属无法确定')
        if value.get('status') not in {'ready-for-agent', 'implementing', 'needs-user', *OLD_STATUSES}:
            raise topics.TopicError(f'{path.name} 无法推断状态')
        if value['status'] in ACTIVE_STATUSES:
            sha, agent = baseline(repo, root, value['id'])
            if value['status'] in {'blocked-by-design', 'revising'}:
                value['status'] = 'needs-user'
            else:
                value['status'] = 'implementing'
            agent = agent or value.get('claimed_by') or value['execution_agent']
            if agent not in {'codex', 'claude', 'cursor'}:
                raise topics.TopicError(f'{path.name} 无法确定已绑定 Agent')
            value['claimed_by'] = agent
            active.append((path, value, sha, agent))
        value.setdefault('claimed_by', '')
        writes[path] = render_metadata(value, body(path))
    return writes, active, False


def knowledge_plan(repo, roots):
    writes, deletes = {}, []
    context = repo / '.agent/CONTEXT.md'
    combined = context.read_text() if context.exists() else ''
    definitions = {}
    def collect(text):
        for name, meaning in re.findall(r'^-\s+([^：:]+)[：:]\s*(.+)$', text, re.M):
            if name in definitions and definitions[name] != meaning:
                raise topics.TopicError(f'术语冲突：{name}；不自动合并')
            definitions[name] = meaning
    collect(combined)
    for root in roots:
        for source in sorted((root / 'contexts').glob('*.md')):
            text = source.read_text()
            collect(text)
            if text not in combined:
                combined += '\n' + text
            deletes.append(source)
        for source in sorted((root / 'adr').glob('*.md')):
            target = repo / '.agent/adr' / source.name
            text = source.read_text()
            previous = writes.get(target, target.read_text() if target.exists() else None)
            if previous is not None and previous != text:
                raise topics.TopicError(f'ADR 冲突：{source.name}；不自动合并')
            writes[target] = text
            deletes.append(source)
    if combined and (not context.exists() or context.read_text() != combined):
        writes[context] = combined
    return writes, deletes


def plan(repo):
    config = raw_config(repo)
    changes, unresolved = [], []
    new_config = {key: config[key] for key in topics.KEYS if key in config}
    new_config.update(schema_version=2, assurance_level='standard' if config.get('assurance_level') == 'audited' else config.get('assurance_level'))
    try:
        topics.validate_config(new_config)
    except topics.TopicError as exc:
        unresolved.append({'path': '.agent/matt-workflow.md', 'reason': str(exc)})
        return new_config, [{'path': '.agent/matt-workflow.md', 'category': '配置',
                             'conversion': '无法自动转换；先补全或修正配置字段'}], unresolved, [], {}, []
    if new_config != config:
        changes.append({'path': '.agent/matt-workflow.md', 'category': '配置', 'conversion': '九键 schema 2'})
    for path in sorted((repo / '.agent/specs').rglob('*')):
        if path.is_file():
            changes.append({'path': str(path.relative_to(repo)), 'category': '长期 Spec', 'conversion': '仅保留在备份'})
    if (repo / '.agent/specs').exists() and not any(c['category'] == '长期 Spec' for c in changes):
        changes.append({'path': '.agent/specs', 'category': '长期 Spec', 'conversion': '备份后删除空旧目录'})
    work = repo / '.agent/work'
    conversions = []
    for path in sorted(work.iterdir()) if work.exists() else ():
        if not path.is_dir() or not legacy_topic(path):
            continue
        try:
            writes, active, archive = convert_topic(repo, path, new_config)
        except (topics.TopicError, TicketError, ValueError, OSError) as exc:
            unresolved.append({'topic': path.name, 'reason': str(exc)})
            continue
        conversions.append((path, writes, active, archive))
        changes.append({'path': str(path.relative_to(repo)), 'category': 'Topic',
                        'conversion': '迁移归档' if archive else '补建 standard；转换 Ticket 和实施记录；合并术语与 ADR'})
        changes.extend({'path': str(p.relative_to(repo)), 'category': 'Spec/Ticket', 'conversion': '补字段并转换状态'} for p in writes)
        if archive or not (path / topics.STATE_FILE).exists():
            changes.append({'path': str((path / topics.STATE_FILE).relative_to(repo)), 'category': 'Topic 状态', 'conversion': '登记迁移状态'})
        changes.extend({'path': str(impl.record_path(repo, path.name, value['id']).relative_to(repo)), 'category': '实施记录', 'conversion': '旧基线；清空证据；绑定转换后定义'} for _, value, _, _ in active)
    try:
        knowledge, deletes = knowledge_plan(repo, [entry[0] for entry in conversions])
    except topics.TopicError as exc:
        unresolved.append({'path': '.agent/CONTEXT.md 或 .agent/adr', 'reason': str(exc)})
        # Conflicting knowledge stays with its entire Topic until resolved.
        conversions = []
        changes = [c for c in changes if c['category'] in {'配置', '长期 Spec'}]
        knowledge, deletes = {}, []
    changes.extend({'path': str(p.relative_to(repo)), 'category': '项目知识', 'conversion': '合并至项目级'} for p in knowledge)
    changes.extend({'path': str(p.relative_to(repo)), 'category': '分片知识', 'conversion': '合并后删除原分片'} for p in deletes)
    return new_config, changes, unresolved, conversions, knowledge, deletes


def migrate(repo, apply=False):
    repo = topics.safe_repo(repo)
    config, changes, unresolved, conversions, knowledge, deletes = plan(repo)
    report = {'applied': False, 'changes': changes, 'unresolved': unresolved,
              'message': '无需迁移' if not changes and not unresolved else '迁移预览'}
    if not apply:
        return report
    if any('topic' not in item for item in unresolved):
        raise topics.TopicError('项目级无法自动判断项未解决；不会执行迁移：' + json.dumps(unresolved, ensure_ascii=False))
    if not changes:
        return report
    topics.preflight_commit(repo, config)
    agent = repo / '.agent'
    backup = agent / ('backup-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    if backup.exists():
        raise topics.TopicError('备份目录重名；请稍后重试')
    shutil.copytree(agent, backup, ignore=shutil.ignore_patterns('.git', 'backup-*'))
    target = agent if config['agent_directory_mode'] == 'private' else repo
    index_path = Path(topics.git(target, 'rev-parse', '--absolute-git-dir').stdout.decode().strip()) / 'index'
    previous_index = index_path.read_bytes() if index_path.exists() else None
    try:
        apply_plan(repo, config, conversions, knowledge, deletes)
    except (topics.TopicError, OSError, ValueError):
        # The backup is retained even when a Git hook or filesystem operation fails.
        for path in agent.iterdir():
            if path.name == '.git' or path.name.startswith('backup-'):
                continue
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        shutil.copytree(backup, agent, dirs_exist_ok=True)
        ensure_backup_ignore(agent)
        if previous_index is None:
            index_path.unlink(missing_ok=True)
        else:
            index_path.write_bytes(previous_index)
        raise
    report.update(applied=True, backup=str(backup.relative_to(repo)), message='迁移已完成')
    return report


def ensure_backup_ignore(agent):
    ignore = agent / '.gitignore'
    text = ignore.read_text() if ignore.exists() else ''
    if 'backup-*/' not in text.splitlines():
        ignore.write_text(text.rstrip('\n') + '\nbackup-*/\n')


def apply_plan(repo, config, conversions, knowledge, deletes):
    agent = repo / '.agent'
    ensure_backup_ignore(agent)
    (agent / 'matt-workflow.md').write_text(topics.render_config(config))
    for root, writes, active, archive in conversions:
        for path, text in writes.items():
            path.write_text(text)
        if archive:
            impl.write_json(root / topics.STATE_FILE, {'status': 'archived', 'level': 'standard',
                            'outcome': 'complete', 'archived_at': topics.now(), 'reason': '迁移归档'})
        elif list((root / 'tickets').glob('*.md')):
            old_baselines = []
            for old_record in (root / 'runs').glob('run-*-spec-r*.json'):
                old = json.loads(old_record.read_text())
                sha = old.get('context', {}).get('base_sha')
                if sha and not topics.git(repo, 'cat-file', '-e', f'{sha}^{{commit}}', check=False).returncode:
                    old_baselines.append((old.get('events', [{}])[0].get('at', ''), sha))
            start = sorted(old_baselines)[0][1] if old_baselines else topics.git(repo, 'merge-base', 'HEAD', config['default_base_branch']).stdout.decode().strip()
            if not (root / topics.STATE_FILE).exists():
                impl.write_json(root / topics.STATE_FILE, {'status': 'active', 'level': 'standard',
                                'baseline': start, 'started_at': topics.now(), 'test_runs': 0,
                                'implementation_started': bool(active)})
            for path, value, sha, execution_agent in active:
                unit = {'ticket': value['id'], 'topic': root.name, 'baseline': sha,
                        'started_at': topics.now(), 'execution_agent': execution_agent,
                        'definition': impl.definition(repo, path), 'tests': [], 'reviews': [],
                        'migrated': True}
                if value['status'] == 'needs-user':
                    unit.update(stop_reason='迁移自旧版阻塞', needs_user_count=1)
                impl.write_json(impl.record_path(repo, root.name, value['id']), unit)
    for path, text in knowledge.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    for path in deletes:
        path.unlink()
    for root, _, _, archive in conversions:
        if archive:
            destination = topics.topic_path(repo, root.name, True)
            destination.parent.mkdir(exist_ok=True)
            root.rename(destination)
    if (agent / 'specs').exists():
        shutil.rmtree(agent / 'specs')
    target = agent if config['agent_directory_mode'] == 'private' else repo
    prefix = '' if target == agent else '.agent/'
    # Force .agent files individually; forcing the directory would stage backups.
    paths = [str(p.relative_to(target)) for p in agent.rglob('*') if p.is_file()
             and not any(part == '.git' or part.startswith('backup-') for part in p.relative_to(agent).parts)]
    topics.git(target, 'add', '--update', '--', '.' if target == agent else '.agent')
    if paths:
        topics.git(target, 'add', '--force', '--', *paths)
    topics.git(target, 'commit', '--only', '-m', 'migrate: convert workflow artifacts to schema 2', '--', '.' if target == agent else '.agent', f':(exclude,glob){prefix}backup-*/**')
