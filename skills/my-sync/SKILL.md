---
name: my-sync
description: 人工审查并同步 Matt 上游 Skills 的变化
disable-model-invocation: true
---

# My Sync

1. 运行 `python3 tools/workflow.py sync` 生成 `upstream/review.json`。其中 `changes` 是已采用 Skill 的上游差异，`recommendations` 是全部未采用 Skill 的只读候选分类。
2. 对每项已采用 Skill 变化展示：上游文件、受影响的 `my-*` Skills、现有个人策略冲突；并单独展示 `recommend` 与 `consider` 候选的通用性、建议名称和安全注意事项。
3. 逐项询问用户选择：
   - 采用上游变化；
   - 保留个人行为；
   - 按新的折中方案重写。
   对推荐候选还可选择：纳入迁移待办，暂缓，或明确排除；候选本身不等于已采用 Skill。
4. 所有需要处理的变化与候选都有决定后，才修改个人 Skills；未决定的候选可继续留在报告中，不阻塞无关同步。
5. 修改后运行 `python3 tools/workflow.py validate`、`python3 -m unittest discover -s tests -p 'test_*.py' -v` 和受影响 Skills 的冒烟测试。
6. 任一验证失败时停止：不构建 release，不更新 `upstream/manifest.json`。
7. 验证全部通过后构建新 release；用户确认并安装成功后，才运行 `workflow.py snapshot` 更新上游快照基线。若已明确接受上游 Skill 删除，使用 `snapshot --allow-deletions`。

逐项决策和验证是硬门禁，即使用户要求全自动或跳过测试也不能省略。不自动合并，不在未完成决策时更新 manifest。

> 项目策略优先：读取 `.agent/matt-workflow.md` 的已解析生效策略；缺键或空值按 `strict-control`。本 Skill 中要求询问、确认、停止或限制后续工作的表述，除绝对安全底线外，均服从该生效策略。绝对安全底线始终不变：不得 Force Push、改写 Git 历史、执行破坏性 Git 操作，或向外部服务发送敏感信息。
