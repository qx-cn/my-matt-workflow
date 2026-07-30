import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.workflow_lib.artifact_resolver import (
    MAX_ARTIFACT_BYTES,
    ArtifactResolverError,
    list_work_artifacts,
    read_work_artifact,
    resolve_work_artifact,
)


class ArtifactResolverTests(unittest.TestCase):
    def _artifact(
        self,
        repo: Path,
        topic: str,
        artifact_type: str,
        filename: str,
        content: str | bytes = "# Artifact\n",
        *,
        nested: str | None = None,
    ) -> Path:
        directory = repo / ".agent" / "work" / topic / artifact_type
        if nested:
            directory /= nested
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / filename
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content)
        return path

    def test_lists_topic_type_and_resolves_latest_sequence_and_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            first = self._artifact(
                repo, "checkout", "tickets", "tickets-checkout-01.md"
            )
            latest = self._artifact(
                repo, "checkout", "tickets", "tickets-checkout-02.md"
            )
            self._artifact(
                repo, "search", "specs", "specs-search-01.md"
            )

            artifacts = list_work_artifacts(
                repo, topic="checkout", artifact_type="tickets"
            )

            self.assertEqual(
                [first.resolve(), latest.resolve()],
                [artifact.path for artifact in artifacts],
            )
            self.assertEqual(
                latest.resolve(),
                resolve_work_artifact(
                    repo, "checkout", "tickets", "latest"
                ).path,
            )
            self.assertEqual(
                first.resolve(),
                resolve_work_artifact(
                    repo, "checkout", "tickets", "01"
                ).path,
            )
            self.assertEqual(
                first.resolve(),
                resolve_work_artifact(
                    repo,
                    "checkout",
                    "tickets",
                    "tickets-checkout-01.md",
                ).path,
            )

    def test_rejects_traversal_and_absolute_components(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._artifact(
                repo, "checkout", "tickets", "tickets-checkout-01.md"
            )
            invalid_requests = (
                ("..", "tickets", "latest"),
                ("checkout", "../tickets", "latest"),
                ("checkout", "tickets", "../matt-workflow.md"),
                ("checkout", "tickets", "/tmp/secret.md"),
            )

            for topic, artifact_type, selector in invalid_requests:
                with self.subTest(selector=selector):
                    with self.assertRaisesRegex(ArtifactResolverError, "非法"):
                        resolve_work_artifact(
                            repo, topic, artifact_type, selector
                        )

    def test_rejects_symlink_escape_and_profile_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            outside = Path(tmp) / "outside.md"
            outside.write_text("# outside\n")
            profile = repo / ".agent" / "matt-workflow.md"
            profile.parent.mkdir(parents=True)
            profile.write_text("private configuration\n")
            escaped = (
                repo
                / ".agent"
                / "work"
                / "checkout"
                / "tickets"
                / "tickets-checkout-01.md"
            )
            escaped.parent.mkdir(parents=True)
            escaped.symlink_to(outside)

            self.assertEqual([], list_work_artifacts(repo, topic="other"))
            with self.assertRaisesRegex(ArtifactResolverError, "越界"):
                resolve_work_artifact(
                    repo,
                    "checkout",
                    "tickets",
                    "tickets-checkout-01.md",
                )
            with self.assertRaisesRegex(ArtifactResolverError, "非法"):
                resolve_work_artifact(
                    repo, "checkout", "tickets", "../../matt-workflow.md"
                )

    def test_rejects_ambiguous_sequence(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._artifact(
                repo, "checkout", "tickets", "tickets-checkout-01-api.md"
            )
            self._artifact(
                repo, "checkout", "tickets", "tickets-checkout-01-ui.md"
            )

            with self.assertRaisesRegex(ArtifactResolverError, "歧义"):
                resolve_work_artifact(repo, "checkout", "tickets", "01")

    def test_domain_type_includes_adr_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            glossary = self._artifact(
                repo,
                "checkout",
                "domain",
                "domain-checkout-glossary.md",
            )
            adr = self._artifact(
                repo,
                "checkout",
                "domain",
                "domain-checkout-0001-payment-state.md",
                nested="adr",
            )

            self.assertEqual(
                [adr.resolve(), glossary.resolve()],
                [
                    artifact.path
                    for artifact in list_work_artifacts(
                        repo, topic="checkout", artifact_type="domain"
                    )
                ],
            )
            self.assertEqual(
                adr.resolve(),
                resolve_work_artifact(
                    repo, "checkout", "domain", "0001"
                ).path,
            )
            self.assertEqual(
                glossary.resolve(),
                resolve_work_artifact(
                    repo,
                    "checkout",
                    "domain",
                    "domain-checkout-glossary.md",
                ).path,
            )

    def test_read_rejects_oversized_non_utf8_and_html_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            oversized = self._artifact(
                repo,
                "checkout",
                "tickets",
                "tickets-checkout-01.md",
                "x" * (MAX_ARTIFACT_BYTES + 1),
            )
            non_utf8 = self._artifact(
                repo,
                "checkout",
                "tickets",
                "tickets-checkout-02.md",
                b"\xff",
            )
            html = self._artifact(
                repo,
                "checkout",
                "tickets",
                "tickets-checkout-03.html",
                "<html><body>not an artifact</body></html>",
            )

            for path, expected in (
                (oversized, "大小"),
                (non_utf8, "UTF-8"),
                (html, "HTML"),
            ):
                with self.subTest(path=path.name):
                    artifact = resolve_work_artifact(
                        repo, "checkout", "tickets", path.name
                    )
                    with self.assertRaisesRegex(ArtifactResolverError, expected):
                        read_work_artifact(artifact)

    def test_cli_lists_resolves_and_reads_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._artifact(
                repo,
                "checkout",
                "tickets",
                "tickets-checkout-01.md",
                "# Checkout ticket\n",
            )
            workflow = Path(__file__).resolve().parents[1] / "tools/workflow.py"
            command = [sys.executable, str(workflow)]

            listed = subprocess.run(
                [
                    *command,
                    "work-list",
                    "--repo",
                    str(repo),
                    "--topic",
                    "checkout",
                    "--type",
                    "tickets",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            resolved = subprocess.run(
                [
                    *command,
                    "work-resolve",
                    "--repo",
                    str(repo),
                    "--topic",
                    "checkout",
                    "--type",
                    "tickets",
                    "--selector",
                    "latest",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            read = subprocess.run(
                [
                    *command,
                    "work-read",
                    "--repo",
                    str(repo),
                    "--topic",
                    "checkout",
                    "--type",
                    "tickets",
                    "--selector",
                    "01",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(0, listed.returncode, listed.stderr)
            self.assertEqual(0, resolved.returncode, resolved.stderr)
            self.assertEqual(0, read.returncode, read.stderr)
            self.assertEqual(
                [".agent/work/checkout/tickets/tickets-checkout-01.md"],
                [item["path"] for item in json.loads(listed.stdout)],
            )
            self.assertEqual(
                ".agent/work/checkout/tickets/tickets-checkout-01.md",
                json.loads(resolved.stdout)["path"],
            )
            self.assertEqual("# Checkout ticket\n", read.stdout)
