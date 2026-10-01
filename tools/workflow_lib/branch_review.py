"""Whole-branch evidence and review, independently bounded from Ticket units."""
from __future__ import annotations

import json
from pathlib import Path
import re
import shlex
import shutil
import uuid

from . import topic_service as topics, ticket_implementation as impl, ticket_review as reviews, review_loop
from .rules import EXECUTION_AGENTS


def load(repo, topic=None, all_complete=True):
    repo = topics.safe_repo(repo)
    config = topics.read_config(repo)
    topic = topics.select_topic(repo, topic)
    root = topics.topic_path(repo, topic)
    if topics.topic_path(repo, topic, True).exists():
        raise topics.TopicError('Topic 已归档，只读')
    if not topics.topic_path(repo, topic).is_dir():
        raise topics.TopicError('Topic 不存在')
    state = topics.state(root)
    tickets = impl.records(repo, topic)
    if state.get('level') != 'standard' or len(tickets) < 2:
        raise topics.TopicError('topic review 只用于多 Ticket standard')
    if all_complete and any(v['status'] != 'complete' for _, v in tickets.values()):
        raise topics.TopicError('整分支审查要求所有 Ticket complete')
    record = root / 'branch-review.json'
    unit = json.loads(record.read_text()) if record.exists() else dict(
        topic=topic, baseline=state['baseline'], started_at=topics.now(), reviews=[], status='implementing')
    return repo, config, topic, root, tickets, unit, record


def definition(repo, tickets):
    return {key: impl.definition(repo, path) for key, (path, _) in tickets.items()}


def tests_record(repo, topic):
    return topics.topic_path(repo, topic) / 'topic-tests.json'


def tests_passed(repo, config, topic):
    record = tests_record(repo, topic)
    commands = [shlex.split(c) for c in topics.full_tests(config)]
    return bool(commands) and record.exists() and impl.tests_passed(repo, json.loads(record.read_text()), commands)


def test(repo, topic=None):
    repo = topics.safe_repo(repo)
    config = topics.read_config(repo)
    topic = topics.select_topic(repo, topic)
    if topics.topic_path(repo, topic, True).exists():
        raise topics.TopicError('Topic 已归档，只读')
    if not topics.topic_path(repo, topic).is_dir():
        raise topics.TopicError('Topic 不存在')
    commands = [shlex.split(c) for c in topics.full_tests(config)]
    if not commands:
        raise topics.TopicError('topic test 需要非空全量测试集合')
    record = tests_record(repo, topic)
    unit = json.loads(record.read_text()) if record.exists() else {'tests': []}
    output = impl.run_test_batch(repo, unit, record, commands)
    return dict(topic=topic, tests=output, tests_passed=tests_passed(repo, config, topic))


def materials(repo, config, topic, tickets):
    rules, sources, specs, acceptance, probes, scope = [], [], [], [], [], []
    for identifier, (path, value) in tickets.items():
        stored = impl.record_path(repo, topic, identifier)
        if stored.is_file():
            agent = json.loads(stored.read_text())['execution_agent']
        else:
            # Migration preserves completed v1 journals without creating v2
            # implementation records. Read their binding, not today's default.
            history = (topics.topic_path(repo, topic) / 'runs').glob(f'run-{identifier}-spec-r*.json')
            agents = {json.loads(p.read_text()).get('context', {}).get('ticket', {}).get('execution_agent')
                      for p in history}
            agents.discard(None)
            if not agents:
                agents = {value.get('execution_agent')}
            if len(agents) != 1 or not agents <= EXECUTION_AGENTS:
                raise topics.TopicError(f'{identifier} 历史执行 Agent 无法唯一确定；请核对旧实施记录')
            agent = agents.pop()
        mapped, text = impl.rule_material(repo, config, value, agent)
        rules.append({'ticket': identifier, 'rules': mapped})
        sources.extend(text)
        specs.append((repo / value['spec_ref']).read_text())
        acceptance.extend(reviews.targets(path))
        probes.extend(value['review_probes'])
        scope.extend(value['rule_scope'])
    return dict(rule_map=rules, rules='\n\n'.join(sources), specs='\n\n'.join(specs),
                acceptance=acceptance, probes=list(dict.fromkeys(probes)), scope=scope)


