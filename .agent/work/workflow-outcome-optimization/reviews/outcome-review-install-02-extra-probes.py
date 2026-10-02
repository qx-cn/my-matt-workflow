import sys, tempfile, json, shutil, time, importlib.util
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,'/tmp')
spec=importlib.util.spec_from_file_location('review02_probes','/tmp/outcome-review-install-02-probes.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
I,R,D=m.I,m.R,m.D
start=time.monotonic()
for projection in ('portable','codex','cursor','claude'):
    with tempfile.TemporaryDirectory(prefix='review02-modern-link-') as tmp:
        base=Path(tmp);root=m.fixture(base);package=m.build(root,'v1');home=base/'home'
        target=None if projection=='portable' else projection
        I.install_release(package,home,target=target)
        runtime=home/'my-matt-workflow/runtime/v1'; (runtime/'unexpected-link').symlink_to(base)
        before=m.tree(home)
        result=m.attempt(lambda:I.install_release(package,home,target=target))
        assert 'error' in result and before==m.tree(home)
        m.emit('modern-runtime-link',projection=projection,home_unchanged=True,**result)

for mode in ('ordinary','migration','state-v1','state-drift','source-drift'):
    with tempfile.TemporaryDirectory(prefix='review02-replay-') as tmp:
        base=Path(tmp);root=m.fixture(base);first=m.build(root,'v1');home=base/'home'
        oldhome=base/'old-skills' if mode=='migration' else home/'skills';newhome=base/'new-skills' if mode=='migration' else oldhome
        I.install_release(first,home,skills_home=oldhome)
        statepath=home/'my-matt-workflow/install-state.json'
        if mode=='state-v1':
            d=json.loads(statepath.read_bytes())
            for key in ('version','managed_inventory','manifest_sha256'): d.pop(key)
            statepath.write_text(json.dumps(d))
        original=m.tree(oldhome);state=statepath.read_bytes()
        (root/'skills/my-alpha/extra.txt').write_text('new');second=m.build(root,'v2')
        rename=Path.rename
        def interrupt_new_move(path,destination):
            result=rename(path,destination)
            if path.name=='staged-runtime': raise KeyboardInterrupt('before commit')
            return result
        try:
            with patch.object(Path,'rename',interrupt_new_move): I.install_release(second,home,skills_home=newhome)
        except KeyboardInterrupt: pass
        txn=home/'my-matt-workflow/transaction'
        if mode=='state-drift':
            d=json.loads(statepath.read_bytes());d['installed_at']='changed-valid-date';statepath.write_text(json.dumps(d))
        if mode=='source-drift': (first/'skills/my-alpha/extra.txt').write_text('tampered release')
        snapshots=(m.tree(home),m.tree(oldhome),m.tree(newhome))
        if mode in ('state-drift','source-drift'):
            result=m.attempt(lambda:I.recover_interrupted_install(home))
            assert 'error' in result and snapshots==(m.tree(home),m.tree(oldhome),m.tree(newhome))
            m.emit('recovery-identity-drift',mode=mode,unchanged=True,**result)
        else:
            def interrupt_restore(path,destination):
                result=rename(path,destination)
                if path.parent.name in ('backup','legacy-backup'): raise KeyboardInterrupt('during recovery restore')
                return result
            try:
                with patch.object(Path,'rename',interrupt_restore): I.recover_interrupted_install(home)
            except KeyboardInterrupt: pass
            assert txn.exists()
            I.recover_interrupted_install(home)
            assert not txn.exists() and m.tree(oldhome)==original and statepath.read_bytes()==state
            m.emit('recovery-replay',mode=mode,original_restored=True,transaction_removed=True)

with tempfile.TemporaryDirectory(prefix='review02-summary-') as tmp:
    base=Path(tmp);root=m.fixture(base);package=m.build(root,'v1');homes={n:base/n for n in ('a','b')}
    for home in homes.values(): I.install_release(package,home)
    with patch.object(I,'verify_release',wraps=I.verify_release) as v:
        ctx=I.ReleaseValidationContext()
        reports={n:D._host_status(h,current_release_id='v1',source_skills=['my-alpha','my-beta'],validation_context=ctx) for n,h in homes.items()}
        count=v.call_count
    assert count==1 and all(r['status']=='valid' for r in reports.values())
    (homes['b']/'my-matt-workflow/runtime/v1/tools/workflow.py').write_text('tampered')
    ctx=I.ReleaseValidationContext()
    reports={n:D._host_status(h,current_release_id='v1',source_skills=['my-alpha','my-beta'],validation_context=ctx) for n,h in homes.items()}
    assert reports['a']['status']=='valid' and reports['b']['status']=='invalid'
    with patch.object(R,'source_manifest',wraps=R.source_manifest) as stage:
        assert R.release_matches_source(package,root/'skills',upstream_id='local');digest_count=stage.call_count
    mp=package/'manifest.json';manifest=json.loads(mp.read_bytes());manifest.pop('source_input_digest');mp.write_text(json.dumps(manifest))
    with patch.object(R,'source_manifest',wraps=R.source_manifest) as stage:
        assert R.release_matches_source(package,root/'skills',upstream_id='local');fallback_count=stage.call_count
    assert digest_count==0 and fallback_count==1
    m.emit('shared-doctor-and-digest-counts',shared_verify=count,hosts={n:r['status'] for n,r in reports.items()},digest_source_manifest=digest_count,legacy_source_manifest=fallback_count)

with tempfile.TemporaryDirectory(prefix='review02-parent-detail-') as tmp:
    base=Path(tmp);root=m.fixture(base);package=m.build(root,'v1');home=base/'home';external=base/'outside'
    external.mkdir();(home/'my-matt-workflow').mkdir(parents=True)
    (home/'my-matt-workflow/runtime').symlink_to(external,target_is_directory=True)
    first=I.install_release(package,home)
    state=json.loads((home/'my-matt-workflow/install-state.json').read_bytes())
    assert (external/'v1/tools/workflow.py').is_file()
    status=D._host_status(home,current_release_id='v1',source_skills=['my-alpha','my-beta'],validation_context=I.ReleaseValidationContext())
    again=m.attempt(lambda:I.install_release(package,home))
    m.emit('runtime-parent-link-detail',first_result=first,outside_written=True,entry=str(Path(state['runtime_entry']).relative_to(base.resolve())),doctor=status['status'],doctor_reason=status.get('reason'),second=again)
m.emit('extra-complete',probes=len(m.RESULTS),elapsed_seconds=round(time.monotonic()-start,3))
