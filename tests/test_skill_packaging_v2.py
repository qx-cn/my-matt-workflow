import unittest
import tempfile
import json
import shutil
import argparse
from unittest.mock import patch

import sys
from pathlib import Path
with patch.object(sys, "path", [str(Path(__file__).resolve().parents[1] / "tools"), *sys.path]):
    from tools import workflow

from tools.workflow_lib.composition import load_composition_manifest, validate_composition_manifest
from tools.workflow_lib.release import ReleaseError, stage_release_tree, build_release
from tools.workflow_lib.validator import ValidationError
from tools.workflow_lib.composition import CompositionError
from tools.workflow_lib.installer import install_release, verify_installed_state, load_install_state

ROOT = Path(__file__).resolve().parents[1]
MODEL_ENTRIES = {
    'my-grilling', 'my-domain-modeling', 'my-codebase-design', 'my-tdd',
    'my-code-review', 'my-review-design', 'my-to-spec', 'my-to-tickets',
    'my-implement', 'my-prototype', 'my-writing-for-agents',
}
MANUAL_ENTRIES = {
    'my-ask-matt', 'my-setup', 'my-install', 'my-grill-me', 'my-grill-with-docs',
    'my-handoff', 'my-research', 'my-diagnosing-bugs', 'my-resolving-merge-conflicts',
    'my-triage', 'my-wayfinder', 'my-wizard', 'my-to-questionnaire', 'my-teach',
    'my-tech-design', 'my-test-report', 'my-edit-article', 'my-humanizer',
    'my-improve-codebase-architecture', 'my-review-artifact', 'my-review-instructions',
}