def current_manifest(repo, config, topic, root, tickets, unit):
    active = unit.get('active_review')
    if not active:
        raise topics.TopicError('review: 缺少整分支审查记录')
    path = Path(active['manifest'])
    if reviews.digest(path.read_bytes()) != active['manifest_sha256']:
        raise topics.TopicError('manifest: 整分支冻结材料已变化')
    manifest = json.loads(path.read_text())
    for entry in manifest['inputs'] + [e for c in manifest['changes'] for e in (c['base'], c['current']) if e]:
        if reviews.digest(Path(entry['snapshot_path']).read_bytes()) != entry['sha256']:
            raise topics.TopicError('snapshot: 整分支冻结材料已变化')
    if topics.content_id(repo) != manifest['content_id']:
        raise topics.TopicError('content_id: 内容已变化，请 topic test/review')
    if definition(repo, tickets) != active['definition'] or config != active['config']:
        raise topics.TopicError('definition: Ticket/Spec/配置已变化，请重新审查或 reopen')
    material = materials(repo, config, topic, tickets)
    decided = root / 'decided' / f'decided-{topic}.md'
    if (material['rule_map'] != manifest['rule_map']
            or reviews.digest(material['rules'].encode()) != manifest['inputs'][0]['sha256']
            or reviews.digest(decided.read_bytes() if decided.exists() else b'') != manifest['inputs'][3]['sha256']):
        raise topics.TopicError('rules: 规则或已决事项已变化，请重新审查')
    return manifest


def require_pass(repo, config, topic, root, tickets, unit):
    if unit['status'] == 'needs-user':
        raise topics.TopicError('整分支 needs-user：' + unit['stop_reason'])
    manifest = current_manifest(repo, config, topic, root, tickets, unit)
    entry = unit['reviews'][-1]
    accepted = root / 'reviews' / f"accepted-{manifest['unit_id']}.json"
    if entry.get('status') != 'pass' or entry['unit_id'] != manifest['unit_id'] or not accepted.exists() or json.loads(accepted.read_text()) != entry:
        raise topics.TopicError('review: 当前整分支审查未通过')
    reviews.validate_result(entry['result'], manifest)
    return entry


