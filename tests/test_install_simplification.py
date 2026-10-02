"""Public install/deploy regressions and byte-exact projection checks."""
import argparse
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.workflow_lib import installer, release, projection

ROOT = Path(__file__).resolve().parents[1]


def fixture(root):
    skill = root / 'skills/my-demo'
    skill.mkdir(parents=True)
    (skill / 'SKILL.md').write_text('---\nname: my-demo\ndescription: test\ndisable-model-invocation: true\n---\n# Demo\n')
    return root


def cli(root):
    spec = importlib.util.spec_from_file_location('simplified_workflow_cli', ROOT / 'tools/workflow.py')
    module = importlib.util.module_from_spec(spec)
    with patch.object(sys, 'path', [str(ROOT / 'tools'), *sys.path]):
        spec.loader.exec_module(module)
    module.ROOT = root
    module.AGENT_STATE_HOMES = {}
    return module


class SimplifiedInstallTests(unittest.TestCase):
    def test_projection_manifest_matches_physical_bytes_without_copytree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture(Path(tmp) / 'repo')
            skill = root / 'skills/my-demo'
            (skill / 'agents').mkdir()
            (skill / 'agents/openai.yaml').write_text('metadata')
            (skill / 'nested').mkdir()
            (skill / 'nested/demo.md').write_bytes(b'{{skill-call:my-demo}}\r\n')
            for target in projection.TARGETS:
                with self.subTest(target=target):
                    staged = Path(tmp) / target
                    shutil.copytree(skill, staged)
                    projection.project_skill_directory(staged, target)
                    expected = projection.directory_inventory(staged)
                    with patch.object(shutil, 'copytree', side_effect=AssertionError('projection copied tree')):
                        self.assertEqual(expected, projection.projected_skill_inventory(skill, target))

    def test_changed_deploy_runs_one_gate_on_packaged_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture(Path(tmp) / 'repo')
            module = cli(root)
            roots = []
            def gate(**kwargs):
                roots.append(kwargs.get('root', module.ROOT))
                self.assertEqual((root / 'skills/my-demo/SKILL.md').read_bytes(),
                                 (roots[-1] / 'skills/my-demo/SKILL.md').read_bytes())
                return {'status': 'valid'}
            with patch.object(module, '_run_all_up_gate', side_effect=gate):
                module.command_deploy(argparse.Namespace(release_id='v1', upstream_id='local',
                                                        target='auto', agent_home=str(Path(tmp) / 'home')))
            self.assertEqual(1, len(roots))
            self.assertNotEqual(root, roots[0])

    def test_unchanged_deploy_neither_stages_source_nor_rewrites_host(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture(Path(tmp) / 'repo')
            package = release.build_release(root / 'skills', root / 'releases', release_id='v1',
                                            upstream_id='local', repo_root=root,
                                            current_pointer=root / 'current.json')
            home = Path(tmp) / 'home'
            installer.install_release(package, home)
            state_path = home / 'my-matt-workflow/install-state.json'
            state = state_path.read_bytes()
            inode = (home / 'skills/my-demo/SKILL.md').stat().st_ino
            module = cli(root)
            def reject_packaging(*args, **kwargs):
                raise AssertionError('repacked unchanged source')
            with patch.object(module, '_run_all_up_gate', return_value={'status':'valid'}) as gate, \
                 patch.dict(module.release_matches_source.__globals__,
                            {'source_manifest': reject_packaging}):
                module.command_deploy(argparse.Namespace(release_id=None, upstream_id='local',
                                                        target='auto', agent_home=str(home)))
            self.assertEqual(1, gate.call_count)
            self.assertEqual(state, state_path.read_bytes())
            self.assertEqual(inode, (home / 'skills/my-demo/SKILL.md').stat().st_ino)

    def test_public_deploy_runs_actual_suite_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture(Path(tmp) / 'repo')
            counter = Path(tmp) / 'suite-counter'
            (root / 'tests').mkdir()
            (root / 'tests/test_gate.py').write_text(
                'import unittest\nfrom pathlib import Path\n'
                'class Gate(unittest.TestCase):\n'
                ' def test_runs(self):\n'
                f'  p = Path({str(counter)!r})\n'
                '  p.write_text(str(int(p.read_text()) + 1) if p.exists() else "1")\n')
            module = cli(root)
            module.command_deploy(argparse.Namespace(release_id='actual-suite', upstream_id='local',
                                                    target='auto', agent_home=str(Path(tmp) / 'home')))
            self.assertEqual('1', counter.read_text())
            installer.verify_release(root / 'releases/actual-suite')

    def test_failed_suite_does_not_publish_or_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture(Path(tmp) / 'repo')
            (root / 'tests').mkdir()
            (root / 'tests/test_gate.py').write_text(
                'import unittest\nclass Gate(unittest.TestCase):\n'
                ' def test_fails(self): self.fail("candidate is invalid")\n')
            module = cli(root)
            home = Path(tmp) / 'home'
            with self.assertRaises(SystemExit):
                module.command_deploy(argparse.Namespace(release_id='bad', upstream_id='local',
                                                        target='auto', agent_home=str(home)))
            self.assertFalse((root / 'current.json').exists())
            self.assertFalse((root / 'releases/bad').exists())
            self.assertFalse(home.exists())

    def test_context_reuses_same_bytes_and_revalidates_drift_and_other_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture(Path(tmp) / 'repo')
            first = release.build_release(root / 'skills', root / 'releases', release_id='v1',
                                          upstream_id='local', repo_root=root)
            second = release.build_release(root / 'skills', root / 'releases', release_id='v2',
                                           upstream_id='local', repo_root=root)
            context = installer.ReleaseValidationContext()
            with patch.object(installer, 'verify_release', wraps=installer.verify_release) as verify:
                context.verify(first)
                context.verify(first)
                context.verify(second)
                self.assertEqual(2, verify.call_count)
                (first / 'skills/my-demo/SKILL.md').write_text('tampered')
                with self.assertRaises(installer.InstallError):
                    context.verify(first)
                self.assertEqual(3, verify.call_count)

    def test_install_rechecks_cached_package_inside_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture(Path(tmp) / 'repo')
            package = release.build_release(root / 'skills', root / 'releases', release_id='v1',
                                            upstream_id='local', repo_root=root)
            context = installer.ReleaseValidationContext()
            context.verify(package)
            from tools.workflow_lib import fs_safety
            original_lock = installer.exclusive_lock
            from contextlib import contextmanager
            @contextmanager
            def mutate_under_lock(directory, name):
                with original_lock(directory, name):
                    if name == installer.REFERENCE_LOCK:
                        (package / 'skills/my-demo/SKILL.md').write_text('mutated after outer validation')
                    yield
            home = Path(tmp) / 'home'
            with patch.object(installer, 'exclusive_lock', side_effect=mutate_under_lock):
                with self.assertRaises(installer.InstallError):
                    installer.install_release(package, home, validation_context=context)
            self.assertFalse((home / 'skills/my-demo').exists())
            self.assertFalse((home / 'my-matt-workflow/install-state.json').exists())

    def test_same_release_install_verifies_once_and_detects_host_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture(Path(tmp) / 'repo')
            package = release.build_release(root / 'skills', root / 'releases', release_id='v1',
                                            upstream_id='local', repo_root=root)
            home = Path(tmp) / 'home'
            installer.install_release(package, home)
            with patch.object(installer, 'verify_release', wraps=installer.verify_release) as verify:
                self.assertEqual('current', installer.install_release(package, home))
                self.assertEqual(1, verify.call_count)
            (home / 'skills/my-demo/SKILL.md').write_text('tampered')
            with self.assertRaises(installer.InstallError):
                installer.install_release(package, home)

    def test_doctor_validates_shared_release_once_and_reports_each_host(self):
        from tools.workflow_lib.doctor import diagnose_repository
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture(Path(tmp) / 'repo')
            package = release.build_release(root / 'skills', root / 'releases', release_id='v1',
                                            upstream_id='local', repo_root=root,
                                            current_pointer=root / 'current.json')
            homes = {name: Path(tmp) / name for name in ('host-a', 'host-b')}
            for home in homes.values():
                installer.install_release(package, home)
            with patch.object(installer, 'verify_release', wraps=installer.verify_release) as verify:
                report = diagnose_repository(root, homes)
                self.assertEqual(1, verify.call_count)
            self.assertEqual(True, report['current_release']['source_match'])
            self.assertEqual({'valid'}, {host['status'] for host in report['hosts'].values()})
            (homes['host-b'] / 'skills/my-demo/SKILL.md').write_text('tampered')
            report = diagnose_repository(root, homes)
            self.assertEqual('valid', report['hosts']['host-a']['status'])
            self.assertEqual('invalid', report['hosts']['host-b']['status'])

    def test_digest_binds_tests_config_links_permissions_and_upstream(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture(Path(tmp) / 'repo')
            package = release.build_release(root / 'skills', root / 'releases', release_id='v1',
                                            upstream_id='local', repo_root=root)
            self.assertTrue(release.release_matches_source(package, root / 'skills', upstream_id='local'))
            self.assertFalse(release.release_matches_source(package, root / 'skills', upstream_id='changed'))
            added = root / 'tests/test_new.py'
            added.parent.mkdir()
            added.write_text('test configuration')
            self.assertFalse(release.release_matches_source(package, root / 'skills', upstream_id='local'))
            added.unlink()
            self.assertTrue(release.release_matches_source(package, root / 'skills', upstream_id='local'))
            config = root / 'build-config.json'
            config.write_text('{"setting": true}')
            self.assertFalse(release.release_matches_source(package, root / 'skills', upstream_id='local'))
            config.unlink()
            builder = root / 'tools/projection_override.py'
            builder.parent.mkdir()
            builder.write_text('PROTOCOL = 2')
            self.assertFalse(release.release_matches_source(package, root / 'skills', upstream_id='local'))
            builder.unlink()
            link = root / 'config-link'
            link.symlink_to('skills/my-demo/SKILL.md')
            self.assertFalse(release.release_matches_source(package, root / 'skills', upstream_id='local'))
            link.unlink()
            skill = root / 'skills/my-demo/SKILL.md'
            skill.chmod(0o700)
            self.assertFalse(release.release_matches_source(package, root / 'skills', upstream_id='local'))

    def test_legacy_digest_missing_uses_full_source_comparison(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture(Path(tmp) / 'repo')
            package = release.build_release(root / 'skills', root / 'releases', release_id='v1',
                                            upstream_id='local', repo_root=root)
            manifest_path = package / 'manifest.json'
            manifest = json.loads(manifest_path.read_text())
            del manifest['source_input_digest']
            manifest_path.write_text(json.dumps(manifest))
            with patch.object(release, 'source_manifest', wraps=release.source_manifest) as stage:
                self.assertTrue(release.release_matches_source(package, root / 'skills', upstream_id='local'))
                self.assertEqual(1, stage.call_count)

    def test_release_verification_computes_projection_without_copytree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture(Path(tmp) / 'repo')
            package = release.build_release(root / 'skills', root / 'releases', release_id='v1',
                                            upstream_id='local', repo_root=root)
            with patch.object(shutil, 'copytree', side_effect=AssertionError('verify copied projection')):
                installer.verify_release(package)
            link = package / 'skills/my-demo/link'
            link.symlink_to('SKILL.md')
            with self.assertRaises(installer.InstallError):
                installer.verify_release(package)

    def test_unbound_or_forged_digest_cannot_hide_stale_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture(Path(tmp) / 'repo')
            package = release.build_release(root / 'skills', root / 'releases', release_id='v1',
                                            upstream_id='local', repo_root=root)
            (root / 'skills/my-demo/SKILL.md').write_text(
                (root / 'skills/my-demo/SKILL.md').read_text() + 'New requirement\n')
            manifest_path = package / 'manifest.json'
            manifest = json.loads(manifest_path.read_text())
            manifest['source_input_digest'] = release.source_input_digest(root, upstream_id='local')
            manifest_path.write_text(json.dumps(manifest))
            with patch.object(release, 'source_manifest', wraps=release.source_manifest) as stage:
                self.assertFalse(release.release_matches_source(package, root / 'skills', upstream_id='local'))
                self.assertEqual(1, stage.call_count)

    def test_context_detects_drift_during_validation_and_does_not_share_mutable_claims(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture(Path(tmp) / 'repo')
            package = release.build_release(root / 'skills', root / 'releases', release_id='v1',
                                            upstream_id='local', repo_root=root)
            context = installer.ReleaseValidationContext()
            returned = context.verify(package)
            returned['skills'].clear()
            self.assertEqual({'my-demo'}, set(context.verify(package)['skills']))
            verify = installer.verify_release
            def mutate_after_verify(path):
                result = verify(path)
                (path / 'skills/my-demo/SKILL.md').write_text('concurrent mutation')
                return result
            with patch.object(installer, 'verify_release', side_effect=mutate_after_verify):
                with self.assertRaisesRegex(installer.InstallError, '漂移'):
                    installer.ReleaseValidationContext().verify(package)

    def test_legacy_manifest_runtime_changes_cannot_return_current(self):
        for mutation in ('modify', 'delete', 'add'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                root = fixture(Path(tmp) / 'repo')
                package = release.build_release(root / 'skills', root / 'releases', release_id='v1',
                                                upstream_id='local', repo_root=root)
                manifest_path = package / 'manifest.json'
                manifest = json.loads(manifest_path.read_text())
                del manifest['target_manifests']
                del manifest['source_input_digest']
                manifest_path.write_text(json.dumps(manifest))
                home = Path(tmp) / 'home'
                installer.install_release(package, home)
                runtime = home / 'my-matt-workflow/runtime/v1'
                entry = runtime / 'tools/workflow.py'
                if mutation == 'modify':
                    entry.write_text('tampered runtime')
                elif mutation == 'delete':
                    entry.unlink()
                else:
                    (runtime / 'unexpected.py').write_text('unexpected runtime')
                with self.assertRaises(installer.InstallError):
                    installer.install_release(package, home)

    def test_runtime_extra_symlink_is_rejected_before_current(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture(Path(tmp) / 'repo')
            package = release.build_release(root / 'skills', root / 'releases', release_id='v1',
                                            upstream_id='local', repo_root=root)
            home = Path(tmp) / 'home'
            installer.install_release(package, home)
            runtime = home / 'my-matt-workflow/runtime/v1'
            (runtime / 'unexpected-link').symlink_to(Path(tmp))
            with self.assertRaises(installer.InstallError):
                installer.install_release(package, home)
            self.assertTrue((runtime / 'unexpected-link').is_symlink())

    def test_rollback_material_is_verified_before_target_or_evidence_mutation(self):
        for refreshed in (False, True):
            for corrupt in (False, True):
                with self.subTest(refreshed=refreshed, corrupt=corrupt), tempfile.TemporaryDirectory() as tmp:
                    root = fixture(Path(tmp) / 'repo')
                    first = release.build_release(root / 'skills', root / 'releases', release_id='v1',
                                                  upstream_id='local', repo_root=root)
                    home = Path(tmp) / 'home'
                    installer.install_release(first, home)
                    original = (home / 'skills/my-demo/SKILL.md').read_bytes()
                    (root / 'skills/my-demo/SKILL.md').write_text(
                        (root / 'skills/my-demo/SKILL.md').read_text() + 'v2\n')
                    second = release.build_release(root / 'skills', root / 'releases', release_id='v2',
                                                   upstream_id='local', repo_root=root)
                    refresh = installer.refresh_owned_directory
                    def stop_after_old_move(*args, **kwargs):
                        if (home / 'my-matt-workflow/transaction/backup/my-demo/SKILL.md').exists():
                            if refreshed:
                                refresh(*args, **kwargs)
                            raise KeyboardInterrupt('interrupted during old target move')
                        return refresh(*args, **kwargs)
                    with patch.object(installer, 'refresh_owned_directory', side_effect=stop_after_old_move):
                        with self.assertRaises(KeyboardInterrupt):
                            installer.install_release(second, home)
                    transaction = home / 'my-matt-workflow/transaction'
                    backup = transaction / 'backup/my-demo/SKILL.md'
                    target = home / 'skills/my-demo/SKILL.md'
                    current = target.read_bytes()
                    state = (home / 'my-matt-workflow/install-state.json').read_bytes()
                    if corrupt:
                        backup.write_text('CORRUPTED BACKUP')
                        with self.assertRaises(installer.InstallError):
                            installer.recover_interrupted_install(home)
                        self.assertTrue(transaction.exists())
                        self.assertEqual(current, target.read_bytes())
                        self.assertEqual(state, (home / 'my-matt-workflow/install-state.json').read_bytes())
                        self.assertEqual('CORRUPTED BACKUP', backup.read_text())
                    else:
                        installer.recover_interrupted_install(home)
                        self.assertEqual(original, target.read_bytes())
                        self.assertFalse(transaction.exists())

    def test_legacy_v4_without_new_receipt_binding_still_verifies_backup(self):
        for corrupt in (False, True):
            with self.subTest(corrupt=corrupt), tempfile.TemporaryDirectory() as tmp:
                root = fixture(Path(tmp) / 'repo')
                first = release.build_release(root / 'skills', root / 'releases', release_id='v1',
                                              upstream_id='local', repo_root=root)
                home = Path(tmp) / 'home'
                installer.install_release(first, home)
                second = release.build_release(root / 'skills', root / 'releases', release_id='v2',
                                               upstream_id='local', repo_root=root)
                rename = Path.rename
                def stop_after_stage(path, destination):
                    result = rename(path, destination)
                    if path.parent.name == 'staged' and path.name == 'my-demo':
                        raise KeyboardInterrupt('legacy v4 interruption')
                    return result
                with patch.object(Path, 'rename', stop_after_stage):
                    with self.assertRaises(KeyboardInterrupt):
                        installer.install_release(second, home)
                transaction = home / 'my-matt-workflow/transaction'
                journal_path = transaction / 'journal.json'
                journal = json.loads(journal_path.read_text())
                del journal['previous_state_sha256']
                journal_path.write_text(json.dumps(journal))
                installer.register_owned_directory(transaction.parent, transaction,
                                                   purpose='install-transaction',
                                                   control_paths=('journal.json',))
                backup = transaction / 'backup/my-demo/SKILL.md'
                if corrupt:
                    backup.write_text('corrupted legacy backup')
                    with self.assertRaises(installer.InstallError):
                        installer.recover_interrupted_install(home)
                    self.assertTrue(transaction.exists())
                else:
                    installer.recover_interrupted_install(home)
                    self.assertFalse(transaction.exists())

    def test_committed_state_cleanup_checks_actual_new_targets(self):
        for corrupt in (False, True):
            with self.subTest(corrupt=corrupt), tempfile.TemporaryDirectory() as tmp:
                root = fixture(Path(tmp) / 'repo')
                first = release.build_release(root / 'skills', root / 'releases', release_id='v1',
                                              upstream_id='local', repo_root=root)
                home = Path(tmp) / 'home'
                installer.install_release(first, home)
                second = release.build_release(root / 'skills', root / 'releases', release_id='v2',
                                               upstream_id='local', repo_root=root)
                replace = Path.replace
                def stop_after_state_commit(path, destination):
                    result = replace(path, destination)
                    if path.name == 'install-state.json':
                        raise KeyboardInterrupt('interrupted after state commit')
                    return result
                with patch.object(Path, 'replace', stop_after_state_commit):
                    with self.assertRaises(KeyboardInterrupt):
                        installer.install_release(second, home)
                transaction = home / 'my-matt-workflow/transaction'
                target = home / 'skills/my-demo/SKILL.md'
                if corrupt:
                    target.write_text('corrupted committed target')
                    with self.assertRaises(installer.InstallError):
                        installer.recover_interrupted_install(home)
                    self.assertTrue(transaction.exists())
                    self.assertEqual('corrupted committed target', target.read_text())
                else:
                    installer.recover_interrupted_install(home)
                    self.assertFalse(transaction.exists())
                    self.assertEqual('v2', json.loads((home / 'my-matt-workflow/install-state.json').read_text())['release_id'])

    def test_migration_rollback_proves_old_home_backups_before_any_moves(self):
        for corrupt in (False, True):
            with self.subTest(corrupt=corrupt), tempfile.TemporaryDirectory() as tmp:
                root = fixture(Path(tmp) / 'repo')
                first = release.build_release(root / 'skills', root / 'releases', release_id='v1',
                                              upstream_id='local', repo_root=root)
                home = Path(tmp) / 'home'
                old_home = Path(tmp) / 'old-skills'
                new_home = Path(tmp) / 'new-skills'
                installer.install_release(first, home, skills_home=old_home)
                original = (old_home / 'my-demo/SKILL.md').read_bytes()
                second = release.build_release(root / 'skills', root / 'releases', release_id='v2',
                                               upstream_id='local', repo_root=root)
                refresh = installer.refresh_owned_directory
                def stop_after_legacy_move(*args, **kwargs):
                    result = refresh(*args, **kwargs)
                    if (home / 'my-matt-workflow/transaction/legacy-backup/my-demo').exists():
                        raise KeyboardInterrupt('interrupted during home migration')
                    return result
                with patch.object(installer, 'refresh_owned_directory', side_effect=stop_after_legacy_move):
                    with self.assertRaises(KeyboardInterrupt):
                        installer.install_release(second, home, skills_home=new_home)
                transaction = home / 'my-matt-workflow/transaction'
                backup = transaction / 'legacy-backup/my-demo/SKILL.md'
                if corrupt:
                    backup.write_text('corrupted old home backup')
                    with self.assertRaises(installer.InstallError):
                        installer.recover_interrupted_install(home)
                    self.assertTrue(transaction.exists())
                    self.assertFalse((old_home / 'my-demo').exists())
                    self.assertTrue((new_home / 'my-demo/SKILL.md').exists())
                else:
                    installer.recover_interrupted_install(home)
                    self.assertEqual(original, (old_home / 'my-demo/SKILL.md').read_bytes())
                    self.assertFalse((new_home / 'my-demo').exists())
                    self.assertFalse(transaction.exists())

    def test_initial_install_rejects_internal_parent_links_before_any_host_write(self):
        for parent in ('my-matt-workflow', 'my-matt-workflow/runtime'):
            with self.subTest(parent=parent), tempfile.TemporaryDirectory() as tmp:
                root = fixture(Path(tmp) / 'repo')
                package = release.build_release(root / 'skills', root / 'releases', release_id='v1',
                                                upstream_id='local', repo_root=root)
                home = Path(tmp) / 'home'
                outside = Path(tmp) / 'outside'
                outside.mkdir()
                (outside / 'sentinel').write_bytes(b'existing outside bytes')
                linked = home / parent
                linked.parent.mkdir(parents=True)
                linked.symlink_to(outside, target_is_directory=True)
                def tree(directory):
                    return {str(path.relative_to(directory)): ('link:' + str(path.readlink())
                            if path.is_symlink() else path.read_bytes() if path.is_file() else 'directory')
                            for path in directory.rglob('*')}
                before_outside = tree(outside)
                before_home = tree(home)
                with self.assertRaises(installer.InstallError):
                    installer.install_release(package, home)
                self.assertEqual(before_outside, tree(outside))
                self.assertEqual(before_home, tree(home))
                with self.assertRaises(installer.InstallError):
                    installer.recover_interrupted_install(home)
                self.assertEqual(before_outside, tree(outside))
                self.assertEqual(before_home, tree(home))

    def test_explicit_host_root_alias_is_allowed_but_internal_links_are_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture(Path(tmp) / 'repo')
            package = release.build_release(root / 'skills', root / 'releases', release_id='v1',
                                            upstream_id='local', repo_root=root)
            actual_home = Path(tmp) / 'actual-home'
            actual_home.mkdir()
            alias = Path(tmp) / 'explicit-home-alias'
            alias.symlink_to(actual_home, target_is_directory=True)
            self.assertEqual('installed', installer.install_release(package, alias))
            state = installer.load_install_state(actual_home / 'my-matt-workflow/install-state.json')
            self.assertEqual(str(actual_home.resolve() / 'my-matt-workflow/runtime/v1/tools/workflow.py'), state['runtime_entry'])
            installer.verify_installed_state(state, state_home=alias)
            installer.recover_interrupted_install(alias)
            self.assertEqual('current', installer.install_release(package, alias))

    def test_recorded_old_skill_root_drift_rejects_before_any_install_write(self):
        for version in (1, 2):
            for target in (None, 'codex', 'cursor', 'claude'):
                for layout in ('custom', 'default'):
                    with self.subTest(version=version, target=target, layout=layout), tempfile.TemporaryDirectory() as tmp:
                        root = fixture(Path(tmp) / 'repo')
                        agents = root / 'skills/my-demo/agents'
                        agents.mkdir()
                        (agents / 'openai.yaml').write_text('policy:\n  allow_implicit_invocation: false\n')
                        package = release.build_release(root / 'skills', root / 'releases', release_id='v1',
                                                        upstream_id='local', repo_root=root)
                        home = Path(tmp) / 'home'
                        old_home = home / ('legacy-skills' if layout == 'custom' else 'skills')
                        new_home = home / ('skills' if layout == 'custom' else 'new-skills')
                        installer.install_release(package, home, target=target, skills_home=old_home)
                        state_path = home / 'my-matt-workflow/install-state.json'
                        if version == 1:
                            state = json.loads(state_path.read_text())
                            for name in ('version', 'managed_inventory', 'manifest_sha256'):
                                del state[name]
                            state_path.write_text(json.dumps(state))
                        outside = Path(tmp) / 'outside'
                        old_home.rename(outside)
                        (outside / 'sentinel').write_bytes(b'outside sentinel')
                        old_home.symlink_to(outside, target_is_directory=True)
                        def tree(directory):
                            return {str(path.relative_to(directory)):
                                    ('link:' + str(path.readlink()) if path.is_symlink()
                                     else path.read_bytes() if path.is_file() else 'directory')
                                    for path in directory.rglob('*')}
                        (home / 'my-matt-workflow/.install.lock').unlink()
                        before = (tree(home), tree(outside), state_path.read_bytes())
                        with self.assertRaises(installer.InstallError):
                            installer.install_release(package, home, target=target, skills_home=new_home)
                        self.assertEqual(before, (tree(home), tree(outside), state_path.read_bytes()))
                        self.assertFalse((home / 'my-matt-workflow/transaction').exists())

    def test_canonical_cross_host_old_skill_root_and_selected_alias_still_migrate(self):
        for version in (1, 2):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as tmp:
                root = fixture(Path(tmp) / 'repo')
                package = release.build_release(root / 'skills', root / 'releases', release_id='v1',
                                                upstream_id='local', repo_root=root)
                home = Path(tmp) / 'home'
                actual_old_home = Path(tmp) / 'another-host/skills'
                actual_old_home.mkdir(parents=True)
                selected_alias = Path(tmp) / 'explicit-old-root-alias'
                selected_alias.symlink_to(actual_old_home, target_is_directory=True)
                installer.install_release(package, home, skills_home=selected_alias)
                state_path = home / 'my-matt-workflow/install-state.json'
                state = json.loads(state_path.read_text())
                self.assertEqual(str(actual_old_home.resolve()), state['skills_home'])
                if version == 1:
                    for name in ('version', 'managed_inventory', 'manifest_sha256'):
                        del state[name]
                    state_path.write_text(json.dumps(state))
                self.assertEqual('installed', installer.install_release(package, home))
                self.assertFalse((actual_old_home / 'my-demo').exists())
                self.assertEqual('current', installer.install_release(package, home))
                installer.recover_interrupted_install(home)

    def test_recorded_skill_root_ancestor_link_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture(Path(tmp) / 'repo')
            package = release.build_release(root / 'skills', root / 'releases', release_id='v1',
                                            upstream_id='local', repo_root=root)
            home = Path(tmp) / 'home'
            old_parent = home / 'nested'
            installer.install_release(package, home, skills_home=old_parent / 'skills')
            state_path = home / 'my-matt-workflow/install-state.json'
            state = installer.load_install_state(state_path)
            outside = Path(tmp) / 'outside'
            old_parent.rename(outside)
            old_parent.symlink_to(outside, target_is_directory=True)
            contents = (outside / 'skills/my-demo/SKILL.md').read_bytes()
            receipt = state_path.read_bytes()
            with self.assertRaises(installer.InstallError):
                installer.verify_installed_state(state, state_home=home)
            with self.assertRaises(installer.InstallError):
                installer.install_release(package, home)
            self.assertEqual(contents, (outside / 'skills/my-demo/SKILL.md').read_bytes())
            self.assertEqual(receipt, state_path.read_bytes())
            self.assertFalse((home / 'skills').exists())
            self.assertFalse((home / 'my-matt-workflow/transaction').exists())


if __name__ == '__main__':
    unittest.main()
