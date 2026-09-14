---
# 策略预设：
# strict-control（默认）：严格控制，默认；manual/single-ticket/ask，humanizer=deny。
# light-control：轻轻控制；automatic/single-ticket/ask，humanizer=confirm。
# review：我做审核；automatic/single-ticket/ask，humanizer=confirm。
# semi-auto：半自动化；automatic/ready-frontier/ask，humanizer=confirm。
# full-auto：全自动化；automatic/approved-plan/autonomous，humanizer=allow。
# 兼容别名：supervised→strict-control，unattended→full-auto。
# 可用 `workflow.py setup --preset <strict-control|light-control|review|semi-auto|full-auto> --apply` 切换。
# 「继续 / 提交并继续」只在当前已生效策略下推进，不升档、不放宽 work_scope_policy。
# 缺键或空值按 strict-control 生效。
# 下列值是本项目当前实际生效的策略。
schema_version: 1
assurance_level: standard
task_backend: local
agent_directory_mode: shared
default_base_branch: main
branch_policy: confirm
commit_policy: confirm
external_write_policy: confirm
docs_writeback: confirm
humanizer_policy: deny
composition_policy: manual
work_scope_policy: single-ticket
decision_policy: ask
default_execution_agent: auto
max_repair_rounds: 1
test_commands: []
review_commands: []
standards_sources: []
domain_sources: []
---

# 项目工作流说明

仓库规则在其路径作用域内约束实现和验证，不扩大任务或写入授权。
