"""Serial batches, enhanced self-review and baseline-relative full tests."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
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
    history=unit.setdefault('self_reviews',[unit['self_review']] if 'self_review' in unit else [])
    unit['self_review']=dict(content_id=topics.content_id(repo),text=text,at=topics.now(),definition=impl.definition(repo,path))
    if findings is not None:unit['self_review']['findings']=findings
    history.append(unit['self_review'])
    impl.write_json(record,unit)
    return dict(ticket=unit['ticket'],self_review='已记录')


def require_self(repo,unit):
    value=unit.get('self_review',{})
    _, path = impl.ticket_path(repo,unit['ticket'])
    if value.get('definition') != impl.definition(repo,path) or value.get('content_id') != topics.content_id(repo):
        raise topics.TopicError('self-review: 当前内容缺少完整增强自审；请 implement self-review --notes-file <记录>')
    if not set(SELF_SECTIONS) <= {t for t,_ in topics.summary_headings(value.get('text',''))}:
        raise topics.TopicError('self-review: 增强自审缺节')


def failures(output, code):
    if not code:return []
    cases = re.findall(r'^(?:FAIL|ERROR): (.+)$',output,re.M)
    cases += re.findall(r'^FAILED\s+(\S+)',output,re.M)
    cases += re.findall(r'^\s*--- FAIL: (\S+)',output,re.M)
    # Unknown runners are compared conservatively by the whole diagnostic.
    return sorted(set(cases)) or ['command:'+hashlib.sha256(output.encode()).hexdigest()]


def run_full(repo,config):
    commands=topics.full_tests(config)
    if not commands:raise topics.TopicError('全量测试集合为空')
    identity=topics.content_id(repo)
    rows=[]
    for command in commands:
        try:
            result=subprocess.run(shlex.split(command),cwd=repo,capture_output=True,text=True,errors='replace')
            output=result.stdout+result.stderr
            unavailable=result.returncode != 0 and (result.returncode in (126,127) or bool(re.search(r'ModuleNotFoundError|No module named|command not found',output)))
            code=result.returncode
        except OSError as exc:
            output=str(exc);code=127;unavailable=True
        rows.append(dict(command=command,exit_code=code,unavailable=unavailable,failures=failures(output,code),output_tail=output[-4000:]))
    if topics.content_id(repo)!=identity:raise topics.TopicError('全量测试改变了内容；本次记录无效')
    return dict(content_id=identity,head=topics.git(repo,'rev-parse','HEAD').stdout.decode().strip(),commands=commands,results=rows,at=topics.now())


def compare(baseline,current):
    if baseline['commands']!=current['commands']:raise topics.TopicError('全量测试配置与基线不同；不能比较')
    new=[];known=[];unverified=[]
    for old,now in zip(baseline['results'],current['results']):
        if old['unavailable']:
            unverified.append(old['command']);continue
        if now['unavailable']:
            new.append(dict(command=now['command'],failure='当前环境无法运行'));continue
        added=set(now['failures'])-set(old['failures'])
        new.extend(dict(command=now['command'],failure=f) for f in sorted(added))
        known.extend(dict(command=now['command'],failure=f) for f in sorted(set(now['failures']) & set(old['failures'])))
    return dict(new_failures=new,known_failures=known,unverified=unverified)


def test(repo,topic=None):
    repo=topics.safe_repo(repo);topic=topics.select_topic(repo,topic)
    value,batch=active(repo,topic)
    if batch['status']=='closed':raise topics.TopicError('批次已收口')
    current=run_full(repo,topics.read_config(repo))
    baseline=json.loads((topics.topic_path(repo,topic)/'test-baseline.json').read_text())
    current.update(compare(baseline,current))
    impl.write_json(topics.topic_path(repo,topic)/f"batch-tests-{batch['id']}.json",current)
    return current


def tests_passed(repo,config,topic,batch):
    path=topics.topic_path(repo,topic)/f"batch-tests-{batch['id']}.json"
    if not path.exists():return False
    value=json.loads(path.read_text())
    return value['content_id']==topics.content_id(repo) and value['commands']==topics.full_tests(config) and not value['new_failures']


def status(repo,topic=None):
    repo=topics.safe_repo(repo);topic=topics.select_topic(repo,topic)
    value,batch=active(repo,topic)
    config=topics.read_config(repo)
    tickets=impl.records(repo,topic)
    implementing=[t for t in batch['tickets'] if tickets[t][1]['status'] in ('implementing','needs-user')]
    command=impl.status(repo,implementing[0],topic)['next_command'] if implementing else impl.next_start_command(repo,topic)
    if all(tickets[t][1]['status']=='complete' for t in batch['tickets']):
        command=f'workflow.py batch {"review" if tests_passed(repo,config,topic,batch) else "test"} --repo {shlex.quote(str(repo))} --topic {topic}'
        if batch['status']=='needs-user':command=f'workflow.py batch accept --repo {shlex.quote(str(repo))} --topic {topic} --reason <裁决>'
        else:
            from . import branch_review
            try:
                branch_review.require_pass(repo,config,topic,topics.topic_path(repo,topic),{t:tickets[t] for t in batch['tickets']},batch)
                command=f'workflow.py batch close --repo {shlex.quote(str(repo))} --topic {topic}'
            except (topics.TopicError,OSError,ValueError):pass
    labels={'pending':'待开始','open':'实施中','reviewing':'审查中','needs-user':'需要用户裁决','closed':'已收口'}
    latest=batch.get('reviews',[])[-1:] 
    return dict(topic=topic,batch=batch['id'],state=labels[batch['status']],tickets=batch['tickets'],next_command=command,
        decisions_needed=[dict(finding=f,decision='请决定修订 Spec、接受风险或按原 Spec 继续') for r in latest for f in r.get('result',{}).get('findings',[]) if f.get('view')=='spec-challenge'],
        unverified=[dict(command=r['command'],note='基线环境缺失，无法验证；收口摘要必须披露') for r in json.loads((topics.topic_path(repo,topic)/'test-baseline.json').read_text()).get('results',[]) if r['unavailable']] if (topics.topic_path(repo,topic)/'test-baseline.json').exists() else [])


def repair(repo,topic=None,notes_file=None):
    repo=topics.safe_repo(repo);topic=topics.select_topic(repo,topic)
    value,batch=active(repo,topic)
    if batch['status']!='reviewing':raise topics.TopicError('只有批次审查修复可以提交')
    findings=[f for r in batch.get('reviews',[])[-1:] for f in r.get('result',{}).get('findings',[]) if f['severity']=='blocking' or f.get('disposition')=='fix-in-batch']
    branch=topics.topic_path(repo,topic)/'branch-review.json'
    if branch.exists():
        findings += [f for r in json.loads(branch.read_text()).get('reviews',[])[-1:] for f in r.get('result',{}).get('findings',[]) if f['severity']=='blocking' or f.get('disposition')=='fix-in-batch']
    notes=Path(notes_file).read_text() if notes_file else ''
    if not findings or any(f['id'] not in notes for f in findings):raise topics.TopicError('修复说明必须引用全部待修复发现 id')
    topics.preflight_commit(repo,topics.read_config(repo))
    if not topics.content_dirty(repo):raise topics.TopicError('没有修复差异')
    topics.git(repo,'add','--all','--','.',':(top,exclude).agent')
    topics.git(repo,'commit','-m',f"Topic {topic} batch {batch['id']} repair\n\n{notes}")
    batch.setdefault('repair_commits',[]).append(topics.git(repo,'rev-parse','HEAD').stdout.decode().strip())
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
    if topics.content_dirty(repo):raise topics.TopicError('批次内容尚未提交；请 batch repair')
    if not tests_passed(repo,config,topic,batch):raise topics.TopicError('全量测试新增失败或记录过期；请 batch test')
    from . import branch_review
    if accept:
        if batch['status']!='needs-user' or not reason.strip():raise topics.TopicError('接受需要待裁决批次和非空用户理由')
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
    if accept:additions['已知问题'] += '\n用户接受：'+reason+'\n'+json.dumps(batch.get('reviews',[])[-1:],ensure_ascii=False)
    for heading,content in additions.items():
        marker=f'## {heading}\n'
        text=text.replace(marker,marker+f"\n批次 {batch['id']}：\n{content}\n",1)
    summary.write_text(text)
    save(repo,topic,value)
    return dict(topic=topic,batch=batch['id'],state='已收口',next_command=impl.next_start_command(repo,topic))


def reopen(repo,topic=None,reason=''):
    repo=topics.safe_repo(repo);topic=topics.select_topic(repo,topic)
    plan,batch=active(repo,topic)
    if batch['status'] not in ('reviewing','needs-user') or not reason.strip():
        raise topics.TopicError('重新审查需要未收口批次和用户裁决理由')
    from . import branch_review
    tickets=impl.records(repo,topic)
    subset={t:tickets[t] for t in batch['tickets']}
    changed=branch_review.definition(repo,subset)
    if not batch.get('definition') or changed==batch['definition']:
        raise topics.TopicError('reopen 要求 Ticket/Spec 有效定义修订；状态或勾选不算')
    for p,_ in subset.values():impl.validate(repo,p)
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
