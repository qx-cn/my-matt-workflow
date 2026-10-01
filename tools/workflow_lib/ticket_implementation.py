"""Local v2 Ticket admission, execution briefing, and content-bound tests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import shutil
import uuid

from . import topic_service as topics
from .rules import resolve_rules
from .tickets import (TicketError, _admission_fields, acceptance_items, frontmatter,
                      ticket_definition, validate_ready_ticket)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def ticket_path(repo, identifier):
    match = re.fullmatch(r"([a-zA-Z0-9][a-zA-Z0-9_-]*)-([0-9]{2})", identifier or "")
    if not match or int(match[2]) == 0:
        raise topics.TopicError("ticket id 必须为 <topic>-<NN>，NN 从 01 开始")
    topic = match[1]
    from .migration import require_topic
    require_topic(topics.topic_path(repo, topic))
    if topics.topic_path(repo, topic, True).exists():
        raise topics.TopicError("Topic 已归档，只读")
    path = topics.topic_path(repo, topic) / "tickets" / f"tickets-{identifier}.md"
    if not path.is_file():
        raise topics.TopicError(f"Ticket 不存在：{identifier}；请运行 topic status --topic {topic}")
    return topic, path


def records(repo, topic):
    result = {}
    for path in sorted((topics.topic_path(repo, topic) / "tickets").glob("*.md")):
        value = frontmatter(path)
        identifier = value.get("id")
        if not isinstance(identifier, str) or identifier in result:
            raise topics.TopicError(f"Ticket id 缺失或重复：{path}")
        owner, expected = ticket_path(repo, identifier)
        if owner != topic or expected != path:
            raise topics.TopicError(f"Ticket id 与目录/文件名不一致：{path}")
        result[identifier] = (path, value)
    return result


def argv_matches(argv, configured):
    for command in configured:
        prefix = command.endswith(" *")
        candidate = shlex.split(command[:-2] if prefix else command)
        if argv == candidate or prefix and argv[:len(candidate)] == candidate:
            return True
    return False


def validate(repo, path, config=None):
    repo = topics.safe_repo(repo)
    config = config or topics.read_config(repo)
    path = Path(path).resolve()
    value = frontmatter(path)
    topic, expected = ticket_path(repo, value.get("id"))
    if path != expected:
        raise topics.TopicError("Ticket 必须位于所选 repo 的规范路径")
    statuses = {key: str(v[1].get("status")) for key, v in records(repo, topic).items()}
    if value.get("status") not in {"ready-for-agent", "implementing", "needs-user", "complete"}:
        raise topics.TopicError("旧 Ticket 状态；请运行 migrate")
    commands = value.get("test_commands")
    if not isinstance(commands, list) or not commands or any(not isinstance(c, str) or not c.strip() for c in commands):
        raise topics.TopicError("Ticket test_commands 必须是非空字符串列表")
    for command in commands:
        try:
            argv = shlex.split(command)
        except ValueError as exc:
            raise topics.TopicError(f"test_commands：{exc}") from exc
        if not argv or any(token.lower() in {'todo','tbd','<command>','<test-command>'} for token in argv):
            raise topics.TopicError(f'test_commands 占位符不可执行：{command}')
        executable = (repo / argv[0]) if '/' in argv[0] else None
        if (executable and not executable.is_file()) or (not executable and not shutil.which(argv[0])):
            raise topics.TopicError(f'test_commands 无法执行：{argv[0]}')
        if not argv or not argv_matches(argv, config["test_commands"]):
            raise topics.TopicError(f"test_commands 未匹配配置：{command}")
    if value["status"] == "ready-for-agent":
        report = validate_ready_ticket(path, dependency_statuses=statuses)
    else:
        _admission_fields({**value, "claimed_by": ""}, path)
        report = {"status": value["status"], "path": str(path)}
    if not isinstance(value.get("title"), str) or not value["title"].strip():
        raise topics.TopicError("Ticket title 必须非空")
    try:
        sequence = int(str(value.get("sequence")))
    except ValueError as exc:
        raise topics.TopicError("Ticket sequence 必须为正整数") from exc
    if sequence <= 0:
        raise topics.TopicError("Ticket sequence 必须为正整数")
    for dependency in value["blocked_by"]:
        if statuses.get(dependency) != "complete":
            raise topics.TopicError(f"Ticket 依赖尚未完成或不存在：{dependency}")
    return {**report, "ticket": value["id"], "topic": topic}


def select(repo, ticket=None, topic=None):
    if ticket:
        owner, path = ticket_path(repo, ticket)
        if topic and owner != topic:
            raise topics.TopicError("ticket 与 --topic 不属于同一 Topic")
        return owner, path
    topic = topics.select_topic(repo, topic)
    active = [p for p, value in records(repo, topic).values() if value.get("status") in {"implementing", "needs-user"}]
    if len(active) != 1:
        raise topics.TopicError(f"没有唯一实施中 Ticket；请运行 topic status --topic {topic}")
    return topic, active[0]


def record_path(repo, topic, identifier):
    return topics.topic_path(repo, topic) / "implementations" / f"{identifier}.json"


def definition(repo, path):
    ticket = frontmatter(path)
    spec = repo / str(ticket["spec_ref"])
    return {"ticket": ticket_definition(path), "spec_sha256": hashlib.sha256(spec.read_bytes()).hexdigest()}


def spec_acceptance(text):
    """Extract tagged acceptance; retain older Spec formats without rewriting."""
    output = []
    collecting = False
    for line in text.splitlines():
        if re.match(r"^- (?:AC-\d+|\[[ xX]\])", line):
            collecting = True
        elif collecting and line.strip() and not line[:1].isspace():
            collecting = False
        if collecting:
            output.append(line)
    if not output:
        if not text.strip():
            raise topics.TopicError("Spec 内容为空")
        # v1 accepted ordinary prose and bullets. Carry the original document
        # into the briefing rather than guessing which lines are acceptance.
        return text
    return "\n".join(output)


def rule_material(repo, config, value, agent):
    rules = resolve_rules(repo, agent, value["rule_scope"])
    sources = []
    references = [*value["rule_sources"], *config["standards_sources"], *config["domain_sources"],
                  *(r["source"] for r in rules)]
    for ref in dict.fromkeys(references):
        source = repo / ref
        if Path(ref).is_absolute() or ".." in Path(ref).parts or not source.is_file() or not source.resolve().is_relative_to(repo):
            raise topics.TopicError(f"规则来源无效：{ref}")
        sources.append(f"### {ref}\n{source.read_text()}")
    return rules, sources


def admission_inputs(repo, path, topic):
    from . import batches
    return {"batch_plan": batches.read(repo,topic) if batches.enabled(repo,topic) else None, "config": topics.read_config(repo), "definition": definition(repo, path),
            "tickets": {key: value for key, (_, value) in records(repo, topic).items()},
            "topic": topics.state(topics.topic_path(repo, topic))}


def section_text(text, title):
    headings=list(topics.summary_headings(text))
    lines=text.splitlines()
    for heading,index in headings:
        if heading == title:
            level=len(lines[index].lstrip().split()[0])
            end=next((j for _,j in headings if j>index and
                      len(lines[j].lstrip().split()[0])<=level),len(lines))
            return '\n'.join(lines[index+1:end]).strip()
    return ''


def start(repo, ticket=None, topic=None, agent=None):
    repo = topics.safe_repo(repo)
    config = topics.read_config(repo)
    topic, path = select(repo, ticket, topic)
    validate(repo, path, config)
    value = frontmatter(path)
    if value["status"] != "ready-for-agent":
        raise topics.TopicError("implement start 只接受 ready-for-agent")
    if any(v.get("status") in {"implementing", "needs-user"} for _, v in records(repo, topic).values()):
        raise topics.TopicError("同 Topic 已有 implementing/needs-user Ticket")
    root = topics.topic_path(repo, topic)
    state = topics.state(root)
    if state["status"] not in {"active", "pending"}:
        raise topics.TopicError("文档 Topic 请先 topic start --level standard")
    if state.get("level") == "quick":
        raise topics.TopicError("quick Topic 不允许 implement start")
    if not topics.full_tests(config):
        raise topics.TopicError("standard 需要非空全量测试集合")
    if topics.content_dirty(repo):
        raise topics.TopicError("内容不干净；请先提交或恢复内容")
    requested = value["execution_agent"]
    agent = agent or (requested if requested != "auto" else config["default_execution_agent"])
    if agent == "auto":
        raise topics.TopicError("auto 尚未绑定宿主；请用 --agent codex|cursor|claude")
    if requested != "auto" and agent != requested:
        raise topics.TopicError("--agent 与 Ticket execution_agent 不一致")
    rules, sources = rule_material(repo, config, value, agent)
    spec_section = spec_acceptance((repo / value["spec_ref"]).read_text())
    original_inputs = admission_inputs(repo, path, topic)
    pending = state["status"] == "pending"
    base_branch = config["default_base_branch"]
    if pending:
        topics.git(repo, "merge-base", "HEAD", base_branch)
    if not state.get("implementation_started"):
        branch = topics.git(repo, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
        if branch.returncode:
            raise topics.TopicError("implement start 需要当前分支")
        if branch.stdout.decode().strip() == base_branch:
            exists = topics.git(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{topic}", check=False)
            topics.git(repo, "switch", topic) if exists.returncode == 0 else topics.git(repo, "switch", "-c", topic)
    topics.safe_repo(repo)
    if admission_inputs(repo, path, topic) != original_inputs:
        raise topics.TopicError("分支切换后准入输入已变化；保留目标分支原文，请运行 topic status 后重新选择 Ticket")
    validate(repo, path, config)
    if topics.content_dirty(repo):
        raise topics.TopicError("分支切换后内容不干净；不会认领 Ticket")
    rules, sources = rule_material(repo, config, value, agent)
    baseline = topics.git(repo, "rev-parse", "HEAD").stdout.decode().strip()
    if pending:
        fork = topics.git(repo, "merge-base", "HEAD", base_branch).stdout.decode().strip()
        state = {"status": "active", "level": "standard", "started_at": topics.now(), "baseline": fork, "test_runs": 0}
    from . import batches
    batch_id = batches.before_start(repo, topic, value['id'])
    unit = {"ticket": value["id"], "topic": topic, "baseline": baseline, "started_at": topics.now(),
            "execution_agent": agent, "definition": definition(repo, path), "tests": []}
    if batch_id:
        unit['batch_id'] = batch_id
        unit['implementation_session_id'] = batches.read(repo,topic)['implementation_session_id']
    brief = root / "briefings" / f"briefing-{value['id']}.md"
    parts = [f"# {value['id']} 执行简报", "## Ticket", path.read_text(),
             "## Spec 验收", spec_section,
             "## 已完成前置 Ticket", "## 适用规则", json.dumps(rules, ensure_ascii=False, indent=2)]
    for dependency in value["blocked_by"]:
        previous = record_path(repo, topic, dependency)
        prior = json.loads(previous.read_text()) if previous.exists() else {}
        commit = prior.get("commit")
        if not commit:
            log = topics.git(repo, "log", "--format=%H", f"--grep=^{dependency}:", "-1").stdout.decode().strip()
            commit = log or None
        changed = topics.git(repo, "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", commit).stdout.decode() if commit else "不可观察：未记录提交\n"
        impact=section_text(prior.get('self_review',{}).get('text',''),'影响面')
        parts.insert(6, f"### {dependency}\n提交：{commit}\n改动文件：\n{changed}\n契约与消费者（前置 Ticket 声明）：\n{impact or '未记录；实施者须自行核实'}")
    touchpoints=value.get('touchpoints') or section_text(path.read_text(),'触点提示') or '无：Ticket 未提供触点提示'
    parts += ['## 非约束性触点提示',json.dumps(touchpoints,ensure_ascii=False) if isinstance(touchpoints,list) else str(touchpoints)]
    if batch_id:
        _, batch=batches.active(repo,topic,batch_id)
        parts.append('## 同批次已提交 Ticket 的影响面（实施者声明，待核实）')
        for identifier in batch['tickets']:
            if identifier != value['id'] and records(repo,topic)[identifier][1]['status']=='complete':
                previous=record_path(repo,topic,identifier)
                previous_unit=json.loads(previous.read_text()) if previous.exists() else {}
                impact=section_text(previous_unit.get('self_review',{}).get('text',''),'影响面')
                parts.append(f"### {identifier}\n{impact or '未记录；自行核实'}")
    parts += sources + ["## 测试命令", "\n".join(value["test_commands"]),
                        "## 实施计划", "Agent 动手前补写：文件和接口；现状断言→代码依据；契约/共享函数/表结构/配置/锁/错误码→调用方/消费者和兼容、数据、并发、权限、性能结论；每项验收各自对应测试断言。事实冲突按 spec-challenge 停止，不任选一边实现。"]
    brief.parent.mkdir(parents=True, exist_ok=True)
    brief.write_text("\n\n".join(parts) + "\n")
    unit["briefing"] = str(brief)
    write_json(record_path(repo, topic, value["id"]), unit)
    state["implementation_started"] = True
    write_json(root / topics.STATE_FILE, state)
    text = re.sub(r"^status:.*$", "status: implementing", path.read_text(), count=1, flags=re.M)
    text = re.sub(r"^claimed_by:.*$", f"claimed_by: {agent}", text, count=1, flags=re.M)
    path.write_text(text)
    return {"ticket": value["id"], "topic": topic, "baseline": baseline, "briefing": str(brief)}


def load_active(repo, ticket, topic, check_commands=True):
    repo = topics.safe_repo(repo)
    config = topics.read_config(repo)
    topic, path = select(repo, ticket, topic)
    value = frontmatter(path)
    if value.get("status") not in {"implementing", "needs-user"}:
        raise topics.TopicError(f"Ticket 不在实施中；请运行 topic status --topic {topic}")
    record = record_path(repo, topic, value["id"])
    if not record.is_file():
        raise topics.TopicError("缺少新实施记录；请运行 migrate")
    unit = json.loads(record.read_text())
    if check_commands and value.get("test_commands") != unit["definition"]["ticket"]["metadata"].get("test_commands"):
        raise topics.TopicError("test_commands 与定义快照不同；恢复原值，或用户确认修订后 resolve --reopen")
    if check_commands:
        validate(repo, path, config)
    return repo, config, topic, path, unit, record


def tests_passed(repo, unit, commands=None):
    content = topics.content_id(repo)
    commands = commands if commands is not None else [shlex.split(c) for c in unit["definition"]["ticket"]["metadata"]["test_commands"]]
    run = unit.get("test_run")
    # Old per-command history cannot prove one whole declaration completed.
    if not run or not run["completed"] or run["commands"] != commands:
        return False
    entries = [t for t in unit["tests"] if not t["progress"] and t.get("run_id") == run["id"]]
    return len(entries) == len(commands) and all(
        t.get("command_index") == index and t["argv"] == command
        and t["content_id"] == content and t["exit_code"] == 0
        for index, (t, command) in enumerate(zip(entries, commands)))


def test(repo, ticket=None, topic=None, argv=None):
    repo, config, topic, path, unit, record = load_active(repo, ticket, topic)
    progress = bool(argv)
    if progress and not argv_matches(argv, config["test_commands"]):
        raise topics.TopicError("测试 argv 未匹配配置 test_commands")
    commands = [argv] if progress else [shlex.split(c) for c in frontmatter(path)["test_commands"]]
    outputs = run_test_batch(repo, unit, record, commands, progress)
    return {"ticket": unit["ticket"], "topic": topic, "progress": progress,
            "tests": outputs, "tests_passed": tests_passed(repo, unit)}


def run_test_batch(repo, unit, record, commands, progress=False):
    run_id = uuid.uuid4().hex
    if not progress:
        # Persist before executing: a crash must invalidate previous success.
        unit["test_run"] = {"id": run_id, "commands": commands, "completed": False}
        write_json(record, unit)
    outputs = []
    failed = False
    for index, command in enumerate(commands):
        content = topics.content_id(repo)
        try:
            result = subprocess.run(command, cwd=repo, capture_output=True, text=True, errors="replace")
            exit_code, output = result.returncode, result.stdout + result.stderr
        except OSError as exc:
            exit_code, output = 127, str(exc)
        entry = {"argv": command, "exit_code": exit_code, "content_id": content,
                 "run_id": run_id, "command_index": index,
                 "progress": progress, "finished_at": topics.now(), "output_tail": output[-4000:]}
        unit["tests"].append(entry)
        write_json(record, unit)
        outputs.append(entry)
        failed = failed or exit_code != 0
    if not progress:
        unit["test_run"]["completed"] = True
        write_json(record, unit)
    if failed:
        messages = [f"测试失败：{shlex.join(t['argv'])}\n退出码：{t['exit_code']}\n{t['output_tail']}" for t in outputs if t["exit_code"]]
        raise topics.TopicError("\n".join(messages))
    return outputs


def status(repo, ticket=None, topic=None):
    repo, config, topic, path, unit, _ = load_active(repo, ticket, topic, check_commands=False)
    passed = tests_passed(repo, unit)
    definition_changed = definition(repo, path) != unit["definition"]
    command = "review" if passed else "test"
    if unit.get("batch_id") and passed:
        command = "self-review" if unit.get("self_review",{}).get("content_id") != topics.content_id(repo) else "finish"
    if passed and (not unit.get("batch_id") or unit.get("reviews")):
        from . import ticket_review
        try:
            ticket_review.require_pass(repo, config, topic, path, unit)
            command = "finish"
        except (topics.TopicError, OSError, ValueError):
            command = "review"
    if passed:
        from . import batches
        try:batches.require_self(repo,unit)
        except topics.TopicError:command='self-review'
    next_command = f"workflow.py implement {command} --repo {shlex.quote(str(repo))} --ticket {unit['ticket']}"
    if command == 'review' and unit.get('high_risk_reason'):
        next_command += ' --reason '+shlex.quote(unit['high_risk_reason'])
    if frontmatter(path)['status'] == 'needs-user' and passed and command != 'self-review':
        next_command = f"workflow.py resolve --repo {shlex.quote(str(repo))} --ticket {unit['ticket']} --accept --reason '<理由>'"
    if definition_changed:
        next_command = f"workflow.py resolve --repo {shlex.quote(str(repo))} --ticket {unit['ticket']} --reopen --reason '<理由>'"
    return {"ticket": unit["ticket"], "topic": topic, "status": frontmatter(path)["status"],
            "baseline": unit["baseline"], "tests_passed": passed, "definition_changed": definition_changed,
            "stop_reason": unit.get("stop_reason"),
            "decisions_needed": [dict(finding=f, decision="请决定修订 Spec、接受风险或按原 Spec 继续") for r in unit.get("reviews", [])[-1:] for f in r.get("result", {}).get("findings", []) if f.get("view") == "spec-challenge"], "rounds_used": len(unit.get("reviews", [])),
            "decisions": unit.get("decisions", []),
            "next_command": next_command}


def next_start_command(repo, topic):
    for path, value in records(repo, topic).values():
        try:
            if value.get("status") == "ready-for-agent":
                validate(repo, path)
                return f"workflow.py implement start --repo {shlex.quote(str(repo))} --ticket {value['id']}"
        except (topics.TopicError, TicketError):
            continue
    return f"workflow.py topic complete --repo {shlex.quote(str(repo))} --topic {topic}"
