from pathlib import Path
import json, os, subprocess, sys, tempfile, traceback
SOURCE=Path('/tmp/outcome-review-final-04')
CLI=SOURCE/'tools/workflow.py'
OUT=Path('/tmp/outcome-runtime-03-evidence');OUT.mkdir(exist_ok=True)
ENV={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}
for key in ('PYTHONPATH','PYTHONSTARTUP'): ENV.pop(key,None)
EVENTS=[];RESULTS={}

def record(name,value):
    RESULTS[name]=value
    (OUT/'results.json').write_text(json.dumps(RESULTS,ensure_ascii=False,indent=2))
    print(name,json.dumps(value,ensure_ascii=False),flush=True)

class Fixture:
    def __init__(self,label,full,files=None,count=1):
        self.label=label;self.repo=Path(tempfile.mkdtemp(prefix='runtime03-'+label+'-',dir='/tmp'))
        self.root=self.repo/'.agent/work/feature'
        self.git('init','-q','--initial-branch=main');self.git('config','user.name','Independent Runtime Probe');self.git('config','user.email','runtime-probe@example.invalid')
        self.write('code.txt','initial\n')
        for path,body in (files or {}).items():self.write(path,body)
        self.commit('independent baseline')
        self.call('setup','--apply','--agent-directory-mode','shared','--test-command',full,'--test-command',"python3 -B -c 'pass'")
        for n in range(1,count+1): self.ticket(n)
    def write(self,path,body):
        p=self.repo/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body);return p
    def git(self,*args):return subprocess.check_output(['git',*args],cwd=self.repo,text=True,env=ENV).strip()
    def commit(self,message):self.git('add','--all');self.git('commit','-qm',message)
    def call(self,*args,expect=0):
        result=subprocess.run([sys.executable,'-B',str(CLI),*args,'--repo',str(self.repo)],cwd=self.repo,env=ENV,text=True,capture_output=True)
        EVENTS.append(dict(fixture=self.label,repo=str(self.repo),argv=[sys.executable,'-B',str(CLI),*args,'--repo',str(self.repo)],exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr))
        (OUT/'cli-events.json').write_text(json.dumps(EVENTS,ensure_ascii=False,indent=2))
        if expect is not None: assert result.returncode==expect,(args,result.returncode,result.stderr,result.stdout)
        return result
    def data(self,*args):return json.loads(self.call(*args).stdout)
    def ticket(self,n):
        spec=self.write('.agent/work/feature/specs/specs-feature-01.md','---\nspec_id: feature\nrevision: 1\n---\n# Probe contract\n## 验收标准\n- AC-01: marker observed\n')
        values=dict(id=f'feature-{n:02d}',title='Independent temporary probe',ticket_kind='implementation',spec_id='feature',spec_revision=1,spec_ref=str(spec.relative_to(self.repo)),status='ready-for-agent',blocked_by=[f'feature-{n-1:02d}'] if n>1 else [],sequence=n,test_commands=["python3 -B -c 'pass'"],rule_sources=[str(spec.relative_to(self.repo))],rule_scope=['code.txt'],rule_constraints=['observe tests'],rule_conflicts=[],review_probes=['recovery'],execution_agent='auto',claimed_by='',supersedes_ticket=[],compensates=[],tags=[])
        self.write(f'.agent/work/feature/tickets/tickets-feature-{n:02d}.md','---\n'+'\n'.join(f'{k}: {json.dumps(v)}' for k,v in values.items())+'\n---\n## 要构建什么\nProbe marker\n## 适用规则与影响区域\nlocal\n## 验收标准\n- [ ] marker observed\n')
    def implement(self,n=1):
        self.call('implement','start','--ticket',f'feature-{n:02d}','--agent','codex')
        self.write('code.txt',f'probe marker {n}\n');self.call('implement','test')
        notes=self.write('.agent/self.md','\n'.join('## '+h+'\n无：隔离门禁夹具，非真实产品验收。\n' for h in ('验收对照','现状核实','影响面','对抗检查','简洁与约定','已知缺口')))
        self.call('implement','self-review','--notes-file',str(notes))
        p=self.root/f'tickets/tickets-feature-{n:02d}.md';p.write_text(p.read_text().replace('- [ ]','- [x]'));self.call('implement','finish')
    def review(self,action='batch',finding=None):
        self.data('batch','test','--topic','feature')
        extra=['--initiated-by','agent','--reason','independent fixture gate'] if action=='topic' else []
        report=self.data(action,'review','--topic','feature','--reviewer-model','fixture','--reviewer-session-id','synthetic-fixture-only',*extra)
        manifest=json.loads(Path(report['manifest']).read_text());result=json.loads(Path(report['result_file']).read_text())
        result.update(status='findings' if finding else 'pass',reviewer={'provenance':'independent','model':'fixture'},coverage=[{'target':t,'result':'ok'} for t in manifest['coverage_targets']],findings=[finding] if finding else [])
        Path(report['result_file']).write_text(json.dumps(result));self.call(action,'review','--topic','feature','--submit',report['result_file'])
    def baseline(self):return json.loads((self.root/'test-baseline.json').read_text())
    def close_blocked(self):
        r=self.call('batch','close','--topic','feature',expect=1)
        assert '全量测试新增失败或记录过期' in r.stderr,r.stderr
        return {'exit_code':r.returncode,'stderr':r.stderr.strip()}


