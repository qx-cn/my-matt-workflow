from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.workflow_lib.doctor import diagnose_repository


class DoctorTests(unittest.TestCase):
    def test_missing_release_and_host_are_reported_without_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            (root / "skills/my-one").mkdir(parents=True)
            home = Path(tmp) / "host"

            report = diagnose_repository(root, {"test": home})

            self.assertEqual("not-applicable", report["current_release"]["status"])
            self.assertEqual("not-installed", report["hosts"]["test"]["status"])
            self.assertFalse(home.exists())

    def test_source_comparison_failure_does_not_mislabel_verified_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            release = root / "releases/v1"
            skill = release / "skills/my-one/SKILL.md"
            runtime = release / "runtime/tools/workflow.py"
            skill.parent.mkdir(parents=True)
            runtime.parent.mkdir(parents=True)
            skill.write_text("source", encoding="utf-8")
            runtime.write_text("runtime", encoding="utf-8")
            import hashlib
            import json

            (release / "manifest.json").write_text(
                json.dumps(
                    {
                        "release_id": "v1",
                        "upstream_id": "local",
                        "skills": {
                            "my-one": {
                                "SKILL.md": hashlib.sha256(skill.read_bytes()).hexdigest()
                            }
                        },
                        "runtime": {
                            "tools/workflow.py": hashlib.sha256(runtime.read_bytes()).hexdigest()
                        },
                    }
                ),
                encoding="utf-8",
            )
            (root / "current.json").write_text('{"release_id":"v1"}', encoding="utf-8")
            (root / "skills/my-one").mkdir(parents=True)

            report = diagnose_repository(root, {})

            self.assertEqual("valid", report["current_release"]["status"])
            self.assertEqual("unavailable", report["current_release"]["source_match"])


if __name__ == "__main__":
    unittest.main()
