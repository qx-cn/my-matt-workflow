import json,re,posixpath,hashlib
from pathlib import Path
from urllib.parse import urlsplit,unquote
ROOT=Path('/tmp/outcome-review-integrated-01')
resources=json.loads((ROOT/'resources/manifest.json').read_text())['resources']
files={}
for skill in (ROOT/'skills').iterdir():
 if not skill.is_dir():continue
 for p in skill.rglob('*.md'):files[f'{skill.name}/{p.relative_to(skill).as_posix()}']=p.read_text()
 for res in resources.values():files[f"{skill.name}/{res['release_path']}"]=(ROOT/res['source']).read_text()
files={k:re.sub(r'\{\{skill-call:(my-[a-z0-9-]+)\}\}',r'/\1',v) for k,v in files.items()}
def prose(text):
 fence=None;out=[]
 for line in text.splitlines():
  m=re.match(r'^\s{0,3}(`{3,}|~{3,})',line)
  if m:
   marker=m.group(1)
   if fence is None:fence=marker
   elif marker[0]==fence[0] and len(marker)>=len(fence):fence=None
   continue
  if fence is None:out.append(line)
 return '\n'.join(out)
link=re.compile(r'!?\[[^\]]*\]\((<[^>]+>|[^)\s]+)(?:\s+[^)]*)?\)')
def closure(names):
 todo=[f'{n}/SKILL.md' for n in names];seen=set();texts=set();missing=[]
 while todo:
  p=todo.pop()
  if p in seen:continue
  seen.add(p)
  if p not in files:missing.append(p);continue
  t=files[p];texts.add(t)
  for m in link.finditer(prose(t)):
   u=urlsplit(m.group(1).strip('<>'));raw=unquote(u.path)
   if u.scheme or u.netloc or not raw or raw.startswith('/'):continue
   dest=posixpath.normpath(posixpath.join(posixpath.dirname(p),raw))
   if dest.startswith(p.split('/')[0]+'/') and dest.endswith('.md'):todo.append(dest)
 return dict(characters=sum(map(len,texts)),reachable_files=len(seen),unique_contents=len(texts),missing=missing)
main=['my-grill-with-docs','my-grilling','my-domain-modeling','my-to-spec','my-to-tickets','my-implement','my-tdd','my-code-review','my-review-design']
result={'baseline_record':json.loads((ROOT/'tests/fixtures/workflow_simplification/baseline.json').read_text())['measurement']['characters'],'main_all_optional_branches':closure(main),'entry_bodies':{n:len(files[f'{n}/SKILL.md']) for n in ['my-to-spec','my-triage','my-test-report','my-resolving-merge-conflicts','my-diagnosing-bugs']},'single_entry_all_optional':{n:closure([n]) for n in ['my-to-spec','my-triage','my-test-report','my-diagnosing-bugs']},'note':'Independent virtual Cursor Markdown projection and link traversal; resources available by declared release_path; no host or runtime execution. Not actual model reads.'}
print(json.dumps(result,ensure_ascii=False,indent=2))
Path('/tmp/outcome-review-loading-probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
