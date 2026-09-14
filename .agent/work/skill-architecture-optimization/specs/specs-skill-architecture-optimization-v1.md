---
spec_id: skill-architecture-optimization
revision: 4
status: implemented-with-declared-evidence-gaps
baseline: 7825887d4bcdedbcd745aa45aaad25f00e55217d
execution_agent: auto
supersedes: null
---

# Skill 架构与运行时可信边界优化

## 问题陈述

仓库已经形成 Skill、共享规则、组合图、确定性 runtime、release/install 和分层验证五层架构，且当前静态门禁全部通过；但若干承重不变量仍只存在于 prose、调用方布尔参数或多个互相独立的状态文件中。结果是：当前 `check` 为绿时，仍可发生越界删除、错误 Ticket 准入、伪造完成证据、宿主调用漂移，以及 Skill 路由和产物位置失联。

本次优化把机械安全与状态不变量收回 runtime，把 Skill 保持为小而清楚的语义入口，并建立可审计的 portfolio 图。目标不是增加更多规则，而是让每项承重行为只有一个可执行事实来源。

## 基线与证据边界

- 固定审查基线：`main@7825887`，审查开始时工作树干净且与 `origin/main` 同步。
- `python3 -m unittest discover -s tests`：203 项通过。
- `python3 tools/workflow.py validate-evals`：8 个 deterministic scenario，通过；其中 7 个为 required。
- `python3 tools/workflow.py check`：37 Skills、2 个 shell scripts、release `runtime-session-contract-v6` 均有效。
- 上述结果只证明 static、unit、deterministic-contract 与当前 release/source 一致，不证明模型真实遵循 37 个 Skill。
- 临时目录故障注入已复现三类越界删除：伪造 install state、work-artifact recovery journal、伪造 artifact-review snapshot directory。
- 当前本机 Codex/Claude 安装状态仍指向 `shared-rule-review-v1`（34 Skills）；这是部署漂移，不影响源树基线，但不能冒充已安装最新版。

## 目标结果

1. 任何损坏、伪造或过期的持久状态都在文件系统写入前 fail closed；删除、移动与清理只能作用于独立可信 registry 登记、且位于专用可信根内的对象。
2. Ticket 准入、领取、选择、运行和完成由同一 runtime 生命周期执行；不存在较弱入口或裸布尔参数绕过。
3. 测试、审查、规则、profile、Spec、Ticket 与代码内容使用结构化 receipt 绑定；输入漂移会使当前 work unit 失效。
4. release 只由一个 byte-exact、稳定的显式源码快照生成；manifest、目录名、current 指针与安装状态的 release identity 一致。
5. 37 个 Skill 在一个机器可读 portfolio 中恰好登记一次；路由、组合、共享资源和验证覆盖可由图校验，不再依赖手写总数。
6. 宿主调用语法在安装投影时生成；Skill 源码不再散落 Codex/Cursor/Claude 专属调用文本。
7. 直接影响行为的 Skill 合同得到修复；参考、模板和机械检查下沉到正确层级。
8. 源树健康、Agent 行为证据、release 健康和宿主部署健康分别报告，互不冒充。

## 范围边界

### 范围内

- `tools/workflow_lib/**` 与 `tools/workflow.py` 的安全、Ticket/run、release/install、profile/rules、doctor 和 portfolio 校验。
- `composition/manifest.json`、`resources/manifest.json`、`resources/governance.json`、新增 portfolio registry，以及相应测试/eval。
- 37 个 Skill 的全量 inventory；对已确认存在失败路径的 Skill 做定向重构。
- 新 release 构建与临时 Agent home 的升级/回滚验证。
- 使用当前模型与默认 reasoning 的 fresh-context 评审或行为 smoke；任何模型升级都不在本次授权内。

### 范围外

