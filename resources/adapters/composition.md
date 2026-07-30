# 组合调用适配

读取 `.agent/matt-workflow.md` 的 `composition_policy`，只在当前流程已进入相应阶段时选择依赖：

- `automatic`：读取并遵守宿主 Skill 指向的已打包 `references/composed/` 参考。
- `manual`：输出当前运行时对应的下一条显式调用，然后停止；不要在宿主流程中隐式执行依赖。

此适配只决定组合调用方式，不改变被调用 Skill 的停止条件、确认门槛或其他上游方法。
