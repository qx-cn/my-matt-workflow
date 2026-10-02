import sys,os,json,copy,traceback
from pathlib import Path
source=Path('/tmp/outcome-compensation-review-probe-v3.py').read_text()
exec(compile(source.split("cases={'R1_correctness_recovery'")[0],'/tmp/outcome-compensation-review-probe-v3.py','exec'),globals())
RESULTS={};OUTPUT=Path(sys.argv[2])
def cli_case(interpreter):
 t=new();use(CANDIDATE)
 try:
  suite=t.repo/'suite';suite.mkdir();runner=suite/'test_behavior.py';runner.write_text('import outcome_ci_cli_missing_dependency\n');t.git('add','suite');t.git('commit','-qm','CI review baseline real missing dependency');t.setup(full=interpreter+' -B -m unittest discover -s suite');t.implement()
  root=t.repo/'.agent/work/feature';baseline_path=root/'test-baseline.json';receipt_path=root/'batch-tests-01.json';baseline=json.loads(baseline_path.read_text());same=json.loads(t.cli('batch','test','--topic','feature').stdout);assert same['known_failures'] and same['unverified'] and not same['new_failures'];initial_review=fixture_review(t)
  # Preserve executed raw output/exit/environment, only recreate old v3 derived cache fields.
  cached_baseline=copy.deepcopy(baseline);cached_receipt=json.loads(receipt_path.read_text())
  for record in (cached_baseline,cached_receipt):
   for row in record['results']:
    if row['exit_code']:row.update(loader_dependency_fingerprints={},execution_observed=True,comparison_eligible=True)
  baseline_path.write_text(json.dumps(cached_baseline));receipt_path.write_text(json.dumps(cached_receipt));cached_status=json.loads(t.cli('batch','status','--topic','feature').stdout);cached_close=raw(t,'batch','close','--topic','feature');assert cached_close.returncode!=0,'v3 empty-fingerprint receipt closed'
  baseline_path.write_text(json.dumps(baseline));variants={}
  for name,code in [('dynamic',"from pathlib import Path\nimport importlib\ndef selected_plugin():\n return 'outcome_ci_cli_changed_dependency'\nPath('.agent/actual-business-executed').write_text('selected_plugin entered')\nimportlib.import_module(selected_plugin())\n"),('assertion',"from pathlib import Path\nPath('.agent/actual-business-executed').write_text('assertion reached')\nassert 7 == 8, 'actual business assertion'\n")]:
   runner.write_text(code);t.git('add','suite');t.git('commit','-qm','actual CI review '+name);tested=json.loads(t.cli('batch','test','--topic','feature').stdout);review=fixture_review(t);closed=raw(t,'batch','close','--topic','feature');assert tested['new_failures'] and not tested['known_failures'] and not tested['results'][0]['unavailable'] and closed.returncode!=0
   variants[name]=dict(receipt=tested,review=review,close_exit=closed.returncode,marker=(t.repo/'.agent/actual-business-executed').read_text())
  runner.write_text('import unittest\nclass RepairedBehavior(unittest.TestCase):\n def test_actual_value(self): self.assertEqual(7,3+4)\n');t.git('add','suite');t.git('commit','-qm','actual passing TestCase repair');repaired=json.loads(t.cli('batch','test','--topic','feature').stdout);assert repaired['results'][0]['exit_code']==0 and 'Ran 1 test' in repaired['results'][0]['output_tail'] and not repaired['new_failures'];repair_review=fixture_review(t);closed=raw(t,'batch','close','--topic','feature');assert closed.returncode==0
  return dict(baseline=baseline,same=same,initial_review=initial_review,v3_cache_fixture=dict(baseline=cached_baseline,receipt=cached_receipt),v3_status=cached_status,v3_close_exit=cached_close.returncode,variants=variants,repair=repaired,repair_review=repair_review,repair_close_exit=closed.returncode,checks=dict(v3_stale_blocks=True,real_dynamic_and_assertion_block=True,passing_repair_closes=True))
 finally:t.doCleanups()
for name,interpreter in [('public_CLI_python39','/usr/bin/python3'),('public_CLI_python314','python3')]:
 offset=len(LOG)
 try:item=cli_case(interpreter);item['passed']=all(item['checks'].values())
 except Exception as exc:item=dict(passed=False,error=str(exc),traceback=traceback.format_exc())
 item['cli_calls']=LOG[offset:];RESULTS[name]=item;OUTPUT.write_text(json.dumps(RESULTS,ensure_ascii=False,indent=2));print(name,item['passed'],item.get('checks',item.get('error')),flush=True)
sys.exit(0 if all(v['passed'] for v in RESULTS.values()) else 1)
