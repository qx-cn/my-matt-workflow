# 组合调用适配

读取 `.agent/matt-workflow.md` 的 `composition_policy`，只在当前流程已进入相应阶段时选择依赖：

- `automatic`：读取并遵守宿主 Skill 指向的已打包 `references/composed/` 参考。
- `manual`：输出当前运行时对应的下一条显式调用，然后停止；不要在宿主流程中隐式执行依赖。

已打包依赖的 Skill 正文固定命名为 `references/composed/<skill>/COMPOSED.md`。这是供宿主读取的参考副本，不是可调用 Skill；顶层 `SKILL.md` 才是运行时注册入口。

流程交接也遵循同一规则：`automatic` 只能在当前阶段已经完成且宿主已声明的下一阶段之间继续；`manual` 只给出下一条显式调用并停止。交接不得绕过被调用 Skill 的停止条件、确认门槛或 Ticket 准入。

此适配只决定组合调用方式，不改变被调用 Skill 的停止条件、确认门槛或其他上游方法。