- 没有 comparative 证据时，不退役 `my-requirement-analysis` 或专项 review Skill。
- 不把所有 Skill 强制改成同一模板、同一长度或同一种完成条件。
- 不修改 Matt 原生 Skills，不引入外部 Tracker，不写真实宿主安装目录，不 push、不提交。
- 不把全浏览器视觉自动化作为本次硬门禁；真实 viewport/打印/键盘仍明确记录为人工或后续证据。
- 不为了提高行为证据等级切换到 Astra、提高 reasoning 或服务档位。

## 当前架构判断

保留现有五层方向：

1. `skills/**`：用户目标与模型判断。
2. `resources/**`、`policies/**`：共享语义和宿主适配。
3. `tools/workflow_lib/**`：机械状态、授权、快照与事务。
4. `release/install`：编译、投影、校验和回滚。
5. `tests/**`、`evals/**`：static/unit、deterministic contract 与 fresh-agent 证据定义。

需要改变的是层间边界：prose 不得独自承担可确定执行的安全不变量；runtime 也不得相信调用者用一个 flag 自证授权或完成。

## 审查结论

### P0：破坏性操作缺少路径 capability

- `installer.py:307-378` 信任 `install-state.json.skills`。伪造 `../victim` 或普通个人目录名可被移入 transaction 后随成功清理删除。
- `work_artifacts.py:50-87` 对未规范化的 `.agent/../victim` 使用 `is_relative_to`，rollback 可删除 `.agent` 外文件。
- `artifact_review.py:129-157` 只凭目录名前缀与可伪造 marker 递归删除目录。
- `prune-releases` 与 build 的固定 staging cleanup 也是递归删除 sink；它们虽未在本轮复现越界，必须进入同一 destructive-sink inventory，不能留作旁路。

### P1：Ticket/Run 契约存在旁路

- `tickets.py:126-134` 的 `validate_ready_ticket` 未执行 `ticket_kind`、显式 `claimed_by`、`blocked_by`、依赖环和至少一项未完成验收的完整准入。
- `run-start` 直接依赖较弱准入，可绕过 `implementation-open`。
- `transitions.py:37-43` 把依赖环、被认领或受阻塞造成的“无候选”误报为完成。
- `approved-plan` 缼少 allowed scope 时退化为不过滤；external write 仅以 `--approved-scope` 布尔值自证授权。
- `submit_run_outcome` 可从 `admitted` 直接完成，且 test/review receipt 只是非空字符串；Ticket/Spec 之外的规则、profile 与代码漂移不使 work unit stale。Ticket 内的稳定定义与会在运行中变化的 claim/status/验收记录也尚未分离，若把整份 Ticket 当 immutable receipt，会与合法状态变化自相矛盾。

### P1：release/install 完整性不闭合

- release staging 复制整个 Skill 目录，已把 `__pycache__/*.pyc` 带入当前 release，构建结果依赖本机缓存与 Python 版本。
- `verify_release` 不拒绝 manifest 外 Skill 目录；`release_id` 不要求与目录名一致。current 只应约束默认当前 release，不能阻止显式旧版安装或回滚。
- install state 与 transaction journal 的 schema 校验强度不一致。
- `check` 不报告真实宿主仍安装旧 release。

### P1：Skill 控制模型与真实宿主合同冲突

- `my-writing-great-skills` 把 description 的存在/删除定义为调用轴；本仓库 37/37 的 source Skill 保留 description，真正由宿主 policy 禁止隐式调用。
- 12 个 Skill 源码共写死 78 处 `/my-*`，Codex 正式入口却是 `$my-*`；安装阶段只投影 metadata，不投影正文调用。
- `my-ask-matt` 漏掉 `my-install`、`my-requirement-analysis`、`my-tech-design`、`my-test-report`；主链正文停在 implement，而 fresh-context contract 把 test report 作为交付尾段。

### P1：已确认的 Skill 行为缺陷

