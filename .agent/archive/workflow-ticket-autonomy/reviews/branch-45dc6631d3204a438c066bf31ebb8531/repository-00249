"""Generate A–E using a pinned v1 runtime, never the runtime under construction."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from tools.capture_workflow_baseline import OLD_CHAIN, measure_markdown


APP = 'def greeting(name):\n    return "Hello, " + name.strip()\n'
TEST = ('import unittest\nfrom app import greeting\n\n'
        'class GreetingTests(unittest.TestCase):\n'
        '    def test_trimmed_name(self):\n'
        '        self.assertEqual("Hello, fixture", greeting(" fixture "))\n')
STATES = {"A": ["ready-for-agent", "complete", "implementing"],
          "B": ["blocked-by-design"], "C": ["revalidated"],
          "D": ["complete"], "E": ["implementing", "blocked-by-design"]}


def capture(repo: Path, runtime: Path, release: Path, output: Path) -> dict:
    """Persist raw runtime output, its Git baseline, and the text measurement."""
    if output.exists():
        raise ValueError(f"refusing to overwrite a captured baseline: {output}")
    runtime = runtime.resolve()
    release = release.resolve()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    events = []

    def command(argv, cwd):
        result = subprocess.run([str(a) for a in argv], cwd=cwd, env=env,
                                capture_output=True, text=True, check=True)
        return result.stdout.strip()

    def cli(project, *args):
        raw = command([sys.executable, runtime, *args], project)
        # setup emits more than one JSON document; all other used commands emit one.
        events.append({"argv": list(map(str, args)), "stdout": raw, "exit_code": 0})
        return json.loads(raw)

    with tempfile.TemporaryDirectory(prefix="workflow-v1-baseline-") as tmp:
        staging = Path(tmp)
        project = staging / "project"
        project.mkdir()
        command(["git", "init", "-q", "-b", "main"], project)
        command(["git", "config", "user.name", "Workflow fixture"], project)
        command(["git", "config", "user.email", "fixture@example.invalid"], project)
        (project / "app.py").write_text(APP)
        (project / "test_app.py").write_text(TEST)
        (project / ".gitignore").write_text("__pycache__/\n*.pyc\n")
        (project / "AGENTS.md").write_text("# Fixture rules\nUse only the Python standard library.\n")
        # Public old setup owns the configuration. No real Agent home is touched.
        args = ["setup", "--repo", str(project), "--apply", "--agent-directory-mode", "shared",
                "--assurance-level", "audited", "--execution-agent", "codex",
                "--test-command", "python3 -m unittest -v"]
        setup = command([sys.executable, runtime, *args], project)
        events.append({"argv": args, "stdout": setup, "exit_code": 0})
        for topic, states in STATES.items():
            slug = f"legacy-{topic.lower()}"
            work = project / ".agent" / "work" / slug
            (work / "specs").mkdir(parents=True)
            (work / "tickets").mkdir()
            (work / "contexts").mkdir()
            (work / "contexts" / f"contexts-{slug}-01.md").write_text(
                "# 术语\n\n- Greeting：去掉名字首尾空白后的问候。\n", encoding="utf-8")
            (work / "specs" / f"specs-{slug}-01.md").write_text(
                f"---\nspec_id: {slug}\nrevision: 1\nsupersedes:\nstatus: current\n---\n"
                "\n# Greeting fixture\n\n## 验收\n\n- 去掉名字首尾空白后输出问候。\n")
            for number in range(1, len(states) + 1):
                tid = f"{slug}-{number:02}"
                (work / "tickets" / f"tickets-{tid}.md").write_text(
                    f"---\nid: {tid}\ntitle: Trim greeting name\nticket_kind: implementation\n"
                    f"spec_id: {slug}\nspec_revision: 1\n"
                    f"spec_ref: .agent/work/{slug}/specs/specs-{slug}-01.md\n"
                    "supersedes_ticket: []\ncompensates: []\nstatus: ready-for-agent\n"
                    "blocked_by: []\nclaimed_by:\ntags: []\n"
                    f"sequence: {number}\nrule_sources: [AGENTS.md]\n"
                    "rule_scope: [app.py, test_app.py]\nrule_constraints: [standard-library-only]\n"
                    "rule_conflicts: []\nreview_probes: []\nexecution_agent: codex\n---\n"
                    "\n# Greeting fixture\n\n- [ ] greeting trims the name and returns Hello, fixture.\n")
        command(["git", "add", "."], project)
        command(["git", "commit", "-qm", "Seed pre-simplification fixture"], project)
        baseline = command(["git", "rev-parse", "HEAD"], project)
        for topic, states in STATES.items():
            slug = f"legacy-{topic.lower()}"
            for number, state in enumerate(states, 1):
                ticket = project / ".agent" / "work" / slug / "tickets" / f"tickets-{slug}-{number:02}.md"
                if state == "ready-for-agent":
                    continue
                opened = cli(project, "implementation-open", "--repo", project, "--ticket", ticket,
                             "--base", baseline, "--agent", "codex", "--path", "app.py", "--path", "test_app.py")
                journal = opened["lanes"][0]["work_unit"]["journal"]
                if state == "implementing":
                    cli(project, "run-record", journal, "--phase", "implementing")
                    continue
                result_file = staging / "result.json"
                if state == "complete":
                    cli(project, "run-record", journal, "--phase", "implementing")
                    test = cli(project, "run-test-evidence", "--journal", journal,
                               "--", "python3", "-m", "unittest", "-v")
                    cli(project, "run-record", journal, "--phase", "reviewing")
                    review = cli(project, "run-review-open", "--journal", journal)
                    unit = review
                    # This calibration fixture has exactly two tiny immutable inputs.
                    frozen = {a["repo_path"]: Path(a["snapshot_path"]).read_text()
                              for a in unit["artifacts"]}
                    if frozen != {"app.py": APP, "test_app.py": TEST}:
                        raise ValueError("fixture review input is not the known greeting example")
                    boundary = unit["ticket_boundary"]
                    refs = ["snapshot:app.py", "snapshot:test_app.py", f"test:{test['evidence_id']}"]
                    result_file.write_text(json.dumps({
                        "review_id": unit["review_id"], "code_content_id": unit["code_content_id"],
                        "status": "pass", "reviewer_provenance": {
                            "kind": "self", "session_id": unit["implementation_session_id"]},
                        "findings": [], "follow_ons": [], "design_gap": None,
                        "self_review_coverage": {
                            "acceptance": [{"acceptance_id": a["id"], "evidence_refs": refs}
                                           for a in boundary["current"]["acceptance"]],
                            "probes": [{"probe": p, "summary": "Known greeting fixture; no downstream consumer change.",
                                        "evidence_refs": refs} for p in boundary["required_probes"]]},
                    }))
                    reviewed = cli(project, "run-review-submit", "--journal", journal,
                                   "--snapshot-dir", review["snapshot_dir"], "--result-file", result_file)
                    if reviewed["status"] != "pass":
                        raise ValueError(f"calibration review was not accepted: {reviewed}")
                    code = cli(project, "run-code-receipt", "--journal", journal)
                    cli(project, "run-record", journal, "--phase", "committing")
                    outcome = {"outcome": "completed", "test_receipt": test,
                               "review_receipt": reviewed["review_receipt"], "code_receipt": code,
                               "blocker": None}
                else:
                    outcome = {"outcome": "blocked-by-design", "test_receipt": None,
                               "review_receipt": None, "code_receipt": None,
                               "blocker": "Synthetic legacy design-blocked example for migration."}
                result_file.write_text(json.dumps(outcome))
                cli(project, "implementation-submit", "--journal", journal, "--result-file", result_file)
                cli(project, "implementation-close", "--journal", journal)
                if state == "revalidated":
                    # v1 exposes validation and projection separately for these two states.
                    for target in ("revising", "revalidated"):
                        cli(project, "ticket-transition", ticket, "--to", target)
                        snippet = (
                            "import sys; from pathlib import Path; "
                            "from workflow_lib.lifecycle import project_ticket; "
                            "p=Path(sys.argv[1]); "
                            "p.write_text(project_ticket(p.read_text(),status=sys.argv[2],claimed_by=''))"
                        )
                        command([sys.executable, "-c", snippet, ticket, target], runtime.parent)
                        events.append({"api": "workflow_lib.lifecycle.project_ticket",
                                       "ticket": str(ticket), "to": target})
        captured = staging / "capture"
        captured.mkdir()
        command(["git", "bundle", "create", captured / "baseline.bundle", "--all"], project)
        shutil.copytree(project, captured / "legacy_project",
                        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
        unfinished = repo / "evals" / "fixtures" / "my-implement" / "unfinished-session"
        shutil.copytree(unfinished, captured / "unfinished_session")
        cursor = staging / "cursor"
        shutil.copytree(release / "skills", cursor)
        projection = ("from pathlib import Path; from workflow_lib.projection import project_skill_directory; "
                      "import sys; root=Path(sys.argv[1]); "
                      "[project_skill_directory(p,'cursor') for p in root.iterdir() if p.is_dir()]")
        command([sys.executable, "-c", projection, cursor], runtime.parent)
        measurement = measure_markdown(cursor, OLD_CHAIN)
        metadata = {
            "source_commit": command(["git", "rev-parse", "HEAD"], repo),
            "release_id": json.loads((release / "manifest.json").read_text())["release_id"],
            "release_manifest_sha256": hashlib.sha256((release / "manifest.json").read_bytes()).hexdigest(),
            "runtime_sha256": hashlib.sha256(runtime.read_bytes()).hexdigest(),
            "runtime_source": str(runtime), "fixture_source_root": str(project),
            "baseline_commit": baseline, "legacy_states": STATES,
            "measurement": dict(measurement, target="cursor", skills=list(OLD_CHAIN)),
            "expected_migration": {"A": "resume implementing after dropping old evidence",
                                   "B": "needs-user; accept after tests or reopen after revision",
                                   "C": "implementing", "D": "complete, migration-archived",
                                   "E": "cannot migrate whole Topic automatically: violates I-T3"},
        }
        (captured / "baseline.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
        (captured / "generation.json").write_text(json.dumps(events, ensure_ascii=False, indent=2) + "\n")
        shutil.copytree(captured, output)
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--legacy-runtime", type=Path, required=True)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    captured = capture(args.repo.resolve(), args.legacy_runtime, args.release, args.output.resolve())
    print(json.dumps({"states": captured["legacy_states"],
                      "characters": captured["measurement"]["characters"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
