import json
from pathlib import Path
import tempfile
import unittest
from tools.workflow_lib.text_measurement import MAIN_CHAIN, measure_markdown
from tools.workflow_lib.release import stage_release_tree
from tools.workflow_lib.projection import project_skill_directory

ROOT = Path(__file__).resolve().parents[1]

class TextMeasurementTests(unittest.TestCase):
    def test_cursor_main_chain_stays_under_budget(self):
        # Ticket01's actual pre-construction Cursor baseline was 58,213 characters
        # (90 reachable files / 38 unique contents), not the rounded Spec estimate.
        baseline = json.loads((ROOT/'tests/fixtures/workflow_simplification/baseline.json').read_text())
        self.assertEqual(58213,baseline['measurement']['characters'])
        with tempfile.TemporaryDirectory() as tmp:
            release = Path(tmp)/'r';stage_release_tree(ROOT,release)
            for skill in (release/'skills').iterdir():project_skill_directory(skill,'cursor')
            self.assertLessEqual(measure_markdown(release/'skills',MAIN_CHAIN)['characters'],35000)

    def test_transitive_unicode_content_dedup_and_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ('a','b'):
                skill=root/name;skill.mkdir()
                (skill/'SKILL.md').write_text('[next](one.md)\n```md\n[example](missing.md)\n```\n')
                (skill/'one.md').write_text('[again](two.md)\n[outside](../outside.md)\n')
                (skill/'two.md').write_text('中文\n[cycle](one.md)\n')
            (root/'outside.md').write_text('do not count')
            report=measure_markdown(root,('a','b'))
            expected=sum(len((root/'a'/name).read_text()) for name in ('SKILL.md','one.md','two.md'))
            self.assertEqual(expected,report['characters'])
            self.assertEqual(6,report['reachable_files']);self.assertEqual(3,report['unique_contents'])
