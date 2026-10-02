from pathlib import Path
import json,hashlib,subprocess,sys
root=Path('/Users/sherly/CS/wsp/ai/my-matt-workflow');manifest=json.loads(Path('/tmp/outcome-ci-install-final-02/source-manifest.json').read_text());h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert all(h(root/r['path'])==r['sha256'] for r in manifest['files'])
report=json.loads(subprocess.check_output([sys.executable,'-B',str(root/'tools/workflow.py'),'doctor'],cwd=root,text=True));assert report['source']['status']=='valid',report;assert report['current_release']['status']=='valid' and report['current_release']['source_match'] is True,report
hosts={}
for host in ['codex','claude']:
 state=json.loads((Path('/Users/sherly')/('.'+host)/'my-matt-workflow/install-state.json').read_text());assert report['hosts'][host]['status']=='valid',report['hosts'][host];assert state['release_id']==report['current_release']['release_id'];entry=Path(state['runtime_entry']);result=subprocess.run([sys.executable,'-B',str(entry),'--help'],capture_output=True,text=True);assert result.returncode==0 and 'workflow.py' in result.stdout,result
 runtime=entry.parent.parent
 for name in ['tools/workflow_lib/evidence.py','tools/workflow_lib/batches.py','tools/workflow_lib/validator.py']:
  assert h(runtime/name)==h(root/name),(host,name)
 hosts[host]={'release_id':state['release_id'],'skills':len(state['skills']),'runtime_entry':str(entry),'runtime_help_exit':result.returncode,'changed_runtime_bytes_match_source':True}
result={'doctor':report,'hosts':hosts,'source_manifest_sha256':h(Path('/tmp/outcome-ci-install-final-02/source-manifest.json')),'source_files':len(manifest['files']),'verification':'host installed content verified by doctor; runtime help actual exit; changed runtime bytes match source'}
Path('/tmp/outcome-final-host-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'release_id':report['current_release']['release_id'],'source_status':report['source']['status'],'source_match':True,'hosts':hosts},ensure_ascii=False))
