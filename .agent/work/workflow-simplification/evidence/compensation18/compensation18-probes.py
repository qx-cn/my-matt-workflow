import sys,json,shlex,subprocess
sys.path.insert(0,'tests')
from test_completion_compensation import CompletionCompensationTests
from tools.workflow_lib import topic_service as topics,ticket_review
c=CompletionCompensationTests();c.setUp()
try:
 case=c.fixture(2);c.restore_legacy(case)
 case.cli('implement','test','--ticket','feature-01')
 case.cli('resolve','--ticket','feature-01','--accept','--reason','user accepts gap')
 report=json.loads(case.cli('topic','status','--topic','feature').stdout)
 follow=subprocess.run(shlex.split(report['next_command'].replace('workflow.py',sys.executable+' tools/workflow.py',1)),capture_output=True,text=True)
 print(json.dumps({'legacy_between_tickets':report,'following_next':{'exit':follow.returncode,'stderr':follow.stderr}},ensure_ascii=False))
 case2=c.fixture();child,oid=c.gitlink(case2)
 # git submodule absorbgitdirs gives the conventional real submodule .git file.
 case2.git('submodule','absorbgitdirs','module')
 print(json.dumps({'git_file':(child/'.git').is_file(),'identity':topics.content_id(case2.repo),'frozen_mode':ticket_review.current_files(case2.repo)['module'][0]}))
 (child/'consumer.txt').write_text('dirty\n')
 try:topics.content_id(case2.repo)
 except topics.TopicError as e:print('actual_submodule_dirty_rejected='+str(e))
 # The private metadata repository can itself be a gitlink: explicitly ignored.
 case3=c.fixture();private=case3.repo/'.agent'
 case3.git('init','-q',cwd=private);case3.git('config','user.name','Test',cwd=private);case3.git('config','user.email','test@example.invalid',cwd=private)
 case3.git('add','.',cwd=private);case3.git('commit','-qm','metadata',cwd=private)
 case3.git('add','-f','.agent');case3.git('commit','-qm','private gitlink')
 before=topics.content_id(case3.repo)
 (private/'extra.md').write_text('private metadata change')
 print(json.dumps({'private_agent_gitlink_ignored':before==topics.content_id(case3.repo),'private_absent_from_frozen':'.agent' not in ticket_review.current_files(case3.repo)}))
finally:c.doCleanups()
