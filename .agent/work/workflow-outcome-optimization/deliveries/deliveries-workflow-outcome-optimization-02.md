# workflow-outcome-optimization revision 2 工程交付

已完成批准的 revision 2 源码、26 项验收证据和完整源码包；采用 direct-engineering。前三组在隔离 worktree 并行施工，根 Agent 串行集成；独立审查使用新上下文和冻结源码。没有用本 workflow 自身 Skill/runtime 管理施工，也没有生成产品自签完成回执。

Spec 原文保持，SHA256 `efd7c71b787657623b1d5d58a817330cdbf32b5f532b5d55192db2c3cbe72d13`。Spec 中阶段字段保留定稿时事实；后续授权及验收事实记录在本交付与普通工程 Ticket，不回写定义历史。基线提交 `7947cb28e37512ab52a0c87c2cfd736bc3205c25`；最终本地提交以 Git log 为准。

## 改动及作用

| 范围 | 改动 | 防止的失败 |
|---|---|---|
| runtime 事实层 | 共用命令、环境、内容身份与冻结字节事实；各 scope 保留各自的成功策略；失效结果重新判断 | 重复事实实现漂移、旧成功沿用、内容/定义/环境变了仍宣称完成 |
| 完成判断 | 缺依赖与实际失败分开；loader 同一粗身份不能证明行为相同；完整/截断记录及旧错误缓存重新核验；自审阻断、Spec challenge 和 reopen 历史保留 | 实际 Assertion/RuntimeError 被算作 known，部分执行失败被算作环境缺失，未解发现绕过收口 |
| 执行与审查 | quick 摘要只需有意义的证据类别；几何位置与 diff 体积作线索；真实矛盾、证据及预算仍决定停止；status 和末票 finish 共用下一动作 | 空表格负担、启发式误停、下一步不可执行 |
| 安装升级 | 单次命令按不可变内容共享验包，锁内重核；可信输入摘要与旧包回退；内容投影；同版核验实际 runtime；变化 deploy 在稳定快照只运行一次完整 suite | 重复验包/复制整树、摘要或旧 manifest 掩盖损坏、无变化重写宿主 |
| 安装保护 | 回滚前验备份；拒绝 runtime 额外链接/特殊文件；首次安装父路径、旧 recorded roots 在 resolve/写入/迁移前验身份 | 恢复损坏备份并删证据，链接将安装或迁移引向外部目录 |
| 指令衔接 | 授权、存储和 setup 有唯一来源；triage 从已确认 brief 建合法 Spec/Ticket 血缘；既有授权与阶段止点明确；未知外部结果先查原身份 | 循环确认、缺 Spec 卡住、越阶段继续、未知结果直接重试写入 |
| 需求与测试 | 用户原话、代码事实、推断与承重假设分开；跨 Ticket 的用户结果有验收 owner；真实入口、存储、重开、消费者接线以及多对多 AC 证据 | 只测 helper/adapter、自证 oracle、每张票都绿但用户结果缺失 |
| 排障与写作 | 保存症状、环境及可区分证据；详细排障方法按需；表达按读者选择；区分静态代码、实际执行和未知动机 | 秒级复现/固定假设数挡住推进，图示/词汇流程替代写作判断，测试报告写出未发生的事实 |

这次精简的是重复职责、流程与验证工作；新增正确性检查也增加了代码和显式条款，没有宣称所有文件或 runtime 总行数变少。

## 完整替换与兼容

完整源码包：[workflow-outcome-optimization-source-02.tar.gz](workflow-outcome-optimization-source-02.tar.gz)。包含 281 个最终源码文件以及本次交付、索引、Ticket 和验收说明；`package-manifest.json` 记录全部文件 SHA256、mode 和删除路径。包内字节及 mode 均已核验。源码身份记录在 `../evidence/final-source-identity.json`；包外 SHA256 校验记录在仓库的 `../evidence/source-package-identity.json`。

推荐在独立目录展开并核对后用于源码替换；覆盖旧源码时，必须按 `removed_paths` 删除以下五条已合并路径，并保留既有项目数据和其他 Topic 历史。该源码包没有 Git 元数据、旧 Topic、发布目录/current 指针、缓存或真实宿主状态；不会替用户完成真实宿主升级。

- `policies/decision-taxonomy.md`
- `policies/project-discovery.md`
- `policies/project-storage.md`
- `policies/write-boundaries.md`
- `resources/adapters/write-actions.md`

对象归宿索引 `../evidence/outcome-instructions-object-dispositions.json` 覆盖 32 Skills、原 39 共享对象及 1 新参考，共 72 对象：23 KEEP、43 MODIFY、6 MERGE。MERGE 包括保留路径的内容迁移，实际删除上述 5 路径。67 个保留/新增候选内容哈希核验匹配；消费者及按需触发明确。

旧活动记录按当前定义重核；缺乏可证明证据时要求重跑。已完成历史不改。不同版本 writer 同时修改同一活动状态不支持。独立审查、引用/快照完整性、宿主锁、staging、最终验证、回滚及非托管路径保护保留；旧包缺输入摘要时仍走完整内容比较。

