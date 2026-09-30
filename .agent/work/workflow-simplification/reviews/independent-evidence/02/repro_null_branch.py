import os,pathlib,subprocess,sys,tempfile
ENV={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}
for side in ('baseline','current'):
 with tempfile.TemporaryDirectory(prefix='independent02-null-') as d:
  repo=pathlib.Path(d)
  for argv in [('git','init','-q','--initial-branch=null'),('git','config','user.name','Test'),('git','config','user.email','test@example.invalid')]:subprocess.run(argv,cwd=repo,check=True,env=ENV)
  (repo/'app.txt').write_text('base\n')
  subprocess.run(['git','add','app.txt'],cwd=repo,check=True,env=ENV)
  subprocess.run(['git','commit','-qm','base'],cwd=repo,check=True,env=ENV)
  cli=['python3',f'/tmp/independent02/{side}/tools/workflow.py']
  setup=subprocess.run(cli+['setup','--repo',d,'--apply','--agent-directory-mode','shared','--base-branch','null'],capture_output=True,text=True,env=ENV)
  overview=subprocess.run(cli+['work-overview','--repo',d,'--json'],capture_output=True,text=True,env=ENV)
  print(side,'setup=',setup.returncode,'overview=',overview.returncode,'stderr=',overview.stderr.strip())
  if setup.returncode: print('setup stderr',setup.stderr)
  if side=='current':
   start=subprocess.run(cli+['topic','start','--repo',d,'--topic','change','--level','quick'],capture_output=True,text=True,env=ENV)
   print('current topic start=',start.returncode,'stderr=',start.stderr.strip())
 assert setup.returncode==0
 assert overview.returncode==(0 if side=='baseline' else 1)
print('formal baseline comparison assertion exit=0')