- `my-triage` 的本地 ready Ticket 模板缺少强制 lineage、rules、agent 和验收字段，无法进入实施；还残留不存在的旧 Skill 名。外部 Tracker 的原生 triage brief/status 路径本身应保留，不能被本地 Ticket handoff 取代。
- `my-install` 在全局安装后仍假设 cwd 含 `tools/workflow.py`。
- `my-prototype` 的附属分支把可抛弃原型直接融入生产模块，越过 implementation scope。
- `my-wayfinder` 声明读取五项 composed dependency，却没有实际上下文指针。
- `my-tdd` 的 description 承诺 red-green-refactor，正文却排除 refactor；其 seam 规则与 `my-codebase-design`、`DEEPENING.md`、`mocking.md` 多源冲突。
- `my-tech-design` 的通用 checker 混入历史方案词表，模板无条件保留可选总览图，默认 prompt 承诺 HTML 而默认流程只产 content。
- `my-wizard` 可把 secret 写入默认 `.env`，却不机械验证 tracked/ignored 状态或收紧权限。
- `my-to-questionnaire` 与 `my-test-report` 偏离 `.agent/work/<topic>/<type>/` 统一存储。
- `my-edit-article` 在用户已明确授权原地编辑时仍强制重复确认。

### P2：信息层级与验证覆盖仍分散

- `my-requirement-analysis`、`my-to-tickets`、`my-wayfinder`、`my-diagnosing-bugs`、`my-triage` 的步骤、模板和参考混在顶层。
- review 家族重复维护通用 finding gate；测试 seam 也有多份定义。
- deterministic smoke registry 只映射 11/37 个 Skill；26 个无映射。当前 validator 不要求 portfolio 覆盖或明确 exemption。
- resource governance 只验证测试方法名存在，不证明该 contract 被测试执行。

## 目标设计

### 1. Filesystem capability kernel

新增小型内部模块，提供：

- `strict_relative_path(root, raw)`：只接受非空相对路径，拒绝 absolute、`..`、NUL；resolve 后仍必须位于 resolved root；目标或祖先 symlink 不能把写入带出 root。
- 版本化 schema loader：exact required/optional fields、类型、合法 name、绝对 home、未知版本 fail closed。
- 独立 ownership registry：nonce/capability 不与待删除目录放在同一个可伪造 marker 中；登记 canonical root、device/inode（平台可得时）、用途和完整 inventory digest。可恢复事务另登记 immutable control file digest；恢复先核对稳定 identity/control，再按 journal 推进，不能让合法变化的 transaction tree digest 阻断恢复。目录内 marker 只是辅助证据，不能自证所有权。
- destructive sink 只接受专用可信根的直接子项。删除前重新验证 registry 与路径，把目标原子移入同根 quarantine 后再清理；无法提供安全 dir-fd/no-follow 语义的平台至少拒绝 symlink ancestor、跨设备和 identity 漂移。
- 单写者 lock：install、build、prune、artifact migration 与 review snapshot cleanup 不把另一个进程的活动事务当作崩溃恢复。build/prune 共用 releases mutation lock，candidate rename 与 `current.json` 原子切换位于同一临界区。固定 staging 已存在时先验证 ownership；未知目录 fail closed，不直接清理。

installer 仅移动具备前一 release manifest/ownership receipt 的托管目录。损坏旧 state 直接停止，不得当成空状态，也不得接触未知目录。

### 2. 单一 Ticket/Run 生命周期

建立统一 application service，并让所有 CLI 入口委托给它：

- `ImplementationTicket` 准入一次性验证 kind、状态、显式 claim、依赖存在且无环、至少一个未完成验收、Spec lineage、rule fields 与 execution agent。
- selector 返回 `continue | complete | blocked | invalid`；只有批准范围内所有 Ticket 均为不可变终态才返回 complete。
- approved-plan 使用 runtime 生成的 `scope_id`/scope artifact；缺失或不匹配时 fail closed。
- 将 Ticket 拆成稳定 definition（kind、目标、lineage、rules、acceptance 文本）与可变 execution state（claim、status、acceptance observations）；definition receipt 必须稳定，可变状态由 runtime 事务单独管理。
- `claim-run` 以 definition hash + 原子创建/CAS 领取；同一 Ticket 的每次尝试有独立 attempt id。
- `complete-run` 是唯一终态入口：要求合法前态、runtime 实际执行并登记的 test evidence（argv、exit code、output digests）、runtime 对 profile 预声明 reviewer command 的真实子进程执行证据、绑定当前 code snapshot 与 runtime 保存结果 digest 的 review evidence、当前 code content id 以及所有稳定 source receipt 一致；不得接受调用者提供的 review result 文件或手拼 pass dict。再通过 WAL/transaction journal 对 run state 与 Ticket 投影做可恢复的协调更新；不得把两个普通文件写入宣称为单次原子操作。
- 旧 `run-start`、`run-record`、`implementation-submit` 保留一个 release 的兼容入口，但调用同一 service，不能走较弱逻辑。旧字符串 receipt 无法转换成结构化证据时只能记录非终态或 fail closed，不能被兼容层伪造升级。

