"""Public CLI batch paths in temporary real Git repositories."""
import json
from pathlib import Path
import unittest
import test_implement_lifecycle as legacy
import test_topic_lifecycle as topic_tests
from tools.workflow_lib import batches, topic_service

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
    def test_briefing_contains_predecessor_contracts_batch_impacts_and_hints(self):
        self.setup(2)
        self.cli('implement','start','--ticket','feature-01')
        (self.repo/'code.txt').write_text('first')
        self.cli('implement','test')
        notes=self.repo/'.agent/self.md'
        notes.write_text('\n'.join(f'## {h}\n无：玩具用例。\n' for h in batches.SELF_SECTIONS).replace(
            '## 影响面\n无：玩具用例。', '## 影响面\n概述\n### 对外契约\nCONTRACT_CALLER_SENTINEL\n### 兼容性\nROLLING_SENTINEL'))
        self.cli('implement','self-review','--notes-file',str(notes))
        first=self.repo/'.agent/work/feature/tickets/tickets-feature-01.md'
        first.write_text(first.read_text().replace('- [ ]','- [x]'))
        self.cli('implement','finish')
        p=self.repo/'.agent/work/feature/tickets/tickets-feature-02.md'
        p.write_text(p.read_text()+'\n## 触点提示\nshared module; public contract\n')
        report=json.loads(self.cli('implement','start','--ticket','feature-02').stdout)
        text=Path(report['briefing']).read_text()
        self.assertIn('code.txt',text)
        self.assertIn('CONTRACT_CALLER_SENTINEL',text)
        self.assertIn('ROLLING_SENTINEL',text)
        prior=text.split('## 已完成前置 Ticket',1)[1].split('## 适用规则',1)[0]
        peers=text.split('## 同批次已提交 Ticket 的影响面',1)[1].split('## 测试命令',1)[0]
        for section in (prior,peers):
            self.assertIn('CONTRACT_CALLER_SENTINEL',section)
            self.assertIn('ROLLING_SENTINEL',section)
        self.assertIn('契约与消费者',text)
        self.assertIn('同批次已提交 Ticket 的影响面',text)
        self.assertIn('shared module; public contract',text)
        self.assertIn('现状断言→代码依据',text)
        (self.repo/'code.txt').write_text('second')
        self.cli('implement','test');self.self_review()
        p.write_text(p.read_text().replace('- [ ]','- [x]'))
        self.cli('implement','finish')
        report=self.review()
        manifest=json.loads(Path(report['manifest']).read_text())
        declaration=next(item for item in manifest['inputs'] if Path(item['snapshot_path']).name=='impact-declarations.md')
        frozen=Path(declaration['snapshot_path']).read_text()
        self.assertIn('CONTRACT_CALLER_SENTINEL',frozen)
        self.assertIn('ROLLING_SENTINEL',frozen)

    def test_new_ticket_without_legacy_rule_fields_uses_actual_repository_rules(self):
        self.setup()
        p=self.repo/'.agent/work/feature/tickets/tickets-feature-01.md'
        import re
        p.write_text(re.sub(r'^rule_(sources|scope|constraints|conflicts):.*\n','',p.read_text(),flags=re.M))
        (self.repo/'nested').mkdir()
        (self.repo/'nested/AGENTS.md').write_text('ACTUAL_PATH_RULE_SENTINEL')
        (self.repo/'nested/client.py').write_text('initial')
        self.git('add','nested');self.git('commit','-m','existing nested caller')
        report=json.loads(self.cli('implement','start','--ticket','feature-01').stdout)
        self.assertIn('ACTUAL_PATH_RULE_SENTINEL',Path(report['briefing']).read_text())
        (self.repo/'nested/client.py').write_text('changed')
        self.cli('implement','test');self.self_review()
        p.write_text(p.read_text().replace('- [ ]','- [x]'))
        self.cli('implement','finish')
        report=self.review()
        manifest=json.loads(Path(report['manifest']).read_text())
        rules=Path(manifest['inputs'][0]['snapshot_path']).read_text()
        self.assertIn('ACTUAL_PATH_RULE_SENTINEL',rules)

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

    def test_go_package_identity_distinguishes_same_named_cases_and_build_failure(self):
        old_output='--- FAIL: TestSame (0.00s)\nFAIL\texample.com/probe/a\t0.003s\nok\texample.com/probe/b\t0.002s\nFAIL\n'
        new_output='--- FAIL: TestSame (0.00s)\nFAIL\texample.com/probe/a\t0.003s\n--- FAIL: TestSame (0.00s)\nFAIL\texample.com/probe/b\t0.002s\nFAIL\n'
        def result(output):
            return dict(commands=['go test ./...'],results=[dict(command='go test ./...',unavailable=False,failures=batches.failures(output,1))])
        added=batches.compare(result(old_output),result(new_output))['new_failures']
        self.assertIn('go:example.com/probe/b:TestSame',[f['failure'] for f in added])
        self.assertNotIn('go:example.com/probe/a:TestSame',[f['failure'] for f in added])
        legacy=result(old_output)
        legacy['results'][0].update(failures=['TestSame'],output_tail=old_output,exit_code=1)
        self.assertEqual([],batches.compare(legacy,result(old_output))['new_failures'])
        self.assertIn('go:example.com/probe/b:TestSame',[f['failure'] for f in batches.compare(legacy,result(new_output))['new_failures']])
        build=batches.compare(result(old_output),result(old_output+'FAIL\texample.com/probe/c [build failed]\n'))
        self.assertIn('go:example.com/probe/c:[package]',[f['failure'] for f in build['new_failures']])

    def test_partial_missing_dependency_does_not_hide_executed_test_failure(self):
        suite=self.repo/'suite';suite.mkdir()
        (suite/'test_missing.py').write_text('import dependency_missing_in_this_toy_repo\n')
        behavior=suite/'test_behavior.py'
        behavior.write_text('import unittest\nclass Behavior(unittest.TestCase):\n def test_behavior(self): self.assertEqual(1, 1)\n')
        self.git('add','suite');self.git('commit','-qm','partial environment baseline')
        # A wrapper may report a missing dependency via exit 127 even though
        # unittest already executed another test. Execution evidence wins.
        (self.repo/'runner.py').write_text(
            "import subprocess, sys\nsubprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'suite'])\nraise SystemExit(127)\n")
        self.git('add','runner.py');self.git('commit','-qm','partial runner exit status')
        self.setup(full='python3 -B runner.py');self.implement();self.review()
        baseline=json.loads((self.repo/'.agent/work/feature/test-baseline.json').read_text())
        self.assertFalse(baseline['results'][0]['unavailable'])
        behavior.write_text(behavior.read_text().replace('assertEqual(1, 1)','assertEqual(1, 2)'))
        self.git('add','suite');self.git('commit','-qm','inject reachable behavior failure')
        current=json.loads(self.cli('batch','test','--topic','feature').stdout)
        self.assertFalse(current['unverified'])
        self.assertTrue(any('test_behavior' in f['failure'] for f in current['new_failures']))
        self.cli('batch','close','--topic','feature',ok=False)
        self.assertTrue(batches.execution_observed('ERROR tests/test_missing.py - ModuleNotFoundError\n1 passed, 1 error in 0.2s\n'))
        self.assertFalse(batches.execution_observed('ERROR tests/test_missing.py - ModuleNotFoundError\n1 error during collection\n'))
        self.assertEqual(['tests/test_missing.py'],batches.failures('ERROR tests/test_missing.py - ModuleNotFoundError\n',1))
        # Old partial baselines mislabelled unavailable can still be compared.
        baseline['results'][0]['unavailable']=True
        observed=batches.run_full(self.repo,topic_service.read_config(self.repo))
        self.assertTrue(batches.compare(baseline,observed)['new_failures'])

    def test_fixing_one_of_two_unittest_failures_does_not_create_new_case(self):
        suite=self.repo/'suite';suite.mkdir()
        behavior=suite/'test_behavior.py'
        behavior.write_text('import unittest\nclass Behavior(unittest.TestCase):\n def test_a(self): self.assertEqual(1, 2)\n def test_b(self): self.assertEqual(3, 4)\n')
        self.git('add','suite');self.git('commit','-qm','two failing baseline cases')
        self.setup(full='python3 -B -m unittest discover -s suite');self.implement()
        behavior.write_text(behavior.read_text().replace('assertEqual(3, 4)','assertEqual(3, 3)'))
        self.git('add','suite');self.git('commit','-qm','repair one known failure')
        current=json.loads(self.cli('batch','test','--topic','feature').stdout)
        self.assertEqual([],current['new_failures'])
        self.assertTrue(any('test_a' in f['failure'] for f in current['known_failures']))
        self.assertFalse(any('(failures=' in f['failure'] for f in current['known_failures']))
        self.review();self.cli('batch','close','--topic','feature')

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
