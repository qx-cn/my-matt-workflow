# Ticket 02 runtime 基础接口

来源：`workflow-simplification-02`，Spec revision 1。这里只记录本轮接口和后续 owner，不变更 Spec 或 Ticket 图。

## 当前接口

- 新配置与 Topic 模型由 `tools/workflow_lib/topic_service.py` 独立实现，不调用旧 session 状态机。
- `read_config(repo)` 校验九键 v2 配置；旧 schema、删除字段及 audited 拒绝并提示 migrate。`setup` 先完整探测/校验，默认不写；apply 才写配置，private 初始化 `.agent` 嵌套 Git。
- Topic 运行状态文件是 Topic 目录内的 `topic-state.json`。active 包含 status、level、started_at、baseline、test_runs；private quick 恢复时可有 code_commit。归档后记录 outcome、finished_at、reason。
- 无状态文件时，有 `tickets/*.md` 为 pending，无 Ticket 为 document。显式选择归档 Topic 只能读 status。活动 Topic 唯一时可省略选择，多个活动 Topic 时拒绝。
- `full_tests(config)` 排除末尾字面量 ` *` 的命令。`content_paths` / `content_id` 包含 Git 已跟踪及非忽略未跟踪内容，排除 `.agent`；执行 argv，不使用 shell。
- quick complete 检查真实 Markdown 章节，逐条运行全量测试，拒绝失败或测试导致的内容变化；无测试时标明未配置测试。shared 合并代码和元数据提交，private 分别提交；private 元数据失败后记录 code_commit，重试不会第二次提交代码。
- document complete 只提交 `.agent`，保留无关内容和其暂存状态；指标不可观察字段为 null。quick 不建立实施记录。

## 后续 owner

- Ticket 03：以本模块的配置、Topic 定位和内容函数接入 Ticket 校验、implement start/test/status。pending Topic 的下一步命令应选定 ready Ticket 并带 `--ticket`；当前 Topic 状态视图仅建立分类，尚未拥有 Ticket 调度。
- Ticket 05/07：接入 standard 的单 Ticket/多 Ticket 收尾，当前明确拒绝 standard 完成，避免提前宣称已支持。
- Ticket 08：旧 Topic 内容探测与迁移。
- Ticket 13：完成公共命令裁剪、指标全部观察字段/汇总及新行为测试收缩。旧 profile、refresh-project 和旧 session 的内部测试目前仍用于施工回归，未作为新入口的兼容路径。
- Ticket 14：转换本仓库配置与 README；本轮未改本仓库 schema 1 配置，施工继续用已安装 runtime。

## 验证边界

验证使用临时本地 Git 仓库，覆盖 shared/private、默认与已有/非默认分支、摘要缺节/围栏模板、测试失败/修改内容、Git hook 提交失败与恢复、归档只读与不覆盖。未做宿主安装、发布、推送或其他项目迁移。进程强制终止和机器掉电后的事务恢复未验证。