class PackagingV2Tests(unittest.TestCase):
    def test_build_gate_retains_configuration_without_topic_state(self):
        from tools.workflow_lib.topic_service import read_config

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            source = root / 'skills/my-a'
            source.mkdir(parents=True)
            (source / 'SKILL.md').write_text(
                '---\nname: my-a\ndescription: test\n'
                'disable-model-invocation: true\n---\n# Test\n')
            agent = root / '.agent'
            (agent / 'work').mkdir(parents=True)
            shutil.copy2(ROOT / '.agent/matt-workflow.md', agent / 'matt-workflow.md')
            (agent / 'work/state.json').write_text('{}')
            expected = read_config(root)

            def gate(snapshot):
                self.assertEqual(expected, read_config(snapshot))
                self.assertFalse((snapshot / '.agent/work').exists())

            release = build_release(
                root / 'skills', root / 'releases', release_id='config-gate',
                upstream_id='test', repo_root=root, source_gate=gate)
            self.assertFalse((release / '.agent').exists())

    def test_invalid_catalog_metadata_and_links_are_rejected_without_evals(self):
        for defect in ['catalog', 'metadata', 'link']:
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                for directory in ['skills', 'resources', 'policies', 'composition', 'tools', 'tests']:
                    shutil.copytree(ROOT / directory, root / directory,
                                    ignore=shutil.ignore_patterns('__pycache__'))
                target = root / 'skills/my-tdd/SKILL.md'
                if defect == 'catalog':
                    shutil.copytree(root / 'skills/my-tdd', root / 'skills/my-extra')
                elif defect == 'metadata':
                    target.write_text(target.read_text().replace('description:', 'disable-model-invocation: true\ndescription:', 1))
                else:
                    target.write_text(target.read_text() + '\n[missing](missing.md)\n')
                with self.assertRaises((ReleaseError, ValidationError, CompositionError)):
                    build_release(root / 'skills', root / 'releases', release_id='broken',
                                  upstream_id='test', repo_root=root)
                self.assertFalse((root / 'releases/broken').exists())

    def test_catalog_and_invocation_graph_match_approved_spec(self):
        manifest = load_composition_manifest(ROOT / 'composition/manifest.json')
        validate_composition_manifest(manifest, ROOT / 'skills')
        self.assertEqual(MODEL_ENTRIES | MANUAL_ENTRIES,
                         {p.name for p in (ROOT / 'skills').iterdir() if p.is_dir()})
        expected_edges = {
            ('my-grill-me', 'my-grilling', 'method'),
            ('my-grill-with-docs', 'my-grilling', 'method'),
            ('my-grill-with-docs', 'my-domain-modeling', 'method'),
            ('my-grill-with-docs', 'my-to-spec', 'chain'),
            ('my-to-spec', 'my-review-design', 'method'),
            ('my-tech-design', 'my-review-design', 'method'),
            ('my-to-spec', 'my-to-tickets', 'chain'),
            ('my-to-tickets', 'my-implement', 'chain'),
            ('my-implement', 'my-tdd', 'method'),
            ('my-implement', 'my-code-review', 'method'),
            ('my-review-artifact', 'my-review-design', 'method'),
            ('my-review-instructions', 'my-writing-for-agents', 'method'),
            ('my-triage', 'my-grilling', 'method'),
            ('my-triage', 'my-domain-modeling', 'method'),
            ('my-triage', 'my-to-tickets', 'handoff'),
            ('my-triage', 'my-to-spec', 'handoff'),
            ('my-triage', 'my-implement', 'handoff'),
            ('my-wayfinder', 'my-grilling', 'method'),
            ('my-wayfinder', 'my-domain-modeling', 'method'),
            ('my-wayfinder', 'my-prototype', 'method'),
            ('my-wayfinder', 'my-to-spec', 'handoff'),
            ('my-prototype', 'my-implement', 'handoff'),
            ('my-improve-codebase-architecture', 'my-codebase-design', 'method'),
            ('my-improve-codebase-architecture', 'my-grilling', 'method'),
            ('my-improve-codebase-architecture', 'my-domain-modeling', 'method'),
        }
        self.assertEqual(expected_edges, {(caller, edge.skill, edge.kind)
                                         for caller, edges in manifest.callers.items() for edge in edges})
        self.assertEqual(MODEL_ENTRIES,
                         {edge.skill for edges in manifest.callers.values() for edge in edges})
        self.assertEqual((MODEL_ENTRIES | MANUAL_ENTRIES) - {'my-ask-matt'},
                         set(manifest.routable_entries['my-ask-matt']))
        self.assertEqual({'my-tdd', 'my-code-review'},
                         {e.skill for e in manifest.callers['my-implement']})
        self.assertEqual([('my-implement', 'chain')],
                         [(e.skill, e.kind) for e in manifest.callers['my-to-tickets']])

    def test_resources_are_bundled_without_composed_bodies(self):
        with tempfile.TemporaryDirectory() as tmp:
            staged = Path(tmp) / 'release'
            manifest = stage_release_tree(ROOT, staged)
            self.assertEqual([], list((staged / 'skills').glob('*/references/composed')))
            self.assertTrue((staged / 'skills/my-review-artifact/references/shared/humanizer.md').is_file())
            self.assertTrue((staged / 'skills/my-wayfinder/references/shared/research-method.md').is_file())
            self.assertEqual(MODEL_ENTRIES, set(manifest['invocable_skills']))

    def test_three_host_installs_use_declared_invocation_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            release = Path(tmp) / 'r1'
            manifest = stage_release_tree(ROOT, release)
            (release / 'manifest.json').write_text(json.dumps({'release_id': 'r1', **manifest}))
            for host in ['codex', 'cursor', 'claude']:
                home = Path(tmp) / host
                install_release(release, home, target=host)
                state = load_install_state(home / 'my-matt-workflow/install-state.json')
                verify_installed_state(state)
                for name in MODEL_ENTRIES | MANUAL_ENTRIES:
                    folder = home / 'skills' / name
                    if host == 'codex':
                        self.assertIn('allow_implicit_invocation: ' + str(name in MODEL_ENTRIES).lower(),
                                      (folder / 'agents/openai.yaml').read_text())
                        self.assertNotRegex((folder / 'SKILL.md').read_text(), r'\{\{skill-call:my-[a-z0-9-]+\}\}')
                    else:
                        self.assertEqual(name in MANUAL_ENTRIES,
                                         'disable-model-invocation: true' in (folder / 'SKILL.md').read_text().split('---', 2)[1])
                        self.assertFalse((folder / 'agents/openai.yaml').exists())
                    self.assertFalse((folder / 'references/composed').exists())

    def test_build_retains_current_previous_and_installed_releases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'skills/my-a'
            source.mkdir(parents=True)
            (source / 'SKILL.md').write_text('---\nname: my-a\ndescription: test\ndisable-model-invocation: true\n---\n# Test\n')
            releases = root / 'releases'
            home = root / 'host'
            for i in range(1, 5):
                release = build_release(root / 'skills', releases, release_id=f'r{i}',
                                        upstream_id='test', repo_root=root,
                                        current_pointer=root / 'current.json', agent_homes=[home])
                if i == 1:
                    install_release(release, home)
            self.assertEqual({'r1', 'r3', 'r4'}, {p.name for p in releases.iterdir() if p.is_dir()})

    def test_deploy_preserves_release_referenced_by_explicit_custom_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'skills/my-a'
            source.mkdir(parents=True)
            (source / 'SKILL.md').write_text('---\nname: my-a\ndescription: test\ndisable-model-invocation: true\n---\n# Test\n')
            (source / 'agents').mkdir()
            (source / 'agents/openai.yaml').write_text('policy:\n  allow_implicit_invocation: false\n')
            home = root / 'custom-codex'
            for i in range(1, 4):
                release = build_release(root / 'skills', root / 'releases', release_id=f'r{i}',
                                        upstream_id='test', repo_root=root,
                                        current_pointer=root / 'current.json', agent_homes=[home])
                if i == 1:
                    install_release(release, home, target='codex')
            with patch.object(workflow, 'ROOT', root), \
                    patch.object(workflow, 'AGENT_STATE_HOMES', {}), \
                    patch.object(workflow, '_run_all_up_gate'):
                workflow.command_deploy(argparse.Namespace(
                    release_id='r4', upstream_id='test', target='codex', agent_home=str(home)))
            self.assertEqual({'r1', 'r3', 'r4'},
                             {p.name for p in (root / 'releases').iterdir() if p.is_dir()})
            state = load_install_state(home / 'my-matt-workflow/install-state.json')
            verify_installed_state(state)
            self.assertEqual('r4', state['release_id'])


