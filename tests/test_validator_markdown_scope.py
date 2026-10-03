"""Repository Markdown gates must distinguish source from workflow history."""

import tempfile
import unittest
import json
import hashlib
from pathlib import Path

from tools.workflow_lib.validator import ValidationError, validate_markdown_references
from tools.workflow_lib.ticket_review import frozen_file


class MarkdownValidationScopeTests(unittest.TestCase):
    def write(self, root, name, body):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
        return path

    def archived_review(self, root, name='review-loop-rules.md', round=1):
        unit_id = str(round) * 32
        topic = root / '.agent/work/topic'
        directory = topic / 'reviews' / ('branch-' + unit_id)
        directory.mkdir(parents=True, exist_ok=True)
        row = frozen_file(directory, name, b'[source reference](missing-original-context.md)')
        manifest = dict(unit_id=unit_id, content_id='a' * 64, round=round, inputs=[row], changes=[])
        path = directory / 'manifest.json'
        path.write_text(json.dumps(manifest))
        entry = {key: manifest[key] for key in ('unit_id', 'content_id', 'round')}
        entry['manifest'] = str(path)
        unit = dict(reviews=[entry], active_review=dict(manifest=str(path),
                    manifest_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        record = topic / 'batches/01.json'
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(json.dumps(unit))
        archive = root / '.agent/archive/topic'
        archive.parent.mkdir(parents=True, exist_ok=True)
        topic.rename(archive)
        return archive / 'reviews' / directory.name / name, archive / 'batches/01.json', archive / 'reviews' / directory.name / 'manifest.json'

    def test_registered_frozen_blobs_remain_valid_after_topic_move(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.archived_review(root)
            validate_markdown_references(root)

    def test_extra_archive_document_is_not_exempted_by_a_valid_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            blob, _, _ = self.archived_review(root)
            self.write(root, str(blob.parent.relative_to(root) / 'review.md'), '[bad](missing.md)')
            with self.assertRaisesRegex(ValidationError, 'Markdown reference missing'):
                validate_markdown_references(root)

    def test_archived_snapshot_byte_changes_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            blob, _, _ = self.archived_review(root)
            blob.chmod(0o644)
            blob.write_text('tampered content without links')
            with self.assertRaisesRegex(ValidationError, 'byte integrity'):
                validate_markdown_references(root)

    def test_archived_manifest_changes_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, _, manifest = self.archived_review(root)
            manifest.write_text(manifest.read_text() + ' ')
            with self.assertRaisesRegex(ValidationError, 'manifest hash'):
                validate_markdown_references(root)

    def test_wrong_identity_outside_path_and_unrecognized_blob_fail_closed(self):
        for kind in ('identity', 'outside', 'unknown', 'symlink', 'malformed-record'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                _, record, manifest = self.archived_review(root, 'review.md' if kind == 'unknown' else 'rules.md')
                data = json.loads(manifest.read_text())
                if kind == 'identity': data['round'] = 9
                if kind == 'outside': data['inputs'][0]['snapshot_path'] = str(root / 'README.md')
                manifest.write_text(json.dumps(data))
                unit = json.loads(record.read_text())
                unit['active_review']['manifest_sha256'] = hashlib.sha256(manifest.read_bytes()).hexdigest()
                record.write_text(json.dumps(unit))
                if kind == 'symlink':
                    outside = root / 'outside.json'
                    outside.write_bytes(manifest.read_bytes())
                    manifest.unlink()
                    manifest.symlink_to(outside)
                if kind == 'malformed-record': record.write_text('[]')
                with self.assertRaisesRegex(ValidationError, 'archived review integrity'):
                    validate_markdown_references(root)

    def test_legacy_historical_review_keeps_identity_and_blob_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            blob, record, _ = self.archived_review(root)
            unit = json.loads(record.read_text())
            unit['past_reviews'] = unit.pop('reviews')
            unit.pop('active_review')
            record.write_text(json.dumps(unit))
            validate_markdown_references(root)
            blob.chmod(0o644)
            blob.write_text('modified historical input')
            with self.assertRaisesRegex(ValidationError, 'byte integrity'):
                validate_markdown_references(root)

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
