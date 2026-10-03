"""Legacy active-state recovery through the real CLI; completed records stay immutable."""
import json
from pathlib import Path
import shlex
import unittest
import test_batches as batch_seam
import test_topic_branch as branch_seam
from tools.workflow_lib import batches, topic_service


class HolisticStateRepairs(unittest.TestCase):
    setUp = batch_seam.BatchTests.setUp
    git = batch_seam.BatchTests.git
    cli = batch_seam.BatchTests.cli
    setup_config = batch_seam.BatchTests.setup_config
    ticket = batch_seam.BatchTests.ticket
    setup = batch_seam.BatchTests.setup
    self_review = batch_seam.BatchTests.self_review
    implement = batch_seam.BatchTests.implement
    review = batch_seam.BatchTests.review

    def legacy(self, views):
        full="python3 -c \"from pathlib import Path; raise SystemExit(0 if Path('code.txt').read_text() == 'fixed output\\n' else 1)\"" if 'correctness' in views else "python3 -c 'pass'"
        self.setup(full=full);self.implement()
        path=self.repo/'.agent/work/feature/implementations/feature-01.json'
        unit=json.loads(path.read_text())
        unit['self_review']['findings']=[dict(id=f'old-{index}',severity='blocking',view=view,
            summary='legacy discovery',location='code.txt:1',basis='caller requires fixed output')
            for index,view in enumerate(views)]
        unit['self_reviews']=[unit['self_review']]
        path.write_text(json.dumps(unit))
        return path,path.read_bytes()

    def open_review(self):
        self.cli('batch','test','--topic','feature')
        report=json.loads(self.cli('batch','review','--topic','feature','--reviewer-model','host','--reviewer-session-id','fresh').stdout)
        manifest=json.loads(Path(report['manifest']).read_text())
        return report,manifest

    def submit(self,report,manifest,findings=(),ok=True):
        result=json.loads(Path(report['result_file']).read_text())
        result.update(status='findings' if findings else 'pass',reviewer=dict(provenance='independent',model='host'),
            coverage=[dict(target=t,result='ok') for t in manifest['coverage_targets']],findings=list(findings))
        Path(report['result_file']).write_text(json.dumps(result))
        return self.cli('batch','review','--topic','feature','--submit',report['result_file'],ok=ok)

    def repair(self,target='self:feature-01:old-0'):
        (self.repo/'code.txt').write_text('fixed output\n')
        notes=self.repo/'.agent/repair.md';notes.write_text(target+': corrected actual caller output')
        status=json.loads(self.cli('batch','status','--topic','feature').stdout)
        self.assertIn('batch repair',status['next_command'])
        self.cli('batch','repair','--topic','feature','--notes-file',str(notes))

    def test_legacy_blocking_requires_content_repair_and_current_review(self):
        record,before=self.legacy(['correctness'])
        report,manifest=self.open_review()
        self.assertEqual('self:feature-01:old-0',manifest['self_findings'][0]['target'])
        self.assertIn('实际 batch repair',self.submit(report,manifest,ok=False).stderr)
        self.cli('batch','close','--topic','feature',ok=False)
        self.repair();self.cli('batch','close','--topic','feature',ok=False)
        self.review();self.cli('batch','close','--topic','feature')
        self.assertEqual([],batches.self_observations(self.repo,'feature',['feature-01']))
        self.assertEqual(before,record.read_bytes())
        self.cli('topic','complete','--topic','feature')

    def test_repaired_discovery_survives_optional_branch_review_and_topic_close(self):
        self.setup(count=2);self.implement(1);self.implement(2)
        path=self.repo/'.agent/work/feature/implementations/feature-01.json'
        unit=json.loads(path.read_text())
        unit['self_review']['findings']=[dict(id='old-0',severity='blocking',view='correctness',
            summary='legacy caller bug',location='code.txt:1',basis='output wrong')]
        unit['self_reviews']=[unit['self_review']];path.write_text(json.dumps(unit));before=path.read_bytes()
        self.repair();self.review();self.review(action='topic')
        self.cli('batch','close','--topic','feature');self.cli('topic','complete','--topic','feature')
        self.assertEqual(before,(self.repo/'.agent/archive/feature/implementations/feature-01.json').read_bytes())

    def test_legacy_challenges_reopen_only_named_target(self):
        record,before=self.legacy(['spec-challenge','spec-challenge'])
        report,manifest=self.open_review()
        self.submit(report,manifest,ok=False)
        spec=self.repo/'.agent/work/feature/specs/specs-feature-01.md'
        spec.write_text(spec.read_text()+'\nUser clarified both contracts.\n')
        self.cli('batch','reopen','--topic','feature','--reason','self:feature-01:old-0: revised first contract')
        status=json.loads(self.cli('batch','status','--topic','feature').stdout)
        self.assertEqual(['self:feature-01:old-1'],[x['target'] for x in status['decisions_needed']])
        report,manifest=self.open_review();self.submit(report,manifest,ok=False)
        spec.write_text(spec.read_text()+'\nSecond contract decision.\n')
        self.cli('batch','reopen','--topic','feature','--reason','self:feature-01:old-1: revised second contract')
        self.review();self.cli('batch','close','--topic','feature')
        self.assertEqual([],batches.self_observations(self.repo,'feature',['feature-01']))
        self.assertEqual(before,record.read_bytes())
        self.cli('topic','complete','--topic','feature')

    def test_legacy_challenge_accept_is_named_and_disclosed(self):
        record,before=self.legacy(['spec-challenge'])
        self.cli('batch','test','--topic','feature')
        self.cli('batch','accept','--topic','feature','--reason','accept all',ok=False)
        status=json.loads(self.cli('batch','status','--topic','feature').stdout)
        self.assertIn('batch accept',status['next_command'])
        self.cli('batch','accept','--topic','feature','--reason','self:feature-01:old-0: user accepts existing semantics')
        self.assertEqual(before,record.read_bytes())
        summary=self.repo/'.agent/work/feature/deliveries/deliveries-feature-01.md'
        self.assertIn('legacy discovery',summary.read_text())
        self.cli('topic','complete','--topic','feature')

    def test_mixed_challenge_accept_cannot_waive_correctness(self):
        record,before=self.legacy(['correctness','spec-challenge'])
        self.cli('batch','test','--topic','feature')
        reason='self:feature-01:old-1: user accepts definition conflict'
        self.cli('batch','accept','--topic','feature','--reason',reason,ok=False)
        self.repair();self.cli('batch','test','--topic','feature')
        self.cli('batch','accept','--topic','feature','--reason',reason,ok=False)
        report,manifest=self.open_review()
        challenge=manifest['self_findings'][1]['finding']
        self.submit(report,manifest,[manifest['self_findings'][0]['finding']])
        self.cli('batch','accept','--topic','feature','--reason',reason,ok=False)
        report,manifest=self.open_review()
        self.submit(report,manifest,[challenge])
        self.cli('batch','accept','--topic','feature','--reason',reason)
        self.assertEqual([],batches.self_observations(self.repo,'feature',['feature-01']))
        self.assertEqual(before,record.read_bytes())
        self.cli('topic','complete','--topic','feature')