def review(repo, topic=None, submit=None, reviewer_model=None, reviewer_session_id=None):
    repo, config, topic, root, tickets, unit, record = load(repo, topic)
    if unit['status'] == 'needs-user':
        raise topics.TopicError('整分支 needs-user：' + unit['stop_reason'])
    if not submit:
        if len(unit['reviews']) >= 4:
            try:
                require_pass(repo, config, topic, root, tickets, unit)
            except (topics.TopicError, OSError, ValueError):
                review_loop.stop(unit, None, record, '轮数耗尽：4 轮后没有当前有效通过记录')
            raise topics.TopicError('轮数上限为 4；拒绝第 5 轮')
    if not tests_passed(repo, config, topic):
        raise topics.TopicError('test: 整分支审查需要当前全量测试通过记录')
    if submit:
        manifest = current_manifest(repo, config, topic, root, tickets, unit)
        result = reviews.validate_result(json.loads(Path(submit).read_text()), manifest)
        review_loop.check_contradictions(unit, result)
        status = result['status']
        if status == 'findings' and not any(f['severity']=='blocking' for f in result['findings']):
            status = 'pass'
        repair = review_loop.repair_for(unit, manifest)
        entry = dict(manifest=unit['active_review']['manifest'], repair=repair, unit_id=manifest['unit_id'],
                     content_id=manifest['content_id'], round=manifest['round'], status=status,
                     reviewer=result['reviewer'], result=result)
        accepted = root / 'reviews' / f"accepted-{manifest['unit_id']}.json"
        if accepted.exists() and json.loads(accepted.read_text()) != entry:
            raise topics.TopicError('unit_id: 当前单元已登记不同结果')
        impl.write_json(accepted, entry)
        unit['reviews'][-1] = entry
        reason = review_loop.signals(unit, manifest, result, repair)
        if reason:
            review_loop.stop(unit, None, record, reason)
        else:
            impl.write_json(record, unit)
        return {**entry, 'rounds_used': manifest['round'], 'rounds_remaining': 4-manifest['round']}
    if not isinstance(reviewer_model, str) or not reviewer_model.strip():
        raise topics.TopicError('reviewer.model: 请声明实际宿主模型')
    identity = topics.content_id(repo)
    frozen_definition = definition(repo, tickets)
    material = materials(repo, config, topic, tickets)
    session = unit.setdefault('implementation_session_id', uuid.uuid4().hex)
    context = dict(provenance='independent' if reviewer_session_id and reviewer_session_id!=session else 'self',
                   model=reviewer_model, session_id=reviewer_session_id or session)
    unit_id = uuid.uuid4().hex
    directory = root / 'reviews' / f'branch-{unit_id}'
    directory.mkdir(parents=True)
    try:
        base, current = reviews.baseline_files(repo, unit['baseline']), reviews.current_files(repo)
        changes = []
        for index, name in enumerate(sorted(base.keys() | current.keys())):
            if base.get(name) == current.get(name): continue
            item = dict(path=name, base=None, current=None)
            for side, files in [('base',base),('current',current)]:
                if name in files:
                    mode, data = files[name]
                    item[side] = reviews.frozen_file(directory,f'{index:04d}-{side}',data,mode)
            changes.append(item)
        decided = root / 'decided' / f'decided-{topic}.md'
        inputs = [reviews.frozen_file(directory,'rules.md',material['rules'].encode()),
                  reviews.frozen_file(directory,'specs.md',material['specs'].encode()),
                  reviews.frozen_file(directory,'review-loop-rules.md',reviews.loop_rules().encode()),
                  reviews.frozen_file(directory,'decided.md',decided.read_bytes() if decided.exists() else b'')]
        skeleton = dict(unit_id=unit_id,content_id=identity,round=len(unit['reviews'])+1,
                        acceptance=material['acceptance'],probes=material['probes'],downstream_tickets=[],
                        status=None,reviewer=dict(provenance=None,model=None),coverage=[],findings=[])
        manifest = {**{k:skeleton[k] for k in reviews.PREFILLED}, 'baseline':unit['baseline'], 'topic':topic,
                    'changes':changes,'inputs':inputs,'rule_map':material['rule_map'],'review_context':context,
                    'coverage_targets':[a['id'] for a in material['acceptance']] + material['probes']
                        + sorted(set(re.findall(r'\*\*(I-(?:[A-Z]+)?[0-9]+)\*\*',material['specs'])))}
        path = directory / 'manifest.json'
        impl.write_json(path,manifest)
        path.chmod(0o444)
        result_file = root / 'reviews' / f'result-{unit_id}.json'
        impl.write_json(result_file,skeleton)
        if (topics.content_id(repo)!=identity or definition(repo,tickets)!=frozen_definition
                or topics.read_config(repo)!=config):
            raise topics.TopicError('冻结期间内容或定义变化，请重新 review')
        active = dict(manifest=str(path),manifest_sha256=reviews.digest(path.read_bytes()),snapshot_dir=str(directory),
                      result_file=str(result_file),definition=frozen_definition,config=config)
        unit.setdefault('definition',frozen_definition)
        unit.setdefault('first_review_volume',review_loop.volume(manifest))
        unit['active_review'] = active
        unit['reviews'].append(dict(unit_id=unit_id,content_id=identity,round=skeleton['round'],status='open',manifest=str(path)))
        impl.write_json(record,unit)
        return {**active,**{k:skeleton[k] for k in reviews.PREFILLED},'rounds_used':skeleton['round'],'rounds_remaining':4-skeleton['round']}
    except Exception:
        shutil.rmtree(directory)
        raise


def resolve(repo, topic=None, accept=False, reason=''):
    if not reason.strip(): raise topics.TopicError('reason: 裁决理由不能为空')
    repo, config, topic, root, tickets, unit, record = load(repo,topic)
    if accept:
        if unit['status']!='needs-user': raise topics.TopicError('branch accept 只接受 needs-user')
        if not tests_passed(repo,config,topic): raise topics.TopicError('test: 接受必须有当前全量测试通过记录')
        known = [f for f in unit['reviews'][-1].get('result',{}).get('findings',[]) if f['severity']=='blocking']
        return topics.complete(repo,topic,accepted_reason=reason,known_issues=known)
    if 'definition' not in unit or definition(repo,tickets)==unit['definition']:
        raise topics.TopicError('reopen 要求首次审查或最近 reopen 后 Ticket/Spec 稳定定义变化')
    for path, _ in tickets.values(): impl.validate(repo,path,config)
    materials(repo,config,topic,tickets)
    unit.update(definition=definition(repo,tickets),reviews=[],status='implementing')
    for key in ('active_review','stop_reason','first_review_volume'): unit.pop(key,None)
    unit.setdefault('decisions',[]).append(dict(action='reopen',reason=reason,at=topics.now()))
    impl.write_json(record,unit)
    return dict(topic=topic,status='implementing',rounds_used=0,reason=reason)
