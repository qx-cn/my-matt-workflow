import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.workflow_lib.review_snapshot import ReviewSnapshotError, build_review_snapshot


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "tools" / "workflow.py"


class ReviewSnapshotTests(unittest.TestCase):
    def _git(self, repo: Path, *arguments: str) -> str:
        result = subprocess.run(
            ["git", *arguments],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def _repo(self, directory: str) -> tuple[Path, str]:
        repo = Path(directory)
        self._git(repo, "init", "-q")
        self._git(repo, "config", "user.email", "review@example.com")
        self._git(repo, "config", "user.name", "Review Test")
        (repo / "tracked.txt").write_text("baseline\n")
        self._git(repo, "add", "tracked.txt")
        self._git(repo, "commit", "-qm", "baseline")
        return repo, self._git(repo, "rev-parse", "HEAD")

    def test_snapshot_covers_every_change_source_and_ignores_staging_movement(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, baseline = self._repo(tmp)

            (repo / "committed.txt").write_text("committed\n")
            self._git(repo, "add", "committed.txt")
            self._git(repo, "commit", "-qm", "committed change")
            (repo / "staged.txt").write_text("staged\n")
            self._git(repo, "add", "staged.txt")
            (repo / "tracked.txt").write_text("unstaged\n")
            (repo / "untracked.txt").write_text("untracked\n")

            before = build_review_snapshot(repo, baseline)

            self.assertEqual("ready", before["status"])
            self.assertEqual(
                {
                    "committed": ["committed.txt"],
                    "staged": ["staged.txt"],
                    "unstaged": ["tracked.txt"],
                    "untracked": ["untracked.txt"],
                },
                before["change_sources"],
            )
            self.assertEqual(
                {"committed.txt", "staged.txt", "tracked.txt", "untracked.txt"},
                {change["path"] for change in before["changes"]},
            )

            self._git(repo, "add", "tracked.txt", "untracked.txt")
            after = build_review_snapshot(repo, baseline)

            self.assertEqual(before["content_id"], after["content_id"])
            self.assertEqual([], after["change_sources"]["unstaged"])
            self.assertEqual([], after["change_sources"]["untracked"])

    def test_cli_rejects_changed_content_and_accepts_clean_equivalent_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, baseline = self._repo(tmp)
            (repo / "tracked.txt").write_text("reviewed\n")
            snapshot = build_review_snapshot(repo, baseline)

            (repo / "tracked.txt").write_text("changed after review\n")
            stale = subprocess.run(
                [
                    sys.executable,
                    str(WORKFLOW),
                    "review-snapshot",
                    "--repo",
                    str(repo),
                    "--base",
                    baseline,
                    "--expect-content-id",
                    snapshot["content_id"],
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(2, stale.returncode)
            self.assertEqual("stale", json.loads(stale.stdout)["status"])

            (repo / "tracked.txt").write_text("reviewed\n")
            self._git(repo, "add", "tracked.txt")
            self._git(repo, "commit", "-qm", "reviewed implementation")
            verified = subprocess.run(
                [
                    sys.executable,
                    str(WORKFLOW),
                    "review-snapshot",
                    "--repo",
                    str(repo),
                    "--base",
                    baseline,
                    "--expect-content-id",
                    snapshot["content_id"],
                    "--require-clean",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, verified.returncode, verified.stderr)
            self.assertEqual("match", json.loads(verified.stdout)["status"])

    def test_snapshot_expands_unborn_embedded_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, baseline = self._repo(tmp)
            embedded = repo / ".agent"
            embedded.mkdir()
            self._git(embedded, "init", "-q")
            spec = embedded / "spec.md"
            spec.write_text("# Spec\n")

            before = build_review_snapshot(repo, baseline)

            self.assertEqual(2, before["schema_version"])
            self.assertEqual("ready", before["status"])
            self.assertEqual([".agent/spec.md"], before["change_sources"]["untracked"])
            self.assertEqual(
                {".agent/spec.md"},
                {change["path"] for change in before["changes"]},
            )
            self.assertNotIn(".agent/.git", json.dumps(before))

            self._git(embedded, "add", "spec.md")
            staged = build_review_snapshot(repo, baseline)
            self.assertEqual(before["content_id"], staged["content_id"])

            spec.write_text("# Changed Spec\n")
            changed = build_review_snapshot(repo, baseline)
            self.assertNotEqual(before["content_id"], changed["content_id"])

    def test_snapshot_expands_committed_embedded_repository_and_honors_ignores(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, baseline = self._repo(tmp)
            embedded = repo / ".agent"
            embedded.mkdir()
            self._git(embedded, "init", "-q")
            self._git(embedded, "config", "user.email", "nested@example.com")
            self._git(embedded, "config", "user.name", "Nested Test")
            (embedded / ".gitignore").write_text("ignored.txt\n")
            (embedded / "tracked.md").write_text("committed\n")
            self._git(embedded, "add", ".gitignore", "tracked.md")
            self._git(embedded, "commit", "-qm", "nested baseline")
            (embedded / "tracked.md").write_text("modified\n")
            (embedded / "untracked.md").write_text("new\n")
            (embedded / "ignored.txt").write_text("ignored\n")

            snapshot = build_review_snapshot(repo, baseline)
            paths = {change["path"] for change in snapshot["changes"]}

            self.assertEqual(
                {".agent/.gitignore", ".agent/tracked.md", ".agent/untracked.md"},
                paths,
            )
            self.assertNotIn(".agent/ignored.txt", paths)

    def test_parent_owned_gitlink_stays_gitlink_and_rejects_dirty_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, baseline = self._repo(tmp)
            embedded = repo / "vendor"
            embedded.mkdir()
            self._git(embedded, "init", "-q")
            self._git(embedded, "config", "user.email", "nested@example.com")
            self._git(embedded, "config", "user.name", "Nested Test")
            (embedded / "library.txt").write_text("library\n")
            self._git(embedded, "add", "library.txt")
            self._git(embedded, "commit", "-qm", "library")
            nested_head = self._git(embedded, "rev-parse", "HEAD")
            self._git(repo, "add", "vendor")

            snapshot = build_review_snapshot(repo, baseline)
            vendor = next(
                change for change in snapshot["changes"] if change["path"] == "vendor"
            )
            self.assertEqual(
                {"mode": "160000", "object_id": nested_head}, vendor["current"]
            )

            (embedded / "dirty.txt").write_text("dirty\n")
            with self.assertRaisesRegex(
                ReviewSnapshotError, "gitlink 含未绑定到 commit 的工作树内容：vendor"
            ):
                build_review_snapshot(repo, baseline)


if __name__ == "__main__":
    unittest.main()
