"""Shared command observations and frozen-byte integrity, without scope policy."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

# Earlier revisions treated exceptions and loader wrappers as startup proof.
# Neither proves that application initialization did not execute.
DEPENDENCY_PROOF_VERSION=3


def loader_failure_identity(identity):
    """Recognize unittest's legacy and qualified loader wrapper identities."""
    return bool(re.fullmatch(r'[^\n]+ \(unittest\.loader\._FailedTest(?:\.[^()\s]+)?\)',identity))


def execution_observed(output, failure_identities=None):
    cases=re.findall(r'^(?:FAIL|ERROR): (.+)$',output,re.M)
    loader_errors=sum(loader_failure_identity(case) for case in cases)
    if failure_identities is not None:
        loader_errors=max(loader_errors,sum(loader_failure_identity(case) for case in failure_identities))
    # A stored tail may hide loader headers while retaining Ran N. Complete
    # identities and the footer error count bound loaders, never imply execution.
    if failure_identities and all(loader_failure_identity(case) for case in failure_identities):
        errors=re.search(r'^FAILED \(.*?errors=(\d+)',output,re.M)
        if errors:loader_errors=max(loader_errors,int(errors.group(1)))
    if any(not loader_failure_identity(case) for case in cases):return True
    ran=re.search(r'^Ran (\d+) tests?\b',output,re.M)
    if ran and int(ran.group(1))>loader_errors:return True
    return bool(re.search(r'^FAILED\s+[^\s(]\S*|^\s*--- FAIL: |\b[1-9]\d* passed\b',output,re.M))


def loader_only_failure(output):
    cases=re.findall(r'^(?:FAIL|ERROR): (.+)$',output,re.M)
    return bool(cases) and all(loader_failure_identity(case) for case in cases) and not execution_observed(output)


def row_execution_observed(row):
    """Use full-output facts; legacy tails need their complete identity array."""
    observed=row.get('execution_observed')
    if isinstance(observed,bool):return observed
    return execution_observed(row.get('output_tail',''),row.get('failures',[]))


def row_loader_only_failure(row):
    cases=row.get('failures',[])
    return bool(cases) and all(loader_failure_identity(case) for case in cases) and not row_execution_observed(row)


def loader_dependency_fingerprints(stdout,stderr):
    """Bind dependency diagnostics inside a complete unittest report.

    A passing test elsewhere does not make a loader module name a stable behavior
    identity. Compare the full blocks, including every duplicate occurrence;
    a wrapper or exception type alone never proves startup-only execution.
    """
    if stdout.strip():return {}
    diagnostic=stderr.strip()
    progress=re.match(r'[.EFsxu]+\n',diagnostic)
    verbose=not progress
    if verbose:
        progress=re.match(r'(?:[^\n]+ \.\.\. (?:ok|ERROR|FAIL|expected failure|unexpected success|skipped [^\n]+)\n)+\n',diagnostic)
    footer=re.search(r'\n-{10,}\nRan (\d+) tests? in [\d.]+s\n\nFAILED \(([^\n]+)\)$',diagnostic)
    headers=list(re.finditer(r'^={10,}\n(?:FAIL|ERROR): ([^\n]+)\n-{10,}\n',diagnostic,re.M))
    if not progress or not footer or not headers or headers[0].start()!=progress.end():return {}
    counts=dict(re.findall(r'(failures|errors)=(\d+)',footer[2]))
    if sum(int(n) for n in counts.values())!=len(headers):return {}
    if verbose:
        lines=progress[0].strip().splitlines()
        announced=[re.sub(r' \.\.\. (?:ERROR|FAIL)$','',line) for line in lines if line.endswith((' ... ERROR',' ... FAIL'))]
        if len(lines)!=int(footer[1]) or sorted(announced)!=sorted(h[1] for h in headers):return {}
    elif len(progress[0].strip())!=int(footer[1]) or any(progress[0].count(marker)!=int(counts.get(name,0)) for marker,name in (('E','errors'),('F','failures'))):
        return {}
    observations={}
    for index,header in enumerate(headers):
        if not loader_failure_identity(header[1]):continue
        end=headers[index+1].start() if index+1<len(headers) else footer.start()
        block=diagnostic[header.end():end].strip()
        prefix=re.match(r'ImportError: Failed to import test module: [^\n]+\n',block)
        # The same coarse identity may occur more than once. Every block must
        # carry a typed dependency diagnostic; unknown blocks cannot match.
        observations.setdefault(header[1],[]).append(block if prefix and module_missing_diagnostic(block[prefix.end():]) else None)
    return {identity:hashlib.sha256(json.dumps(facts,ensure_ascii=False).encode()).hexdigest()
            for identity,facts in observations.items() if all(facts)}


def unavailable_loader_failures(stdout,stderr):
    return list(loader_dependency_fingerprints(stdout,stderr))


def current_loader_gap_fingerprints(row):
    if row.get('dependency_proof_version')==DEPENDENCY_PROOF_VERSION:
        return row.get('loader_dependency_fingerprints',{})
    if not recorded_output_complete(row):return {}
    return loader_dependency_fingerprints('',row.get('output_tail',''))


