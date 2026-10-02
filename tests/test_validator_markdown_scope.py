"""Repository Markdown gates must distinguish source from workflow history."""

import tempfile
import unittest
from pathlib import Path

from tools.workflow_lib.validator import ValidationError, validate_markdown_references


class MarkdownValidationScopeTests(unittest.TestCase):
    def write(self, root, name, body):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
        return path

    def test_runtime_evidence_and_nested_fixture_are_not_source_documents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, 'README.md', '[guide](docs/guide.md)')
            self.write(root, 'docs/guide.md', 'Repository guide')
            self.write(root, '.agent/matt-workflow.md', '[guide](../docs/guide.md)')
            for name in (
                '.agent/work/topic/delivery.md',
                '.agent/work/topic/reviews/raw-report.md',
                '.agent/work/topic/fixture/repo/README.md',
            ):
                self.write(root, name, '[evidence](/tmp/expired-review.md)')
            validate_markdown_references(root)

    def test_formal_docs_and_repository_configuration_still_reject_bad_links(self):
        for name in ('README.md', 'docs/guide.md', '.agent/matt-workflow.md',
                     '.agent/policy.md', '.agent/archive/topic/review.md',
                     'tests/fixtures/example/README.md', 'docs/.agent/guide.md'):
            for target, error in (('missing.md', 'missing'),
                                  ('/tmp/outside.md', 'escapes repository')):
                with self.subTest(name=name, target=target):
                    with tempfile.TemporaryDirectory() as directory:
                        root = Path(directory)
                        self.write(root, name, f'[bad]({target})')
                        with self.assertRaisesRegex(ValidationError, error):
                            validate_markdown_references(root)


if __name__ == '__main__':
    unittest.main()
