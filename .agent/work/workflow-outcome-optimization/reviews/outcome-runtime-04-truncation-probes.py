import os,sys,json,pathlib,subprocess,tempfile,hashlib
ROOT=pathlib.Path('/tmp/outcome-review-runtime-04')
CLI=ROOT/'tools/workflow.py'
E=pathlib.Path('/tmp/outcome-runtime-04-truncation-evidence');E.mkdir(exist_ok=True)
ENV=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
events=[];results={}
def save():
    (E/'cli-events.json').write_text(json.dumps(events,indent=2,ensure_ascii=False))
    (E/'results.json').write_text(json.dumps(results,indent=2,ensure_ascii=False))
def run(argv,cwd):
    p=subprocess.run(argv,cwd=cwd,env=ENV,text=True,capture_output=True)
    events.append(dict(argv=argv,cwd=str(cwd),exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr));save()
    return p
class Fixture:
    def __init__(self,label,files,full):
        self.repo=pathlib.Path(tempfile.mkdtemp(prefix='outcome-runtime04-'+label+'-',dir='/tmp'))
        self.label=label;self.full=full;self.root=self.repo/'.agent/work/feature'
        self.git('init','-q','--initial-branch=main');self.git('config','user.name','Review Fixture');self.git('config','user.email','review@example.invalid')
        self.write(dict(files,**{'code.txt':'initial\n'}));self.commit('initial runner')
        self.cli('setup','--apply','--agent-directory-mode','shared','--test-command',full,'--test-command',"python3 -B -c 'pass'")
        spec=self.root/'specs/specs-feature-01.md';spec.parent.mkdir(parents=True,exist_ok=True)
        spec.write_text('---\nspec_id: feature\nrevision: 1\n---\n# Spec\n## 验收标准\n- AC-01: marker observed\n')
        self.ticket=self.root/'tickets/tickets-feature-01.md';self.ticket.parent.mkdir(parents=True,exist_ok=True)
        fields=dict(id='feature-01',title='Toy marker',ticket_kind='implementation',spec_id='feature',spec_revision=1,spec_ref=str(spec.relative_to(self.repo)),status='ready-for-agent',blocked_by=[],sequence=1,test_commands=["python3 -B -c 'pass'"],rule_sources=[str(spec.relative_to(self.repo))],rule_scope=['code.txt'],rule_constraints=['observe marker'],rule_conflicts=[],review_probes=['recovery'],execution_agent='auto',claimed_by='',supersedes_ticket=[],compensates=[],tags=[])
        self.ticket.write_text('---\n'+'\n'.join(k+': '+json.dumps(v) for k,v in fields.items())+'\n---\n\n## 要构建什么\nChange toy marker\n## 适用规则与影响区域\ncode.txt\n## 验收标准\n- [ ] marker observed\n')
        self.cli('implement','start','--ticket','feature-01','--agent','codex')
        self.baseline=json.loads((self.root/'test-baseline.json').read_text())
        (self.repo/'code.txt').write_text('implemented marker\n')
        self.cli('implement','test')
        notes=self.repo/'.agent/self-notes.md';notes.write_text('\n'.join('## '+h+'\n无：自建玩具 fixture，仅用于到达被测门禁。\n' for h in ('验收对照','现状核实','影响面','对抗检查','简洁与约定','已知缺口')))
        self.cli('implement','self-review','--notes-file',str(notes))
        self.ticket.write_text(self.ticket.read_text().replace('- [ ]','- [x]'))
        self.cli('implement','finish')
        results[label]=dict(repo=str(self.repo),baseline=self.baseline);save()
    def cli(self,*args,ok=True):
        p=run(['python3','-B',str(CLI),*args,'--repo',str(self.repo)],self.repo)
        if ok:assert p.returncode==0,(self.label,args,p.stderr)
        else:assert p.returncode!=0,(self.label,args,p.stdout)
        return p
    def git(self,*args):
        p=run(['git',*args],self.repo);assert p.returncode==0,p.stderr;return p.stdout.strip()
    def write(self,files):
        for n,s in files.items():
            p=self.repo/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
    def commit(self,message):self.git('add','--all');self.git('commit','-qm',message)
    def change(self,files):self.write(files);self.commit('probe current change')
    def test(self,key):
        r=json.loads(self.cli('batch','test','--topic','feature').stdout);results[self.label][key]=r;save();return r
    def review(self):
        p=json.loads(self.cli('batch','review','--topic','feature','--reviewer-model','fixture','--reviewer-session-id','synthetic-to-reach-gate').stdout)
        manifest=json.loads(pathlib.Path(p['manifest']).read_text());rp=pathlib.Path(p['result_file']);r=json.loads(rp.read_text())
        r.update(status='pass',reviewer=dict(provenance='independent',model='fixture'),coverage=[dict(target=t,result='ok') for t in manifest['coverage_targets']],findings=[])
        rp.write_text(json.dumps(r));self.cli('batch','review','--topic','feature','--submit',str(rp))
        results[self.label].setdefault('synthetic_reviews',[]).append(p);save()
    def blocked(self,key='close'):
        p=self.cli('batch','close','--topic','feature',ok=False)
        assert '全量测试新增失败或记录过期' in p.stderr,p.stderr
        results[self.label][key]=dict(exit_code=p.returncode,stderr=p.stderr);save()
    def status(self,key):
        s=json.loads(self.cli('batch','status','--topic','feature').stdout);results[self.label][key]=s;save();return s
