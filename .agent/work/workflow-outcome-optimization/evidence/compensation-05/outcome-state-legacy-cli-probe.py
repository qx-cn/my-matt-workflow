import sys,json,types,unittest
from pathlib import Path
sys.path[:0]=['/Users/sherly/CS/wsp/ai/my-matt-workflow','/Users/sherly/CS/wsp/ai/my-matt-workflow/tests']
import test_topic_lifecycle as seam
import test_holistic_state_repairs as tests
BASE=Path('/tmp/outcome-holistic-base-7947cb2/tools/workflow.py')
FINAL=Path('/Users/sherly/CS/wsp/ai/my-matt-workflow/tools/workflow.py')
def legacy(self,views):
    seam.CLI=BASE
    try:
        full="python3 -c \"from pathlib import Path; raise SystemExit(0 if Path('code.txt').read_text() == 'fixed output\\n' else 1)\"" if 'correctness' in views else "python3 -c 'pass'"
        self.setup(full=full);self.cli('implement','start','--ticket','feature-01')
        (self.repo/'code.txt').write_text('wrong output\n')
        self.cli('implement','test');self.self_review()
        findings=self.repo/'.agent/findings.json'
        findings.write_text(json.dumps([dict(id=f'old-{i}',severity='blocking',view=view,summary='legacy discovery',location='code.txt:1',basis='caller requires fixed output') for i,view in enumerate(views)]))
        self.cli('implement','self-review','--notes-file',str(self.repo/'.agent/self.md'),'--findings-file',str(findings))
        ticket=self.repo/'.agent/work/feature/tickets/tickets-feature-01.md'
        ticket.write_text(ticket.read_text().replace('- [ ]','- [x]'))
        self.cli('implement','finish')
        path=self.repo/'.agent/work/feature/implementations/feature-01.json'
        return path,path.read_bytes()
    finally:seam.CLI=FINAL
suite=unittest.TestSuite()
for name in unittest.defaultTestLoader.getTestCaseNames(tests.HolisticStateRepairs):
    t=tests.HolisticStateRepairs(name);t.legacy=types.MethodType(legacy,t);suite.addTest(t)
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
