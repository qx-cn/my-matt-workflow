"""Design reports cannot silently drop facts or product assumptions."""
import tempfile
import unittest
from pathlib import Path
from tools.workflow_lib.artifact_review import (ArtifactReviewError, build_artifact_review_snapshot,
    submit_artifact_review_result, validate_design_report)

class DesignReportTests(unittest.TestCase):
    def empty(self):
        return {k:{'none':'此玩具方案无相关内容'} for k in ('assertions','findings','excluded_risks','semantic_assumptions')}
    def test_design_submit_requires_four_part_report_and_preserves_it(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'design.md';p.write_text('design')
            unit=build_artifact_review_snapshot([p],artifact_kind='design')
            result=dict(content_id=unit['content_id'], checks={k:dict(status='pass',reason=None) for k in unit['review_unit']['required_checks']},findings=[],inconclusive=[])
            with self.assertRaisesRegex(ArtifactReviewError,'design_report'):
                submit_artifact_review_result([p],Path(unit['snapshot_dir']),result)
            result['design_report']=self.empty()
            accepted=submit_artifact_review_result([p],Path(unit['snapshot_dir']),result)
            self.assertEqual(result['design_report'],accepted['design_report'])
    def test_mismatch_requires_linked_finding_and_cannot_hide_challenge(self):
        r=self.empty();r['assertions']=[dict(assertion='API returns null',status='mismatch',finding_id='F1')]
        with self.assertRaisesRegex(ArtifactReviewError,'finding_id'):validate_design_report(r,'finding')
        r['findings']=[dict(id='F1',summary='API throws',view='spec-challenge',severity='blocking',location='Spec API',basis='caller catches exception')]
        validate_design_report(r,'finding')
        with self.assertRaisesRegex(ArtifactReviewError,'挑战'):validate_design_report(r,'pass')
    def test_missing_sections_and_pending_semantics_prevent_pass(self):
        for key in self.empty():
            r=self.empty();del r[key]
            with self.assertRaises(ArtifactReviewError):validate_design_report(r,'pass')
        r=self.empty();r['semantic_assumptions']=['业务只允许单次重试，需用户决定']
        with self.assertRaisesRegex(ArtifactReviewError,'用户'):validate_design_report(r,'pass')
