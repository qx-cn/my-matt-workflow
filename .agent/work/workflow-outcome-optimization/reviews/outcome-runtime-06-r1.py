import importlib.util
import json
from pathlib import Path
import sys

spec=importlib.util.spec_from_file_location('independent_fixture','/tmp/outcome-runtime-06-independent-harness.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m.OUT=Path('/tmp/outcome-runtime-06-r1-evidence')
m.OUT.mkdir(exist_ok=True)

RUNNER='''import pathlib,sys,traceback,unittest
from unittest.loader import _FailedTest
def construct(kind):
 try:
  if kind=='assertion': assert False, "No module named 'review05_behavior_condition'"
  import independent_review05_extra_missing_dependency
 except Exception as exc:
  # A concise exception-only wrapper preserves the actual exception class.
  detail=''.join(traceback.format_exception_only(exc)) if kind=='assertion' else traceback.format_exc()
  return _FailedTest('collision',ImportError('Failed to import test module: collision\\n'+detail))
class Visible(unittest.TestCase):
 def test_ok(self): self.assertEqual(6,6)
mode=pathlib.Path('mode.txt').read_text().strip()
suite=unittest.TestSuite([construct(mode),construct('missing'),Visible('test_ok')])
result=unittest.TextTestRunner(verbosity=2 if '-v' in sys.argv else 1).run(suite)
raise SystemExit(not result.wasSuccessful())
'''

for verbose in (False,True):
 name='proof-concise-assertion-'+('verbose' if verbose else 'default')
 f=m.Fixture(name,{'runner.py':RUNNER,'mode.txt':'missing'},'python3 -B runner.py'+(' -v' if verbose else ''))
 control=f.test()
 f.write('mode.txt','assertion');f.commit('Real assertion retained by concise exception wrapper')
 current=f.test();raw=f.direct()
 assert raw.returncode==1 and "AssertionError: No module named 'review05_behavior_condition'" in raw.stderr
 assert raw.stderr.count('ERROR: collision (unittest.loader._FailedTest.collision)')==2
 assert current['results'][0]['failures']==control['results'][0]['failures']
 review=f.review(synthetic_test=True)
 close=f.cli('batch','close','--topic','feature',ok=None)
 m.RESULTS.append(dict(probe=name,baseline=f.baseline,control=m.facts(control),current=m.facts(current),
                       actual_fixture_review=review,close=dict(exit_code=close.returncode,stdout=close.stdout,stderr=close.stderr),
                       bypass=not current['new_failures'] and close.returncode==0))
 m.persist();print(name,'bypass=',m.RESULTS[-1]['bypass'],flush=True)

assert all(not x['bypass'] and x['close']['exit_code']==1 and x['current']['new'] for x in m.RESULTS)
print('R1 REPAIR VERIFIED',flush=True)
