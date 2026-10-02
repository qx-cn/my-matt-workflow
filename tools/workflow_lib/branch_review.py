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


def load(repo, topic=None, all_complete=True, batch=False):
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
    from . import batches
    if batch:
        value, unit = batches.active(repo, topic)
        subset = {t:tickets[t] for t in unit['tickets']}
        if all_complete and any(v['status'] != 'complete' for _,v in subset.values()):
            raise topics.TopicError('批次审查要求全部 Ticket 已提交')
        if unit['status'] in ('closed','needs-user'):
            raise topics.TopicError('当前批次不能继续审查；请 batch status')
        unit['status'] = 'reviewing'
        if unit['id'] == value['batches'][-1]['id']:
            unit['topic_changes'] = topics.git(repo,'diff','--name-only',state['baseline'],'HEAD').stdout.decode().splitlines()
        return repo, config, topic, root, subset, unit, root/'batches'/f"{unit['id']}.json"
    if batches.enabled(repo, topic):
        value, last = batches.active(repo, topic)
        if last['id'] != value['batches'][-1]['id']:
            raise topics.TopicError('整分支审查只能在最后一个批次收口前执行')
    if state.get('level') != 'standard' or len(tickets) < 2:
        raise topics.TopicError('topic review 只用于多 Ticket standard')
    if all_complete and any(v['status'] != 'complete' for _, v in tickets.values()):
        raise topics.TopicError('整分支审查要求所有 Ticket complete')
    record = root / 'branch-review.json'
    unit = json.loads(record.read_text()) if record.exists() else dict(
        topic=topic, baseline=state['baseline'], started_at=topics.now(), reviews=[], status='implementing')
    if unit.get('status')=='needs-user' and review_loop.recover_geometry(unit,
            lambda candidate:require_pass(repo,config,topic,root,tickets,candidate)):
        impl.write_json(record,unit)
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
    ticket_documents, impacts, self_findings = [], [], []
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
        ticket_documents.append(path.read_text())
        history = json.loads(stored.read_text()) if stored.is_file() else {}
        self_text = history.get('self_review',{}).get('text','')
        from .batches import pending_self_findings
        self_findings.extend(dict(ticket=identifier,target=f"self:{identifier}:{f['id']}",finding=f,
            observed_content_id=observation.get('content_id')) for f,observation in pending_self_findings(history).values() if f.get('disposition')=='fix-in-batch')
        impacts.append(f"### {identifier}（实施者声明，待核实）\n" + impl.section_text(self_text, '影响面'))
        mapped, text = impl.rule_material(repo, config, value, agent, topics.git(repo,'diff','--name-only', topics.state(topics.topic_path(repo,topic))['baseline']).stdout.decode().splitlines())
        rules.append({'ticket': identifier, 'rules': mapped})
        sources.extend(text)
        specs.append((repo / value['spec_ref']).read_text())
        acceptance.extend(reviews.targets(path))
        probes.extend(value['review_probes'])
        scope.extend(value.get('rule_scope', []))
    return dict(rule_map=rules, rules='\n\n'.join(sources), specs='\n\n'.join(specs),
                acceptance=acceptance, probes=list(dict.fromkeys(probes)), scope=scope,self_findings=self_findings,ticket_documents='\n\n'.join(ticket_documents),impacts='\n\n'.join(impacts))


