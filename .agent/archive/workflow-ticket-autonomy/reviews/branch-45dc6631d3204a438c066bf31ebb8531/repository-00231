"""Durable observations and public escaped-defect registration, without fabricated history."""
import json
from pathlib import Path
import unittest
import test_batches as batch_cases
from tools.workflow_lib import quality_metrics as quality

class QualityTests(unittest.TestCase):
    setUp=batch_cases.BatchTests.setUp
    git=batch_cases.BatchTests.git
    cli=batch_cases.BatchTests.cli
    setup_config=batch_cases.BatchTests.setup_config
    ticket=batch_cases.BatchTests.ticket
    replace=batch_cases.BatchTests.replace
    summary=batch_cases.BatchTests.summary
    setup=batch_cases.BatchTests.setup
    implement=batch_cases.BatchTests.implement
    review=batch_cases.BatchTests.review
    def self_review(self):
        path=self.repo/'.agent/self.md'
        from tools.workflow_lib.batches import SELF_SECTIONS
        path.write_text('\n'.join(f'## {h}\n无：玩具用例无此风险。\n' for h in SELF_SECTIONS))
        self.cli('implement','self-review','--notes-file',str(path),'--no-findings')
    def test_clean_batch_counts_and_archived_escape_with_automatic_design_context(self):
        self.setup();self.implement();self.review();self.cli('batch','close','--topic','feature')
        root=self.repo/'.agent/work/feature'
        (root/'reviews/design.md').write_text('# 独立设计审查\n'+ '\n'.join('## '+h+'\n无：此演练无风险。' for h in ('承重断言核验表','审查发现','已考察但排除的风险','待用户确认的需求语义假设')))
        self.summary('feature');self.cli('topic','complete','--topic','feature')
        archive=self.repo/'.agent/archive/feature'
        before={str(p.relative_to(archive)):p.read_bytes() for p in archive.rglob('*') if p.is_file()}
        result=json.loads(self.cli('escape','--topic','feature','--ticket','feature-01','--source','人工评审','--view','impact','--expected-layer','批次审查','--description','caller lost semantics').stdout)
        self.assertEqual(('已执行','01'),(result['design_review'],result['batch']))
        report=json.loads(self.cli('metrics','--topic','feature').stdout)['topics']['feature']
        self.assertEqual(1,report['escaped_defects']);self.assertEqual(1,report['escaped_by_expected_layer']['批次审查'])
        stats=report['quality'];self.assertEqual(1,stats['batches'][0]['review_subagents'])
        self.assertEqual(0,stats['finding_counts']['self']['impact']['blocking'])
        self.assertFalse(stats['whole_branch_review']['executed'])
        rows=[json.loads(x) for x in (self.repo/'.agent/metrics.jsonl').read_text().splitlines()]
        self.assertIn('batches',rows[-1]);self.assertEqual(1,rows[-1]['batches'][0]['review_subagents'])
        self.assertEqual(before,{str(p.relative_to(archive)):p.read_bytes() for p in archive.rglob('*') if p.is_file()})
    def test_escape_validation_unknown_context_and_grouping_without_completion_record(self):
        self.setup();self.cli('implement','start','--ticket','feature-01')
        args=('escape','--topic','feature','--source','后续开发','--view','correctness','--expected-layer','实施自审','--description','boundary case')
        bad=self.cli(*args,'--batch','99',ok=False);self.assertIn('batch',bad.stderr)
        bad=self.cli(*args,'--ticket','other-01',ok=False);self.assertIn('ticket',bad.stderr)
        result=json.loads(self.cli(*args).stdout);self.assertEqual('未知',result['design_review'])
        report=json.loads(self.cli('metrics','--topic','feature').stdout)
        self.assertEqual(0,len(report['records']));self.assertEqual(1,report['topics']['feature']['escaped_by_expected_layer']['实施自审'])
        spec=next((self.repo/'.agent/work/feature/specs').glob('*.md'));spec.write_text(spec.read_text().replace('revision: 1\n','revision: 1\nstatus: current\n')+'\n未触发设计审查：只修改展示文案。\n')
        self.assertEqual('未触发',json.loads(self.cli(*args).stdout)['design_review'])
    def test_self_findings_are_validated_and_deduplicated_across_records(self):
        self.setup();self.cli('implement','start','--ticket','feature-01')
        self.self_review()
        data=self.repo/'.agent/findings.json'
        finding=dict(id='S1',view='maintainability',severity='advisory',location='code.txt',basis='project rule',summary='duplicate',disposition='fix-in-batch')
        data.write_text(json.dumps([finding]));notes=self.repo/'.agent/self.md'
        for _ in range(2):self.cli('implement','self-review','--notes-file',str(notes),'--findings-file',str(data))
        stats=json.loads(self.cli('metrics','--topic','feature').stdout)['topics']['feature']['quality']
        self.assertEqual(1,stats['finding_counts']['self']['maintainability']['advisory'])
        legacy=self.repo/'.agent/work/feature/implementations/feature-01.json'
        value=json.loads(legacy.read_text());value.pop('self_reviews');value['self_review'].pop('findings')
        legacy.write_text(json.dumps(value));self.self_review()
        self.assertIsNone(json.loads(self.cli('metrics','--topic','feature').stdout)['topics']['feature']['quality']['finding_counts']['self'])
        finding['view']='invalid';data.write_text(json.dumps([finding]))
        self.assertIn('view',self.cli('implement','self-review','--notes-file',str(notes),'--findings-file',str(data),ok=False).stderr)
        data.write_text('null')
        self.assertIn('findings',self.cli('implement','self-review','--notes-file',str(notes),'--findings-file',str(data),ok=False).stderr)
    def test_history_keeps_counts_without_reopening_budget_and_old_sources_stay_unknown(self):
        finding=dict(id='F1',view='impact',severity='blocking')
        entry=dict(review_series='series1',review_context=dict(provenance='independent',session_id='fresh1'),result=dict(findings=[finding]))
        unit=dict(reviews=[entry])
        quality.preserve_history(unit);unit['reviews']=[]
        self.assertEqual(1,quality.dispatch_count([unit]))
        self.assertEqual(1,quality.counts(quality.unit_items(unit,'batch','01'))['batch']['impact']['blocking'])
        unit['reviews']=[dict(entry,review_context=dict(provenance='independent',session_id='fresh2'))]
        self.assertEqual(2,quality.dispatch_count([unit]))
        self.assertEqual(1,quality.counts(quality.unit_items(unit,'batch','01'))['batch']['impact']['blocking'])
        self.assertIsNone(quality.dispatch_count([dict(reviews=[dict(result={})])]))
        self.assertIsNone(quality.counts([('self','old',[dict(severity='blocking')])])['self'])
        legacy=dict(ticket='old-01',reviews=[entry])
        tally=quality.ticket_fields(legacy)['finding_counts']
        self.assertEqual(1,tally['ticket-legacy']['impact']['blocking'])
        self.assertEqual(0,tally['batch']['impact']['blocking'])
    def submit_result(self,report,findings=()):
        manifest=json.loads(Path(report['manifest']).read_text())
        result=json.loads(Path(report['result_file']).read_text())
        result.update(status='findings' if findings else 'pass',reviewer=dict(provenance='independent',model='host'),
            coverage=[dict(target=t,result='ok') for t in manifest['coverage_targets']],findings=list(findings))
        Path(report['result_file']).write_text(json.dumps(result))
        return report['result_file']
    def test_high_risk_blocking_observation_and_whole_branch_request_provenance(self):
        self.setup(2);self.cli('implement','start','--ticket','feature-01')
        (self.repo/'code.txt').write_text('first');self.cli('implement','test');self.self_review()
        report=json.loads(self.cli('implement','review','--ticket','feature-01','--reason','public contract','--reviewer-model','host','--reviewer-session-id','risk-fresh').stdout)
        finding=dict(id='R1',summary='old caller breaks',view='impact',severity='blocking',location='caller.py',basis='formal path')
        self.cli('implement','review','--ticket','feature-01','--submit',self.submit_result(report,[finding]))
        stats=json.loads(self.cli('metrics','--topic','feature').stdout)['topics']['feature']['quality']
        self.assertEqual(dict(count=1,with_blocking=1,rounds=1),stats['high_risk_reviews'])
        self.assertEqual(1,stats['finding_counts']['high-risk']['impact']['blocking'])
        self.assertEqual(1,stats['batches'][0]['review_subagents'])
        report=json.loads(self.cli('implement','review','--ticket','feature-01','--reason','public contract','--reviewer-model','host','--reviewer-session-id','risk-fresh-2').stdout)
        self.cli('implement','review','--ticket','feature-01','--submit',self.submit_result(report))
        p=self.repo/'.agent/work/feature/tickets/tickets-feature-01.md';p.write_text(p.read_text().replace('- [ ]','- [x]'))
        self.cli('implement','finish');self.implement(2)
        self.cli('batch','test','--topic','feature')
        report=json.loads(self.cli('topic','review','--topic','feature','--initiated-by','user','--reason','cross-batch contract','--reviewer-model','host','--reviewer-session-id','whole-fresh').stdout)
        stats=json.loads(self.cli('metrics','--topic','feature').stdout)['topics']['feature']['quality']
        self.assertIsNone(stats['whole_branch_review']['executed'])
        self.cli('topic','review','--topic','feature','--submit',self.submit_result(report))
        stats=json.loads(self.cli('metrics','--topic','feature').stdout)['topics']['feature']['quality']
        self.assertTrue(stats['whole_branch_review']['executed'])
        self.assertEqual(('user','cross-batch contract'),(stats['whole_branch_review']['initiated_by'],stats['whole_branch_review']['reason']))
        self.assertEqual(3,stats['batches'][0]['review_subagents'])

    def test_human_status_reports_challenge_without_internal_state_names(self):
        self.setup();self.implement()
        self.review(finding=dict(id='D1',view='spec-challenge',severity='blocking',location='Spec',basis='wrong existing contract',summary='现有接口与方案冲突'))
        text=self.cli('batch','status','--topic','feature','--human').stdout
        self.assertIn('需要用户裁决',text);self.assertIn('请决定修订 Spec',text)
        for code in ('needs-user','blocked-by-design','reviewing','open'):self.assertNotIn(code,text)
        text=self.cli('topic','status','--topic','feature','--human').stdout
        self.assertIn('现有接口与方案冲突',text);self.assertNotIn('needs-user',text)