## 最终验证

- 最终冻结 `final07`：281 文件；清单 SHA256 `0f7c4296a473ec1df31e3e61f87d8a861aa2ef6eaaa904a46c4c85ae4ecd3eb1`。运行结束后当前源码逐字节匹配，Spec 和其他已跟踪 Topic 历史保持不变。
- 最终全量 unittest：**338 tests / 409.614 秒 / exit 0**。命令、退出码、耗时及日志摘要在 `../evidence/outcome-integrated-full-07-result.json`，完整输出在同名 `.txt`。
- `workflow.py validate`：`VALID skills=32`；生产源码及本次编写文档的差异空白检查通过；原始日志/补丁按原样保留。validator 只作被测静态检查，不作施工控制器。
- 独立审查累计报告 17 个阻塞，全部修复并在对应限定范围复核，当前未解阻塞 0。最终 runtime 短诊断/旧缓存复审见 `../reviews/outcome-review-runtime-06.md`；安装最终限定结论通过，9 个相关文件与已审版本逐字节相同，见 `../reviews/outcome-review-install-04-final07-binding.json`；指令修复复审 0 blocking，两个 advisory 已按原文修正并核对。范围及真实 agent 身份见 `../evidence/independent-review-provenance.json`。
- 原始反例、失败与成功日志均保留。完整 suite 的过程记录：01 为 312 tests/exit1（两条旧 policy 断言），02 为 325/exit1（设计路由旧断言），随后 03–07 为 325/328/331/335/338 tests/exit0。这些早期绿色版本仍有独立反例，均未当最终交付。首次预检查的 4 errors 是 README 链接未进快照；修正后打包测试通过，不记为干净基线。隔离作者与 reviewer 日志不替代最终完整 suite。

共享断言按当前契约更新：Force Push 查唯一安全来源，冲突处理查既有授权，普通 smoke test 不等于退役 smoke CLI，seam 包含实际消费者，tech-design 只验实际设计入口。正文语义仍交独立审查，而非靠字符串测试自证。

安装同一最小 fixture 的工作计数：完整验包 **4→1**、临时源码打包 **1→0**、验证投影整树操作 **15→0**，suite gate 保持 **1**。最终版本计数再次核验；fixture 使用 stub suite 隔离阶段，所以耗时不作为真实工程提速比例。实际公开 deploy 单次完整 suite 与失败不发布由单独回归验证。原始及最终计数见 `../evidence/outcome-install-benchmark-before.json`、`outcome-install-benchmark-final07.json`。

主链所有按需分支 Markdown 并集 **38,356 字符**（旧 33,919，原规模基准 58,213），九个主链入口 15,774、按需参考 22,582；94 可达文件、34 唯一内容。九个源入口正文另一口径从 15,233 增至 15,886。血缘、授权、恢复与证据需要显式规则，有真实上下文代价；并集不等于一次任务常载，没有读取追踪就不能宣称实际常载上下文下降。

## 七项能力的检验

完整运行说明：[outcome-evaluation-runbook.md](../evidence/outcome-evaluation-runbook.md)。它为七项能力定义机制、代表任务、指标及限制；真实任务覆盖需求歧义、跨票交付、存储/重开、难复现 Bug、接口变更、文档面向不同读者、环境缺依赖、失败自动化和未知外部结果。

| 能力 | 待检验的改进 | 观察方式 |
|---|---|---|
| 任务完成率 | 少误停，下一步可执行，必要恢复优先 | 全部已分配任务为分母，统计正确完整交付、阻塞和超时 |
| 准确率 | 实际失败、自审阻断与过期证据不能绕过完成 | 独立验收错误、回归、错误完成声明 |
| 需求理解 | 来源、关键假设及用户结果 owner 明确 | 隐藏用户 oracle、关键约束遗漏、无必要追问 |
| 文档写作 | 按读者组织，执行事实可追溯 | 人类与 Agent 文档的理解/执行正确性，事实错误 |
| 代码实现 | 真实消费者与持久状态覆盖 | 公共入口、关开重启、独立 oracle 和跨票结果 |
| Bug 排查 | 证据区分假设，减少固定门槛 | 定位正确性、回归、证据采集成本与错误修复 |
| 自动化 | 复用既有授权，未知结果先查身份 | 无人干预的正确完成、重复写入、越权/失败恢复 |

比较时固定模型、预算、起始源码与环境；旧/新版本用同类独立任务，保留全部分配样本；首次独立验收与修复后最终正确分别统计，blocked/超时/环境失败不静默剔除。越权不能算自动化成功。当前完成的是机制、机械回归、隔离 CLI/安装探针及独立场景审查，**没有同条件模型效果试验，不能承诺七项能力或一次做对率已提高**。

## 交付状态

源码实现、普通工程验收、完整源码包和本地提交已完成。远端 push、发布、真实宿主安装及模型效果试验未执行；临时 fixture 不代表真实宿主或上线验证。