统一 `SourceReceipt` 形状为 `kind/path/sha256/size`。Ticket、Spec、profile、rules、standards/domain sources、代码快照和验证产物都进入 work unit；submit/close 前重验。

Ticket 的 Spec lineage 不以 Ticket 自报字段为准：runtime 要求 `spec_ref` 指向同一 `.agent/work/<topic>/specs/` 的直接文件，并解析 Spec frontmatter，核对 `spec_id` 与正整数 `revision`。

external write scope 改成 runtime 生成的 capability，绑定 `kind/target/operation/scope_id`；裸 `--approved-scope` 不再产生授权。runtime 只能证明“被宿主确认过的范围未扩大”，不能凭本地文件证明用户确实授权；授权来源必须是宿主可信 confirmation receipt，宿主无法提供时仍由宿主 gate 实时确认。

### 3. 确定性 release 与部署诊断

- validate、source manifest 与 build 共用一个 source walker。
- build 在输出锁内先复制源码并比较复制前、复制后与快照 inventory；源码在复制或门禁期间变化时重试，无法得到稳定视图则 fail closed。完整门禁与打包必须读取同一个不可变快照，不能先验证活动工作树、再从另一个时刻打包。
- walker 包含 `SKILL.md`、标准子目录，以及由 prose Markdown/脚本直接引用形成的经校验可达闭包；现有 `GLOSSARY.md`、`CONTENT.md`、`FRONTEND.md`、`LOGIC.md`、`UI.md`、`DEEPENING.md`、`tests.md`、`mocking.md`、`template.sh` 等根级 sidecar 必须可达。未被引用但确需发布的文件通过 per-Skill source inventory 显式声明。统一排除 `__pycache__`、`*.py[cod]`、`.DS_Store`、log/tmp 和 symlink escape。
- release 验证比较根目录、Skill 同级目录、每个文件及 runtime 的精确闭包。
- 任意 release 都要求 `manifest.release_id == release directory`；只有 `verify-current` 与默认 install 要求 current 指针等于被选 release。显式安装旧 release 与 rollback 仍合法，且 previous release 在回滚窗口内受 prune 保护。
- host projection 是确定性编译步骤：为 Codex/Cursor/Claude 分别派生 target manifest。安装后与 `doctor` 都按 target manifest 检查完整文件集合和 digest，而不只检查 metadata 字段。
- 新增只读 `doctor`，分别报告 source/current release 与每个指定宿主 install state、Skill 集合、runtime、target manifest 的一致/漂移/损坏状态；不自动安装。

### 4. Portfolio contract graph

新增 `portfolio/manifest.json`，每个 source Skill 恰好登记一次，只记录跨文件才有意义的事实：

- `category`
- `discoverability: routed | specialist | administrative`
- `roles: entry | method | handoff | review | admin`（可多值）
- `criticality`
- 分层 `evidence.static/deterministic/fresh_agent/real_project`，每层分别列 case id 或带理由、风险与解除条件的 exemption

Skill 的名称、description 与正文仍以自身目录为权威，不复制到 portfolio。

validator 从目录与 portfolio 派生总数，移除 `EXPECTED_MANUAL_SKILLS`。它验证：

