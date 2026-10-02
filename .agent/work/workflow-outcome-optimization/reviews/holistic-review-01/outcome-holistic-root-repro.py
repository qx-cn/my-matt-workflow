import os,sys,json,subprocess
from pathlib import Path
sys.dont_write_bytecode=True
FINAL=Path('/tmp/outcome-holistic-608b72b'); BASE=Path('/tmp/outcome-holistic-base-7947cb2')
sys.path[:0]=[str(FINAL),str(FINAL/'tests')]
import test_topic_lifecycle as seam
from test_batches import BatchTests

def new():
    t=BatchTests();t.setUp();return t

def old_pending(view):
    t=new()
    try:
        seam.CLI=BASE/'tools/workflow.py'
        t.setup();t.cli('implement','start','--ticket','feature-01')
        (t.repo/'code.txt').write_text('still incorrect\n')
        t.cli('implement','test');t.self_review()
        findings=t.repo/'.agent/findings.json';findings.write_text(json.dumps([dict(id='persisted-old-blocker',severity='blocking',view=view,summary='unresolved real caller failure',location='code.txt:1',basis='real caller requires correct output')]))
        t.cli('implement','self-review','--notes-file',str(t.repo/'.agent/self.md'),'--findings-file',str(findings))
        ticket=t.repo/'.agent/work/feature/tickets/tickets-feature-01.md';ticket.write_text(ticket.read_text().replace('- [ ]','- [x]'))
        old_finish=t.cli('implement','finish')
        seam.CLI=FINAL/'tools/workflow.py'
        stat=json.loads(t.cli('batch','status','--topic','feature').stdout)
        report=t.review()
        manifest=json.loads(Path(report['manifest']).read_text())
        closed=t.cli('batch','close','--topic','feature')
        unit=json.loads((t.repo/'.agent/work/feature/implementations/feature-01.json').read_text())
        return dict(case='legacy-'+view,old_finish=json.loads(old_finish.stdout),candidate_status=stat,review_self_findings=manifest['self_findings'],candidate_close=json.loads(closed.stdout),persisted_findings=unit['self_review']['findings'])
    finally:t.doCleanups()

def dynamic_import_failure():
    t=new()
    try:
        seam.CLI=FINAL/'tools/workflow.py'
        runner=t.repo/'full.py';runner.write_text('import unavailable_test_dependency\n')
        t.git('add','full.py');t.git('commit','-qm','unavailable baseline')
        t.setup(full='python3 -B full.py');t.implement()
        # A real behavior probe loads the plugin selected by the application.
        # The marker independently proves the behavior test reached its SUT.
        runner.write_text("from pathlib import Path\nimport importlib\ndef selected_plugin():\n    return 'json_typo_regression'\nPath('.agent/behavior-executed').write_text('selected_plugin invoked')\nimportlib.import_module(selected_plugin())\n")
        t.git('add','full.py');t.git('commit','-qm','regressed plugin selection')
        current=json.loads(t.cli('batch','test','--topic','feature').stdout)
        marker=(t.repo/'.agent/behavior-executed').read_text()
        report=t.review();closed=t.cli('batch','close','--topic','feature')
        return dict(case='actual-dynamic-import-failure',marker=marker,current=current,candidate_close=json.loads(closed.stdout))
    finally:t.doCleanups()

out=[old_pending('correctness'),old_pending('spec-challenge'),dynamic_import_failure()]
Path('/tmp/outcome-holistic-root-repro.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False,indent=2))
