"""Governance checks for shared rule and protocol documents."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from .resources import SharedResourceManifest


class ResourceGovernanceError(RuntimeError):
    """Raised when a shared document lacks its required review mechanism."""


def _relative_file(value: object, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ResourceGovernanceError(f"{location}: 路径不能为空")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ResourceGovernanceError(f"{location}: 路径必须位于仓库内：{value}")
    return value


def _shared_markdown(root: Path) -> set[str]:
    documents = {
        str(path.relative_to(root))
        for path in (root / "resources").rglob("*.md")
        if path.is_file()
    }
    documents.update(
        str(path.relative_to(root))
        for path in (root / "policies").glob("*.md")
        if path.is_file()
    )
    return documents


def _resource_for_document(
    root: Path,
    manifest: SharedResourceManifest,
    document: str,
):
    target = (root / document).resolve()
    matches = []
    for resource in manifest.resources.values():
        source = (root / resource.source).resolve()
        if (resource.source_is_dir and target.is_relative_to(source)) or target == source:
            matches.append(resource)
    if len(matches) != 1:
        raise ResourceGovernanceError(
            f"{document}: 必须且只能属于一个 resources/manifest.json 条目"
        )
    return matches[0]


def _test_exists(root: Path, selector: object, location: str) -> None:
    if not isinstance(selector, str) or selector.count("::") != 1:
        raise ResourceGovernanceError(
            f"{location}: validation 必须是 <test-file>::<Class.method>"
        )
    raw_path, qualified_name = selector.split("::")
    test_path = _relative_file(raw_path, f"{location}.validation")
    parts = qualified_name.split(".")
    if len(parts) != 2 or not all(parts):
        raise ResourceGovernanceError(
            f"{location}: validation 必须指向 Class.method"
        )
    path = root / test_path
    if not path.is_file():
        raise ResourceGovernanceError(f"{location}: validation 文件不存在：{test_path}")
    try:
        tree = ast.parse(path.read_text())
    except (OSError, SyntaxError) as exc:
        raise ResourceGovernanceError(
            f"{location}: validation 文件无法解析：{test_path}"
        ) from exc
    class_name, method_name = parts
    exists = any(
        isinstance(node, ast.ClassDef)
        and node.name == class_name
        and any(
            isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            and child.name == method_name
            for child in node.body
        )
        for node in tree.body
    )
    if not exists:
        raise ResourceGovernanceError(
            f"{location}: validation 不存在：{selector}"
        )


def validate_resource_governance(
    root: Path,
    manifest: SharedResourceManifest,
    governance_path: Path,
) -> None:
    """Require every shared Markdown document to have a reviewer or test."""
    try:
        raw = json.loads(governance_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ResourceGovernanceError(
            f"共享资源治理清单无法读取：{governance_path}"
        ) from exc
    if not isinstance(raw, dict) or set(raw) != {"version", "documents"}:
        raise ResourceGovernanceError("治理清单字段必须为 version、documents")
    if raw["version"] != 1 or not isinstance(raw["documents"], dict):
        raise ResourceGovernanceError("治理清单必须使用 version 1 且 documents 为对象")

    actual = _shared_markdown(root)
    declared = set(raw["documents"])
    if missing := sorted(actual - declared):
        raise ResourceGovernanceError(
            "共享 Markdown 未声明 review 或 validation：" + ", ".join(missing)
        )
    if extra := sorted(declared - actual):
        raise ResourceGovernanceError("治理清单引用不存在文件：" + ", ".join(extra))

    review_skills: set[str] = set()
    for document, rule in raw["documents"].items():
        if not isinstance(rule, dict):
            raise ResourceGovernanceError(f"{document}: 治理声明必须是对象")
        resource = _resource_for_document(root, manifest, document)
        kind = rule.get("kind")
        if kind == "reviewable-rule":
            if set(rule) != {"kind", "review_skill"}:
                raise ResourceGovernanceError(
                    f"{document}: reviewable-rule 只能声明 kind、review_skill"
                )
            skill = rule.get("review_skill")
            if not isinstance(skill, str) or not skill.strip():
                raise ResourceGovernanceError(f"{document}: review_skill 不能为空")
            if skill in review_skills:
                raise ResourceGovernanceError(
                    f"{document}: review Skill 必须专用于一条共享规则：{skill}"
                )
            review_skills.add(skill)
            skill_file = root / "skills" / skill / "SKILL.md"
            if not skill_file.is_file():
                raise ResourceGovernanceError(
                    f"{document}: review Skill 不存在：{skill}"
                )
            if resource.consumers != "*" and skill not in resource.consumers:
                raise ResourceGovernanceError(
                    f"{document}: {skill} 未声明为共享规则 consumer"
                )
            skill_text = skill_file.read_text()
            if resource.release_path not in skill_text:
                raise ResourceGovernanceError(
                    f"{document}: {skill} 未直接引用 {resource.release_path}"
                )
            review_terms = ("review", "评审", "审查")
            if (
                not any(term in skill_text.lower() for term in review_terms)
                or "只读" not in skill_text
            ):
                raise ResourceGovernanceError(
                    f"{document}: {skill} 未声明只读 review 能力"
                )
        elif kind == "execution-protocol":
            if set(rule) != {"kind", "validation"}:
                raise ResourceGovernanceError(
                    f"{document}: execution-protocol 只能声明 kind、validation"
                )
            _test_exists(root, rule.get("validation"), document)
        else:
            raise ResourceGovernanceError(
                f"{document}: kind 必须是 reviewable-rule 或 execution-protocol"
            )