- 目录与 registry 一一对应；
- composition caller/callee 和 router 均存在且 role 合法；
- `my-ask-matt` 正文中的调用宏集合与 routed edges 双向相等；非 routed 项有明确分类且不能被 router prose 暗中调用；
- 每个 Skill 在各证据层有映射或该层 exemption；critical Skill 不能用 deterministic 映射冒充 fresh-agent 覆盖；
- raw `/my-*`、`$my-*` 只可出现在声明为宿主示例的测试 fixture，不进入可移植 Skill prose。

source 以 `{{skill-call:my-name}}` 表示需要交给用户的显式调用。installer 在目标 staging tree 中投影为 Codex `$my-name` 或 Cursor/Claude `/my-name`。composed method 只使用 Markdown 指针。每条 handoff 同时拥有 composed-body 指针与调用宏：`automatic` 读取前者，`manual` 输出后者并停止；validator 将两者与 manifest edge 对齐。

resources manifest 只声明 direct consumers；build 根据 composition closure 与资源自身的链接依赖闭包派生 effective consumers，并把 direct/effective 图写入 release manifest。Markdown parser 必须统一识别普通、尖括号、fragment 与 title 形式。validator 要求 direct consumers 与源码直接引用精确一致；传递消费者不得继续手工重复。

### 5. Skill 定向重构

- `my-writing-great-skills`：把调用定义改为 host policy 决定；description 是宿主可见摘要/候选触发文本，其作用受 policy 控制。修复 glossary 自相矛盾。
- `my-ask-matt`：route set 由 portfolio/composition 校验；主链在 implementation 完成后按需进入 test report。四个遗漏入口全部获得明确归类。
- `my-triage`：保留外部 Tracker 的原生状态/brief 流程；仅移除不完整的本地 implementation Ticket 模板，本地分支把已确认 brief 及来源 lineage handoff 给 `my-to-tickets`。修正旧调用名与固定 `CONTEXT.md`。
- `my-install`：从 install state 找绝对 runtime；`deploy` 明确要求 workflow source root；安装/回滚不依赖目标项目 cwd。
- `my-prototype`：以“记录结论并 handoff”结束；生产吸收只能由已批准 `my-implement` work unit 完成。
- `my-wayfinder`：为每个 composed method/handoff 提供明确指针；地图格式、Ticket 格式和类型词典下推到 reference。
- `my-tdd`：采用标准 red-green-refactor 主导词；共享 testing-seam reference 统一公共/内部 seam、adapter/mock 规则；TDD 顶层只保留循环与完成门。
- `my-tech-design`：checker 只保留通用结构规则；删除历史术语词表；无 `visual_intent` 时删除整块可选图；default prompt 与阶段合同一致。
- `my-wizard`：任何 secret 落盘前检查目标未 tracked、已 ignored，并将权限收紧到 0600；不满足时停止或只写已获明确批准的安全目标。
- `my-to-questionnaire`、`my-test-report`：统一使用 artifact storage adapter 和 `.agent/work/<topic>/<type>/`。
- `my-edit-article`：用户已明确要求原地编辑即为授权；只有范围变化或 profile gate 要求时再确认。
- 长 Skill 只下推分支专用模板/参考；reference-only Skill 不为追求统一而强加步骤。
- review finding 共性抽到一份 shared contract；专项 Skill 仅保留独有判断与输出差异。

`my-requirement-analysis` 本轮保留入口但重构为短合同：明确用户调用后，先形成主 Agent 摘要；简单请求快速通过，复杂或隐含请求交给一个独立 reviewer；没有 sub-agent 能力时标记 independence evidence gap，不伪造独立性。完整 reviewer brief 下推到 reference。退役/合并要等 comparative 证据，不在本轮静态判断中决定。

### 6. 验证与证据

`check` 继续只代表 static/unit/deterministic-contract，但增加 portfolio、严格 state/path、release closure 和 Ticket/run contract 测试。另提供 `release-candidate-check` 或等价报告：

