#!/usr/bin/env python3
"""Reproduce selected runtime paths from the hash-checked retained audit sources.

No source writes, external services, full test suite, or LLM review execution.
The review 'pass' is an explicit deterministic test fixture, so this proves
runtime acceptance behavior only, not reviewer effectiveness or independence.
"""
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import types

sys.dont_write_bytecode = True
import zipfile
artifact_root = Path(__file__).resolve().parent
manifest = json.loads((artifact_root / 'source-manifest.json').read_text())
source_root = Path(manifest['source_root'])
derived = tempfile.TemporaryDirectory(prefix='my-matt-quality-derived-', dir='/tmp')
derived_root = Path(derived.name)
artifacts = []
with zipfile.ZipFile(artifact_root / 'retained-source.zip') as archive:
    for entry in manifest['artifacts']:
        if 'archive_path' not in entry:
            continue
        relative = Path(entry['archive_path'])
        target = derived_root / relative
        target.resolve().relative_to(derived_root.resolve())
        data = archive.read(entry['archive_path'])
        if hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise RuntimeError('retained source hash mismatch: ' + str(relative))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        artifacts.append(dict(entry, snapshot_path=str(target)))
snapshot = {'content_id': manifest['content_id']}
sys.path[:0] = [str(derived_root), str(derived_root / 'tests')]
from test_batches import BatchTests
from tools.workflow_lib import batches

output = {
    'content_id': snapshot['content_id'],
    'kind': 'exact snapshot derived public CLI probes; deterministic fixture review',
    'limits': 'No LLM execution, no independent review, no whole-suite test result',
}
case = BatchTests()
case.setUp()
try:
    case.setup(full='python3 full.py')
    (case.repo / 'full.py').write_text('import quality_probe_missing_dependency\n')
    case.git('add', 'full.py')
    case.git('commit', '-qm', 'baseline unavailable')
    case.cli('implement', 'start', '--ticket', 'feature-01')
    (case.repo / 'full.py').write_text(
        'import unittest\nclass Case(unittest.TestCase):\n'
        ' def test_behavior(self): self.assertEqual(1, 2, "current behavior wrong")\n'
        'if __name__ == "__main__": unittest.main()\n')
    (case.repo / 'code.txt').write_text('ticket 1\n')
    case.cli('implement', 'test')
    case.self_review()
    ticket = case.repo / '.agent/work/feature/tickets/tickets-feature-01.md'
    ticket.write_text(ticket.read_text().replace('- [ ]', '- [x]'))
    case.cli('implement', 'finish')
    # BatchTests.review synthesizes a pass and declares a distinct session ID.
    # This is the runtime's own established test seam, not a real reviewer.
    case.review()
    topic = case.repo / '.agent/work/feature'
    output['baseline_recovery'] = {
        'baseline': json.loads((topic / 'test-baseline.json').read_text()),
        'current': json.loads((topic / 'batch-tests-01.json').read_text()),
        'closed': json.loads(case.cli('batch', 'close', '--topic', 'feature').stdout),
        'summary': (topic / 'deliveries/deliveries-feature-01.md').read_text(),
    }
finally:
    case.doCleanups()

output['self_findings'] = []
for view in ('correctness', 'spec-challenge'):
    case = BatchTests()
    case.setUp()
    try:
        case.setup()
        case.cli('implement', 'start', '--ticket', 'feature-01')
        (case.repo / 'code.txt').write_text('ticket 1\n')
        case.cli('implement', 'test')
        notes = case.repo / '.agent/self.md'
        notes.write_text('\n'.join(f'## {h}\n已做检查。' for h in batches.SELF_SECTIONS))
        findings = case.repo / '.agent/findings.json'
        findings.write_text(json.dumps([dict(
            id='S1', view=view, severity='blocking', location='code.txt:1',
            basis='已观测到当前实现错误，需要修复或用户裁决', summary='明确未处理问题',
        )], ensure_ascii=False))
        case.cli('implement', 'self-review', '--notes-file', str(notes),
                 '--findings-file', str(findings))
        before = json.loads(case.cli('implement', 'status', '--ticket', 'feature-01').stdout)
        ticket = case.repo / '.agent/work/feature/tickets/tickets-feature-01.md'
        ticket.write_text(ticket.read_text().replace('- [ ]', '- [x]'))
        finished = json.loads(case.cli('implement', 'finish').stdout)
        output['self_findings'].append(dict(view=view, status_before=before, finished=finished))
    finally:
        case.doCleanups()

source = next(a for a in artifacts if a['source_path'].endswith('/review_loop.py'))
tree = ast.parse(Path(source['snapshot_path']).read_text())
environment = {'re': re, 'volume': lambda manifest: manifest.get('probe_volume', 1)}
functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)
             and n.name in ('overlap', 'inside', 'signals')]
exec(compile(ast.Module(body=functions, type_ignores=[]), source['snapshot_path'], 'exec'), environment)
repair = dict(path='code.py', old=[0, 1], new=[0, 1])
unit = dict(first_review_volume=1, reviews=[
    dict(status='findings'),
    dict(status='findings', repair=[repair], result=dict(findings=[])),
    dict(status=None),
])
passed = dict(status='pass', findings=[])
output['review_stop_signals'] = {
    'pass_with_overlap': environment['signals'](unit, dict(round=3, probe_volume=1), passed, [repair]),
    'pass_with_volume_growth': environment['signals'](
        dict(first_review_volume=1, reviews=[dict(status=None)]),
        dict(round=1, probe_volume=2), passed, []),
}
target = Path('/tmp/my-matt-quality-runtime-reproduced.json')
target.write_text(json.dumps(output, ensure_ascii=False, indent=2))
print(json.dumps({
    'receipt': str(target),
    'baseline_current_exit_codes': [r['exit_code'] for r in output['baseline_recovery']['current']['results']],
    'baseline_new_failures': output['baseline_recovery']['current']['new_failures'],
    'baseline_closed': output['baseline_recovery']['closed']['state'],
    'self_findings_finish_states': [r['finished']['status'] for r in output['self_findings']],
    'review_stop_signals': output['review_stop_signals'],
}, ensure_ascii=False, indent=2))
derived.cleanup()
