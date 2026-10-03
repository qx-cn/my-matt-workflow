"""Technical corrections through the public CLI in real temporary repositories."""
import copy
import json
from pathlib import Path
import unittest

import test_batches as batch_tests
from tools.workflow_lib.batches import pending_self_findings


class TechnicalRefreshTests(unittest.TestCase):
    setUp = batch_tests.BatchTests.setUp
    git = batch_tests.BatchTests.git
    cli = batch_tests.BatchTests.cli
    setup_config = batch_tests.BatchTests.setup_config
    ticket = batch_tests.BatchTests.ticket
    replace = batch_tests.BatchTests.replace
    setup = batch_tests.BatchTests.setup
    implement = batch_tests.BatchTests.implement
    self_review = batch_tests.BatchTests.self_review
    review = batch_tests.BatchTests.review

    def unit(self, name='feature-01'):
        return self.repo / f'.agent/work/feature/implementations/{name}.json'

    def notes(self, findings=(), **changes):
        value = dict(kind='technical', adjustment='Correct a repository fact, preserving approved behavior',
                     unchanged_behavior='Marker remains observable through the existing interface',
                     unchanged_acceptance='All approved marker assertions and failures remain covered',
                     evidence=[dict(path='code.txt', detail='Observed marker through the real repository file')],
                     findings=list(findings))
        value.update(changes)
        path = self.repo / '.agent/technical-refresh.json'
        path.write_text(json.dumps(value))
        return path

    def refresh(self, target='ticket', findings=(), ok=True, **changes):
        notes = self.notes(findings, **changes)
        args = ('batch', 'refresh', '--topic', 'feature') if target == 'batch' else (
            'resolve', '--branch', '--topic', 'feature', '--refresh') if target == 'branch' else (
            'resolve', '--ticket', 'feature-01', '--refresh')
        return self.cli(*args, '--reason', 'Observed technical correction', '--notes-file', str(notes), ok=ok)

    def change_fact(self, text='Corrected a verified internal fact.'):
        spec = self.repo / '.agent/work/feature/specs/specs-feature-01.md'
        spec.write_text(spec.read_text() + '\n'+text+'\n')

    def self_findings(self, values):
        notes = self.repo / '.agent/self.md'
        path = self.repo / '.agent/findings.json'
        path.write_text(json.dumps(values))
        self.cli('implement', 'self-review', '--notes-file', str(notes), '--findings-file', str(path))

    def finding(self, identifier, view='spec-challenge', **extra):
        return dict(id=identifier, severity='blocking', view=view, summary=identifier,
                    location='code.txt:1', basis='Observed marker contract at its caller', **extra)

    def chosen(self, identifier, unit='self:feature-01'):
        return dict(unit_id=unit, finding_id=identifier, basis='The approved result is unchanged; code.txt supplies the corrected fact')

    def start_ticket(self):
        self.setup()
        self.cli('implement', 'start', '--ticket', 'feature-01')
        self.cli('implement', 'test')
        self.self_review()

    def open_ticket_review(self):
        return json.loads(self.cli('implement', 'review', '--ticket', 'feature-01',
            '--reason', 'concurrent recovery', '--reviewer-model', 'host').stdout)

    def test_ticket_refresh_invalidates_evidence_and_is_idempotent(self):
        self.start_ticket()
        old = json.loads(self.unit().read_text())
        self.change_fact()
        result = json.loads(self.refresh().stdout)
        self.assertEqual('applied', result['refresh'])
        current = json.loads(self.unit().read_text())
        self.assertEqual(old['baseline'], current['baseline'])
        self.assertEqual(old['tests'], current['tests'])
        self.assertIn(old['self_review'], current['self_reviews'])
        self.assertNotIn('test_run', current)
        self.assertEqual(old['test_run'],current['invalidated_evidence'][-1]['records']['test_run'])
        self.assertEqual(old['self_review'],current['invalidated_evidence'][-1]['records']['self_review'])
        self.assertFalse(json.loads(self.cli('implement', 'status').stdout)['tests_passed'])
        self.cli('implement', 'finish', ok=False)
        before = self.unit().read_bytes()
        self.assertEqual('unchanged', json.loads(self.refresh().stdout)['refresh'])
        self.assertEqual(before, self.unit().read_bytes())

    def test_missing_invalid_or_wrong_evidence_does_not_mutate_records(self):
        self.start_ticket(); self.change_fact()
        before = self.unit().read_bytes()
        self.cli('resolve', '--ticket', 'feature-01', '--refresh', '--reason', 'fact', ok=False)
        for changes in (dict(evidence=[]), dict(evidence=[dict(path='missing.txt',detail='not found')]),
                        dict(unchanged_acceptance=''), dict(kind='product')):
            self.refresh(ok=False, **changes)
            self.assertEqual(before, self.unit().read_bytes())
        self.refresh(findings=[self.chosen('missing')], ok=False)
        self.assertEqual(before, self.unit().read_bytes())

    def test_mixed_self_challenges_only_dispose_the_named_technical_one(self):
        self.start_ticket()
        findings = [self.finding('fact'), self.finding('product'), self.finding('bug', view='correctness')]
        self.self_findings(findings)
        old = copy.deepcopy(json.loads(self.unit().read_text())['self_review'])
        self.refresh(findings=[self.chosen('fact')])
        unit = json.loads(self.unit().read_text())
        self.assertIn(old, unit['self_reviews'])
        self.assertEqual({'product','bug'}, set(pending_self_findings(unit)))
        status = json.loads(self.cli('implement', 'status').stdout)
        self.assertEqual('needs-user', status['status'])
        self.assertEqual({'product'}, {d['finding']['id'] for d in status['decisions_needed']})
        self.cli('implement', 'finish', ok=False)

    def test_technical_self_challenge_restores_and_does_not_reappear(self):
        self.start_ticket(); self.self_findings([self.finding('fact')])
        self.refresh(findings=[self.chosen('fact')])
        status = json.loads(self.cli('implement', 'status').stdout)
        self.assertEqual('implementing', status['status'])
        self.assertEqual([], status['decisions_needed'])
        self.cli('implement', 'test'); self.self_review()
        ticket = self.repo / '.agent/work/feature/tickets/tickets-feature-01.md'
        ticket.write_text(ticket.read_text().replace('- [ ]','- [x]'))
        self.cli('implement', 'finish')
        self.assertFalse(pending_self_findings(json.loads(self.unit().read_text())))

    def test_open_review_refresh_keeps_round_and_series_and_expires_result(self):
        self.start_ticket()
        review = self.open_ticket_review()
        old = json.loads(self.unit().read_text())
        self.change_fact(); self.refresh()
        unit = json.loads(self.unit().read_text())
        self.assertEqual(old['reviews'], unit['reviews'])
        self.assertNotIn('active_review', unit)
        self.cli('implement', 'review', '--submit', review['result_file'], ok=False)
        self.cli('implement', 'test'); self.self_review()
        second = self.open_ticket_review()
        self.assertEqual(2, second['round'])
        final = json.loads(self.unit().read_text())
        self.assertEqual(final['reviews'][0]['review_series'], final['reviews'][1]['review_series'])

    def test_ticket_exhaustion_is_not_refunded_by_technical_refresh(self):
        self.start_ticket()
        for _ in range(4): self.open_ticket_review()
        self.cli('implement', 'review', '--reason', 'recovery', '--reviewer-model', 'host', ok=False)
        self.change_fact(); result = json.loads(self.refresh().stdout)
        self.assertEqual((4,0), (result['rounds_used'], result['rounds_remaining']))
        status = json.loads(self.cli('implement', 'status').stdout)
        self.assertEqual('needs-user', status['status'])
        self.assertEqual(4, status['rounds_used'])
        self.cli('implement', 'test'); self.self_review()
        self.cli('implement', 'review', '--reason', 'recovery', '--reviewer-model', 'host', ok=False)

    def test_legacy_missing_reviews_keeps_observed_rounds(self):
        self.start_ticket()
        for _ in range(3): self.open_ticket_review()
        unit = json.loads(self.unit().read_text())
        unit['past_reviews'] = unit.pop('reviews')
        self.unit().write_text(json.dumps(unit))
        self.change_fact(); self.refresh()
        self.cli('implement', 'test'); self.self_review()
        self.assertEqual(4, self.open_ticket_review()['round'])
        self.cli('implement', 'review', '--reason', 'recovery', '--reviewer-model', 'host', ok=False)

    def test_batch_and_branch_refresh_keep_open_rounds_and_exhaustion(self):
        for action in ('batch','branch'):
            with self.subTest(action=action):
                self.setUp(); self.setup(2); self.implement(1); self.implement(2)
                self.cli('batch','test','--topic','feature')
                args=('topic','review','--initiated-by','agent','--reason','cross-module') if action=='branch' else ('batch','review')
                for _ in range(4):
                    self.cli(*args,'--topic','feature','--reviewer-model','host')
                self.cli(*args,'--topic','feature','--reviewer-model','host',ok=False)
                root=self.repo/'.agent/work/feature'
                record=root/('branch-review.json' if action=='branch' else 'batches/01.json')
                original=json.loads(record.read_text())
                self.change_fact(); self.refresh(target=action)
                current=json.loads(record.read_text())
                self.assertEqual(original['reviews'],current['reviews'])
                self.assertEqual('needs-user',current['status'])
                self.assertNotIn('active_review',current)
                self.cli('batch','test','--topic','feature')
                self.cli(*args,'--topic','feature','--reviewer-model','host',ok=False)

    def test_independent_challenges_recover_in_batch_and_branch(self):
        for action in ('batch','branch'):
            with self.subTest(action=action):
                self.setUp(); self.setup(2); self.implement(1); self.implement(2)
                report=self.review(action='topic' if action=='branch' else 'batch',finding=self.finding('fact'))
                result=self.refresh(target=action,findings=[self.chosen('fact',report['unit_id'])])
                self.assertEqual('applied',json.loads(result.stdout)['refresh'])
                record=self.repo/'.agent/work/feature'/('branch-review.json' if action=='branch' else 'batches/01.json')
                current=json.loads(record.read_text())
                self.assertNotEqual('needs-user',current['status'])
                self.assertEqual('fact',current['reviews'][0]['result']['findings'][0]['id'])
                self.cli('batch','test','--topic','feature')
                fresh=self.review(action='topic' if action=='branch' else 'batch')
                self.assertEqual(2,fresh['round'])

    def test_definition_only_refresh_does_not_remove_product_or_evidence_stop(self):
        self.start_ticket(); self.self_findings([self.finding('product')])
        self.change_fact(); self.refresh()
        status=json.loads(self.cli('implement','status').stdout)
        self.assertEqual('needs-user',status['status'])
        self.assertEqual('product',status['decisions_needed'][0]['finding']['id'])

    def test_status_routes_definition_adjustment_to_refresh_with_inputs(self):
        self.start_ticket(); self.change_fact()
        status=json.loads(self.cli('implement','status').stdout)
        self.assertIn('--refresh',status['next_command'])
        self.assertIn('--notes-file',status['next_command'])
        self.assertEqual([],status['decisions_needed'])
        self.assertTrue(status['inputs_needed'])

    def test_batch_and_branch_old_test_and_pass_receipts_expire(self):
        for target in ('batch', 'branch'):
            with self.subTest(target=target):
                self.setUp(); self.setup(2); self.implement(1); self.implement(2)
                report=self.review(action='topic' if target=='branch' else 'batch')
                root=self.repo/'.agent/work/feature'
                record=root/('branch-review.json' if target=='branch' else 'batches/01.json')
                old=json.loads(record.read_text())
                old_tests=json.loads((root/'batch-tests-01.json').read_text())
                self.change_fact(); refreshed=json.loads(self.refresh(target=target).stdout)
                new=json.loads(record.read_text())
                self.assertEqual(old['reviews'],new['reviews'])
                self.assertNotIn('active_review',new)
                self.cli('batch','close','--topic','feature',ok=False)
                status=json.loads(self.cli('batch','status','--topic','feature').stdout)
                self.assertIn('batch test',status['next_command'])
                args=('topic','review','--initiated-by','agent','--reason','contract') if target=='branch' else ('batch','review')
                failed=self.cli(*args,'--topic','feature','--reviewer-model','host',ok=False)
                self.assertIn('test:',failed.stderr)
                self.assertIn('batch test',refreshed['next_command'])
                import shlex
                self.cli(*shlex.split(refreshed['next_command'])[1:])
                archived=json.loads((root/'batches/01.json').read_text())['technical_refreshes'][-1]['prior_full_tests']
                self.assertEqual(old_tests,archived['batch-tests-01.json'])
                self.assertEqual(2,self.review(action='topic' if target=='branch' else 'batch')['round'])

    def test_mixed_independent_challenges_keep_product_waiting(self):
        for target in ('ticket','batch','branch'):
            with self.subTest(target=target):
                self.setUp()
                if target=='ticket':
                    self.start_ticket(); report=self.open_ticket_review(); action=('implement','review')
                else:
                    self.setup(2);self.implement(1);self.implement(2);self.cli('batch','test','--topic','feature')
                    action=('topic','review') if target=='branch' else ('batch','review')
                    extra=('--initiated-by','agent','--reason','contract') if target=='branch' else ()
                    report=json.loads(self.cli(*action,'--topic','feature','--reviewer-model','host',*extra).stdout)
                manifest=json.loads(Path(report['manifest']).read_text())
                result=json.loads(Path(report['result_file']).read_text())
                result.update(status='findings',reviewer=manifest['review_context'],
                    coverage=[dict(target=t,result='ok') for t in manifest['coverage_targets']],
                    findings=[self.finding('fact'),self.finding('product')])
                result['reviewer']={k:result['reviewer'][k] for k in ('provenance','model')}
                Path(report['result_file']).write_text(json.dumps(result))
                self.cli(*action,'--topic','feature','--submit',report['result_file'])
                self.refresh(target=target,findings=[self.chosen('fact',report['unit_id'])])
                status=json.loads(self.cli('implement' if target=='ticket' else 'batch','status','--topic','feature').stdout)
                self.assertEqual({'product'},{d['finding']['id'] for d in status['decisions_needed']})
                unit=self.unit() if target=='ticket' else self.repo/'.agent/work/feature'/('branch-review.json' if target=='branch' else 'batches/01.json')
                value=json.loads(unit.read_text())
                self.assertEqual(['fact','product'],[f['id'] for f in value['reviews'][-1]['result']['findings']])
                self.assertEqual('needs-user',status.get('status',value.get('status')))

    def test_evidence_and_contradiction_stops_survive_definition_refresh(self):
        for reason in ('inconclusive','前后矛盾：contradicts 指向之前的问题'):
            with self.subTest(reason=reason):
                self.setUp();self.start_ticket()
                record=self.unit();value=json.loads(record.read_text())
                value['stop_reason']=reason;record.write_text(json.dumps(value))
                ticket=self.repo/'.agent/work/feature/tickets/tickets-feature-01.md'
                ticket.write_text(ticket.read_text().replace('status: implementing','status: needs-user'))
                self.change_fact();self.refresh()
                self.assertEqual(reason,json.loads(record.read_text())['stop_reason'])
                self.assertEqual('needs-user',json.loads(self.cli('implement','status').stdout)['status'])

    def test_evidence_paths_fail_closed_and_transaction_leaves_no_partial_write(self):
        self.start_ticket();self.change_fact()
        link=self.repo/'evidence-link';link.symlink_to(self.repo/'code.txt')
        before={p:p.read_bytes() for p in (self.repo/'.agent/work/feature').glob('**/*.json')}
        for path in ('../escape',str(self.repo/'code.txt'),'evidence-link'):
            self.refresh(ok=False,evidence=[dict(path=path,detail='invalid')])
            self.assertEqual(before,{p:p.read_bytes() for p in before})

    def test_explicit_user_reopen_remains_a_new_series_after_refresh(self):
        for target in ('ticket','batch','branch'):
            with self.subTest(target=target):
                self.setUp()
                if target=='ticket':
                    self.start_ticket(); report=self.open_ticket_review()
                else:
                    self.setup(2);self.implement(1);self.implement(2)
                    report=self.review(action='topic' if target=='branch' else 'batch')
                self.change_fact();self.refresh(target=target)
                self.change_fact('User approved a changed definition and explicit new review series.')
                args=('batch','reopen','--topic','feature') if target=='batch' else (
                    'resolve','--branch','--topic','feature','--reopen') if target=='branch' else (
                    'resolve','--ticket','feature-01','--reopen')
                self.cli(*args,'--reason','User explicitly approved new series')
                self.change_fact('Further technical correction within the newly approved goal.')
                self.refresh(target=target)
                if target=='ticket':
                    self.cli('implement','test');self.self_review(); fresh=self.open_ticket_review()
                    record=self.unit()
                else:
                    fresh=self.review(action='topic' if target=='branch' else 'batch')
                    record=self.repo/'.agent/work/feature'/('branch-review.json' if target=='branch' else 'batches/01.json')
                self.assertEqual(1,fresh['round'])
                self.assertNotEqual(report['unit_id'],json.loads(record.read_text())['reviews'][0]['review_series'])

    def test_reverting_to_an_earlier_definition_is_a_real_refresh(self):
        self.start_ticket()
        spec=self.repo/'.agent/work/feature/specs/specs-feature-01.md'
        original=spec.read_text()
        self.change_fact('Fact A.');definition_a=spec.read_text();self.refresh()
        self.change_fact('Fact B.');self.refresh()
        spec.write_text(definition_a)
        self.assertEqual('applied',json.loads(self.refresh().stdout)['refresh'])
        self.assertFalse(json.loads(self.cli('implement','status').stdout)['definition_changed'])
        self.assertEqual(3,len(json.loads(self.unit().read_text())['technical_refreshes']))
        self.assertEqual('unchanged',json.loads(self.refresh().stdout)['refresh'])

    def test_technical_disposition_does_not_clear_mirrored_evidence_stop(self):
        self.setup(2);self.implement(1);self.implement(2)
        self.cli('batch','test','--topic','feature')
        report=json.loads(self.cli('topic','review','--topic','feature','--initiated-by','agent',
            '--reason','cross-module','--reviewer-model','host').stdout)
        manifest=json.loads(Path(report['manifest']).read_text())
        result=json.loads(Path(report['result_file']).read_text())
        result.update(status='inconclusive',reviewer=dict(provenance='self',model='host'),
            coverage=[dict(target=t,result='ok') for t in manifest['coverage_targets']],
            findings=[self.finding('fact')])
        Path(report['result_file']).write_text(json.dumps(result))
        self.cli('topic','review','--topic','feature','--submit',report['result_file'])
        self.refresh(target='branch',findings=[self.chosen('fact',report['unit_id'])])
        root=self.repo/'.agent/work/feature'
        self.assertEqual('needs-user',json.loads((root/'branch-review.json').read_text())['status'])
        self.assertEqual('needs-user',json.loads((root/'batches/01.json').read_text())['status'])
        self.cli('batch','test','--topic','feature')
        self.cli('batch','review','--topic','feature','--reviewer-model','host',ok=False)

    def test_existing_temporary_symlink_cannot_redirect_a_refresh_write(self):
        import tempfile
        self.start_ticket();self.change_fact()
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        outside=Path(directory.name)/'sentinel.json';outside.write_text('outside sentinel')
        temporary=self.unit().with_suffix('.json.refresh-tmp');temporary.symlink_to(outside)
        before=self.unit().read_bytes()
        result=self.refresh(ok=False)
        self.assertIn('符号链接',result.stderr)
        self.assertEqual('outside sentinel',outside.read_text())
        self.assertEqual(before,self.unit().read_bytes())

    def test_accepted_ticket_challenge_does_not_block_later_technical_recovery(self):
        for target in ('batch','branch'):
            with self.subTest(target=target):
                self.setUp();self.setup(2)
                self.cli('implement','start','--ticket','feature-01')
                (self.repo/'code.txt').write_text('approved current behavior')
                self.cli('implement','test');self.self_review();self.self_findings([self.finding('accepted-product')])
                ticket=self.repo/'.agent/work/feature/tickets/tickets-feature-01.md'
                ticket.write_text(ticket.read_text().replace('- [ ]','- [x]'))
                self.cli('resolve','--ticket','feature-01','--accept','--reason','User accepts the recorded product risk')
                accepted=self.unit().read_bytes()
                self.implement(2)
                review=self.review(action='topic' if target=='branch' else 'batch',finding=self.finding('fact'))
                self.refresh(target=target,findings=[self.chosen('fact',review['unit_id'])])
                root=self.repo/'.agent/work/feature'
                record=root/('branch-review.json' if target=='branch' else 'batches/01.json')
                self.assertNotEqual('needs-user',json.loads(record.read_text())['status'])
                self.assertEqual(accepted,self.unit().read_bytes())
                self.assertEqual('accepted-product',json.loads(self.unit().read_text())['known_issues'][0]['id'])

    def test_branch_refresh_cannot_rewrite_closed_batch_history(self):
        self.setup(2);self.implement(1);self.implement(2)
        self.review(action='topic');self.review();self.cli('batch','close','--topic','feature')
        root=self.repo/'.agent/work/feature'
        before={p:p.read_bytes() for p in root.glob('**/*.json')}
        self.change_fact()
        result=self.refresh(target='branch',ok=False)
        self.assertIn('收口',result.stderr)
        self.assertEqual(before,{p:p.read_bytes() for p in before})


if __name__ == '__main__':
    unittest.main()