def module_missing_diagnostic(diagnostic):
    """Recognize typed diagnostics for comparison, not startup proof."""
    diagnostic=diagnostic.strip()
    if re.fullmatch(r"ModuleNotFoundError: No module named [^\n]+",diagnostic):return True
    if diagnostic.count('Traceback (most recent call last):')!=1 or not diagnostic.startswith('Traceback (most recent call last):'):
        return False
    lines=diagnostic.splitlines()
    if not re.fullmatch(r"ModuleNotFoundError: No module named [^\n]+",lines[-1]):return False
    return all(line.startswith(('  File ','    ','    ~','    ^')) or not line.strip()
               for line in lines[1:-1])


def python_module_startup_gap(diagnostic,argv):
    # -m must precede any script operand; a Python script printing a startup-like
    # line is not an interpreter startup failure.
    if not argv or '-m' not in argv or any(not arg.startswith('-') or arg in ('-c','--') for arg in argv[1:argv.index('-m')]):return False
    name=r'python(?:\d+(?:\.\d+)*)?(?:\.exe)?'
    if not re.fullmatch(name,re.split(r'[/\\]',argv[0])[-1],re.I):return False
    match=re.fullmatch(r"((?:[A-Za-z]:)?[^:\n]+): (?:No module named [^\n]+|Error while finding module specification for [^\n]+ \(ModuleNotFoundError: No module named [^\n]+\))",diagnostic)
    return bool(match and re.fullmatch(name,re.split(r'[/\\]',match[1])[-1],re.I))


def environment_only_failure(stdout, stderr, code, argv=None):
    """Recognize specific startup evidence; other nonzero runs are failures."""
    if code==0 or stdout.strip():return False
    diagnostic=stderr.strip()
    # A standalone exception says nothing about when application code ran.
    # A loader wrapper also cannot prove initialization did not run.
    if python_module_startup_gap(diagnostic,argv):return True
    # Shell diagnostics must actually name a shell, rather than an arbitrary
    # exception whose message happens to mention a missing command or file.
    shell=argv and re.fullmatch(r'(?:sh|bash|zsh|dash|ksh)',re.split(r'[/\\]',argv[0])[-1])
    if code in (126,127) and shell and re.fullmatch(r"(?:[^:\n]*/)?(?:sh|bash|zsh|dash|ksh): [^\n]*(?:command not found|: not found|No such file or directory)",diagnostic):return True
    return False


def recorded_output_complete(row):
    return row.get('output_complete') is True or ('output_complete' not in row and len(row.get('output_tail',''))<4000)


def current_unavailable(row):
    if not row.get('unavailable') or row_execution_observed(row):return False
    # Reevaluate earlier exception/wrapper exemptions from complete facts.
    if row.get('dependency_proof_version')==DEPENDENCY_PROOF_VERSION:return True
    if not recorded_output_complete(row):return False
    import shlex
    argv=row.get('argv') or shlex.split(row.get('command',''))
    return environment_only_failure('',row.get('output_tail',''),row.get('exit_code',1),argv)


def environment(repo,argv):
    return dict(python=sys.version,python_executable=sys.executable,platform=platform.platform(),
                executable=shutil.which(argv[0]) if '/' not in argv[0] else str((repo/argv[0]).resolve()))


def execute(repo, argv):
    """Return raw facts; each caller retains its own success/comparison policy."""
    from . import topic_service as topics
    identity=topics.content_id(repo)
    execution_environment=environment(repo,argv)
    try:
        result=subprocess.run(argv,cwd=repo,capture_output=True,text=True,errors='replace')
        code,output=result.returncode,result.stdout+result.stderr
        unavailable=code!=0 and environment_only_failure(result.stdout,result.stderr,code,argv) and not execution_observed(output)
        loader_fingerprints=loader_dependency_fingerprints(result.stdout,result.stderr)
        loader_gaps=list(loader_fingerprints)
    except OSError as exc:
        code,output,unavailable,loader_gaps=127,str(exc),True,[]
        loader_fingerprints={}
    return dict(argv=argv,exit_code=code,content_id=identity,environment=execution_environment,
                unavailable=unavailable,comparison_eligible=not loader_only_failure(output),
                execution_observed=execution_observed(output),output_complete=len(output)<=4000,output_length=len(output),
                unavailable_loader_failures=loader_gaps,loader_dependency_fingerprints=loader_fingerprints,dependency_proof_version=DEPENDENCY_PROOF_VERSION,
                content_changed=topics.content_id(repo)!=identity,output_tail=output[-4000:]),output


def bytes_match(path, sha256, size=None):
    content=Path(path).read_bytes()
    return hashlib.sha256(content).hexdigest()==sha256 and (size is None or len(content)==size)


def frozen_manifest(active):
    from .topic_service import TopicError
    path=Path(active['manifest'])
    if not bytes_match(path,active['manifest_sha256']):
        raise TopicError('manifest: 冻结材料已变化，请重新 review')
    manifest=json.loads(path.read_text())
    entries=manifest['inputs']+[e for c in manifest['changes'] for e in (c['base'],c['current']) if e]
    if any(not bytes_match(e['snapshot_path'],e['sha256']) for e in entries):
        raise TopicError('snapshot: 冻结材料已变化，请重新 review')
    return manifest


def accepted_matches(path, entry):
    path=Path(path)
    return path.is_file() and json.loads(path.read_text())==entry
