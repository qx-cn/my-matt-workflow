"""Public CLI batch paths in temporary real Git repositories."""
import json
from pathlib import Path
import unittest
import test_implement_lifecycle as legacy
import test_topic_lifecycle as topic_tests
from tools.workflow_lib import batches

class BatchTests(unittest.TestCase):
    git=legacy.ImplementationTests.git
    cli=legacy.ImplementationTests.cli
    setup_config=legacy.ImplementationTests.setup_config
    ticket=legacy.ImplementationTests.ticket
    replace=legacy.ImplementationTests.replace
    summary=topic_tests.TopicLifecycleTests.summary
    def setUp(self):
        legacy.ImplementationTests.setUp(self)
        self.batch_model=True
    def setup(self,count=1,full="python3 -c 'pass'"):
        self.setup_config(tests=(full,"python3 -c 'pass'"))
        for i in range(1,count+1):self.ticket(number=i,dependencies=('feature-%02d'%(i-1),) if i>1 else ())
    def self_review(self):
        path=self.repo/'.agent/self.md'
        path.write_text('\n'.join(f'## {h}\n无：玩具用例无此风险。\n' for h in batches.SELF_SECTIONS))
        self.cli('implement','self-review','--notes-file',str(path))
    def implement(self,number=1,mutation=None):
        self.cli('implement','start','--ticket',f'feature-{number:02d}')
        (self.repo/'code.txt').write_text(f'ticket {number}\n')
        if mutation:mutation()
        self.cli('implement','test');self.self_review()
        p=self.repo/f'.agent/work/feature/tickets/tickets-feature-{number:02d}.md'
        p.write_text(p.read_text().replace('- [ ]','- [x]'))
        return self.cli('implement','finish')
    def review(self,action='batch',finding=None):
        self.cli('batch','test','--topic','feature')
        options=('--initiated-by','agent','--reason','shared contract') if action=='topic' else ()
        report=json.loads(self.cli(action,'review','--topic','feature','--reviewer-model','host',
                     '--reviewer-session-id','fresh-context',*options).stdout)
        manifest=json.loads(Path(report['manifest']).read_text())
        result=json.loads(Path(report['result_file']).read_text())
        result.update(status='findings' if finding else 'pass',reviewer=dict(provenance='independent',model='host'),
                      coverage=[dict(target=t,result='ok') for t in manifest['coverage_targets']],findings=[finding] if finding else [])
        Path(report['result_file']).write_text(json.dumps(result))
        self.cli(action,'review','--topic','feature','--submit',report['result_file'])
        return report
    def test_clean_three_ticket_batch_one_dispatch_and_topic_completion(self):
        self.setup(3)
        for i in range(1,4):self.implement(i)
        self.review();self.cli('batch','close','--topic','feature')
        value=batches.read(self.repo,'feature')
        self.assertEqual(1,len(value['batches'][0]['reviews']))
        self.assertEqual('independent',value['batches'][0]['reviews'][0]['reviewer']['provenance'])
        self.summary('feature');self.cli('topic','complete','--topic','feature')
        self.assertTrue((self.repo/'.agent/archive/feature').exists())
    def test_submit_requires_targeted_test_and_complete_self_review(self):
        self.setup();self.cli('implement','start','--ticket','feature-01')
        self.cli('implement','finish',ok=False)
        self.cli('implement','test')
        self.assertIn('self-review',self.cli('implement','finish',ok=False).stderr)
        bad=self.repo/'.agent/bad.md';bad.write_text('## 验收对照\nnone')
        self.assertIn('缺少章节',self.cli('implement','self-review','--notes-file',str(bad),ok=False).stderr)
        self.self_review();(self.repo/'code.txt').write_text('drift')
        self.assertIn('test',self.cli('implement','finish',ok=False).stderr)
    def test_unanchored_impact_blocks_then_batch_repair_and_rereview_closes(self):
        (self.repo/'shared.py').write_text('def value(): return 1\n')
        (self.repo/'caller.py').write_text('from shared import value\nassert value()+1 == 2\n')
        self.git('add','shared.py','caller.py');self.git('commit','-qm','formal baseline caller')
        import subprocess,sys
        self.assertEqual(0,subprocess.run([sys.executable,'-B','caller.py'],cwd=self.repo,capture_output=True).returncode)
        self.setup(3)
        for i in range(1,4):
            self.implement(i,lambda:(self.repo/'shared.py').write_text('def value(): return "1"\n') if i==2 else None)
        self.assertNotEqual(0,subprocess.run([sys.executable,'-B','caller.py'],cwd=self.repo,capture_output=True).returncode)
        finding=dict(id='F-impact',view='impact',severity='blocking',summary='unchanged caller breaks',
                     location='caller.py:3',basis='public caller reaches changed shared function semantics')
        self.review(finding=finding)
        self.cli('batch','close','--topic','feature',ok=False)
        (self.repo/'shared.py').write_text('def value(): return 1\n')
        self.assertEqual(0,subprocess.run([sys.executable,'-B','caller.py'],cwd=self.repo,capture_output=True).returncode)
        notes=self.repo/'.agent/repair.md';notes.write_text('F-impact: restore shared contract')
        self.cli('batch','repair','--topic','feature','--notes-file',str(notes))
        self.review();self.cli('batch','close','--topic','feature')
        self.assertIn('F-impact',self.git('log','-1','--format=%B'))
    def test_high_risk_review_blocks_ticket_and_never_replaces_batch(self):
        self.setup();self.cli('implement','start','--ticket','feature-01');self.cli('implement','test');self.self_review()
        self.cli('implement','review','--reviewer-model','host',ok=False)
        report=json.loads(self.cli('implement','review','--reviewer-model','host','--reason','persistent contract','--reviewer-session-id','fresh').stdout)
        result=json.loads(Path(report['result_file']).read_text())
        result.update(status='findings',reviewer=dict(provenance='independent',model='host'),coverage=[dict(target=a['id'],result='ok') for a in result['acceptance']]+[dict(target=t,result='ok') for t in result['probes']],
            findings=[dict(id='risk',view='correctness',severity='blocking',summary='failure',location='code.txt:1',basis='public read fails')])
        Path(report['result_file']).write_text(json.dumps(result));self.cli('implement','review','--submit',report['result_file'])
        self.assertIn('implement review',json.loads(self.cli('batch','status','--topic','feature').stdout)['next_command'])
        self.cli('implement','finish',ok=False)
        report=json.loads(self.cli('implement','review','--reviewer-model','host','--reason','persistent contract','--reviewer-session-id','fresh2').stdout)
        result.update(unit_id=report['unit_id'],content_id=report['content_id'],round=report['round'],status='pass',findings=[])
        Path(report['result_file']).write_text(json.dumps(result));self.cli('implement','review','--submit',report['result_file'])
        p=self.repo/'.agent/work/feature/tickets/tickets-feature-01.md';p.write_text(p.read_text().replace('- [ ]','- [x]'))
        self.cli('implement','finish');self.cli('batch','test','--topic','feature')
        self.cli('batch','close','--topic','feature',ok=False)
        self.review();self.cli('batch','close','--topic','feature')
    def test_baseline_existing_failure_allows_close_new_failure_blocks(self):
        script=self.repo/'full.py';script.write_text("from pathlib import Path\nprint('FAIL: old')\nif Path('code.txt').read_text()=='bad': print('FAIL: new')\nraise SystemExit(1)\n")
        self.git('add','full.py');self.git('commit','-qm','baseline runner')
        self.setup(full='python3 full.py');self.implement()
        report=json.loads(self.cli('batch','test','--topic','feature').stdout)
        self.assertEqual([],report['new_failures']);self.assertTrue(report['known_failures'])
        (self.repo/'code.txt').write_text('bad');self.git('add','code.txt');self.git('commit','-qm','inject new failure')
        report=json.loads(self.cli('batch','test','--topic','feature').stdout)
        self.assertTrue(report['new_failures']);self.cli('batch','close','--topic','feature',ok=False)
    def test_unavailable_baseline_is_reported_and_challenge_stops(self):
        self.setup(full='missing-test-program')
        self.implement()
        result=json.loads(self.cli('batch','test','--topic','feature').stdout)
        self.assertIn('missing-test-program',result['unverified'])
        self.review(finding=dict(id='challenge',view='spec-challenge',severity='blocking',summary='Spec conflicts',location='Spec:behavior',basis='existing caller fails'))
        status=json.loads(self.cli('batch','status','--topic','feature').stdout)
        self.assertEqual('需要用户裁决',status['state']);self.assertTrue(status['decisions_needed'])
        self.cli('batch','accept','--topic','feature','--reason','user accepts stated conflict')
        self.assertIn('missing-test-program',self.cli('topic','status','--topic','feature').stdout)
    def test_successful_negative_import_diagnostic_is_not_unavailable(self):
        script=self.repo/'full.py';script.write_text("from pathlib import Path\nprint('ModuleNotFoundError expected by negative probe')\nraise SystemExit(1 if Path('code.txt').read_text()=='bad' else 0)\n")
        self.git('add','full.py');self.git('commit','-qm','baseline diagnostic probe')
        self.setup(full='python3 full.py');self.implement()
        baseline=json.loads((self.repo/'.agent/work/feature/test-baseline.json').read_text())
        self.assertFalse(baseline['results'][0]['unavailable'])
        (self.repo/'code.txt').write_text('bad');self.git('add','code.txt');self.git('commit','-qm','inject actual failure')
        result=json.loads(self.cli('batch','test','--topic','feature').stdout)
        self.assertTrue(result['new_failures'])

    def test_go_nested_failure_comparison_detects_new_case(self):
        old=dict(commands=['go test ./...'],results=[dict(command='go test ./...',unavailable=False,failures=batches.failures('--- FAIL: TestPaths (0.00s)\n    --- FAIL: TestPaths/old (0.00s)\n',1))])
        current=dict(commands=['go test ./...'],results=[dict(command='go test ./...',unavailable=False,failures=batches.failures('--- FAIL: TestPaths (0.00s)\n    --- FAIL: TestPaths/old (0.00s)\n    --- FAIL: TestPaths/new (0.00s)\n',1))])
        result=batches.compare(old,current)
        self.assertEqual(['TestPaths/new'],[f['failure'] for f in result['new_failures']])

    def test_status_recovery_reopen_and_postclosure_drift(self):
        self.setup()
        self.cli('implement','start','--ticket','feature-01')
        for command in ('batch','topic'):
            status=json.loads(self.cli(command,'status','--topic','feature').stdout)
            self.assertIn('implement test',status['next_command'])
        self.cli('implement','test');self.self_review()
        p=self.repo/'.agent/work/feature/tickets/tickets-feature-01.md';p.write_text(p.read_text().replace('- [ ]','- [x]'))
        self.cli('implement','finish')
        self.review(finding=dict(id='challenge',view='spec-challenge',severity='blocking',summary='conflict',location='Spec:behavior',basis='reachable failure'))
        self.cli('batch','reopen','--topic','feature','--reason','status alone',ok=False)
        spec=self.repo/'.agent/work/feature/specs/specs-feature-01.md';spec.write_text(spec.read_text()+'\nclarified contract\n')
        self.cli('batch','reopen','--topic','feature','--reason','user clarified')
        self.review();self.cli('batch','close','--topic','feature')
        (self.repo/'code.txt').write_text('post closure drift')
        self.git('add','code.txt');self.git('commit','-qm','unreviewed drift')
        self.assertIn('补偿',self.cli('topic','complete','--topic','feature',ok=False).stderr)

    def test_two_batches_optional_branch_and_content_binding(self):
        self.setup(2)
        groups=self.repo/'.agent/groups.json';groups.write_text(json.dumps([['feature-01'],['feature-02']]))
        self.cli('batch','plan','--topic','feature','--groups-file',str(groups),'--reason','integration boundary')
        self.implement();self.cli('implement','start','--ticket','feature-02',ok=False)
        self.review();self.cli('batch','close','--topic','feature')
        self.implement(2);report=self.review()
        manifest=json.loads(Path(report['manifest']).read_text());self.assertIn('code.txt',manifest['topic_changes'])
        self.review(action='topic')
        (self.repo/'code.txt').write_text('drift')
        self.cli('batch','close','--topic','feature',ok=False)
        self.git('restore','code.txt');self.cli('batch','close','--topic','feature')
        self.summary('feature');self.cli('topic','complete','--topic','feature')
