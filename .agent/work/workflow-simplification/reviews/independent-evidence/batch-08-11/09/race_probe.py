import sys,pathlib,json
root=pathlib.Path('/private/tmp/reviewer09');sys.path[:0]=[str(root/'current')]
from tools.workflow_lib.release import build_release
from tools.workflow_lib.installer import install_release,load_install_state,verify_installed_state
# Baseline valid custom installed old-r1 is referenced but omitted by ordinary build
build_release(root/'current/skills',root/'base-releases',release_id='new-r3',upstream_id='test',repo_root=root/'current',agent_homes=[])
print('BASE-REACHABILITY old-r1 deleted',not (root/'base-releases/old-r1').exists())
try:verify_installed_state(load_install_state(root/'baseline-custom/my-matt-workflow/install-state.json'))
except Exception as e:print('BASE receipt unusable',type(e).__name__,str(e))
# Race uses configured host; source_gate represents time occupied by the real tests.
releases=root/'race-releases';home=root/'race-home'
for rid in ['r1','r2']:
 build_release(root/'current/skills',releases,release_id=rid,upstream_id='test',repo_root=root/'current',agent_homes=[home])
def gate(snapshot):
 install_release(releases/'r1',home,target='codex')
 verify_installed_state(load_install_state(home/'my-matt-workflow/install-state.json'))
 print('RACE installed and verified during gate r1')
build_release(root/'current/skills',releases,release_id='r3',upstream_id='test',repo_root=root/'current',agent_homes=[home],source_gate=gate)
print('RACE configured-home source exists',(releases/'r1').exists())
try:verify_installed_state(load_install_state(home/'my-matt-workflow/install-state.json'))
except Exception as e:print('RACE receipt unusable',type(e).__name__,str(e))