class ReleaseReferenceRegressionTests(unittest.TestCase):
    def fixture(self, root):
        source = root / 'skills/my-a'
        source.mkdir(parents=True)
        (source / 'SKILL.md').write_text('---\nname: my-a\ndescription: test\ndisable-model-invocation: true\n---\n# Test\n')

    def build(self, root, name, **kwargs):
        return build_release(root / 'skills', root / 'releases', release_id=name,
                             upstream_id='test', repo_root=root,
                             current_pointer=root / 'current.json', **kwargs)

    def test_plain_build_preserves_custom_install_and_allows_reinstall(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            self.fixture(root)
            home = Path(tmp) / 'custom-home'
            old = self.build(root, 'r1')
            install_release(old, home)
            with patch.object(workflow, 'ROOT', root), \
                    patch.object(workflow, 'AGENT_STATE_HOMES', {}), \
                    patch.object(workflow, '_run_all_up_gate'):
                for name in ['r2', 'r3', 'r4']:
                    workflow.command_build(argparse.Namespace(release_id=name, upstream_id='test'))
            verify_installed_state(load_install_state(home / 'my-matt-workflow/install-state.json'))
            install_release(old, home)
            self.assertEqual({'r1', 'r3', 'r4'}, {p.name for p in (root / 'releases').iterdir() if p.is_dir()})

    def test_install_during_source_gate_is_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            self.fixture(root)
            home = Path(tmp) / 'custom-home'
            old = self.build(root, 'r1')
            self.build(root, 'r2')
            def gate(snapshot):
                install_release(old, home)
                verify_installed_state(load_install_state(home / 'my-matt-workflow/install-state.json'))
            self.build(root, 'r3', source_gate=gate, agent_homes=[home])
            verify_installed_state(load_install_state(home / 'my-matt-workflow/install-state.json'))
            install_release(old, home)
            self.assertTrue(old.is_dir())

    def test_upgrade_does_not_pin_obsolete_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            self.fixture(root)
            home = Path(tmp) / 'host'
            first = self.build(root, 'r1')
            install_release(first, home)
            second = self.build(root, 'r2')
            install_release(second, home)
            self.build(root, 'r3')
            self.build(root, 'r4')
            self.assertFalse(first.exists())
            self.assertEqual({'r2', 'r3', 'r4'}, {p.name for p in (root / 'releases').iterdir() if p.is_dir()})
            verify_installed_state(load_install_state(home / 'my-matt-workflow/install-state.json'))

    def test_unindexed_legacy_release_is_preserved(self):
        from tools.workflow_lib.release_references import REGISTRY_FILE
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            self.fixture(root)
            home = Path(tmp) / 'host'
            old = self.build(root, 'legacy')
            install_release(old, home)
            # A legacy tree has an install receipt but no discovery registry.
            (root / 'releases' / REGISTRY_FILE).unlink()
            self.build(root, 'r2')
            self.build(root, 'r3')
            self.build(root, 'r4')
            verify_installed_state(load_install_state(home / 'my-matt-workflow/install-state.json'))
            self.assertTrue(old.exists())

    def test_corrupt_reference_registry_stops_deletion_and_install(self):
        from tools.workflow_lib.installer import InstallError
        from tools.workflow_lib.release_references import REGISTRY_FILE
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            self.fixture(root)
            home = Path(tmp) / 'host'
            first = self.build(root, 'r1')
            install_release(first, home)
            second = self.build(root, 'r2')
            state = home / 'my-matt-workflow/install-state.json'
            before = state.read_bytes()
            (root / 'releases' / REGISTRY_FILE).write_text('broken')
            with self.assertRaises(InstallError):
                install_release(second, home)
            self.assertEqual(before, state.read_bytes())
            with self.assertRaises(ReleaseError):
                self.build(root, 'r3')
            verify_installed_state(load_install_state(state))
            self.assertTrue(first.is_dir())

    def test_cleanup_lock_rejects_install_before_side_effects_then_retry_succeeds(self):
        from tools.workflow_lib.installer import InstallError
        from tools.workflow_lib.fs_safety import exclusive_lock
        from tools.workflow_lib.release_references import REFERENCE_LOCK
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            self.fixture(root)
            home = Path(tmp) / 'host'
            first = self.build(root, 'r1')
            install_release(first, home)
            second = self.build(root, 'r2')
            state = home / 'my-matt-workflow/install-state.json'
            before = state.read_bytes()
            with exclusive_lock(root / 'releases', REFERENCE_LOCK):
                with self.assertRaises(InstallError):
                    install_release(second, home)
            self.assertEqual(before, state.read_bytes())
            verify_installed_state(load_install_state(state))
            install_release(second, home)
            verify_installed_state(load_install_state(state))
            self.assertEqual('r2', load_install_state(state)['release_id'])
