"""Serial batches, enhanced self-review and baseline-relative full tests."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import shlex
import uuid
from . import topic_service as topics, ticket_implementation as impl

SELF_SECTIONS = ('验收对照','现状核实','影响面','对抗检查','简洁与约定','已知缺口')


def enabled(repo, topic):
    return (topics.topic_path(repo, topic) / 'batches.json').exists()


def read(repo, topic):
    root = topics.topic_path(repo, topic)
    value = json.loads((root / 'batches.json').read_text())
    value['batches'] = [json.loads((root/'batches'/f"{b['id']}.json").read_text()) if (root/'batches'/f"{b['id']}.json").exists() else b for b in value['batches']]
    return value


def save(repo, topic, plan):
    root = topics.topic_path(repo, topic)
    for b in plan['batches']:
        if b.get('baseline'):impl.write_json(root/'batches'/f"{b['id']}.json", b)
    impl.write_json(root / 'batches.json', plan)


def plan(repo, topic, groups=None, reason='默认整个 Topic 一个批次'):
    repo = topics.safe_repo(repo)
    topics.read_config(repo)
    root = topics.topic_path(repo, topic)
    if topics.topic_path(repo, topic, True).exists():
        raise topics.TopicError('Topic 已归档；不能重新划分批次')
    if topics.state(root).get('level') == 'quick':
        raise topics.TopicError('quick 不使用批次、Spec 或 Ticket')
    tickets = impl.records(repo, topic)
    if not tickets:
        raise topics.TopicError('批次划分需要 Ticket')
    prior = read(repo,topic) if enabled(repo,topic) else None
    started = prior and any(b.get('baseline') for b in prior['batches'])
    ordered = sorted(tickets, key=lambda k: (int(tickets[k][1]['sequence']), k))
    if groups is None:
        previous=[b['tickets'] for b in prior['batches']] if started else []
        owned={t for g in previous for t in g}
        remaining=[t for t in ordered if t not in owned]
        groups=previous + ([remaining] if remaining else [])

    if not isinstance(groups,list) or any(not isinstance(g,list) or not g or any(not isinstance(t,str) for t in g) for g in groups):
        raise topics.TopicError('groups 必须为非空 Ticket 列表的数组')
    if started and groups[:len(prior['batches'])] != [b['tickets'] for b in prior['batches']]:
        raise topics.TopicError('批次已开始：不能改写历史划分，只能追加批次')
    flat = [t for g in groups for t in g]
    if not groups or any(not isinstance(g, list) or not g for g in groups) or len(flat) != len(set(flat)) or set(flat) != set(tickets):
        raise topics.TopicError('groups 必须恰好覆盖全部 Ticket，不能重复或为空')
    positions = {t:i for i,t in enumerate(flat)}
    for identifier in flat:
        for dep in tickets[identifier][1]['blocked_by']:
            if dep not in positions or positions[dep] >= positions[identifier]:
                raise topics.TopicError(f'{identifier}: 批次顺序违反依赖 {dep}')
    if not reason.strip():
        raise topics.TopicError('批次划分理由不能为空')
    result = dict(topic=topic, reason=reason, implementation_session_id=uuid.uuid4().hex,
                  batches=[dict(id=f'{i+1:02d}',tickets=g,status='pending',reviews=[]) for i,g in enumerate(groups)])
    if started:
        result['implementation_session_id']=prior['implementation_session_id']
        result['batches'][:len(prior['batches'])]=prior['batches']
    save(repo, topic, result)
    return result


def active(repo, topic, identifier=None):
    value = read(repo, topic)
    candidates = [b for b in value['batches'] if b['status'] != 'closed']
    batch = next((b for b in value['batches'] if b['id']==identifier), None) if identifier else (candidates[0] if candidates else None)
    if not batch:
        raise topics.TopicError('没有待收口批次')
    if batch.get('status')=='needs-user':
        from . import branch_review, review_loop
        tickets=impl.records(repo,topic)
        if review_loop.recover_geometry(batch,lambda candidate:branch_review.require_pass(
                repo,topics.read_config(repo),topic,topics.topic_path(repo,topic),
                {t:tickets[t] for t in batch['tickets']},candidate)):
            save(repo,topic,value)
    return value, batch


def before_start(repo, topic, ticket):
    if not enabled(repo, topic):
        # Existing implementation histories keep their legacy protocol.
        if any((topics.topic_path(repo, topic)/'implementations').glob('*.json')):
            return None
        plan(repo, topic)
    current=read(repo,topic)
    if all(b['status']=='closed' for b in current['batches']) and ticket not in {t for b in current['batches'] for t in b['tickets']}:
        plan(repo,topic,reason='已确认新 Ticket，追加批次；历史批次保持不变')
    value, batch = active(repo, topic)
    if ticket not in batch['tickets'] or batch['status'] not in ('pending','open'):
        raise topics.TopicError('请先收口当前批次，不能越序实施')
    if not batch.get('baseline'):
        batch.update(baseline=topics.git(repo,'rev-parse','HEAD').stdout.decode().strip(),status='open',topic=topic,implementation_session_id=value['implementation_session_id'])
        save(repo, topic, value)
    baseline_file = topics.topic_path(repo, topic)/'test-baseline.json'
    if not baseline_file.exists():
        baseline = run_full(repo, topics.read_config(repo))
        baseline['baseline'] = batch['baseline']
        impl.write_json(baseline_file, baseline)
    return batch['id']


def pending_self_findings(unit):
    """Missing old fields never silently dispose of an earlier discovery."""
    history=unit.get('self_reviews',[])
    latest=unit.get('self_review')
    if latest and (not history or history[-1]!=latest):history=[*history,latest]
    pending={}
    for observation in history:
        for resolution in observation.get('resolutions',[]):pending.pop(resolution['id'],None)
        for finding in observation.get('findings',[]):
            prior=pending.get(finding['id'])
            if prior and (prior[0].get('severity')=='blocking' or prior[0].get('view')=='spec-challenge'):
                continue  # A later missing/downgraded field is not a resolution.
            if finding.get('severity')=='blocking' or finding.get('view')=='spec-challenge' or finding.get('disposition')=='fix-in-batch':
                pending[finding['id']]=(finding,observation)
            else:pending.pop(finding['id'],None)
    return pending


def self_observations(repo, topic, identifiers):
    """Carry discoveries into the active batch without rewriting completed Tickets."""
    resolutions = []
    if enabled(repo, topic):
        resolutions = [r for b in read(repo, topic)['batches']
                       for r in b.get('self_finding_resolutions', [])]
    result = []
    for identifier in identifiers:
        record = impl.record_path(repo, topic, identifier)
        if not record.is_file():continue
        history = json.loads(record.read_text())
        for finding, observation in pending_self_findings(history).values():
            if not enabled(repo,topic) and finding.get('disposition')!='fix-in-batch':continue
            if history.get('outcome') == 'accepted' and finding in history.get('known_issues', []):continue
            if any(r['ticket'] == identifier and r['finding'] == finding['id'] for r in resolutions):continue
            result.append(dict(ticket=identifier, target=f"self:{identifier}:{finding['id']}",
                finding=finding, observed_content_id=observation.get('content_id'),
                observed_definition=observation.get('definition', history.get('definition'))))
    return result


def named(reason, target):
    return bool(re.search(r'(?<![\w-])'+re.escape(target)+r'(?![\w-])', reason))


def require_self_repairs(repo, topic, unit, observations, allow_challenges=False):
    """A review pass cannot substitute for an actual recorded content repair."""
    if not enabled(repo,topic):return
    identity = topics.content_id(repo)
    pending={o['target'] for o in self_observations(repo,topic,{o['ticket'] for o in observations})}
    for observation in observations:
        if observation['target'] not in pending:continue
        finding = observation['finding']
        if finding.get('view') == 'spec-challenge':
            if allow_challenges:continue
            raise topics.TopicError('self-review: 需要点名裁决 '+observation['target']+'；请 batch reopen 或 batch accept')
        if finding.get('severity') != 'blocking':continue
        repairs = [r for b in read(repo,topic)['batches'] for r in b.get('self_finding_repairs',[])] if enabled(repo,topic) else unit.get('self_finding_repairs', [])
        if (observation.get('observed_content_id') == identity or not any(
                observation['target'] in r['targets'] and r['content_id'] == identity
                and topics.git(repo,'merge-base','--is-ancestor',r['head'],'HEAD',check=False).returncode == 0
                for r in repairs)):
            raise topics.TopicError('self-review: 需要实际 batch repair 和当前测试/审查证据 '+observation['target'])


def require_blocking_review(repo, topic, batch, observations):
    blockers=[o for o in observations if o['finding'].get('severity')=='blocking'
              and o['finding'].get('view')!='spec-challenge']
    if not blockers:return
    from . import branch_review, evidence
    root=topics.topic_path(repo,topic)
    tickets=impl.records(repo,topic)
    manifest=branch_review.current_manifest(repo,topics.read_config(repo),topic,root,
        {t:tickets[t] for t in batch['tickets']},batch)
    entry=batch['reviews'][-1]
    if not evidence.accepted_matches(root/'reviews'/f"accepted-{manifest['unit_id']}.json",entry):
        raise topics.TopicError('self-review: 接受挑战前必须审查实际 blocking 修复')
    if any(f.get('view')!='spec-challenge' and (f.get('severity')=='blocking' or f.get('disposition')=='fix-in-batch')
           for f in entry.get('result',{}).get('findings',[])):
        raise topics.TopicError('self-review: 当前审查仍有未修复的 correctness/待批次修复发现')
    coverage={c['target']:c['result'] for c in entry.get('result',{}).get('coverage',[])}
    if any(coverage.get(o['target'])!='ok' for o in blockers):
        raise topics.TopicError('self-review: blocking 修复尚未通过当前审查')


def self_review(repo, ticket=None, topic=None, notes_file=None, findings_file=None, no_findings=False):
    repo, config, topic, path, unit, record = impl.load_active(repo,ticket,topic)
    text = Path(notes_file).read_text() if notes_file else ''
    sections = list(topics.summary_headings(text))
    titles = {t for t,_ in sections}
    missing = set(SELF_SECTIONS)-titles
    if missing:
        raise topics.TopicError('self-review 缺少章节：'+', '.join(sorted(missing)))
    lines=text.splitlines()
    for title,index in sections:
        if title in SELF_SECTIONS:
            end=next((j for _,j in sections if j>index),len(lines))
            if not '\n'.join(lines[index+1:end]).strip():
                raise topics.TopicError(f'self-review {title}: 内容不能为空；无内容说明理由')
    findings=json.loads(Path(findings_file).read_text()) if findings_file else [] if no_findings else None
    if findings_file and not isinstance(findings,list):
        raise topics.TopicError('self-review.findings: 必须是 M2 发现数组')
    if findings is not None:
        from . import ticket_review as review
        manifest=dict(unit_id='self-observation',content_id=topics.content_id(repo),round=0,acceptance=[],probes=[],
            downstream_tickets=review.downstream(repo,topic,unit['ticket']),coverage_targets=[],
            review_context=dict(provenance='self',model='实施者'))
        result={k:manifest[k] for k in review.PREFILLED}
        result.update(status='findings' if findings else 'pass',reviewer=manifest['review_context'],coverage=[],findings=findings)
        review.validate_result(result,manifest)
    pending=pending_self_findings(unit)
    unresolved=[f for f,_ in pending.values()]
    incoming={f['id']:f for f in findings or []}
    removed=[f for f in unresolved if findings is not None and (f['id'] not in incoming or
        (f.get('severity')=='blocking' and incoming[f['id']].get('severity')!='blocking') or
        (f.get('view')=='spec-challenge' and incoming[f['id']].get('view')!='spec-challenge'))]
    if any(f.get('view')=='spec-challenge' or
           pending[f['id']][1].get('content_id')==topics.content_id(repo) for f in removed):
        raise topics.TopicError('self-review: 未修复内容或未裁决 Spec 挑战，不能仅删除 findings')
    if findings is None and unresolved:findings=unresolved
    history=unit.setdefault('self_reviews',[unit['self_review']] if 'self_review' in unit else [])
    unit['self_review']=dict(content_id=topics.content_id(repo),text=text,at=topics.now(),definition=impl.definition(repo,path))
    if findings is not None:unit['self_review']['findings']=findings
    if removed:
        unit['self_review']['resolutions']=[dict(id=f['id'],prior_content_id=pending[f['id']][1].get('content_id'),
            content_id=unit['self_review']['content_id'],at=topics.now(),evidence=text) for f in removed]
    history.append(unit['self_review'])
    if any(f.get('view')=='spec-challenge' for f in findings or []):
        from .review_loop import stop
        stop(unit,path,record,'Spec 与现有系统冲突：增强自审需要用户裁决')
    else:
        impl.write_json(record,unit)
    return dict(ticket=unit['ticket'],self_review='已记录')


def require_self(repo,unit,allow_findings=False):
    value=unit.get('self_review',{})
    _, path = impl.ticket_path(repo,unit['ticket'])
    if value.get('definition') != impl.definition(repo,path) or value.get('content_id') != topics.content_id(repo):
        raise topics.TopicError('self-review: 当前内容缺少完整增强自审；请 implement self-review --notes-file <记录>')
    if not set(SELF_SECTIONS) <= {t for t,_ in topics.summary_headings(value.get('text',''))}:
        raise topics.TopicError('self-review: 增强自审缺节')
    blocking=[f for f,_ in pending_self_findings(unit).values() if f.get('severity')=='blocking' or f.get('view')=='spec-challenge']
    if blocking and not allow_findings:
        raise topics.TopicError('self-review: 未解决发现：'+', '.join(f['id'] for f in blocking))


def failures(output, code):
    if not code:return []
    cases = re.findall(r'^(?:FAIL|ERROR): (.+)$',output,re.M)
    # pytest node IDs; unittest's FAILED (failures=N) is a summary, not a case.
    cases += re.findall(r'^(?:FAILED|ERROR)\s+([^\s(]\S*)',output,re.M)
    pending=[]
    for line in output.splitlines():
        failed=re.match(r'^\s*--- FAIL: (\S+)',line)
        if failed:pending.append(failed.group(1))
        package=re.match(r'^FAIL\s+(\S+)(?:\s|$)',line)
        if package:
            name=package.group(1)
            cases.extend(f'go:{name}:{test}' for test in pending)
            # A package can fail to build without any executable test case.
            cases.append(f'go:{name}:[package]')
            pending=[]
    cases.extend(pending)  # Single-package snippets without a Go result line.
    # Unknown runners are compared conservatively by the whole diagnostic.
    return sorted(set(cases)) or ['command:'+hashlib.sha256(output.encode()).hexdigest()]


from .evidence import loader_failure_identity, execution_observed, row_execution_observed, row_loader_only_failure, current_unavailable, current_loader_gap_fingerprints


def run_full(repo,config):
    commands=topics.full_tests(config)
    if not commands:raise topics.TopicError('全量测试集合为空')
    identity=topics.content_id(repo)
    rows=[]
    for command in commands:
        from .evidence import execute
        observed,output=execute(repo,shlex.split(command))
        rows.append(dict(observed,command=command,failures=failures(output,observed['exit_code'])))
        if observed['content_changed']:raise topics.TopicError('全量测试改变了内容；本次记录无效')

    if topics.content_id(repo)!=identity:raise topics.TopicError('全量测试改变了内容；本次记录无效')
    return dict(completed=True,content_id=identity,head=topics.git(repo,'rev-parse','HEAD').stdout.decode().strip(),commands=commands,results=rows,at=topics.now())


def baseline_gap(row):
    if row.get('unavailable') and not row_execution_observed(row):
        return ('baseline-unavailable','基线环境缺失，无法比较；当前执行失败仍须修复')
    if row.get('comparison_eligible') is False or row_loader_only_failure(row):
        return ('baseline-identity-unverifiable','基线仅有模块载入失败身份，不能可靠比较；当前执行失败仍须修复')
    return None


def compare(baseline,current):
    if baseline['commands']!=current['commands']:raise topics.TopicError('全量测试配置与基线不同；不能比较')
    if any(len(value.get('results',[]))!=len(value['commands']) or
           any(row.get('command')!=command for row,command in zip(value.get('results',[]),value['commands']))
           for value in (baseline,current)):
        raise topics.TopicError('全量测试记录不完整；不能比较')
    new=[];known=[];unverified=[]
    for old,now in zip(baseline['results'],current['results']):
        unavailable=current_unavailable(now)
        gap=baseline_gap(old)
        old_loader=current_loader_gap_fingerprints(old)
        now_loader=current_loader_gap_fingerprints(now)
        matching_loader={f for f,digest in now_loader.items() if old_loader.get(f)==digest}
        if gap:
            unverified.append(old['command'])
            if not unavailable and now.get('exit_code',bool(now.get('failures'))):
                new.extend(dict(command=now['command'],failure=f,comparison=gap[0]) for f in now['failures'] if f not in matching_loader)
                known.extend(dict(command=now['command'],failure=f) for f in now['failures'] if f in matching_loader)
            continue
        if unavailable:
            new.append(dict(command=now['command'],failure='当前环境无法运行'));continue
        previous=set(old['failures'])
        tail=old.get('output_tail','')
        if not any(f.startswith('go:') for f in previous) and re.search(r'^FAIL\s+\S+',tail,re.M):
            # Recover package identity from recorded facts, never from a bare
            # test-name match that could hide a different package's failure.
            previous=set(failures(tail,old.get('exit_code',1)))
        added=set(now['failures'])-previous
        unchanged=set(now['failures']) & previous
        # Loader names identify modules, not executed behavior cases. Only a
        # identical complete dependency diagnostic may remain known; changed
        # or unknown import failures require repair even in partial runs.
        coarse={f for f in unchanged if loader_failure_identity(f)}
        uncertain=coarse-matching_loader
        if uncertain:
            unverified.append(old['command'])
            new.extend(dict(command=now['command'],failure=f,comparison='loader-identity-unverifiable') for f in sorted(uncertain))
        new.extend(dict(command=now['command'],failure=f) for f in sorted(added))
        known.extend(dict(command=now['command'],failure=f) for f in sorted(unchanged-uncertain))
    return dict(new_failures=new,known_failures=known,unverified=unverified)


def test(repo,topic=None):
    repo=topics.safe_repo(repo);topic=topics.select_topic(repo,topic)
    value,batch=active(repo,topic)
    if batch['status']=='closed':raise topics.TopicError('批次已收口')
    record=topics.topic_path(repo,topic)/f"batch-tests-{batch['id']}.json"
    impl.write_json(record,dict(content_id=topics.content_id(repo),completed=False))
    current=run_full(repo,topics.read_config(repo))
    baseline=json.loads((topics.topic_path(repo,topic)/'test-baseline.json').read_text())
    current.update(compare(baseline,current))
    impl.write_json(topics.topic_path(repo,topic)/f"batch-tests-{batch['id']}.json",current)
    return current


def tests_passed(repo,config,topic,batch):
    path=topics.topic_path(repo,topic)/f"batch-tests-{batch['id']}.json"
    if not path.exists():return False
    value=json.loads(path.read_text())
    if value.get('completed') is not True or value.get('content_id')!=topics.content_id(repo) or value.get('commands')!=topics.full_tests(config):return False
    try:
        baseline=json.loads((topics.topic_path(repo,topic)/'test-baseline.json').read_text())
        from .evidence import environment
        if any(row.get('environment')!=environment(repo,shlex.split(row['command'])) for row in value['results']):return False
        # Re-evaluate raw legacy receipts; a pre-upgrade empty comparison is not proof.
        return not compare(baseline,value)['new_failures']
    except (KeyError,ValueError,OSError,topics.TopicError):return False


def status(repo,topic=None):
    repo=topics.safe_repo(repo);topic=topics.select_topic(repo,topic)
    value,batch=active(repo,topic)
    config=topics.read_config(repo)
    tickets=impl.records(repo,topic)
    tests_current=tests_passed(repo,config,topic,batch)
    implementing=[t for t in batch['tickets'] if tickets[t][1]['status'] in ('implementing','needs-user')]
    implementation_status=impl.status(repo,implementing[0],topic) if implementing else {}
    command=implementation_status.get('next_command') or impl.next_ready_command(repo,topic)
    if all(tickets[t][1]['status']=='complete' for t in batch['tickets']):
        command=f'workflow.py batch {"review" if tests_current else "test"} --repo {shlex.quote(str(repo))} --topic {topic}'
        if batch['status']=='needs-user' and tests_current:command=f'workflow.py batch accept --repo {shlex.quote(str(repo))} --topic {topic} --reason <裁决>'
        elif tests_current:
            from . import branch_review
            try:
                branch_review.require_pass(repo,config,topic,topics.topic_path(repo,topic),{t:tickets[t] for t in batch['tickets']},batch)
                command=f'workflow.py batch close --repo {shlex.quote(str(repo))} --topic {topic}'
                branch=topics.topic_path(repo,topic)/'branch-review.json'
                if branch.exists():
                    try:
                        branch_review.require_pass(repo,config,topic,topics.topic_path(repo,topic),tickets,json.loads(branch.read_text()))
                    except (topics.TopicError,OSError,ValueError):
                        command=f"workflow.py topic review --repo {shlex.quote(str(repo))} --topic {topic} --initiated-by agent --reason '恢复已发起的整分支审查'"
            except (topics.TopicError,OSError,ValueError):pass
    content_input=[]
    if topics.content_dirty(repo) and (batch['status']=='reviewing' or self_observations(repo,topic,batch['tickets'])):
        if repair_findings(repo,topic,batch):
            command=f'workflow.py batch repair --repo {shlex.quote(str(repo))} --topic {topic} --notes-file <修复说明>'
        else:
            command=None
            content_input=['恢复未审查的内容漂移，或先将已授权的新工作归入新 Ticket；当前没有待修复发现可供 batch repair']
    labels={'pending':'待开始','open':'实施中','reviewing':'审查中','needs-user':'需要用户裁决','closed':'已收口'}
    observations=self_observations(repo,topic,batch['tickets'])
    challenges=[o for o in observations if o['finding'].get('view')=='spec-challenge']
    if challenges and not implementing and not topics.content_dirty(repo):
        targets=' '.join(o['target'] for o in challenges)
        decision_ready=True
        try:
            require_self_repairs(repo,topic,batch,observations,allow_challenges=True)
            require_blocking_review(repo,topic,batch,observations)
        except (topics.TopicError,OSError,ValueError):decision_ready=False
        if decision_ready:
            command=f"workflow.py batch {'accept' if tests_current else 'test'} --repo {shlex.quote(str(repo))} --topic {topic}"
            if tests_current:command+=f" --reason '{targets}: <裁决理由>'"
        content_input=['点名挑战并说明裁决；修订定义后可 batch reopen --reason；接受会保留已知问题；correctness blocking 须先修复并审查']
    latest=batch.get('reviews',[])[-1:]
    return dict(topic=topic,batch=batch['id'],state=labels[batch['status']],tickets=batch['tickets'],next_command=command,
        inputs_needed=content_input or (['实际 reviewer-model 与审查上下文来源'] if command and ' review ' in command else ['包含待修复发现 id 的说明文件'] if command and ' repair ' in command else []),
        self_findings=observations,
        decisions_needed=[dict(finding=o['finding'],target=o['target'],decision='请点名修订定义后 reopen 或 accept') for o in challenges]+implementation_status.get('decisions_needed',[])+[dict(finding=f,decision='请决定修订 Spec、接受风险或按原 Spec 继续') for r in latest for f in r.get('result',{}).get('findings',[]) if f.get('view')=='spec-challenge'],
        unverified=[dict(command=r['command'],note=baseline_gap(r)[1]) for r in json.loads((topics.topic_path(repo,topic)/'test-baseline.json').read_text()).get('results',[]) if baseline_gap(r)] if (topics.topic_path(repo,topic)/'test-baseline.json').exists() else [])


def repair_findings(repo,topic,batch):
    findings=[f for r in batch.get('reviews',[])[-1:] for f in r.get('result',{}).get('findings',[]) if f['severity']=='blocking' or f.get('disposition')=='fix-in-batch']
    branch=topics.topic_path(repo,topic)/'branch-review.json'
    if branch.exists():
        findings += [f for r in json.loads(branch.read_text()).get('reviews',[])[-1:] for f in r.get('result',{}).get('findings',[]) if f['severity']=='blocking' or f.get('disposition')=='fix-in-batch']
    findings += [dict(o['finding'],id=o['target']) for o in self_observations(repo,topic,batch['tickets']) if o['finding'].get('view')!='spec-challenge']
    return findings


def repair(repo,topic=None,notes_file=None):
    repo=topics.safe_repo(repo);topic=topics.select_topic(repo,topic)
    value,batch=active(repo,topic)
    if batch['status'] not in ('reviewing','open','needs-user') or not repair_findings(repo,topic,batch):raise topics.TopicError('只有批次审查修复可以提交')
    findings=repair_findings(repo,topic,batch)
    notes=Path(notes_file).read_text() if notes_file else ''
    if not findings or any(f['id'] not in notes for f in findings):raise topics.TopicError('修复说明必须引用全部待修复发现 id')
    topics.preflight_commit(repo,topics.read_config(repo))
    if not topics.content_dirty(repo):raise topics.TopicError('没有修复差异')
    topics.git(repo,'add','--all','--','.',':(top,exclude).agent')
    topics.git(repo,'commit','-m',f"Topic {topic} batch {batch['id']} repair\n\n{notes}")
    batch.setdefault('repair_commits',[]).append(topics.git(repo,'rev-parse','HEAD').stdout.decode().strip())
    batch.setdefault('self_finding_repairs',[]).append(dict(
        targets=[o['target'] for o in self_observations(repo,topic,batch['tickets']) if named(notes,o['target'])],
        head=batch['repair_commits'][-1],content_id=topics.content_id(repo),notes=notes,at=topics.now()))
    save(repo,topic,value)
    return dict(batch=batch['id'],commit=batch['repair_commits'][-1],next_command=f'workflow.py batch test --topic {topic}')


def close(repo,topic=None,accept=False,reason=''):
    repo=topics.safe_repo(repo);topic=topics.select_topic(repo,topic)
    value,batch=active(repo,topic);config=topics.read_config(repo);root=topics.topic_path(repo,topic)
    tickets=impl.records(repo,topic)
    if any(tickets[t][1]['status']!='complete' for t in batch['tickets']):raise topics.TopicError('批次还有未提交 Ticket；请 batch status')
    for t in batch['tickets']:
        receipt=batch.get('submitted',{}).get(t)
        if not receipt or topics.git(repo,'merge-base','--is-ancestor',receipt['head'],'HEAD',check=False).returncode:
            raise topics.TopicError(f'{t}: 缺少当前分支的提交回执')
    if topics.content_dirty(repo):
        message='批次内容尚未提交；请 batch repair' if repair_findings(repo,topic,batch) else '批次存在未审查内容且无待修复发现；请恢复内容，或先归入已授权的新 Ticket'
        raise topics.TopicError(message)
    if not tests_passed(repo,config,topic,batch):raise topics.TopicError('全量测试新增失败或记录过期；请 batch test')
    from . import branch_review
    observations=self_observations(repo,topic,batch['tickets'])
    challenges=[o for o in observations if o['finding'].get('view')=='spec-challenge']
    require_self_repairs(repo,topic,batch,observations,allow_challenges=accept)
    if accept:
        if any(not named(reason,o['target']) for o in challenges):raise topics.TopicError('accept 理由必须点名全部待接受挑战 target')
        if (batch['status']!='needs-user' and not challenges) or not reason.strip():raise topics.TopicError('接受需要待裁决批次和非空用户理由')
        require_blocking_review(repo,topic,batch,observations)
        batch['acceptance']=dict(reason=reason,head=topics.git(repo,'rev-parse','HEAD').stdout.decode().strip(),at=topics.now())
    else:
        branch_review.require_pass(repo,config,topic,root,{t:tickets[t] for t in batch['tickets']},batch)
    branch=root/'branch-review.json'
    if branch.exists():
        unit=json.loads(branch.read_text())
        if accept and unit.get('status') == 'needs-user':
            unit['acceptance'] = dict(reason=reason,head=topics.git(repo,'rev-parse','HEAD').stdout.decode().strip(),content_id=topics.content_id(repo))
            unit['known_issues'] = [f for r in unit.get('reviews',[])[-1:] for f in r.get('result',{}).get('findings',[])]
            impl.write_json(branch,unit)
        branch_review.require_pass(repo,config,topic,root,tickets,unit)
    if accept:
        batch['known_issues']=[dict(o['finding'],ticket=o['ticket'],target=o['target']) for o in challenges]
        for o in observations:
            batch.setdefault('self_finding_resolutions',[]).append(dict(ticket=o['ticket'],finding=o['finding']['id'],
                action='accept' if o in challenges else 'reviewed-repair',reason=reason,content_id=topics.content_id(repo),at=topics.now()))
    if not accept:
        manifest=branch_review.current_manifest(repo,config,topic,root,{t:tickets[t] for t in batch['tickets']},batch)
        for observation in manifest.get('self_findings',[]):
            batch.setdefault('self_finding_resolutions',[]).append(dict(ticket=observation['ticket'],
                finding=observation['finding']['id'],review_unit=manifest['unit_id'],content_id=manifest['content_id'],at=topics.now()))
    batch.update(status='closed',closed_at=topics.now(),head=topics.git(repo,'rev-parse','HEAD').stdout.decode().strip(),content_id=topics.content_id(repo))
    report=json.loads((root/f"batch-tests-{batch['id']}.json").read_text())
    summary=root/'deliveries'/f'deliveries-{topic}-01.md'
    summary.parent.mkdir(parents=True,exist_ok=True)
    if not summary.exists():summary.write_text('\n'.join(f'## {h}\n无\n' for h in topics.HEADINGS))
    text=summary.read_text()
    additions={'已知问题':json.dumps(report['known_failures'],ensure_ascii=False),
               '未验证项':json.dumps(report['unverified'],ensure_ascii=False)}
    sources={r.get('reviewer',{}).get('provenance') for r in batch.get('reviews',[])}
    if 'self' in sources:additions['未验证项'] += '\n独立性缺口：宿主未派出新上下文，批次审查来源为 self。'
    if accept:additions['已知问题'] += '\n用户接受：'+reason+'\n'+json.dumps([*batch.get('reviews',[])[-1:],*batch.get('known_issues',[])],ensure_ascii=False)
    for heading,content in additions.items():
        marker=f'## {heading}\n'
        text=text.replace(marker,marker+f"\n批次 {batch['id']}：\n{content}\n",1)
    summary.write_text(text)
    save(repo,topic,value)
    return dict(topic=topic,batch=batch['id'],state='已收口',next_command=impl.next_start_command(repo,topic))


def reopen(repo,topic=None,reason=''):
    repo=topics.safe_repo(repo);topic=topics.select_topic(repo,topic)
    plan,batch=active(repo,topic)
    if batch['status'] not in ('open','reviewing','needs-user') or not reason.strip():
        raise topics.TopicError('重新审查需要未收口批次和用户裁决理由')
    from . import branch_review
    tickets=impl.records(repo,topic)
    subset={t:tickets[t] for t in batch['tickets']}
    changed=branch_review.definition(repo,subset)
    prior_definition=batch.get('definition') or {t:json.loads(impl.record_path(repo,topic,t).read_text())['definition'] for t in subset}
    if changed==prior_definition:
        raise topics.TopicError('reopen 要求 Ticket/Spec 有效定义修订；状态或勾选不算')
    for p,_ in subset.values():impl.validate(repo,p)
    observations=self_observations(repo,topic,batch['tickets'])
    for o in observations:
        if o['finding'].get('view')=='spec-challenge' and named(reason,o['target']):
            if changed[o['ticket']]==o.get('observed_definition'):
                raise topics.TopicError('点名挑战的 Ticket/Spec 定义尚未修订：'+o['target'])
            batch.setdefault('self_finding_resolutions',[]).append(dict(ticket=o['ticket'],finding=o['finding']['id'],
                action='definition-reopen',reason=reason,definition=changed[o['ticket']],at=topics.now()))
    from .quality_metrics import preserve_history
    preserve_history(batch)
    batch.update(definition=changed,reviews=[],status='reviewing')
    for key in ('active_review','first_review_volume','stop_reason','acceptance'):batch.pop(key,None)
    branch_file=topics.topic_path(repo,topic)/'branch-review.json'
    if branch_file.exists():
        branch=json.loads(branch_file.read_text())
        full_definition=branch_review.definition(repo,tickets)
        if branch.get('status')=='needs-user' and branch.get('definition') != full_definition:
            from .quality_metrics import preserve_history
            preserve_history(branch)
            branch.update(definition=full_definition,reviews=[],status='implementing')
            for key in ('active_review','first_review_volume','stop_reason','acceptance'):branch.pop(key,None)
            branch.setdefault('decisions',[]).append(dict(action='reopen',reason=reason,at=topics.now()))
            impl.write_json(branch_file,branch)
    batch.setdefault('decisions',[]).append(dict(action='reopen',reason=reason,at=topics.now()))
    save(repo,topic,plan)
    return status(repo,topic)
