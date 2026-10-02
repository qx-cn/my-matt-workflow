import sys,os,json,traceback,copy
from pathlib import Path
# Reuse only the frozen legacy CLI fixture helpers and independently edited probe definitions.
source=Path('/tmp/outcome-compensation-review-probe-v3.py').read_text()
exec(compile(source.split("cases={'R1_correctness_recovery'")[0],'/tmp/outcome-compensation-review-probe-v3.py','exec'),globals())
OUTPUT=Path(sys.argv[2]); RESULTS={}

def loader_controls(partial=False,verbose=False,long=False):
 t=new();use(CANDIDATE)
 try:
  suite=t.repo/'suite';suite.mkdir();runner=suite/'test_missing.py'
  initial='import outcome_review_same_dependency\n'
  if long:initial="import importlib\nimportlib.import_module('outcome_review_'+ 'x'*5000)\n"
  runner.write_text(initial)
  if partial:(suite/'test_ok.py').write_text('import unittest\nclass RealBehavior(unittest.TestCase):\n def test_ok(self): self.assertEqual(2+2,4)\n')
  t.git('add','suite');t.git('commit','-qm','independent loader baseline')
  t.setup(full='python3 -B -m unittest discover -s suite'+(' -v' if verbose else ''));t.implement()
  root=t.repo/'.agent/work/feature';baseline_path=root/'test-baseline.json';baseline=json.loads(baseline_path.read_text())
  same=json.loads(t.cli('batch','test','--topic','feature').stdout);row=same['results'][0]
  assert row['exit_code']!=0 and not row['unavailable'] and same['known_failures'] and not same['new_failures'],'unchanged diagnosis not correctly known'
  if not partial:assert same['unverified'],'all-loader gap not disclosed'
  assert row['execution_observed']==partial
  assert row['output_complete']!=long
  recovered={}
  # Explicitly emulate old cache schema from the same real full diagnostics.
  # Change no exit/output/failure identity, only stale derived classification.
  original_receipt=json.loads((root/'batch-tests-01.json').read_text())
  for version in (1,2):
   old=copy.deepcopy(baseline);cached=copy.deepcopy(original_receipt)
   for record in (old,cached):
    for r in record['results']:
     r['dependency_proof_version']=version;r.pop('loader_dependency_fingerprints',None)
     if r['exit_code']:r['unavailable']=True
   baseline_path.write_text(json.dumps(old));(root/'batch-tests-01.json').write_text(json.dumps(cached))
   status=json.loads(t.cli('batch','status','--topic','feature').stdout)
   current=json.loads(t.cli('batch','test','--topic','feature').stdout)
   recovered[str(version)]={'receipt':current,'status':status}
   if long:assert current['new_failures'] and not current['known_failures'],'truncated legacy proof reused as known'
   else:assert current['known_failures'] and not current['new_failures'],'complete old diagnostics not rederived'
   if long:
    assert raw(t,'batch','close','--topic','feature').returncode!=0
  baseline_path.write_text(json.dumps(baseline))
  if long:
   # Recompute v3 complete fingerprints from full execution even when the tail is truncated.
   refreshed=json.loads(t.cli('batch','test','--topic','feature').stdout);assert refreshed['known_failures'] and not refreshed['new_failures']
   review=fixture_review(t);closed=raw(t,'batch','close','--topic','feature')
   return dict(baseline=baseline,same=same,legacy_controls=recovered,review=review,close_exit=closed.returncode,checks=dict(closes=closed.returncode==0,full_fingerprint_from_long_output=bool(row['loader_dependency_fingerprints'])))
  changed={}
  variants={'module':'import outcome_review_changed_dependency\n','stack':"import importlib\ndef load_dependency():\n return importlib.import_module('outcome_review_same_dependency')\nload_dependency()\n",'assertion':"assert False, 'actual loader initialization regression'\n"}
  for kind,code in variants.items():
   runner.write_text(code);t.git('add','suite');t.git('commit','-qm','independent loader '+kind)
   receipt=json.loads(t.cli('batch','test','--topic','feature').stdout);review=fixture_review(t);closed=raw(t,'batch','close','--topic','feature')
   assert receipt['new_failures'] and not receipt['known_failures'] and closed.returncode!=0,kind+' diagnostic borrowed loader identity'
   assert not receipt['results'][0]['unavailable']
   changed[kind]=dict(receipt=receipt,review=review,close_exit=closed.returncode)
  runner.write_text(initial);t.git('add','suite');t.git('commit','-qm','restore baseline diagnosis')
  review=fixture_review(t);closed=raw(t,'batch','close','--topic','feature')
  assert closed.returncode==0
  return dict(baseline=baseline,same=same,legacy_controls=recovered,changed=changed,review=review,close_exit=closed.returncode,checks=dict(changed_blocks=True,legacy_complete_recomputed=True,known_closes=True))
 finally:t.doCleanups()

