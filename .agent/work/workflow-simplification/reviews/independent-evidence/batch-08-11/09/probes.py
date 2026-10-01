import sys,json,pathlib,shutil,subprocess,argparse,os
from unittest.mock import patch
root=pathlib.Path('/private/tmp/reviewer09');sys.path[:0]=[str(root/'current/tools'),str(root/'current')]
from tools import workflow
from tools.workflow_lib.release import build_release
from tools.workflow_lib.installer import install_release,verify_release,load_install_state,verify_installed_state
r=build_release(root/'current/skills', root/'releases',release_id='r1',upstream_id='test',repo_root=root/'current',agent_homes=[])
verify_release(r)
for host in ['codex','cursor','claude']:
 home=root/'homes'/host;install_release(r,home,target=host);s=load_install_state(home/'my-matt-workflow/install-state.json');verify_installed_state(s)
 print('HOST PASS',host,len(s['skills']))
 assert len(s['skills'])==32
 assert not list((home/'skills').glob('*/references/composed'))
 for md in (home/'skills').rglob('*.md'):assert '{{skill-call:my-' not in md.read_text()
# independent corruption probe: projected installed file breaks ownership validation
f=root/'homes/codex/skills/my-tdd/SKILL.md';saved=f.read_bytes();f.write_text(f.read_text()+'\nmodified\n')
try:verify_installed_state(load_install_state(root/'homes/codex/my-matt-workflow/install-state.json'))
except Exception as e:print('FAULT rejected installed tamper',type(e).__name__,str(e))
else:raise AssertionError('tamper accepted')
f.write_bytes(saved)
# declared homes are retained across repeated actual builds
for rid in ['r2','r3']:
 build_release(root/'current/skills',root/'releases',release_id=rid,upstream_id='test',repo_root=root/'current',agent_homes=[root/'homes'/h for h in ['codex','cursor','claude']])
print('KNOWN HOME retained',sorted(p.name for p in (root/'releases').iterdir() if p.is_dir()))
# use exact public CLI helper with only standard homes disabled at system boundary;
# real custom installation root has valid persisted receipt, but build cannot accept it
workflow.ROOT=root/'current';workflow.AGENT_STATE_HOMES={};(root/'current/current.json').write_text('{"release_id":"r3"}')
# CLI helper always uses ROOT/releases, relocate genuine registered ownership roots via new builds below
r=build_release(root/'current/skills',root/'current/releases',release_id='custom-r1',upstream_id='test',repo_root=root/'current',current_pointer=root/'current/current.json',agent_homes=[])
custom=root/'custom-home';install_release(r,custom,target='codex')
with patch.object(workflow,'_run_all_up_gate'):
 for rid in ['custom-r2','custom-r3']:
  workflow.command_build(argparse.Namespace(release_id=rid,upstream_id='test'))
print('CUSTOM reference source exists',pathlib.Path(load_install_state(custom/'my-matt-workflow/install-state.json')['source']).exists())
try:verify_installed_state(load_install_state(custom/'my-matt-workflow/install-state.json'))
except Exception as e:print('CUSTOM verify failure',type(e).__name__,str(e))
try:install_release(root/'current/releases/custom-r3',custom,target='codex')
except Exception as e:print('CUSTOM next install failure',type(e).__name__,str(e))