def loader(verbose):
    label='loader-v' if verbose else 'loader-default'
    f=Fixture(label,'python3 -B -m unittest discover -s suite'+(' -v' if verbose else ''),{'suite/test_behavior.py':'import runtime03_missing_dependency\n'})
    f.implement()
    initial_review=None
    if not verbose: f.review()
    else:
        f.data('batch','test','--topic','feature')
        r=f.call('batch','review','--topic','feature','--reviewer-model','fixture','--reviewer-session-id','synthetic-fixture-only',expect=1)
        initial_review={'exit_code':r.returncode,'stderr':r.stderr.strip()}
    base=f.baseline();row=base['results'][0]
    assert row['comparison_eligible'] is False
    assert row['unavailable'] is (not verbose),(row['unavailable'],verbose)
    f.write('suite/test_behavior.py',"assert 1 == 2, 'runtime03 actual top-level assertion'\n");f.commit('current real assertion')
    current=f.data('batch','test','--topic','feature');r=current['results'][0]
    assert r['exit_code']==1 and not r['unavailable'] and 'AssertionError: runtime03 actual top-level assertion' in r['output_tail']
    assert current['new_failures'] and current['unverified'] and not current['known_failures']
    assert row['failures']==r['failures'],(row['failures'],r['failures'])
    status=f.data('batch','status','--topic','feature');topic=f.data('topic','status','--topic','feature')
    blocked=f.close_blocked()
    # Simulate actual pre-newfield receipts, preserving raw loader failure facts;
    # historical incorrect unavailable=false and empty cached comparisons included.
    old=json.loads(json.dumps(base));old['results'][0].pop('comparison_eligible');old['results'][0]['unavailable']=False
    (f.root/'test-baseline.json').write_text(json.dumps(old))
    now=json.loads(json.dumps(current));now['results'][0].pop('comparison_eligible');now.update(new_failures=[],known_failures=[{'command':r['command'],'failure':r['failures'][0]}],unverified=[])
    (f.root/'batch-tests-01.json').write_text(json.dumps(now))
    legacy_status=f.data('batch','status','--topic','feature');legacy_block=f.close_blocked()
    legacy=f.data('batch','test','--topic','feature');assert legacy['new_failures'] and legacy['unverified'] and not legacy['known_failures']
    assert 'batch test' in legacy_status['next_command']
    record(label,dict(repo=str(f.repo),initial_review=initial_review,baseline=base,current=current,status=status,topic=topic,close=blocked,legacy_baseline=old,legacy_status=legacy_status,legacy_close=legacy_block,legacy_current=legacy))


def partial(verbose):
    body='import unittest\nclass Behavior(unittest.TestCase):\n def test_known(self): self.assertEqual(1, 2)\n def test_new(self): self.assertEqual(3, 3)\n'
    f=Fixture('partial-v' if verbose else 'partial-default','python3 -B -m unittest discover -s suite'+(' -v' if verbose else ''),{'suite/test_missing.py':'import runtime03_partial_dependency\n','suite/test_behavior.py':body})
    f.implement();base=f.baseline();assert not base['results'][0]['unavailable'] and base['results'][0]['comparison_eligible']
    f.write('suite/test_behavior.py',body.replace('assertEqual(3, 3)','assertEqual(3, 4)'));f.commit('new executed failure')
    result=f.data('batch','test','--topic','feature');assert not result['results'][0]['unavailable'] and not result['unverified']
    assert len(result['new_failures'])==1 and 'test_new' in result['new_failures'][0]['failure']
    assert any('test_known' in r['failure'] for r in result['known_failures'])
    blocked=f.close_blocked()
    base['results'][0].pop('comparison_eligible');base['results'][0]['unavailable']=True
    (f.root/'test-baseline.json').write_text(json.dumps(base));old=f.data('batch','test','--topic','feature')
    assert len(old['new_failures'])==1 and 'test_new' in old['new_failures'][0]['failure'] and not old['unverified'];f.close_blocked()
    record(f.label,dict(repo=str(f.repo),baseline=base,current=result,close=blocked,legacy_current=old))


