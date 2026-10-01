"""Ticket completion gates and commits observed through the CLI."""
import json
from pathlib import Path
import unittest
import test_implement_review as reviews


class FinishTests(unittest.TestCase):
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

    def approve(self):
        report = self.review()
        self.submit(self.result(report))
        path = self.repo / '.agent/work/feature/tickets/tickets-feature-01.md'
        path.write_text(path.read_text().replace('- [ ]', '- [x]'))

    def test_five_steps_finish_commits_once_and_archives_single_ticket(self):
        self.setup_config(tests=("python3 -c 'pass'",))
        self.ticket()
        self.cli('implement', 'start', '--ticket', 'feature-01')
        baseline = self.git('rev-parse', 'HEAD')
        (self.repo / 'code.txt').write_text('implementation')
        self.cli('implement', 'test', '--ticket', 'feature-01')
        self.approve()
        output = json.loads(self.cli('implement', 'finish', '--ticket', 'feature-01').stdout)
        self.assertEqual('complete', output['status'])
        self.assertEqual('feature-01: Execute tests', self.git('log', '-1', '--format=%s'))
        self.assertEqual('1', self.git('rev-list', '--count', baseline + '..HEAD'))
        self.assertIn('topic complete', output['next_command'])
        self.assertEqual('', self.git('status', '--porcelain'))
        self.cli('topic', 'complete', '--topic', 'feature', ok=False)
        root = self.repo / '.agent/work/feature/deliveries'
        root.mkdir()
        headings = ['改动概述','测试结果','审查发现与修复','建议','已知问题','长期知识沉淀','用户介入记录','未验证项']
        (root/'deliveries-feature-01.md').write_text('\n'.join('## '+h+'\nnone' for h in headings))
        self.cli('topic', 'complete', '--topic', 'feature')
        self.assertTrue((self.repo / '.agent/archive/feature').is_dir())
        self.assertEqual('2', self.git('rev-list', '--count', baseline + '..HEAD'))
        self.assertEqual('', self.git('status', '--porcelain'))

    def test_finish_rejects_missing_review_unchecked_and_stale_content(self):
        self.start()
        self.assertIn('review', self.cli('implement', 'finish', ok=False).stderr)
        report = self.review()
        self.submit(self.result(report))
        self.assertIn('acceptance', self.cli('implement', 'finish', ok=False).stderr)
        path = self.repo / '.agent/work/feature/tickets/tickets-feature-01.md'
        path.write_text(path.read_text().replace('- [ ]', '- [x]'))
        (self.repo / 'code.txt').write_text('stale')
        self.assertIn('test', self.cli('implement', 'finish', ok=False).stderr)
        self.assertIn('implement test', json.loads(self.cli('implement', 'status').stdout)['next_command'])
        self.cli('implement', 'test')
        self.assertIn('content_id', self.cli('implement', 'finish', ok=False).stderr)
        self.assertIn('implement review', json.loads(self.cli('implement', 'status').stdout)['next_command'])

    def test_private_metadata_failure_retries_with_one_code_commit(self):
        self.setup_config('private', tests=("python3 -c 'pass'",))
        self.ticket()
        self.cli('implement', 'start', '--ticket', 'feature-01')
        baseline = self.git('rev-parse', 'HEAD')
        (self.repo / 'code.txt').write_text('implementation')
        self.cli('implement', 'test')
        self.approve()
        hook = self.repo / '.agent/.git/hooks/pre-commit'
        hook.write_text('#!/bin/sh\nexit 1\n')
        hook.chmod(0o755)
        self.cli('implement', 'finish', ok=False)
        self.assertIn('status: implementing', (self.repo / '.agent/work/feature/tickets/tickets-feature-01.md').read_text())
        self.assertEqual('1', self.git('rev-list', '--count', baseline + '..HEAD'))
        hook.unlink()
        self.cli('implement', 'finish')
        self.assertEqual('1', self.git('rev-list', '--count', baseline + '..HEAD'))
        self.assertEqual('', self.git('ls-files', '.agent'))
        self.assertEqual('', self.git('status', '--porcelain', cwd=self.repo / '.agent'))
        metrics = [json.loads(l) for l in (self.repo / '.agent/metrics.jsonl').read_text().splitlines()]
        self.assertEqual(1, len(metrics))
        self.assertEqual(('ticket', 'complete'), (metrics[0]['kind'], metrics[0]['outcome']))

    def test_no_content_ignores_metadata_and_preserves_next_ticket(self):
        self.start()
        self.ticket(number=2, dependencies=('feature-01',))
        self.approve()
        (self.repo / '.agent/note.md').write_text('only metadata')
        output = json.loads(self.cli('implement', 'finish').stdout)
        self.assertIsNone(output['commit'])
        self.assertIn('--ticket feature-02', output['next_command'])
        self.assertEqual('', self.git('status', '--porcelain'))

    def test_repairs_require_notes_and_commit_body_keeps_reason(self):
        self.start()
        (self.repo / 'code.txt').write_text('initial implementation')
        report = self.review()
        finding = {'id': 'bug', 'severity': 'blocking', 'view': 'correctness', 'summary': 'marker failure',
                   'anchor': 'feature-01#A1', 'location': 'code.txt:1',
                   'failure_path': 'read marker then mismatch', 'reachability': 'normal read'}
        result = self.result(report, status='findings', findings=[finding])
        result['coverage'][0] = {'target': 'feature-01#A1', 'result': 'finding', 'finding_id': 'bug'}
        self.submit(result)
        (self.repo / 'code.txt').write_text('fixed')
        self.cli('implement', 'test')
        self.approve()
        self.assertIn('notes_file', self.cli('implement', 'finish', ok=False).stderr)
        notes = self.repo / '.agent/notes.md'
        notes.write_text('Repair the marker at its source.')
        self.cli('implement', 'finish', '--notes-file', str(notes))
        self.assertIn(notes.read_text(), self.git('log', '-1', '--format=%B'))



if __name__ == '__main__':
    unittest.main()
