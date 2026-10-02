import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

SOURCE = Path('/tmp/outcome-review-install-03')
sys.path.insert(0, str(SOURCE))
from tools.workflow_lib import installer, projection, doctor
assert all(Path(m.__file__).is_relative_to(SOURCE) for m in (installer, projection, doctor))

RESULTS = []
def emit(name, **data):
    row = {'probe': name, **data}
    RESULTS.append(row)
    print(json.dumps(row, ensure_ascii=False), flush=True)

def tree(root):
    result = {}
    if not root.exists() and not root.is_symlink():
        return {'[root]': 'absent'}
    def visit(path, rel):
        s = path.lstat()
        if stat.S_ISLNK(s.st_mode):
            result[rel] = ['symlink', os.readlink(path)]
        elif stat.S_ISDIR(s.st_mode):
            result[rel] = ['dir', stat.S_IMODE(s.st_mode)]
            for child in sorted(path.iterdir()):
                visit(child, f'{rel}/{child.name}')
        elif stat.S_ISREG(s.st_mode):
            result[rel] = ['file', stat.S_IMODE(s.st_mode), hashlib.sha256(path.read_bytes()).hexdigest()]
        else:
            result[rel] = ['special', s.st_mode]
    visit(root, '.')
    return result

def package(root, version, legacy=False):
    r = root / 'releases' / version
    names = ['my-alpha', 'my-removed'] if version == 'v1' else ['my-alpha', 'my-added']
    for name in names:
        d = r / 'skills' / name
        (d / 'agents').mkdir(parents=True)
        (d / 'SKILL.md').write_text(f'---\nname: {name}\ndescription: fixture\ndisable-model-invocation: true\n---\n# {name}\n{version}\n')
        (d / 'agents/openai.yaml').write_text('policy:\n  allow_implicit_invocation: false\n')
    runtime = r / 'runtime/tools'
    runtime.mkdir(parents=True)
    (runtime / 'workflow.py').write_text(f'# inert fixture runtime {version}\n')
    skills = projection.skills_inventory(r / 'skills')
    runtime_inv = projection.directory_inventory(r / 'runtime')
    m = {'release_id': version, 'upstream_id': 'independent-fixture', 'skills': skills, 'runtime': runtime_inv}
    if not legacy:
        m['target_manifests'] = {t: {'skills': projection.projected_skills_inventory(r / 'skills', t), 'runtime': runtime_inv} for t in projection.TARGETS}
    (r / 'manifest.json').write_text(json.dumps(m))
    installer.verify_release(r)
    return r

def refused(call):
    try:
        call()
    except installer.InstallError as e:
        return str(e)
    raise AssertionError('expected InstallError')

TARGETS = [None, 'codex', 'cursor', 'claude']
DIRS = ['my-matt-workflow', 'my-matt-workflow/runtime', 'my-matt-workflow/transaction', 'my-matt-workflow/runtime/v1', 'skills', 'nested/skills']
FILES = ['my-matt-workflow/install-state.json', 'my-matt-workflow/.install.lock', 'my-matt-workflow/.my-matt-ownership.json']
for target in TARGETS:
    for rel in DIRS + FILES:
        for kind in ['outside', 'dangling', 'internal']:
            with tempfile.TemporaryDirectory(prefix='independent-install03-link-') as tmp:
                b = Path(tmp).resolve(); r = package(b, 'v1'); h = b / 'host'; h.mkdir()
                ext = b / 'external'; ext.mkdir(); (ext / 'sentinel').write_bytes(b'external pre-existing bytes')
                destination = (ext / 'target') if kind != 'internal' else h / 'safe-looking-target'
                if kind != 'dangling':
                    if rel in FILES: destination.write_bytes(b'pre-existing file')
                    else: destination.mkdir(); (destination / 'untouched').write_bytes(b'pre-existing dir')
                link = h / rel; link.parent.mkdir(parents=True, exist_ok=True); link.symlink_to(destination)
                before = tree(b)
                kwargs = {'target': target}
                if rel == 'nested/skills': kwargs['skills_home'] = link
                error = refused(lambda: installer.install_release(r, h, **kwargs))
                assert tree(b) == before, (target, rel, kind, 'install mutated fixture')
                recover_reject = rel not in ['my-matt-workflow/runtime/v1', 'skills', 'nested/skills']
                if recover_reject:
                    refused(lambda: installer.recover_interrupted_install(h))
                    assert tree(b) == before, (target, rel, kind, 'recover mutated fixture')
                emit('initial-link-refusal', target=target or 'portable', path=rel, kind=kind, error=error, fixture_unchanged=True, recover_rejected=recover_reject)

