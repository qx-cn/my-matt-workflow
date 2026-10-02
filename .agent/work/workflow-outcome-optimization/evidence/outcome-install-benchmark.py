import argparse
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
from unittest.mock import patch

code_root = Path(sys.argv[1])
sys.path.insert(0, str(code_root / 'tools'))
import workflow
from workflow_lib import installer, release

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp) / 'repo'
    skill = root / 'skills/my-demo'
    skill.mkdir(parents=True)
    (skill / 'SKILL.md').write_text('---\nname: my-demo\ndescription: test\ndisable-model-invocation: true\n---\n# Demo\n')
    package = release.build_release(root / 'skills', root / 'releases', release_id='v1',
                                    upstream_id='local', repo_root=root)
    (root / 'current.json').write_text('{"release_id":"v1"}')
    home = Path(tmp) / 'home'
    installer.install_release(package, home)
    workflow.ROOT = root
    workflow.AGENT_STATE_HOMES = {}
    checks = []
    counts = {'release_verifications':0, 'source_match_packaging':0,
              'copytree_calls':0, 'projection_tree_copies':0, 'projection_tree_operations':0}
    elapsed = {'release_verification_seconds':0, 'source_packaging_seconds':0}
    verify = installer.verify_release
    manifest = release.source_manifest
    copytree = shutil.copytree
    def timed_verify(*args, **kwargs):
        counts['release_verifications'] += 1
        start = time.perf_counter()
        try: return verify(*args, **kwargs)
        finally: elapsed['release_verification_seconds'] += time.perf_counter() - start
    def timed_manifest(*args, **kwargs):
        counts['source_match_packaging'] += 1
        start = time.perf_counter()
        try: return manifest(*args, **kwargs)
        finally: elapsed['source_packaging_seconds'] += time.perf_counter() - start
    def counted_copy(*args, **kwargs):
        counts['copytree_calls'] += 1
        destination = str(args[1])
        if any(x in destination for x in ('-projection-', 'my-matt-verify-')):
            counts['projection_tree_copies'] += 1
            if Path(destination).name == 'skills':
                counts['projection_tree_operations'] += 1
        return copytree(*args, **kwargs)
    def check(**kwargs):
        checks.append(str(kwargs.get('root', workflow.ROOT)))
        return {'status':'valid'}
    start = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()), \
         patch.object(workflow, '_run_all_up_gate', side_effect=check), \
         patch.object(installer, 'verify_release', side_effect=timed_verify), \
         patch.object(release, 'source_manifest', side_effect=timed_manifest), \
         patch.object(shutil, 'copytree', side_effect=counted_copy):
        workflow.command_deploy(argparse.Namespace(release_id=None, upstream_id='local', target='auto', agent_home=str(home)))
    print(json.dumps({'scenario':'unchanged minimal fixture deploy, suite stubbed for phase isolation',
                      'implementation':str(code_root), 'counts':{**counts, 'suite_gate_calls':len(checks)},
                      'seconds':{**elapsed, 'operation':time.perf_counter()-start}}, sort_keys=True))
