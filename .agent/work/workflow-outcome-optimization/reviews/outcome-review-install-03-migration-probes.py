import ast
import json
import tempfile
from pathlib import Path

# Reuse only this reviewer's fixture helpers; do not rerun the completed matrix.
p=Path('/tmp/outcome-review-install-03-probes.py')
module=ast.parse(p.read_text(),filename=str(p))
cut=next(i for i,n in enumerate(module.body) if isinstance(n,ast.For))
exec(compile(ast.Module(body=module.body[:cut],type_ignores=[]),str(p),'exec'))

for target in TARGETS:
    for receipt in [1,2]:
        for old_layout in ['default-skills','custom-internal']:
            with tempfile.TemporaryDirectory(prefix='independent-install03-recorded-') as tmp:
                b=Path(tmp).resolve(); r=package(b,'v1'); h=b/'host'
                old=h/('skills' if old_layout=='default-skills' else 'legacy-skills')
                installer.install_release(r,h,target=target,skills_home=old)
                state_path=h/'my-matt-workflow/install-state.json'
                if receipt==1:
                    state=json.loads(state_path.read_text())
                    for k in ['version','manifest_sha256','managed_inventory']:state.pop(k)
                    state_path.write_text(json.dumps(state))
                original=json.loads(state_path.read_text())
                assert original['skills_home']==str(old)
                ext=b/'outside'; old.rename(ext); old.symlink_to(ext)
                (ext/'unmanaged-sentinel').write_bytes(b'external sentinel')
                before=tree(ext); host_before=tree(h)
                new=h/('new-skills' if old_layout=='default-skills' else 'skills')
                kwargs={'target':target}
                if old_layout=='default-skills':kwargs['skills_home']=new
                try: result=installer.install_release(r,h,**kwargs)
                except installer.InstallError as e:result='rejected: '+str(e)
                after=json.loads(state_path.read_text())
                row={'target':target or 'portable','receipt':receipt,'old_layout':old_layout,'old_recorded':original['skills_home'],'new_selected':str(new),'result':result,'outside_unchanged':tree(ext)==before,'host_unchanged':tree(h)==host_before,'outside_managed_removed':not (ext/'my-alpha').exists() and not (ext/'my-removed').exists(),'outside_sentinel_unchanged':(ext/'unmanaged-sentinel').read_bytes()==b'external sentinel','receipt_new_home':after['skills_home']}
                emit('internal-recorded-root-migration-drift',**row)
                assert result=='installed' and not row['outside_unchanged'] and row['outside_managed_removed'] and row['outside_sentinel_unchanged']

# Canonical, unchanged old roots remain legal, including a selected external alias.
for alias_old in [False,True]:
    with tempfile.TemporaryDirectory(prefix='independent-install03-recorded-valid-') as tmp:
        b=Path(tmp).resolve(); r=package(b,'v1'); h=b/'host'; old=b/'old-canonical'
        old.mkdir(); selected=old
        if alias_old:
            selected=b/'explicit-old-alias'; selected.symlink_to(old)
        installer.install_release(r,h,skills_home=selected)
        state=installer.load_install_state(h/'my-matt-workflow/install-state.json')
        assert state['skills_home']==str(old)
        assert installer.install_release(r,h)=='installed'
        assert not (old/'my-alpha').exists()
        assert installer.install_release(r,h)=='current'
        installer.recover_interrupted_install(h)
        emit('legitimate-recorded-canonical-migration',selected_old_alias=alias_old,installed=True,current=True,recover=True)

Path('/tmp/outcome-review-install-03-migration-summary.json').write_text(json.dumps({'observations':len(RESULTS),'results':RESULTS},ensure_ascii=False,indent=2)+'\n')
