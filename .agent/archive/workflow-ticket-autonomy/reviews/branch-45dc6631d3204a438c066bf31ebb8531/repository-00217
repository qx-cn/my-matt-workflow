"""Public CLI regressions for the two historical completion-review defects."""
import json
from pathlib import Path
import unittest
import test_batches as batch_cases


class CompletionCompensationTests(unittest.TestCase):
    def fixture(self, count=1):
        case=batch_cases.BatchTests('test_clean_three_ticket_batch_one_dispatch_and_topic_completion')
        case.setUp()
        self.addCleanup(case.doCleanups)
        case.setup(count)
        return case

    def gitlink(self, case):
        child=case.repo/'module';child.mkdir()
        case.git('init','-q','--initial-branch=main',cwd=child)
        case.git('config','user.name','Test',cwd=child)
        case.git('config','user.email','test@example.invalid',cwd=child)
        (child/'consumer.txt').write_text('baseline consumer\n')
        case.git('add','consumer.txt',cwd=child);case.git('commit','-qm','module baseline',cwd=child)
        (case.repo/'.gitmodules').write_text('[submodule "module"]\n\tpath = module\n\turl = ../module-origin\n')
        case.git('add','.gitmodules','module');case.git('commit','-qm','existing gitlink')
        return child,case.git('rev-parse','HEAD',cwd=child)

    def assert_pointer(self, report, oid):
        manifest=json.loads(Path(report['manifest']).read_text())
        link=next(entry for entry in manifest['repository'] if entry['path']=='module')
        self.assertEqual('160000',link['mode'])
        self.assertEqual(f'Subproject commit {oid}\n',Path(link['snapshot_path']).read_text())
        self.assertNotIn('module',{change['path'] for change in manifest['changes']})

    def submit(self, case, report, command):
        manifest=json.loads(Path(report['manifest']).read_text())
        result=json.loads(Path(report['result_file']).read_text())
        result.update(status='pass',reviewer={'provenance':'independent','model':'host'},
                      coverage=[{'target':target,'result':'ok'} for target in manifest['coverage_targets']],findings=[])
        Path(report['result_file']).write_text(json.dumps(result))
        case.cli(*command,'--submit',report['result_file'])

    def test_unchanged_gitlink_batch_and_optional_branch_can_close(self):
        case=self.fixture(2);_,oid=self.gitlink(case)
        case.implement(1);case.implement(2)
        batch=case.review();self.assert_pointer(batch,oid)
        branch=case.review('topic');self.assert_pointer(branch,oid)
        case.cli('batch','close','--topic','feature')
        case.summary('feature');case.cli('topic','complete','--topic','feature')
        self.assertTrue((case.repo/'.agent/archive/feature').is_dir())

    def restore_legacy(self, case):
        from tools.workflow_lib import ticket_implementation as impl, topic_service as topics
        root=case.repo/'.agent/work/feature'
        ticket=root/'tickets/tickets-feature-01.md'
        case.replace(ticket,'status','needs-user')
        fixture=Path(__file__).parent/'fixtures/workflow_simplification/v2_needs_user.json'
        unit=json.loads(fixture.read_text())['implementation']
        unit.update(baseline=case.git('rev-parse','HEAD'),definition=impl.definition(case.repo,ticket))
        (root/'implementations').mkdir()
        (root/'implementations/feature-01.json').write_text(json.dumps(unit))
        (root/topics.STATE_FILE).write_text(json.dumps(dict(status='active',level='standard',
            baseline=unit['baseline'],started_at=unit['started_at'],implementation_started=True,test_runs=0)))
        return root

    def test_restored_v2_stop_has_ticket_reason_and_executable_next_step(self):
        case=self.fixture();self.restore_legacy(case)
        report=json.loads(case.cli('topic','status','--topic','feature').stdout)
        self.assertEqual([dict(ticket='feature-01',status='needs-user',stop_reason='inconclusive')],report['tickets'])
        self.assertEqual('feature-01',report['decisions_needed'][0]['ticket'])
        self.assertEqual(json.loads(case.cli('implement','status','--ticket','feature-01').stdout)['next_command'],report['next_command'])
        self.assertIn('implement test',report['next_command'])
        human=case.cli('topic','status','--topic','feature','--human').stdout
        self.assertIn('feature-01',human);self.assertIn('证据不足',human)
        self.assertNotIn('inconclusive',human);self.assertNotIn('needs-user',human)
        case.cli('implement','test','--ticket','feature-01')
        ready=json.loads(case.cli('topic','status','--topic','feature').stdout)
        self.assertIn('resolve',ready['next_command']);self.assertIn('--accept',ready['next_command'])
        case.cli('resolve','--ticket','feature-01','--accept','--reason','user accepts stated evidence gap')
        self.assertEqual('complete',json.loads(case.cli('topic','status','--topic','feature').stdout)['tickets'][0]['status'])

    def test_gitlink_high_risk_requires_own_batch_review(self):
        case=self.fixture();_,oid=self.gitlink(case)
        case.cli('implement','start','--ticket','feature-01');case.cli('implement','test');case.self_review()
        report=json.loads(case.cli('implement','review','--ticket','feature-01','--reviewer-model','host',
            '--reviewer-session-id','fresh','--reason','persistent contract').stdout)
        self.assert_pointer(report,oid)
        self.submit(case,report,('implement','review','--ticket','feature-01'))
        ticket=case.repo/'.agent/work/feature/tickets/tickets-feature-01.md'
        ticket.write_text(ticket.read_text().replace('- [ ]','- [x]'))
        case.cli('implement','finish');case.cli('batch','test','--topic','feature')
        case.cli('batch','close','--topic','feature',ok=False)
        self.assert_pointer(case.review(),oid);case.cli('batch','close','--topic','feature')

    def test_gitlink_new_commit_invalidates_tests_and_review_and_dirty_child_rejected(self):
        case=self.fixture();child,oid=self.gitlink(case)
        case.cli('implement','start','--ticket','feature-01');case.cli('implement','test');case.self_review()
        (child/'consumer.txt').write_text('different consumer\n')
        case.git('add','consumer.txt',cwd=child);case.git('commit','-qm','changed child',cwd=child)
        self.assertNotEqual(oid,case.git('rev-parse','HEAD',cwd=child))
        self.assertFalse(json.loads(case.cli('implement','status').stdout)['tests_passed'])
        case.cli('implement','finish',ok=False)
        case.cli('implement','test');case.self_review()
        ticket=case.repo/'.agent/work/feature/tickets/tickets-feature-01.md'
        ticket.write_text(ticket.read_text().replace('- [ ]','- [x]'))
        case.cli('implement','finish');case.review()
        (child/'consumer.txt').write_text('new review drift\n')
        case.git('add','consumer.txt',cwd=child);case.git('commit','-qm','unreviewed child',cwd=child)
        case.cli('batch','close','--topic','feature',ok=False)
        (child/'untracked.txt').write_text('not bound to commit')
        blocked=case.cli('batch','review','--topic','feature','--reviewer-model','host','--reviewer-session-id','fresh',ok=False)
        self.assertIn('未绑定到 commit',blocked.stderr)
        case.cli('batch','test','--topic','feature',ok=False)
        (child/'untracked.txt').unlink()
        case.git('add','module');case.git('commit','-qm','bind new child')
        self.assertEqual('160000',next(e for e in json.loads(Path(case.review()['manifest']).read_text())['repository'] if e['path']=='module')['mode'])
        case.cli('batch','close','--topic','feature')

    def test_archived_stopped_history_is_visible_without_new_decision(self):
        case=self.fixture();root=self.restore_legacy(case)
        case.cli('topic','abandon','--topic','feature','--reason','user drops stopped work')
        report=json.loads(case.cli('topic','status','--topic','feature').stdout)
        self.assertEqual('archived',report['status'])
        self.assertEqual('needs-user',report['tickets'][0]['status'])
        self.assertEqual([],report['decisions_needed']);self.assertIsNone(report['next_command'])
        self.assertIn('已归档',case.cli('topic','status','--topic','feature','--human').stdout)

    def test_document_and_batch_recovery_priorities_remain(self):
        case=self.fixture()
        docs=case.repo/'.agent/work/docs';docs.mkdir();(docs/'note.md').write_text('documentation')
        report=json.loads(case.cli('topic','status','--topic','docs').stdout)
        self.assertEqual([],report['tickets']);self.assertEqual([],report['decisions_needed'])
        self.assertIn('topic complete',report['next_command'])
        case.cli('implement','start','--ticket','feature-01')
        report=json.loads(case.cli('topic','status','--topic','feature').stdout)
        self.assertEqual('implementing',report['tickets'][0]['status'])
        self.assertEqual(json.loads(case.cli('batch','status','--topic','feature').stdout)['next_command'],report['next_command'])

    def test_missing_legacy_record_reports_diagnostic_instead_of_completion(self):
        case=self.fixture();root=self.restore_legacy(case)
        (root/'implementations/feature-01.json').unlink()
        report=json.loads(case.cli('topic','status','--topic','feature').stdout)
        self.assertIn('implement status',report['next_command'])
        self.assertIn('缺少新实施记录',report['tickets'][0]['recovery_error'])

    def test_accepted_legacy_ticket_resumes_ready_successor(self):
        case=self.fixture(2);self.restore_legacy(case)
        case.cli('implement','test','--ticket','feature-01')
        case.cli('resolve','--ticket','feature-01','--accept','--reason','user accepts evidence gap')
        report=json.loads(case.cli('topic','status','--topic','feature').stdout)
        self.assertEqual(['complete','ready-for-agent'],[ticket['status'] for ticket in report['tickets']])
        self.assertIn('implement start',report['next_command']);self.assertIn('--ticket feature-02',report['next_command'])
        case.cli('implement','start','--ticket','feature-02')
        self.assertIn('implement test',json.loads(case.cli('topic','status','--topic','feature').stdout)['next_command'])

    def test_batch_human_status_accepts_ticket_id_list(self):
        case=self.fixture();case.cli('implement','start','--ticket','feature-01')
        human=case.cli('batch','status','--topic','feature','--human').stdout
        self.assertIn('feature-01',human);self.assertIn('实施中',human)
        self.assertNotIn('open',human)
