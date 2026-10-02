import os,sys,json,subprocess,tempfile
from pathlib import Path
os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True
ROOT=Path('/tmp/outcome-review-runtime-repair-02b');sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from test_batches import BatchTests
from tools.workflow_lib import evidence,batches,topic_service
CLI=ROOT/'tools/workflow.py'
def cli(t,*args):
 r=subprocess.run([sys.executable,'-B',str(CLI),*args,'--repo',str(t.repo)],capture_output=True,text=True)
 return dict(rc=r.returncode,stdout=r.stdout.strip(),stderr=r.stderr.strip())
def emit(label,x):print(label,json.dumps(x,ensure_ascii=False),flush=True)
def runner_boundaries():
 t=BatchTests();t.setUp()
 try:
  t.setup(full='python3 -B full.py')
  script=t.repo/'full.py';script.write_text('import outcome_missing_startup_dependency\n');t.git('add','full.py');t.git('commit','-qm','startup baseline');t.implement()
  for label,phase in [('assertion',"subprocess.run([sys.executable,'-c',\"assert 1 == 2, 'actual regression'\"])") ,('systemexit',"subprocess.run([sys.executable,'-c',\"raise SystemExit('actual regression')\"])") ,('shellfailure',"subprocess.run(['sh','-c','echo actual regression >&2; exit 1'])")]:
   script.write_text('import subprocess,sys\n'+phase+'\nimport outcome_missing_optional_phase\n');t.git('add','full.py');t.git('commit','-qm',label)
   raw=cli(t,'batch','test','--topic','feature');x=json.loads(raw['stdout']);emit('PARTIAL_'+label,dict(rc=raw['rc'],exit=x['results'][0]['exit_code'],unavailable=x['results'][0]['unavailable'],new=x['new_failures'],unverified=x['unverified']));emit('PARTIAL_CLOSE_'+label,cli(t,'batch','close','--topic','feature'))
  for label,argv in [('missingexec',['outcome-missing-test-executable']),('python-module',[sys.executable,'-B','-m','outcome_missing_module']),('python-import',[sys.executable,'-B','-c','import outcome_missing_module']),('shell-startup',['sh','-c','outcome-missing-test-executable'])]:
   row,_=evidence.execute(t.repo,argv);emit('STARTUP_'+label,row)
 finally:t.doCleanups()
def unittest_startup():
 t=BatchTests();t.setUp()
 try:
  suite=t.repo/'suite';suite.mkdir();p=suite/'test_behavior.py';p.write_text('import outcome_missing_startup_dependency\n');t.git('add','suite');t.git('commit','-qm','pure loader startup missing dependency')
  t.setup(full='python3 -B -m unittest discover -s suite');t.implement()
  baseline=json.loads((t.repo/'.agent/work/feature/test-baseline.json').read_text());emit('LOADER_STARTUP_BASELINE',baseline)
  p.write_text("assert 1 == 2, 'actual behavior regression at import'\n");t.git('add','suite');t.git('commit','-qm','actual failing module assertion')
  emit('LOADER_CURRENT',cli(t,'batch','test','--topic','feature'))
  t.review();emit('LOADER_CLOSE',cli(t,'batch','close','--topic','feature'))
 finally:t.doCleanups()
for fn in (runner_boundaries,unittest_startup):
 try:fn()
 except Exception as ex:emit('PROBE_ERROR',dict(probe=fn.__name__,type=type(ex).__name__,message=str(ex)))
