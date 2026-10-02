import sys,time,tempfile,json,contextlib,io
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,sys.argv[1])
from tools.workflow_lib.release import build_release
from tools.workflow_lib import installer
from tools.workflow_lib.doctor import diagnose_repository
root=Path(sys.argv[1])
with tempfile.TemporaryDirectory(prefix='holistic-install-bench-') as tmp:
    tmp=Path(tmp)
    start=time.perf_counter()
    package=build_release(root/'skills',tmp/'releases',release_id='bench',upstream_id='local',repo_root=root)
    result={'source':str(root),'build_without_suite_seconds':time.perf_counter()-start}
    result['verify_seconds']=[]
    for i in range(3):
        start=time.perf_counter();installer.verify_release(package);result['verify_seconds'].append(time.perf_counter()-start)
    home=tmp/'home'
    start=time.perf_counter();installer.install_release(package,home);result['first_install_seconds']=time.perf_counter()-start
    result['same_install_seconds']=[]
    for i in range(3):
        start=time.perf_counter();outcome=installer.install_release(package,home);result['same_install_seconds'].append(time.perf_counter()-start)
    result['last_install_outcome']=outcome
    print(json.dumps(result))
