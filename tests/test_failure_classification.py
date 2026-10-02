"""Public CLI regressions for trusted startup evidence and legacy receipts."""
import json
import unittest
import test_batches


class FailureClassificationTests(unittest.TestCase):
    setUp = test_batches.BatchTests.setUp
    git = test_batches.BatchTests.git
    cli = test_batches.BatchTests.cli
    setup_config = test_batches.BatchTests.setup_config
    ticket = test_batches.BatchTests.ticket
    replace = test_batches.BatchTests.replace
    setup = test_batches.BatchTests.setup
    implement = test_batches.BatchTests.implement
    self_review = test_batches.BatchTests.self_review
    review = test_batches.BatchTests.review

    def dynamic_failure(self):
        runner = self.repo / 'full.py'
        runner.write_text('import unavailable_test_dependency\n')
        self.git('add', 'full.py'); self.git('commit', '-qm', 'original unavailable baseline')
        self.setup(full='python3 -B full.py'); self.implement()
        # Recreate the admitted pre-upgrade baseline from the holistic probe.
        baseline_path = self.repo / '.agent/work/feature/test-baseline.json'
        baseline = json.loads(baseline_path.read_text())
        baseline['results'][0].update(unavailable=True, dependency_proof_version=1)
        baseline_path.write_text(json.dumps(baseline))
        runner.write_text("from pathlib import Path\nimport importlib\ndef selected_plugin():\n    return 'json_typo_regression'\nPath('.agent/behavior-executed').write_text('selected_plugin invoked')\nimportlib.import_module(selected_plugin())\n")
        self.git('add', 'full.py'); self.git('commit', '-qm', 'regressed plugin selection')
        current = json.loads(self.cli('batch', 'test', '--topic', 'feature').stdout)
        self.assertEqual('selected_plugin invoked', (self.repo / '.agent/behavior-executed').read_text())
        return current

    def test_dynamic_business_import_failure_blocks_review_and_close(self):
        current = self.dynamic_failure()
        self.assertFalse(current['results'][0]['unavailable'])
        self.assertTrue(current['new_failures'])
        self.assertIn('python3 -B full.py', current['unverified'])
        for action in ('review', 'close'):
            self.assertIn('新增失败', self.cli('batch', action, '--topic', 'feature', ok=False).stderr)
        # Upgrade recovery must also reject the exact real diagnostic when its
        # old receipt cached the now-invalid version 1 environment exemption.
        receipt = self.repo / '.agent/work/feature/batch-tests-01.json'
        current['results'][0].update(unavailable=True, dependency_proof_version=1)
        current.update(new_failures=[], known_failures=[], unverified=[])
        receipt.write_text(json.dumps(current))
        self.assertIn('batch test', json.loads(self.cli('batch', 'status', '--topic', 'feature').stdout)['next_command'])
        self.assertIn('新增失败', self.cli('batch', 'close', '--topic', 'feature', ok=False).stderr)

    def test_version_one_cached_dynamic_failure_cannot_close_after_accepted_review(self):
        # Obtain a real accepted review on the same content, then replace its
        # test receipt with the historical misclassification. Close must inspect
        # the receipt facts even when a review has already been accepted.
        self.setup(full='python3 -B -m missing_startup_runner'); self.implement(); self.review()
        receipt = self.repo / '.agent/work/feature/batch-tests-01.json'
        old = json.loads(receipt.read_text())
        row = old['results'][0]
        row.update(dependency_proof_version=1, unavailable=True,
                   output_tail='Traceback (most recent call last):\n  File "full.py", line 4, in <module>\n    importlib.import_module(selected_plugin())\nModuleNotFoundError: No module named \'json_typo_regression\'\n',
                   output_complete=True, execution_observed=False)
        old.update(new_failures=[], known_failures=[], unverified=[])
        receipt.write_text(json.dumps(old))
        self.assertIn('batch test', json.loads(self.cli('batch', 'status', '--topic', 'feature').stdout)['next_command'])
        self.assertIn('新增失败', self.cli('batch', 'close', '--topic', 'feature', ok=False).stderr)

    def test_loader_dynamic_business_failure_and_old_caches_block_close(self):
        runner = self.repo / 'test_loader.py'
        runner.write_text('import unavailable_test_dependency\n')
        self.git('add', 'test_loader.py'); self.git('commit', '-qm', 'direct loader baseline')
        self.setup(full='python3 -B -m unittest test_loader'); self.implement()
        runner.write_text("from pathlib import Path\nimport importlib\ndef selected_plugin():\n    return 'json_typo_regression'\nPath('.agent/behavior-executed').write_text('selected_plugin invoked')\nimportlib.import_module(selected_plugin())\n")
        self.git('add', 'test_loader.py'); self.git('commit', '-qm', 'business loader regression')
        current = json.loads(self.cli('batch', 'test', '--topic', 'feature').stdout)
        self.assertTrue((self.repo / '.agent/behavior-executed').exists())
        self.assertFalse(current['results'][0]['unavailable'])
        self.assertTrue(current['new_failures'])
        receipt = self.repo / '.agent/work/feature/batch-tests-01.json'
        for version in (1, 2):
            with self.subTest(version=version):
                old = json.loads(json.dumps(current))
                old['results'][0].update(unavailable=True, dependency_proof_version=version)
                old.update(new_failures=[], known_failures=[], unverified=[])
                receipt.write_text(json.dumps(old))
                self.assertIn('batch test', json.loads(self.cli('batch', 'status', '--topic', 'feature').stdout)['next_command'])
                self.assertIn('新增失败', self.cli('batch', 'close', '--topic', 'feature', ok=False).stderr)

    def test_identical_direct_loader_dependency_remains_reviewable(self):
        runner = self.repo / 'test_loader.py'
        runner.write_text('import unavailable_test_dependency\n')
        self.git('add', 'test_loader.py'); self.git('commit', '-qm', 'direct loader baseline')
        self.setup(full='python3 -B -m unittest test_loader'); self.implement()
        current = json.loads(self.cli('batch', 'test', '--topic', 'feature').stdout)
        self.assertFalse(current['results'][0]['unavailable'])
        self.assertFalse(current['new_failures'])
        self.assertTrue(current['known_failures'])
        self.assertTrue(current['unverified'])
        self.review(); self.cli('batch', 'close', '--topic', 'feature')

    def test_partial_loader_new_missing_dependency_is_not_known(self):
        runner = self.repo / 'test_loader.py'
        runner.write_text('import unavailable_test_dependency\n')
        (self.repo / 'test_pass.py').write_text('import unittest\nclass Pass(unittest.TestCase):\n def test_ok(self): self.assertTrue(True)\n')
        self.git('add', 'test_loader.py', 'test_pass.py'); self.git('commit', '-qm', 'partial loader baseline')
        self.setup(full='python3 -B -m unittest test_loader test_pass'); self.implement()
        runner.write_text("import importlib\nimportlib.import_module('json_typo_regression')\n")
        self.git('add', 'test_loader.py'); self.git('commit', '-qm', 'partial loader business regression')
        current = json.loads(self.cli('batch', 'test', '--topic', 'feature').stdout)
        self.assertTrue(current['results'][0]['execution_observed'])
        self.assertTrue(current['new_failures'])
        self.assertFalse(current['known_failures'])
        self.assertIn('新增失败', self.cli('batch', 'close', '--topic', 'feature', ok=False).stderr)

    def test_actual_startup_gaps_remain_disclosed(self):
        commands = ('python3 -B -m missing_startup_runner', './missing-executable')
        for index, command in enumerate(commands):
            with self.subTest(command=command):
                if index: self.setUp()
                self.setup(full=command); self.implement()
                current = json.loads(self.cli('batch', 'test', '--topic', 'feature').stdout)
                self.assertTrue(current['results'][0]['unavailable'])
                self.assertFalse(current['new_failures'])
                self.assertIn(command, current['unverified'])
                self.review(); self.cli('batch', 'close', '--topic', 'feature')
