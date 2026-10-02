import os,sys,json
from pathlib import Path
sys.dont_write_bytecode=True
FINAL=Path('/tmp/outcome-holistic-608b72b');BASE=Path('/tmp/outcome-holistic-base-7947cb2')
sys.path[:0]=[str(FINAL),str(FINAL/'tests')]
import test_topic_lifecycle as seam
from test_topic_branch import BranchTests
seam.CLI=BASE/'tools/workflow.py'
t=BranchTests();t.setUp()
try:
    t.multi();t.cli('topic','test')
    first=t.branch_review();t.branch_submit(t.blocking(first))
    (t.repo/'code.txt').write_text('fixed\nsecond\nline three\nline four\n')
    t.cli('topic','test');t.branch_submit(t.result(t.branch_review()))
    before=json.loads(t.cli('topic','status').stdout)
    seam.CLI=FINAL/'tools/workflow.py'
    status=json.loads(t.cli('topic','status').stdout)
    attempt=t.cli('resolve','--branch','--accept','--reason','follow suggested status',ok=False)
    after=json.loads(t.cli('topic','status').stdout)
    out=dict(case='legacy-branch-geometric-stop',legacy_status=before,candidate_status=status,suggested_action_returncode=attempt.returncode,suggested_action_stderr=attempt.stderr,status_after_failed_action=after)
    Path('/tmp/outcome-holistic-runtime-geometry.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
    print(json.dumps(out,ensure_ascii=False,indent=2))
finally:t.doCleanups()
