import pathlib,sys,traceback,unittest
from unittest.loader import _FailedTest
mode=pathlib.Path('mode.txt').read_text().strip()
def make(kind):
 try:
  if kind=='assertion': assert False, 'review05 duplicate assertion'
  if kind=='unknown': raise RuntimeError('review05 duplicate unknown diagnostic')
  import independent_review05_missing_duplicate_dependency
 except Exception:
  return _FailedTest('collision',ImportError('Failed to import test module: collision\n'+traceback.format_exc()))
class Visible(unittest.TestCase):
 def test_ok(self): self.assertTrue(True)
suite=unittest.TestSuite([make(mode),make('missing'),Visible('test_ok')])
result=unittest.TextTestRunner(verbosity=2 if '-v' in sys.argv else 1).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
