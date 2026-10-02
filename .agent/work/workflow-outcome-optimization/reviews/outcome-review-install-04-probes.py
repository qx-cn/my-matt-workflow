import hashlib
import json
import os
import stat
import sys
import tempfile
import traceback
from pathlib import Path
from unittest.mock import patch

FROZEN = Path('/tmp/outcome-review-final-05')
sys.path.insert(0, str(FROZEN))
from tools.workflow_lib import installer, projection, fs_safety

OUT = Path('/tmp/outcome-review-install-04-probes.jsonl')
OUT.write_text('')
RESULTS = []

def digest(b):
    return hashlib.sha256(b).hexdigest()

def tree(root):
    result = {}
    def visit(p):
        info = p.lstat()
        mode = stat.S_IMODE(info.st_mode)
        key = str(p.relative_to(root))
        if stat.S_ISLNK(info.st_mode):
            result[key] = ['link', mode, os.readlink(p)]
        elif stat.S_ISDIR(info.st_mode):
            result[key] = ['dir', mode]
            for child in sorted(p.iterdir()):
                visit(child)
        elif stat.S_ISREG(info.st_mode):
            result[key] = ['file', mode, digest(p.read_bytes())]
        else:
            result[key] = ['other', mode]
    if root.exists() or root.is_symlink():
        visit(root)
    return result

def own_inventory(root):
    return {k: v[2] for k, v in tree(root).items() if v[0] == 'file'}

def package(root, rid):
    p = root / 'releases' / rid
    for name in ('my-alpha', 'my-beta'):
        s = p / 'skills' / name
        (s / 'agents').mkdir(parents=True)
        (s / 'SKILL.md').write_text('---\nname: '+name+'\ndescription: independent fixture\ndisable-model-invocation: true\n---\n# Fixture '+rid+'\n')
        (s / 'agents/openai.yaml').write_text('policy:\n  allow_implicit_invocation: false\n')
        (s / 'payload.bin').write_bytes((name + ':' + rid).encode())
    rt = p / 'runtime/tools/workflow.py'
    rt.parent.mkdir(parents=True)
    rt.write_text('# inert independent fixture runtime '+rid+'\n')
    skills = {s.name: own_inventory(s) for s in (p/'skills').iterdir()}
    runtime = own_inventory(p/'runtime')
    manifest = {'release_id': rid, 'skills': skills, 'runtime': runtime,
                'target_manifests': {t: {'skills': projection.projected_skills_inventory(p/'skills',t), 'runtime':runtime} for t in projection.TARGETS}}
    (p/'manifest.json').write_text(json.dumps(manifest, sort_keys=True))
    installer.verify_release(p)
    return p

def receipt_path(home):
    return home / 'my-matt-workflow/install-state.json'

def legacy(home, version):
    p = receipt_path(home)
    state = json.loads(p.read_text())
    if version == 1:
        for key in ('version', 'managed_inventory', 'manifest_sha256'):
            del state[key]
        p.write_text(json.dumps(state, sort_keys=True))
    state = installer.load_install_state(p)
    installer.verify_installed_state(state, state_home=home)
    return state

def remove_lock(home):
    (home/'my-matt-workflow/.install.lock').unlink(missing_ok=True)

def unchanged_reject(root, call):
    before = tree(root)
    try:
        call()
    except installer.InstallError as exc:
        error = str(exc)
    else:
        raise AssertionError('expected InstallError, call returned successfully')
    after = tree(root)
    assert before == after, {'changed': sorted(k for k in set(before)|set(after) if before.get(k)!=after.get(k))}
    return {'error': error, 'full_fixture_unchanged': True, 'before_sha256': digest(json.dumps(before,sort_keys=True).encode())}

def record(kind, **values):
    with tempfile.TemporaryDirectory(prefix='independent-r2-04-') as tmp:
        root = Path(tmp).resolve()
        row = {'kind':kind, 'fixture':str(root), **values}
        try:
            row.update(RUNNERS[kind](root, **values))
            row['pass'] = True
        except Exception as exc:
            row.update({'pass':False, 'exception':repr(exc), 'traceback':traceback.format_exc()})
        RESULTS.append(row)
        with OUT.open('a') as f:
            f.write(json.dumps(row,sort_keys=True)+'\n')

def target_value(target):
    return None if target == 'portable' else target