- critical fresh-agent cases 必须 `pass`；blocked/inconclusive 不算行为通过。
- 记录 release manifest digest、宿主、模型、输入/输出或 artifact digest 和 rubric observations。
- baseline/candidate 使用相同模型、reasoning、权限、输入和评分规则。
- 非 critical Skill 可声明 exemption，包含理由、风险和后续验证条件。

## 实施批次

### 批次 A：安全封口

1. 安全 path/state/capability kernel与独立 ownership registry。
2. installer、work-artifact rollback、artifact-review finalize、build staging 与 prune 接入。
3. release 精确闭包、ID 绑定、确定性 walker及根级 sidecar 可达性。
4. byte-exact 源码快照；完整门禁与打包读取同一快照，并发变化触发重试或 fail closed。
5. 并发 lock、quarantine 与故障注入测试。

完成条件：三个已复现的越界删除 case 全部在任何目标变化前 fail closed；foreign Skill sentinel、repo root victim 和伪造 review directory 均保持 byte-identical；伪造 build staging、foreign/corrupt release prune 也不能触发递归删除。

### 批次 B：Ticket/Run 单一事实源

1. 收紧 admission、依赖图与 approved scope。
2. 分离稳定 Ticket definition 与可变 execution state，统一 lifecycle service 与 attempt/claim。
3. 结构化 source/test/review/code receipts。
4. 激活 profile 的 custom standards/domain sources。
5. external write capability。

完成条件：所有旧旁路均复现为拒绝；代码、规则、profile、Spec 或 Ticket definition 任一漂移都会使提交 stale；合法 claim/status/acceptance observation 不会误判 definition stale；依赖环返回 invalid，不返回 complete；中断的双文件投影可由 WAL 恢复。

### 批次 C：Portfolio 与宿主投影

1. 建 registry 和全量校验。
2. 移除硬编码 Skill 数量。
3. 统一 route set、调用宏和安装投影。
4. direct resource consumer 派生与审计。
5. 新增 doctor。

完成条件：37/37 恰好登记；router 宏与 routed edges 双向一致；零悬空 edge、零未分类入口、零 raw host-specific 调用；三份 target manifest 闭合；doctor 能准确报告当前 37/34 源树/部署漂移。

### 批次 D：Skill 合同与信息层级

按“治理词汇 → 错误产物/越权 → 调用可达性 → 共享事实源 → 蔓延”的顺序完成定向重构。

完成条件：本 spec 列出的每个 Skill 失败路径都有静态或 deterministic regression；五个长 Skill 的每条实际分支仍可由顶层强指针抵达，模板和参考不再遮蔽主要步骤。

### 批次 E：发布候选与行为审查

1. 运行 affected tests，再运行完整 203+ suite、`validate-evals`。
2. 构建全新 release；运行 `check`。
3. 在临时 Codex/Cursor/Claude home 执行 clean install、34→candidate、37→candidate、candidate→previous rollback。
4. 用当前模型/default reasoning 对 critical affected flows 做 fresh-context review/smoke，并保存原始证据；不升级模型。
5. 运行 doctor；真实宿主保持不变，除非另获安装授权。

完成条件：static/unit/deterministic/release/install/rollback 全过；fresh-agent 的 pass、fail、blocked、inconclusive 如实分开报告；工作树只包含本 spec 授权的源文件与测试改动。

## 兼容、迁移与回滚

- 保留现有 release，不原地修改；candidate 使用新 ID。
- current 只在 candidate 完整构建后原子切换。
- install state 和 journal 使用新版本时继续读取已验证的旧 v1/v2/v3；未知或损坏版本 fail closed。
- 兼容 CLI 入口至少保留一个 release，内部委托同一严格 service，并输出迁移提示。
- Skill 调用宏只在安装 staging tree 投影；portable release 保留宏，三宿主安装结果分别验证。
- 删除/合并 Skill 需要 retirement map；本轮不退役任何 Skill。
- 故障或行为证据不足时，可回滚到 `runtime-session-contract-v6`；当前宿主引用的 `shared-rule-review-v1` 在真实安装升级前不得清理。

## 验收标准