class HolisticBranchGeometry(unittest.TestCase):
    setUp = branch_seam.BranchTests.setUp
    git = branch_seam.BranchTests.git
    cli = branch_seam.BranchTests.cli
    setup_config = branch_seam.BranchTests.setup_config
    ticket = branch_seam.BranchTests.ticket
    replace = branch_seam.BranchTests.replace
    review = branch_seam.BranchTests.review
    result = branch_seam.BranchTests.result
    submit = branch_seam.BranchTests.submit
    approve = branch_seam.BranchTests.approve
    summary = branch_seam.BranchTests.summary
    multi = branch_seam.BranchTests.multi
    branch_review = branch_seam.BranchTests.branch_review
    branch_submit = branch_seam.BranchTests.branch_submit

    def test_status_recovers_only_current_pass_and_next_command_executes(self):
        self.multi();self.cli('topic','test')
        self.branch_submit(self.result(self.branch_review()))
        path=self.repo/'.agent/work/feature/branch-review.json'
        unit=json.loads(path.read_text());unit.update(status='needs-user',stop_reason='体积膨胀：legacy limit')
        path.write_text(json.dumps(unit))
        status=json.loads(self.cli('topic','status').stdout)
        self.assertEqual('reviewing',status['branch_review']['status'])
        self.assertIn('topic complete',status['next_command'])
        self.assertTrue(json.loads(path.read_text())['recoveries'])
        self.cli(*shlex.split(status['next_command'])[1:])

    def test_status_preserves_geometric_stop_without_current_pass(self):
        self.multi();self.cli('topic','test');self.branch_review()
        path=self.repo/'.agent/work/feature/branch-review.json'
        unit=json.loads(path.read_text());unit.update(status='needs-user',stop_reason='体积膨胀：legacy limit')
        path.write_text(json.dumps(unit))
        status=json.loads(self.cli('topic','status').stdout)
        self.assertEqual('needs-user',status['branch_review']['status'])
        self.cli('topic','complete',ok=False)

    def test_status_preserves_geometric_stop_with_stale_pass(self):
        self.multi();self.cli('topic','test')
        self.branch_submit(self.result(self.branch_review()))
        path=self.repo/'.agent/work/feature/branch-review.json'
        unit=json.loads(path.read_text());unit.update(status='needs-user',stop_reason='体积膨胀：legacy limit')
        path.write_text(json.dumps(unit))
        (self.repo/'code.txt').write_text('unreviewed output\n')
        self.git('add','code.txt');self.git('commit','-qm','unreviewed content')
        status=json.loads(self.cli('topic','status').stdout)
        self.assertEqual('needs-user',status['branch_review']['status'])
        self.assertNotIn('recoveries',json.loads(path.read_text()))
        self.cli('topic','complete',ok=False)
