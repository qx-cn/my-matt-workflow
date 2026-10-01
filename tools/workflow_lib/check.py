"""Run the repository tests without touching releases or tracked source files."""
import subprocess
import sys
from pathlib import Path

class CheckError(RuntimeError):
    pass

def run_check(repo_root: Path):
    result = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests'],
                            cwd=repo_root.resolve(), capture_output=True, text=True, check=False)
    if result.returncode:
        raise CheckError('unit tests failed:\n' + (result.stdout + result.stderr).strip())
    return {'status':'valid', 'tests':{'status':'valid','evidence_level':'unit'}}
