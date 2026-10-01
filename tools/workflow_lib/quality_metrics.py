"""Quality observations from durable review evidence, including archived Topics."""
import json
import re
import uuid
from . import topic_service as topics

VIEWS=('correctness','impact','spec','spec-challenge','maintainability')
SOURCES=('self','batch','high-risk','whole-branch','ticket-legacy')
LAYERS=('访谈','Spec 编写','设计审查','实施自审','批次审查')
ESCAPE_SOURCES=('人工评审','外部审查工具','测试环境','生产','后续开发')


def empty_fields():
    return dict(finding_counts=None,batches=None,high_risk_reviews=None,whole_branch_review=None)


def read_json(path):
    return json.loads(path.read_text())


def topic_root(repo,topic):
    current=topics.topic_path(repo,topic)
    archived=topics.topic_path(repo,topic,True)
    return current if current.is_dir() else archived if archived.is_dir() else None


def design_status(root):
    if root is None:return '未知'
    reviews=root/'reviews'
    for path in reviews.glob('*.json'):
        try:value=read_json(path)
        except (OSError,ValueError):continue
        if isinstance(value,dict) and value.get('status')=='accepted' and isinstance(value.get('design_report'),dict) and set(value['design_report'])=={'assertions','findings','excluded_risks','semantic_assumptions'}:return '已执行'
    marker=root/'design-review.json'
    if marker.is_file():
        try:value=read_json(marker)
        except (OSError,ValueError):value={}
        if not isinstance(value,dict):value={}
        if value.get('ran') is True:return '已执行'
        if value.get('ran') is False:return '未触发'
    for path in reviews.glob('*.md'):
        text=path.read_text()
        headings={h for h,_ in topics.summary_headings(text)}
        if '设计审查' in text and all(x in headings for x in ('承重断言核验表','审查发现','已考察但排除的风险','待用户确认的需求语义假设')):
            return '已执行'
    from .tickets import frontmatter
    current=[p for p in (root/'specs').glob('*.md') if frontmatter(p).get('status')=='current']
    if current and all(re.search(r'(?m)^(?:设计审查[：:]\s*)?未触发设计审查(?:[：:，。；\s]|$)',p.read_text()) for p in current):
        return '未触发'
    return '未知'


def counts(items, unknown=()):
    result={source:{v:{s:0 for s in ('blocking','advisory')} for v in VIEWS} for source in SOURCES}
    seen=set();incomplete=set(unknown)
    for source,scope,findings in items:
        for f in findings:
            if f.get('view') not in VIEWS or f.get('severity') not in ('blocking','advisory') or not f.get('id'):
                incomplete.add(source);continue
            key=(source,scope,f['id'])
            if key in seen:continue
            seen.add(key)
            result[source][f['view']][f['severity']]+=1
    for source in incomplete:result[source]=None
    return result


def all_reviews(unit):
    return unit.get('past_reviews',[])+unit.get('reviews',[])


def preserve_history(unit):
    unit.setdefault('past_reviews',[]).extend(unit.get('reviews',[]))


def unit_items(unit,source,scope):
    return [(source,(scope,r.get('review_series','legacy')),r.get('result',{}).get('findings',[])) for r in all_reviews(unit)]


def dispatch_count(units):
    sessions=set()
    for unit in units:
        for review in all_reviews(unit):
            context=review.get('review_context')
            if not isinstance(context,dict):return None
            if context.get('provenance')=='independent':sessions.add(context['session_id'])
    return len(sessions)


def high_risk_info(units):
    risky=[u for u in units if u.get('high_risk_reason')]
    return dict(count=len(risky),with_blocking=sum(any(f.get('severity')=='blocking' for r in all_reviews(u) for f in r.get('result',{}).get('findings',[])) for u in risky),rounds=sum(len(all_reviews(u)) for u in risky))


def ticket_fields(unit):
    own=unit.get('self_reviews', [unit['self_review']] if 'self_review' in unit else [])
    items=[('self',unit['ticket'],r.get('findings',[])) for r in own]
    source='high-risk' if unit.get('high_risk_reason') else 'batch' if unit.get('batch_id') else 'ticket-legacy'
    items+=unit_items(unit,source,unit['ticket'])
    return dict(finding_counts=counts(items,('self',) if not own or any('findings' not in r for r in own) else ()),batches=None,
                high_risk_reviews=high_risk_info([unit]),whole_branch_review=None)


