from pathlib import Path
import subprocess,hashlib,json,shutil,sys
root=Path('/Users/sherly/CS/wsp/ai/my-matt-workflow');dest=Path(sys.argv[1]);dest.mkdir()
paths=set(subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0'))|set(subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=root).decode().split('\0'))
extra={'.agent/matt-workflow.md','.agent/work/workflow-outcome-optimization/specs/specs-workflow-outcome-optimization-02.md','.agent/work/workflow-outcome-optimization/evidence/outcome-evaluation-runbook.md'}
rows=[]
for name in sorted(paths|extra):
 if not name or (name.startswith('.agent/') and name not in extra):continue
 p=root/name
 if not p.is_file():continue
 q=dest/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
 rows.append({'path':name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
m=dest/'source-manifest.json';m.write_text(json.dumps({'files':rows},ensure_ascii=False,indent=2)+'\n');print(json.dumps({'source_root':str(dest),'files':len(rows),'manifest_sha256':hashlib.sha256(m.read_bytes()).hexdigest()}))
