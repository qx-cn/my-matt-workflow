"""Reproduce the open-review accept defect using only frozen artifacts/public CLI.
Run from any cwd: python3 <this-script> [snapshot.json] [evidence-output.json]
The default manifest belongs to this review; every project is disposable /tmp.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

HERE = Path(__file__).resolve().parent
manifest_path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE/'independent-evidence/batch-05-07/snapshot.json'
output = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE/'review-batch-05-07-independent-round-1-repro-evidence.json'
manifest = json.loads(manifest_path.read_text())
artifacts = manifest['artifacts']
repo_prefix = '/Users/sherly/CS/wsp/ai/my-matt-workflow/'
base_prefix = repo_prefix+'.agent/work/workflow-simplification/reviews/independent-evidence/batch-05-07/base/'
evidence = {'content_id':manifest['content_id'], 'commands':[], 'scenarios':[], 'driver_exit_code':None}
with tempfile.TemporaryDirectory(prefix='batch057-independent-repro-') as temporary:
    tree = Path(temporary)/'final'
    for artifact in artifacts:
        source = artifact['source_path']
        relative = source.removeprefix(repo_prefix)
        if source.startswith(repo_prefix) and relative.startswith(('tools/','tests/')):
            snapshot = Path(artifact['snapshot_path'])
            assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == artifact['sha256']
            destination = tree/relative
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(snapshot,destination)
    base = Path(temporary)/'base'
    shutil.copytree(tree/'tools',base/'tools')
    for artifact in artifacts:
        source = artifact['source_path']
        if source.startswith(base_prefix) and source.removeprefix(base_prefix).startswith('tools/'):
            snapshot = Path(artifact['snapshot_path'])
            assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == artifact['sha256']
            shutil.copyfile(snapshot,base/source.removeprefix(base_prefix))
    sys.path.insert(0,str(tree/'tests'))
    import test_topic_lifecycle as topics
    from test_implement_review import ReviewTests
    from test_topic_branch import BranchTests
    original_cli = topics.CLI
    def wrap(case,scenario):
        original = case.cli
        def invoke(*args,**kwargs):
            result=original(*args,**kwargs)
            evidence['commands'].append(dict(scenario=scenario,runtime=str(topics.CLI),args=list(args),exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr))
            return result
        case.cli=invoke
    for mode in ('shared','private'):
        case=ReviewTests();case.setUp();scenario='formal-base-to-final-ticket-'+mode;wrap(case,scenario)
        try:
            topics.CLI=base/'tools/workflow.py'
            case.setup_config(mode,tests=("python3 -c 'pass'",));case.ticket()
            case.cli('implement','start','--ticket','feature-01');case.cli('implement','test')
            for _ in range(4):case.review()
            topics.CLI=original_cli
            case.cli('implement','review','--ticket','feature-01','--reviewer-model','actual-host-model',ok=False)
            stopped=json.loads(case.cli('implement','status').stdout)
            assert stopped['status']=='needs-user' and stopped['tests_passed']
            result=case.cli('resolve','--ticket','feature-01','--accept','--reason','accept interrupted review',ok=False)
            assert "KeyError: 'reviewer'" in result.stderr
            ticket=case.repo/'.agent/work/feature/tickets/tickets-feature-01.md'
            assert 'status: complete' in ticket.read_text()
            metrics=case.repo/'.agent/metrics.jsonl'
            evidence['scenarios'].append(dict(name=scenario,accept_exit_code=result.returncode,ticket_status='complete',metrics=metrics.read_text() if metrics.exists() else None,agent_dirty=case.git('status','--porcelain',cwd=case.repo/'.agent' if mode=='private' else case.repo)))
        finally:topics.CLI=original_cli;case.doCleanups()
    case=BranchTests();case.setUp();scenario='final-open-branch';wrap(case,scenario)
    try:
        case.multi();case.cli('topic','test')
        for _ in range(4):case.branch_review()
        case.cli('topic','review','--reviewer-model','actual-host-model',ok=False)
        result=case.cli('resolve','--branch','--accept','--reason','accept interrupted review',ok=False)
        assert "KeyError: 'reviewer'" in result.stderr
        evidence['scenarios'].append(dict(name=scenario,accept_exit_code=result.returncode,topic_still_active=(case.repo/'.agent/work/feature').exists(),archived=(case.repo/'.agent/archive/feature').exists()))
    finally:case.doCleanups()
evidence['driver_exit_code']=0
output.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'evidence':str(output),'driver_exit_code':0,'scenarios':evidence['scenarios']},ensure_ascii=False,indent=2))
