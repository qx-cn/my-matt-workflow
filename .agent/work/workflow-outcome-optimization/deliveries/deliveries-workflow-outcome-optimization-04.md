# CI 与本机双宿主安装交付

本次补偿 Ticket 06 处理推送后的 Python 3.10 CI 失败和本机安装检查发现的问题。施工采用普通工程工具，不调用被测 workflow 自身 Skills 治理任务；原 Spec、完成 Ticket 和原独立报告不回写。

## 修复

1. Python 3.10 的 unittest 只在 loader identity 中写类名，3.14 写类名与 method。统一完整身份识别，保持 v3 typed 完整诊断 fingerprint 和真实业务失败门禁。旧 v3 空 fingerprint 不能借粗粒度身份 become known。
2. 仓库 Markdown 校验仅排除根 `.agent/work` 活动状态及原始证据；其他 `.agent` 配置、正式文档和 tests/fixtures 仍严格拒绝缺失及逃逸链接。原始 `/tmp` 报告与合成反例字节保留。
3. 迁移测试的临时 Git clone 禁用 detached 自动维护，避免清理 `.git` 时后台重建目录。生产 Git 行为、所有测试断言和严格 cleanup 均未改变；没有吞异常、跳过或增加重试。

## 验证

- 最终 source manifest SHA256：`671d93dedb49daf0f3af403ce41572f9a2a125f12f4812a38f0c7fb8191ffc6b`，285 文件。完整 discovery 为 357 项；构建在稳定快照上执行完整 check。
- 最终 CI：[run 37032744557](https://github.com/qx-cn/my-matt-workflow/actions/runs/37032744557)，`ee589c2` 的 Python 3.10/3.14 两个 job 均成功。两个 job 均执行 `python3 tools/workflow.py check` 和 `git diff --exit-code`，没有删除 Python 3.10 矩阵。之前失败的 run 和中间成功 run 均保留证据。
- 独立复审 7 组函数/实际进程控制及 2 组公共 CLI 控制通过；包含 21 次真实测试进程、48 次 CLI 调用和 23 个 Markdown 路径控制。final02 补充复核确认唯一新增差异为临时 migration fixture 配置，原受审生产文件及兼容测试逐字节相同。见 [原始独立报告](../evidence/compensation-06/independent/outcome-ci-install-review-final.md) 和 [最终 binding](../evidence/compensation-06/independent/outcome-ci-install-review-final02-binding.json)。
- 本机曾有完整 357 项检查的一次临时目录清理错误，原失败日志保留；Trace2 的 3 次默认运行均启动 detached maintenance，2 次控制运行均不启动，5 次定向测试全部 exit 0。未在这些定向运行中复现原 Errno66，不宣称所有文件系统竞态都已消除。
- 最终完整构建：正式 deploy exit 0，稳定快照完整检查通过，release `20261003-001558` 构建并安装成功。最终双宿主验证见 [host-verification.json](../evidence/compensation-06/host-verification.json)。

## 安装结果

Codex 与 Claude 均为 `20261003-001558`，各 32 个 Skills。安装命令分别 exit 0。

`doctor` 核验各宿主实际 Skill/runtime 内容，source 与 current release 均 valid 且 source_match=true；两个已安装 runtime 的 `--help` 实际 exit 0。三个修复 runtime 文件分别与当前源码逐字节一致。未安装 Cursor。

## 工件与边界

- [补偿 Ticket 06](../tickets/tickets-workflow-outcome-optimization-06.md)
- [完整当前源码包](workflow-outcome-optimization-source-04.tar.gz)
- [包字节/mode 校验身份](../evidence/compensation-06/source-package-identity-04.json)
- [完成证据](../evidence/compensation-06/completion-evidence.json)

生产代码提交为 `718f39f`；最后的临时测试仓库修复提交为 `ee589c2`，最终 CI 验证它。此后的完成证据提交只改变 `.agent/work` 中的记录/源码包，不改变受审、测试和安装的 285 文件；源码 manifest 绑定这种对应关系。

作者与独立 reviewer 使用用户指定的 gpt-6.1-sol；代理协调使用通用 Paseo Skill（`/Users/sherly/.agents/skills/paseo/SKILL.md`）。实际宿主安装和机械合同已验证，没有真实模型任务效果对照或七项能力提升幅度的结论。
