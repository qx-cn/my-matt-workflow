import sys,pathlib
r=pathlib.Path('/private/tmp/reviewer09');sys.path[:0]=[str(r/'baseline')]
from tools.workflow_lib.release import build_release
from tools.workflow_lib.installer import install_release,verify_installed_state,load_install_state
out=r/'formal-race-releases';home=r/'formal-race-home'
for n in ['r1','r2','r3']:
 def gate(snapshot):
  install_release(out/'r1',home,target='codex')
  verify_installed_state(load_install_state(home/'my-matt-workflow/install-state.json'))
 build_release(r/'baseline/skills',out,release_id=n,upstream_id='test',repo_root=r/'baseline',source_gate=gate if n=='r3' else None)
print('BASE concurrent install and build retained',sorted(p.name for p in out.iterdir() if p.is_dir()))