def current_manifest(repo, config, topic, root, tickets, unit):
    active = unit.get('active_review')
    if not active:
        raise topics.TopicError('review: 缺少整分支审查记录')
    from .evidence import frozen_manifest
    manifest=frozen_manifest(active)
    if manifest.get('head') and topics.git(repo,'rev-parse','HEAD').stdout.decode().strip() != manifest['head']:
        raise topics.TopicError('HEAD 已变化；请对变化部分复审')
    if topics.content_id(repo) != manifest['content_id']:
        raise topics.TopicError('content_id: 内容已变化，请 topic test/review')
    if definition(repo, tickets) != active['definition'] or config != active['config']:
        raise topics.TopicError('definition: Ticket/Spec/配置已变化，请重新审查或 reopen')
    material = materials(repo, config, topic, tickets)
    if material['self_findings']!=manifest.get('self_findings',[]):
        raise topics.TopicError('self-review: 批次待处置发现已变化，请重新审查')
    decided = root / 'decided' / f'decided-{topic}.md'
    if (material['rule_map'] != manifest['rule_map']
            or reviews.digest(material['rules'].encode()) != manifest['inputs'][0]['sha256']
            or reviews.digest(decided.read_bytes() if decided.exists() else b'') != manifest['inputs'][3]['sha256']):
        raise topics.TopicError('rules: 规则或已决事项已变化，请重新审查')
    return manifest


def acceptance_current(repo,unit):
    accepted=unit.get('acceptance',{})
    return accepted.get('head')==topics.git(repo,'rev-parse','HEAD').stdout.decode().strip() and accepted.get('content_id')==topics.content_id(repo)


def require_pass(repo, config, topic, root, tickets, unit):
    accepted = unit.get('acceptance',{})
    if acceptance_current(repo,unit):
        return dict(status='accepted',reason=accepted['reason'])
    if unit['status'] == 'needs-user':
        raise topics.TopicError('审查需要用户裁决：' + unit['stop_reason'])
    manifest = current_manifest(repo, config, topic, root, tickets, unit)
    entry = unit['reviews'][-1]
    from . import evidence
    accepted = root / 'reviews' / f"accepted-{manifest['unit_id']}.json"
    if entry.get('status') != 'pass' or entry['unit_id'] != manifest['unit_id'] or not evidence.accepted_matches(accepted,entry):
        raise topics.TopicError('review: 当前整分支审查未通过')
    reviews.validate_result(entry['result'], manifest)
    return entry


