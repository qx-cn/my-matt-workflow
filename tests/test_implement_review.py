"""Review materials and result admission observed through the public CLI."""
import json
from pathlib import Path
import unittest
import test_implement_lifecycle as impl_tests


class ReviewTests(unittest.TestCase):
    setUp = impl_tests.ImplementationTests.setUp
    git = impl_tests.ImplementationTests.git
    cli = impl_tests.ImplementationTests.cli
    setup_config = impl_tests.ImplementationTests.setup_config
    ticket = impl_tests.ImplementationTests.ticket
    replace = impl_tests.ImplementationTests.replace

    def start(self):
        self.setup_config(tests=("python3 -c 'pass'",))
        self.ticket()
        self.cli("implement", "start", "--ticket", "feature-01")
        self.cli("implement", "test", "--ticket", "feature-01")

    def review(self):
        return json.loads(self.cli("implement", "review", "--ticket", "feature-01", "--reviewer-model", "actual-host-model").stdout)

    def result(self, report, **overrides):
        result = json.loads(Path(report["result_file"]).read_text())
        result.update(status="pass", reviewer={"provenance": "self", "model": "actual-host-model"},
                      coverage=[{"target": a["id"], "result": "ok"} for a in result["acceptance"]]
                               + [{"target": p, "result": "ok"} for p in result["probes"]], findings=[])
        result.update(overrides)
        return result

    def submit(self, result, ok=True):
        path = self.repo / ".agent/result.json"
        path.write_text(json.dumps(result))
        return self.cli("implement", "review", "--ticket", "feature-01", "--submit", str(path), ok=ok)

    def test_freezes_all_changes_and_excludes_agent_plan(self):
        self.start()
        (self.repo / "code.txt").write_text("committed change")
        self.git("add", "code.txt")
        self.git("commit", "-qm", "implementation")
        (self.repo / "code.txt").write_text("final unstaged change")
        (self.repo / "outside.txt").write_text("outside scope")
        self.git("add", "outside.txt")
        (self.repo / "untracked.txt").write_text("untracked")
        (self.repo / ".agent/summary.md").write_text("IMPLEMENTER SECRET SUMMARY")
        briefing = self.repo / ".agent/work/feature/briefings/briefing-feature-01.md"
        briefing.write_text("IMPLEMENTER SECRET PLAN")
        report = self.review()
        package = json.loads(Path(report["manifest"]).read_text())
        self.assertEqual({"code.txt", "outside.txt", "untracked.txt"}, {c["path"] for c in package["changes"]})
        self.assertEqual(["outside.txt", "untracked.txt"], package["outside_scope"])
        change = next(c for c in package["changes"] if c["path"] == "code.txt")
        self.assertEqual("final unstaged change", Path(change["current"]["snapshot_path"]).read_text())
        self.assertNotEqual(Path(change["base"]["snapshot_path"]).read_text(), "committed change")
        materials = "\n".join(p.read_text(errors="replace") for p in Path(report["snapshot_dir"]).rglob("*") if p.is_file())
        self.assertNotIn("IMPLEMENTER SECRET", materials)
        self.assertEqual("feature-01#A1", package["acceptance"][0]["id"])
        self.assertEqual("marker observed", package["acceptance"][0]["text"])
        (self.repo / "outside.txt").write_text("later mutation")
        self.assertEqual("outside scope", Path(next(c for c in package["changes"] if c["path"] == "outside.txt")["current"]["snapshot_path"]).read_text())

    def test_pass_and_advisory_results_are_registered_truthfully(self):
        self.start()
        report = self.review()
        result = self.result(report, status="findings", findings=[{"id": "suggestion", "severity": "advisory", "summary": "optional clarity", "anchor": "feature-01#A1"}])
        output = json.loads(self.submit(result).stdout)
        self.assertEqual("pass", output["status"])
        self.assertEqual("self", output["reviewer"]["provenance"])
        topic = json.loads(self.cli("topic", "status", "--topic", "feature").stdout)
        self.assertEqual("suggestion", topic["advisories"][0]["id"])
        self.assertEqual("pass", json.loads(self.submit(result).stdout)["status"])

    def test_submit_reports_all_missing_and_changed_prefilled_fields(self):
        self.start()
        report = self.review()
        valid = self.result(report)
        broken = dict(valid)
        for key in ("unit_id", "content_id", "round", "acceptance", "probes", "downstream_tickets"):
            broken[key] = None
        output = self.submit(broken, ok=False).stderr
        for key in ("unit_id", "content_id", "round", "acceptance", "probes", "downstream_tickets"):
            self.assertIn(key + ":", output)
        missing = {"status": "pass"}
        output = self.submit(missing, ok=False).stderr
        for key in ("reviewer", "coverage", "findings", "unit_id"):
            self.assertIn(key + ":", output)
        self.assertEqual("pass", json.loads(self.submit(valid).stdout)["status"])

    def test_semantic_validation_coverage_severity_and_blocking_evidence(self):
        self.start()
        report = self.review()
        result = self.result(report)
        for key, value, field in [("status", "approved", "status"), ("coverage", [], "coverage"),
                                  ("reviewer", {"provenance": "independent", "model": "actual-host-model"}, "reviewer.provenance"),
                                  ("reviewer", {"provenance": "self", "model": "different-model"}, "reviewer.model")]:
            broken = {**result, key: value}
            self.assertIn(field, self.submit(broken, ok=False).stderr)
        finding = {"id": "bug", "severity": "blocking", "summary": "observable bug", "anchor": "feature-01#A1"}
        result["findings"] = [finding]
        result["coverage"][0] = {"target": "feature-01#A1", "result": "finding", "finding_id": "bug"}
        output = self.submit(result, ok=False).stderr
        for field in ("status", "location", "failure_path", "reachability"):
            self.assertIn(field, output)
        result["status"] = "findings"
        finding.update(location="code.txt:1", failure_path="read code then fails", reachability="default operation reaches this file")
        self.assertEqual("findings", json.loads(self.submit(result).stdout)["status"])
        result["findings"][0]["severity"] = "P1"
        self.assertIn("severity", self.submit(result, ok=False).stderr)

    def test_stale_content_and_frozen_corruption_reject_without_losing_retry(self):
        self.start()
        report = self.review()
        result = self.result(report)
        (self.repo / "code.txt").write_text("changed")
        self.assertIn("content_id", self.submit(result, ok=False).stderr)
        self.git("restore", "code.txt")
        self.assertEqual("pass", json.loads(self.submit(result).stdout)["status"])
        report = self.review()
        manifest = json.loads(Path(report["manifest"]).read_text())
        frozen = Path(manifest["inputs"][0]["snapshot_path"])
        frozen.chmod(0o644)
        frozen.write_text("tampered")
        self.assertIn("snapshot", self.submit(self.result(report), ok=False).stderr)

    def test_changed_rules_decisions_and_downstream_require_fresh_materials(self):
        self.setup_config(tests=("python3 -c 'pass'",))
        ticket = self.ticket()
        rule = self.repo / ".agent/rule.md"
        rule.write_text("initial rule")
        spec = ".agent/work/feature/specs/specs-feature-01.md"
        self.replace(ticket, "rule_sources", [spec, ".agent/rule.md"])
        self.ticket(number=2, dependencies=("feature-01",))
        decided = self.repo / ".agent/work/feature/decided/decided-feature.md"
        decided.parent.mkdir()
        decided.write_text("approved decision")
        self.cli("implement", "start", "--ticket", "feature-01")
        report = self.review()
        self.assertEqual("feature-02", report["downstream_tickets"][0]["id"])
        result = self.result(report)
        rule.write_text("changed rule")
        self.assertIn("rules", self.submit(result, ok=False).stderr)
        rule.write_text("initial rule")
        decided.write_text("changed decision")
        self.assertIn("decided", self.submit(result, ok=False).stderr)
        decided.write_text("approved decision")
        successor = self.repo / ".agent/work/feature/tickets/tickets-feature-02.md"
        successor.write_text(successor.read_text().replace("marker observed", "new downstream acceptance"))
        self.assertIn("downstream_tickets", self.submit(result, ok=False).stderr)
        fresh = self.review()
        self.assertEqual("pass", json.loads(self.submit(self.result(fresh)).stdout)["status"])

    def test_materials_include_loop_decisions_downstream_and_all_coverage(self):
        self.setup_config(tests=("python3 -c 'pass'",))
        self.ticket()
        self.ticket(number=2, dependencies=("feature-01",))
        spec = self.repo / ".agent/work/feature/specs/specs-feature-01.md"
        spec.write_text(spec.read_text() + "\n**I-K1**: preserve tests\n")
        decided = self.repo / ".agent/work/feature/decided/decided-feature.md"
        decided.parent.mkdir()
        decided.write_text("approved choice")
        self.cli("implement", "start", "--ticket", "feature-01")
        report = self.review()
        manifest = json.loads(Path(report["manifest"]).read_text())
        loop = Path(next(i for i in manifest["inputs"] if Path(i["snapshot_path"]).name == "review-loop-rules.md")["snapshot_path"]).read_text()
        for phrase in ("4", "needs-user", "同一根因", "1.5", "inconclusive"):
            self.assertIn(phrase, loop)
        result = self.result(report)
        self.assertIn("I-K1", self.submit(result, ok=False).stderr)
        result["coverage"].append({"target": "I-K1", "result": "not-applicable"})
        self.assertIn("reason", self.submit(result, ok=False).stderr)
        result["coverage"][-1]["reason"] = "no test-command modification in this change"
        self.assertEqual("pass", json.loads(self.submit(result).stdout)["status"])
        conflicting = dict(result, status="inconclusive")
        self.assertIn("unit_id", self.submit(conflicting, ok=False).stderr)

    def test_declared_reviewer_session_is_bound_and_self_cannot_upgrade(self):
        self.start()
        report = self.review()
        result = self.result(report)
        result["reviewer"]["provenance"] = "independent"
        self.assertIn("reviewer.provenance", self.submit(result, ok=False).stderr)
        independent = json.loads(self.cli("implement", "review", "--ticket", "feature-01",
            "--reviewer-model", "declared-model", "--reviewer-session-id", "separate-host-session").stdout)
        result = self.result(independent)
        result["reviewer"] = {"provenance": "independent", "model": "declared-model"}
        self.assertEqual("independent", json.loads(self.submit(result).stdout)["reviewer"]["provenance"])
        self.assertIn("unit_id", self.submit(self.result(report), ok=False).stderr)

    def test_deletion_binary_links_modes_and_ignored_files_are_observable(self):
        (self.repo / "remove.txt").write_text("delete me")
        (self.repo / "binary.bin").write_bytes(b"\x00\xffinitial")
        (self.repo / ".gitignore").write_text("ignored.txt\n")
        self.git("add", ".")
        self.git("commit", "-qm", "base assets")
        self.start()
        (self.repo / "remove.txt").unlink()
        (self.repo / "binary.bin").write_bytes(b"\x00\xffchanged")
        (self.repo / "code.txt").chmod(0o755)
        (self.repo / "link").symlink_to("/not-read-outside-repo")
        (self.repo / "ignored.txt").write_text("ignored")
        report = self.review()
        manifest = json.loads(Path(report["manifest"]).read_text())
        changes = {c["path"]: c for c in manifest["changes"]}
        self.assertNotIn("ignored.txt", changes)
        self.assertIsNone(changes["remove.txt"]["current"])
        self.assertEqual(b"\x00\xffchanged", Path(changes["binary.bin"]["current"]["snapshot_path"]).read_bytes())
        self.assertEqual("100755", changes["code.txt"]["current"]["mode"])
        self.assertEqual("120000", changes["link"]["current"]["mode"])
        self.assertEqual("/not-read-outside-repo", Path(changes["link"]["current"]["snapshot_path"]).read_text())
        (self.repo / "ignored.txt").write_text("changed ignored")
        (self.repo / ".agent/summary.md").write_text("changed excluded")
        self.assertEqual("pass", json.loads(self.submit(self.result(report)).stdout)["status"])

    def test_invalid_shapes_report_fields_without_tracebacks(self):
        self.start()
        report = self.review()
        valid = self.result(report)
        cases = [({"coverage": [{"target": [], "result": "ok"}]}, "coverage"),
                 ({"findings": [{"id": "bad", "anchor": [], "severity": "blocking", "summary": "bad"}]}, "anchor"),
                 ({"findings": [{"id": {}, "anchor": "feature-01#A1", "severity": {}, "summary": None}]}, "findings"),
                 ({"reviewer": []}, "reviewer"), ({"coverage": "ok"}, "coverage"), ({"findings": {}}, "findings")]
        for mutation, field in cases:
            with self.subTest(mutation=mutation):
                output = self.submit({**valid, **mutation}, ok=False).stderr
                self.assertIn(field, output)
                self.assertNotIn("Traceback", output)
        valid["coverage"].append(valid["coverage"][0])
        self.assertIn("target", self.submit(valid, ok=False).stderr)

    def test_nonpass_statuses_preserve_result_and_needs_user_refuses_review(self):
        self.start()
        for expected in ("inconclusive", "blocked-by-design"):
            report = self.review()
            result = self.result(report, status=expected)
            self.assertEqual(expected, json.loads(self.submit(result).stdout)["status"])
        path = self.repo / ".agent/work/feature/tickets/tickets-feature-01.md"
        self.replace(path, "status", "needs-user")
        self.assertIn("implementing", self.cli("implement", "review", "--ticket", "feature-01",
                                              "--reviewer-model", "actual-host-model", ok=False).stderr)

    def test_nested_agent_fixtures_remain_content_in_complete_review(self):
        fixture = self.repo / "tests/fixtures/demo/.agent/config.md"
        fixture.parent.mkdir(parents=True)
        fixture.write_text("fixture baseline")
        self.git("add", "tests")
        self.git("commit", "-qm", "test fixture baseline")
        self.start()
        fixture.write_text("fixture modified")
        added = self.repo / "tests/fixtures/demo/.agent/new.md"
        added.write_text("new fixture")
        (self.repo / ".agent/summary.md").write_text("root summary excluded")
        report = self.review()
        manifest = json.loads(Path(report["manifest"]).read_text())
        changes = {c["path"]: c for c in manifest["changes"]}
        self.assertEqual({"tests/fixtures/demo/.agent/config.md", "tests/fixtures/demo/.agent/new.md"}, set(changes))
        old = changes["tests/fixtures/demo/.agent/config.md"]
        self.assertEqual("fixture baseline", Path(old["base"]["snapshot_path"]).read_text())
        self.assertEqual("fixture modified", Path(old["current"]["snapshot_path"]).read_text())
        self.assertEqual(sorted(changes), manifest["outside_scope"])


if __name__ == "__main__":
    unittest.main()
