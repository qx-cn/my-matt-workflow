from pathlib import Path
import subprocess,time,hashlib,json,sys
root=Path('/Users/sherly/CS/wsp/ai/my-matt-workflow');tag=sys.argv[1];frozen=Path(sys.argv[2]);log=Path('/tmp')/(tag+'.log')
start=time.monotonic();command=[sys.executable,'-B','-m','unittest','discover','-s','tests','-v']
with log.open('w') as stream:result=subprocess.run(command,cwd=root,stdout=stream,stderr=subprocess.STDOUT)
data={'command':command,'exit_code':result.returncode,'elapsed_seconds':round(time.monotonic()-start,3),'source_manifest_sha256':hashlib.sha256((frozen/'source-manifest.json').read_bytes()).hexdigest(),'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()}
(Path('/tmp')/(tag+'-result.json')).write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data));raise SystemExit(result.returncode)
