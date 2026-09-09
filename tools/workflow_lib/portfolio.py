"""Strict portfolio contract for source Skills and their cross-file graph."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .composition import CompositionManifest, load_composition_manifest


class PortfolioError(RuntimeError):
    """Raised when the Skill portfolio is incomplete or internally inconsistent."""


_SKILL_NAME = re.compile(r"my-[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_CALL_MACRO = re.compile(r"\{\{skill-call:(my-[a-z0-9]+(?:-[a-z0-9]+)*)\}\}")
_RAW_HOST_CALL = re.compile(r"(?<![A-Za-z0-9_-])(?:/|\$)my-[a-z0-9-]+")
_DISCOVERABILITY = {"routed", "specialist", "administrative", "internal"}
_ROLES = {"entry", "method", "handoff", "review", "admin"}
_CRITICALITY = {"critical", "standard"}
_EVIDENCE_LAYERS = {"static", "deterministic", "fresh_agent", "real_project"}


@dataclass(frozen=True)
class PortfolioEntry:
    category: str
    discoverability: str
    roles: frozenset[str]
    criticality: str
    evidence: dict[str, object]


@dataclass(frozen=True)
class PortfolioManifest:
    version: int
    skills: dict[str, PortfolioEntry]


def _fail(location: str, message: str) -> PortfolioError:
    return PortfolioError(f"portfolio {location}: {message}")


def _validate_evidence(skill: str, value: object) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != _EVIDENCE_LAYERS:
        raise _fail(f"{skill}.evidence", "必须精确声明四个证据层")
    result: dict[str, object] = {}
    for layer, record in value.items():
        if not isinstance(record, dict):
            raise _fail(f"{skill}.evidence.{layer}", "必须是对象")
        if set(record) == {"cases"}:
            cases = record["cases"]
            if (
                not isinstance(cases, list)
                or not cases
                or any(not isinstance(case, str) or not case.strip() for case in cases)
                or len(cases) != len(set(cases))
            ):
                raise _fail(f"{skill}.evidence.{layer}.cases", "必须是非空且不重复的 case id 数组")
        elif set(record) == {"exemption"}:
            exemption = record["exemption"]
            required = {"reason", "risk", "release_condition"}
            if not isinstance(exemption, dict) or set(exemption) != required:
                raise _fail(
                    f"{skill}.evidence.{layer}.exemption",
                    "必须精确包含 reason、risk、release_condition",
                )
            if any(
                not isinstance(exemption[field], str) or not exemption[field].strip()
                for field in required
            ):
                raise _fail(f"{skill}.evidence.{layer}.exemption", "字段不能为空")
        else:
            raise _fail(f"{skill}.evidence.{layer}", "只能声明 cases 或 exemption")
        result[layer] = record
    return result


def load_portfolio_manifest(path: Path) -> PortfolioManifest:
    """Load the strict version-1 portfolio manifest."""
    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise PortfolioError(f"portfolio 清单无法读取：{path}") from exc
    if not isinstance(raw, dict) or set(raw) != {"version", "skills"}:
        raise PortfolioError("portfolio 清单字段必须为 version、skills")
    if raw["version"] != 1:
        raise PortfolioError(f"不支持的 portfolio 清单版本：{raw['version']!r}")
    if not isinstance(raw["skills"], dict):
        raise PortfolioError("portfolio skills 必须是对象")

    entries: dict[str, PortfolioEntry] = {}
    expected_fields = {
        "category",
        "discoverability",
        "roles",
        "criticality",
        "evidence",
    }
    for name, value in raw["skills"].items():
        if not isinstance(name, str) or not _SKILL_NAME.fullmatch(name):
            raise _fail(str(name), "Skill 名称不合法")
        if not isinstance(value, dict) or set(value) != expected_fields:
            raise _fail(name, "字段必须为 category、discoverability、roles、criticality、evidence")
        category = value["category"]
        discoverability = value["discoverability"]
        roles = value["roles"]
        criticality = value["criticality"]
        if not isinstance(category, str) or not category.strip():
            raise _fail(f"{name}.category", "不能为空")
        if discoverability not in _DISCOVERABILITY:
            raise _fail(f"{name}.discoverability", "分类不合法")
        if (
            not isinstance(roles, list)
            or not roles
            or any(role not in _ROLES for role in roles)
            or len(roles) != len(set(roles))
        ):
            raise _fail(f"{name}.roles", "必须是非空且不重复的合法 role 数组")
        if discoverability == "internal" and set(roles) != {"method"}:
            raise _fail(f"{name}.roles", "internal Skill 必须且只能具有 method role")
        if criticality not in _CRITICALITY:
            raise _fail(f"{name}.criticality", "必须是 critical 或 standard")
        entries[name] = PortfolioEntry(
            category=category,
            discoverability=discoverability,
            roles=frozenset(roles),
            criticality=criticality,
            evidence=_validate_evidence(name, value["evidence"]),
        )
    return PortfolioManifest(version=1, skills=entries)


def _validate_graph(
    root: Path, portfolio: PortfolioManifest, composition: CompositionManifest
) -> None:
    entries = portfolio.skills
    for caller, edges in composition.callers.items():
        if caller not in entries:
            raise _fail(caller, "composition caller 未登记")
        caller_entry = entries[caller]
        if not caller_entry.roles & {"entry", "review"}:
            raise _fail(caller, "composition caller 必须具有 entry 或 review role")
        body = (root / "skills" / caller / "SKILL.md").read_text()
        for edge in edges:
            if edge.skill not in entries:
                raise _fail(caller, f"composition target 未登记：{edge.skill}")
            target = entries[edge.skill]
            pointer = f"references/composed/{edge.skill}/COMPOSED.md"
            if pointer not in body:
                raise _fail(caller, f"缺少 {edge.skill} 的 composed-body 指针")
            if edge.kind == "method" and "method" not in target.roles:
                raise _fail(edge.skill, "method edge 的目标必须具有 method role")
            if edge.kind == "handoff":
                if "handoff" not in target.roles:
                    raise _fail(edge.skill, "handoff edge 的目标必须具有 handoff role")
                if f"{{{{skill-call:{edge.skill}}}}}" not in body:
                    raise _fail(caller, f"handoff edge 缺少 {edge.skill} 调用宏")

    for router, route_targets in composition.routable_entries.items():
        if router not in entries:
            raise _fail(router, "router 未登记")
        if "entry" not in entries[router].roles:
            raise _fail(router, "router 必须具有 entry role")
        body = (root / "skills" / router / "SKILL.md").read_text()
        macros = set(_CALL_MACRO.findall(body))
        routed = set(route_targets)
        if macros != routed:
            missing = sorted(routed - macros)
            undeclared = sorted(macros - routed)
            raise _fail(
                router,
                f"调用宏与 routed edges 不一致；缺少={missing} 未声明={undeclared}",
            )
        for target in routed:
            if target not in entries:
                raise _fail(router, f"route target 未登记：{target}")
            if entries[target].discoverability != "routed":
                raise _fail(target, "router 目标必须标记 discoverability=routed")


def _validate_evidence_case_ids(root: Path, portfolio: PortfolioManifest) -> None:
    deterministic: dict[str, set[str]] = {}
    scenarios_dir = root / "evals" / "scenarios"
    behavior_path = root / "evals" / "agent-smokes" / "astra-behavior-suite.json"
    # The build preflight owns missing-eval diagnostics. When the registries
    # exist, portfolio verifies that evidence claims point to real cases.
    if not scenarios_dir.is_dir() or not behavior_path.is_file():
        return
    for path in sorted(scenarios_dir.glob("*.json")):
        try:
            raw = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise PortfolioError(f"portfolio 无法读取 deterministic case：{path}") from exc
        identifier = raw.get("id") if isinstance(raw, dict) else None
        skills = raw.get("skills") if isinstance(raw, dict) else None
        if isinstance(identifier, str) and isinstance(skills, list):
            deterministic[identifier] = {
                skill for skill in skills if isinstance(skill, str)
            }

    try:
        behavior_raw = json.loads(behavior_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise PortfolioError(
            f"portfolio 无法读取 fresh-agent suite：{behavior_path}"
        ) from exc
    behavior_cases = behavior_raw.get("cases") if isinstance(behavior_raw, dict) else None
    fresh_ids = {
        case["id"]
        for case in behavior_cases or []
        if isinstance(case, dict) and isinstance(case.get("id"), str)
    }

    for skill, entry in portfolio.skills.items():
        deterministic_record = entry.evidence["deterministic"]
        if "cases" in deterministic_record:
            for identifier in deterministic_record["cases"]:
                if identifier not in deterministic:
                    raise _fail(skill, f"引用未知 deterministic case：{identifier}")
                if skill not in deterministic[identifier]:
                    raise _fail(
                        skill,
                        f"deterministic case 未声明覆盖该 Skill：{identifier}",
                    )
        fresh_record = entry.evidence["fresh_agent"]
        if "cases" in fresh_record:
            for identifier in fresh_record["cases"]:
                if identifier not in fresh_ids:
                    raise _fail(skill, f"引用未知 fresh-agent case：{identifier}")


def _validate_portable_prose(root: Path) -> None:
    for markdown in sorted((root / "skills").glob("**/*.md")):
        match = _RAW_HOST_CALL.search(markdown.read_text())
        if match:
            raise _fail(
                str(markdown.relative_to(root)),
                f"可移植 prose 含宿主专属调用：{match.group(0)}",
            )


def validate_portfolio(root: Path) -> PortfolioManifest:
    """Validate directory inventory, roles, routing, evidence, and portable prose."""
    source_root = root.resolve()
    manifest = load_portfolio_manifest(source_root / "portfolio" / "manifest.json")
    skill_names = {
        path.name for path in (source_root / "skills").iterdir() if path.is_dir()
    }
    registered = set(manifest.skills)
    if skill_names != registered:
        raise PortfolioError(
            "portfolio 与 skills 目录不一致；"
            f"未登记={sorted(skill_names - registered)} "
            f"无目录={sorted(registered - skill_names)}"
        )
    composition = load_composition_manifest(
        source_root / "composition" / "manifest.json"
    )
    _validate_graph(source_root, manifest, composition)
    _validate_evidence_case_ids(source_root, manifest)
    _validate_portable_prose(source_root)
    return manifest
