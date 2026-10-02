import sys,os,json,tempfile,subprocess,copy,traceback,hashlib,datetime
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(sys.argv[1]).resolve();OUT=Path(sys.argv[2]);sys.path.insert(0,str(ROOT))
from tools.workflow_lib import evidence as e,batches as b,validator as v
RESULTS={};RUNS=[]

def run(argv,cwd):
 r=subprocess.run(argv,cwd=cwd,capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'});RUNS.append(dict(command=argv,cwd=str(cwd),exit=r.returncode,stdout=r.stdout,stderr=r.stderr));return r

def receipt(result,command):
 output=result.stdout+result.stderr
 return dict(command=command,argv=command.split(),exit_code=result.returncode,failures=b.failures(output,result.returncode),execution_observed=e.execution_observed(output),comparison_eligible=not e.loader_only_failure(output),output_tail=output[-4000:],output_complete=len(output)<=4000,output_length=len(output),loader_dependency_fingerprints=e.loader_dependency_fingerprints(result.stdout,result.stderr),dependency_proof_version=3,unavailable=e.environment_only_failure(result.stdout,result.stderr,result.returncode,command.split()))

def compare(old,now):
 return b.compare(dict(commands=[old['command']],results=[old]),dict(commands=[now['command']],results=[now]))

def identities():
 valid=['missing (unittest.loader._FailedTest)','missing (unittest.loader._FailedTest.missing)']
 invalid=['unittest.loader._FailedTest','missing (fake.unittest.loader._FailedTest)','missing (unittest.loader._FailedTestish)','missing (unittest.loader._FailedTest.missing) garbage','missing (unittest.loader._FailedTest','missing (unittest.loader._FailedTest.)','missing (unittest.loader._FailedTest.foo bar)','missing (unittest.loader._FailedTest.missing)\nextra','test_unittest.loader._FailedTest.name (real.Behavior.test_case)']
 assert all(e.loader_failure_identity(x) for x in valid)
 assert all(not e.loader_failure_identity(x) for x in invalid)
 return dict(valid=valid,invalid=invalid,checks=dict(anchored_exact_class=True))

def actual_reports(interpreter,partial=False,verbose=False):
 with tempfile.TemporaryDirectory() as directory:
  root=Path(directory);suite=root/'suite';suite.mkdir();missing=suite/'test_missing.py';missing.write_text('import outcome_ci_review_missing_dependency\n')
  if partial:(suite/'test_real.py').write_text('import unittest\nclass ActualBehavior(unittest.TestCase):\n def test_ok(self): self.assertEqual(7,3+4)\n')
  args=[interpreter,'-B','-m','unittest','discover','-s','suite']+(['-v'] if verbose else []);command=' '.join(args)
  initial=run(args,root);old=receipt(initial,command);same=receipt(run(args,root),command);comparison=compare(old,same)
  assert old['loader_dependency_fingerprints'] and initial.returncode==1 and not old['unavailable']
  assert old['execution_observed']==partial and old['comparison_eligible']==partial
  assert comparison['known_failures'] and not comparison['new_failures']
  if not partial:assert comparison['unverified']
  variants={}
  for kind,code in [('changed_dependency','import outcome_ci_review_changed_dependency\n'),('changed_stack',"import importlib\ndef selected():\n return 'outcome_ci_review_missing_dependency'\nimportlib.import_module(selected())\n"),('assertion',"assert False, 'actual module initialization assertion'\n")]:
   missing.write_text(code);current=receipt(run(args,root),command);comp=compare(old,current);assert comp['new_failures'] and not comp['known_failures'];assert not current['unavailable'];variants[kind]=dict(receipt=current,comparison=comp)
  # Cached v3 facts produced by the old mistaken Python 3.10 classification:
  # same raw diagnostics and failure identities, but empty fingerprint and observed=true.
  cached=copy.deepcopy(old);cached.update(loader_dependency_fingerprints={},comparison_eligible=True,execution_observed=True)
  stale=compare(cached,same);assert stale['new_failures'] and not stale['known_failures'] and stale['unverified']
  assertion=compare(cached,variants['assertion']['receipt']);assert assertion['new_failures'] and not assertion['known_failures']
  return dict(baseline=old,same=same,same_comparison=comparison,variants=variants,v3_misclassification_fixture=cached,v3_stale_comparison=stale,v3_assertion_comparison=assertion,checks=dict(real_reports=True,changed_blocked=True,v3_empty_fingerprint_blocked=True))

def strict_reports():
 # Base is an actual current-interpreter report; only these controls adapt/mutate its grammar.
 with tempfile.TemporaryDirectory() as directory:
  root=Path(directory);(root/'test_missing.py').write_text('import outcome_ci_strict_missing\n');r=run([sys.executable,'-B','-m','unittest','test_missing'],root)
  text=r.stderr;identity=b.failures(text,r.returncode)[0];assert e.loader_failure_identity(identity)
  prefix='ImportError: Failed to import test module: test_missing\n';start=text.index(prefix);end=text.rindex('\n----------------------------------------------------------------------\nRan ');block=text[start:end].strip()
  legacy='missing (unittest.loader._FailedTest)';modern='missing (unittest.loader._FailedTest.missing)'
  grammar={}
  for name in (legacy,modern):
   report='E\n======================================================================\nERROR: '+name+'\n----------------------------------------------------------------------\n'+block+'\n\n----------------------------------------------------------------------\nRan 1 test in 0.001s\n\nFAILED (errors=1)\n'
   assert e.loader_dependency_fingerprints('',report)
   assert not e.loader_dependency_fingerprints('ordinary stdout',report)
   assert not e.loader_dependency_fingerprints('',report.replace('errors=1','errors=2'))
   assert not e.loader_dependency_fingerprints('',report[:report.rindex('FAILED')])
   duplicate='EE\n'+report[2:report.index('\n----------------------------------------------------------------------\nRan ')]+'\n\n======================================================================\nERROR: '+name+'\n----------------------------------------------------------------------\nImportError: Failed to import test module: missing\nTraceback (most recent call last):\n  File "behavior.py", line 1, in <module>\n    assert False\nAssertionError: actual duplicate business failure\n\n----------------------------------------------------------------------\nRan 2 tests in 0.001s\n\nFAILED (errors=2)\n'
   assert not e.loader_dependency_fingerprints('',duplicate),'duplicate real failure accepted'
   # A v3 truncated tail without a saved full fingerprint cannot establish known.
   old=dict(command='runner',exit_code=1,failures=[name],unavailable=False,dependency_proof_version=3,comparison_eligible=False,execution_observed=False,output_complete=False,output_tail=report[-100:],loader_dependency_fingerprints={})
   now=dict(old,output_complete=True,output_tail=report,loader_dependency_fingerprints=e.loader_dependency_fingerprints('',report))
   comp=compare(old,now);assert comp['new_failures'] and not comp['known_failures']
   grammar[name]=dict(complete=report,duplicate=duplicate,truncated_comparison=comp)
  return dict(grammar_fixture_from_real_report=grammar,checks=dict(complete_only=True,duplicate_rejected=True,v3_truncated_blocks=True))

def markdown_scope():
 cases={}
 def check(name,relative,target,expected,existing=None,symlink=False):
  with tempfile.TemporaryDirectory() as directory,tempfile.TemporaryDirectory() as outside:
   root=Path(directory);document=root/relative;document.parent.mkdir(parents=True,exist_ok=True)
   if existing:(root/existing).parent.mkdir(parents=True,exist_ok=True);(root/existing).write_text('actual target\n')
   if symlink:
    p=Path(outside)/'target.md';p.write_text('outside target');(root/'linked.md').symlink_to(p)
   document.write_text('[actual reference]('+target+')\n')
   try:v.validate_markdown_references(root);outcome='pass';error=None
   except v.ValidationError as exc:outcome='reject';error=str(exc)
   assert outcome==expected,name+': '+str(error)
   cases[name]=dict(relative=relative,target=target,expected=expected,outcome=outcome,error=error)
 check('root_work_raw_missing','.agent/work/topic/reviews/raw.md','/tmp/outcome_ci_definitely_expired_701/report.md','pass')
 check('root_work_embedded_fixture','.agent/work/topic/evidence/project/README.md','missing.md','pass')
 for relative in ['.agent/matt-workflow.md','.agent/policy.md','.agent/archive/topic/reviews/raw.md','docs/formal.md','tests/fixtures/project/README.md','docs/.agent/work/topic/report.md','.agent/work-other/topic/report.md']:
  check('missing:'+relative,relative,'missing.md','reject')
  depth=len(Path(relative).parts)-1
  check('escape:'+relative,relative,'../'*(depth+1)+'outside.md','reject')
 check('config_absolute_escape','.agent/matt-workflow.md','/tmp/outcome_ci_absolute_external.md','reject')
 check('config_symlink_escape','.agent/matt-workflow.md','../linked.md','reject',symlink=True)
 check('formal_refs_missing_runtime','README.md','.agent/work/topic/nonexistent.md','reject')
 check('config_valid','.agent/matt-workflow.md','../docs/existing.md','pass',existing='docs/existing.md')
 check('formal_valid','README.md','docs/existing.md#anchor','pass',existing='docs/existing.md')
 check('formal_https','README.md','https://example.invalid/current','pass')
 with tempfile.TemporaryDirectory() as directory:
  root=Path(directory);(root/'README.md').write_text('```markdown\n[example](missing.md)\n```\n');v.validate_markdown_references(root);cases['fenced_example']={'outcome':'pass'}
 return dict(cases=cases,checks=dict(root_only_exclusion=True,formal_missing_and_escape_rejected=True,positive_links_preserved=True))

CASES={'identity_predicate':identities,'real_python39_all':lambda:actual_reports('/usr/bin/python3'),'real_python39_partial_verbose':lambda:actual_reports('/usr/bin/python3',True,True),'real_python314_all_verbose':lambda:actual_reports(sys.executable,False,True),'real_python314_partial':lambda:actual_reports(sys.executable,True),'strict_duplicate_truncated':strict_reports,'validator_scope':markdown_scope}
for name,case in CASES.items():
 offset=len(RUNS)
 try:item=case();item['passed']=all(item['checks'].values())
 except Exception as exc:item=dict(passed=False,error=str(exc),traceback=traceback.format_exc())
 item['process_runs']=RUNS[offset:];RESULTS[name]=item;OUT.write_text(json.dumps(RESULTS,ensure_ascii=False,indent=2));print(name,item['passed'],item.get('checks',item.get('error')),flush=True)
sys.exit(0 if all(v['passed'] for v in RESULTS.values()) else 1)