# Generate one true v2 receipt via the immutable preview runtime, then re-evaluate under final.
dynamic_source=source[source.index('def dynamic('):source.index('\ndef startup(')]
dynamic_source=dynamic_source.replace('def dynamic(', 'def dynamic_v2(').replace('use(OLD if v1 else CANDIDATE)',"use(Path('/tmp/outcome-compensation-preview-01'))")
exec(compile(dynamic_source,'v2-cache-control','exec'),globals())

def optional_branch():
 t=new();use(BASE)
 try:
  t.setup();t.cli('implement','start','--ticket','feature-01');(t.repo/'code.txt').write_text('incorrect result\n');t.cli('implement','test');t.self_review()
  findings=t.repo/'.agent/findings.json';findings.write_text(json.dumps([dict(id='legacy-correctness',severity='blocking',view='correctness',summary='wrong caller result',location='code.txt:1',basis='caller requires correct result')]))
  t.cli('implement','self-review','--notes-file',str(t.repo/'.agent/self.md'),'--findings-file',str(findings));root=t.repo/'.agent/work/feature';ticket=root/'tickets/tickets-feature-01.md';ticket.write_text(ticket.read_text().replace('- [ ]','- [x]'));t.cli('implement','finish')
  unit=root/'implementations/feature-01.json';history={str(p.relative_to(root)):p.read_bytes() for p in (ticket,unit)}
  use(CANDIDATE);initial=fixture_review(t);assert raw(t,'batch','close','--topic','feature').returncode!=0
  notes=t.repo/'.agent/repair.md';notes.write_text('self:feature-01:legacy-correctness: actual caller output corrected; independent value oracle.\n');(t.repo/'code.txt').write_text('correct result\n');t.cli('batch','repair','--topic','feature','--notes-file',str(notes));review=fixture_review(t)
  branch=t.review(action='topic');branch_unit=json.loads((root/'branch-review.json').read_text());closed=raw(t,'batch','close','--topic','feature');completed=raw(t,'topic','complete','--topic','feature');archived=t.repo/'.agent/archive/feature';unchanged=archived.exists() and all((archived/p).read_bytes()==v for p,v in history.items())
  return dict(initial=initial,review=review,branch=branch,branch_unit=branch_unit,close_exit=closed.returncode,complete_exit=completed.returncode,checks=dict(close=closed.returncode==0,complete=completed.returncode==0,history_unchanged=unchanged))
 finally:t.doCleanups()

def stale_geometry():
 t=new(BranchTests);use(BASE)
 try:
  t.multi();t.cli('topic','test');first=t.branch_review();t.branch_submit(t.blocking(first));(t.repo/'code.txt').write_text('fixed\nsecond\nline three\nline four\n');t.cli('topic','test');report=t.branch_review();t.branch_submit(t.result(report));old=json.loads(t.cli('topic','status').stdout)
  (t.repo/'code.txt').write_text('changed after frozen pass\n');t.git('add','code.txt');t.git('commit','-qm','stale previously passing evidence')
  use(CANDIDATE);status=json.loads(t.cli('topic','status').stdout);attempt=raw(t,'topic','complete');return dict(before=old,status=status,complete_exit=attempt.returncode,checks=dict(blocked=attempt.returncode!=0,not_archived=not(t.repo/'.agent/archive/feature').exists()))
 finally:t.doCleanups()

def os_startup():
 t=new();use(CANDIDATE)
 try:
  t.setup(full='outcome_review_missing_executable_7626');t.implement();receipt=json.loads(t.cli('batch','test','--topic','feature').stdout);review=fixture_review(t);closed=raw(t,'batch','close','--topic','feature');r=receipt['results'][0];return dict(receipt=receipt,review=review,close_exit=closed.returncode,checks=dict(unavailable=r['unavailable'],os_exit=r['exit_code']==127,unverified=bool(receipt['unverified']),no_new_failure=not receipt['new_failures'],close=closed.returncode==0))
 finally:t.doCleanups()

cases={'R2_loader_all_controls':loader_controls,'R2_loader_partial_controls':lambda:loader_controls(partial=True,verbose=True),'R2_loader_long_legacy_controls':lambda:loader_controls(long=True),'R2_v2_loader_cache':lambda:dynamic_v2(loader=True),'R1_optionalbranch_close_complete':optional_branch,'R3_stale_pass_blocks':stale_geometry,'R2_OS_startup_gap':os_startup}
for name,case in cases.items():
 offset=len(LOG)
 try:
  result=case();result['passed']=all(result['checks'].values())
 except Exception as exc:result=dict(passed=False,error=str(exc),traceback=traceback.format_exc())
 result['cli_calls']=LOG[offset:];RESULTS[name]=result;OUTPUT.write_text(json.dumps(RESULTS,ensure_ascii=False,indent=2));print(name,result['passed'],result.get('checks',result.get('error')),flush=True)
sys.exit(0 if all(v['passed'] for v in RESULTS.values()) else 1)
