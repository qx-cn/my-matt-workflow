# Workflow Optimization State

- 当前阶段：阶段④ Astra 指令兼容性实施已完成；行为证据 8 pass、1 inconclusive
- 工作仓库：`/Users/sherly/CS/wsp/ai/my-matt-workflow`
- 路径说明：用户文本中的 `/Users/admin/wsp/futu/my-matt-workflow` 在当前会话未挂载；以当前实际工作区为准。

## 已完成项

- 已确认磁盘上此前没有本任务的 `STATE.md`，从阶段 0 开始。
- 已完成独立需求理解审查：PASS。
- 已复现静态根因：`skills/my-grill-me/SKILL.md` 在 `manual` 策略下仅输出 `/my-grilling` 或 `$my-grilling` 后停止，宿主不会自动触发依赖 Skill。
- 阶段 0 已完成：将 `my-grill-me` 明确为单依赖薄入口；在 `manual` 下，用户显式调用入口即满足门槛，入口读取已打包的 `my-grilling` 正文并在同一次调用中提出第一个问题。
- 已增加回归测试，覆盖 Cursor / Claude 与 Codex 两类旧触发文本均不得作为输出，并要求同轮开始访谈。
- 已构建本地 release `grill-me-manual-fix-v1`。
- 阶段 0 门禁已通过：`python3 tools/workflow.py check` 返回整体 `valid`（32 skills、2 scripts、5 eval scenarios、4 required scenarios，tests valid）。
- 阶段①已完成：调研与诊断报告已写入 `.agent/work/workflow-optimization/diagnosis-report.md`。
- 报告已按三类文档分别调研，并覆盖固定 10 节、H1/H2、主工作流、所有人读文档 Skill、M1/M2/M3、优先级清单及 P1-P6 原则草案。
- 阶段①期间未再修改项目源文件；只写入本任务的报告与状态文件。
- 用户已明确要求继续，硬停止点 1 已解除。
- 已按阶段 0 修复后的 `my-grill-me` 规则在同一次调用中进入访谈，没有输出 `$my-grilling` 或 `/my-grilling` 后停止。
- P1 已获用户确认，最终版本已写入 `principles.md`。
- P2 已获用户确认，最终版本已写入 `principles.md`。
- P3 已获用户确认，最终版本已写入 `principles.md`。
- P4 已获用户确认，最终版本已写入 `principles.md`。
- P5 已获用户确认，最终版本已写入 `principles.md`。
- P6 已获用户确认，最终版本已写入 `principles.md`。
- 用户补充了文档型前端渲染的模型分工需求；P6 已再次确认并加入“单一用户入口、内容与前端两个可独立阶段、结构化交接工件、按角色分配模型、前端不得改写内容”的边界。
- P1–P6 已全部逐条确认；`principles.md` 只包含最终版本，没有保留被取代的候选表述。
- 在整份原则文档确认前，用户补充要求：带前端渲染的 Skill 应拆分内容与前端阶段，以便分别使用内容推理模型和前端模型；该补充已写入 P6 并获用户确认。
- 用户已明确确认整份 `principles.md`，阶段②完成，硬停止点 2 已解除。
- 阶段③基线检查通过：`python3 tools/workflow.py check` 返回整体 `valid`；开始批次 1。
- 批次 1 已完成：新增内容寻址的 `review-snapshot` runtime；`my-code-review` 覆盖 committed、staged、unstaged、untracked；`my-implement` 以 review receipt 校验提交等价性。
- 批次 1 门禁通过：128 项测试通过；release `workflow-opt-review-snapshot-v1`；`python3 tools/workflow.py check` 整体 `valid`；变更说明已追加到 `changelog.md`。
- 批次 2 已完成：composition manifest v2 区分 `method` 与 `handoff`；manual 仅在 router/handoff 停止，内部方法同轮执行并返回宿主。
- 批次 2 门禁通过：130 项测试通过；release `workflow-opt-composition-v2`；`python3 tools/workflow.py check` 整体 `valid`；变更说明已追加到 `changelog.md`。
- 批次 3 已完成：新增四层产物最终校验 gate，并接入 Spec、handoff、design review 与 final-state writing。
- 批次 3 门禁通过：132 项测试通过；release `workflow-opt-finalization-gate-v1`；`python3 tools/workflow.py check` 整体 `valid`；变更说明已追加到 `changelog.md`。
- 批次 4 已完成：Spec 精简并加入 revision；Ticket 绑定 Spec 血缘；runtime 增加设计回退状态机与准入/完成门禁。
- 批次 4 门禁通过：138 项测试通过；release `workflow-opt-spec-revision-v1`；`python3 tools/workflow.py check` 整体 `valid`；变更说明已追加到 `changelog.md`。
- 批次 5 已完成源树改造：验证结果区分 static、unit、deterministic-contract、fresh-agent-smoke；新增主链 fresh-context 契约、隔离行为用例与 fixture。
- 隔离主链行为用例已通过全部 rubric；独立代理完成主体后因用量上限中断，主代理完成最终审查/提交收口，因此完整独立端到端结论为 `inconclusive`，详细证据见 `fresh-agent-smoke.md`。
- smoke 发现标准 YAML 块列表不被 Ticket parser 接受；已做窄修复并增加回归测试。
- 批次 5 门禁通过：140 项测试通过；release `workflow-opt-validation-layers-v2`；`python3 tools/workflow.py check` 整体 `valid`；变更说明已补全。
- 批次 6 已完成：新增 reader-first 共享规则；面向人文档 Skill 接入读者导向；三类 HTML 文档 Skill 拆出内容/前端阶段和结构化交接；去掉默认强制图示；强化 my-teach 与 my-humanizer。
- 批次 6 门禁通过：143 项测试通过；release `workflow-opt-document-stages-v1`；`python3 tools/workflow.py check` 整体 `valid`；变更说明已追加。
- 批次 7 已完成：六 adapter 保持拆分；新增一次性 run context receipt、按 Spec revision 区分的 run journal、阶段/证据/blocker 原子记录与恢复规则。
- 批次 7 门禁通过：147 项测试通过；release `workflow-opt-run-journal-v1`；`python3 tools/workflow.py check` 整体 `valid`；变更说明已追加。
- 批次 8 已完成：代码审查两轴在 manual/automatic 下都作为内部方法完成；发现统一包含严重度、位置、失败场景/不变量、证据与置信度、影响和验证，P0/P1 才阻断。
- 批次 8 门禁通过：147 项测试通过；release `workflow-opt-code-review-v1`；`python3 tools/workflow.py check` 整体 `valid`；变更说明已追加。
- 阶段③最终差距审计已完成：诊断报告的 P0/P1 建议、M1/M2/M3 及确认后的 P1–P6 均已映射到源树或明确证据边界；旧 fixture 中的统一段落上限和强制前后图也已更新。
- 用户根据 OpenAI GPT-6 Astra 模型指南提出重新审视 workflow，并明确要求继续。
- 已使用 OpenAI 官方模型指南与 Codex `AGENTS.md` 指南核对 Astra 的主动推进、指令敏感、子代理和测试范围建议。
- 阶段④只读审计已完成，报告写入 `.agent/work/workflow-optimization/astra-compatibility-audit.md`。
- 审计确认 4 个 P0：Codex AGENTS 发现不符合原生层级；缺少统一指令权威契约；composition manual 含义冲突；decision policy 过宽且部分 Skill 分支未确定映射。
- 另确认测试范围、诊断 fallback、确认时机、子代理数量、调用元数据重复和 Astra 行为 eval 缺口。
- requirement-analysis 独立审查为 PASS：本轮授权覆盖只读审计，不预先批准新的优先级、停止条件或测试投入规则。
- D1「指令权威」已获用户采纳，并作为 P7.1 写入 `principles.md`。
- D2「确认门槛」已获用户采纳，并作为 P7.2 写入 `principles.md`。
- D3「测试范围」已获用户采纳，并作为 P7.3 写入 `principles.md`。
- D4「无法复现 Bug 时的推进方式」已获用户采纳，并作为 P7.4 写入 `principles.md`。
- D5「子代理使用」已获用户采纳，并作为 P7.5 写入 `principles.md`。
- Astra 兼容性 D1–D5 已全部确认，P7 成为阶段④实施的硬约束。
- Astra 批次 1 已完成：Codex 原生 `AGENTS*` 分层发现、指令权威契约、确定性 `decision-gate`、composition/decision 文案单义化均已落地。
- Astra 批次 1 门禁通过：受影响测试 125 项；release `astra-instruction-semantics-v2`；`python3 tools/workflow.py check` 整体 `valid`。Astra 行为证据仍未建立。
- Astra 批次 2 已完成：Ticket 拆分、文章重组、无 red loop 诊断、领域上下文、原型语言和 Wayfinder 收口已统一到主动推进与唯一 gate 语义。
- Astra 批次 2 门禁通过：受影响测试 130 项；release `astra-confirmation-flow-v1`；`python3 tools/workflow.py check` 整体 `valid`。Astra 行为证据仍未建立。
- Astra 批次 3 已完成：测试范围按风险分层，子代理按能力与收益选择；跨宿主源码的显式调用元数据在安装时按 Codex/Cursor/Claude 投影。
- Cursor 与 Claude 官方文档确认仍消费 `disable-model-invocation: true`，因此没有从可移植源树删除该字段；Codex 安装件不再保留这条非 Codex 控制。
- Astra 批次 3 门禁通过：受影响测试 118 项；release `astra-validation-delegation-v1`；`python3 tools/workflow.py check` 整体 `valid`。Astra 行为证据仍未建立。
- Astra 批次 4 已完成：新增 9 项行为场景、证据 schema、严格 validator 与 `validate-agent-evidence` CLI；状态与 rubric 必须一致，场景齐全不等于全部通过。
- 真实 Astra 测试发现普通本地写入的“通用 write gate”歧义；已收窄为仅 `branch`、`commit`、`external`、`docs` 四类 profile 写入执行 write gate。
- Astra 行为证据已写入 `astra-behavior-evidence.json` 与 `astra-behavior-evidence.md`：ChatGPT app Codex CLI 0.153.0、`gpt-6-astra`、9 项记录齐全，8 pass、1 inconclusive、0 fail、0 blocked。
- 主链已验证 Spec/Ticket 血缘与准入、三轮 TDD、7 项实际验收测试（exit 0）和覆盖完整工作树的 review snapshot；账户周额度在 commit 前耗尽，commit equivalence、Ticket complete、测试报告和最终 handoff 未观察到，故保持 `inconclusive`。
- Astra 批次 4 门禁通过：`python3 -m unittest discover -s tests` 通过 160 项；release `astra-behavior-eval-v2`；`python3 tools/workflow.py check` 整体 `valid`。
- 曾从保留的主链临时仓库续跑一次 Astra；模型只读核对既有 snapshot 与 journal，尚未提交或改变临时仓库时，为控制高价模型成本主动中断。本次约消耗 40,438 tokens，不提升证据结论。
- 成本边界已收紧：默认不再调用 Astra 补齐最后一项；行为结果保持 8 pass、1 inconclusive，禁止为凑齐 9/9 降低证据标准。
- 成本收口后的最终本地复验已通过：行为证据 validator 返回 9 runs / 8 pass / 1 inconclusive；160 项单测通过；`python3 tools/workflow.py check` 对 release `astra-behavior-eval-v2` 返回整体 `valid`。
- 阶段④源树改造已提交到本地 `main`：`667b3f2 feat: harden workflow instructions for Astra`，提交包含 35 个源树文件，不包含被忽略的 `.agent` 工作产物。
- release `astra-behavior-eval-v2` 已安装到本地 Codex 与 Claude；两端 install-state 均回读为 32 Skills，metadata projection 分别为 `codex` 与 `claude`。
- 首次 `git push origin main` 被自动安全审查拦截；披露具体远端 `https://github.com/qx-cn/my-matt-workflow.git` 并取得用户明确授权后，已成功推送 `589317c..667b3f2`。本地 `main` 与 `origin/main` 均为 `667b3f25b1e769116cbbfd38a5651f937fa781c3`，领先/落后为 0/0。

## 下一步

1. 可选证据补齐（默认不执行）：只有用户明确接受 Astra 成本后，才从 `/tmp/my-matt-astra-smoke.GfpCdT/main-workflow` 的保留状态续跑 commit equivalence、Ticket complete、测试报告和最终 handoff；成功前主链不得改成 pass。
2. 若源树继续改动，先构建新 release，再运行 `python3 -m unittest discover -s tests`、`validate-agent-evidence --require-complete` 与 `python3 tools/workflow.py check`。
3. 阶段④提交、远端推送及 Codex/Claude 本地安装均已完成；默认不再调用 Astra 补齐最后一项 inconclusive 行为证据。
