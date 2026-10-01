"""Whole-Topic tests, review, decisions and archival through the public CLI."""
import json
from pathlib import Path
import unittest
import test_implement_finish as finish
import test_review_resolution as resolution
import test_topic_lifecycle as topics


class BranchTests(unittest.TestCase):
    setUp = finish.FinishTests.setUp
    git = finish.FinishTests.git
    cli = finish.FinishTests.cli
    setup_config = finish.FinishTests.setup_config
    ticket = finish.FinishTests.ticket
    replace = finish.FinishTests.replace
    review = finish.FinishTests.review
    result = finish.FinishTests.result
    submit = finish.FinishTests.submit
    approve = finish.FinishTests.approve
    summary = topics.TopicLifecycleTests.summary
    blocking = resolution.ResolutionTests.blocking

    def multi(self, mode='shared', command="python3 -c 'print(\"full test\")'"):
        self.setup_config(mode, tests=(command, "python3 -c *", "python3 -c 'pass'"))
        self.ticket()
        self.ticket(number=2, dependencies=('feature-01',))
        baseline = self.git('rev-parse', 'HEAD')
        self.cli('implement', 'start', '--ticket', 'feature-01')
        (self.repo / 'code.txt').write_text('first')
        self.cli('implement', 'test')
        self.approve()
        self.cli('implement', 'finish')
        self.cli('implement', 'start', '--ticket', 'feature-02')
        (self.repo / 'code.txt').write_text('second')
        self.cli('implement', 'test')
        report = json.loads(self.cli('implement', 'review', '--reviewer-model', 'actual-host-model').stdout)
        path = self.repo / '.agent/result.json'
        path.write_text(json.dumps(self.result(report)))
        self.cli('implement', 'review', '--submit', str(path))
        ticket = self.repo / '.agent/work/feature/tickets/tickets-feature-02.md'
        ticket.write_text(ticket.read_text().replace('- [ ]', '- [x]'))
        self.cli('implement', 'finish')
        self.summary('feature')
        return baseline

    def branch_review(self):
        return json.loads(self.cli('topic', 'review', '--reviewer-model', 'actual-host-model').stdout)

    def branch_submit(self, result, ok=True):
        path = self.repo / '.agent/branch-result.json'
        path.write_text(json.dumps(result))
        return self.cli('topic', 'review', '--submit', str(path), ok=ok)

    def test_advisory_spec_challenge_is_visible_and_preserved_after_acceptance(self):
        self.multi()
        self.cli('topic','test')
        report = self.branch_review()
        finding = dict(id='challenge',severity='advisory',view='spec-challenge',summary='existing caller conflicts',
                       location='Spec:behavior',basis='public caller reaches failure',disposition='defer',owner='user')
        self.branch_submit(self.result(report,status='findings',findings=[finding]))
        status = json.loads(self.cli('topic','status').stdout)
        self.assertEqual(finding,status['decisions_needed'][0]['finding'])
        self.assertIn(finding,status['advisories'])
        self.cli('resolve','--branch','--accept','--reason','accept stated conflict')
        summary=(self.repo/'.agent/archive/feature/deliveries/deliveries-feature-01.md').read_text()
        self.assertIn('existing caller conflicts',summary)
        self.assertIn('public caller reaches failure',summary)
        self.assertEqual([], json.loads(self.cli('topic','status','--topic','feature').stdout)['decisions_needed'])

    def test_accept_unsubmitted_branch_reviews_in_both_modes(self):
        for mode in ('shared', 'private'):
            with self.subTest(mode=mode):
                self.setUp()
                baseline = self.multi(mode)
                for _ in range(4):
                    if _ == 0:
                        self.cli('topic', 'test')
                    self.branch_review()
                self.cli('topic', 'review', '--reviewer-model', 'actual-host-model', ok=False)
                self.assertIn('needs-user', self.cli('topic', 'status').stdout)
                self.cli('resolve', '--branch', '--accept', '--reason', 'interrupted branch')
                archive = self.repo / '.agent/archive/feature'
                self.assertTrue(archive.is_dir())
                unit = json.loads((archive / 'branch-review.json').read_text())
                self.assertEqual('interrupted branch', unit['decisions'][-1]['reason'])
                self.assertEqual([], unit['known_issues'])
                metric = json.loads((self.repo / '.agent/metrics.jsonl').read_text().splitlines()[-1])
                self.assertEqual(('accepted', 4, None), (metric['outcome'], metric['review_rounds'], metric['reviewer_provenance']))
                self.assertIn('interrupted branch', (archive / 'deliveries/deliveries-feature-01.md').read_text())
                self.assertEqual('2' if mode == 'private' else '3', self.git('rev-list', '--count', baseline + '..HEAD'))
                self.assertEqual('', self.git('status', '--porcelain', cwd=self.repo / '.agent' if mode == 'private' else self.repo))

    def test_multi_with_branch_repair_closes_in_both_modes(self):
        for mode in ('shared', 'private'):
            with self.subTest(mode=mode):
                self.setUp()
                baseline = self.multi(mode)
                self.cli('topic', 'review', '--reviewer-model', 'actual-host-model', ok=False)
                self.cli('topic', 'test')
                report = self.branch_review()
                manifest = json.loads(Path(report['manifest']).read_text())
                self.assertEqual({'feature-01#A1','feature-02#A1'}, {a['id'] for a in manifest['acceptance']})
                self.assertEqual(baseline, manifest['baseline'])
                self.assertEqual('second', Path(manifest['changes'][0]['current']['snapshot_path']).read_text())
                result = self.result(report)
                target = result['acceptance'][0]['id']
                finding = dict(id='branch-bug',severity='blocking',view='correctness',summary='marker',anchor=target,
                               location='code.txt:1',failure_path='read marker',reachability='normal read')
                result.update(status='findings',findings=[finding])
                result['coverage'][0] = dict(target=target,result='finding',finding_id='branch-bug')
                self.branch_submit(result)
                (self.repo / 'code.txt').write_text('fixed second')
                self.cli('topic', 'complete', ok=False)
                self.cli('topic', 'test')
                self.branch_submit(self.result(self.branch_review()))
                output = self.cli('topic', 'complete')
                self.assertIn('complete', output.stdout)
                self.assertEqual('3', self.git('rev-list','--count',baseline+'..HEAD'))
                self.assertTrue((self.repo / '.agent/archive/feature').is_dir())
                self.assertEqual('', self.git('status','--porcelain',cwd=self.repo / '.agent' if mode=='private' else self.repo))
                if mode=='private': self.assertEqual('', self.git('ls-files','.agent'))
                self.cli('topic','complete','--topic','feature',ok=False)

    def test_branch_needs_user_accept_and_definition_only_reopen(self):
        for mode in ('shared','private'):
            with self.subTest(mode=mode):
                self.setUp()
                self.check_branch_decision(mode)

    def check_branch_decision(self, mode):
        self.multi(mode)
        self.cli('topic','test')
        report = self.branch_review()
        self.branch_submit(self.result(report,status='inconclusive'))
        self.assertIn('inconclusive', self.cli('topic','status').stdout)
        self.cli('topic','complete',ok=False)
        self.cli('resolve','--branch','--reopen','--reason','status only',ok=False)
        spec = self.repo / '.agent/work/feature/specs/specs-feature-01.md'
        spec.write_text(spec.read_text()+'\nclarification\n')
        self.cli('resolve','--branch','--reopen','--reason','clarified')
        self.assertEqual(1,self.branch_review()['round'])
        report = self.branch_review()
        result = self.blocking(report)
        result['status'] = 'blocked-by-design'
        self.branch_submit(result)
        (self.repo / 'code.txt').write_text('accepted branch repair')
        self.cli('resolve','--branch','--accept','--reason','take risk',ok=False)
        self.cli('topic','test')
        self.cli('resolve','--branch','--accept','--reason','take risk')
        metric=json.loads((self.repo / '.agent/metrics.jsonl').read_text().splitlines()[-1])
        self.assertEqual('accepted',metric['outcome'])
        self.assertIn('marker mismatch',(self.repo/'.agent/archive/feature/deliveries/deliveries-feature-01.md').read_text())
        self.assertEqual('', self.git('status','--porcelain',cwd=self.repo/'.agent' if mode=='private' else self.repo))

    def test_abandon_preserves_dirty_content_in_both_modes(self):
        for mode in ('shared','private'):
            with self.subTest(mode=mode):
                self.setUp()
                self.setup_config(mode,tests=("python3 -c 'pass'",))
                self.ticket()
                (self.repo / 'code.txt').write_text('keep dirty')
                output=json.loads(self.cli('topic','abandon','--topic','feature','--reason','stop work').stdout)
                self.assertIn('code.txt',output['dirty_content'])
                self.assertEqual('keep dirty',(self.repo/'code.txt').read_text())
                self.assertNotIn('feature',self.cli('work-overview').stdout)
                self.cli('implement','start','--ticket','feature-01',ok=False)
                if mode=='private':
                    self.assertEqual('',self.git('status','--porcelain',cwd=self.repo/'.agent'))
                else:
                    self.assertEqual('',self.git('status','--porcelain','--','.agent'))

    def test_single_ticket_closes_without_branch_review_in_both_modes(self):
        for mode in ('shared','private'):
            with self.subTest(mode=mode):
                self.setUp()
                self.setup_config(mode, tests=("python3 -c 'pass'",))
                self.ticket()
                self.cli('implement','start','--ticket','feature-01')
                self.cli('implement','test')
                self.approve()
                self.cli('implement','finish')
                self.summary('feature')
                self.cli('topic','review','--reviewer-model','actual-host-model',ok=False)
                self.cli('topic','complete')
                self.assertEqual('', self.git('status','--porcelain',cwd=self.repo/'.agent' if mode=='private' else self.repo))

    def test_topic_tests_empty_failure_and_whole_batch(self):
        self.setup_config(tests=("python3 -c *",))
        self.ticket()
        self.assertIn('全量',self.cli('topic','test','--topic','feature',ok=False).stderr)
        self.setup_config(tests=("python3 -c 'raise SystemExit(7)'", "python3 -c 'print(\"second command\")'"))
        self.assertIn('7',self.cli('topic','test','--topic','feature',ok=False).stderr)
        record=json.loads((self.repo/'.agent/work/feature/topic-tests.json').read_text())
        self.assertEqual(2,len(record['tests']))
        self.assertIn('second command',record['tests'][1]['output_tail'])
        self.cli('topic','review','--topic','feature','--reviewer-model','actual-host-model',ok=False)

    def test_branch_rounds_independent_and_fifth_after_invalidation_stops(self):
        self.multi()
        for i in range(4):
            self.cli('topic','test')
            report=self.branch_review()
            self.assertEqual(i+1,report['round'])
            self.branch_submit(self.result(report))
            (self.repo/'code.txt').write_text('version '+str(i))
        self.cli('topic','review','--reviewer-model','actual-host-model',ok=False)
        status=json.loads(self.cli('topic','status').stdout)['branch_review']
        self.assertEqual('needs-user',status['status'])
        self.assertIn('4',status['stop_reason'])

    def test_complete_reruns_tests_and_keeps_topic_active_on_failure(self):
        command = 'python3 -c "from pathlib import Path; raise SystemExit(8 if Path(\'.agent/fail\').exists() else 0)"'
        self.multi(command=command)
        self.cli('topic','test')
        self.branch_submit(self.result(self.branch_review()))
        (self.repo/'.agent/fail').touch()
        self.assertIn('8',self.cli('topic','complete',ok=False).stderr)
        self.assertTrue((self.repo/'.agent/work/feature').exists())
        self.assertFalse((self.repo/'.agent/archive/feature').exists())

    def test_branch_stop_signal_and_private_archive_commit_retry(self):
        baseline = self.multi('private')
        self.cli('topic','test')
        report = self.branch_review()
        self.branch_submit(self.blocking(report,'first'))
        report = self.branch_review()
        self.branch_submit(self.blocking(report,'second',contradicts='first'))
        self.assertIn('前后矛盾',self.cli('topic','status').stdout)
        (self.repo/'code.txt').write_text('accepted fix')
        self.cli('topic','test')
        hook=self.repo/'.agent/.git/hooks/pre-commit'
        hook.write_text('#!/bin/sh\nexit 1\n')
        hook.chmod(0o755)
        self.cli('resolve','--branch','--accept','--reason','exception',ok=False)
        self.assertTrue((self.repo/'.agent/work/feature').exists())
        self.assertEqual('3',self.git('rev-list','--count',baseline+'..HEAD'))
        hook.unlink()
        self.cli('resolve','--branch','--accept','--reason','exception')
        self.assertEqual('3',self.git('rev-list','--count',baseline+'..HEAD'))
        record=json.loads((self.repo/'.agent/archive/feature/branch-review.json').read_text())
        self.assertEqual(1,len([d for d in record['decisions'] if d['action']=='accept']))

    def test_accept_rejects_when_closing_tests_mutate_content(self):
        command = 'python3 -c "from pathlib import Path; Path(\'code.txt\').write_text(\'mutated\') if Path(\'.agent/mutate\').exists() else None"'
        self.multi(command=command)
        self.cli('topic','test')
        self.branch_submit(self.result(self.branch_review(),status='inconclusive'))
        (self.repo/'.agent/mutate').touch()
        self.assertIn('改变了内容',self.cli('resolve','--branch','--accept','--reason','exception',ok=False).stderr)
        self.assertFalse((self.repo/'.agent/archive/feature').exists())


if __name__ == '__main__': unittest.main()
