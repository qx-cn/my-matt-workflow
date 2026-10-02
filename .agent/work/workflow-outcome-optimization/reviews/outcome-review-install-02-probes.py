import sys, json, hashlib, shutil, tempfile, time, os
from pathlib import Path
from unittest.mock import patch

SOURCE = Path('/tmp/outcome-review-install-repair-02b')
sys.path.insert(0, str(SOURCE))
from tools.workflow_lib import installer as I, release as R, doctor as D, projection as P
assert Path(I.__file__).resolve() == SOURCE.resolve() / 'tools/workflow_lib/installer.py'
RESULTS = []

def emit(name, **facts):
    item = dict(probe=name, **facts)
    RESULTS.append(item)
    print(json.dumps(item, ensure_ascii=False), flush=True)

def fixture(base, names=('my-alpha', 'my-beta')):
    root = base / 'repo'
    for name in names:
        s = root / 'skills' / name
        (s / 'agents').mkdir(parents=True)
        (s / 'SKILL.md').write_bytes(('---\nname: '+name+'\ndescription: probe\ndisable-model-invocation: true\n---\n# One\n{{skill-call:my-alpha}}\n[extra](extra.txt)\n').encode())
        (s / 'agents/openai.yaml').write_text('policy:\n  allow_implicit_invocation: false\n')
        (s / 'extra.txt').write_text('original '+name)
    return root

def build(root, version):
    return R.build_release(root/'skills',root/'releases',release_id=version,upstream_id='local',repo_root=root)

def legacy(package):
    p=package/'manifest.json'; d=json.loads(p.read_bytes())
    for name in ('target_manifests','source_input_digest'): d.pop(name, None)
    p.write_text(json.dumps(d))

def tree(root):
    if not root.exists(): return None
    return {p.relative_to(root).as_posix(): ('link:'+os.readlink(p) if p.is_symlink() else hashlib.sha256(p.read_bytes()).hexdigest())
            for p in root.rglob('*') if p.is_file() or p.is_symlink()}

def attempt(call):
    try: return {'returned':call()}
    except (I.InstallError, OSError, RuntimeError) as e: return {'error_type':type(e).__name__,'error':str(e)}

def runtime_matrix():
    for projection in ('portable','codex','cursor','claude'):
        for mutation in ('clean','modify','delete','add','link','dangling','cache-link','fifo','byproducts'):
            with tempfile.TemporaryDirectory(prefix='review02-runtime-') as tmp:
                base=Path(tmp); root=fixture(base); package=build(root,'v1'); legacy(package)
                home=base/'home'; target=None if projection=='portable' else projection
                I.install_release(package,home,target=target)
                rt=home/'my-matt-workflow/runtime/v1'; entry=rt/'tools/workflow.py'
                before=(home/'my-matt-workflow/install-state.json').read_bytes()
                if mutation=='modify': entry.write_text('raise RuntimeError("TAMPERED")')
                if mutation=='delete': entry.unlink()
                if mutation=='add': (rt/'unexpected.py').write_text('UNEXPECTED')
                if mutation=='link': (rt/'unexpected-link').symlink_to(base)
                if mutation=='dangling': (rt/'unexpected-link').symlink_to(base/'missing')
                if mutation=='cache-link': (rt/'__pycache__').symlink_to(base)
                if mutation=='fifo': os.mkfifo(rt/'unexpected-fifo')
                if mutation=='byproducts':
                    (rt/'__pycache__').mkdir(); (rt/'__pycache__/demo.pyc').write_bytes(b'cache'); (rt/'.DS_Store').write_text('finder')
                outcome=attempt(lambda:I.install_release(package,home,target=target))
                host=D._host_status(home,current_release_id='v1',source_skills=['my-alpha','my-beta'],validation_context=I.ReleaseValidationContext())
                expected=mutation in ('clean','byproducts')
                assert (outcome.get('returned')=='current') == expected, outcome
                assert host['status']==('valid' if expected else 'invalid'), host
                assert before==(home/'my-matt-workflow/install-state.json').read_bytes()
                emit('legacy-runtime',projection=projection,mutation=mutation,host=host['status'],state_unchanged=True,**outcome)

