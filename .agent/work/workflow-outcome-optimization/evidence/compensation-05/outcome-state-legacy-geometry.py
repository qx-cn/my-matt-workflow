import os,sys,json
from pathlib import Path
sys.dont_write_bytecode=True
FINAL=Path('/Users/sherly/CS/wsp/ai/my-matt-workflow');BASE=Path('/tmp/outcome-holistic-base-7947cb2')
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
    import shlex
    assert 'topic complete' in status['next_command'], status
    attempt=t.cli(*shlex.split(status['next_command'])[1:])
    after=json.loads(t.cli('topic','status','--topic','feature').stdout)
    out=dict(case='legacy-branch-geometric-stop',legacy_status=before,candidate_status=status,suggested_action_returncode=attempt.returncode,suggested_action_stderr=attempt.stderr,status_after_recommended_action=after)
    Path('/tmp/outcome-state-legacy-geometry.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
    print(json.dumps(out,ensure_ascii=False,indent=2))
finally:t.doCleanups()
