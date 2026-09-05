import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.workflow_lib.review_snapshot import build_review_snapshot


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


if __name__ == "__main__":
    unittest.main()