def interrupted_matrix():
    phases=('old-first','old-last','new-first','after-refresh','runtime','commit')
    for mode in ('upgrade','migration','initial','legacy-v4'):
        for phase in phases:
            if mode=='initial' and phase.startswith('old'): continue
            if mode=='migration' and phase=='old-first': continue
            for corrupt in (False,True):
                if corrupt and mode=='initial': continue
                with tempfile.TemporaryDirectory(prefix='review02-recover-') as tmp:
                    base=Path(tmp); root=fixture(base); first=build(root,'v1'); home=base/'home'
                    oldhome=base/'old-skills' if mode=='migration' else home/'skills'
                    newhome=base/'new-skills' if mode=='migration' else oldhome
                    if mode!='initial': I.install_release(first,home,skills_home=oldhome,target='codex')
                    old_tree=tree(oldhome)
                    statepath=home/'my-matt-workflow/install-state.json'
                    old_state=statepath.read_bytes() if statepath.exists() else None
                    # exercise removed old name, changed old name, and added new name
                    shutil.rmtree(root/'skills/my-beta')
                    shutil.copytree(root/'skills/my-alpha',root/'skills/my-gamma')
                    gamma=root/'skills/my-gamma/SKILL.md'; gamma.write_text(gamma.read_text().replace('name: my-alpha','name: my-gamma'))
                    (root/'skills/my-alpha/extra.txt').write_text('V2')
                    second=build(root,'v2'); txn=home/'my-matt-workflow/transaction'
                    real_rename=Path.rename; real_replace=Path.replace; real_refresh=I.refresh_owned_directory
                    fired=[False]
                    def stop():
                        fired[0]=True; raise KeyboardInterrupt('independent interruption '+phase)
                    def rename(path,destination):
                        result=real_rename(path,destination); dest=Path(destination)
                        if phase=='old-first' and dest.parent.name=='backup': stop()
                        if phase=='old-last' and dest.parent.name in ('legacy-backup' if mode=='migration' else 'backup',) and path.name=='my-beta': stop()
                        if phase=='new-first' and path.parent.name=='staged': stop()
                        if phase=='runtime' and path.name=='staged-runtime': stop()
                        return result
                    def replace(path,destination):
                        result=real_replace(path,destination)
                        if phase=='commit' and path.name=='install-state.json': stop()
                        return result
                    def refresh(*args,**kwargs):
                        result=real_refresh(*args,**kwargs)
                        if phase=='after-refresh' and not (txn/'staged/my-alpha').exists(): stop()
                        return result
                    try:
                        with patch.object(Path,'rename',rename),patch.object(Path,'replace',replace),patch.object(I,'refresh_owned_directory',refresh):
                            I.install_release(second,home,skills_home=newhome,target='codex')
                    except KeyboardInterrupt: pass
                    assert fired[0], (mode,phase)
                    if mode=='legacy-v4':
                        jp=txn/'journal.json'; j=json.loads(jp.read_bytes()); j.pop('previous_state_sha256'); jp.write_text(json.dumps(j))
                        I.register_owned_directory(txn.parent,txn,purpose='install-transaction',control_paths=('journal.json',))
                    if corrupt:
                        victim = newhome/'my-alpha/extra.txt' if phase=='commit' else txn/('legacy-backup' if mode=='migration' else 'backup')/'my-alpha/extra.txt'
                        if not victim.exists():
                            victim=oldhome/'my-alpha/extra.txt'
                        assert victim.exists(), (mode,phase)
                        victim.write_text('CORRUPTED BACKUP OR TARGET')
                    snapshots=(tree(oldhome),tree(newhome),tree(txn),statepath.read_bytes() if statepath.exists() else None)
                    outcome=attempt(lambda:I.recover_interrupted_install(home))
                    if corrupt:
                        assert 'error' in outcome,(mode,phase,outcome)
                        assert snapshots==(tree(oldhome),tree(newhome),tree(txn),statepath.read_bytes() if statepath.exists() else None),(mode,phase,'mutated')
                    else:
                        assert 'error' not in outcome,(mode,phase,outcome)
                        assert not txn.exists()
                        if phase=='commit':
                            I.verify_installed_state(I.load_install_state(statepath),state_home=home)
                            assert I.load_install_state(statepath)['release_id']=='v2'
                        else:
                            assert tree(oldhome)==({} if mode=='initial' else old_tree),(mode,phase,'old content differs')
                            assert (statepath.read_bytes() if statepath.exists() else None)==old_state
                            if mode=='migration': assert tree(newhome)=={}
                    emit('interrupted',mode=mode,phase=phase,corrupt=corrupt,evidence_preserved=corrupt,**outcome)