def drift(root, version, target, layout):
    p = package(root,'v1'); home = root/'host'
    old = home/('legacy-skills' if layout=='custom' else 'skills')
    new = home/('skills' if layout=='custom' else 'new-skills')
    assert installer.install_release(p,home,target=target_value(target),skills_home=old)=='installed'
    state = legacy(home,version)
    outside = root/'outside'
    old.rename(outside); (outside/'sentinel').write_bytes(b'independent outside sentinel')
    old.symlink_to(outside,target_is_directory=True)
    remove_lock(home)
    assert not new.exists()
    verify = unchanged_reject(root,lambda:installer.verify_installed_state(state,state_home=home))
    install = unchanged_reject(root,lambda:installer.install_release(p,home,target=target_value(target),skills_home=new))
    assert not (home/'my-matt-workflow/transaction').exists()
    assert not (home/'my-matt-workflow/.install.lock').exists()
    return {'old_recorded':state['skills_home'],'new_selected':str(new), 'verify':verify,'install':install,'transaction_absent_unchanged':True,'old_lock_not_recreated':True}

def ancestor(root,version,target):
    p=package(root,'v1'); home=root/'host'; parent=home/'nested'; old=parent/'skills'; new=home/'skills'
    installer.install_release(p,home,target=target_value(target),skills_home=old)
    state=legacy(home,version); outside=root/'outside'; parent.rename(outside)
    (outside/'sentinel').write_bytes(b'ancestor outside sentinel'); parent.symlink_to(outside,target_is_directory=True)
    remove_lock(home)
    return {'verify':unchanged_reject(root,lambda:installer.verify_installed_state(state,state_home=home)), 'install':unchanged_reject(root,lambda:installer.install_release(p,home,target=target_value(target),skills_home=new)), 'transaction_absent_unchanged':not (home/'my-matt-workflow/transaction').exists()}

def legal(root,version,target,layout):
    p=package(root,'v1'); home=root/'actual-host'; selected=home
    if layout=='host-alias':
        selected=root/'selected-host'; home.mkdir(); selected.symlink_to(home,target_is_directory=True)
        old=selected/'nested/legacy-skills'; canonical_old=home/'nested/legacy-skills'
    else:
        canonical_old=root/'another-host/skills'; canonical_old.mkdir(parents=True)
        old=root/'historically-selected-external-alias'; old.symlink_to(canonical_old,target_is_directory=True)
    installer.install_release(p,selected,target=target_value(target),skills_home=old)
    state=legacy(home,version)
    assert state['skills_home']==str(canonical_old)
    assert state['runtime_entry']==str(home/'my-matt-workflow/runtime/v1/tools/workflow.py')
    (canonical_old/'sentinel').write_bytes(b'legal old sentinel')
    before={n:tree(canonical_old/n) for n in state['skills']}
    status=installer.install_release(p,selected,target=target_value(target))
    assert status=='installed'
    for n in state['skills']:
        assert not (canonical_old/n).exists()
        assert before[n]==tree(home/'skills'/n)
    assert (canonical_old/'sentinel').read_bytes()==b'legal old sentinel'
    new=installer.load_install_state(receipt_path(home)); installer.verify_installed_state(new,state_home=selected)
    assert new['skills_home']==str(home/'skills')
    snap=tree(root); assert installer.install_release(p,selected,target=target_value(target))=='current'; assert tree(root)==snap
    installer.recover_interrupted_install(selected); assert tree(root)==snap
    return {'migration':status,'current':'current','recovery':'no-transaction unchanged','recorded_old':state['skills_home'],'recorded_new':new['skills_home'],'managed_bytes_preserved':True,'sentinel_unchanged':True}

