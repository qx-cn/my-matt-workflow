import sys,pathlib
root=pathlib.Path('/private/tmp/reviewer09');sys.path[:0]=[str(root/'baseline')]
from tools.workflow_lib.release import build_release
from tools.workflow_lib.installer import install_release,load_install_state,verify_installed_state
for rid in ['old-r1','old-r2']:
 r=build_release(root/'baseline/skills',root/'base-releases',release_id=rid,upstream_id='test',repo_root=root/'baseline')
 if rid=='old-r1':
  install_release(r,root/'baseline-custom',target='codex');verify_installed_state(load_install_state(root/'baseline-custom/my-matt-workflow/install-state.json'))
print('BASE build 39 and custom codex install verified')
