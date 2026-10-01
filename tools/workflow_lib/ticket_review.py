"""Frozen v2 Ticket review materials and semantic-result admission."""
from __future__ import annotations

import fnmatch
import hashlib
import json
from pathlib import Path
import shutil
import re
import uuid

from . import ticket_implementation as impl
from . import topic_service as topics, review_loop
from .tickets import acceptance_items, frontmatter

PREFILLED = ('unit_id', 'content_id', 'round', 'acceptance', 'probes', 'downstream_tickets')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def content_path(name):
    return Path(name).parts[0] not in {'.agent', '.git'}


def baseline_files(repo, baseline):
    files = {}
    for entry in topics.git(repo, 'ls-tree', '-rz', '--full-tree', baseline).stdout.split(b'\0'):
        if not entry:
            continue
        metadata, name = entry.split(b'\t', 1)
        mode, kind, oid = metadata.decode().split()
        name = name.decode()
        if content_path(name):
            if kind != 'blob':
                raise topics.TopicError(f'无法冻结非 blob 内容：{name}')
            files[name] = (mode, topics.git(repo, 'cat-file', 'blob', oid).stdout)
    return files


def current_files(repo):
    files = {}
    for name in topics.content_paths(repo):
        if not content_path(name):
            continue
        path = repo / name
        if path.is_symlink():
            files[name] = ('120000', path.readlink().as_posix().encode())
        elif path.is_file():
            files[name] = ('100755' if path.stat().st_mode & 0o111 else '100644', path.read_bytes())
        elif path.exists():
            raise topics.TopicError(f'无法冻结非常规内容：{name}')
    return files


def frozen_file(directory, filename, data, mode='100644'):
    path = directory / filename
    path.write_bytes(data)
    path.chmod(0o444)
    return {'snapshot_path': str(path), 'sha256': digest(data), 'size': len(data), 'mode': mode}


def targets(path):
    return acceptance_items(path)


def downstream(repo, topic, identifier):
    return [{'id': value['id'], 'acceptance': targets(path)}
            for path, value in impl.records(repo, topic).values() if identifier in value['blocked_by']]


def loop_rules():
    return (Path(__file__).resolve().parents[2] / 'resources' / 'review-loop.md').read_text()


