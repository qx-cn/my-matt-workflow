import os, sys, json, hashlib, subprocess, shlex, traceback
from pathlib import Path
sys.dont_write_bytecode=True
OLD=Path('/tmp/outcome-holistic-608b72b'); BASE=Path('/tmp/outcome-holistic-base-7947cb2')
CANDIDATE=Path(sys.argv[1]).resolve(); OUT=Path(sys.argv[2])
sys.path[:0]=[str(OLD),str(OLD/'tests')]
import test_topic_lifecycle as seam
from test_batches import BatchTests
from test_topic_branch import BranchTests
LOG=[]
original_run=subprocess.run
def traced_run(*a,**k):
    result=original_run(*a,**k)
    command=a[0] if a else k.get('args')
    if isinstance(command,list) and any('workflow.py' in str(x) for x in command):
        LOG.append(dict(command=[str(x) for x in command],cwd=str(k.get('cwd','')),exit=result.returncode,stdout=result.stdout,stderr=result.stderr))
    return result
subprocess.run=traced_run

def use(path):seam.CLI=path/'tools/workflow.py'
def new(cls=BatchTests):
    t=cls();t.setUp();return t

def raw(t,*args):
    return subprocess.run([sys.executable,str(seam.CLI),*args,'--repo',str(t.repo)],capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
def fixture_review(t,retain_challenge=False):
    tested=raw(t,'batch','test','--topic','feature')
    opened=raw(t,'batch','review','--topic','feature','--reviewer-model','host','--reviewer-session-id','independent-gate-fixture')
    if opened.returncode:return {'test_exit':tested.returncode,'open_exit':opened.returncode}
    report=json.loads(opened.stdout);manifest=json.loads(Path(report['manifest']).read_text());result=json.loads(Path(report['result_file']).read_text())
    result.update(status='pass',reviewer=dict(provenance='independent',model='host'),coverage=[dict(target=v,result='ok') for v in manifest['coverage_targets']],findings=[])
    if retain_challenge:
        observations=[o for o in manifest['self_findings'] if o['finding'].get('view')=='spec-challenge']
        result.update(status='findings',findings=[o['finding'] for o in observations])
        for row in result['coverage']:
            match=next((o for o in observations if o['target']==row['target']),None)
            if match:row.update(result='finding',finding_id=match['finding']['id'])
    Path(report['result_file']).write_text(json.dumps(result))
    submitted=raw(t,'batch','review','--topic','feature','--submit',report['result_file'])
    return dict(test_exit=tested.returncode,open_exit=0,manifest=manifest,submit_exit=submitted.returncode)

def legacy_pending(view):
    t=new();use(BASE)
    try:
        t.setup();t.cli('implement','start','--ticket','feature-01');(t.repo/'code.txt').write_text('incorrect caller result\n')
        t.cli('implement','test');t.self_review()
        finding=dict(id='legacy-'+view,severity='blocking',view=view,summary='unresolved caller requirement',location='code.txt:1',basis='caller requires correct result')
        path=t.repo/'.agent/findings.json';path.write_text(json.dumps([finding]))
        t.cli('implement','self-review','--notes-file',str(t.repo/'.agent/self.md'),'--findings-file',str(path))
        ticket=t.repo/'.agent/work/feature/tickets/tickets-feature-01.md';ticket.write_text(ticket.read_text().replace('- [ ]','- [x]'))
        t.cli('implement','finish');unit=t.repo/'.agent/work/feature/implementations/feature-01.json'
        history={str(p):p.read_bytes() for p in (ticket,unit)}
        use(CANDIDATE);status=json.loads(t.cli('batch','status','--topic','feature').stdout)
        review=fixture_review(t);closed=raw(t,'batch','close','--topic','feature')
        return dict(status=status,review=review,close_exit=closed.returncode,historical_bytes_unchanged=all(p.read_bytes()==v for name,v in history.items() for p in [Path(name)]),checks=dict(close_blocked=closed.returncode!=0,history_unchanged=all(Path(p).read_bytes()==v for p,v in history.items())))
    finally:t.doCleanups()

def dynamic(v1=False,loader=False):
    t=new();use(OLD if v1 else CANDIDATE)
    try:
        runner=t.repo/('suite/test_behavior.py' if loader else 'full.py');runner.parent.mkdir(exist_ok=True);runner.write_text('import unavailable_review_baseline_dependency\n');t.git('add',str(runner.relative_to(t.repo)));t.git('commit','-qm','missing baseline dependency')
        t.setup(full='python3 -B -m unittest discover -s suite' if loader else 'python3 -B full.py');t.implement()
        runner.write_text("from pathlib import Path\nimport importlib\ndef selected_plugin():\n    return 'json_typo_regression'\nPath('.agent/behavior-executed').write_text('selected_plugin invoked')\nimportlib.import_module(selected_plugin())\n")
        t.git('add',str(runner.relative_to(t.repo)));t.git('commit','-qm','regressed real plugin selection')
        receipt=json.loads(t.cli('batch','test','--topic','feature').stdout)
        failure_review=fixture_review(t)
        if v1:
            assert receipt['results'][0]['dependency_proof_version']==1
            assert receipt['results'][0]['unavailable']
        use(CANDIDATE)
        status=json.loads(t.cli('batch','status','--topic','feature').stdout)
        refused=raw(t,'batch','close','--topic','feature')
        if refused.returncode==0:
            return dict(initial_receipt=receipt,status=status,failure_review=failure_review,refused_exit=0,checks=dict(failure_blocks=False))
        # After repair the assertion observes the selected module's actual API.
        runner.write_text("import importlib\ndef selected_plugin():\n    return 'json'\nmodule=importlib.import_module(selected_plugin())\nassert module.loads('{\"ok\": true}') == {'ok': True}\n")
        if loader:
            runner.write_text("import importlib\nimport unittest\ndef selected_plugin():\n    return 'json'\nclass PluginBehavior(unittest.TestCase):\n    def test_selected_plugin_api(self):\n        module=importlib.import_module(selected_plugin())\n        self.assertEqual({'ok': True}, module.loads('{\"ok\": true}'))\n")
        t.git('add',str(runner.relative_to(t.repo)));t.git('commit','-qm','repair plugin selection')
        repaired=json.loads(t.cli('batch','test','--topic','feature').stdout);review=fixture_review(t)
        closed=raw(t,'batch','close','--topic','feature')
        if loader:
            assert repaired['results'][0]['exit_code']==0, 'loader repair did not pass actual tests'
            assert 'Ran 1 test' in repaired['results'][0]['output_tail'], 'loader repair ran no TestCase'
        return dict(initial_receipt=receipt,status=status,refused_exit=refused.returncode,repair_receipt=repaired,repair_review=review,close_exit=closed.returncode,checks=dict(real_marker=(t.repo/'.agent/behavior-executed').read_text()=='selected_plugin invoked',failure_blocks=refused.returncode!=0,repair_passes=not repaired['new_failures'],repair_closes=closed.returncode==0))
    finally:t.doCleanups()

def startup(loader=False):
    t=new();use(CANDIDATE)
    try:
        if loader:
            suite=t.repo/'suite';suite.mkdir();(suite/'test_behavior.py').write_text('import outcome_review_direct_missing_dependency\n');t.git('add','suite');t.git('commit','-qm','direct loader dependency gap')
        t.setup(full='python3 -B -m unittest discover -s suite' if loader else 'python3 -B -m outcome_review_missing_runner');t.implement()
        receipt=json.loads(t.cli('batch','test','--topic','feature').stdout);review=fixture_review(t);closed=raw(t,'batch','close','--topic','feature')
        checks=dict(unavailable=receipt['results'][0]['unavailable'],unverified=bool(receipt['unverified']),no_behavior_failure=not receipt['new_failures'],close=closed.returncode==0)
        if loader:
            checks=dict(loader_not_unavailable=not receipt['results'][0]['unavailable'],
                        same_known=bool(receipt['known_failures']),unverified=bool(receipt['unverified']),
                        not_current_pass=receipt['results'][0]['exit_code']!=0,
                        no_new_failure=not receipt['new_failures'],close=closed.returncode==0)
        return dict(receipt=receipt,review=review,close_exit=closed.returncode,checks=checks)
    finally:t.doCleanups()

def geometry(nonpass=False):
    t=new(BranchTests);use(BASE)
    try:
        t.multi();t.cli('topic','test');first=t.branch_review();t.branch_submit(t.blocking(first))
        (t.repo/'code.txt').write_text('fixed\nsecond\nline three\nline four\n');t.cli('topic','test')
        report=t.branch_review();t.branch_submit(t.blocking(report) if nonpass else t.result(report))
        before=json.loads(t.cli('topic','status').stdout)
        use(CANDIDATE);status=json.loads(t.cli('topic','status').stdout)
        if nonpass: attempted=raw(t,'topic','complete')
        else: attempted=raw(t,*shlex.split(status['next_command'])[1:])
        root=t.repo/'.agent';records=list(root.glob('*/feature/branch-review.json'))
        record=json.loads(records[0].read_text()) if records else {}
        return dict(before=before,status=status,attempt_exit=attempted.returncode,record=record,checks=dict(expected_exit=(attempted.returncode!=0 if nonpass else attempted.returncode==0),not_archived=(not (root/'archive/feature').exists() if nonpass else True)))
    finally:t.doCleanups()

def legacy_recovery(view='correctness',mixed=False,reopen=False):
    t=new();use(BASE)
    try:
        t.setup();t.cli('implement','start','--ticket','feature-01');(t.repo/'code.txt').write_text('incorrect caller result\n')
        t.cli('implement','test');t.self_review()
        views=['correctness','spec-challenge'] if mixed else [view]
        findings=[dict(id='legacy-'+v,severity='blocking',view=v,summary='unresolved caller requirement',location='code.txt:1',basis='caller requires correct result') for v in views]
        path=t.repo/'.agent/findings.json';path.write_text(json.dumps(findings))
        t.cli('implement','self-review','--notes-file',str(t.repo/'.agent/self.md'),'--findings-file',str(path))
        root=t.repo/'.agent/work/feature';ticket=root/'tickets/tickets-feature-01.md';ticket.write_text(ticket.read_text().replace('- [ ]','- [x]'))
        t.cli('implement','finish');unit=root/'implementations/feature-01.json'
        history={str(p.relative_to(root)):p.read_bytes() for p in (ticket,unit)}
        use(CANDIDATE);review=fixture_review(t);before=json.loads(t.cli('batch','status','--topic','feature').stdout)
        wrong_accept=raw(t,'batch','accept','--topic','feature','--reason','accept unrelated finding')
        assert wrong_accept.returncode!=0,'unrelated decision accepted'
        mixed_attempt=None
        if mixed:
            mixed_attempt=raw(t,'batch','accept','--topic','feature','--reason','User accepts self:feature-01:legacy-spec-challenge only')
            assert mixed_attempt.returncode!=0,'challenge decision also accepted correctness blocker'
        if 'correctness' in views:
            notes=t.repo/'.agent/repair.md';notes.write_text('self:feature-01:legacy-correctness: caller result repaired; oracle reads exact required value.\n')
            nochange=raw(t,'batch','repair','--topic','feature','--notes-file',str(notes));assert nochange.returncode!=0,'unchanged code recorded as repair'
            (t.repo/'code.txt').write_text('correct caller result\n')
            t.cli('batch','repair','--topic','feature','--notes-file',str(notes))
            assert (t.repo/'code.txt').read_text()=='correct caller result\n'
            stale=raw(t,'batch','close','--topic','feature');assert stale.returncode!=0,'repair closed without refreshed tests/review'
            review=fixture_review(t,retain_challenge=mixed)
        if 'spec-challenge' in views:
            if reopen:
                spec=root/'specs/specs-feature-01.md';spec.write_text(spec.read_text()+'\nUser clarifies the caller requirement and resolves legacy-spec-challenge.\n')
                t.cli('batch','reopen','--topic','feature','--reason','User revised definition for self:feature-01:legacy-spec-challenge')
                review=fixture_review(t);closed=raw(t,'batch','close','--topic','feature')
            else:closed=raw(t,'batch','accept','--topic','feature','--reason','User explicitly accepts self:feature-01:legacy-spec-challenge')
        else:closed=raw(t,'batch','close','--topic','feature')
        batch=json.loads((root/'batches.json').read_text())
        completion=raw(t,'topic','complete','--topic','feature') if closed.returncode==0 else None
        archived=t.repo/'.agent/archive/feature';finalroot=archived if archived.exists() else root
        unchanged=all((finalroot/p).read_bytes()==v for p,v in history.items())
        return dict(status=before,review=review,batch=batch,wrong_accept_exit=wrong_accept.returncode,mixed_accept_exit=mixed_attempt.returncode if mixed_attempt else None,close_exit=closed.returncode,complete_exit=completion.returncode if completion else None,checks=dict(closes=closed.returncode==0,completes=completion is not None and completion.returncode==0,history_unchanged=unchanged))
    finally:t.doCleanups()

cases={'R1_correctness_recovery':legacy_recovery,'R1_challenge_accept':lambda:legacy_recovery('spec-challenge'),'R1_challenge_reopen':lambda:legacy_recovery('spec-challenge',reopen=True),'R1_mixed_recovery':lambda:legacy_recovery(mixed=True),'R1_correctness':lambda:legacy_pending('correctness'),'R1_challenge':lambda:legacy_pending('spec-challenge'),'R2_dynamic':dynamic,'R2_dynamic_loader':lambda:dynamic(loader=True),'R2_v1':lambda:dynamic(True),'R2_startup':startup,'R2_direct_loader_startup':lambda:startup(loader=True),'R3_pass':geometry,'R3_nonpass':lambda:geometry(True)}
results={}
for name,case in cases.items():
    if os.environ.get('REVIEW_CASES') and name not in os.environ['REVIEW_CASES'].split(','):continue
    offset=len(LOG)
    try:
        item=case();item['passed']=all(item['checks'].values())
    except Exception as exc:item=dict(passed=False,error=str(exc),traceback=traceback.format_exc())
    item['cli_calls']=LOG[offset:];results[name]=item
    OUT.write_text(json.dumps(results,ensure_ascii=False,indent=2))
    print(name,item['passed'],item.get('checks',item.get('error')),flush=True)
sys.exit(0 if all(v['passed'] for v in results.values()) else 1)
