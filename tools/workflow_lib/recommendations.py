"""Curated, review-only recommendations for unadopted upstream Skills."""

from __future__ import annotations

from collections import Counter


_CATALOG: dict[str, dict[str, str]] = {
    "engineering/resolving-merge-conflicts": {
        "status": "covered",
        "priority": "none",
        "suggested_name": "my-resolving-merge-conflicts",
        "reason": "本地 my-resolving-merge-conflicts 已覆盖审阅、验证与安全边界。",
        "caveat": "本地版本保留批准门禁与禁止破坏性 Git 操作。",
    },
    "in-progress/to-questionnaire": {
        "status": "covered",
        "priority": "none",
        "suggested_name": "my-to-questionnaire",
        "reason": "本地 my-to-questionnaire 已提供按 topic 保存的异步发现问卷。",
        "caveat": "发送给外部人员仍须按外部写入策略确认。",
    },
    "in-progress/wizard": {
        "status": "covered",
        "priority": "none",
        "suggested_name": "my-wizard",
        "reason": "本地 my-wizard 已提供逐步确认的配置与迁移向导。",
        "caveat": "保留秘密不回显与每项外部写入单独确认。",
    },
    "misc/setup-pre-commit": {
        "status": "consider",
        "priority": "medium",
        "suggested_name": "my-setup-pre-commit",
        "reason": "常见的工程质量需求，可作为仓库级可选能力。",
        "caveat": "当前上游实现偏 Node/Husky；应先做跨语言和既有工具链检测，再修改团队配置。",
    },
    "personal/edit-article": {
        "status": "covered",
        "priority": "none",
        "suggested_name": "my-edit-article",
        "reason": "本地 my-edit-article 已提供确认结构方案后的安全文章编辑。",
        "caveat": "默认保留原稿，仅在明确授权时原地修改。",
    },
    "in-progress/writing-fragments": {
        "status": "consider",
        "priority": "low",
        "suggested_name": "my-writing-fragments",
        "reason": "可作为从素材探索到成文的写作套件的一部分。",
        "caveat": "仅在决定纳入完整写作套件时采用；单独采用价值有限。",
    },
    "in-progress/writing-beats": {
        "status": "consider",
        "priority": "low",
        "suggested_name": "my-writing-beats",
        "reason": "将固定素材按可理解的叙事节奏逐段写作。",
        "caveat": "仅在决定纳入完整写作套件时采用；需要本地化输出目录。",
    },
    "in-progress/writing-shape": {
        "status": "consider",
        "priority": "low",
        "suggested_name": "my-writing-shape",
        "reason": "将原始材料逐段塑造成文章，适合长文生产。",
        "caveat": "仅在决定纳入完整写作套件时采用；需要本地化输出目录。",
    },
    "productivity/grilling": {
        "status": "covered",
        "priority": "none",
        "suggested_name": "my-grilling",
        "reason": "本地已有等价的 my-grilling；不需要新增 Skill。",
        "caveat": "保留为未映射上游项，直到完成本轮迁移和发布时再决定是否纳入映射基线。",
    },
    "engineering/setup-matt-pocock-skills": {
        "status": "covered",
        "priority": "none",
        "suggested_name": "my-setup",
        "reason": "本地 my-setup 与安装/项目配置工具已覆盖其核心目的。",
        "caveat": "现有本地实现比上游更通用；无需按上游原样迁移。",
    },
    "in-progress/claude-handoff": {
        "status": "covered",
        "priority": "none",
        "suggested_name": "my-handoff",
        "reason": "本地 my-handoff 已提供跨 Agent 的交接产物。",
        "caveat": "上游版本依赖 Claude 专用代理机制，不能直接采用。",
    },
    "misc/git-guardrails-claude-code": {
        "status": "defer",
        "priority": "none",
        "suggested_name": "",
        "reason": "现有企业安全策略已覆盖关键 Git 禁止项。",
        "caveat": "该 Skill 只适用于 Claude Code Hook；若未来需要跨 Agent 的本机防护，再单独设计。",
    },
    "in-progress/setup-ts-deep-modules": {
        "status": "defer",
        "priority": "none",
        "suggested_name": "",
        "reason": "仅适用于 TypeScript 深模块架构，通用性不足。",
        "caveat": "应在具体 TypeScript 仓库有明确需求时再考虑。",
    },
    "misc/migrate-to-shoehorn": {
        "status": "defer",
        "priority": "none",
        "suggested_name": "",
        "reason": "Shoehorn 迁移高度依赖特定 TypeScript 测试库。",
        "caveat": "不应进入通用个人工作流。",
    },
    "misc/scaffold-exercises": {
        "status": "defer",
        "priority": "none",
        "suggested_name": "",
        "reason": "面向特定课程仓库和内部 lint 命令。",
        "caveat": "不具备可移植性。",
    },
    "personal/obsidian-vault": {
        "status": "defer",
        "priority": "none",
        "suggested_name": "",
        "reason": "上游内含个人 Vault 路径和组织约定。",
        "caveat": "如需笔记管理，应另做可配置、无硬编码路径的版本。",
    },
}


def _default_entry(path: str) -> dict[str, str]:
    if path.startswith("deprecated/"):
        return {
            "status": "defer",
            "priority": "none",
            "suggested_name": "",
            "reason": "上游已标记为 deprecated，不应纳入新的个人工作流。",
            "caveat": "仅在需要迁移旧项目且没有可替代方案时，再单独审查。",
        }
    if path.startswith("in-progress/"):
        return {
            "status": "defer",
            "priority": "none",
            "suggested_name": "",
            "reason": "上游仍处于 in-progress 状态，稳定性与边界尚未确认。",
            "caveat": "等待上游稳定或出现明确本地需求后再评审。",
        }
    if path.startswith("personal/"):
        return {
            "status": "defer",
            "priority": "none",
            "suggested_name": "",
            "reason": "上游属于个人环境定制，尚未证明可移植性。",
            "caveat": "若有明确需求，应重新设计为可配置版本，而非直接迁移。",
        }
    return {
        "status": "defer",
        "priority": "none",
        "suggested_name": "",
        "reason": "尚未人工评估其通用性与本地策略兼容性。",
        "caveat": "保留在未映射清单中，待需要明确后再评审。",
    }


def build_recommendation_report(unmapped_skills: list[str]) -> dict[str, object]:
    """Classify every unadopted upstream Skill without selecting one for adoption."""
    items: list[dict[str, str]] = []
    for path in sorted(unmapped_skills):
        entry = _CATALOG.get(path, _default_entry(path))
        items.append({"upstream_skill": path, **entry})

    counts = Counter(item["status"] for item in items)
    return {
        "summary": {
            "recommend": counts["recommend"],
            "consider": counts["consider"],
            "covered": counts["covered"],
            "defer": counts["defer"],
        },
        "items": items,
    }
