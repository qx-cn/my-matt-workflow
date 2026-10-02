# workflow-outcome-optimization 独立设计审查

- 审查者：新上下文独立审查；与作者同模型/档位，无升级。
- Spec：`7835aae695f1ee46dd8c133dc21153a847721b6ee08356394eebf530a89a8c16`，只读 `/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-7835aae695f1-ijhjgecm/000-specs-workflow-outcome-optimization-01.md`。
- 当前源码：`36ce314358fac1f680ba8c536ef07e1f594964478395a56578923248445b91b0`，只读 metadata 映射的 snapshot_path。代码位置以下用 source_path 相对仓库路径表示；全部读取来自固定目录 `/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-36ce314358fa-21w4czad/`，未读可变源码作为证据。
- 已逐文件核验 Spec 1 个、源码/测试/历史 522 个快照的 size/SHA256，均匹配 metadata。没有修改源码或 Spec，没有运行全套测试，没有 finalize。
- 公共 CLI 探针是作者提供的确定性 fixture 证据；结论另以源码独立核验。额外只运行精确快照抽取的 compare 函数边界探针，结果 `/tmp/my-matt-quality-spec-review-probe.json`，不构成宿主/LLM 效果证据。
- 本轮：一次全面设计审查。结论：**findings / 需修订**；两项 blocking，均建议 fix-in-batch。核心机制成立，无需要新开产品对齐点的语义挑战。修订后最多一次差异复审。

## 1. 承重断言核验表

| 断言 | 状态 | 独立核验依据 | finding_id |
|---|---|---|---|
| §2 基线不可运行可吞掉当前已执行失败，并允许普通收口 | verified | `tools/workflow_lib/batches.py:199-216` 先 old.unavailable→continue；`:230-234` 只查 new_failures；`:289-295` 据此关闭。公共 CLI baseline-recovery 文件确有 exit_code=1/执行失败而 new_failures=[]，closed；新抽取探针重复该 compare 结果 | — |
| §2 登记自审 blocking/spec-challenge 后仍可 finish | verified | `batches.py:108-138` 验证并保存 findings，`:141-147` require_self 只查绑定/章节；`ticket_completion.py:28-43` 消费该门禁。公共 CLI self-findings 文件分别完成两种 fixture | — |
| §2 当前 pass 可被重叠行/体积信号硬停 | verified | `review_loop.py:88-109` 两项信号无 pass 例外；`ticket_review.py:361-365` 据此 stop。停止探针 SHA 与固定 `509-review_loop.py` 匹配并给出 pass 两种停止原因 | — |
| §4.5 表格的“任意基线＋当前完全不可运行”可统一归为未验证而沿旧策略披露 | mismatch | 现版 `batches.py:205-206` 对 runnable baseline/current unavailable 明确新增失败；`:234`、`:289` 阻断。独立抽取探针返回 failure=当前环境无法运行、unverified=[]；与“不退化现有正确行为”不符 | DR-01 |
| §3 旧活动会话按旧协议恢复，同时 AC01/AC02 新完成保证适用范围明确 | mismatch | `batches.py:85-90` 保留无 batch 旧协议；implementation record `ticket_implementation.py:238-242` 无协议版本；`topic_service.py:61-67` 只有项目 schema_version=2；旧 writer 的 `require_self/tests_passed` 仍忽略新版门禁，且没有定义新runtime恢复旧记录时是否重新评估 | DR-02 |
| §2 local triage 无 Spec 血缘的调用缺口 | verified | `skills/my-triage/SKILL.md:54`、`composition/manifest.json:84-87` 直接交 to-tickets；`my-to-tickets/SKILL.md:12-14,22` 需 current Spec/血缘，`my-to-spec/SKILL.md:10,16-18` 已有可复用 confirmed input 与唯一设计关口 | — |
| §2 旧 Topic test/review 和重复授权静态冲突 | verified | `resources/adapters/work-scope.md:3` 多 Ticket 要 Topic test/review，而 `implementation-session.md:9` 可选；`user-intervention.md:3,8` 已授权持续与每次问并存；merge-conflict policy `:3-5` 再次批准所有可逆处理 | — |
| §4.4 验收独占测试/禁止旁路存储验证确有原文 | verified | `my-implement/SKILL.md:10`、`workflow-delivery.md:24` 禁共用；`my-tdd/SKILL.md:26`、`my-tdd/tests.md:45-60` 将不经接口 DB 查询普遍列反模式。共享 seam 的 `:3-9` 则已有风险/稳定边界原则 | — |
| §4.4 生产+测试两个 adapter 数量被用来决定 port | verified | `my-codebase-design/DEEPENING.md:29` 数量门槛，`testing-seams.md:7` mock 不能证明价值。只证明文本约束及可达风险，不证明实际项目普遍造抽象 | — |
| §4.6 保留既有代码四轮/三修复与文档全面+一次复审 | verified | `resources/review-loop.md:21,34`；`review_loop.py:108-109` 及 review open 的轮次准入，Spec改变几何信号并没有提案解除预算 | — |
| §5 已有固定未中断上下文、按空间优先错误交接与图示硬选型 | verified | `context-hygiene.md:3,7`；`my-ask-matt/SKILL.md:22-28` first-match；`visual-communication.md:3-13` 必须图示/none阻断；用户当前表达原则直接否定默认偏好图示 | — |
| §5 当前打包不等于资源始终常驻，composition/resource manifest 各有职责 | verified | `resources/manifest.json:204-212` 声明 policies 分发消费者；`composition/manifest.json:38-87` 明确 method/chain/handoff；安装适配从 install-state runtime_entry 读取。没有把包装大小当实际上下文使用 | — |
| §2 522 文件、32 Skill/30 resource 文件/7 policy 的规模 | verified | metadata artifacts 522；路径集合有32 `SKILL.md`、28 resources Markdown加2 JSON、7 policy Markdown | — |
| §2 历史证据说明曾有迁移歧义、验证假阳性等设计返工；不能证明现版仍错或候选净收益 | verified（历史记录层） | 快照 `.agent/work/skill-architecture-optimization/reviews/reviews-skill-architecture-optimization-v1.md:13,19-35,44-48` 记录17处订正与证据边界；`.agent/work/workflow-first-principles/reviews/reviews-first-principles-deep-review-03.md:13,34` 明确 self/deterministic不等于comparative。只确认历史记录存在，不确认每项历史事故或真实项目发生率 | — |
| §2 当前宿主 runtime=20261002-093849、源码 HEAD=c10906c | unknown（来源元信息） | artifact metadata 固定字节与content_id，但不含当前宿主 install-state 或Git HEAD证明；本审查按指派不读可变宿主/源码。固定字节与现版机制可独立核验，因此不影响两项设计发现或核心成立 | — |

