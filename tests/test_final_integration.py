"""Final public contracts; behavioral cases use temporary repositories and CLI."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from tools.workflow_lib import check

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'tools/workflow.py'
COMMANDS = {'setup','validate','check','doctor','build','install','deploy','prune-releases',
 'resolve-rules','inspect-rules','validate-ticket','work-overview','review-snapshot',
 'artifact-review-snapshot','artifact-review-open','artifact-review-submit',
 'artifact-review-verify','artifact-review-finalize','topic','implement','resolve','migrate','metrics','batch','escape'}
REMOVED = ('refresh-project validate-evals validate-agent-evidence smoke decision-gate write-gate '
 'ticket-transition next-ticket ticket-scope run-context run-start implementation-open '
 'implementation-submit implementation-close implementation-status implementation-next-action '
 'run-record run-code-receipt run-test-evidence run-review-evidence run-review-submit run-review-open '
 'implementation-repair-plan-open implementation-repair-plan-review-open implementation-repair-plan-review-submit '
 'archive-spec archive-topic archive-show archive-list').split()

class FinalIntegrationTests(unittest.TestCase):
    def test_exact_public_commands_and_unknown_legacy_commands(self):
        help_text = subprocess.check_output([sys.executable,str(CLI),'--help'],text=True)
        listed = help_text.split('{',1)[1].split('}',1)[0].split(',')
        self.assertEqual(COMMANDS,set(listed))
        for command in REMOVED:
            result=subprocess.run([sys.executable,str(CLI),command],capture_output=True,text=True)
            self.assertNotEqual(0,result.returncode,command)
            self.assertIn('未知命令',result.stderr)

    def test_removed_names_are_absent_from_skill_resources_and_policies(self):
        keys = 'branch_policy commit_policy external_write_policy docs_writeback composition_policy work_scope_policy decision_policy max_repair_rounds humanizer_policy review_commands'.split()
        for root in ('skills','resources','policies'):
            for path in (ROOT/root).rglob('*'):
                if path.is_file() and path.suffix in {'.md','.json','.yaml'}:
                    text = path.read_text()
                    self.assertFalse([name for name in REMOVED+keys if name in text],str(path))

    def test_artifact_cli_rejects_retired_kinds_and_options(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact=Path(tmp)/'a.md';artifact.write_text('# Current design')
            for args in [('--parallel',),('--topic','x'),('--kind','repair-plan')]:
                result=subprocess.run([sys.executable,str(CLI),'artifact-review-open','--artifact',str(artifact),*args],capture_output=True,text=True)
                self.assertNotEqual(0,result.returncode,args)
            opened=json.loads(subprocess.check_output([sys.executable,str(CLI),'artifact-review-open','--artifact',str(artifact)],text=True))
            self.assertNotIn('round',opened['review_unit'])
            self.assertEqual(['final-state-writing','reader-first-writing','visual-communication','humanizer','artifact-finalization'],opened['review_unit']['required_checks'])
            subprocess.run([sys.executable,str(CLI),'artifact-review-finalize','--artifact',str(artifact),'--snapshot-dir',opened['snapshot_dir'],'--expect-content-id',opened['content_id']],check=True,capture_output=True)

    def test_check_only_runs_tests_even_with_a_stale_release_pointer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'current.json').write_text('{"release_id":"missing"}')
            with mock.patch.object(check.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'','')) as run:
                self.assertEqual('valid',check.run_check(root)['status'])
            self.assertEqual([sys.executable,'-m','unittest','discover','-s','tests'],run.call_args.args[0])

    def test_metric_summary_preserves_unknowns_and_filters_topic(self):
        from tools.workflow_lib.metrics import summarize
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp);(repo/'.agent').mkdir()
            rows=[dict(topic='a',kind='ticket',outcome='complete',test_runs=2,review_rounds=1,
                       reviewer_provenance='self',findings={'blocking':0,'advisory':1},command_errors=0),
                  dict(topic='a',kind='topic',outcome='complete',test_runs=None,review_rounds=None,
                       reviewer_provenance='independent',findings={'blocking':None,'advisory':None},command_errors=None),
                  dict(topic='b',kind='quick',outcome='complete',test_runs=1,reviewer_provenance='self')]
            (repo/'.agent/metrics.jsonl').write_text('\n'.join(json.dumps(r) for r in rows)+'\n')
            report=summarize(repo,'a')
            self.assertEqual(['a'],list(report['topics']))
            self.assertEqual(2,report['topics']['a']['records'])
            self.assertEqual('mixed',report['topics']['a']['reviewer_provenance'])
            self.assertEqual(rows[:2],report['records'])

    def test_ticket_metric_reports_mixed_review_sources(self):
        from tools.workflow_lib.ticket_completion import metric
        unit=dict(topic='a',ticket='a-01',started_at='start',tests=[],reviews=[
            {'result':{'reviewer':{'provenance':'self'},'findings':[]}},
            {'result':{'reviewer':{'provenance':'independent'},'findings':[]}}])
        self.assertEqual('mixed',metric(unit,'complete',{'reviewer':{'provenance':'independent'}})['reviewer_provenance'])

class MetricsBehaviorTests(unittest.TestCase):
    def test_check_test_failures_are_not_command_errors(self):
        from test_topic_lifecycle import TopicLifecycleTests
        from tools.workflow_lib.metrics import command_error_count
        import shutil
        fixture = TopicLifecycleTests('test_document_completion_preserves_staged_content')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.setup_config()
        fixture.cli('topic', 'start', '--topic', 'change', '--level', 'quick')
        shutil.copytree(ROOT / 'tools', fixture.repo / 'tools',
                        ignore=shutil.ignore_patterns('__pycache__'))
        tests = fixture.repo / 'tests'
        tests.mkdir()
        (tests / 'test_failure.py').write_text(
            'import unittest\nclass Failure(unittest.TestCase):\n'
            ' def test_failure(self): self.fail("intentional")\n')
        result = subprocess.run([sys.executable, str(fixture.repo / 'tools/workflow.py'), 'check'],
                                cwd=fixture.repo, capture_output=True, text=True)
        self.assertNotEqual(0, result.returncode)
        self.assertIn('unit tests failed', result.stdout)
        self.assertEqual(0, command_error_count(fixture.repo, 'change'))

    def test_document_completion_keeps_unobserved_errors_unknown(self):
        from test_topic_lifecycle import TopicLifecycleTests
        from tools.workflow_lib.metrics import FIELDS
        fixture = TopicLifecycleTests('test_document_completion_preserves_staged_content')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.setup_config()
        document = fixture.repo / '.agent/work/docs/note.md'
        document.parent.mkdir(parents=True)
        document.write_text('# Document\n')
        fixture.cli('topic', 'review', '--topic', 'docs', ok=False)
        fixture.cli('topic', 'complete', '--topic', 'docs')
        row = json.loads((fixture.repo / '.agent/metrics.jsonl').read_text())
        self.assertEqual(set(FIELDS), set(row))
        self.assertIsNone(row['level'])
        self.assertIsNone(row['command_errors'])

    def test_usage_errors_count_but_test_failures_do_not(self):
        from test_implement_lifecycle import ImplementationTests
        fixture = ImplementationTests('test_declared_tests_progress_failure_and_definition_change')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.setup_config(tests=("python3 -c 'raise SystemExit(3)'",))
        fixture.ticket(commands=["python3 -c 'raise SystemExit(3)'"])
        fixture.cli('implement','start','--ticket','feature-01')
        fixture.cli('implement','finish',ok=False)
        fixture.cli('implement','test',ok=False)
        from tools.workflow_lib.metrics import command_error_count
        self.assertEqual(1,command_error_count(fixture.repo,'feature'))
        result=subprocess.run([sys.executable,str(CLI),'implement','finish',
                               '--repo='+str(fixture.repo),'--topic=feature'],capture_output=True,text=True)
        self.assertNotEqual(0,result.returncode)
        self.assertEqual(2,command_error_count(fixture.repo,'feature'))

    def test_completion_metrics_have_every_field_and_cli_summary(self):
        from test_implement_finish import FinishTests
        from tools.workflow_lib.metrics import FIELDS
        fixture=FinishTests('test_no_content_ignores_metadata_and_preserves_next_ticket')
        fixture.setUp();self.addCleanup(fixture.doCleanups)
        fixture.start();fixture.approve()
        fixture.cli('implement','finish')
        rows=[json.loads(line) for line in (fixture.repo/'.agent/metrics.jsonl').read_text().splitlines()]
        self.assertEqual(set(FIELDS),set(rows[0]))
        self.assertEqual(('ticket','feature-01','complete'),(rows[0]['kind'],rows[0]['ticket'],rows[0]['outcome']))
        report=json.loads(fixture.cli('metrics','--topic','feature').stdout)
        self.assertEqual(rows,report['records'])
        self.assertEqual(1,report['topics']['feature']['records'])
