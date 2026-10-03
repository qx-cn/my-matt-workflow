"""System findings are independent of acceptance anchors."""
import copy
import unittest
from tools.workflow_lib.ticket_review import validate_result
from tools.workflow_lib.topic_service import TopicError

class FindingAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.manifest = dict(unit_id='u',content_id='c',round=1,acceptance=[dict(id='A1')],probes=[],downstream_tickets=[],
                             coverage_targets=['A1'],review_context=dict(provenance='independent',model='host'))
        self.result={k:self.manifest[k] for k in ('unit_id','content_id','round','acceptance','probes','downstream_tickets')}
        self.result.update(status='findings',reviewer=dict(provenance='independent',model='host'),
                           coverage=[dict(target='A1',result='ok')],findings=[dict(id='F1',view='impact',severity='blocking',
                           summary='caller breaks',location='caller.py:4-8',basis='public caller reaches changed return type')])
    def test_unanchored_blocker_and_optional_anchor(self):
        validate_result(self.result,self.manifest)
        self.result['findings'][0]['anchor']='A1'
        self.result['coverage']=[dict(target='A1',result='finding',finding_id='F1')]
        validate_result(self.result,self.manifest)
    def test_field_errors_and_coverage(self):
        for field in ('location','basis','view'):
            value=copy.deepcopy(self.result);value['findings'][0].pop(field)
            with self.assertRaisesRegex(TopicError,field):validate_result(value,self.manifest)
        self.result['coverage']=[]
        with self.assertRaisesRegex(TopicError,'coverage: 缺少 A1'):validate_result(self.result,self.manifest)
    def test_pass_cannot_hide_blocking_or_challenge(self):
        self.result['status']='pass'
        with self.assertRaisesRegex(TopicError,'status'):validate_result(self.result,self.manifest)
        self.result['findings'][0].update(view='spec-challenge',severity='advisory',disposition='defer',owner='user')
        with self.assertRaisesRegex(TopicError,'status'):validate_result(self.result,self.manifest)
    def test_advisory_disposition_is_required(self):
        self.result['findings'][0]['severity']='advisory'
        with self.assertRaisesRegex(TopicError,'disposition'):validate_result(self.result,self.manifest)
