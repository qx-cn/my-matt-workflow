import copy
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import traceback

SOURCE = Path('/tmp/outcome-review-final-06')
CLI = SOURCE / 'tools/workflow.py'
OUT = Path('/tmp/outcome-runtime-05-evidence')
OUT.mkdir(exist_ok=True)
EVENTS = []
RESULTS = []
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
FIELDS = ('comparison_eligible', 'execution_observed', 'output_complete', 'output_length', 'unavailable_loader_failures')

def persist():
    (OUT/'cli-events.json').write_text(json.dumps(EVENTS, ensure_ascii=False, indent=2))
    (OUT/'results.json').write_text(json.dumps(RESULTS, ensure_ascii=False, indent=2))

class Fixture:
    def __init__(self, name, files, command):
        self.name = name
        self.repo = OUT/name
        self.repo.mkdir()
        self.command = command
        self.git('init', '-q', '--initial-branch=main')
        self.git('config', 'user.name', 'Independent CLI Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.write('code.txt', 'initial fixture marker\n')
        for name, content in files.items(): self.write(name, content)
        self.git('add', '.')
        self.git('commit', '-qm', 'Independent baseline')
        self.cli('setup', '--apply', '--agent-directory-mode', 'shared', '--test-command', command,
                 '--test-command', "python3 -B -c 'pass'")
        self.root = self.repo/'.agent/work/feature'
        spec = self.root/'specs/specs-feature-01.md'
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text('---\nspec_id: feature\nrevision: 1\n---\n# Fixture Spec\n## 验收标准\n- AC-01: independent marker is written\n')
        self.ticket = self.root/'tickets/tickets-feature-01.md'
        self.ticket.parent.mkdir()
        meta = dict(id='feature-01', title='Independent marker', ticket_kind='implementation',
                    spec_id='feature', spec_revision=1, spec_ref=str(spec.relative_to(self.repo)),
                    status='ready-for-agent', blocked_by=[], sequence=1,
                    test_commands=["python3 -B -c 'pass'"], rule_sources=[str(spec.relative_to(self.repo))],
                    rule_scope=['code.txt'], rule_constraints=['write the marker'], rule_conflicts=[],
                    review_probes=['recovery'], execution_agent='auto', claimed_by='',
                    supersedes_ticket=[], compensates=[], tags=[])
        self.ticket.write_text('---\n'+'\n'.join(k+': '+json.dumps(v) for k,v in meta.items())+
                               '\n---\n## 要构建什么\nWrite marker\n## 适用规则与影响区域\ncode.txt\n## 验收标准\n- [ ] independent marker is written\n')
        self.cli('implement', 'start', '--ticket', 'feature-01', '--agent', 'codex')
        self.baseline = self.load('test-baseline.json')
        self.write('code.txt', 'independent marker is written\n')
        self.cli('implement', 'test')
        notes = self.repo/'.agent/fixture-self.md'
        notes.write_text(''.join('## '+h+'\nFixture marker verified; runner semantics are the probe under test.\n' for h in
                                ('验收对照','现状核实','影响面','对抗检查','简洁与约定','已知缺口')))
        self.cli('implement','self-review','--notes-file',str(notes), '--no-findings')
        self.ticket.write_text(self.ticket.read_text().replace('- [ ]','- [x]'))
        self.cli('implement','finish')

    def write(self, path, content):
        target = self.repo/path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    def git(self, *args):
        p = subprocess.run(['git', *args], cwd=self.repo, env=ENV, capture_output=True, text=True)
        if p.returncode: raise AssertionError(p.stderr)
        return p.stdout.strip()

    def commit(self, message):
        self.git('add','--all','--','.',':(top,exclude).agent')
        self.git('commit','-qm',message)

    def cli(self, *args, ok=True, role=None):
        argv = [sys.executable, '-B', str(CLI), *args, '--repo', str(self.repo)]
        p = subprocess.run(argv, cwd=self.repo, env=ENV, capture_output=True, text=True)
        EVENTS.append(dict(fixture=self.name, role=role or 'public-cli', argv=argv,
                           exit_code=p.returncode, stdout=p.stdout, stderr=p.stderr))
        persist()
        if ok is True and p.returncode: raise AssertionError((args,p.stderr))
        if ok is False and not p.returncode: raise AssertionError((args,'unexpected exit 0'))
        return p

    def load(self, name): return json.loads((self.root/name).read_text())
    def save(self, name, data): (self.root/name).write_text(json.dumps(data))
    def test(self): return json.loads(self.cli('batch','test','--topic','feature').stdout)
    def status(self): return json.loads(self.cli('batch','status','--topic','feature').stdout)
    def direct(self):
        p = subprocess.run(shlex.split(self.command), cwd=self.repo, env=ENV, capture_output=True, text=True)
        EVENTS.append(dict(fixture=self.name,role='direct-runner-confirmation',argv=shlex.split(self.command),
                           exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr))
        persist()
        return p

    def review(self, synthetic_test=False):
        # Synthetic accepted review is a test precondition, never reviewer certification.
        # Temporarily provide zero-failure raw receipt so public CLI can freeze a fresh
        # current-HEAD review. Restore the actual runner receipt before testing close.
        original = self.load('batch-tests-01.json')
        if synthetic_test:
            temporary = copy.deepcopy(original)
            for row in temporary['results']:
                row.update(exit_code=0, failures=[], unavailable=False)
            temporary.update(new_failures=[],known_failures=[],unverified=[])
            self.save('batch-tests-01.json', temporary)
        try:
            info = json.loads(self.cli('batch','review','--topic','feature','--reviewer-model',
                                       'synthetic-fixture','--reviewer-session-id','fixture-fresh-'+self.name,
                                       role='synthetic-review-create').stdout)
            manifest = json.loads(Path(info['manifest']).read_text())
            result_path = Path(info['result_file'])
            result = json.loads(result_path.read_text())
            result.update(status='pass', reviewer=dict(provenance='independent',model='synthetic-fixture'),
                          coverage=[dict(target=t,result='ok') for t in manifest['coverage_targets']],findings=[])
            result_path.write_text(json.dumps(result))
            self.cli('batch','review','--topic','feature','--submit',str(result_path),role='synthetic-review-submit')
            assert manifest['head'] == self.git('rev-parse','HEAD')
            assert manifest['content_id'] == original['content_id']
            return dict(head=manifest['head'],content_id=manifest['content_id'],unit_id=manifest['unit_id'],
                        manifest=info['manifest'],synthetic_test_precondition=synthetic_test)
        finally:
            if synthetic_test: self.save('batch-tests-01.json', original)

    def refused(self, fresh=False):
        review = self.review(synthetic_test=True) if fresh else None
        p = self.cli('batch','close','--topic','feature',ok=False)
        assert '新增失败' in p.stderr, p.stderr
        return dict(exit_code=p.returncode,stderr=p.stderr,fresh_fixture_review=review)

def facts(value):
    row = value['results'][0]
    return dict(row=row,new=value.get('new_failures',[]),known=value.get('known_failures',[]),unverified=value.get('unverified',[]))

def legacy(value, unavailable):
    value = copy.deepcopy(value)
    for row in value['results']:
        for key in FIELDS: row.pop(key,None)
        if row['exit_code']: row['unavailable']=unavailable
    return value

def pure(verbose):
    name = 'tail-legacy-'+('verbose' if verbose else 'default')
    files = {'suite/test_%02d.py'%n: 'import independent_review05_missing_tail_dependency\n' for n in range(12)}
    f = Fixture(name,files,'python3 -B -m unittest discover -s suite'+(' -v' if verbose else ''))
    base = f.baseline
    row = base['results'][0]
    assert len(row['failures'])==12 and len(row['output_tail'])==4000
    assert row['output_tail'].count('ERROR:')<12 and row['unavailable'] and not row['execution_observed']
    current = f.test()
    assert current['results'][0]['unavailable'] and not current['new_failures'] and current['unverified']
    pure_status = f.status(); assert ' review ' in pure_status['next_command'] and pure_status['unverified']
    initial_review = f.review()
    f.write('suite/test_00.py', "assert False, 'independent review05 top-level assertion'\n")
    f.commit('Actual top-level regression with same loader identity')
    actual = f.test(); raw = f.direct()
    assert 'AssertionError: independent review05 top-level assertion' in raw.stderr
    assert actual['results'][0]['failures']==row['failures']
    assert not actual['results'][0]['unavailable'] and actual['new_failures']
    cases=[]
    for unavailable in (False,True):
        old = legacy(base,unavailable); f.save('test-baseline.json',old)
        stale = legacy(actual,False)
        stale.update(new_failures=[],known_failures=[dict(command=row['command'],failure=x) for x in row['failures']],unverified=[])
        f.save('batch-tests-01.json',stale)
        status = f.status(); assert ' test ' in status['next_command']
        cache_close = f.refused()
        rerun = f.test()
        assert rerun['new_failures'] and rerun['unverified'] and not rerun['known_failures']
        assert not rerun['results'][0]['unavailable']
        fresh_close = f.refused(fresh=True)
        cases.append(dict(legacy_unavailable=unavailable,legacy_baseline=old,stale_status=status,
                          stale_close=cache_close,rerun=facts(rerun),fresh_close=fresh_close))
    RESULTS.append(dict(probe=name,baseline=base,pure_current=facts(current),pure_status=pure_status,
                        initial_review=initial_review,actual_current=facts(actual),legacy_cases=cases))
    persist(); print(name,'PASS',flush=True)

def partial_passing(verbose):
    name='partial-passing-'+('verbose' if verbose else 'default')
    files={'suite/test_ok.py':'import unittest\nclass Visible(unittest.TestCase):\n def test_ok(self): self.assertEqual(8,8)\n',
           'suite/test_missing.py':'import independent_review05_missing_partial_dependency\n'}
    f=Fixture(name,files,'python3 -B -m unittest discover -s suite'+(' -v' if verbose else ''))
    current=f.test(); row=current['results'][0]
    assert row['execution_observed'] and not row['unavailable'] and len(row['unavailable_loader_failures'])==1
    assert not current['new_failures'] and len(current['known_failures'])==1 and not current['unverified']
    control_review=f.review()
    f.write('suite/test_missing.py',"assert False, 'review05 partial real assertion'\n")
    f.commit('Partial loader module now raises assertion')
    changed=f.test(); raw=f.direct(); assert 'AssertionError: review05 partial real assertion' in raw.stderr
    assert changed['results'][0]['failures']==row['failures'] and not changed['results'][0]['unavailable']
    assert len(changed['new_failures'])==1 and not changed['known_failures'] and changed['unverified']
    refused=f.refused(fresh=True)
    RESULTS.append(dict(probe=name,baseline=f.baseline,control=facts(current),control_review=control_review,
                        changed=facts(changed),fresh_close=refused))
    persist(); print(name,'PASS',flush=True)

def partial_known(verbose):
    name='partial-known-'+('verbose' if verbose else 'default')
    files={'suite/test_%02d.py'%n:'import independent_review05_missing_known_dependency\n' for n in range(12)}
    files['suite/test_behavior.py']='import unittest\nclass Visible(unittest.TestCase):\n def test_known(self): self.assertEqual(1,2)\n def test_new(self): self.assertEqual(4,4)\n'
    f=Fixture(name,files,'python3 -B -m unittest discover -s suite'+(' -v' if verbose else ''))
    controls=[]
    for unavailable in (False,True):
        f.save('test-baseline.json',legacy(f.baseline,unavailable))
        control=f.test()
        assert not control['new_failures'] and not control['unverified'] and len(control['known_failures'])==13
        assert len(control['results'][0]['unavailable_loader_failures'])==12
        controls.append(dict(legacy_unavailable=unavailable,result=facts(control)))
    control_review=f.review()
    f.write('suite/test_behavior.py',files['suite/test_behavior.py'].replace('assertEqual(4,4)','assertEqual(4,5)'))
    f.commit('New executed behavior regression')
    changed=[]
    for unavailable in (False,True):
        f.save('test-baseline.json',legacy(f.baseline,unavailable))
        result=f.test(); assert len(result['new_failures'])==1 and 'test_new' in result['new_failures'][0]['failure']
        assert len(result['known_failures'])==13 and any('test_known' in r['failure'] for r in result['known_failures'])
        assert not result['unverified'] and not result['results'][0]['unavailable']
        changed.append(dict(legacy_unavailable=unavailable,result=facts(result),close=f.refused()))
    f.direct()
    RESULTS.append(dict(probe=name,baseline=f.baseline,controls=controls,control_review=control_review,changed=changed))
    persist(); print(name,'PASS',flush=True)

DUPLICATE_RUNNER='''import pathlib,sys,traceback,unittest
from unittest.loader import _FailedTest
mode=pathlib.Path('mode.txt').read_text().strip()
def make(kind):
 try:
  if kind=='assertion': assert False, 'review05 duplicate assertion'
  if kind=='unknown': raise RuntimeError('review05 duplicate unknown diagnostic')
  import independent_review05_missing_duplicate_dependency
 except Exception:
  return _FailedTest('collision',ImportError('Failed to import test module: collision\\n'+traceback.format_exc()))
class Visible(unittest.TestCase):
 def test_ok(self): self.assertTrue(True)
suite=unittest.TestSuite([make(mode),make('missing'),Visible('test_ok')])
result=unittest.TextTestRunner(verbosity=2 if '-v' in sys.argv else 1).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
'''

def duplicate(verbose):
    name='duplicate-loader-'+('verbose' if verbose else 'default')
    f=Fixture(name,{'runner.py':DUPLICATE_RUNNER,'mode.txt':'missing'},'python3 -B runner.py'+(' -v' if verbose else ''))
    control=f.test(); assert len(control['known_failures'])==1 and not control['new_failures']
    assert len(control['results'][0]['unavailable_loader_failures'])==1
    f.review()
    cases=[]
    for mode in ('assertion','unknown'):
        f.write('mode.txt',mode); f.commit('First duplicate block '+mode+' followed by dependency gap')
        result=f.test();raw=f.direct()
        assert raw.stderr.count('ERROR: collision (unittest.loader._FailedTest.collision)')==2
        assert ('AssertionError: review05 duplicate assertion' if mode=='assertion' else 'RuntimeError: review05 duplicate unknown diagnostic') in raw.stderr
        assert result['results'][0]['failures']==control['results'][0]['failures']
        assert not result['results'][0]['unavailable'] and not result['results'][0]['unavailable_loader_failures']
        assert len(result['new_failures'])==1 and not result['known_failures'] and result['unverified']
        cases.append(dict(mode=mode,result=facts(result),fresh_close=f.refused(fresh=True)))
    RESULTS.append(dict(probe=name,baseline=f.baseline,control=facts(control),cases=cases))
    persist();print(name,'PASS',flush=True)

if __name__=='__main__':
    try:
        for v in (False,True):
            pure(v)
            partial_passing(v)
            partial_known(v)
            duplicate(v)
        print('ALL CORE PROBES PASSED',flush=True)
    except BaseException:
        persist();traceback.print_exc();sys.exit(1)
