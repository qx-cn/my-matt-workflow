from pathlib import Path
import json,subprocess,shutil,os,time,hashlib
root=Path('/private/tmp/reviewer08-isolated');cli=root/'current/tools/workflow.py';fixture=root/'current/tests/fixtures/workflow_simplification';repo=root/'probe-project'
subprocess.run(['git','clone','-q',str(fixture/'baseline.bundle'),str(repo)],check=True)
shutil.copytree(fixture/'legacy_project',repo,dirs_exist_ok=True)
def git(*args): return subprocess.check_output(['git',*args],cwd=repo,text=True).strip()
for k,v in [('user.name','Independent reviewer'),('user.email','reviewer@example.invalid')]:git('config',k,v)
def call(*args):
 p=subprocess.run(['python3',str(cli),*args,'--repo',str(repo)],capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
 print(json.dumps({'argv':list(args),'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr},ensure_ascii=False))
 return p
handoff=repo/'.agent/work/legacy-a/handoffs/original.md';handoff.parent.mkdir();handoff.write_bytes(b'original handoff\n')
completed={str(p.relative_to(repo)):p.read_bytes() for p in (repo/'.agent/work/legacy-a').rglob('*') if p.is_file() and 'legacy-a-02' in p.name}
# Preserve an independently staged content file through failure and retry.
content=repo/'probe-content.txt';content.write_text('staged content\n');git('add','probe-content.txt')
index_before=git('diff','--cached','--binary','--','probe-content.txt');head=git('rev-parse','HEAD')
hook=repo/'.git/hooks/pre-commit';hook.write_text('#!/bin/sh\nexit 1\n');hook.chmod(0o755)
assert call('migrate','--apply').returncode!=0
assert git('rev-parse','HEAD')==head
assert git('diff','--cached','--binary','--','probe-content.txt')==index_before
print('recovery: HEAD and independently staged content preserved')
hook.unlink();time.sleep(1.1)
p=call('migrate','--apply');assert p.returncode==0
assert git('diff','--cached','--binary','--','probe-content.txt')==index_before
assert handoff.read_bytes()==b'original handoff\n'
assert all((repo/name).read_bytes()==data for name,data in completed.items())
assert not git('status','--porcelain','--','.agent')
print('success: handoff and mixed completed history bytes preserved; staged content preserved; metadata clean')
for args in [('implement','status','--ticket','legacy-a-03'),('topic','status','--topic','legacy-c'),('topic','status','--topic','legacy-e')]:
 p=call(*args);assert (p.returncode!=0)==('legacy-e' in args)
# Reject invalid schema-2 field, preserve selected project files.
config=repo/'.agent/matt-workflow.md';original=config.read_text();config.write_text(original.replace('"task_backend"','"task_backend"').replace('task_backend: "local"','task_backend: "external"'))
before=config.read_bytes();p=call('topic','status','--topic','legacy-a');assert p.returncode!=0 and 'task_backend' in p.stderr and config.read_bytes()==before
print('invalid new config reports exact field without mutation')
