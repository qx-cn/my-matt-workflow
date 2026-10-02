import sys, tempfile, json, shutil
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode=True
sys.path.insert(0, '/tmp/outcome-review-code-01')
from tools.workflow_lib import installer, release, fs_safety

def fixture(root):
    s=root/'skills/my-demo';s.mkdir(parents=True)
    (s/'SKILL.md').write_text('---\nname: my-demo\ndescription: test\ndisable-model-invocation: true\n---\n# Demo\n')
    return root

def build(root, name):
    return release.build_release(root/'skills',root/'releases',release_id=name,upstream_id='local',repo_root=root)

with tempfile.TemporaryDirectory(prefix='install-review-legacy-') as t:
    root=fixture(Path(t)/'repo');p=build(root,'v1')
    legacy=Path(t)/'legacy/v1';shutil.copytree(p,legacy)
    m=json.loads((legacy/'manifest.json').read_text());m.pop('target_manifests');m.pop('source_input_digest');(legacy/'manifest.json').write_text(json.dumps(m))
    home=Path(t)/'home';installer.install_release(legacy,home)
    runtime=home/'my-matt-workflow/runtime/v1/tools/workflow.py';runtime.write_text('raise RuntimeError("TAMPERED")\n')
    result=installer.install_release(legacy,home)
    print('LEGACY_RUNTIME_DRIFT',json.dumps({'result':result,'tampered_runtime_remains':runtime.read_text().startswith('raise')}))

with tempfile.TemporaryDirectory(prefix='install-review-links-') as t:
    root=fixture(Path(t)/'repo');p=build(root,'v1');home=Path(t)/'home';installer.install_release(p,home)
    runtime=home/'my-matt-workflow/runtime/v1';(runtime/'unexpected-link').symlink_to('/tmp')
    print('RUNTIME_EXTRA_SYMLINK',json.dumps({'result':installer.install_release(p,home),'symlink_remains':(runtime/'unexpected-link').is_symlink()}))

with tempfile.TemporaryDirectory(prefix='install-review-recovery-') as t:
    root=fixture(Path(t)/'repo');p1=build(root,'v1');home=Path(t)/'home';installer.install_release(p1,home)
    (root/'skills/my-demo/SKILL.md').write_text((root/'skills/my-demo/SKILL.md').read_text()+'v2\n');p2=build(root,'v2')
    refresh=installer.refresh_owned_directory
    def interrupt_after_move(*args,**kwargs):
        refresh(*args,**kwargs)
        if (home/'my-matt-workflow/transaction/backup/my-demo/SKILL.md').is_file():
            raise KeyboardInterrupt('simulated crash after moving old target')
    try:
        with patch.object(installer,'refresh_owned_directory',side_effect=interrupt_after_move):installer.install_release(p2,home)
    except KeyboardInterrupt:pass
    tx=home/'my-matt-workflow/transaction';(tx/'backup/my-demo/SKILL.md').write_text('CORRUPTED BACKUP\n')
    try:fs_safety.verify_owned_directory(tx.parent,tx,purpose='install-transaction')
    except fs_safety.FilesystemSafetyError as exc:print('BACKUP_FULL_BINDING_REJECTS',str(exc))
    installer.recover_interrupted_install(home,skills_home=home/'skills')
    print('ROLLBACK_TAMPER',json.dumps({'restored_text':(home/'skills/my-demo/SKILL.md').read_text().strip(),'transaction_removed':not tx.exists(),'state_release':json.loads((home/'my-matt-workflow/install-state.json').read_text())['release_id']}))

# Control: disable only the newly added current return; retain all other candidate code.
with tempfile.TemporaryDirectory(prefix='install-review-control-') as t:
    root=fixture(Path(t)/'repo');p=build(root,'v1');legacy=Path(t)/'legacy/v1';shutil.copytree(p,legacy)
    m=json.loads((legacy/'manifest.json').read_text());m.pop('target_manifests');m.pop('source_input_digest');(legacy/'manifest.json').write_text(json.dumps(m))
    home=Path(t)/'home';installer.install_release(legacy,home);(home/'my-matt-workflow/runtime/v1/tools/workflow.py').write_text('TAMPERED\n')
    source=Path('/tmp/outcome-review-code-01/tools/workflow_lib/installer.py').read_text()
    start=source.index('        if (previous_state.get("version") == 2 and')
    end=source.index('            return "current"',start)+len('            return "current"')
    scope={'__name__':'tools.workflow_lib.review_control_installer','__package__':'tools.workflow_lib'}
    exec(compile(source[:start]+source[end:],'/tmp/outcome-review-code-01/tools/workflow_lib/installer.py','exec'),scope)
    try:scope['install_release'](legacy,home)
    except installer.InstallError as exc:print('SHORTCUT_DISABLED_CONTROL',str(exc))
    except scope['InstallError'] as exc:print('SHORTCUT_DISABLED_CONTROL',str(exc),'cause',str(exc.__cause__))

from tools.workflow_lib import projection
import time
start=time.monotonic();comparisons=0
with tempfile.TemporaryDirectory(prefix='install-review-projections-') as t:
    for skill in sorted(Path('/tmp/outcome-review-code-01/skills').iterdir()):
        if not skill.is_dir():continue
        for target in projection.TARGETS:
            dest=Path(t)/target/skill.name;shutil.copytree(skill,dest)
            projection.project_skill_directory(dest,target)
            assert projection.directory_inventory(dest)==projection.projected_skill_inventory(skill,target),(skill.name,target)
            comparisons+=1
print('SOURCE_PHYSICAL_PROJECTION',json.dumps({'comparisons':comparisons,'elapsed_seconds':round(time.monotonic()-start,3)}))

# Exercise the unchanged deploy gate with an actual test failure, without changing source bytes.
import importlib.util, argparse, os, contextlib, io
with tempfile.TemporaryDirectory(prefix='install-review-unchanged-gate-') as t:
    root=fixture(Path(t)/'repo');(root/'tests').mkdir()
    (root/'tests/test_gate.py').write_text('import os,unittest\nclass Gate(unittest.TestCase):\n def test_gate(self): self.assertNotEqual(os.environ.get("INSTALL_REVIEW_FAIL_GATE"),"1")\n')
    spec=importlib.util.spec_from_file_location('review_cli','/tmp/outcome-review-code-01/tools/workflow.py');module=importlib.util.module_from_spec(spec)
    sys.path.insert(0,'/tmp/outcome-review-code-01/tools');spec.loader.exec_module(module);module.ROOT=root;module.AGENT_STATE_HOMES={}
    home=Path(t)/'home';args=argparse.Namespace(release_id='v1',upstream_id='local',target='auto',agent_home=str(home))
    with contextlib.redirect_stdout(io.StringIO()):module.command_deploy(args)
    state=home/'my-matt-workflow/install-state.json';old_state=state.read_bytes();args.release_id=None
    with patch.dict(os.environ,{'INSTALL_REVIEW_FAIL_GATE':'1'}):
        try:
            with contextlib.redirect_stdout(io.StringIO()):module.command_deploy(args)
        except SystemExit as exc:print('UNCHANGED_ACTUAL_GATE',json.dumps({'exit':exc.code,'host_state_unchanged':old_state==state.read_bytes()}))
