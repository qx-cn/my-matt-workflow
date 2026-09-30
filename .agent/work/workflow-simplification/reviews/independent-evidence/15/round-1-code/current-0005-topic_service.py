"""Configuration v2 and local Topic lifecycle.

This module owns the new model; legacy session APIs are kept separately while
their consumers are migrated by subsequent implementation Tickets.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess


class TopicError(ValueError):
    pass


KEYS = ("schema_version", "task_backend", "agent_directory_mode", "default_base_branch",
        "test_commands", "standards_sources", "domain_sources", "default_execution_agent",
        "assurance_level")
STRING_KEYS = {"task_backend", "agent_directory_mode", "default_base_branch",
               "default_execution_agent", "assurance_level"}
REMOVED = {"branch_policy", "commit_policy", "external_write_policy", "docs_writeback",
           "composition_policy", "work_scope_policy", "decision_policy", "max_repair_rounds",
           "humanizer_policy", "review_commands"}
HEADINGS = ("改动概述", "测试结果", "审查发现与修复", "建议", "已知问题",
            "长期知识沉淀", "用户介入记录", "未验证项")
STATE_FILE = "topic-state.json"


def now():
    return datetime.now(timezone.utc).isoformat()


def git(repo, *args, check=True):
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True)
    if check and result.returncode:
        raise TopicError(f"git {args[0]} 失败：{result.stderr.decode(errors='replace').strip()}")
    return result


def safe_repo(repo):
    repo = Path(repo).resolve()
    if not repo.is_dir():
        raise TopicError(f"repo 不存在：{repo}")
    # Do not follow project-controlled links out of the selected repository.
    agent = repo / ".agent"
    if agent.is_symlink():
        raise TopicError(".agent 不能是符号链接")
    if agent.exists() and not agent.is_dir():
        raise TopicError(".agent 必须是目录")
    for path in agent.rglob("*") if agent.exists() else ():
        if path.is_symlink():
            raise TopicError(f".agent 内不能有符号链接：{path.relative_to(repo)}")
    return repo


def validate_config(config):
    if type(config.get("schema_version")) is not int or config.get("schema_version") != 2 or REMOVED.intersection(config) or config.get("assurance_level") == "audited":
        raise TopicError("旧配置：请运行 workflow.py migrate --repo <路径>")
    unknown = set(config) - set(KEYS)
    missing = set(KEYS) - set(config)
    if unknown or missing:
        raise TopicError(f"配置字段错误：unknown={sorted(unknown)}, missing={sorted(missing)}")
    enums = {"task_backend": {"local"}, "agent_directory_mode": {"private", "shared"},
             "default_execution_agent": {"auto", "codex", "cursor", "claude"},
             "assurance_level": {"quick", "standard"}}
    for key, allowed in enums.items():
        if not isinstance(config[key], str) or config[key] not in allowed:
            raise TopicError(f"{key} 非法：应为 {sorted(allowed)}")
    if not isinstance(config["default_base_branch"], str) or not config["default_base_branch"].strip():
        raise TopicError("default_base_branch 必须为非空字符串")
    for key in ("test_commands", "standards_sources", "domain_sources"):
        values = config[key]
        if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
            raise TopicError(f"{key} 必须为非空字符串的列表")
    for command in config["test_commands"]:
        try:
            argv = shlex.split(command[:-2] if command.endswith(" *") else command)
        except ValueError as exc:
            raise TopicError(f"test_commands：{exc}") from exc
        if not argv:
            raise TopicError("test_commands 命令不能为空")
    return config


def read_config(repo):
    path = repo / ".agent/matt-workflow.md"
    try:
        lines = path.read_text().splitlines()
    except OSError as exc:
        raise TopicError("缺少配置，请先运行 setup --apply") from exc
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        raise TopicError("配置 frontmatter 无效；旧配置请运行 migrate")
    config = {}
    for line in lines[1:lines.index("---", 1)]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if not separator or key in config:
            raise TopicError(f"配置字段无效或重复：{key}")
        if key in STRING_KEYS and not value.startswith('"'):
            # Legacy v2 files used bare strings, including legal branch names
            # such as null/true/123. Their type comes from the field schema.
            config[key] = value
        else:
            try:
                config[key] = json.loads(value)
            except json.JSONDecodeError:
                config[key] = value
    return validate_config(config)


def render_config(config):
    validate_config(config)
    return "---\n" + "\n".join(f"{k}: {json.dumps(config[k], ensure_ascii=False)}" for k in KEYS) + "\n---\n"


def setup(repo, overrides, apply=False, candidates=()):
    repo = safe_repo(repo)
    path = repo / ".agent/matt-workflow.md"
    is_git = git(repo, "rev-parse", "--show-toplevel", check=False).returncode == 0
    config = read_config(repo) if path.exists() else {
        "schema_version": 2, "task_backend": "local", "agent_directory_mode": "private",
        "default_base_branch": "main", "test_commands": [], "standards_sources": [],
        "domain_sources": [], "default_execution_agent": "auto", "assurance_level": "standard"}
    if not path.exists() and is_git:
        remote = git(repo, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD", check=False)
        if remote.returncode == 0:
            config["default_base_branch"] = remote.stdout.decode().strip().removeprefix("refs/remotes/origin/")
    config.update({k: v for k, v in overrides.items() if v is not None})
    validate_config(config)
    if git(repo, "check-ref-format", "--branch", config["default_base_branch"], check=False).returncode:
        raise TopicError("default_base_branch 非法")
    mode = config["agent_directory_mode"]
    if mode == "private" and is_git and git(repo, "ls-files", "--", ".agent").stdout:
        raise TopicError("主仓库已跟踪 .agent；请运行 migrate 或选择 shared")
    if mode == "shared" and (repo / ".agent/.git").exists():
        raise TopicError("private → shared 需要 migrate；不会删除嵌套仓库")
    report = {"config": config, "detected_standards_sources": list(candidates),
              "agent_directory": {"mode": mode}, "applied": apply}
    if apply:
        path.parent.mkdir(exist_ok=True)
        if mode == "private" and is_git and not (path.parent / ".git").exists():
            git(path.parent, "init", "--initial-branch=main")
        path.write_text(render_config(config))
    return report


def topic_path(repo, topic, archived=False):
    if not isinstance(topic, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", topic):
        raise TopicError("topic 必须是安全的目录名")
    return repo / ".agent" / ("archive" if archived else "work") / topic


def state(path):
    if not path.is_dir():
        raise TopicError(f"Topic 不存在：{path.name}")
    state_path = path / STATE_FILE
    if state_path.exists():
        try:
            value = json.loads(state_path.read_text())
        except (OSError, ValueError) as exc:
            raise TopicError(f"Topic 状态损坏：{path.name}") from exc
        if not isinstance(value, dict) or value.get("status") not in {"active", "archived"}:
            raise TopicError(f"Topic 状态无效：{path.name}")
        if value["status"] == "active" and (value.get("level") not in {"quick", "standard"}
                or not isinstance(value.get("baseline"), str) or not value.get("started_at")):
            raise TopicError(f"Topic 活动状态字段无效：{path.name}")
        return value
    tickets = list((path / "tickets").glob("*.md"))
    return {"status": "pending" if tickets else "document", "level": None}


def select_topic(repo, topic):
    if topic:
        topic_path(repo, topic)
        return topic
    work = repo / ".agent/work"
    active = [p.name for p in work.iterdir() if p.is_dir() and state(p)["status"] == "active"] if work.exists() else []
    if len(active) != 1:
        raise TopicError("请用 --topic 选择 Topic；运行 work-overview 查看候选")
    return active[0]


def full_tests(config):
    return [c for c in config["test_commands"] if not c.endswith(" *")]


def content_paths(repo):
    raw = git(repo, "ls-files", "-z", "--cached", "--others", "--exclude-standard").stdout
    return sorted({p.decode() for p in raw.split(b"\0") if p and p != b".agent" and not p.startswith(b".agent/")})


def content_id(repo):
    digest = hashlib.sha256()
    for name in content_paths(repo):
        path = repo / name
        digest.update(name.encode() + b"\0")
        if path.is_symlink():
            digest.update(b"link:" + path.readlink().as_posix().encode())
        elif path.is_file():
            digest.update(path.read_bytes())
            digest.update(str(path.stat().st_mode & 0o111).encode())
        else:
            digest.update(b"missing")
    return digest.hexdigest()


def content_dirty(repo):
    tracked = git(repo, "diff", "--quiet", "HEAD", "--", ".", ":(exclude).agent", check=False)
    if tracked.returncode not in (0, 1):
        raise TopicError("需要已有 HEAD 的 Git 仓库")
    untracked = git(repo, "ls-files", "-z", "--others", "--exclude-standard").stdout
    return bool(tracked.returncode or any(p and p != b".agent" and not p.startswith(b".agent/") for p in untracked.split(b"\0")))


def start(repo, topic, level):
    repo = safe_repo(repo)
    config = read_config(repo)
    path = topic_path(repo, topic)
    if level not in {"quick", "standard"}:
        raise TopicError("level 必须为 quick 或 standard")
    if topic_path(repo, topic, True).exists():
        raise TopicError("Topic 已归档，只读；不能覆盖")
    if path.exists() and state(path)["status"] != "document":
        raise TopicError("Topic 已 active 或待补建；请运行 topic status")
    if level == "standard" and not full_tests(config):
        raise TopicError("standard 需要非空全量测试集合（无末尾 *）")
    if content_dirty(repo):
        raise TopicError("内容不干净；请先提交或恢复内容")
    if level == "quick":
        branch = git(repo, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
        if branch.returncode:
            raise TopicError("quick start 需要当前分支，不能使用 detached HEAD")
        if branch.stdout.decode().strip() == config["default_base_branch"]:
            existing = git(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{topic}", check=False)
            git(repo, "switch", topic) if existing.returncode == 0 else git(repo, "switch", "-c", topic)
    baseline = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
    path.mkdir(parents=True, exist_ok=True)
    value = {"status": "active", "level": level, "started_at": now(), "baseline": baseline,
             "test_runs": 0}
    (path / STATE_FILE).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    return {"topic": topic, **value}


def status(repo, topic=None):
    repo = safe_repo(repo)
    read_config(repo)
    topic = select_topic(repo, topic)
    path = topic_path(repo, topic)
    archive = topic_path(repo, topic, True)
    if archive.exists():
        value = state(archive)
    else:
        value = state(path)
    command = None if value["status"] == "archived" else (
        f"workflow.py implement start --repo {shlex.quote(str(repo))} --topic {topic}" if value["status"] == "pending"
        else f"workflow.py topic complete --repo {shlex.quote(str(repo))} --topic {topic}")
    if value["status"] == "pending":
        from .ticket_implementation import next_start_command
        command = next_start_command(repo, topic)
    advisories = []
    for record in ((archive if archive.exists() else path) / "implementations").glob("*.json"):
        implementation = json.loads(record.read_text())
        for review in implementation.get("reviews", []):
            advisories.extend(f for f in review.get("result", {}).get("findings", []) if f.get("severity") == "advisory")
    return {"topic": topic, **value, "advisories": advisories, "next_command": command}


def overview(repo, topic=None):
    repo = safe_repo(repo)
    read_config(repo)
    work = repo / ".agent/work"
    paths = [topic_path(repo, topic)] if topic else sorted(work.iterdir()) if work.exists() else []
    return {"topics": [{"topic": p.name, **state(p)} for p in paths if p.is_dir()
                       and not topic_path(repo, p.name, True).exists()]}


def summary_headings(text):
    """Yield actual ATX headings and their lines, excluding fenced examples."""
    fence = None
    for index, line in enumerate(text.splitlines()):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            if (marker and marker[1][0] == fence[0] and len(marker[1]) >= fence[1]
                    and not marker[2].strip()):
                fence = None
            continue
        if marker:
            if marker[1][0] == "~" or "`" not in marker[2]:
                fence = (marker[1][0], len(marker[1]))
            continue
        heading = re.match(r"^ {0,3}#{1,6}[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$", line)
        if heading:
            yield heading[1], index


def check_summary(path, quick):
    summary = path / "deliveries" / f"deliveries-{path.name}-01.md"
    if not summary.is_file():
        raise TopicError(f"缺少交付摘要：{summary}")
    text = summary.read_text()
    sections = {title for title, _ in summary_headings(text)}
    missing = set(HEADINGS + (("验收对照",) if quick else ())) - sections
    if missing:
        raise TopicError(f"交付摘要缺少章节：{', '.join(sorted(missing))}")
    return summary


def preflight_commit(repo, config):
    if Path(git(repo, "rev-parse", "--show-toplevel").stdout.decode().strip()).resolve() != repo:
        raise TopicError("repo 必须是 Git 仓库根目录")
    if config["agent_directory_mode"] == "private":
        if git(repo, "ls-files", "--", ".agent").stdout:
            raise TopicError("private 主仓库不得跟踪 .agent；请 migrate")
        if not (repo / ".agent/.git").is_dir():
            raise TopicError("private 缺少嵌套仓库；请 setup --apply")
        targets = [repo, repo / ".agent"]
    else:
        if (repo / ".agent/.git").exists():
            raise TopicError("shared 不能有嵌套仓库；请 migrate")
        targets = [repo]
    for target in targets:
        for key in ("user.name", "user.email"):
            if not git(target, "config", "--get", key, check=False).stdout.strip():
                raise TopicError(f"提交前请配置 Git {key}：{target}")
        if git(target, "ls-files", "--unmerged").stdout:
            raise TopicError("存在 Git 合并冲突；请先解决")


def complete(repo, topic=None):
    repo = safe_repo(repo)
    config = read_config(repo)
    topic = select_topic(repo, topic)
    path, archive = topic_path(repo, topic), topic_path(repo, topic, True)
    if archive.exists():
        raise TopicError("Topic 已归档，只读；不能覆盖")
    value = state(path)
    if value["status"] == "pending":
        raise TopicError("待补建 Topic 请先运行 implement start")
    quick = value.get("level") == "quick"
    if value.get("level") == "standard":
        if not full_tests(config):
            raise TopicError("standard 需要非空全量测试集合")
        if not list((path / "tickets").glob("*.md")):
            raise TopicError("standard 没有 Ticket；请拆分 Ticket 或 topic abandon")
        raise TopicError("standard 收尾由后续实施 Ticket 接入；请运行 implement status")
    summary = check_summary(path, True) if quick else None
    preflight_commit(repo, config)
    dirty = content_dirty(repo)
    if quick and dirty and value.get("code_commit"):
        raise TopicError("quick 代码已经提交；新的内容改动请另建 Topic，或恢复后重试收尾")
    tests = full_tests(config) if quick else []
    for command in tests:
        before = content_id(repo)
        value["test_runs"] = value.get("test_runs", 0) + 1
        (path / STATE_FILE).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        try:
            result = subprocess.run(shlex.split(command), cwd=repo, capture_output=True, text=True)
        except OSError as exc:
            raise TopicError(f"测试命令无法执行：{command}：{exc}") from exc
        if result.returncode:
            raise TopicError(f"测试失败：{command}\n退出码：{result.returncode}\n{(result.stdout + result.stderr)[-4000:]}")
        if content_id(repo) != before:
            raise TopicError(f"测试改变了内容：{command}；请检查后重新运行 topic complete")
    original_summary = summary.read_bytes() if summary else None
    finished = now()
    record = {"kind": "quick" if quick else "topic", "topic": topic, "ticket": None,
              "level": value.get("level"), "started_at": value.get("started_at"),
              "finished_at": finished, "outcome": "complete",
              "test_runs": value.get("test_runs", 0) if quick else None,
              "review_rounds": None, "findings": {"blocking": None, "advisory": None},
              "repair_rounds": None, "needs_user_count": None, "command_errors": None,
              "reviewer_provenance": "self" if quick else None,
              "tests_configured": bool(tests) if quick else None}
    metrics = repo / ".agent/metrics.jsonl"
    original_metrics = metrics.read_bytes() if metrics.exists() else None
    private = config["agent_directory_mode"] == "private"
    # In private mode commit content first. If the metadata commit fails,
    # record that commit so recovery cannot create a second quick code commit.
    if private and dirty and quick:
        git(repo, "add", "--all", "--", ".", ":(exclude).agent")
        git(repo, "commit", "-m", f"Topic {topic} quick implementation")
        value["code_commit"] = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
        (path / STATE_FILE).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    active_value = dict(value)
    try:
        if quick and not tests:
            text = summary.read_text()
            lines = text.splitlines()
            index = next(index for title, index in summary_headings(text) if title == "测试结果")
            lines[index] += "\n\n未配置测试"
            summary.write_text("\n".join(lines) + "\n")
        value.update(status="archived", outcome="complete", finished_at=finished, reason="完成")
        (path / STATE_FILE).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        with metrics.open("a") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        archive.parent.mkdir(parents=True, exist_ok=True)
        if archive.exists():
            raise TopicError("归档目录已经存在；不能覆盖")
        path.rename(archive)
        if private:
            agent = repo / ".agent"
            git(agent, "add", "--force", "--all", "--", ".")
            git(agent, "commit", "-m", f"Topic {topic} complete")
        else:
            git(repo, "add", "--force", "--all", "--", ".agent")
            if quick and dirty:
                git(repo, "add", "--all", "--", ".", ":(exclude).agent")
            # A document Topic only commits metadata, preserving unrelated content.
            git(repo, "commit", "--only", "-m", f"Topic {topic} complete", "--",
                "." if quick and dirty else ".agent")
    except (TopicError, OSError):
        # Restore the active Topic and remove the uncommitted metric. Content
        # and the user's staged changes are never discarded.
        if archive.exists() and not path.exists():
            archive.rename(path)
        (path / STATE_FILE).write_text(json.dumps(active_value, ensure_ascii=False, indent=2) + "\n")
        if original_metrics is None:
            metrics.unlink(missing_ok=True)
        else:
            metrics.write_bytes(original_metrics)
        if summary:
            summary.write_bytes(original_summary)
        raise
    return {"topic": topic, **value, "tests_configured": bool(tests) if quick else None}
