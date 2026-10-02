import copy,importlib.util,json
from pathlib import Path
spec=importlib.util.spec_from_file_location('independent_harness','/tmp/outcome-runtime-06-independent-harness.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
h.OUT=Path('/tmp/outcome-runtime-06-truncated-evidence');h.OUT.mkdir()
prior=json.loads(Path('/tmp/outcome-runtime-06-narrow-evidence/results.json').read_text())
for name in ('direct-exception-only','typed-loader-default','typed-loader-verbose'):
 f=h.Fixture.__new__(h.Fixture);f.name=name;f.repo=Path('/tmp/outcome-runtime-06-narrow-evidence')/name;f.root=f.repo/'.agent/work/feature'
 actual=f.load('batch-tests-01.json');is_direct=name.startswith('direct')
 if is_direct:
  typed="ModuleNotFoundError: No module named 'independent_review06_absent_dependency'\n"
 else:
  summary=next(x for x in prior if x.get('fixture')==name and x.get('probe')=='typed-loader')
  typed=summary['controls'][1]['receipt']['row']['output_tail']
 assert len(typed)<4000
 for omitted in (False,True):
  stale=copy.deepcopy(actual);row=stale['results'][0];row.pop('dependency_proof_version',None)
  row['output_tail']=' '*(4000-len(typed))+typed;row['output_complete']=False;row['output_length']=8000
  if omitted:row.pop('output_complete');row.pop('output_length')
  if is_direct:row['unavailable']=True
  else:row['unavailable_loader_failures']=list(row['failures'])
  stale.update(new_failures=[],known_failures=[dict(command=row['command'],failure=v) for v in row['failures']],unverified=[])
  try:
   f.save('batch-tests-01.json',stale);status=f.status();close=f.cli('batch','close','--topic','feature',ok=None)
   h.RESULTS.append(dict(probe='truncated-valid-looking-typed-tail',fixture=name,completeness_omitted=omitted,legacy=stale,status=status,close=dict(exit_code=close.returncode,stdout=close.stdout,stderr=close.stderr)));h.persist()
   assert ' batch test ' in status['next_command'] and close.returncode==1 and '新增失败' in close.stderr
  finally:f.save('batch-tests-01.json',actual)
 print(name,'VALID-LOOKING TRUNCATED LEGACY CACHE REFUSED',flush=True)
print('TRUNCATED CACHE CONTROLS PASSED',flush=True)
