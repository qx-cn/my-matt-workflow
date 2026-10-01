import json
import tempfile
import unittest
from pathlib import Path

from tools.workflow_lib.installer import install_release, load_install_state, verify_installed_state
from tools.workflow_lib.release import stage_release_tree

ROOT = Path(__file__).resolve().parents[1]
REVIEW_ENTRIES = (
    'my-implement', 'my-code-review', 'my-review-design',
    'my-review-artifact', 'my-review-instructions', 'my-tech-design',
)


class WorkflowTextPackagingTests(unittest.TestCase):
    def test_shared_workflow_contracts_survive_host_projection(self):
        """Observe installed resource closure, not keyword-based semantic grading."""
        with tempfile.TemporaryDirectory() as tmp:
            release = Path(tmp) / 'workflow-texts'
            manifest = stage_release_tree(ROOT, release)
            (release / 'manifest.json').write_text(json.dumps(
                {'release_id': release.name, **manifest}))
            for host in ('codex', 'cursor', 'claude'):
                home = Path(tmp) / host
                install_release(release, home, target=host)
                state = load_install_state(home / 'my-matt-workflow/install-state.json')
                verify_installed_state(state)
                for entry in REVIEW_ENTRIES:
                    shared = home / 'skills' / entry / 'references/shared'
                    self.assertTrue((shared / 'review-loop.md').is_file(), (host, entry))
                    self.assertTrue((shared / 'user-intervention.md').is_file(), (host, entry))
                for entry in ('my-grill-with-docs', 'my-to-spec', 'my-to-tickets', 'my-implement'):
                    shared = home / 'skills' / entry / 'references/shared'
                    self.assertTrue((shared / 'workflow-delivery.md').is_file(), (host, entry))
                # Policies use a Skill-root pointer because resources are copied verbatim.
                # Every actual policy consumer must receive its target on all hosts.
                for skill in (home / 'skills').iterdir():
                    policies = skill / 'references/policies'
                    if any('references/shared/user-intervention.md' in p.read_text()
                           for p in policies.glob('*.md')):
                        self.assertTrue((skill / 'references/shared/user-intervention.md').is_file(),
                                        (host, skill.name))
                self.assertFalse(list((home / 'skills').glob('*/references/composed')))
