import os,sys,json
from pathlib import Path
os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True
sys.path[:0]=['/tmp/outcome-review-runtime-repair-02b','/tmp/outcome-review-runtime-repair-02b/tests']
from test_batches import BatchTests
from test_implement_review import ReviewTests
from tools.workflow_lib import batches
exec(Path('/tmp/outcome-review-extension-probes-02.py').read_text().split('for fn in (runner_boundaries,unittest_startup):')[0].split('def runner_boundaries():')[0])
def find(id,view='correctness',severity='blocking'):
 f=dict(id=id,view=view,severity=severity,summary=id+' requires treatment',location='code.txt:1',basis='caller requirement')
 if severity=='advisory':f['disposition']='fix-in-batch'
 return f
def record_findings(t,fs):
 p=t.repo/'.agent/findings.json';p.write_text(json.dumps(fs));return cli(t,'implement','self-review','--notes-file',str(t.repo/'.agent/self.md'),'--findings-file',str(p))
def selected_reopen():
 t=BatchTests();t.setUp()
 try:
  t.setup();t.cli('implement','start','--ticket','feature-01');(t.repo/'code.txt').write_text('wrong');t.cli('implement','test');t.self_review()
  emit('MIXED_REGISTER',record_findings(t,[find('challenge-one','spec-challenge'),find('challenge-two','spec-challenge'),find('unfixed'),find('pending-advisory',severity='advisory')]))
  root=t.repo/'.agent/work/feature';record=root/'implementations/feature-01.json';u=json.loads(record.read_text());u['self_review_epoch_start']=len(u['self_reviews']);record.write_text(json.dumps(u));emit('OLD_EPOCH_PENDING',sorted(batches.pending_self_findings(u)))
  spec=root/'specs/specs-feature-01.md';spec.write_text(spec.read_text()+'\nApproved definition replacement.\n')
  emit('SELECTED_REOPEN',cli(t,'resolve','--ticket','feature-01','--reopen','--reason','challenge-one: approved replacement definition'))
  u=json.loads(record.read_text());emit('SELECTED_PENDING',dict(ids=sorted(batches.pending_self_findings(u)),resolutions=[x for r in u['self_reviews'] for x in r.get('resolutions',[])]))
  t.cli('implement','test');emit('MIXED_NO_FINDINGS',cli(t,'implement','self-review','--notes-file',str(t.repo/'.agent/self.md'),'--no-findings'))
 finally:t.doCleanups()
def valid_reopen_and_finish():
 t=BatchTests();t.setUp()
 try:
  t.setup();t.cli('implement','start','--ticket','feature-01');t.cli('implement','test');t.self_review();record_findings(t,[find('challenge','spec-challenge')]);root=t.repo/'.agent/work/feature';spec=root/'specs/specs-feature-01.md';spec.write_text(spec.read_text()+'\nNew approved definition.\n')
  emit('VALID_REOPEN',cli(t,'resolve','--ticket','feature-01','--reopen','--reason','challenge: user approved new definition'))
  t.cli('implement','test');emit('VALID_SELF',cli(t,'implement','self-review','--notes-file',str(t.repo/'.agent/self.md'),'--no-findings'))
  p=root/'tickets/tickets-feature-01.md';p.write_text(p.read_text().replace('- [ ]','- [x]'))
  emit('VALID_FINISH',cli(t,'implement','finish'));u=json.loads((root/'implementations/feature-01.json').read_text());emit('VALID_HISTORY',dict(pending=sorted(batches.pending_self_findings(u)),history=len(u['self_reviews']),resolved=[x for r in u['self_reviews'] for x in r.get('resolutions',[])]))
  t.review();emit('VALID_CLOSE',cli(t,'batch','close','--topic','feature'));emit('VALID_COMPLETE',cli(t,'topic','complete','--topic','feature'))
  before={str(p):p.read_bytes() for p in (t.repo/'.agent/archive/feature').rglob('*') if p.is_file()};emit('ARCHIVE_REOPEN',cli(t,'resolve','--ticket','feature-01','--reopen','--reason','no changes'));emit('ARCHIVE_COMPLETE',cli(t,'topic','complete','--topic','feature'));after={str(p):p.read_bytes() for p in (t.repo/'.agent/archive/feature').rglob('*') if p.is_file()};emit('ARCHIVE_UNCHANGED',before==after)
 finally:t.doCleanups()
def legacy_singleton():
 t=ReviewTests();t.setUp()
 try:
  t.start();root=t.repo/'.agent/work/feature';record=root/'implementations/feature-01.json';u=json.loads(record.read_text());u.pop('self_reviews',None);u['self_review']['findings']=[find('legacy-block')];record.write_text(json.dumps(u));spec=root/'specs/specs-feature-01.md';spec.write_text(spec.read_text()+'\nUnrelated words.\n')
  emit('LEGACY_NONBATCH_REOPEN',cli(t,'resolve','--ticket','feature-01','--reopen','--reason','approved unrelated words'));u=json.loads(record.read_text());emit('LEGACY_NONBATCH_PRESERVED',dict(pending=sorted(batches.pending_self_findings(u)),history=len(u['self_reviews'])))
  emit('LEGACY_NONBATCH_TEST',cli(t,'implement','test'));notes=t.repo/'.agent/legacy-self.md';emit('LEGACY_NONBATCH_NO_FINDINGS',cli(t,'implement','self-review','--notes-file',str(notes),'--no-findings'))
  (t.repo/'code.txt').write_text('fixed');t.cli('implement','test');emit('LEGACY_NONBATCH_REPAIRED',cli(t,'implement','self-review','--notes-file',str(notes),'--no-findings'));r=t.review();t.submit(t.result(r));p=root/'tickets/tickets-feature-01.md';p.write_text(p.read_text().replace('- [ ]','- [x]'));emit('LEGACY_NONBATCH_FINISH',cli(t,'implement','finish'))
 finally:t.doCleanups()
def human_and_restore():
 t=BatchTests();t.setUp()
 try:
  t.setup();t.implement();t.review();(t.repo/'code.txt').write_text('unreviewed drift')
  emit('DIRTY_BATCH_HUMAN',cli(t,'batch','status','--topic','feature','--human'));emit('DIRTY_TOPIC_HUMAN',cli(t,'topic','status','--topic','feature','--human'));t.git('restore','code.txt');emit('RESTORED_STATUS',cli(t,'batch','status','--topic','feature'));emit('RESTORED_CLOSE',cli(t,'batch','close','--topic','feature'))
 finally:t.doCleanups()
 t=BatchTests();t.setUp()
 try:
  t.setup(2);t.implement(1);t.implement(2);t.review();t.review(action='topic',finding=find('accepted-challenge','spec-challenge'));t.cli('batch','accept','--topic','feature','--reason','user accepts explicit branch risk');emit('ACCEPTED_HUMAN',cli(t,'topic','status','--topic','feature','--human'))
 finally:t.doCleanups()
for fn in (selected_reopen,valid_reopen_and_finish,legacy_singleton,human_and_restore):
 try:fn()
 except Exception as ex:emit('PROBE_ERROR',dict(probe=fn.__name__,type=type(ex).__name__,message=str(ex)))