def review(repo, topic=None, submit=None, reviewer_model=None, reviewer_session_id=None, batch=False, initiated_by=None, reason=None):
    repo, config, topic, root, tickets, unit, record = load(repo, topic, batch=batch)
    from . import batches
    if not batch and batches.enabled(repo,topic) and not submit:
        if initiated_by not in ("user","agent") or not reason or not reason.strip():
            raise topics.TopicError("整分支审查必须记录发起者 user/agent 和理由")
        unit.update(initiated_by=initiated_by,reason=reason)
    if unit['status'] == 'needs-user':
        raise topics.TopicError('整分支 needs-user：' + unit['stop_reason'])
    if not submit:
        if len(unit['reviews']) >= 4:
            try:
                require_pass(repo, config, topic, root, tickets, unit)
            except (topics.TopicError, OSError, ValueError):
                review_loop.stop(unit, None, record, '轮数耗尽：4 轮后没有当前有效通过记录')
            raise topics.TopicError('轮数上限为 4；拒绝第 5 轮')
    if batches.enabled(repo,topic):
        _, current_batch = batches.active(repo,topic)
        passed = batches.tests_passed(repo,config,topic,current_batch)
    else:
        passed = tests_passed(repo,config,topic)
    if not passed:
        raise topics.TopicError('test: 审查需要当前全量测试相对基线无新增失败记录')
    if submit:
        manifest = current_manifest(repo, config, topic, root, tickets, unit)
        result = reviews.validate_result(json.loads(Path(submit).read_text()), manifest)
        review_loop.check_contradictions(unit, result)
        status = result['status']
        if any(f.get('view') == 'spec-challenge' for f in result['findings']):
            status = 'blocked-by-design'
        if status == 'findings' and not any(f['severity']=='blocking' or f.get('disposition') == 'fix-in-batch' for f in result['findings']):
            status = 'pass'
        repair = review_loop.repair_for(unit, manifest)
        entry = dict(manifest=unit['active_review']['manifest'], repair=repair, unit_id=manifest['unit_id'],
                     content_id=manifest['content_id'], round=manifest['round'], status=status,
                     reviewer=result['reviewer'], result=result,review_context=manifest['review_context'],review_series=unit['reviews'][-1].get('review_series',manifest['unit_id']))
        from . import evidence
        accepted = root / 'reviews' / f"accepted-{manifest['unit_id']}.json"
        if accepted.exists() and json.loads(accepted.read_text()) != entry:
            raise topics.TopicError('unit_id: 当前单元已登记不同结果')
        impl.write_json(accepted, entry)
        unit['reviews'][-1] = entry
        reason = review_loop.signals(unit, manifest, result, repair)
        if reason:
            if not batch and batches.enabled(repo,topic):
                plan, last = batches.active(repo,topic)
                last.update(status='needs-user',stop_reason=reason)
                last.setdefault('definition',{t:unit['definition'][t] for t in last['tickets']})
                batches.save(repo,topic,plan)
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
        inputs.extend([reviews.frozen_file(directory,'tickets.md',material['ticket_documents'].encode()),
                       reviews.frozen_file(directory,'impact-declarations.md',material['impacts'].encode())])
        repository = reviews.freeze_repository(directory,current)
        inputs.extend(repository)
        inputs.append(reviews.frozen_file(directory,'self-findings.json',json.dumps(material['self_findings'],ensure_ascii=False).encode()))
        manifest = {**{k:skeleton[k] for k in reviews.PREFILLED},'repository':repository, 'baseline':unit['baseline'], 'topic':topic,
                    'self_findings':material['self_findings'],'head':topics.git(repo,'rev-parse','HEAD').stdout.decode().strip(),'topic_changes':unit.get('topic_changes',[]),'repository_files': sorted(current),'changes':changes,'inputs':inputs,'rule_map':material['rule_map'],'review_context':context,
                    'coverage_targets':[a['id'] for a in material['acceptance']] + material['probes'] + [f['target'] for f in material['self_findings']]
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
        unit['reviews'].append(dict(unit_id=unit_id,content_id=identity,round=skeleton['round'],status='open',manifest=str(path),review_context=context,review_series=unit['reviews'][0].get('review_series',unit_id) if unit['reviews'] else unit_id))
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
        from . import batches
        if batches.enabled(repo,topic):
            return batches.close(repo,topic,accept=True,reason=reason)
        if not tests_passed(repo,config,topic): raise topics.TopicError('test: 接受必须有当前全量测试通过记录')
        known = [f for f in unit['reviews'][-1].get('result',{}).get('findings',[]) if f['severity']=='blocking' or f.get('view') == 'spec-challenge']
        return topics.complete(repo,topic,accepted_reason=reason,known_issues=known)
    if 'definition' not in unit or definition(repo,tickets)==unit['definition']:
        raise topics.TopicError('reopen 要求首次审查或最近 reopen 后 Ticket/Spec 稳定定义变化')
    for path, _ in tickets.values(): impl.validate(repo,path,config)
    materials(repo,config,topic,tickets)
    from .quality_metrics import preserve_history
    preserve_history(unit)
    unit.update(definition=definition(repo,tickets),reviews=[],status='implementing')
    for key in ('active_review','stop_reason','first_review_volume'): unit.pop(key,None)
    from . import batches
    if batches.enabled(repo,topic):
        plan,current=batches.active(repo,topic)
        if current['status']=='needs-user':
            subset={t:tickets[t] for t in current['tickets']}
            changed=definition(repo,subset)
            if current.get('definition') and changed != current['definition']:
                from .quality_metrics import preserve_history
                preserve_history(current)
                current.update(definition=changed,reviews=[],status='reviewing')
                for key in ('active_review','first_review_volume','stop_reason','acceptance'):current.pop(key,None)
            elif not current.get('definition'):
                current['status']='open'
            current.setdefault('decisions',[]).append(dict(action='branch-reopen',reason=reason,at=topics.now()))
            batches.save(repo,topic,plan)
    unit.setdefault('decisions',[]).append(dict(action='reopen',reason=reason,at=topics.now()))
    impl.write_json(record,unit)
    return dict(topic=topic,status='implementing',rounds_used=0,reason=reason)