## 2. 审查发现

### DR-01：任意基线的当前不可运行结果会放宽现有回归阻断

- 位置：Spec §4.5 第113行及第116行、AC01；代码 `batches.py:199-216,230-234,279-295`。
- 视角：correctness / impact；严重度：blocking；建议：fix-in-batch。
- 可达场景：全量测试在基线正常运行；候选改动破坏依赖/加载，使当前在执行验收前报 ModuleNotFoundError。现版将它记录为“当前环境无法运行”的新增失败并阻止 batch close。Spec表格却规定任意基线下当前完全不可运行都按未验证披露，且第116行允许非必要环境缺口按旧策略披露。实现若照表处理，就可能把新出现的无法执行降为缺口，放宽已存在且正确的阻断。是否来自代码回归或外部环境尚未知时，也不能由 Agent 把它先分类成不必要。
- 依据：独立抽取当前 compare 的探针，runnable_baseline_current_unavailable 返回 new_failures=[当前环境无法运行]，unverified=[]。这是精确函数机制证据，不是假设现有 Agent 已发生该回归。
- 最小修改：区分“基线/current均不可运行”与“基线可运行、current不可运行”。后者保留现版新增失败阻断；环境事实与必要性不足不能自动降级。前者继续按现有证据/风险策略披露。AC01加该不退化行为，避免仅覆盖作者探针。
- 最小验证：公共 CLI 一组 runnable baseline→current import/command missing，应拒绝普通close；baseline/current均不可运行按明确的披露策略；已有partial execution failure仍阻断。无需语义日志平台或新普遍审批。

### DR-02：旧活动状态和旧宿主写入的兼容边界未定义，可能继续绕过新版门禁

