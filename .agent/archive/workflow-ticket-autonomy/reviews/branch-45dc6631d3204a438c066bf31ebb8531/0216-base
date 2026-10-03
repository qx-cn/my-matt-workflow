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
    def test_unavailable_baseline_current_failure_and_legacy_recovery_block_close(self):
        runner=self.repo/'full.py'
        self.setup(full='python3 -B -m full');self.implement()
        runner.write_text("print('FAIL: actual behavior'); raise SystemExit(1)\n")
        self.git('add','full.py');self.git('commit','-qm','currently executable failure')
        current=json.loads(self.cli('batch','test','--topic','feature').stdout)
        self.assertTrue(current['new_failures'])
        self.assertIn('python3 -B -m full',current['unverified'])
        self.cli('batch','close','--topic','feature',ok=False)
        # A pre-upgrade record may have hidden the raw failure. Recovery must
        # recompute from those facts, without changing already completed history.
        receipt=self.repo/'.agent/work/feature/batch-tests-01.json'
        old=json.loads(receipt.read_text());old['new_failures']=[]
        receipt.write_text(json.dumps(old))
        status=json.loads(self.cli('batch','status','--topic','feature').stdout)
        self.assertIn('batch test',status['next_command'])
        self.cli('batch','close','--topic','feature',ok=False)
        runner.write_text("print('current passes')\n")
        self.git('add','full.py');self.git('commit','-qm','repair current failure')
        passed=json.loads(self.cli('batch','test','--topic','feature').stdout)
        self.assertEqual([],passed['new_failures'])
        self.assertIn('python3 -B -m full',passed['unverified'])
        self.review();self.cli('batch','close','--topic','feature')

    def test_self_blocking_requires_changed_evidence_and_preserves_history(self):
        self.setup();self.cli('implement','start','--ticket','feature-01')
        (self.repo/'code.txt').write_text('wrong')
        self.cli('implement','test');self.self_review()
        notes=self.repo/'.agent/self.md';findings=self.repo/'.agent/findings.json'
        findings.write_text(json.dumps([dict(id='self-bug',severity='blocking',view='correctness',
            summary='wrong behavior',location='code.txt:1',basis='read marker returns wrong value')]))
        self.cli('implement','self-review','--notes-file',str(notes),'--findings-file',str(findings))
        p=self.repo/'.agent/work/feature/tickets/tickets-feature-01.md'
        p.write_text(p.read_text().replace('- [ ]','- [x]'))
        self.assertIn('self-bug',self.cli('implement','finish',ok=False).stderr)
        self.assertIn('self-review',json.loads(self.cli('implement','status').stdout)['next_command'])
        record=self.repo/'.agent/work/feature/implementations/feature-01.json'
        legacy_record=json.loads(record.read_text());legacy_record['self_review'].pop('findings')
        record.write_text(json.dumps(legacy_record))
        self.assertIn('self-bug',self.cli('implement','finish',ok=False).stderr)
        # Merely replacing the findings with zero on identical content is not a repair.
        self.cli('implement','self-review','--notes-file',str(notes),'--no-findings',ok=False)
        findings.write_text(json.dumps([dict(id='self-bug',severity='advisory',view='correctness',
            summary='downgraded only',location='code.txt:1',basis='same code',disposition='decline',reason='just changed severity')]))
        self.cli('implement','self-review','--notes-file',str(notes),'--findings-file',str(findings),ok=False)
        (self.repo/'code.txt').write_text('correct');self.cli('implement','test')
        self.cli('implement','self-review','--notes-file',str(notes),'--no-findings')
        self.cli('implement','finish')
        unit=json.loads((self.repo/'.agent/work/feature/implementations/feature-01.json').read_text())
        self.assertTrue(any(f['id']=='self-bug' for r in unit['self_reviews'] for f in r.get('findings',[])))
        self.assertTrue(unit['self_review']['resolutions'])

    def test_self_spec_challenge_requires_explicit_decision(self):
        self.setup();self.cli('implement','start','--ticket','feature-01')
        self.cli('implement','test');self.self_review()
        notes=self.repo/'.agent/self.md';findings=self.repo/'.agent/findings.json'
        findings.write_text(json.dumps([dict(id='self-challenge',severity='blocking',view='spec-challenge',
            summary='definition conflicts',location='Spec:behavior',basis='approved result contradicts caller')]))
        self.cli('implement','self-review','--notes-file',str(notes),'--findings-file',str(findings))
        status=json.loads(self.cli('implement','status').stdout)
        self.assertEqual('needs-user',status['status']);self.assertTrue(status['decisions_needed'])
        self.cli('implement','finish',ok=False)
        self.cli('implement','self-review','--notes-file',str(notes),'--no-findings',ok=False)
        self.cli('resolve','--ticket','feature-01','--accept','--reason','user accepts conflict')
        unit=json.loads((self.repo/'.agent/work/feature/implementations/feature-01.json').read_text())
        self.assertEqual('self-challenge',unit['known_issues'][0]['id'])

    def test_revised_definition_reopens_self_challenge_without_losing_history(self):
        self.setup();self.cli('implement','start','--ticket','feature-01');self.cli('implement','test');self.self_review()
        notes=self.repo/'.agent/self.md';findings=self.repo/'.agent/findings.json'
        findings.write_text(json.dumps([dict(id='definition',severity='blocking',view='spec-challenge',
            summary='needs definition decision',location='Spec:behavior',basis='incompatible user interpretations')]))
        self.cli('implement','self-review','--notes-file',str(notes),'--findings-file',str(findings))
        spec=self.repo/'.agent/work/feature/specs/specs-feature-01.md';spec.write_text(spec.read_text()+'\nUser clarified meaning.\n')
        self.cli('resolve','--ticket','feature-01','--reopen','--reason','definition: user clarified meaning')
        self.cli('implement','test');self.cli('implement','self-review','--notes-file',str(notes),'--no-findings')
        p=self.repo/'.agent/work/feature/tickets/tickets-feature-01.md';p.write_text(p.read_text().replace('- [ ]','- [x]'))
        self.cli('implement','finish')
        unit=json.loads((self.repo/'.agent/work/feature/implementations/feature-01.json').read_text())
        self.assertTrue(any(f['id']=='definition' for r in unit['self_reviews'] for f in r.get('findings',[])))

    def test_last_ticket_finish_and_status_have_same_executable_batch_step(self):
        self.setup();output=json.loads(self.implement().stdout)
        status=json.loads(self.cli('batch','status','--topic','feature').stdout)
        self.assertEqual(status['next_command'],output['next_command'])
        self.assertIn('batch test',output['next_command'])
        import shlex
        self.cli(*shlex.split(output['next_command'])[1:])
        self.review();closed=json.loads(self.cli('batch','close','--topic','feature').stdout)
        self.assertIn('topic complete',closed['next_command'])

    def test_interrupted_batch_run_invalidates_prior_success(self):
        runner=self.repo/'full.py'
        runner.write_text("from pathlib import Path\nimport os,signal\nif Path('.agent/interrupt').exists():os.kill(os.getppid(),signal.SIGKILL)\n")
        self.git('add','full.py');self.git('commit','-qm','interruptible fixture')
        self.setup(full='python3 full.py');self.implement();self.review()
        self.assertIn('batch close',json.loads(self.cli('batch','status','--topic','feature').stdout)['next_command'])
        marker=self.repo/'.agent/interrupt';marker.touch()
        self.assertLess(self.cli('batch','test','--topic','feature',ok=False).returncode,0)
        self.assertIn('batch test',json.loads(self.cli('batch','status','--topic','feature').stdout)['next_command'])
        self.cli('batch','close','--topic','feature',ok=False)
        marker.unlink();self.cli('batch','test','--topic','feature');self.cli('batch','close','--topic','feature')

    def test_batch_self_advisory_is_frozen_and_requires_review_disposition(self):
        self.setup();self.cli('implement','start','--ticket','feature-01')
        (self.repo/'code.txt').write_text('implementation');self.cli('implement','test');self.self_review()
        notes=self.repo/'.agent/self.md';findings=self.repo/'.agent/findings.json'
        findings.write_text(json.dumps([dict(id='debt',severity='advisory',view='maintainability',
            summary='cleanup before batch close',location='code.txt:1',basis='contract needs clear names',disposition='fix-in-batch')]))
        self.cli('implement','self-review','--notes-file',str(notes),'--findings-file',str(findings))
        p=self.repo/'.agent/work/feature/tickets/tickets-feature-01.md';p.write_text(p.read_text().replace('- [ ]','- [x]'))
        self.cli('implement','finish');self.cli('batch','test','--topic','feature')
        report=json.loads(self.cli('batch','review','--topic','feature','--reviewer-model','host','--reviewer-session-id','fresh').stdout)
        manifest=json.loads(Path(report['manifest']).read_text())
        target='self:feature-01:debt';self.assertIn(target,manifest['coverage_targets'])
        result=json.loads(Path(report['result_file']).read_text())
        result.update(status='pass',reviewer=dict(provenance='independent',model='host'),findings=[],
            coverage=[dict(target=t,result='ok') for t in manifest['coverage_targets'] if t!=target])
        Path(report['result_file']).write_text(json.dumps(result))
        self.cli('batch','review','--topic','feature','--submit',report['result_file'],ok=False)
        result['coverage'].append(dict(target=target,result='ok'))
        Path(report['result_file']).write_text(json.dumps(result))
        self.cli('batch','review','--topic','feature','--submit',report['result_file'])
        self.cli('batch','close','--topic','feature')
        batch=batches.read(self.repo,'feature')['batches'][0]
        self.assertEqual('debt',batch['self_finding_resolutions'][0]['finding'])

    def test_definition_change_between_status_and_finish_is_rechecked(self):
        self.setup();self.cli('implement','start','--ticket','feature-01');self.cli('implement','test');self.self_review()
        p=self.repo/'.agent/work/feature/tickets/tickets-feature-01.md';p.write_text(p.read_text().replace('- [ ]','- [x]'))
        self.assertIn('implement finish',json.loads(self.cli('implement','status').stdout)['next_command'])
        p.write_text(p.read_text().replace('marker observed','different acceptance'))
        self.self_review()
        self.assertIn('definition',self.cli('implement','finish',ok=False).stderr)
        self.assertIn('--reopen',json.loads(self.cli('implement','status').stdout)['next_command'])

    def test_custom_partial_runner_assertion_is_not_swallowed_by_missing_phase(self):
        runner=self.repo/'full.py'
        self.setup(full='python3 -B -m full');self.implement()
        phases=[
            "subprocess.run([sys.executable,'-c',\"assert 1 == 2, 'actual regression'\"])",
            "subprocess.run([sys.executable,'-c',\"raise SystemExit('actual behavior regression')\"])",
            "subprocess.run(['sh','-c','echo actual behavior regression >&2; exit 1'])",
        ]
        for index,phase in enumerate(phases):
            with self.subTest(phase=phase):
                runner.write_text('import subprocess,sys\n'+phase+'\nimport outcome_missing_optional_phase\n')
                self.git('add','full.py');self.git('commit','-qm',f'actual behavior then optional phase {index}')
                current=json.loads(self.cli('batch','test','--topic','feature').stdout)
                self.assertTrue(current['new_failures']);self.assertFalse(current['results'][0]['unavailable'])
                self.cli('batch','close','--topic','feature',ok=False)

    def test_unrelated_reopen_preserves_correctness_and_legacy_singleton(self):
        self.setup();self.cli('implement','start','--ticket','feature-01');(self.repo/'code.txt').write_text('wrong')
        self.cli('implement','test');self.self_review()
        root=self.repo/'.agent/work/feature';record=root/'implementations/feature-01.json'
        unit=json.loads(record.read_text());unit.pop('self_reviews',None)
        unit['self_review']['findings']=[dict(id='unfixed',severity='blocking',view='correctness',
            summary='still wrong',location='code.txt:1',basis='real caller needs correct marker')]
        record.write_text(json.dumps(unit))
        spec=root/'specs/specs-feature-01.md';spec.write_text(spec.read_text()+'\nUnrelated wording.\n')
        self.cli('resolve','--ticket','feature-01','--reopen','--reason','approve unrelated wording')
        reopened=json.loads(record.read_text())
        self.assertTrue(any(f['id']=='unfixed' for r in reopened.get('self_reviews',[]) for f in r.get('findings',[])))
        self.cli('implement','test')
        self.cli('implement','self-review','--notes-file',str(self.repo/'.agent/self.md'),'--no-findings',ok=False)
        self.cli('implement','finish',ok=False)
        (self.repo/'code.txt').write_text('correct');self.cli('implement','test')
        self.cli('implement','self-review','--notes-file',str(self.repo/'.agent/self.md'),'--no-findings')
        p=root/'tickets/tickets-feature-01.md';p.write_text(p.read_text().replace('- [ ]','- [x]'))
        self.cli('implement','finish')

    def test_dirty_after_pass_without_findings_reports_content_input(self):
        self.setup();self.implement();self.review();(self.repo/'code.txt').write_text('unreviewed drift')
        status=json.loads(self.cli('batch','status','--topic','feature').stdout)
        self.assertIsNone(status['next_command']);self.assertTrue(status['inputs_needed'])
        human=self.cli('batch','status','--topic','feature','--human').stdout
        self.assertIn('恢复未审查的内容漂移',human)
        self.assertNotIn('请 batch repair',self.cli('batch','close','--topic','feature',ok=False).stderr)
        self.git('restore','code.txt')
        self.cli('batch','close','--topic','feature')

    def test_accepted_branch_status_does_not_repeat_closed_decision(self):
        self.setup(2);self.implement(1);self.implement(2);self.review()
        self.review(action='topic',finding=dict(id='branch-definition',severity='blocking',view='spec-challenge',
            summary='user definition conflict',location='Spec:behavior',basis='real caller conflicts'))
        accepted=json.loads(self.cli('batch','accept','--topic','feature','--reason','user accepts branch conflict').stdout)
        status=json.loads(self.cli('topic','status','--topic','feature').stdout)
        self.assertEqual(accepted['next_command'],status['next_command'])
        self.assertFalse(status['decisions_needed']);self.assertTrue(status['known_issues'])
        human=self.cli('topic','status','--topic','feature','--human').stdout
        self.assertNotIn('请用户决定修订 Spec',human)
        self.assertIn('已接受的历史原因',human)
        self.cli('topic','complete','--topic','feature')

    def test_accept_with_changed_definition_requires_reopen(self):
        self.setup();self.cli('implement','start','--ticket','feature-01');self.cli('implement','test');self.self_review()
        notes=self.repo/'.agent/self.md';findings=self.repo/'.agent/findings.json'
        findings.write_text(json.dumps([dict(id='challenge',severity='blocking',view='spec-challenge',
            summary='definition disagreement',location='Spec:behavior',basis='caller contradicts definition')]))
        self.cli('implement','self-review','--notes-file',str(notes),'--findings-file',str(findings))
        spec=self.repo/'.agent/work/feature/specs/specs-feature-01.md';spec.write_text(spec.read_text()+'\nApproved definition clarification.\n')
        self.cli('implement','test');self.cli('implement','self-review','--notes-file',str(notes))
        self.assertIn('definition',self.cli('resolve','--ticket','feature-01','--accept','--reason','accept challenge',ok=False).stderr)
        self.assertIn('--reopen',json.loads(self.cli('implement','status').stdout)['next_command'])

    def test_loader_only_missing_dependency_is_not_a_known_assertion_failure(self):
        for verbose in ('',' -v'):
            with self.subTest(verbose=verbose):
                if verbose:self.setUp()
                suite=self.repo/'suite';suite.mkdir();case=suite/'test_behavior.py'
                case.write_text('import outcome_missing_startup_dependency\n')
                self.git('add','suite');self.git('commit','-qm','loader startup dependency unavailable')
                self.setup(full='python3 -B -m unittest discover -s suite'+verbose);self.implement()
                baseline=json.loads((self.repo/'.agent/work/feature/test-baseline.json').read_text())
                self.assertFalse(baseline['results'][0]['unavailable'])
                self.assertFalse(baseline['results'][0]['comparison_eligible'])
                self.assertFalse(batches.execution_observed(baseline['results'][0]['output_tail']))
                pure=json.loads(self.cli('batch','test','--topic','feature').stdout)
                self.assertFalse(pure['results'][0]['unavailable'])
                self.assertEqual([],pure['new_failures']);self.assertTrue(pure['unverified'])
                self.review()  # Identical complete dependency diagnostics permit disclosed review.
                case.write_text("assert 1 == 2, 'actual behavior regression at import'\n")
                self.git('add','suite');self.git('commit','-qm','actual assertion with same loader identity')
                current=json.loads(self.cli('batch','test','--topic','feature').stdout)
                self.assertTrue(current['new_failures']);self.assertTrue(current['unverified'])
                self.assertFalse(current['results'][0]['unavailable']);self.assertFalse(current['known_failures'])
                status=json.loads(self.cli('batch','status','--topic','feature').stdout)
                self.assertTrue(status['unverified'])
                self.assertIn('模块载入失败',status['unverified'][0]['note'])
                self.cli('batch','close','--topic','feature',ok=False)

    def test_truncated_loader_legacy_baseline_does_not_hide_real_import_failure(self):
        for verbose in ('',' -v'):
            with self.subTest(verbose=verbose):
                if verbose:self.setUp()
                suite=self.repo/'suite';suite.mkdir()
                for number in range(12):
                    (suite/f'test_{number:02d}.py').write_text('import outcome_missing_tail_dependency\n')
                self.git('add','suite');self.git('commit','-qm','twelve unavailable loader modules')
                self.setup(full='python3 -B -m unittest discover -s suite'+verbose);self.implement()
                baseline_path=self.repo/'.agent/work/feature/test-baseline.json'
                baseline=json.loads(baseline_path.read_text());row=baseline['results'][0]
                self.assertEqual(12,len(row['failures']))
                self.assertLess(row['output_tail'].count('ERROR:'),12)
                pure=json.loads(self.cli('batch','test','--topic','feature').stdout)
                self.assertFalse(pure['results'][0]['unavailable']);self.assertFalse(pure['new_failures'])
                self.review()
                (suite/'test_00.py').write_text("assert False, 'actual import assertion with unchanged loader identity'\n")
                self.git('add','suite');self.git('commit','-qm','actual import regression')
                current=json.loads(self.cli('batch','test','--topic','feature').stdout)
                self.assertFalse(current['results'][0]['unavailable']);self.assertTrue(current['new_failures'])
                self.assertFalse(current['results'][0]['execution_observed'])
                for unavailable in (False,True):
                    with self.subTest(legacy_unavailable=unavailable):
                        legacy_baseline=json.loads(json.dumps(baseline));old=legacy_baseline['results'][0]
                        for field in ('comparison_eligible','execution_observed','output_complete','output_length','unavailable_loader_failures','dependency_proof_version'):
                            old.pop(field,None)
                        old['unavailable']=unavailable;baseline_path.write_text(json.dumps(legacy_baseline))
                        receipt=self.repo/'.agent/work/feature/batch-tests-01.json'
                        stale=json.loads(json.dumps(current))
                        for item in stale['results']:
                            for field in ('comparison_eligible','execution_observed','output_complete','output_length','unavailable_loader_failures','dependency_proof_version'):
                                item.pop(field,None)
                        stale.update(new_failures=[],known_failures=[dict(command=old['command'],failure=f) for f in old['failures']],unverified=[])
                        receipt.write_text(json.dumps(stale))
                        self.assertIn('新增失败',self.cli('batch','close','--topic','feature',ok=False).stderr)
                        rerun=json.loads(self.cli('batch','test','--topic','feature').stdout)
                        self.assertFalse(rerun['results'][0]['unavailable'])
                        self.assertTrue(rerun['new_failures']);self.assertTrue(rerun['unverified'])
                        self.assertIn('新增失败',self.cli('batch','review','--topic','feature','--reviewer-model','host','--reviewer-session-id','fresh-context',ok=False).stderr)
                baseline_path.write_text(json.dumps(baseline))
                self.assertFalse(row['execution_observed']);self.assertFalse(row['output_complete'])
                self.assertGreater(row['output_length'],len(row['output_tail']))

    def test_truncated_partial_legacy_preserves_real_known_case_difference(self):
        for verbose in ('',' -v'):
            with self.subTest(verbose=verbose):
                if verbose:self.setUp()
                suite=self.repo/'suite';suite.mkdir()
                for number in range(12):
                    (suite/f'test_{number:02d}.py').write_text('import outcome_missing_partial_tail_dependency\n')
                behavior=suite/'test_behavior.py'
                behavior.write_text('import unittest\nclass Behavior(unittest.TestCase):\n def test_known(self): self.assertEqual(1, 2)\n def test_new(self): self.assertEqual(3, 3)\n')
                self.git('add','suite');self.git('commit','-qm','twelve loader gaps and real behavior cases')
                self.setup(full='python3 -B -m unittest discover -s suite'+verbose);self.implement()
                baseline_path=self.repo/'.agent/work/feature/test-baseline.json'
                baseline=json.loads(baseline_path.read_text());row=baseline['results'][0]
                self.assertTrue(row['execution_observed']);self.assertFalse(row['output_complete'])
                self.assertEqual(13,len(row['failures']))
                self.assertEqual(12,len(row['unavailable_loader_failures']))
                self.review()  # Known executed failure plus unchanged loader gaps remain reviewable.
                behavior.write_text(behavior.read_text().replace('assertEqual(3, 3)','assertEqual(3, 4)'))
                self.git('add','suite');self.git('commit','-qm','new real behavior failure')
                for unavailable in (False,True):
                    with self.subTest(legacy_unavailable=unavailable):
                        legacy_baseline=json.loads(json.dumps(baseline));old=legacy_baseline['results'][0]
                        for field in ('comparison_eligible','execution_observed','output_complete','output_length','unavailable_loader_failures','dependency_proof_version'):
                            old.pop(field,None)
                        old['unavailable']=unavailable;baseline_path.write_text(json.dumps(legacy_baseline))
                        current=json.loads(self.cli('batch','test','--topic','feature').stdout)
                        self.assertTrue(current['results'][0]['execution_observed'])
                        self.assertFalse(current['results'][0]['unavailable']);self.assertTrue(current['unverified'])
                        self.assertEqual(13,len(current['new_failures']))
                        self.assertTrue(any('test_new' in f['failure'] for f in current['new_failures']))
                        self.assertEqual(1,len(current['known_failures']))
                        self.assertTrue(any('test_known' in f['failure'] for f in current['known_failures']))
                        self.assertIn('新增失败',self.cli('batch','close','--topic','feature',ok=False).stderr)

    def test_duplicate_loader_identity_requires_all_blocks_to_be_environment_gaps(self):
        for verbose in ('',' -v'):
            with self.subTest(verbose=verbose):
                if verbose:self.setUp()
                runner=self.repo/'runner.py'
                runner.write_text("import pathlib, sys, traceback, unittest\nfrom unittest.loader import _FailedTest\ndef failed(real):\n try:\n  if real: assert False, 'actual duplicate loader assertion'\n  import outcome_missing_duplicate_dependency\n except Exception:\n  return _FailedTest('same', ImportError('Failed to import test module: same\\n'+traceback.format_exc()))\nclass Behavior(unittest.TestCase):\n def test_ok(self): self.assertTrue(True)\nreal=pathlib.Path('mode.txt').read_text()=='bad'\nsuite=unittest.TestSuite([failed(real), failed(False), Behavior('test_ok')])\nresult=unittest.TextTestRunner(verbosity=2 if '-v' in sys.argv else 1).run(suite)\nraise SystemExit(not result.wasSuccessful())\n")
                mode=self.repo/'mode.txt';mode.write_text('good')
                self.git('add','runner.py','mode.txt');self.git('commit','-qm','duplicate pure loader failures with executed test')
                self.setup(full='python3 -B runner.py'+verbose);self.implement()
                baseline=json.loads((self.repo/'.agent/work/feature/test-baseline.json').read_text())
                self.assertTrue(baseline['results'][0]['execution_observed'])
                self.assertTrue(baseline['results'][0]['unavailable_loader_failures'])
                self.review()
                mode.write_text('bad');self.git('add','mode.txt');self.git('commit','-qm','real duplicate block before pure environment block')
                current=json.loads(self.cli('batch','test','--topic','feature').stdout)
                self.assertFalse(current['results'][0]['unavailable'])
                self.assertEqual([],current['results'][0]['unavailable_loader_failures'])
                self.assertTrue(current['new_failures']);self.assertFalse(current['known_failures'])
                self.assertIn('新增失败',self.cli('batch','close','--topic','feature',ok=False).stderr)

    def test_concise_loader_exceptions_are_not_dependency_proof(self):
        for verbose in ('',' -v'):
            with self.subTest(verbose=verbose):
                if verbose:self.setUp()
                runner=self.repo/'runner.py'
                runner.write_text("import pathlib, sys, traceback, unittest\nfrom unittest.loader import _FailedTest\ndef failed(kind):\n try:\n  if kind=='assertion': assert False, \"No module named 'actual_behavior_condition'\"\n  if kind=='runtime': raise RuntimeError(\"No module named 'actual_behavior_condition'\")\n  import outcome_missing_concise_dependency\n except Exception as exc:\n  detail=traceback.format_exc() if kind=='missing' else ''.join(traceback.format_exception_only(exc))\n  return _FailedTest('same', ImportError('Failed to import test module: same\\n'+detail))\nclass Behavior(unittest.TestCase):\n def test_ok(self): self.assertTrue(True)\nsuite=unittest.TestSuite([failed(pathlib.Path('mode.txt').read_text()), failed('missing'), Behavior('test_ok')])\nresult=unittest.TextTestRunner(verbosity=2 if '-v' in sys.argv else 1).run(suite)\nraise SystemExit(not result.wasSuccessful())\n")
                mode=self.repo/'mode.txt';mode.write_text('missing')
                self.git('add','runner.py','mode.txt');self.git('commit','-qm','typed loader dependency gaps')
                self.setup(full='python3 -B runner.py'+verbose);self.implement()
                mode.write_text('module-only');self.git('add','mode.txt');self.git('commit','-qm','actual ModuleNotFoundError exception-only control')
                pure=json.loads(self.cli('batch','test','--topic','feature').stdout)
                self.assertFalse(pure['results'][0]['unavailable']);self.assertTrue(pure['new_failures'])
                self.assertTrue(pure['results'][0]['unavailable_loader_failures'])
                self.assertFalse(pure['known_failures'])  # Changed/truncated diagnostic cannot borrow the module identity.
                for kind in ('assertion','runtime'):
                    with self.subTest(exception=kind):
                        mode.write_text(kind);self.git('add','mode.txt');self.git('commit','-qm','actual exception-only behavior failure '+kind)
                        current=json.loads(self.cli('batch','test','--topic','feature').stdout)
                        with self.subTest(fresh_classification=kind):
                            self.assertFalse(current['results'][0]['unavailable'])
                            self.assertTrue(current['new_failures']);self.assertFalse(current['known_failures'])
                            self.assertEqual([],current['results'][0]['unavailable_loader_failures'])
                        receipt=self.repo/'.agent/work/feature/batch-tests-01.json'
                        old=json.loads(json.dumps(current));old['results'][0].pop('dependency_proof_version',None)
                        old['results'][0]['unavailable_loader_failures']=old['results'][0]['failures']
                        old.update(new_failures=[],known_failures=[dict(command=old['commands'][0],failure=f) for f in old['results'][0]['failures']],unverified=[])
                        receipt.write_text(json.dumps(old))
                        self.assertIn('batch test',json.loads(self.cli('batch','status','--topic','feature').stdout)['next_command'])
                        self.assertIn('新增失败',self.cli('batch','close','--topic','feature',ok=False).stderr)

    def test_direct_concise_exception_and_old_unavailable_cache_require_rerun(self):
        runner=self.repo/'runner.py'
        self.setup(full='python3 -B -m runner');self.implement()
        runner.write_text("import pathlib, sys, traceback\ntry:\n kind=pathlib.Path('mode.txt').read_text()\n if kind=='assertion': assert False, \"No module named 'actual_behavior_condition'\"\n if kind=='runtime': raise RuntimeError(\"No module named 'actual_behavior_condition'\")\n import outcome_missing_direct_concise_dependency\nexcept Exception as exc:\n sys.stderr.write(''.join(traceback.format_exception_only(exc)))\n raise SystemExit(1)\n")
        mode=self.repo/'mode.txt';mode.write_text('missing')
        self.git('add','runner.py','mode.txt');self.git('commit','-qm','actual exception-only missing dependency')
        pure=json.loads(self.cli('batch','test','--topic','feature').stdout)
        self.assertFalse(pure['results'][0]['unavailable']);self.assertTrue(pure['new_failures']);self.assertTrue(pure['unverified'])
        self.cli('batch','review','--topic','feature',ok=False)
        for kind in ('assertion','runtime'):
            with self.subTest(exception=kind):
                mode.write_text(kind);self.git('add','mode.txt');self.git('commit','-qm','actual direct concise failure '+kind)
                current=json.loads(self.cli('batch','test','--topic','feature').stdout)
                with self.subTest(fresh_classification=kind):
                    self.assertFalse(current['results'][0]['unavailable']);self.assertTrue(current['new_failures'])
                receipt=self.repo/'.agent/work/feature/batch-tests-01.json'
                old=json.loads(json.dumps(current));old['results'][0].pop('dependency_proof_version',None)
                old['results'][0]['unavailable']=True
                old.update(new_failures=[],known_failures=[],unverified=[]);receipt.write_text(json.dumps(old))
                self.assertIn('batch test',json.loads(self.cli('batch','status','--topic','feature').stdout)['next_command'])
                self.assertIn('新增失败',self.cli('batch','close','--topic','feature',ok=False).stderr)
                self.assertFalse(json.loads(self.cli('batch','test','--topic','feature').stdout)['results'][0]['unavailable'])

    def test_python_module_startup_gap_and_legacy_receipt_remain_disclosed(self):
        for module in ('outcome_missing_python_module','outcome_missing_python_module.nested'):
            with self.subTest(module=module):
                if module.endswith('.nested'):self.setUp()
                self.setup(full='python3 -B -m '+module);self.implement()
                pure=json.loads(self.cli('batch','test','--topic','feature').stdout)
                self.assertTrue(pure['results'][0]['unavailable']);self.assertFalse(pure['new_failures']);self.assertTrue(pure['unverified'])
                self.review()
                receipt=self.repo/'.agent/work/feature/batch-tests-01.json';old=json.loads(receipt.read_text())
                for version in (None,1):
                    old['results'][0]['dependency_proof_version']=version;receipt.write_text(json.dumps(old))
                    self.assertIn('batch close',json.loads(self.cli('batch','status','--topic','feature').stdout)['next_command'])
                self.cli('batch','close','--topic','feature')

    def test_partial_loader_identity_cannot_hide_new_import_assertion(self):
        for verbose in ('',' -v'):
            with self.subTest(verbose=verbose):
                if verbose:self.setUp()
                suite=self.repo/'suite';suite.mkdir()
                (suite/'test_ok.py').write_text('import unittest\nclass Behavior(unittest.TestCase):\n def test_ok(self): self.assertEqual(1, 1)\n')
                missing=suite/'test_missing.py';missing.write_text('import outcome_missing_partial_dependency\n')
                self.git('add','suite');self.git('commit','-qm','one real passing test and one loader gap')
                self.setup(full='python3 -B -m unittest discover -s suite'+verbose);self.implement()
                baseline=json.loads((self.repo/'.agent/work/feature/test-baseline.json').read_text())
                self.assertFalse(baseline['results'][0]['unavailable']);self.assertTrue(baseline['results'][0]['comparison_eligible'])
                self.assertTrue(baseline['results'][0]['execution_observed'])
                self.review()
                missing.write_text("assert False, 'new actual import behavior regression'\n")
                self.git('add','suite');self.git('commit','-qm','same loader identity now real failure')
                current=json.loads(self.cli('batch','test','--topic','feature').stdout)
                self.assertFalse(current['results'][0]['unavailable'])
                self.assertTrue(current['new_failures']);self.assertFalse(current['known_failures'])
                self.assertTrue(current['unverified'])
                self.assertIn('新增失败',self.cli('batch','close','--topic','feature',ok=False).stderr)

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