def open_review(repo, ticket=None, topic=None, reviewer_model=None, reviewer_session_id=None):
    repo, config, topic, path, unit, record = impl.load_active(repo, ticket, topic)
    value = frontmatter(path)
    if value['status'] != 'implementing':
        raise topics.TopicError('implement review 只接受 implementing')
    if not isinstance(reviewer_model, str) or not reviewer_model.strip():
        raise topics.TopicError('reviewer.model: 开启审查时请用 --reviewer-model 声明宿主实际模型')
    if len(unit.get('reviews', [])) >= 4:
        try:
            require_pass(repo, config, topic, path, unit)
        except (topics.TopicError, OSError, ValueError):
            review_loop.stop(unit, path, record, '轮数耗尽：4 轮后没有当前有效通过记录')
        raise topics.TopicError('轮数上限为 4；拒绝第 5 轮')
    implementation_session = unit.setdefault('implementation_session_id', uuid.uuid4().hex)
    review_context = {'provenance': 'independent' if reviewer_session_id and reviewer_session_id != implementation_session else 'self',
                      'model': reviewer_model, 'session_id': reviewer_session_id or implementation_session}
    starting_definition = impl.definition(repo, path)
    identity = topics.content_id(repo)
    base, current = baseline_files(repo, unit['baseline']), current_files(repo)
    unit_id = uuid.uuid4().hex
    root = topics.topic_path(repo, topic)
    directory = root / 'reviews' / f"{unit['ticket']}-{unit_id}"
    directory.mkdir(parents=True)
    try:
        changes = []
        for i, name in enumerate(sorted(set(base) | set(current))):
            if base.get(name) == current.get(name):
                continue
            item = {'path': name, 'base': None, 'current': None}
            for side, files in [('base', base), ('current', current)]:
                if name in files:
                    mode, data = files[name]
                    item[side] = frozen_file(directory, f'{i:04d}-{side}', data, mode)
            changes.append(item)
        rules, sources = impl.rule_material(repo, config, value, unit['execution_agent'])
        spec = (repo / value['spec_ref']).read_text()
        decided = root / 'decided' / f'decided-{topic}.md'
        inputs = [frozen_file(directory, 'rules.md', '\n\n'.join(sources).encode()),
                  frozen_file(directory, 'spec.md', spec.encode()),
                  frozen_file(directory, 'review-loop-rules.md', loop_rules().encode()),
                  frozen_file(directory, 'decided.md', decided.read_bytes() if decided.exists() else b'')]
        skeleton = {'unit_id': unit_id, 'content_id': identity,
                    'round': len(unit.get('reviews', [])) + 1,
                    'acceptance': targets(path), 'probes': value['review_probes'],
                    'downstream_tickets': downstream(repo, topic, unit['ticket']),
                    'status': None, 'reviewer': {'provenance': None, 'model': None},
                    'coverage': [], 'findings': []}
        manifest = {**{k: skeleton[k] for k in PREFILLED}, 'ticket': unit['ticket'],
                    'baseline': unit['baseline'], 'changes': changes,
                    'outside_scope': [c['path'] for c in changes if not any(fnmatch.fnmatchcase(c['path'], s) for s in value['rule_scope'])],
                    'inputs': inputs, 'rule_map': rules, 'review_context': review_context,
                    'coverage_targets': [a['id'] for a in skeleton['acceptance']] + skeleton['probes']
                        + sorted(set(re.findall(r'\*\*(I-(?:[A-Z]+)?[0-9]+)\*\*', spec)))}
        manifest_path = directory / 'manifest.json'
        impl.write_json(manifest_path, manifest)
        manifest_path.chmod(0o444)
        result_file = root / 'reviews' / f'result-{unit_id}.json'
        impl.write_json(result_file, skeleton)
        if topics.content_id(repo) != identity:
            raise topics.TopicError('冻结期间 content_id 变化；请重新 review')
        if impl.definition(repo, path) != starting_definition:
            raise topics.TopicError('acceptance: 冻结期间定义变化，请重新 review')
        if topics.read_config(repo) != config:
            raise topics.TopicError('rules: 冻结期间配置变化，请重新 review')
        active = {'manifest': str(manifest_path), 'manifest_sha256': digest(manifest_path.read_bytes()),
                  'snapshot_dir': str(directory), 'result_file': str(result_file),
                  'definition': starting_definition, 'config': config}
        unit.setdefault('first_review_volume', review_loop.volume(manifest))
        unit['active_review'] = active
        unit.setdefault('reviews', []).append({'unit_id': unit_id, 'content_id': identity, 'round': skeleton['round'], 'status': 'open', 'manifest': str(manifest_path)})
        impl.write_json(record, unit)
        return {**active, **{k: skeleton[k] for k in PREFILLED}, 'rounds_used': skeleton['round'], 'rounds_remaining': max(0, 4 - skeleton['round'])}
    except Exception:
        shutil.rmtree(directory)
        raise



