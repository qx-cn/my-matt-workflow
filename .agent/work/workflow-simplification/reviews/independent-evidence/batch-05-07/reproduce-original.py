"""Re-run original frozen defect; output is written outside retained evidence."""
import hashlib,json,subprocess,sys,tarfile,tempfile
from pathlib import Path
root=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='batch057-retained-') as directory:
    tmp=Path(directory)
    manifest=json.loads((root/'retained-snapshot.json').read_text())
    with tarfile.open(root/'retained-artifacts.tar.gz','r:gz') as archive:
        for artifact in manifest['artifacts']:
            name=Path(artifact['snapshot_path']).name
            data=archive.extractfile(name).read()
            assert hashlib.sha256(data).hexdigest()==artifact['sha256']
            destination=tmp/name
            destination.write_bytes(data)
            artifact['snapshot_path']=str(destination)
    path=tmp/'snapshot.json'
    path.write_text(json.dumps(manifest))
    output=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path('/tmp/batch05-07-original-repro.json')
    driver=root.parent.parent/'review-batch-05-07-independent-round-1-repro.py'
    result=subprocess.run([sys.executable,str(driver),str(path),str(output)])
    raise SystemExit(result.returncode)