- 位置：Spec §3 第50-53行、§4.3/4.5/4.6、AC01-03/AC16；代码 `batches.py:85-90,108-147,199-216,230-234`、`ticket_implementation.py:238-242,356-397`、`topic_service.py:61-67`。
- 视角：impact / correctness；严重度：blocking；建议：fix-in-batch。
- 场景一（同一候选runtime恢复）：旧活动记录已包含当前失败，却因旧比较缺陷生成 new_failures=[]；或旧记录含 blocking 自审。若“按其协议恢复”被当作旧记录祖父豁免，升级之后仍能沿旧结论收口，与候选版本完成保证冲突。只缺 findings 字段的旧自审也不能变为“无发现”。相反，如果新版门禁直接读取所有历史 blocking而不按当前绑定处置，又会永久阻断已修复工作。Spec目前没有定义这些活动记录的可观察恢复结果。
- 场景二（多宿主切换）：Codex装候选而Claude/Cursor仍用旧release，均指向同一项目schema_version=2与活动Topic。旧代码能读取记录，继续忽略self findings、只看new_failures，并成功finish/close。包的新增约束无法让旧writer自动遵守；§3未说明这一组合不在支持范围内。
- 已核实事实：当前只校验项目schema_version=2，batch/implementation unit没有能使旧runtime拒绝新门禁的协议版本；现版完成判定确实忽略上述语义。这里是支持边界缺失，不指控当前存在并发攻击或要求重造全局版本架构。
- 最小修改：明确保证限于候选runtime执行的新工作与其成功恢复的活动工作；“成功恢复”须包括当前证据/未解决发现/停止原因重新评估和必要证据重采，不能仅指JSON读取成功。当前失败不能受旧new_failures=[]豁免；缺finding记录保持unknown；几何停止留下有效当前pass时定义受控恢复结果；已完成历史只读保持。旧writer与候选混写同一活动Topic明确不支持。发行切换前盘点实际参与宿主版本并给可审阅切换方案，安装/必要迁移另行授权；不默认自动迁移旧project，不要求额外全局协议。
- 最小验证：public CLI恢复旧raw-failed/new_failures=[]、旧blocking/spec-challenge、无findings字段、已修好但旧geometry needs-user、无batch legacy active，确保候选恢复行为/next_command与完成保证一致；发行说明明确旧writer混写限制，切换方案有参与宿主清单。无需运行旧/新writer并发来宣称支持不存在的兼容承诺。

## 3. 已考察但排除的风险

- **本轮自动越阶段实施**：排除。Spec开头、第6/9节明确本轮止于诊断/方案/Spec，pending-user-review；不自动拆Ticket、开工、push、install或migrate。各行为改变是提案，不能把“当前有draft”当作已经批准执行。
- **取消重复确认就获得任意外部写权限**：排除。§4.1授权按同一动作、目的地、范围和限制判断，未授权目标与超范围仍询问，宿主拒绝仍有效；是消解重复局部规则，不扩大默认写范围。
- **移除几何停止信号会无限返工/改变预算**：排除。§4.6明确保留四轮/三修复和文档全面+一次差异复审，以及真正未解决失败、Spec挑战/未知；只把位置/体积从因果结论退回观测信号。
- **triage插入to-spec会重复访谈或设计审查**：排除。§4.2要求复用confirmed brief，匹配Spec才直接to-tickets，风险设计审查在唯一关口。现有to-spec已接受已确认需求、不重新访谈。
- **多对多验收映射会允许一个绿smoke遮蔽全部验收**：排除。§4.4逐验收要求能区分成功/失败的可定位断言；一个验收也可需要多个层级证据。解除的是case独占，并未解除覆盖。
- **允许DB验证会强迫暴露内部接口或制造ports**：排除。§4.4限于持久化/事务/迁移/恢复等本来就是契约的风险；普通模块优先稳定seam，替身不自动证明新抽象价值，AC08保留既有边界。
- **quick精简输出会省掉必要验证**：排除。§4.2/4.3及AC13保留每项验收、影响/关键失败路径、实际证据和缺口；文本和runtime必须同步修改（现版topic_service.check_summary确实机械强制六节）。不需要为所有quick填高风险空节。
- **默认取消独立review或升级成本**：排除。standard批次独立review、高风险触发与用户不可替代的独立性要求仍保留；同会话只算self；明确不自动换模型/档位。新上下文provenance是宿主证据边界，不要求本地runtime证明认知隔离。
- **全部resource包装将被误算成常驻context**：排除。§5主动区分packaging与实际读取，消费者/触发/单一来源清单；不默认移除unknown价值资源，不强制常驻全部材料。
- **静态修复被称为强模型交付效果提升**：排除。§2/7/8/9分别区分static、deterministic probe、historical与comparative；没有同条件结果不称一次做对率提升；真实效果试点不成为本轮发布门禁。
- **同名测试比较被宣称穷尽回归**：排除。§4.5第118行主动承认证据粒度限制，关键验收仍核实行为；不立即扩展通用日志语义分析。
- **需要新全局schema/更强审查模型才能修兼容**：排除。DR-02支持范围限定、候选runtime重评活动证据、参与宿主切换即可获得所承诺结果；强制新全局协议/升级模型没有本轮证据，属于不必要扩大。

## 4. 待用户确认的需求语义假设

无。原Spec把调整全部标为待用户审阅提案；本轮阶段止点、用户授权持续、表达选择原则和禁止自动模型升级均已有明确输入。两项发现是可查事实与契约内部边界，需要作者订正文稿，不需要额外访谈或新产品决定。将来用户仍需在既有对齐点批准候选实施范围；该普通批准不是本审查发现的新语义假设。

依据与未知：真实宿主当前release与源码HEAD来源元信息未在固定metadata独立证明；现版/候选实际材料读取、真实任务一次做对率和比较净收益仍无数据。前者不影响已固定字节机制判断，后者已在Spec明示并留第8节独立试点，不因此伪造效果结论或给结构修复增加门禁。
