"""Independent narrow CLI probes; imports only the prior independent reviewer harness.
No product helpers or author tests are imported. Synthetic review is a gate input.
"""
import copy, importlib.util, json, traceback, sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('independent_harness','/tmp/outcome-runtime-06-independent-harness.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
h.OUT=Path('/tmp/outcome-runtime-06-narrow-evidence');h.OUT.mkdir()

DIRECT='''import pathlib,sys,traceback
kind=pathlib.Path('mode.txt').read_text().strip()
try:
 if kind=='assertion': assert False, "No module named 'review06_real_behavior'"
 if kind=='runtime': raise RuntimeError("No module named 'review06_real_behavior'")
 import independent_review06_absent_dependency
except Exception as exc:
 sys.stderr.write(traceback.format_exc() if kind=='missing-full' else ''.join(traceback.format_exception_only(exc)))
 raise SystemExit(1)
'''
LOADER='''import pathlib,sys,traceback,unittest
from unittest.loader import _FailedTest
def failed(kind):
 try:
  if kind=='assertion': assert False, "No module named 'review06_real_behavior'"
  if kind=='runtime': raise RuntimeError("No module named 'review06_real_behavior'")
  import independent_review06_absent_dependency
 except Exception as exc:
  detail=traceback.format_exc() if kind=='missing-full' else ''.join(traceback.format_exception_only(exc))
  return _FailedTest('same', ImportError('Failed to import test module: same\\n'+detail))
class Visible(unittest.TestCase):
 def test_ok(self): self.assertEqual(9,9)
kind=pathlib.Path('mode.txt').read_text().strip()
suite=unittest.TestSuite([failed(kind),failed('missing-full'),Visible('test_ok')])
result=unittest.TextTestRunner(verbosity=2 if '-v' in sys.argv else 1).run(suite)
raise SystemExit(not result.wasSuccessful())
'''

def old_cache(actual, kind, truncated=False, omitted_completeness=False):
 stale=copy.deepcopy(actual);row=stale['results'][0]
 row.pop('dependency_proof_version',None)
 if kind=='unavailable': row['unavailable']=True
 else: row['unavailable_loader_failures']=list(row['failures'])
 if truncated:
  # A pre-version raw tail may omit earlier failures; never trust its stored list.
  row['output_tail']=('x'*4000+row['output_tail'])[-4000:]
  row['output_complete']=False;row['output_length']=8000
 if omitted_completeness:
  row.pop('output_complete',None);row.pop('output_length',None)
 stale.update(new_failures=[],known_failures=[dict(command=row['command'],failure=f) for f in row['failures']],unverified=[])
 return stale

def cache_refusals(f,actual,kind):
 answers=[]
 for trunc,omit in [(False,False),(False,True),(True,False),(True,True)]:
  stale=old_cache(actual,kind,trunc,omit);f.save('batch-tests-01.json',stale)
  status=f.status();close=f.cli('batch','close','--topic','feature',ok=None)
  got=dict(truncated=trunc,completeness_fields_omitted=omit,legacy=stale,status=status,close=dict(exit_code=close.returncode,stdout=close.stdout,stderr=close.stderr))
  answers.append(got)
  h.RESULTS.append(dict(probe='cache-check',fixture=f.name,cache_type=kind,case=got));h.persist()
  if not (' batch test ' in status['next_command'] and close.returncode==1 and '新增失败' in close.stderr):
   print('NEW COUNTEREXAMPLE',f.name,kind,trunc,omit,flush=True);raise AssertionError(got)
 f.save('batch-tests-01.json',actual)
 return answers

def direct():
 f=h.Fixture('direct-exception-only',{'runner.py':DIRECT,'mode.txt':'missing-only'},'python3 -B runner.py')
 controls=[]
 for mode in ('missing-only','missing-full'):
  if mode!='missing-only': f.write('mode.txt',mode);f.commit('Independent actual missing dependency '+mode)
  result=f.test();raw=f.direct();row=result['results'][0]
  assert raw.returncode==1 and 'ModuleNotFoundError: No module named' in raw.stderr
  assert row['unavailable'] and not result['new_failures'] and result['unverified']
  review=f.review();status=f.status();assert status['unverified']
  controls.append(dict(mode=mode,receipt=h.facts(result),status=status,synthetic_fixture_review=review))
 cases=[]
 for mode in ('assertion','runtime'):
  f.write('mode.txt',mode);f.commit('Independent real exception '+mode)
  result=f.test();raw=f.direct();row=result['results'][0]
  assert raw.returncode==1 and (('AssertionError' if mode=='assertion' else 'RuntimeError')+': No module named') in raw.stderr
  assert 'Traceback' not in raw.stderr and not row['unavailable'] and len(result['new_failures'])==1 and not result['known_failures']
  fresh=f.review(synthetic_test=True);close=f.refused()
  cache=cache_refusals(f,result,'unavailable')
  rerun=f.test();assert not rerun['results'][0]['unavailable'] and rerun['new_failures']
  cases.append(dict(mode=mode,receipt=h.facts(result),fresh_synthetic_review=fresh,close=close,legacy_cases=cache,rerun=h.facts(rerun)))
 h.RESULTS.append(dict(probe='direct-exception-only',fixture=f.name,controls=controls,cases=cases));h.persist();print('DIRECT AND OLD UNAVAILABLE PASS',flush=True)

def loader(verbose):
 f=h.Fixture('typed-loader-'+('verbose' if verbose else 'default'),{'runner.py':LOADER,'mode.txt':'missing-full'},'python3 -B runner.py'+(' -v' if verbose else ''))
 controls=[]
 for mode in ('missing-full','missing-only'):
  if mode!='missing-full':f.write('mode.txt',mode);f.commit('Actual exception-only ModuleNotFoundError control')
  result=f.test();raw=f.direct();row=result['results'][0]
  assert raw.returncode==1 and row['execution_observed'] and not row['unavailable']
  assert len(result['known_failures'])==1 and not result['new_failures'] and not result['unverified'] and len(row['unavailable_loader_failures'])==1
  fresh=f.review();status=f.status();assert ' batch close ' in status['next_command']
  # Complete pre-version proof list must be re-proved; actual missing still known.
  old=old_cache(result,'loader');f.save('batch-tests-01.json',old)
  legacy_status=f.status();assert ' batch close ' in legacy_status['next_command'];f.save('batch-tests-01.json',result)
  controls.append(dict(mode=mode,receipt=h.facts(result),synthetic_fixture_review=fresh,status=status,complete_legacy_status=legacy_status))
 cases=[]
 for mode in ('assertion','runtime'):
  f.write('mode.txt',mode);f.commit('Actual concise loader exception '+mode)
  result=f.test();raw=f.direct();row=result['results'][0]
  assert raw.returncode==1 and raw.stderr.count('ERROR: same (unittest.loader._FailedTest.same)')==2
  assert (('AssertionError' if mode=='assertion' else 'RuntimeError')+': No module named') in raw.stderr
  assert row['execution_observed'] and not row['unavailable'] and not row['unavailable_loader_failures']
  assert len(result['new_failures'])==1 and not result['known_failures'] and result['unverified']
  fresh=f.review(synthetic_test=True);close=f.refused();cache=cache_refusals(f,result,'loader')
  cases.append(dict(mode=mode,receipt=h.facts(result),fresh_synthetic_review=fresh,close=close,legacy_cases=cache))
 h.RESULTS.append(dict(probe='typed-loader',fixture=f.name,controls=controls,cases=cases));h.persist();print(f.name,'PASS',flush=True)

def startup(nested):
 module='independent_review06_missing_module'+('.nested' if nested else '')
 f=h.Fixture('python-m-'+('nested' if nested else 'plain'),{},'python3 -B -m '+module)
 result=f.test();raw=f.direct();row=result['results'][0]
 assert raw.returncode==1 and row['unavailable'] and not result['new_failures'] and result['unverified']
 fresh=f.review();status=f.status();assert status['unverified'] and ' batch close ' in status['next_command']
 # A true complete interpreter startup record remains disclosed after upgrade.
 legacy=copy.deepcopy(result);legacy['results'][0].pop('dependency_proof_version',None)
 f.save('batch-tests-01.json',legacy);old_status=f.status();close=f.cli('batch','close','--topic','feature',ok=None)
 h.RESULTS.append(dict(probe='python-module-startup',fixture=f.name,receipt=h.facts(result),synthetic_fixture_review=fresh,status=status,legacy_status=old_status,close=dict(exit_code=close.returncode,stdout=close.stdout,stderr=close.stderr)));h.persist()
 assert close.returncode==0 and old_status['unverified'];print(f.name,'DISCLOSED GAP (not behavioral pass)',flush=True)

if __name__=='__main__':
 try:
  direct()
  for v in (False,True):loader(v)
  for nested in (False,True):startup(nested)
  print('ALL NARROW PROBE ASSERTIONS PASSED',flush=True)
 except BaseException:
  h.persist();traceback.print_exc();sys.exit(1)