def ownership_and_counts():
    with tempfile.TemporaryDirectory(prefix='review02-counts-') as tmp:
        base=Path(tmp);root=fixture(base);first=build(root,'v1');homes={n:base/n for n in ('a','b')}
        for home in homes.values(): I.install_release(first,home)
        with patch.object(I,'verify_release',wraps=I.verify_release) as v:
            assert I.install_release(first,homes['a'])=='current'; same=v.call_count
        (root/'skills/my-alpha/extra.txt').write_text('changed'); second=build(root,'v2')
        with patch.object(I,'verify_release',wraps=I.verify_release) as v:
            I.install_release(second,homes['a']); changed=v.call_count
        with patch.object(I,'verify_release',wraps=I.verify_release) as v:
            ctx=I.ReleaseValidationContext()
            reports={n:D._host_status(h,current_release_id='v2',source_skills=['my-alpha','my-beta'],validation_context=ctx) for n,h in homes.items()}
            doctor=v.call_count
        assert same==1 and changed==2 and doctor==2
        emit('validation-counts',current=same,upgrade=changed,doctor_distinct_packages=doctor,hosts={n:r['status'] for n,r in reports.items()})
        # Copy matching runtime bytes to a different home and rewrite only receipt's runtime identity.
        st=homes['b']/'my-matt-workflow/install-state.json'; d=json.loads(st.read_bytes())
        external=base/'external/v1'; shutil.copytree(homes['b']/'my-matt-workflow/runtime/v1',external)
        d['runtime_entry']=str(external/'tools/workflow.py'); st.write_text(json.dumps(d))
        outcome=attempt(lambda:I.install_release(first,homes['b']))
        report=D._host_status(homes['b'],current_release_id='v1',source_skills=['my-alpha','my-beta'],validation_context=I.ReleaseValidationContext())
        assert 'error' in outcome and report['status']=='invalid'
        emit('foreign-runtime-receipt',host=report['status'],**outcome)
    for parent in ('runtime','my-matt-workflow'):
        with tempfile.TemporaryDirectory(prefix='review02-parent-link-') as tmp:
            base=Path(tmp); root=fixture(base); first=build(root,'v1'); home=base/'home';external=base/'external'
            external.mkdir(); home.mkdir()
            if parent=='runtime': (home/'my-matt-workflow').mkdir()
            link=home/'my-matt-workflow' if parent=='my-matt-workflow' else home/'my-matt-workflow/runtime'
            link.symlink_to(external,target_is_directory=True)
            outcome=attempt(lambda:I.install_release(first,home))
            emit('runtime-parent-link',parent=parent,outside_written=bool(tree(external)),**outcome)

if __name__=='__main__':
    start=time.monotonic()
    runtime_matrix(); interrupted_matrix(); ownership_and_counts()
    emit('complete',probes=len(RESULTS),elapsed_seconds=round(time.monotonic()-start,3))