def observations(root):
    if root is None:return empty_fields()
    implementations=[read_json(p) for p in (root/'implementations').glob('*.json')]
    items=[];unknown=[]
    for unit in implementations:
        own=unit.get('self_reviews',[unit['self_review']] if 'self_review' in unit else [])
        if not own or any('findings' not in r for r in own):unknown.append('self')
        items += [('self',unit['ticket'],r.get('findings',[])) for r in own]
        items += unit_items(unit,'high-risk' if unit.get('high_risk_reason') else 'batch' if unit.get('batch_id') else 'ticket-legacy',unit['ticket'])
    branch_path=root/'branch-review.json'
    branch=read_json(branch_path) if branch_path.exists() else None
    if branch:items+=unit_items(branch,'whole-branch','topic')
    plan_path=root/'batches.json'
    batch_reports=None
    if plan_path.exists():
        plan=read_json(plan_path);batch_reports=[]
        for index,stored in enumerate(plan['batches']):
            path=root/'batches'/f"{stored['id']}.json"
            batch=read_json(path) if path.exists() else stored
            items+=unit_items(batch,'batch',batch['id'])
            tickets=[u for u in implementations if u.get('ticket') in batch['tickets']]
            units=[batch,*tickets]+([branch] if branch and index==len(plan['batches'])-1 else [])
            batch_reports.append(dict(id=batch['id'],review_subagents=dispatch_count(units),high_risk_reviews=high_risk_info(tickets)))
    if not implementations and not branch and not plan_path.exists():return empty_fields()
    if not implementations:unknown.append('self')
    tally=counts(items,unknown)
    branch_count=sum(n for view in tally['whole-branch'].values() for n in view.values()) if tally['whole-branch'] is not None else None
    return dict(finding_counts=tally,batches=batch_reports,
                high_risk_reviews=high_risk_info(implementations),
                whole_branch_review=dict(requested=bool(branch),executed=bool(any(r.get('result') for r in all_reviews(branch))) if branch and any(r.get('result') for r in all_reviews(branch)) else None if branch else False,initiated_by=branch.get('initiated_by') if branch else None,
                    reason=branch.get('reason') if branch else None,findings=branch_count if branch and any(r.get('result') for r in all_reviews(branch)) else None if branch else 0))


def escapes(repo,topic=None):
    path=repo/'.agent/escaped-defects.jsonl'
    records=[json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    return [r for r in records if topic is None or r['topic']==topic]


def record_escape(repo,topic,source,view,expected_layer,description,batch=None,ticket=None):
    repo=topics.safe_repo(repo);topics.read_config(repo)
    root=topic_root(repo,topic)
    if root is None:raise topics.TopicError('逃逸缺陷：Topic 不存在（可登记已归档 Topic）')
    for field,value,allowed in (('source',source,ESCAPE_SOURCES),('view',view,VIEWS),('expected_layer',expected_layer,LAYERS)):
        if value not in allowed:raise topics.TopicError(f'逃逸缺陷.{field}: 无效取值')
    if not isinstance(description,str) or not description.strip():raise topics.TopicError('逃逸缺陷.description: 必须非空')
    if ticket:
        from .tickets import frontmatter
        if not any(frontmatter(p).get('id')==ticket for p in (root/'tickets').glob('*.md')):
            raise topics.TopicError('逃逸缺陷.ticket: 不属于该 Topic')
    if ticket and not batch and (root/'batches.json').exists():
        batch=next((b['id'] for b in read_json(root/'batches.json')['batches'] if ticket in b['tickets']),None)
    if batch:
        plan=root/'batches.json'
        found=next((b for b in read_json(plan)['batches'] if b['id']==batch),None) if plan.exists() else None
        if not found or (ticket and ticket not in found['tickets']):raise topics.TopicError('逃逸缺陷.batch: 不存在或 Ticket 不属于此批次')
    record=dict(id=uuid.uuid4().hex,topic=topic,batch=batch,ticket=ticket,source=source,view=view,expected_layer=expected_layer,
                description=description.strip(),design_review=design_status(root),at=topics.now())
    with (repo/'.agent/escaped-defects.jsonl').open('a') as stream:stream.write(json.dumps(record,ensure_ascii=False)+'\n')
    return record