def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def validate_result(result, manifest):
    errors = []
    if not isinstance(result, dict):
        raise topics.TopicError('result: 必须是 JSON 对象')
    required = {*PREFILLED, 'status', 'reviewer', 'coverage', 'findings'}
    for key in sorted(required - result.keys()):
        errors.append(f'{key}: 缺少必填字段')
    for key in sorted(result.keys() - required):
        errors.append(f'{key}: 未声明字段')
    for key in PREFILLED:
        if key in result and (result[key] != manifest[key] or type(result[key]) is not type(manifest[key])):
            errors.append(f'{key}: 与当前冻结单元不一致')
    if result.get('status') not in ('pass', 'findings', 'blocked-by-design', 'inconclusive'):
        errors.append('status: 非法结论')
    reviewer = result.get('reviewer')
    if not isinstance(reviewer, dict):
        errors.append('reviewer: 必须是对象')
    else:
        for key in ('provenance', 'model'):
            if reviewer.get(key) != manifest['review_context'][key]:
                errors.append(f'reviewer.{key}: 与宿主声明的实际审查上下文不一致')
        if set(reviewer) != {'provenance', 'model'}:
            errors.append('reviewer: 必須且仅含 provenance、model')
    expected = set(manifest['coverage_targets'])
    downstream = {a['id'] for t in manifest['downstream_tickets'] for a in t['acceptance']}
    findings = result.get('findings')
    by_id = {}
    if not isinstance(findings, list):
        errors.append('findings: 必须是列表')
        findings = []
    for i, finding in enumerate(findings):
        prefix = f'findings[{i}]'
        if not isinstance(finding, dict):
            errors.append(f'{prefix}: 必须是对象')
            continue
        for key in ('id', 'summary', 'location'):
            if not nonempty(finding.get(key)):
                errors.append(f'{prefix}.{key}: 必须非空')
        identifier = finding.get('id')
        if nonempty(identifier):
            if identifier in by_id:
                errors.append(f'{prefix}.id: 重复')
            by_id[identifier] = finding
        severity = finding.get('severity')
        if severity not in ('blocking', 'advisory'):
            errors.append(f'{prefix}.severity: 非法严重度')
        if 'contradicts' in finding and not nonempty(finding['contradicts']):
            errors.append(f'{prefix}.contradicts: 必须是既有问题 id')
        if 'downstream_ticket' in finding:
            owner = next((t for t in manifest['downstream_tickets'] if t['id'] == finding['downstream_ticket']), None)
            if not owner:
                errors.append(f'{prefix}.downstream_ticket: 未引用真实下游 Ticket')
        if finding.get('view') not in ('correctness', 'impact', 'spec', 'spec-challenge', 'maintainability'):
            errors.append(f'{prefix}.view: 非法视角')
        anchor = finding.get('anchor')
        if 'anchor' in finding and not nonempty(anchor):
            errors.append(f'{prefix}.anchor: 提供时必须非空')
        evidence = finding.get('basis') or finding.get('failure_path')
        if not nonempty(evidence):
            errors.append(f'{prefix}.basis: 必须提供出错路径或被违反的规则')
        if severity == 'advisory':
            if finding.get('disposition') not in ('fix-in-batch', 'defer', 'decline'):
                errors.append(f'{prefix}.disposition: advisory 必须提供有效处置')
            if finding.get('disposition') == 'defer' and not nonempty(finding.get('owner')):
                errors.append(f'{prefix}.owner: defer 必须建议归属')
            if finding.get('disposition') == 'decline' and not nonempty(finding.get('reason')):
                errors.append(f'{prefix}.reason: decline 必须说明理由')
    if result.get('status') == 'pass' and any(f.get('severity') == 'blocking' for f in by_id.values()):
        errors.append('status: pass 不能包含 blocking findings')
    if result.get('status') == 'pass' and any(f.get('view') == 'spec-challenge' or f.get('disposition') == 'fix-in-batch' for f in by_id.values()):
        errors.append('status: Spec 挑战或待修复建议不能通过')
    coverage = result.get('coverage')
    seen = set()
    if not isinstance(coverage, list):
        errors.append('coverage: 必须是列表')
        coverage = []
    for i, item in enumerate(coverage):
        prefix = f'coverage[{i}]'
        if not isinstance(item, dict):
            errors.append(f'{prefix}: 必须是对象')
            continue
        target = item.get('target')
        if not isinstance(target, str) or target not in expected or target in seen:
            errors.append(f'{prefix}.target: 未声明或重复')
        if isinstance(target, str):
            seen.add(target)
        judgement = item.get('result')
        if judgement not in ('ok', 'finding', 'not-applicable'):
            errors.append(f'{prefix}.result: 非法判断')
        if judgement == 'not-applicable' and not nonempty(item.get('reason')):
            errors.append(f'{prefix}.reason: 不适用必须说明原因')
        if judgement == 'finding':
            finding = by_id.get(item.get('finding_id')) if isinstance(item.get('finding_id'), str) else None
            if not finding:
                errors.append(f'{prefix}.finding_id: 未引用该 target 的 finding')
        elif any(f.get('anchor') == target and f.get('severity') == 'blocking' for f in by_id.values()):
            errors.append(f'{prefix}.result: 存在 blocking，不能声明 ok 或不适用')
    for target in sorted(expected - seen):
        errors.append(f'coverage: 缺少 {target}')
    if errors:
        raise topics.TopicError('\n'.join(errors))
    return result


