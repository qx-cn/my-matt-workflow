import json, sys, shlex
sys.path[:0]=['.', 'tests']
from test_completion_compensation import CompletionCompensationTests
from tools.workflow_lib.status_text import render
helper=CompletionCompensationTests()
try:
    case=helper.fixture(3);root=helper.restore_legacy(case)
    first=json.loads(case.cli('topic','status','--topic','feature').stdout)
    assert 'implement test' in first['next_command'] and '--ticket feature-01' in first['next_command']
    print('legacy_stop_priority',json.dumps(first,ensure_ascii=False))
    case.cli('implement','test','--ticket','feature-01')
    case.cli('resolve','--ticket','feature-01','--accept','--reason','review probe accepts evidence gap')
    following=json.loads(case.cli('topic','status','--topic','feature').stdout)
    assert '--ticket feature-02' in following['next_command']
    print('legacy_successor',json.dumps(following,ensure_ascii=False))
    argv=shlex.split(following['next_command'])[1:]
    started=case.cli(*argv)
    assert started.returncode==0
    print('execute_reported_next',started.returncode,started.stdout.strip())
    after=json.loads(case.cli('topic','status','--topic','feature').stdout)
    assert '--ticket feature-02' in after['next_command'] and 'implement test' in after['next_command']
    print('started_successor_priority',json.dumps(after,ensure_ascii=False))
    batchcase=helper.fixture(3);batchcase.cli('implement','start','--ticket','feature-01')
    human=batchcase.cli('batch','status','--topic','feature','--human')
    machine=json.loads(batchcase.cli('batch','status','--topic','feature').stdout)
    assert all(isinstance(t,str) for t in machine['tickets'])
    assert all(t in human.stdout for t in machine['tickets'])
    print('batch_multi_ids_human',human.returncode,human.stdout.strip())
    single=helper.fixture();helper.restore_legacy(single)
    single.cli('implement','test','--ticket','feature-01')
    single.cli('resolve','--ticket','feature-01','--accept','--reason','review probe accepts evidence gap')
    done=json.loads(single.cli('topic','status','--topic','feature').stdout)
    assert 'topic complete' in done['next_command']
    print('legacy_no_successor',json.dumps(done,ensure_ascii=False))
    for tickets in ([],['feature-01'],[{'ticket':'feature-01','status':'needs-user','stop_reason':'inconclusive'}]):
        print('renderer_protocol',render({'topic':'feature','status':'active','tickets':tickets}))
finally:
    helper.doCleanups()