def known():
    body='import unittest\nclass Behavior(unittest.TestCase):\n def test_a(self): self.assertEqual(1, 2)\n def test_b(self): self.assertEqual(3, 4)\n'
    f=Fixture('known-executed','python3 -B -m unittest discover -s suite',{'suite/test_behavior.py':body});f.implement()
    f.write('suite/test_behavior.py',body.replace('assertEqual(3, 4)','assertEqual(3, 3)'));f.commit('repair known b')
    result=f.data('batch','test','--topic','feature');assert not result['new_failures'] and not result['unverified']
    assert len(result['known_failures'])==1 and 'test_a' in result['known_failures'][0]['failure'];f.review()
    close=f.call('batch','close','--topic','feature');record('known-executed',dict(repo=str(f.repo),current=result,close_exit=close.returncode))


def stages():
    f=Fixture('multistage','python3 -B runner.py',{'runner.py':'import runtime03_missing_baseline\n'});f.implement();base=f.baseline();assert base['results'][0]['unavailable']
    cases={
       'assertion':"subprocess.run([sys.executable,'-B','-c',\"assert False, 'runtime03 actual child assertion'\"])",
       'systemexit':"subprocess.run([sys.executable,'-B','-c',\"raise SystemExit('runtime03 actual SystemExit')\"])",
       'shell':"subprocess.run(['sh','-c','echo runtime03-actual-shell-failure >&2; exit 1'])"}
    evidence={}
    for name,phase in cases.items():
        f.write('runner.py','import subprocess,sys\n'+phase+'\nimport runtime03_missing_optional_phase\n');f.commit('independent '+name)
        r=f.data('batch','test','--topic','feature');assert not r['results'][0]['unavailable'] and r['new_failures']
        evidence[name]=dict(current=r,close=f.close_blocked())
    record('multistage',dict(repo=str(f.repo),baseline=base,cases=evidence))


def narrow():
    commands=['runtime03_missing_executable','python3 -B -m runtime03_missing_module','python3 -B import_gap.py',"sh -c 'runtime03_missing_shell_command'"]
    for n,c in enumerate(commands):
        f=Fixture('startup-'+str(n),c,{'import_gap.py':'import runtime03_missing_import\n'});f.implement();r=f.baseline();assert r['results'][0]['unavailable'];record(f.label,dict(repo=str(f.repo),baseline=r))
    f=Fixture('success-diagnostic','python3 -B runner.py',{'runner.py':"print('ModuleNotFoundError: No module named deliberately_negative_probe')\n"});f.implement();base=f.baseline();assert base['results'][0]['exit_code']==0 and not base['results'][0]['unavailable']
    f.write('runner.py',"assert False, 'runtime03 diagnostic-success now real failure'\n");f.commit('real failure after success');r=f.data('batch','test','--topic','feature');assert r['new_failures'] and not r['results'][0]['unavailable'];record(f.label,dict(repo=str(f.repo),baseline=base,current=r,close=f.close_blocked()))


def branch():
    f=Fixture('accepted-branch',"python3 -B -c 'pass'",count=2);f.implement(1);f.implement(2);f.review()
    finding=dict(id='runtime03-branch-conflict',severity='blocking',view='spec-challenge',summary='fixture user contract conflict',location='Spec:AC-01',basis='fixture-only explicit conflict')
    f.review(action='topic',finding=finding)
    before=f.data('topic','status','--topic','feature');assert before['decisions_needed']
    accepted=f.data('batch','accept','--topic','feature','--reason','synthetic fixture user decision accepts conflict')
    state=f.data('topic','status','--topic','feature');human=f.call('topic','status','--topic','feature','--human').stdout
    assert not state['decisions_needed'] and state['known_issues'] and state['branch_review']['status']=='accepted'
    assert state['branch_review']['stop_reason'] is None and state['branch_review']['historical_stop_reason']==before['branch_review']['stop_reason']
    assert accepted['next_command']==state['next_command'] and 'topic complete' in state['next_command']
    assert '已接受的历史原因' in human and '请用户决定修订 Spec' not in human
    complete=f.call('topic','complete','--topic','feature');record('accepted-branch',dict(repo=str(f.repo),before=before,accepted=accepted,current=state,human=human,complete_exit=complete.returncode))

if __name__=='__main__':
    jobs=[('loader-default',lambda:loader(False)),('loader-v',lambda:loader(True)),('partial-default',lambda:partial(False)),('partial-v',lambda:partial(True)),('known',known),('multistage',stages),('narrow',narrow),('branch',branch)]
    errors=[]
    for name,job in jobs:
        try:job()
        except Exception:
            errors.append(name);record('PROBE_ERROR-'+name,traceback.format_exc())
    record('RUN_SUMMARY',{'jobs':len(jobs),'errors':errors,'cli_calls':len(EVENTS),'python':sys.version,'python_executable':sys.executable,'source':str(SOURCE)})
    raise SystemExit(bool(errors))