def current_manifest(repo, config, topic, path, unit):
    """Validate the same frozen inputs for submission and completion consumers."""
    active = unit.get('active_review')
    if not active:
        raise topics.TopicError('unit_id: 没有当前冻结单元；请先 implement review')
    manifest_path = Path(active['manifest'])
    if digest(manifest_path.read_bytes()) != active['manifest_sha256']:
        raise topics.TopicError('manifest: 冻结材料已变化，请重新 review')
    manifest = json.loads(manifest_path.read_text())
    for entry in manifest['inputs'] + [e for c in manifest['changes'] for e in (c['base'], c['current']) if e]:
        if digest(Path(entry['snapshot_path']).read_bytes()) != entry['sha256']:
            raise topics.TopicError('snapshot: 冻结材料已变化，请重新 review')
    if topics.content_id(repo) != manifest['content_id']:
        raise topics.TopicError('content_id: 当前内容已变化，请重新测试和 review')
    if impl.definition(repo, path) != active['definition']:
        raise topics.TopicError('acceptance: Ticket 或 Spec 定义已变化，请重新 review')
    if config != active['config']:
        raise topics.TopicError('rules: 配置已变化，请重新 review')
    rules, sources = impl.rule_material(repo, config, frontmatter(path), unit['execution_agent'])
    if rules != manifest['rule_map'] or digest('\n\n'.join(sources).encode()) != manifest['inputs'][0]['sha256']:
        raise topics.TopicError('rules: 适用规则已变化，请重新 review')
    decided = topics.topic_path(repo, topic) / 'decided' / f'decided-{topic}.md'
    if digest(decided.read_bytes() if decided.exists() else b'') != manifest['inputs'][3]['sha256']:
        raise topics.TopicError('decided: 已决事项已变化，请重新 review')
    if downstream(repo, topic, unit['ticket']) != manifest['downstream_tickets']:
        raise topics.TopicError('downstream_tickets: 下游验收已变化，请重新 review')
    return manifest


def require_pass(repo, config, topic, path, unit):
    manifest = current_manifest(repo, config, topic, path, unit)
    entry = unit.get('reviews', [{}])[-1]
    if entry.get('status') != 'pass' or entry.get('unit_id') != manifest['unit_id']:
        raise topics.TopicError('review: 当前冻结单元没有通过记录')
    accepted = topics.topic_path(repo, topic) / 'reviews' / f"accepted-{manifest['unit_id']}.json"
    if not accepted.is_file() or json.loads(accepted.read_text()) != entry:
        raise topics.TopicError('review: 登记记录不一致，请重新 review')
    validate_result(entry['result'], manifest)
    return entry


def submit_review(repo, ticket=None, topic=None, result_file=None):
    repo, config, topic, path, unit, record = impl.load_active(repo, ticket, topic)
    if frontmatter(path)['status'] != 'implementing':
        raise topics.TopicError('implement review 只接受 implementing')
    manifest = current_manifest(repo, config, topic, path, unit)
    try:
        submitted = json.loads(Path(result_file).read_text())
    except (OSError, ValueError) as exc:
        raise topics.TopicError(f'result: 无法读取有效 JSON：{exc}') from exc
    result = validate_result(submitted, manifest)
    review_loop.check_contradictions(unit, result)
    status = result['status']
    if any(f.get('view') == 'spec-challenge' for f in result['findings']):
        status = 'blocked-by-design'
    if status == 'findings' and not any(f['severity'] == 'blocking' or f.get('disposition') == 'fix-in-batch' for f in result['findings']):
        status = 'pass'
    repair = review_loop.repair_for(unit, manifest)
    entry = {'manifest': unit['active_review']['manifest'], 'repair': repair, 'unit_id': manifest['unit_id'], 'content_id': manifest['content_id'], 'round': manifest['round'],
             'status': status, 'reviewer': result['reviewer'], 'result': result}
    accepted = topics.topic_path(repo, topic) / 'reviews' / f"accepted-{manifest['unit_id']}.json"
    if accepted.exists():
        if json.loads(accepted.read_text()) != entry:
            raise topics.TopicError('unit_id: 当前单元已登记不同结果；请开启新 review')
    else:
        impl.write_json(accepted, entry)
    unit['reviews'][-1] = entry
    reason = review_loop.signals(unit, manifest, result, repair)
    if reason:
        review_loop.stop(unit, path, record, reason)
    else:
        impl.write_json(record, unit)
    return {**entry, 'rounds_used': manifest['round'], 'rounds_remaining': max(0, 4 - manifest['round'])}


def review(repo, ticket=None, topic=None, submit=None, reviewer_model=None, reviewer_session_id=None):
    if submit:
        return submit_review(repo, ticket, topic, submit)
    return open_review(repo, ticket, topic, reviewer_model, reviewer_session_id)