# An existing interrupted transaction is also protected before recovery reads it.
for rel in ['my-matt-workflow', 'my-matt-workflow/runtime', 'my-matt-workflow/transaction', *FILES]:
    with tempfile.TemporaryDirectory(prefix='independent-install03-recover-') as tmp:
        b=Path(tmp).resolve(); r=package(b,'v1'); h=b/'host'; installer.install_release(r,h)
        new=package(b,'v2'); rename=Path.rename
        def stop(path, dest):
            result=rename(path,dest)
            if path.parent.name=='staged' and path.name=='my-alpha': raise KeyboardInterrupt('probe after actual new move')
            return result
        with patch.object(Path,'rename',stop):
            try: installer.install_release(new,h)
            except KeyboardInterrupt: pass
            else: raise AssertionError('no interruption')
        p=h/rel; ext=b/'external'; ext.mkdir(); (ext/'sentinel').write_bytes(b'external')
        moved=ext/'original'
        if p.exists(): p.rename(moved)
        else: moved.mkdir()
        p.symlink_to(moved)
        before=tree(b); err=refused(lambda: installer.recover_interrupted_install(h))
        assert tree(b)==before, (rel, 'recover mutated')
        emit('interrupted-internal-link-refusal',path=rel,error=err,fixture_unchanged=True)

# Explicit root aliases remain trusted; internal Skill roots can use either spelling.
for target in TARGETS:
    for spelling in ['default', 'selected', 'canonical', 'parent-alias']:
        with tempfile.TemporaryDirectory(prefix='independent-install03-alias-') as tmp:
            b=Path(tmp).resolve(); r=package(b,'v1'); actual=b/'actual'; actual.mkdir()
            alias=b/'selected'; alias.symlink_to(actual)
            selected=alias
            if spelling=='parent-alias':
                actual=actual/'child'; selected=alias/'child'
            kwargs={'target':target}
            if spelling=='selected': kwargs['skills_home']=selected/'skills'
            if spelling=='canonical': kwargs['skills_home']=actual/'skills'
            assert installer.install_release(r,selected,**kwargs)=='installed'
            state_path=actual/'my-matt-workflow/install-state.json'; state=installer.load_install_state(state_path)
            assert state['runtime_entry']==str(actual/'my-matt-workflow/runtime/v1/tools/workflow.py')
            assert state['skills_home']==str(actual/'skills')
            installer.verify_installed_state(state,state_home=selected)
            assert doctor._host_status(selected,current_release_id='v1',source_skills=['my-alpha','my-removed'],validation_context=installer.ReleaseValidationContext())['status']=='valid'
            installer.recover_interrupted_install(selected)
            before=tree(actual)
            assert installer.install_release(r,selected,**kwargs)=='current'
            assert tree(actual)==before
            emit('explicit-root-alias',target=target or 'portable',spelling=spelling,installed=True,current=True,recover=True,doctor='valid')

def interrupt_install(r,h,kwargs,seam):
    rename=Path.rename; replace=Path.replace
    def moved(path,dest):
        result=rename(path,dest)
        should=(seam=='new-move' and path.parent.name=='staged' and path.name=='my-alpha') or (seam=='legacy-move' and Path(dest).parent.name=='legacy-backup') or (seam=='runtime-move' and path.name=='staged-runtime')
        if should: raise KeyboardInterrupt(seam)
        return result
    def replaced(path,dest):
        result=replace(path,dest)
        if seam=='committed' and path.name=='install-state.json': raise KeyboardInterrupt(seam)
        return result
    with patch.object(Path,'rename',moved),patch.object(Path,'replace',replaced):
        try: installer.install_release(r,h,**kwargs)
        except KeyboardInterrupt: return
        raise AssertionError('missing interruption '+seam)

