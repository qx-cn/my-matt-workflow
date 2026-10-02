"""Loader comparison must retain strict proof across unittest report formats."""
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from tools.workflow_lib import batches, evidence


class LoaderReportCompatibilityTests(unittest.TestCase):
    def report(self, source, verbose=False):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'test_missing.py').write_text(source)
            command = [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', folder]
            if verbose:
                command.append('-v')
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(1, result.returncode)
            self.assertEqual('', result.stdout)
            return result.stderr

    def formats(self, report):
        # Start with a real interpreter report, replacing only the known class
        # display difference in both progress and diagnostic headers.
        short = report.replace('unittest.loader._FailedTest.test_missing',
                               'unittest.loader._FailedTest')
        yield short
        yield short.replace('unittest.loader._FailedTest)',
                            'unittest.loader._FailedTest.test_missing)')

    def row(self, output):
        return dict(command='python3 -m unittest', exit_code=1,
                    failures=batches.failures(output, 1), output_tail=output,
                    output_complete=True, unavailable=False,
                    comparison_eligible=not evidence.loader_only_failure(output),
                    execution_observed=evidence.execution_observed(output),
                    dependency_proof_version=3,
                    loader_dependency_fingerprints=evidence.loader_dependency_fingerprints('', output))

    def test_real_loader_reports_keep_typed_proof_in_both_formats(self):
        for verbose in (False, True):
            report = self.report('import outcome_ci_dependency_missing\n', verbose)
            for output in self.formats(report):
                with self.subTest(verbose=verbose, output=output):
                    self.assertFalse(evidence.execution_observed(output))
                    self.assertTrue(evidence.loader_only_failure(output))
                    self.assertEqual(1, len(evidence.loader_dependency_fingerprints('', output)))
                    row = self.row(output)
                    comparison = batches.compare(dict(commands=[row['command']], results=[row]),
                                                 dict(commands=[row['command']], results=[row]))
                    self.assertFalse(comparison['new_failures'])
                    self.assertTrue(comparison['known_failures'])
                    self.assertTrue(comparison['unverified'])

    def test_changed_assertion_and_old_v3_cache_cannot_be_known(self):
        baseline_report = self.report('import outcome_ci_dependency_missing\n')
        assertion_report = self.report("assert False, 'actual import regression'\n")
        for baseline_output, assertion_output in zip(self.formats(baseline_report), self.formats(assertion_report)):
            baseline = self.row(baseline_output)
            current = self.row(assertion_output)
            self.assertEqual({}, current['loader_dependency_fingerprints'])
            # These are the incorrect facts cached by pre-fix v3 on Python 3.10.
            baseline.update(execution_observed=True, comparison_eligible=True,
                            loader_dependency_fingerprints={})
            current.update(execution_observed=True, comparison_eligible=True)
            comparison = batches.compare(dict(commands=[baseline['command']], results=[baseline]),
                                         dict(commands=[current['command']], results=[current]))
            self.assertTrue(comparison['new_failures'])
            self.assertFalse(comparison['known_failures'])
            self.assertTrue(comparison['unverified'])

    def test_unrelated_class_names_are_not_loader_wrappers(self):
        for identity in ('test (custom.unittest.loader._FailedTest)',
                         'test (unittest.loader._FailedTestFake)',
                         'test (unittest.loader._FailedTest) trailing'):
            self.assertFalse(evidence.loader_failure_identity(identity))
