import sys,json,unittest
sys.path.insert(0,'/tmp/independent03/current/tests')
from test_implement_lifecycle import ImplementationTests

def new():
 t=ImplementationTests();t.setUp();return t

t=new()
try:
 command="python3 -c \"from pathlib import Path; p=Path('.agent/counter'); n=int(p.read_text()) if p.exists() else 0; p.write_text(str(n+1)); print('attempt',n+1); raise SystemExit(9 if n==0 else 0)\""
 t.setup_config(tests=(command,));t.ticket(commands=[command,command])
 start=t.cli('implement','start','--ticket','feature-01');print('start_exit',start.returncode)
 result=t.cli('implement','test',ok=False);print('test_exit',result.returncode,'stderr',result.stderr.strip())
 status=t.cli('implement','status');print('status_exit',status.returncode,'status',status.stdout.strip())
 rec=json.loads((t.repo/'.agent/work/feature/implementations/feature-01.json').read_text());print('recorded_exit_codes',[x['exit_code'] for x in rec['tests']])
finally:t.doCleanups()

t=new()
try:
 t.setup_config(mode='private',tests=("python3 -c 'pass'",));p=t.ticket()
 print('private_start_exit',t.cli('implement','start','--ticket','feature-01').returncode)
 print('private_test_exit',t.cli('implement','test').returncode)
 t.replace(p,'status','needs-user');print('needs_user_test_exit',t.cli('implement','test').returncode)
 t.replace(p,'test_commands',["python3 -c 'print(1)'"]);r=t.cli('implement','test',ok=False);print('changed_test_exit',r.returncode,'stderr',r.stderr.strip())
 t.replace(p,'test_commands',["python3 -c 'pass'"]);print('restored_test_exit',t.cli('implement','test').returncode)
 print('restored_status',t.cli('implement','status').stdout.strip())
finally:t.doCleanups()
