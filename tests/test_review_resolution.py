"""Bounded reviews and human decisions through restartable public CLI calls."""
import json
import unittest
import test_implement_review as reviews


class ResolutionTests(unittest.TestCase):
    setUp = reviews.ReviewTests.setUp
    git = reviews.ReviewTests.git
    cli = reviews.ReviewTests.cli
    setup_config = reviews.ReviewTests.setup_config
    ticket = reviews.ReviewTests.ticket
    replace = reviews.ReviewTests.replace
    start = reviews.ReviewTests.start
    review = reviews.ReviewTests.review
    result = reviews.ReviewTests.result
    submit = reviews.ReviewTests.submit

    def blocking(self, report, identifier='bug', location='code.txt:1', **extra):
        finding = dict(id=identifier, severity='blocking',view='correctness', summary='marker mismatch',
                       anchor='feature-01#A1', location=location,
                       failure_path='read marker then mismatch', reachability='default read', **extra)
        result = self.result(report, status='findings', findings=[finding])
        result['coverage'][0] = dict(target='feature-01#A1', result='finding', finding_id=identifier)
        return result

    def test_accept_unsubmitted_reviews_recovers_in_both_modes(self):
        for mode in ('shared', 'private'):
            with self.subTest(mode=mode):
                self.setUp()
                self.setup_config(mode, tests=("python3 -c 'pass'",))
                ticket = self.ticket()
                self.cli('implement', 'start', '--ticket', 'feature-01')
                baseline = self.git('rev-parse', 'HEAD')
                for _ in range(4):
                    self.review()
                self.cli('implement', 'review', '--reviewer-model', 'actual-host-model', ok=False)
                self.assertEqual('needs-user', json.loads(self.cli('implement', 'status').stdout)['status'])
                self.cli('resolve', '--ticket', 'feature-01', '--accept', '--reason', 'interrupted', ok=False)
                self.assertIn('status: needs-user', ticket.read_text())
                self.cli('implement', 'test')
                # A failed metadata commit retains a retryable decision state.
                git_dir = self.repo / '.agent/.git' if mode == 'private' else self.repo / '.git'
                hook = git_dir / 'hooks/pre-commit'
                hook.write_text('#!/bin/sh\nexit 1\n')
                hook.chmod(0o755)
                self.cli('resolve', '--ticket', 'feature-01', '--accept', '--reason', 'interrupted', ok=False)
                self.assertIn('status: needs-user', ticket.read_text())
                hook.unlink()
                self.cli('resolve', '--ticket', 'feature-01', '--accept', '--reason', 'interrupted')
                self.assertIn('status: complete', ticket.read_text())
                metric = json.loads((self.repo / '.agent/metrics.jsonl').read_text().splitlines()[-1])
                self.assertEqual(('accepted', 4, 1, None),
                                 (metric['outcome'], metric['review_rounds'], metric['test_runs'], metric['reviewer_provenance']))
                unit = json.loads((self.repo / '.agent/work/feature/implementations/feature-01.json').read_text())
                self.assertEqual([], unit['known_issues'])
                self.assertEqual(['interrupted'], [d['reason'] for d in unit['decisions']])
                self.assertEqual('0' if mode == 'private' else '1', self.git('rev-list', '--count', baseline + '..HEAD'))
                self.assertEqual('', self.git('status', '--porcelain', cwd=self.repo / '.agent' if mode == 'private' else self.repo))

    def test_four_passes_invalidate_then_fifth_stops_persistently(self):
        self.start()
        (self.repo / 'code.txt').write_text('first reviewed change')
        for i in range(4):
            report = self.review()
            self.assertEqual(i + 1, report['rounds_used'])
            self.submit(self.result(report))
            (self.repo / 'code.txt').write_text(str(i))
        self.assertIn('4', self.cli('implement', 'review', '--reviewer-model', 'actual-host-model', ok=False).stderr)
        status = json.loads(self.cli('implement', 'status').stdout)
        self.assertEqual('needs-user', status['status'])
        self.assertIn('轮数', status['stop_reason'])
        self.cli('implement', 'review', '--reviewer-model', 'actual-host-model', ok=False)
        self.cli('resolve', '--ticket', 'feature-01', '--accept', '--reason', 'accept', ok=False)
        self.cli('implement', 'test')
        self.cli('resolve', '--ticket', 'feature-01', '--accept', '--reason', 'accept')
        metrics = json.loads((self.repo / '.agent/metrics.jsonl').read_text().splitlines()[-1])
        self.assertEqual('accepted', metrics['outcome'])
        self.assertEqual('', self.git('status', '--porcelain'))

    def test_four_blocking_reviews_and_terminal_verdicts(self):
        self.start()
        for i in range(4):
            report = self.review()
            self.submit(self.blocking(report, str(i)))
        self.assertEqual('needs-user', json.loads(self.cli('implement', 'status').stdout)['status'])
        self.cli('implement', 'review', '--reviewer-model', 'actual-host-model', ok=False)

    def test_reopen_requires_real_definition_change_and_clears_old_tests(self):
        self.start()
        path = self.repo / '.agent/work/feature/tickets/tickets-feature-01.md'
        baseline = json.loads(self.cli('implement', 'status').stdout)['baseline']
        self.submit(self.result(self.review(), status='inconclusive'))
        path.write_text(path.read_text().replace('- [ ]', '- [x]'))
        self.cli('resolve', '--ticket', 'feature-01', '--reopen', '--reason', 'checkbox', ok=False)
        spec = self.repo / '.agent/work/feature/specs/specs-feature-01.md'
        spec.write_text(spec.read_text() + '\nclarified marker\n')
        self.cli('resolve', '--ticket', 'feature-01', '--reopen', '--reason', 'clarified')
        status = json.loads(self.cli('implement', 'status').stdout)
        self.assertEqual(('implementing', baseline, False), (status['status'], status['baseline'], status['tests_passed']))
        self.assertEqual(1, self.review()['round'])

    def test_accept_keeps_blocking_as_known_issues(self):
        self.start()
        self.submit(self.blocking(self.review(), contradicts='missing'), ok=False)
        report = self.review()
        result = self.blocking(report)
        result['status'] = 'blocked-by-design'
        self.submit(result)
        self.cli('resolve', '--ticket', 'feature-01', '--accept', '--reason', 'approved exception')
        self.assertIn('approved exception', self.git('log', '-1', '--format=%B'))
        self.assertEqual('bug', json.loads(self.cli('topic', 'status').stdout)['known_issues'][0]['id'])
        metric = json.loads((self.repo / '.agent/metrics.jsonl').read_text().splitlines()[-1])
        self.assertEqual('self', metric['reviewer_provenance'])

    def test_accept_preserves_submitted_independent_provenance(self):
        self.start()
        report = json.loads(self.cli('implement', 'review', '--reviewer-model', 'declared-model',
                                     '--reviewer-session-id', 'different-review-session').stdout)
        result = self.result(report, status='inconclusive')
        result['reviewer'] = dict(provenance='independent', model='declared-model')
        self.submit(result)
        self.cli('resolve', '--ticket', 'feature-01', '--accept', '--reason', 'known uncertainty')
        metric = json.loads((self.repo / '.agent/metrics.jsonl').read_text().splitlines()[-1])
        self.assertEqual('independent', metric['reviewer_provenance'])

    def prepare_lines(self):
        (self.repo / 'code.txt').write_text('a\nb\nc\nd\ne\nf\n')
        self.git('add', 'code.txt')
        self.git('commit', '-qm', 'six lines')
        self.start()
        (self.repo / 'code.txt').write_text('A\nB\nC\nD\nE\nF\n')

    def stopped(self, reason):
        self.assertIn(reason, json.loads(self.cli('implement', 'status').stdout)['stop_reason'])
        self.cli('implement', 'review', '--reviewer-model', 'actual-host-model', ok=False)

    def test_same_root_two_repair_reviews_in_distinct_ranges(self):
        self.prepare_lines()
        self.submit(self.blocking(self.review(), 'first'))
        (self.repo / 'code.txt').write_text('fixed A\nB\nC\nD\nE\nF\n')
        self.submit(self.blocking(self.review(), 'second'))
        (self.repo / 'code.txt').write_text('fixed A\nB\nC\nD\nfixed E\nF\n')
        self.submit(self.blocking(self.review(), 'third', 'code.txt:5'))
        self.stopped('同一根因')

    def test_overlapping_repairs_use_middle_snapshot_line_numbers(self):
        self.prepare_lines()
        self.submit(self.blocking(self.review(), 'first'))
        (self.repo / 'code.txt').write_text('inserted\nA\nB\nC\nD\nE\nF\n')
        self.submit(self.blocking(self.review(), 'second', 'code.txt:6'))
        (self.repo / 'code.txt').write_text('edited insertion\nA\nB\nC\nD\nE\nF\n')
        self.submit(self.blocking(self.review(), 'third', 'code.txt:6'))
        self.stopped('中间快照')

    def test_contradiction_stops_without_content_change(self):
        self.start()
        self.submit(self.blocking(self.review(), 'first'))
        self.submit(self.blocking(self.review(), 'second', contradicts='first'))
        self.stopped('前后矛盾')

    def test_volume_stops_at_more_than_one_point_five(self):
        self.start()
        (self.repo / 'code.txt').write_text('first')
        self.submit(self.blocking(self.review(), 'first'))
        (self.repo / 'code.txt').write_text('a\nb\nc\nd\n')
        self.submit(self.blocking(self.review(), 'second'))
        self.stopped('1.5')

    def test_revised_test_argv_revalidates_and_becomes_effective(self):
        self.setup_config(tests=("python3 -c *", "python3 -c 'pass'"))
        path = self.ticket()
        self.cli('implement', 'start', '--ticket', 'feature-01')
        self.replace(path, 'test_commands', ["python3 -c 'print(123)'"])
        self.cli('implement', 'test', ok=False)
        self.cli('resolve', '--ticket', 'feature-01', '--reopen', '--reason', 'new test')
        self.assertIn('123', self.cli('implement', 'test').stdout)
        self.replace(path, 'test_commands', ['unconfigured command'])
        self.cli('resolve', '--ticket', 'feature-01', '--reopen', '--reason', 'bad test', ok=False)

    def test_private_accept_commits_content_once_and_agent_separately(self):
        self.setup_config('private', tests=("python3 -c 'pass'",))
        self.ticket()
        self.cli('implement', 'start', '--ticket', 'feature-01')
        baseline = self.git('rev-parse', 'HEAD')
        (self.repo / 'code.txt').write_text('accepted implementation')
        self.submit(self.result(self.review(), status='inconclusive'))
        self.cli('resolve', '--ticket', 'feature-01', '--accept', '--reason', 'accept risk', ok=False)
        self.cli('implement', 'test')
        self.cli('resolve', '--ticket', 'feature-01', '--accept', '--reason', 'accept risk')
        self.assertEqual('1', self.git('rev-list', '--count', baseline + '..HEAD'))
        self.assertEqual('', self.git('ls-files', '.agent'))
        self.assertEqual('', self.git('status', '--porcelain', cwd=self.repo / '.agent'))


if __name__ == '__main__':
    unittest.main()
