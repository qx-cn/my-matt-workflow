import os,sys,json,subprocess,hashlib
from pathlib import Path
os.environ['PYTHONDONTWRITEBYTECODE']='1'
sys.dont_write_bytecode=True
sys.path[:0]=['/tmp/outcome-review-code-01','/tmp/outcome-review-code-01/tests']
from test_batches import BatchTests
from test_topic_lifecycle import TopicLifecycleTests
from tools.workflow_lib import batches,topic_service

def cli(t,*args):
 r=subprocess.run([sys.executable,'-B','/tmp/outcome-review-code-01/tools/workflow.py',*args,'--repo',str(t.repo)],capture_output=True,text=True,env=os.environ)
 return dict(rc=r.returncode,stdout=r.stdout.strip(),stderr=r.stderr.strip())
def finding(view='correctness',identifier='unfixed'):
 return dict(id=identifier,severity='blocking',view=view,summary='marker is incorrect',location='code.txt:1',basis='caller requires correct marker')
def observed(t, fs):
 p=t.repo/'.agent/findings.json';p.write_text(json.dumps(fs));return cli(t,'implement','self-review','--notes-file',str(t.repo/'.agent/self.md'),'--findings-file',str(p))

def quick():
 t=TopicLifecycleTests();t.setUp()
 try:
  t.setup_config(tests=());t.cli('topic','start','--topic','change','--level','quick')
  p=t.repo/'.agent/work/change/deliveries/deliveries-change-01.md';p.parent.mkdir(parents=True)
  p.write_text('## 验收证据\n人工读取 marker 符合预期。\n## 影响与风险\n唯一调用者已检查；缺值路径无变化。\n## 未验证项\n未配置自动测试，人工核验已完成。\n')
  print('QUICK_NO_TESTS',json.dumps(cli(t,'topic','complete','--topic','change'),ensure_ascii=False));print('QUICK_STATUS',cli(t,'topic','status','--topic','change')['stdout'])
 finally:t.doCleanups()

def reopen():
 t=BatchTests();t.setUp()
 try:
  t.setup();t.cli('implement','start','--ticket','feature-01');(t.repo/'code.txt').write_text('wrong')
  t.cli('implement','test');t.self_review();print('BLOCK_RECORDED',observed(t,[finding()]))
  root=t.repo/'.agent/work/feature';p=root/'tickets/tickets-feature-01.md';p.write_text(p.read_text().replace('- [ ]','- [x]'))
  print('BEFORE_REOPEN_FINISH',cli(t,'implement','finish'))
  spec=root/'specs/specs-feature-01.md';spec.write_text(spec.read_text()+'\nClarify an unrelated description.\n')
  print('REOPEN',cli(t,'resolve','--ticket','feature-01','--reopen','--reason','user approved unrelated documentation clarification'))
  t.cli('implement','test');t.cli('implement','self-review','--notes-file',str(t.repo/'.agent/self.md'),'--no-findings')
  u=json.loads((root/'implementations/feature-01.json').read_text());print('REOPEN_PENDING',batches.pending_self_findings(u),'EPOCH',u.get('self_review_epoch_start'),'CODE', (t.repo/'code.txt').read_text())
  print('AFTER_REOPEN_FINISH',cli(t,'implement','finish'))
 finally:t.doCleanups()

def partial():
 t=BatchTests();t.setUp()
 try:
  f=t.repo/'full.py';f.write_text("raise ModuleNotFoundError('baseline dependency')\n");t.git('add','full.py');t.git('commit','-qm','baseline unavailable')
  t.setup(full='python3 -B full.py');t.implement()
  f.write_text("import subprocess,sys\nr=subprocess.run([sys.executable,'-c',\"assert 1 == 2, 'actual behavior regression'\"])\nprint('executed behavior exit:',r.returncode,flush=True)\nraise ModuleNotFoundError('optional environment')\n")
  t.git('add','full.py');t.git('commit','-qm','partial failure with missing optional phase')
  print('PARTIAL_BATCH_TEST',cli(t,'batch','test','--topic','feature'))
  t.review();print('PARTIAL_BATCH_CLOSE',cli(t,'batch','close','--topic','feature'))
 finally:t.doCleanups()

def accept_drift():
 t=BatchTests();t.setUp()
 try:
  t.setup();t.cli('implement','start','--ticket','feature-01');t.cli('implement','test');t.self_review();observed(t,[finding('spec-challenge','challenge')])
  root=t.repo/'.agent/work/feature';spec=root/'specs/specs-feature-01.md';spec.write_text(spec.read_text()+'\nUnadmitted changed contract.\n')
  t.cli('implement','test');t.cli('implement','self-review','--notes-file',str(t.repo/'.agent/self.md'))
  print('DRIFT_STATUS',cli(t,'implement','status'))
  print('DRIFT_ACCEPT',cli(t,'resolve','--ticket','feature-01','--accept','--reason','accept previously reported challenge'))
 finally:t.doCleanups()
for fn in (quick,reopen,partial,accept_drift):
 print('\nPROBE',fn.__name__)
 try: fn()
 except Exception as e: print('PROBE_ERROR',type(e).__name__,str(e))
