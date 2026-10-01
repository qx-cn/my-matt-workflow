# Ticket 拆分调整提案（待用户确认）

Spec revision 1 保持不变；不改写已完成 Ticket。

## Ticket 09 增加的当前职责

把构建所需的旧校验迁移纳入本 Ticket：build 的 preflight 和 source_gate 不再读取 evals、smoke 或行为证据注册表；以 tests 覆盖 Skill 元数据、Markdown 链接、资源与 governance、调用图和安装投影。保留来源/文件安全校验。同步受影响的 tests 中旧正文复制、旧 Skill 集合和旧校验引用。必要的 check 入口解耦与对应测试在此交付，以保证新清单能完整构建和临时安装。

原六项验收保留。增加一项验收：从施工前基线转换为新清单后，build 与临时三宿主 install 校验不读取旧 Skill eval 路径；故意破坏新集合、调用元数据或本地链接时仍拒绝构建；tests 验证实际产物。09 可继续沿用 tools/tests 等当前路径范围，不修改 evals 历史内容。

## Ticket 13 调整的后续职责

第3项验收改为：样例已保留后删除 evals 及 fixture ignore 例外；确认 check 只运行 tests，完成剩余旧模块/命令清理和全量集成。构建前置静态校验与对应测试沿用09已交付结果，不把它们作为09完成后的前置工作。其他验收不变。

## 恢复步骤

用户确认后更新09/13的 Ticket 定义并通过准入，重新建立绑定新 definition 的实施 attempt；旧 blocked 记录保留。候选补丁仅作为研究材料，重新逐切片执行、验证和审查，不直接当成可交付实现。
