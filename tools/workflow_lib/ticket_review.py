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
from . import topic_service as topics
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


# Ticket 09 will move this single runtime definition into the shared Skill resource.
REVIEW_LOOP_RULES = """# 审查循环规则

Ticket 审查覆盖 Ticket 基线以来全部内容改动；整分支审查用于多 Ticket standard Topic，覆盖 Topic 基线以来改动及全部 Ticket 验收。
standard 审查由宿主派出新上下文；只读冻结材料，不读实施者总结或简报计划。继承实际模型和思考档位，记录实际模型；更强模型由用户指定。self 来源如实记录，不能称 independent。
阻断问题必须违反明确验收或不变量，写明锚定对象、位置、出错路径和真实可达性；其余是 advisory。只有 blocking 进入修复循环，下游 owner 的未来能力记为 advisory。只有建议时通过。
第一轮穷尽，覆盖每项验收、探针、不变量，标注 ok、finding 或 not-applicable 并说明原因。复审只看本轮修复差异及影响，范围外新问题默认 advisory。
每个对象最多 4 轮，review 每次计一轮；修复最多 3 次。通过后内容变化即失效，重审占轮数，不重置。第4轮有阻断，或耗尽4轮且当前内容没有有效通过记录，进入 needs-user，拒绝第5轮。
blocked-by-design、inconclusive 均进入 needs-user。存在以下停止信号也进入 needs-user：
- 同一根因：连续两次复审的阻断问题落在紧挨的上次修复差异内。
- 同一处连续修改：相邻修复在同一文件的区间重叠，换算到中间快照行号。
- 前后矛盾：contradicts 指向之前问题。
- 体积膨胀：增加行加删除行超过第一轮的1.5倍。
needs-user 拒绝新审查；整分支 needs-user 时 topic complete 拒绝，status 显示原因。用户可接受现状、修订定义后 reopen 或放弃。
reopen 要求 Ticket 稳定定义或 Spec 改动，不计 status、claimed_by、勾选。Ticket 审查保留代码和基线，重读定义并清空测试及审查历史、轮数和停止信号；整分支审查从首次开启或最近 reopen 后定义改变才可重开。
修复只改正、删除、收窄。需要新增规则、场景或要求时 blocked-by-design。修复前同步同一事实在其他位置的写法，文档规则只定义一次。修复思路写 notes-file，不另写修复方案文档。
已决事项不可重开，有异议为 inconclusive。报告写已用轮数和剩余额度，不写趋势。
文档审查也受严重度、复审范围、修复约束、4轮上限及停止信号约束，runtime 不计数；扩大范围、补审、用户要求直到通过不重置。体积按第一轮字节数，多产物合计。Agent 在 reviews/review-log-<topic>.md 逐轮记产物、轮次、阻断数、建议数、修改范围、体积，无 Topic 在对话记录。达到上限或停止信号由用户裁决。
artifact-review-* 不接受 topic，不计轮数。
"""


def loop_rules():
    return REVIEW_LOOP_RULES


def open_review(repo, ticket=None, topic=None, reviewer_model=None, reviewer_session_id=None):
    repo, config, topic, path, unit, record = impl.load_active(repo, ticket, topic)
    value = frontmatter(path)
    if value['status'] != 'implementing':
        raise topics.TopicError('implement review 只接受 implementing')
    if not isinstance(reviewer_model, str) or not reviewer_model.strip():
        raise topics.TopicError('reviewer.model: 开启审查时请用 --reviewer-model 声明宿主实际模型')
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
        unit['active_review'] = active
        unit.setdefault('reviews', []).append({'unit_id': unit_id, 'content_id': identity, 'round': skeleton['round'], 'status': 'open'})
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
        for key in ('id', 'summary', 'anchor'):
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
            if not owner or finding.get('anchor') not in [a['id'] for a in owner['acceptance']]:
                errors.append(f'{prefix}.downstream_ticket: 未引用真实下游验收')
        anchor = finding.get('anchor')
        if not isinstance(anchor, str) or anchor not in expected | downstream:
            errors.append(f'{prefix}.anchor: 未锚定当前验收、探针、不变量或下游验收')
        if severity == 'blocking':
            if isinstance(anchor, str) and anchor in downstream or finding.get('downstream_ticket'):
                errors.append(f'{prefix}.severity: 下游问题只能是 advisory')
            for key in ('location', 'failure_path', 'reachability'):
                if not nonempty(finding.get(key)):
                    errors.append(f'{prefix}.{key}: blocking 必须提供非空证据')
    if result.get('status') == 'pass' and any(f.get('severity') == 'blocking' for f in by_id.values()):
        errors.append('status: pass 不能包含 blocking findings')
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
            if not finding or finding.get('anchor') != target:
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
    status = result['status']
    if status == 'findings' and not any(f['severity'] == 'blocking' for f in result['findings']):
        status = 'pass'
    entry = {'unit_id': manifest['unit_id'], 'content_id': manifest['content_id'], 'round': manifest['round'],
             'status': status, 'reviewer': result['reviewer'], 'result': result}
    accepted = topics.topic_path(repo, topic) / 'reviews' / f"accepted-{manifest['unit_id']}.json"
    if accepted.exists():
        if json.loads(accepted.read_text()) != entry:
            raise topics.TopicError('unit_id: 当前单元已登记不同结果；请开启新 review')
    else:
        impl.write_json(accepted, entry)
    unit['reviews'][-1] = entry
    impl.write_json(record, unit)
    return {**entry, 'rounds_used': manifest['round'], 'rounds_remaining': max(0, 4 - manifest['round'])}


def review(repo, ticket=None, topic=None, submit=None, reviewer_model=None, reviewer_session_id=None):
    if submit:
        return submit_review(repo, ticket, topic, submit)
    return open_review(repo, ticket, topic, reviewer_model, reviewer_session_id)
