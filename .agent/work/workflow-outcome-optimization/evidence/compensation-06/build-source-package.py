from pathlib import Path
import json,hashlib,tarfile,io
root=Path('/Users/sherly/CS/wsp/ai/my-matt-workflow');frozen=Path('/tmp/outcome-ci-install-final-02');base=root/'.agent/work/workflow-outcome-optimization'
rows=json.loads((frozen/'source-manifest.json').read_text())['files'];items={x['path']:frozen/x['path'] for x in rows}
for directory in ['deliveries','plans','tickets','evidence','reviews']:
 for p in (base/directory).rglob('*'):
  if p.is_file() and not p.name.endswith('.tar.gz') and not p.name.startswith('source-package-identity') and not any(part in ('.git','__pycache__') for part in p.parts) and p.suffix!='.pyc':items[str(p.relative_to(root))]=p
for name in ['acceptance-evidence-02.json','outcome-instructions-object-dispositions.json','advisory-corrections.json','independent-review-provenance.json','final-source-identity.json','independent-findings.json','outcome-final-document-audit.json']:
 p=base/'evidence'/name;items[str(p.relative_to(root))]=p
items['construction-source-manifest.json']=frozen/'source-manifest.json'
manifest={'kind':'complete source candidate; not published or installed release','source_manifest_sha256':hashlib.sha256((frozen/'source-manifest.json').read_bytes()).hexdigest(),'removed_paths':['policies/decision-taxonomy.md','policies/project-discovery.md','policies/project-storage.md','policies/write-boundaries.md','resources/adapters/write-actions.md'],'files':[{'path':name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'mode':oct(p.stat().st_mode&0o777)} for name,p in sorted(items.items())]}
encoded=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode();dest=base/'deliveries/workflow-outcome-optimization-source-04.tar.gz'
with tarfile.open(dest,'w:gz') as tar:
 for name,p in sorted(items.items()):tar.add(p,arcname=name,recursive=False)
 info=tarfile.TarInfo('package-manifest.json');info.size=len(encoded);tar.addfile(info,io.BytesIO(encoded))
with tarfile.open(dest,'r:gz') as tar:
 for row in manifest['files']:
  assert hashlib.sha256(tar.extractfile(row['path']).read()).hexdigest()==row['sha256'],row['path']
  assert oct(tar.getmember(row['path']).mode&0o777)==row['mode'],row['path']
identity={'artifact':str(dest.relative_to(root)),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'size_bytes':dest.stat().st_size,'files':len(items),'source_manifest_sha256':manifest['source_manifest_sha256'],'verified':'all archive file bytes and modes checked against package-manifest; complete source plus delivery/index/AC/provenance','excluded':'Git metadata, old Topic histories, generated releases/current pointer, caches, real host state, historical snapshot archives and package self-hash receipt'}
(base/'evidence/compensation-06/source-package-identity-04.json').write_text(json.dumps(identity,ensure_ascii=False,indent=2)+'\n');print(json.dumps(identity,ensure_ascii=False))