- [x] 三个已复现的路径/状态越界删除用例均 fail closed，目标未改变。
- [x] 损坏 install state、未知版本、非法 Skill 名、越界 home 在创建 transaction 前失败。
- [x] release 拒绝额外根文件、额外 Skill、遗漏文件、hash 漂移和 manifest ID/目录不一致；verify-current 单独拒绝 current 漂移，显式旧版安装和回滚仍通过。
- [x] 两次干净构建在排除 release ID 后产生相同 manifest/content digest，且不含缓存或临时文件。
- [x] build 门禁与打包读取同一个稳定源码快照；并发删除、恢复或改写 Skill 时不会生成混合 release，也不会把瞬时缺文件误报成 walker 缺陷。
- [x] build/prune 共用 releases mutation lock；candidate 发布与 current 切换之间不存在可删除窗口。
- [x] install 与 work-artifact 在 transaction tree 已合法变化、进程硬退出后仍能凭稳定 control receipt 恢复；伪造 control/journal 仍 fail closed。
- [x] 所有 Ticket 入口使用同一 admission；Wayfinder Ticket、已认领/受阻塞/无验收 Ticket 均不能进入 implementation。
- [x] 依赖环、无候选但未完成、approved scope 缺失分别返回 invalid/blocked，不返回 complete。
- [x] 完成只能从合法 phase 发生，且 test/review/code/source receipts 全部匹配当前稳定定义；claim/status 等合法可变状态不污染 definition receipt。
- [x] custom standards/domain/profile/rule 文件进入 work unit 并在漂移时使其 stale。
- [x] Ticket 的 `spec_ref/spec_id/spec_revision` 与同 topic Spec frontmatter 不一致时，在 run 创建前拒绝。
- [x] completed 只接受 runtime 登记且可重验的 test/review evidence；review 必须由 runtime 执行 profile 预声明命令并采集 stdout，调用者结果文件、未声明命令、手拼 pass dict、非零退出、evidence/result/code 漂移均拒绝。
- [x] external write request 必须与宿主可信确认 receipt 及 runtime scope capability 的 kind/target/operation 匹配；缺可信 receipt 时回到实时确认。
- [x] portfolio 对 37 个 Skill 一一闭合；route、composition、resources、evidence 无悬空关系。
- [x] 三宿主调用投影正确，投影后完整 target manifest/digest 匹配，可移植 Skill 源码无未声明的宿主专属调用。
- [x] `my-triage` 不能再产出无法准入的 implementation Ticket。
- [x] `my-prototype` 不再直接修改生产模块；`my-wizard` 不把 secret 写入 tracked/unignored 文件。
- [x] TDD、seam、invocation、artifact storage 和 review finding 各自只有一个权威定义。
- [x] `my-tech-design` 的默认动作、模板与 checker 对任意主题一致。
- [x] `my-ask-matt` 对所有 routed Skill 完整，test-report 生命周期单义。
- [x] 受影响测试、完整 unittest、`validate-evals`、新 release `check`、三宿主临时安装和回滚全部通过。
- [x] fresh-agent 证据等级与结果如实报告；没有行为证据的 Skill 不宣称已验证有效。

## 依据与未知

- 以上安全与契约缺陷来自当前源码和临时目录复现，属于 confirmed repository/execution evidence。
- 37 个 Skill 的 prose 有效性大多仍只有 static evidence；本次只修复有明确失败路径或单一事实来源冲突的部分。
- `my-requirement-analysis` 是否最终保留、专项 review Skill 是否应隐藏为 method，需要 comparative forward test；当前保留并显式登记证据缺口。
- HTML 的真实 viewport、打印和键盘行为仍需浏览器或人工验证；静态 checker 通过不等于视觉完成。
- 本地 runtime 能证明预声明 reviewer 进程确实针对冻结 snapshot 执行并返回了什么；它不能对抗拥有同一 OS 用户权限、可改写可执行程序或运行时本身的恶意进程。需要更强独立性时，必须由宿主隔离 reviewer 并签发 runtime 可验证的 attestation。
