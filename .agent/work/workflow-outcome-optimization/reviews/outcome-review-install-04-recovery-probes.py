import importlib.util
import json
import tempfile
import traceback
from pathlib import Path
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('independent04','/tmp/outcome-review-install-04-probes.py')
base=importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
# Loading helper definitions does not run its main. Preserve the main log separately.
installer=base.installer
rows=[]
output=Path('/tmp/outcome-review-install-04-recovery-probes.jsonl'); output.write_text('')

def run(kind,fn,**params):
    with tempfile.TemporaryDirectory(prefix='independent-r2-recovery04-') as tmp:
        root=Path(tmp).resolve(); row={'kind':kind,'fixture':str(root),**params}
        try:
            row.update(fn(root,**params)); row['pass']=True
        except Exception as exc:
            row.update({'pass':False,'exception':repr(exc),'traceback':traceback.format_exc()})
        rows.append(row)
        with output.open('a') as f: f.write(json.dumps(row,sort_keys=True)+'\n')

def legacy_journal(root,receipt_version,journal_version,link):
    p=base.package(root,'v1'); home=root/'host'; old=home/'old-parent/skills'
    installer.install_release(p,home,skills_home=old); state=base.legacy(home,receipt_version)
    originals={n:base.tree(old/n) for n in state['skills']}; receipt=base.receipt_path(home).read_bytes()
    txn=home/'my-matt-workflow/transaction'; backup=txn/('legacy-backup' if journal_version==3 else 'backup'); backup.mkdir(parents=True)
    new=home/'new-parent/skills' if journal_version==3 else old; new.mkdir(parents=True,exist_ok=True)
    for name in state['skills']:
        (old/name).rename(backup/name)
        (new/name).mkdir(); (new/name/'SKILL.md').write_text('partial new legacy target')
    journal={'skills':state['skills'],'old_present':state['skills'] if journal_version<3 else []}
    if journal_version>1:
        journal.update(version=journal_version,skills_home=str(new),new_release_id='v2',transaction_id='independent-legacy-tx')
    if journal_version==3: journal.update(previous_skills_home=str(old),legacy_old_present=state['skills'])
    (txn/'journal.json').write_text(json.dumps(journal,sort_keys=True)); base.remove_lock(home)
    if link!='none':
        moved=old if link=='root' else old.parent; outside=root/'outside'; moved.rename(outside)
        (outside/'sentinel').write_bytes(b'legacy recovery outside sentinel'); moved.symlink_to(outside,target_is_directory=True)
        r=base.unchanged_reject(root,lambda:installer.recover_interrupted_install(home))
        assert txn.exists() and base.receipt_path(home).read_bytes()==receipt
        return {'recovery':r,'transaction_preserved':True,'receipt_preserved':True}
    installer.recover_interrupted_install(home)
    assert not txn.exists() and base.receipt_path(home).read_bytes()==receipt
    for name in originals: assert base.tree(old/name)==originals[name]
    installer.verify_installed_state(state,state_home=home)
    return {'recovery':'restored exact old managed bytes','receipt_unchanged':True,'transaction_cleaned':True}

def missing_old(root,receipt_version,old_layout):
    p=base.package(root,'v1'); second=base.package(root,'v2'); home=root/'host'
    old=home/'old-parent/skills' if old_layout=='internal' else root/'canonical-external/skills'; new=home/'skills'
    installer.install_release(p,home,skills_home=old); state=base.legacy(home,receipt_version)
    originals={n:base.tree(old/n) for n in state['skills']}; receipt=base.receipt_path(home).read_bytes()
    rename=Path.rename
    def stop(path,dest):
        result=rename(path,dest)
        if Path(dest).parent.name=='legacy-backup' and Path(dest).name=='my-beta':
            raise KeyboardInterrupt('after all old managed moves')
        return result
    try:
        with patch.object(Path,'rename',stop): installer.install_release(second,home,skills_home=new)
    except KeyboardInterrupt: pass
    else: raise AssertionError('stop not reached')
    old.rmdir(); assert not old.exists()
    installer.recover_interrupted_install(home)
    assert base.receipt_path(home).read_bytes()==receipt
    for name in originals: assert base.tree(old/name)==originals[name]
    assert not (home/'my-matt-workflow/transaction').exists()
    installer.verify_installed_state(state,state_home=home)
    return {'recovery':'missing canonical old root recreated from verified backups','receipt_unchanged':True,'transaction_cleaned':True}

def committed_drift(root,receipt_version,link):
    home,old,new,txn,original,receipt,p=base.interrupted(root,receipt_version,'committed')
    moved=new if link=='root' else new.parent; outside=root/'outside'; moved.rename(outside); moved.symlink_to(outside,target_is_directory=True)
    base.remove_lock(home)
    r=base.unchanged_reject(root,lambda:installer.recover_interrupted_install(home))
    assert txn.exists()
    return {'recovery':r,'transaction_preserved':True}

for receipt_version in (1,2):
    for journal_version in (1,2,3):
        for link in ('none','root','ancestor'):
            run('legacy-journal',legacy_journal,receipt_version=receipt_version,journal_version=journal_version,link=link)
    for old_layout in ('internal','external'):
        run('missing-old',missing_old,receipt_version=receipt_version,old_layout=old_layout)
    for link in ('root','ancestor'):
        run('committed-drift',committed_drift,receipt_version=receipt_version,link=link)
summary={'source':str(base.FROZEN),'total':len(rows),'passed':sum(r['pass'] for r in rows),'failed':[r for r in rows if not r['pass']],'counts':{k:sum(r['kind']==k for r in rows) for k in ('legacy-journal','missing-old','committed-drift')},'script_sha256':base.digest(Path(__file__).read_bytes())}
Path('/tmp/outcome-review-install-04-recovery-summary.json').write_text(json.dumps(summary,indent=2)); print(json.dumps(summary,indent=2))
raise SystemExit(0 if not summary['failed'] else 1)
