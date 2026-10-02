"""Ordinary engineering runner: execute every discovered unittest once in shards."""
from pathlib import Path
import sys,unittest,json,subprocess,time,hashlib,collections
root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(exist_ok=True,parents=True)
sys.path[:0]=[str(root),str(root/'tests')]
if len(sys.argv)>3:
    n=sys.argv[3];ids=json.loads((out/f'shard-{n}-ids.json').read_text())
    start=time.monotonic()
    with (out/f'shard-{n}.log').open('w') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(ids))
    data={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'expected_failures':len(result.expectedFailures),'unexpected_successes':len(result.unexpectedSuccesses),'seconds':round(time.monotonic()-start,3),'successful':result.wasSuccessful()}
    (out/f'shard-{n}-result.json').write_text(json.dumps(data,indent=2)+'\n')
    sys.exit(not result.wasSuccessful())
manifest=root/'source-manifest.json';m=json.loads(manifest.read_text())
def mismatches():
    return [x['path'] for x in m['files'] if hashlib.sha256((root/x['path']).read_bytes()).hexdigest()!=x['sha256']]
assert not mismatches(),mismatches()
def flatten(suite):
    for test in suite:
        if isinstance(test,unittest.TestSuite):yield from flatten(test)
        else:yield test.id()
ids=list(flatten(unittest.defaultTestLoader.discover(str(root/'tests'))))
assert len(set(ids))==len(ids),'discovery duplicated test IDs'
modules=collections.defaultdict(list)
for testid in ids:modules[testid.split('.')[0]].append(testid)
buckets=[[] for _ in range(4)]
for group in sorted(modules.values(),key=len,reverse=True):min(buckets,key=len).extend(group)
(out/'discovery.json').write_text(json.dumps({'source_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'discovery':'unittest.defaultTestLoader.discover(tests)','count':len(ids),'ids':ids,'shards':len(buckets)},indent=2)+'\n')
start=time.monotonic();children=[];streams=[]
for i,bucket in enumerate(buckets):
    (out/f'shard-{i}-ids.json').write_text(json.dumps(bucket,indent=2)+'\n')
    stream=(out/f'shard-{i}-stdout.log').open('w');streams.append(stream)
    children.append(subprocess.Popen([sys.executable,'-B',__file__,str(root),str(out),str(i)],cwd=root,stdout=stream,stderr=subprocess.STDOUT))
print(json.dumps({'discovered':len(ids),'shard_counts':list(map(len,buckets))}),flush=True)
codes=[child.wait() for child in children]
for stream in streams:stream.close()
results=[json.loads((out/f'shard-{i}-result.json').read_text()) if (out/f'shard-{i}-result.json').exists() else {'missing_result':True} for i in range(4)]
bad=mismatches();successful=not any(codes) and not bad and sum(r.get('tests',0) for r in results)==len(ids)
summary={'successful':successful,'exit_codes':codes,'discovered':len(ids),'executed':sum(r.get('tests',0) for r in results),'seconds':round(time.monotonic()-start,3),'shards':results,'source_mismatches':bad,'source_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest()}
(out/'result.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary),flush=True)
sys.exit(not successful)
