# Ticket 03 → 04 实施接口交接

Handoff-Status: ready

## 已交付

`tools/workflow_lib/ticket_implementation.py` 提供 `select`、`validate`、`start`、`load_active`、`tests_passed`、`test`、`status`。Topic 02 状态仍由 `topic_service` 管理。CLI `--ticket` 可推导 Topic，禁止与另一个 `--topic` 混用；start 必须选 ready Ticket，省略规则仅选唯一 implementing/needs-user。

实施记录：`.agent/work/<topic>/implementations/<id>.json`。字段包含 `ticket`、`topic`、`baseline`（当前 HEAD）、`started_at`、`execution_agent`、`definition`、`tests`、`briefing`。definition.ticket 使用旧 `ticket_definition` 排除状态、claim 和勾选变化；definition.spec_sha256 绑定 Spec。简报位于 `briefings/briefing-<id>.md`。

测试记录逐条含 argv、exit_code、content_id、progress、finished_at、output_tail。每条运行前计算内容身份；`tests_passed` 仅接受当前内容上每条声明命令最近一次非 progress 记录 exit 0。内容身份排除 `.agent`、`.git`、git ignored 文件。`load_active` 拒绝 test_commands 偏离定义快照，其他定义变化由 status.definition_changed 暴露。04 冻结审查、05 finish、06 reopen 要复用这些约束。

## 下游边界

04 接管 review 及 submit 的冻结单元、来源真实性和 coverage 校验。03 不包含 review、finish、resolve、审查循环或配置迁移。Topic 状态中的 `implementation_started` 控制仅首次执行分支规则。

`auto` 是请求策略，执行记录必须绑定具体宿主。显式 Ticket agent 或配置 default_agent 已具体时可用；均为 auto 时，宿主 Skill 调 start 需带 `--agent codex|cursor|claude`，runtime 不猜测环境。后续 Skill 接入由 10 实施。

第一次实施切换到已存在 Topic 分支后，重新读取配置、Topic 状态、所有 Ticket 元数据和稳定定义；不同就拒绝并保留实际分支材料，随后重新验证内容与规则。不会把切换前缓存写回目标 Ticket。

已完成前置提交优先读新实施记录的 commit，否则查询 `<id>:` Git 日志；无法观察时输出 null，不伪造提交。新 finish 05 应写 commit 字段，旧施工日志的提交标题不属于新模型的完整行为样本。

## 施工状态

03 已由安装 runtime 登记 completed、close 和 single-ticket complete。仓库自身配置仍 schema 1，直到 14；不要以源 runtime 管理当前施工。当前未安装新源码到宿主。下一张 04 依赖 03，接续前按 installed runtime 验证。
