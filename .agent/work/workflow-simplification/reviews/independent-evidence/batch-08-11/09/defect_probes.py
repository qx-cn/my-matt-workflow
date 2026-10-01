import sys,pathlib,shutil
r=pathlib.Path('/private/tmp/reviewer09');sys.path[:0]=[str(r/'current')]
from tools.workflow_lib.release import build_release
for defect in ['catalog','metadata','link','symlink']:
 dest=r/('fault-'+defect)
 for part in ['skills','resources','policies','composition','tools','tests']:
  shutil.copytree(r/'current'/part,dest/part)
 f=dest/'skills/my-tdd/SKILL.md'
 if defect=='catalog':shutil.copytree(dest/'skills/my-tdd',dest/'skills/my-extra')
 if defect=='metadata':f.write_text(f.read_text().replace('description:','disable-model-invocation: true\ndescription:',1))
 if defect=='link':f.write_text(f.read_text()+'\n[missing](missing.md)\n')
 if defect=='symlink':(dest/'skills/my-tdd/escape.md').symlink_to('/private/tmp/reviewer09/probes.log');f.write_text(f.read_text()+'\n[escape](escape.md)\n')
 try:build_release(dest/'skills',dest/'releases',release_id='bad',upstream_id='test',repo_root=dest)
 except Exception as e:print('FAULT',defect,'rejected',type(e).__name__,str(e));assert not (dest/'releases/bad').exists()
 else:raise AssertionError('accepted '+defect)
print('Python',sys.version)
