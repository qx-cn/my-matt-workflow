import os,sys,json,subprocess
from pathlib import Path
os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True
sys.path[:0]=['/tmp/outcome-review-runtime-repair-02b','/tmp/outcome-review-runtime-repair-02b/tests']
from test_batches import BatchTests

def cli(t,*args):
 r=subprocess.run([sys.executable,'-B','/tmp/outcome-review-runtime-repair-02b/tools/workflow.py',*args,'--repo',str(t.repo)],capture_output=True,text=True,env=os.environ)
 return dict(rc=r.returncode,stdout=r.stdout.strip(),stderr=r.stderr.strip())
t=BatchTests();t.setUp()
try:
 t.setup(2);t.implement(1);t.implement(2);t.review()
 t.review(action='topic',finding=dict(id='whole-branch-challenge',severity='blocking',view='spec-challenge',summary='caller conflicts with definition',location='Spec:behavior',basis='whole branch user scenario conflicts'))
 print('BRANCH_ACCEPT_CLOSE',cli(t,'batch','accept','--topic','feature','--reason','user accepts stated branch conflict'))
 print('BRANCH_ACCEPT_TOPIC_STATUS',cli(t,'topic','status','--topic','feature'))
 print('BRANCH_ACCEPT_STATUS_NEXT',cli(t,'resolve','--branch','--topic','feature','--accept','--reason','user accepts stated branch conflict'))
 print('BRANCH_ACCEPT_COMPLETE',cli(t,'topic','complete','--topic','feature'))
finally:t.doCleanups()
