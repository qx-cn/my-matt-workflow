"""Migration contracts through the public CLI, using captured v1 projects."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

CLI = Path(__file__).resolve().parents[1] / 'tools/workflow.py'
FIXTURE = Path(__file__).parent / 'fixtures/workflow_simplification'


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / 'project'
        subprocess.run(['git', 'clone', '-q', str(FIXTURE / 'baseline.bundle'), str(self.repo)], check=True)
        shutil.copytree(FIXTURE / 'legacy_project', self.repo, dirs_exist_ok=True)
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.repo, text=True).strip()

    def cli(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(CLI), *args, '--repo', str(self.repo)],
                                capture_output=True, text=True,
                                env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        self.assertEqual(ok, result.returncode == 0, result.stderr + result.stdout)
        return result

    def files(self):
        return {str(p.relative_to(self.repo)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.repo.rglob('*') if p.is_file()}

    def test_preview_is_zero_write_and_lists_blocked_topic(self):
        before = self.files()
        report = json.loads(self.cli('migrate').stdout)
        self.assertFalse(report['applied'])
        self.assertTrue(report['changes'])
        self.assertIn('legacy-e', json.dumps(report['unresolved']))
        self.assertEqual(before, self.files())

    def test_apply_backs_up_converts_and_keeps_completed_history(self):
        agent = self.repo / '.agent'
        original = (agent / 'work/legacy-d/tickets/tickets-legacy-d-01.md').read_bytes()
        record = (agent / 'work/legacy-d/runs/run-legacy-d-01-spec-r1.json').read_bytes()
        (agent / 'specs').mkdir()
        (agent / 'specs/old.md').write_text('long-term spec')
        (agent / 'backup-old').mkdir()
        (agent / 'backup-old/sentinel').write_text('do not copy')
        report = json.loads(self.cli('migrate', '--apply').stdout)
        backup = self.repo / report['backup']
        self.assertEqual('long-term spec', (backup / 'specs/old.md').read_text())
        self.assertFalse((backup / '.git').exists())
        self.assertFalse((backup / 'backup-old').exists())
        self.assertFalse((agent / 'specs').exists())
        self.assertIn('backup-*/', (agent / '.gitignore').read_text())
        self.assertEqual(original, (agent / 'archive/legacy-d/tickets/tickets-legacy-d-01.md').read_bytes())
        self.assertEqual(record, (agent / 'archive/legacy-d/runs/run-legacy-d-01-spec-r1.json').read_bytes())
        self.assertIn('迁移归档', (agent / 'archive/legacy-d/topic-state.json').read_text())
        self.assertEqual('implementing', json.loads(self.cli('implement', 'status', '--ticket', 'legacy-c-01').stdout)['status'])
        self.assertEqual('needs-user', json.loads(self.cli('implement', 'status', '--ticket', 'legacy-b-01').stdout)['status'])
        self.assertIn('Greeting', (agent / 'CONTEXT.md').read_text())
        self.assertEqual('', self.git('status', '--porcelain', '--', '.agent'))
        second = json.loads(self.cli('migrate').stdout)
        self.assertEqual([], second['changes'])
        self.assertIn('legacy-e', json.dumps(second['unresolved']))

    def test_project_and_topic_legacy_gates_are_read_only(self):
        commands = [('work-overview',), ('topic', 'status', '--topic', 'legacy-a'),
                    ('implement', 'status', '--ticket', 'legacy-a-03'),
                    ('implement', 'start', '--ticket', 'legacy-a-01', '--agent', 'codex'),
                    ('validate-ticket', '--ticket', 'legacy-a-01'),
                    ('topic', 'start', '--topic', 'other', '--level', 'quick')]
        before = self.files()
        for command in commands:
            self.assertIn('migrate', self.cli(*command, ok=False).stderr)
        self.assertEqual(before, self.files())

        self.cli('migrate', '--apply')
        before = self.files()
        self.assertIn('migrate', self.cli('topic', 'status', '--topic', 'legacy-e', ok=False).stderr)
        report = json.loads(self.cli('work-overview', '--json').stdout)
        self.assertEqual('需要迁移', next(t['status'] for t in report['topics'] if t['topic'] == 'legacy-e'))
        self.cli('topic', 'status', '--topic', 'legacy-a')
        self.cli('topic', 'status', '--topic', 'legacy-d')
        self.assertEqual(before, self.files())
        long_specs = self.repo / '.agent/specs'
        long_specs.mkdir()
        (long_specs / 'legacy.md').write_text('old')
        before = self.files()
        for command in commands:
            self.assertIn('migrate', self.cli(*command, ok=False).stderr)
        self.assertEqual(before, self.files())

    def test_migrated_active_ticket_runs_tests_review_and_finish(self):
        self.cli('migrate', '--apply')
        active = self.repo / '.agent/work/legacy-a/implementations/legacy-a-03.json'
        unit = json.loads(active.read_text())
        old = json.loads((self.repo / '.agent/work/legacy-a/runs/run-legacy-a-03-spec-r1.json').read_text())
        self.assertEqual(old['context']['base_sha'], unit['baseline'])
        self.assertEqual([], unit['tests'])
        self.assertEqual([], unit['reviews'])
        self.assertFalse(json.loads(self.cli('implement', 'status', '--ticket', 'legacy-a-03').stdout)['definition_changed'])
        self.cli('implement', 'test', '--ticket', 'legacy-a-03')
        opened = json.loads(self.cli('implement', 'review', '--ticket', 'legacy-a-03', '--reviewer-model', 'test').stdout)
        manifest = json.loads(Path(opened['manifest']).read_text())
        result_file = Path(opened['result_file'])
        result = json.loads(result_file.read_text())
        result.update(status='pass', reviewer={'provenance': 'self', 'model': 'test'},
                      coverage=[{'target': t, 'result': 'ok'} for t in manifest['coverage_targets']])
        result_file.write_text(json.dumps(result))
        self.cli('implement', 'review', '--ticket', 'legacy-a-03', '--submit', str(result_file))
        ticket = self.repo / '.agent/work/legacy-a/tickets/tickets-legacy-a-03.md'
        ticket.write_text(ticket.read_text().replace('- [ ]', '- [x]'))
        self.cli('implement', 'finish', '--ticket', 'legacy-a-03')
        self.assertEqual('', self.git('status', '--porcelain', '--', '.agent'))

    def test_migrated_blocker_can_be_accepted_after_tests(self):
        self.cli('migrate', '--apply')
        self.cli('resolve', '--ticket', 'legacy-b-01', '--accept', '--reason', 'fixture acceptance', ok=False)
        self.cli('implement', 'test', '--ticket', 'legacy-b-01')
        self.cli('resolve', '--ticket', 'legacy-b-01', '--accept', '--reason', 'fixture acceptance')
        self.assertEqual('', self.git('status', '--porcelain', '--', '.agent'))

    def test_migrated_blocker_can_reopen_after_definition_revision(self):
        self.cli('migrate', '--apply')
        self.cli('resolve', '--ticket', 'legacy-b-01', '--reopen', '--reason', 'no revision', ok=False)
        ticket = self.repo / '.agent/work/legacy-b/tickets/tickets-legacy-b-01.md'
        ticket.write_text(ticket.read_text().replace('Trim greeting name', 'Trim greeting names'))
        before = json.loads(self.cli('implement', 'status', '--ticket', 'legacy-b-01').stdout)['baseline']
        self.cli('resolve', '--ticket', 'legacy-b-01', '--reopen', '--reason', 'revised title')
        status = json.loads(self.cli('implement', 'status', '--ticket', 'legacy-b-01').stdout)
        self.assertEqual('implementing', status['status'])
        self.assertEqual(before, status['baseline'])
        self.assertFalse(status['definition_changed'])

    def test_empty_tests_missing_baseline_and_archive_collision_are_not_guessed(self):
        config = self.repo / '.agent/matt-workflow.md'
        config.write_text(config.read_text().replace('["python3 -m unittest -v"]', '[]'))
        journal = self.repo / '.agent/work/legacy-c/runs/run-legacy-c-01-spec-r1.json'
        value = json.loads(journal.read_text())
        value['context'].pop('base_sha')
        journal.write_text(json.dumps(value))
        (self.repo / '.agent/archive/legacy-d').mkdir(parents=True)
        before = self.files()
        report = json.loads(self.cli('migrate').stdout)
        reasons = json.dumps(report['unresolved'], ensure_ascii=False)
        self.assertIn('全量测试集合为空', reasons)
        self.assertIn('归档重名', reasons)
        self.assertEqual(before, self.files())
        config.write_text(config.read_text().replace('test_commands: []', 'test_commands: ["python3 -m unittest -v"]'))
        reasons = json.dumps(json.loads(self.cli('migrate').stdout)['unresolved'], ensure_ascii=False)
        self.assertIn('基线', reasons)

    def test_conflicting_knowledge_and_nonlocal_backend_are_reported(self):
        context = self.repo / '.agent/work/legacy-c/contexts/contexts-legacy-c-01.md'
        context.write_text('- Greeting：a conflicting meaning\n')
        report = json.loads(self.cli('migrate').stdout)
        self.assertIn('术语冲突', json.dumps(report['unresolved'], ensure_ascii=False))
        before = self.files()
        self.cli('migrate', '--apply', ok=False)
        self.assertEqual(before, self.files())
        config = self.repo / '.agent/matt-workflow.md'
        config.write_text(config.read_text().replace('task_backend: local', 'task_backend: external'))
        report = json.loads(self.cli('migrate').stdout)
        self.assertIn('task_backend', json.dumps(report['unresolved']))

    def test_private_migration_commits_metadata_and_excludes_git_from_backup(self):
        config = self.repo / '.agent/matt-workflow.md'
        config.write_text(config.read_text().replace('agent_directory_mode: shared', 'agent_directory_mode: private'))
        self.git('rm', '-qr', '--cached', '.agent')
        self.git('commit', '-qm', 'private metadata')
        agent = self.repo / '.agent'
        subprocess.run(['git', 'init', '-q', '--initial-branch=main'], cwd=agent, check=True)
        for key, value in [('user.name', 'Test'), ('user.email', 'test@example.invalid')]:
            subprocess.run(['git', 'config', key, value], cwd=agent, check=True)
        subprocess.run(['git', 'add', '.'], cwd=agent, check=True)
        subprocess.run(['git', 'commit', '-qm', 'old metadata'], cwd=agent, check=True)
        report = json.loads(self.cli('migrate', '--apply').stdout)
        self.assertFalse((self.repo / report['backup'] / '.git').exists())
        status = subprocess.check_output(['git', 'status', '--porcelain'], cwd=agent, text=True)
        self.assertEqual('', status)

    def test_spec_and_ticket_fields_are_inferred_only_from_unique_sources(self):
        spec = self.repo / '.agent/work/legacy-c/specs/specs-legacy-c-01.md'
        spec.write_text(spec.read_text().split('---', 2)[2])
        ticket = self.repo / '.agent/work/legacy-c/tickets/tickets-legacy-c-01.md'
        ticket.write_text('\n'.join(line for line in ticket.read_text().splitlines()
                                   if not line.startswith(('id:', 'title:'))) + '\n')
        self.cli('migrate', '--apply')
        self.assertIn('"legacy-c"', spec.read_text())
        self.assertIn('"Greeting fixture"', ticket.read_text())
        self.cli('implement', 'test', '--ticket', 'legacy-c-01')

    def test_topic_adr_is_merged_and_conflicting_adr_is_not_overwritten(self):
        adr = self.repo / '.agent/work/legacy-a/adr/0001.md'
        adr.parent.mkdir()
        adr.write_text('# Decision\nUse standard library\n')
        self.cli('migrate', '--apply')
        target = self.repo / '.agent/adr/0001.md'
        self.assertEqual('# Decision\nUse standard library\n', target.read_text())
        self.assertFalse(adr.exists())
        other = self.repo / '.agent/work/knowledge/adr/0001.md'
        other.parent.mkdir(parents=True)
        other.write_text('conflict')
        before = self.files()
        self.assertIn('ADR 冲突', json.dumps(json.loads(self.cli('migrate').stdout)['unresolved'], ensure_ascii=False))
        self.cli('migrate', '--apply', ok=False)
        self.assertEqual(before, self.files())

    def test_commit_failure_preserves_backup_and_allows_retry(self):
        hook = self.repo / '.git/hooks/pre-commit'
        hook.write_text('#!/bin/sh\nexit 1\n')
        hook.chmod(0o755)
        original = (self.repo / '.agent/matt-workflow.md').read_bytes()
        self.cli('migrate', '--apply', ok=False)
        self.assertEqual(original, (self.repo / '.agent/matt-workflow.md').read_bytes())
        self.assertTrue(list((self.repo / '.agent').glob('backup-*')))
        hook.unlink()
        time.sleep(1.05)  # Backup directory names have one-second resolution.
        self.cli('migrate', '--apply')
        self.assertEqual('', self.git('status', '--porcelain', '--', '.agent'))

    def test_incomplete_config_is_reported_without_planning_or_writes(self):
        path = self.repo / '.agent/matt-workflow.md'
        original = path.read_text()
        for declaration in (None, 'test_commands: 123'):
            with self.subTest(declaration=declaration):
                lines = [line for line in original.splitlines() if not line.startswith('test_commands:')]
                if declaration:
                    lines.insert(1, declaration)
                path.write_text('\n'.join(lines) + '\n')
                before = self.files()
                report = json.loads(self.cli('migrate').stdout)
                self.assertIn('test_commands', json.dumps(report['unresolved']))
                self.assertFalse(any('topic' in item for item in report['unresolved']))
                self.assertEqual(before, self.files())
                self.cli('migrate', '--apply', ok=False)
                self.assertEqual(before, self.files())



if __name__ == '__main__':
    unittest.main()
