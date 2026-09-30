import json,sys,unittest
sys.path.insert(0, '/tmp/independent02/current/tests')
from test_topic_lifecycle import TopicLifecycleTests
class ExtraProbes(TopicLifecycleTests):
    def test_private_document_preserves_content_and_commits_agent(self):
        self.setup_config('private')
        (self.repo / '.agent/work/docs').mkdir(parents=True)
        (self.repo / 'code.txt').write_text('unrelated staged\n')
        self.git('add','code.txt')
        before=self.git('rev-parse','HEAD')
        self.cli('topic','complete','--topic','docs')
        self.assertEqual(before,self.git('rev-parse','HEAD'))
        self.assertEqual('M  code.txt',self.git('status','--porcelain','--','code.txt'))
        self.assertEqual('',self.git('status','--porcelain',cwd=self.repo / '.agent'))
        self.assertEqual('',self.git('ls-files','.agent'))
        metric=json.loads((self.repo / '.agent/metrics.jsonl').read_text())
        for k in ('level','started_at','test_runs','review_rounds','repair_rounds','needs_user_count','command_errors','reviewer_provenance','tests_configured'):
            self.assertIsNone(metric[k],k)
    def test_no_content_private_quick_has_no_code_commit(self):
        self.setup_config('private',tests=("python3 -c 'pass'",))
        self.cli('topic','start','--topic','change','--level','quick');self.summary()
        before=self.git('rev-parse','HEAD')
        self.cli('topic','complete')
        self.assertEqual(before,self.git('rev-parse','HEAD'))
        self.assertEqual('',self.git('status','--porcelain',cwd=self.repo / '.agent'))
    def test_failed_command_execution_then_retry(self):
        self.setup_config(tests=('nonexistent-workflow-independent-executable',))
        self.cli('topic','start','--topic','change','--level','quick');self.summary()
        result=self.cli('topic','complete',ok=False)
        self.assertIn('无法执行',result.stderr)
        self.assertEqual('active',json.loads(self.cli('topic','status').stdout)['status'])
        self.assertFalse((self.repo / '.agent/metrics.jsonl').exists())
        profile=self.repo / '.agent/matt-workflow.md'
        profile.write_text(profile.read_text().replace('nonexistent-workflow-independent-executable', "python3 -c 'pass'"))
        self.cli('topic','complete')
        self.assertEqual(1,len((self.repo / '.agent/metrics.jsonl').read_text().splitlines()))
    def test_existing_quick_branch_records_switched_head(self):
        self.setup_config()
        self.git('switch','-c','change')
        (self.repo / 'code.txt').write_text('branch content\n')
        self.git('add','code.txt');self.git('commit','-qm','branch content')
        expected=self.git('rev-parse','HEAD');self.git('switch','main')
        result=json.loads(self.cli('topic','start','--topic','change','--level','quick').stdout)
        self.assertEqual(expected,result['baseline'])
        self.assertEqual('branch content\n',(self.repo / 'code.txt').read_text())
    def test_invalid_new_config_points_to_field(self):
        self.setup_config();p=self.repo / '.agent/matt-workflow.md'
        original=p.read_text()
        for old,new,field in [('test_commands: []','test_commands: 1','test_commands'),('assurance_level: standard','assurance_level: invalid','assurance_level')]:
            p.write_text(original.replace(old,new));before=p.read_bytes()
            self.assertIn(field,self.cli('topic','status','--topic','change',ok=False).stderr)
            self.assertEqual(before,p.read_bytes())
    def test_private_retry_new_content_is_rejected_after_code_commit(self):
        self.setup_config('private');self.cli('topic','start','--topic','change','--level','quick');self.summary()
        (self.repo / 'code.txt').write_text('first\n')
        hook=self.repo / '.agent/.git/hooks/pre-commit';hook.write_text('#!/bin/sh\nexit 1\n');hook.chmod(0o755)
        self.cli('topic','complete',ok=False);first=self.git('rev-parse','HEAD')
        (self.repo / 'code.txt').write_text('second\n');hook.unlink()
        self.assertIn('已经提交',self.cli('topic','complete',ok=False).stderr)
        self.assertEqual(first,self.git('rev-parse','HEAD'))
        self.git('restore','code.txt');self.cli('topic','complete')
        self.assertEqual(first,self.git('rev-parse','HEAD'))
if __name__=='__main__':
    suite=unittest.TestSuite(ExtraProbes(n) for n in ExtraProbes.__dict__ if n.startswith('test_'))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