def interrupted(root,version,phase,old_layout='internal'):
    p=package(root,'v1'); second=package(root,'v2'); home=root/'host'
    old=home/'nested/legacy-skills' if old_layout=='internal' else root/'canonical-external/skills'
    new=home/'new-parent/skills'
    installer.install_release(p,home,skills_home=old); legacy(home,version)
    original={n:tree(old/n) for n in ('my-alpha','my-beta')}; receipt=receipt_path(home).read_bytes()
    rename=Path.rename; replace=Path.replace
    def stop_move(path,dest):
        result=rename(path,dest)
        if phase=='old-move' and Path(dest).parent.name=='legacy-backup' and Path(dest).name=='my-alpha':
            raise KeyboardInterrupt('independent stop after real old rename')
        return result
    def stop_commit(path,dest):
        result=replace(path,dest)
        if phase=='committed' and Path(dest)==receipt_path(home):
            raise KeyboardInterrupt('independent stop after real receipt commit')
        return result
    try:
        with patch.object(Path,'rename',stop_move),patch.object(Path,'replace',stop_commit):
            installer.install_release(second,home,skills_home=new)
    except KeyboardInterrupt:
        pass
    else:
        raise AssertionError('interruption was not reached')
    transaction=home/'my-matt-workflow/transaction'
    assert (transaction/'journal.json').is_file()
    return home,old,new,transaction,original,receipt,second

def recovery_drift(root,version,which,link):
    home,old,new,txn,original,receipt,p=interrupted(root,version,'old-move')
    chosen=old if which=='old' else new
    moved=chosen if link=='root' else chosen.parent
    outside=root/'outside'; moved.rename(outside); (outside/'sentinel').write_bytes(b'recovery sentinel')
    moved.symlink_to(outside,target_is_directory=True); remove_lock(home)
    result=unchanged_reject(root,lambda:installer.recover_interrupted_install(home))
    assert txn.is_dir() and receipt_path(home).read_bytes()==receipt
    return {'recovery':result,'transaction_preserved':True,'receipt_preserved':True}

def recovery_positive(root,version,phase,old_layout):
    home,old,new,txn,original,receipt,p=interrupted(root,version,phase,old_layout)
    installer.recover_interrupted_install(home)
    assert not txn.exists()
    if phase=='old-move':
        assert receipt_path(home).read_bytes()==receipt
        for n in original:
            assert tree(old/n)==original[n]
            assert not (new/n).exists()
        installer.verify_installed_state(installer.load_install_state(receipt_path(home)),state_home=home)
        assert installer.install_release(p,home,skills_home=new)=='installed'
    else:
        assert installer.load_install_state(receipt_path(home))['release_id']=='v2'
    assert installer.install_release(p,home,skills_home=new)=='current'
    return {'recovery':'rollback exact old bytes/receipt' if phase=='old-move' else 'committed v2 retained','transaction_cleaned':True,'retry_current':True}

def runtime_drift(root,version,link):
    p=package(root,'v1'); home=root/'host'; installer.install_release(p,home); state=legacy(home,version)
    rt=home/'my-matt-workflow/runtime/v1'; moved=rt if link=='root' else rt.parent
    outside=root/'outside'; moved.rename(outside); moved.symlink_to(outside,target_is_directory=True); remove_lock(home)
    return {'verify':unchanged_reject(root,lambda:installer.verify_installed_state(state,state_home=home)), 'install':unchanged_reject(root,lambda:installer.install_release(p,home))}

RUNNERS={'drift':drift,'ancestor':ancestor,'legal':legal,'recovery-drift':recovery_drift,'recovery-positive':recovery_positive,'runtime-drift':runtime_drift}

if __name__=='__main__':
    identities={m.__name__:str(Path(m.__file__)) for m in (installer,projection,fs_safety)}
    for path in identities.values():
        assert Path(path).is_relative_to(FROZEN)
    for version in (1,2):
        for target in ('portable','codex','cursor','claude'):
            for layout in ('custom','default'):
                record('drift',version=version,target=target,layout=layout)
            record('ancestor',version=version,target=target)
            for layout in ('host-alias','external-alias'):
                record('legal',version=version,target=target,layout=layout)
        for which in ('old','new'):
            for link in ('root','ancestor'):
                record('recovery-drift',version=version,which=which,link=link)
        for phase in ('old-move','committed'):
            for old_layout in ('internal','external'):
                record('recovery-positive',version=version,phase=phase,old_layout=old_layout)
        for link in ('root','ancestor'):
            record('runtime-drift',version=version,link=link)
    summary={'source':str(FROZEN),'module_identities':identities,'total':len(RESULTS),'passed':sum(r['pass'] for r in RESULTS),'failed':[r for r in RESULTS if not r['pass']], 'counts':{k:sum(r['kind']==k for r in RESULTS) for k in RUNNERS},'script_sha256':digest(Path(__file__).read_bytes())}
    Path('/tmp/outcome-review-install-04-probes-summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
    sys.exit(0 if not summary['failed'] else 1)