missing='import review04_intentionally_missing_dependency\n'
assertion="assert False, 'review04 real top-level assertion'\n"
passing='import unittest\nclass Behavior(unittest.TestCase):\n    def test_ok(self): self.assertTrue(True)\n'

for verbose in ('',' -v'):
    mode='verbose' if verbose else 'default'
    full='python3 -B -m unittest discover -s suite'+verbose
    files={f'suite/test_{i:02d}.py':missing for i in range(12)}
    f=Fixture('truncated-legacy-'+mode,files,full)
    b=f.baseline['results'][0]
    assert b['unavailable'] is True and b['comparison_eligible'] is False and len(b['failures'])==12,b
    tail=b['output_tail'];visible=tail.count('ERROR: ')
    assert len(tail)==4000 and visible<12,(len(tail),visible)
    results[f.label]['truncation_facts']=dict(tail_size=len(tail),visible_error_headers=visible,full_failure_count=len(b['failures']))
    pure=f.test('pure');assert pure['results'][0]['unavailable'] and not pure['new_failures'] and pure['unverified'],pure
    f.review()
    f.change({'suite/test_00.py':assertion})
    current=f.test('current_with_new_schema')
    assert not current['results'][0]['unavailable'] and current['new_failures'] and current['results'][0]['failures']==b['failures'],current
    f.blocked('new_schema_close')
    bp=f.root/'test-baseline.json';base=json.loads(bp.read_text());base['results'][0].pop('comparison_eligible');base['results'][0]['unavailable']=False;bp.write_text(json.dumps(base))
    # Preserve all original failure identities, content bindings, and raw output tails.
    results[f.label]['legacy_baseline_injected']=base
    cp=f.root/'batch-tests-01.json';old=json.loads(cp.read_text());old['results'][0].pop('comparison_eligible');old.update(new_failures=[],known_failures=[dict(command=full,failure=x) for x in b['failures']],unverified=[]);cp.write_text(json.dumps(old))
    results[f.label]['legacy_receipt_injected']=old;save()
    after=f.test('legacy_actual_rerun')
    results[f.label]['current_source_bytes']=(f.repo/'suite/test_00.py').read_text()
    direct=f.cli('batch','close','--topic','feature',ok=False)
    results[f.label]['legacy_direct_close']=dict(exit_code=direct.returncode,stderr=direct.stderr)
    if not after['new_failures']:
        f.review()
        closed=f.cli('batch','close','--topic','feature')
        results[f.label]['legacy_refreshed_review_close']=dict(exit_code=closed.returncode,stdout=closed.stdout)
        results[f.label]['delivery']=(f.root/'deliveries/deliveries-feature-01.md').read_text()
        results[f.label]['reproduced_bypass']=True
    else:
        f.blocked('legacy_close');results[f.label]['reproduced_bypass']=False
    save();print(f.label+' bypass='+str(results[f.label]['reproduced_bypass']),flush=True)
print('TRUNCATION PROBES FINISHED',flush=True)
