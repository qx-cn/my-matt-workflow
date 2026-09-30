import sys,json
from pathlib import Path
sys.path.insert(0,'/tmp/ind04/current/tests')
from test_implement_review import ReviewTests
u=json.load(open('/tmp/workflow-independent-04-unit.json'))
spec_artifact=next(a for a in u['artifacts'] if a['side']=='input' and a['repo_path'].endswith('specs-workflow-simplification.md'))
text=Path(spec_artifact['snapshot_path']).read_text()
invariants=text.split('### M7. 全局不变量',1)[1].split('## 行为与验收',1)[0]
t=ReviewTests();t.setUp()
try:
 t.setup_config(tests=("python3 -c 'pass'",));t.ticket()
 spec=t.repo/'.agent/work/feature/specs/specs-feature-01.md'
 spec.write_text(spec.read_text()+'\n### M7. 全局不变量\n'+invariants+'\n**I-K1**: control invariant\n')
 t.cli('implement','start','--ticket','feature-01');t.cli('implement','test','--ticket','feature-01')
 report=t.review();manifest=json.loads(Path(report['manifest']).read_text())
 result=t.result(report)
 result['coverage'].append({'target':'I-K1','result':'not-applicable','reason':'control'})
 accepted=t.submit(result)
 print(json.dumps({'case':'omit_all_global_invariants','coverage_targets':manifest['coverage_targets'],'exit_code':accepted.returncode,'registered_status':json.loads(accepted.stdout)['status']},ensure_ascii=False))
 result['coverage'].append({'target':'I-6','result':'ok'})
 rejected=t.submit(result,ok=False)
 print(json.dumps({'case':'supply_I-6_coverage','exit_code':rejected.returncode,'stderr':rejected.stderr},ensure_ascii=False))
finally:t.doCleanups()
