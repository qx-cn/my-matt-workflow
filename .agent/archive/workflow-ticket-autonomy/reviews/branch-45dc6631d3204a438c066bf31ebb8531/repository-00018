# 宿主规则适用性


按[指令权威](instruction-authority.md)消解冲突，不把项目规则当成授权来源：

- Cursor 的 `alwaysApply` 与合法 `globs` 可机械判断；`description` 必须记录相关性依据；无三种激活字段的是 `manual`，只有显式引用时适用；无效 metadata 不得静默丢弃。
- Codex 必须区分 `selected`、`shadowed` 与 `candidate`，并按目录 precedence 判断目标路径。
- Claude 的合法 `paths` 可机械判断；有效且无 `paths` 的规则为 always；无效 frontmatter 不得退化为 always。
- `target_match: null` 表示需要语义判断或显式引用，不表示适用，也不表示不适用。

完成条件：目标规则的每种激活方式、覆盖边和权威冲突都已闭合为事实、finding 或会限制 Verdict 的 Evidence Gap。