for target in TARGETS:
    for migration in [False,True]:
        for seam in (['new-move','legacy-move','runtime-move','committed'] if migration else ['new-move','runtime-move','committed']):
            with tempfile.TemporaryDirectory(prefix='independent-install03-legit-') as tmp:
                b=Path(tmp).resolve(); r=package(b,'v1'); new=package(b,'v2'); actual=b/'actual'; actual.mkdir(); alias=b/'selected'; alias.symlink_to(actual)
                old=b/'recorded-skills' if migration else actual/'skills'; old_kwargs={'target':target,'skills_home':old}
                installer.install_release(r,alias,**old_kwargs)
                # Model a valid legacy v1 receipt and migration from its recorded canonical home.
                state_path=actual/'my-matt-workflow/install-state.json'
                if migration:
                    s=json.loads(state_path.read_text())
                    for field in ['version','manifest_sha256','managed_inventory']: s.pop(field)
                    state_path.write_text(json.dumps(s))
                old_state=state_path.read_bytes(); old_tree=tree(old)
                kwargs={'target':target,'skills_home':alias/'skills'}
                interrupt_install(new,alias,kwargs,seam)
                installer.recover_interrupted_install(alias)
                assert not (actual/'my-matt-workflow/transaction').exists()
                if seam=='committed':
                    s=installer.load_install_state(state_path); assert s['release_id']=='v2'; installer.verify_installed_state(s,state_home=alias)
                    if migration: assert not (old/'my-alpha').exists() and not (old/'my-removed').exists()
                    assert installer.install_release(new,alias,**kwargs)=='current'
                else:
                    assert state_path.read_bytes()==old_state; assert tree(old)==old_tree
                    if migration: assert not (actual/'skills/my-alpha').exists() and not (actual/'skills/my-added').exists()
                    assert installer.install_release(new,alias,**kwargs)=='installed'
                    assert installer.install_release(new,alias,**kwargs)=='current'
                emit('alias-upgrade-recover',target=target or 'portable',migration=migration,seam=seam,recovered=True,subsequent_current=True)

# Recovery must preserve recorded materials after a recorded root changes into a link.
for drift in ['new-skills','old-recorded']:
    with tempfile.TemporaryDirectory(prefix='independent-install03-drift-') as tmp:
        b=Path(tmp).resolve(); r=package(b,'v1'); new=package(b,'v2'); h=b/'host'; old=b/'old-skills'
        installer.install_release(r,h,skills_home=old)
        interrupt_install(new,h,{'skills_home':h/'skills'},'new-move')
        root=h/'skills' if drift=='new-skills' else old
        ext=b/'external'; root.rename(ext); root.symlink_to(ext)
        before=tree(b); err=refused(lambda:installer.recover_interrupted_install(h)); assert tree(b)==before
        emit('recorded-root-recovery-drift',root=drift,error=err,fixture_unchanged=True)

# Probe older recorded root drift on a fresh migration (observational; do not presume a pass).
with tempfile.TemporaryDirectory(prefix='independent-install03-migration-drift-') as tmp:
    b=Path(tmp).resolve(); r=package(b,'v1'); h=b/'host'; old=b/'old-recorded-skills'
    installer.install_release(r,h,skills_home=old)
    ext=b/'external'; old.rename(ext); old.symlink_to(ext)
    before=tree(ext)
    try: result=installer.install_release(r,h,skills_home=h/'skills')
    except installer.InstallError as e: result='rejected: '+str(e)
    emit('fresh-migration-recorded-root-drift',result=result,external_unchanged=tree(ext)==before,external_old_skill_present=(ext/'my-alpha').exists())

Path('/tmp/outcome-review-install-03-probes-summary.json').write_text(json.dumps({'source':str(SOURCE),'observations':len(RESULTS),'results':RESULTS},ensure_ascii=False,indent=2)+'\n')
