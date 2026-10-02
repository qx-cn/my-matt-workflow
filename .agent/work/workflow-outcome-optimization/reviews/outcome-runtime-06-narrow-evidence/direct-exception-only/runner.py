import pathlib,sys,traceback
kind=pathlib.Path('mode.txt').read_text().strip()
try:
 if kind=='assertion': assert False, "No module named 'review06_real_behavior'"
 if kind=='runtime': raise RuntimeError("No module named 'review06_real_behavior'")
 import independent_review06_absent_dependency
except Exception as exc:
 sys.stderr.write(traceback.format_exc() if kind=='missing-full' else ''.join(traceback.format_exception_only(exc)))
 raise SystemExit(1)
