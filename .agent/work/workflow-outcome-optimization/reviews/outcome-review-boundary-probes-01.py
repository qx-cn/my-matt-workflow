import os,sys,json,subprocess,tempfile
from pathlib import Path
os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True
sys.path[:0]=['/tmp/outcome-review-code-01','/tmp/outcome-review-code-01/tests']
from test_batches import BatchTests
from tools.workflow_lib import batches,ticket_review,evidence,artifact_review

def cli(t,*args):
 r=subprocess.run([sys.executable,'-B','/tmp/outcome-review-code-01/tools/workflow.py',*args,'--repo',str(t.repo)],capture_output=True,text=True,env=os.environ)
 return dict(rc=r.returncode,stdout=r.stdout.strip(),stderr=r.stderr.strip())

def dirty_next():
 t=BatchTests();t.setUp()
 try:
  t.setup();t.implement();t.review();(t.repo/'code.txt').write_text('unreviewed drift')
  print('DIRTY_STATUS',cli(t,'batch','status','--topic','feature'))
  n=t.repo/'.agent/repair.md';n.write_text('reassess changed marker behavior')
  print('DIRTY_NEXT_MUTATION',cli(t,'batch','repair','--topic','feature','--notes-file',str(n)))
  print('DIRTY_CLOSE',cli(t,'batch','close','--topic','feature'))
 finally:t.doCleanups()

def singleton_history():
 t=BatchTests();t.setUp()
 try:
  t.setup();t.cli('implement','start','--ticket','feature-01');t.cli('implement','test');t.self_review()
  root=t.repo/'.agent/work/feature';record=root/'implementations/feature-01.json';u=json.loads(record.read_text());u.pop('self_reviews',None)
  u['self_review']['findings']=[dict(id='legacy-bug',severity='blocking',view='correctness',summary='marker fails',location='code.txt:1',basis='marker mismatches caller')];record.write_text(json.dumps(u))
  print('LEGACY_BEFORE',sorted(batches.pending_self_findings(u)))
  spec=root/'specs/specs-feature-01.md';spec.write_text(spec.read_text()+'\nUnrelated wording clarification.\n')
  print('LEGACY_REOPEN',cli(t,'resolve','--ticket','feature-01','--reopen','--reason','approved unrelated wording'))
  after=json.loads(record.read_text());print('LEGACY_AFTER',json.dumps({'pending':sorted(batches.pending_self_findings(after)),'self_review':after.get('self_review'),'self_reviews':after.get('self_reviews'),'past_reviews':after.get('past_reviews')},ensure_ascii=False))
 finally:t.doCleanups()

def head_integrity():
 t=BatchTests();t.setUp()
 try:
  t.setup(2);t.implement(1);t.implement(2);t.review();report=t.review(action='topic')
  t.git('commit','--allow-empty','-qm','same bytes different HEAD')
  print('HEAD_DRIFT_CLOSE',cli(t,'batch','close','--topic','feature'))
 finally:t.doCleanups()

def artifact_scope():
 with tempfile.TemporaryDirectory(prefix='outcome-artifact-') as name:
  p=Path(name);a=p/'a.md';b=p/'b.md';a.write_text('same');b.write_text('same')
  snap=artifact_review.build_artifact_review_snapshot([a],snapshot_root=p/'snapshots')
  result=artifact_review.finalize_artifact_review_snapshot([b],snap['content_id'],Path(snap['snapshot_dir']))
  print('ARTIFACT_DIFFERENT_PATH',result)

def frozen_corruption():
 with tempfile.TemporaryDirectory(prefix='outcome-frozen-') as name:
  root=Path(name);item=ticket_review.frozen_file(root,'source',b'correct')
  m=root/'manifest.json';m.write_text(json.dumps(dict(inputs=[item],changes=[])));active=dict(manifest=str(m),manifest_sha256=ticket_review.digest(m.read_bytes()))
  print('FROZEN_INTACT',bool(evidence.frozen_manifest(active)))
  source=Path(item['snapshot_path']);source.chmod(0o644);source.write_bytes(b'wrong')
  try:evidence.frozen_manifest(active)
  except Exception as ex: print('FROZEN_CORRUPT_REJECT',type(ex).__name__,str(ex))
for fn in (dirty_next,singleton_history,head_integrity,artifact_scope,frozen_corruption):
 print('\nPROBE',fn.__name__)
 try:fn()
 except Exception as ex:print('PROBE_ERROR',type(ex).__name__,str(ex))
