# workflow-simplification Ticket 拆分审阅

来源：Spec workflow-simplification revision 1。分类：routine，安装 runtime decision-gate 返回 allow。后端 local；14 张 implementation Ticket；execution_agent 全部 auto；未解决规则冲突 0。

源 Spec 为首版，没有 supersedes，也没有已有 Ticket；无需修订未完成 Ticket或补偿已完成工作。原 Spec 不改。项目当前配置 schema 1 与 test_commands 空值保持原状；施工不强制使用本工作流 runtime/Skill（源 Spec 施工顺序末句），也不把新模型提前当成当前项目策略。完成 Ticket 拆分不表示实施、提交或安装获批或已完成。

本拆分不是跨目录机械重命名：每个普通 Ticket 交付可独立验证的 CLI 或 Skill 行为，随切片交付测试。01 是 Spec 明确要求最先完成的基线准备。09 将相互依赖的 Skill 集合、引用、投影、构建校验放在同一切片，避免安装件引用已删除入口。13 负责最终命令集合与集成验证；阶段中未完成的删除项不算最终兼容承诺，不得把旧 runtime 包一层当新 runtime。各阶段只承诺自身交付与相应回归；全仓最终 check 的 green 由 13 承诺。

14 的配置测试命令采用 `python3 -m unittest discover -s tests`，承接现有 unittest 写法并匹配全部 Ticket 声明。最终仍按 Spec 运行 `python3 tools/workflow.py check`；不把 check 和它内部执行的 unittest 同时配置为两条全量命令，避免重复运行同一套测试。实际实施可按 Spec 直接使用 CLI/测试，不受空旧配置测试列表阻断。

## 编号方案

1. **[保存施工前样例与文本量基线](../tickets/tickets-workflow-simplification-01.md)**
   - 被谁阻塞：无。
   - 交付什么：在旧版行为仍可运行时，生成迁移将使用的真实旧格式样例，并记录可重复测量的主链文本量。后续施工可验证历史产物，而不靠手写猜测旧格式。
   - 适用规则与影响区域：施工顺序第 1 步；第 9、10 节；AC-34 基线、AC-35 样例来源；tools/**、tests/**、evals/fixtures/**；先完成本 Ticket 再修改旧版格式或删除功能；不部署、不安装、不在其他项目迁移。

2. **[创建配置 v2 与可完成的 quick Topic](../tickets/tickets-workflow-simplification-02.md)**
   - 被谁阻塞：01。
   - 交付什么：用户可预览 setup、写入新配置，在干净内容上启动 quick Topic，测试并提交、归档；同一套定位规则可以只读查看多个 Topic。
   - 适用规则与影响区域：M1、M2、M5 quick/文档、M6、M7；第 2、5、6 节；AC-04、05、06 显式启动、14 Topic 定位、25 显式启动与文档；tools/**、tests/**；先在临时仓库验证新配置；本仓库配置留到最终收尾转换；quick 摘要逐条映射验收与不同测试，由 Skill 在后续接入。

3. **[从 Ticket 启动实施并登记真实测试](../tickets/tickets-workflow-simplification-03.md)**
   - 被谁阻塞：02。
   - 交付什么：用户选择合格 Ticket 后获得执行简报，并直接运行其声明的测试；失败和定义变化不会被误判为可以完成。
   - 适用规则与影响区域：M1–M3、M5 记录绑定、M6；第 3 节；AC-06 自动补建、08、10、12、14 Ticket 定位、25 自动补建入口；tools/**、tests/**；以外部 CLI 和内容状态测试，argv 不经过 shell；简报不进入 Spec 血缘。

4. **[冻结完整审查材料并校验结果](../tickets/tickets-workflow-simplification-04.md)**
   - 被谁阻塞：03。
   - 交付什么：审查者获得与当前内容绑定的材料包和预填结果骨架；只填写判断字段即可提交，格式错误明确指出字段。
   - 适用规则与影响区域：M4 材料与结果、M5 绑定；第 3、4 节；AC-11、13、16、21；tools/**、tests/**；runtime 不决定宿主模型，不把自审冒充独立；循环规则文字接入由后续 Ticket 完成，本阶段提供材料与结果边界。

5. **[按五步完成并提交单张 Ticket](../tickets/tickets-workflow-simplification-05.md)**
   - 被谁阻塞：04。
   - 交付什么：一张干净的 Ticket 可沿 start、test、review、review submit、finish 完成；runtime 自动绑定证据并提交，Agent 无须手写哈希。
   - 适用规则与影响区域：M3、M5 finish/单 Ticket complete、M6、M7；AC-03 提交、07、09、25 单 Ticket 收尾；tools/**、tests/**；测试失败、内容变化、缺失审查和未勾验收均不能绕过提交门槛；不推送。

6. **[限制审查轮数并处理 Ticket 裁决](../tickets/tickets-workflow-simplification-06.md)**
   - 被谁阻塞：05。
   - 交付什么：审查遇到上限、停止信号或设计问题时停止；用户接受可完成 Ticket，修订定义后重开可继续实施。
   - 适用规则与影响区域：M3 定义变化、M4、M5 Ticket accept；第 4 节；AC-17、18、19；tools/**、tests/**；只 reopen 能重置 runtime 轮数；不因同会话重复派审重置；接受不能绕过测试。

7. **[审查整分支并完成或放弃 Topic](../tickets/tickets-workflow-simplification-07.md)**
   - 被谁阻塞：06。
   - 交付什么：多张 Ticket 完成后，可按全量测试和整分支审查收尾；用户可裁决分支审查，或放弃 Topic 并保留未提交代码。
   - 适用规则与影响区域：M2、M4 分支、M5、M6、M7；第 5 节；AC-20 分支、23、24；tools/**、tests/**；分支内容修复后的测试/审查必须重新绑定；归档 Topic 不写入；全量测试在每条 standard 入口与收尾检查。

8. **[预览并安全迁移旧项目产物](../tickets/tickets-workflow-simplification-08.md)**
   - 被谁阻塞：07。
   - 交付什么：旧项目先得到零写入迁移摘要，再在 apply 前备份并转换；旧的进行中 Ticket 能恢复，无法判断的条目明确列出。
   - 适用规则与影响区域：M2 迁移、M3 快照、M7 I-8/I-9；第 10 节；AC-04/27 旧格式拒绝、35、36；tools/**、tests/**；只在 fixtures/临时项目执行迁移；不操作用户其他项目，本仓库历史 work 文档不转换。

9. **[按新 Skill 清单构建三种宿主安装件](../tickets/tickets-workflow-simplification-09.md)**
   - 被谁阻塞：08。
   - 交付什么：构建输出恰好 32 个 Skill，调用方式由组合清单确定，资源仍可读取；无需正文副本，release 保留规则自动生效。
   - 适用规则与影响区域：第 7 节结构/调用边/冻结、第 11 节构建；AC-29、30、40；skills/**、resources/**、composition/**、portfolio/**、tools/**、tests/**；方法正文的主链行为和上游语义后续切片负责；本 Ticket 将结构、引用和校验一起改完，不产生引用不存在 Skill 的安装件。

10. **[接通两个对齐点与统一审查收尾](../tickets/tickets-workflow-simplification-10.md)**
   - 被谁阻塞：09。
   - 交付什么：用户在需求与 Spec/Ticket 两处对齐后，主链自动逐张实施、独立审查并收尾；文档审查也按统一停止条件记录，长期知识归于项目。
   - 适用规则与影响区域：第 1–6 节文本行为、第 9 节；AC-01、02、15、26；skills/**、resources/**、policies/**、tests/**；runtime 已强制的规则从 Skill 正文删除；手动 humanizer 保留且不成为强制步骤；冻结入口只同步许可的全局调用与交接变化。

11. **[吸收上游五项方法改动](../tickets/tickets-workflow-simplification-11.md)**
   - 被谁阻塞：09。
   - 交付什么：TDD、指令写作、阶段路由、架构改进入口和 Spec 写作采用 Spec 已明确给出的上游方法，保持冻结 Skill 方法不变。
   - 适用规则与影响区域：第 7 节吸收上游；AC-32；skills/**、resources/**、tests/**；上游内容已自包含于 Spec，不引入其他上游变更；8 个冻结 Skill 不吸收方法改动。

12. **[让技术方案保留契约并可独立阅读](../tickets/tickets-workflow-simplification-12.md)**
   - 被谁阻塞：10。
   - 交付什么：技术方案读者获得契约、接口原文、上线与回滚边界；有参考文档时沿用其体例，交付前按统一循环完成自检。
   - 适用规则与影响区域：第 8 节；AC-33；skills/my-tech-design/**、resources/**、tests/**；本 Ticket 只交付 Skill 契约与可核对材料，不执行外部写入，不声称飞书已实测。

13. **[完成命令收缩与全量行为验证](../tickets/tickets-workflow-simplification-13.md)**
   - 被谁阻塞：10, 11, 12。
   - 交付什么：check 只运行 tests，完整验证新 CLI、迁移和安装件；旧命令不可调用，主链满足文本量上限，度量可供后续观察。
   - 适用规则与影响区域：M1–M7、第 9–11 节、验证策略；AC-20 artifact 部分、22、27 新配置、28、31、34、37、38、39；tools/**、tests/**、evals/**、skills/**、resources/**、policies/**、.gitignore、.github/workflows/**；最终全量验证是集成承诺，不以静态核对代替行为验证；不构建或安装到真实宿主来证明测试。

14. **[更新使用文档与本仓库配置](../tickets/tickets-workflow-simplification-14.md)**
   - 被谁阻塞：13。
   - 交付什么：README 按最终工作流说明用法，本仓库采用新配置；维护者清楚何时可以新增门禁以及提交如何记录触发来源。
   - 适用规则与影响区域：第 6、10、11 节；AC-27 本仓库新配置、41；范围边界；README.md、.agent/matt-workflow.md、tests/**；本次仅本地起草 Ticket；实际写 README/配置属于实施范围。施工可按 Spec 直接实施，不强制使用将被替换的工作流 runtime/Skill。

## 验收覆盖（不写入 Ticket 正文）

表内 A<n> 对应 Ticket 的第 n 个复选框。每条源验收有 owner；拆分子项不重定义源验收，实施时仍需对照 Spec 全文。共享不变量作为约束引用不构成新增范围。

| 源验收 | Owner / Ticket 验收 |
|---|---|
| AC-01 | 10#A1 |
| AC-02 | 10#A2–A3 |
| AC-03 | 02#A2（分支）；05#A3（提交与无推送） |
| AC-04 | 02#A1（配置判定）；08#A1（全部代表性入口） |
| AC-05 | 02#A4 |
| AC-06 | 02#A2（显式）；03#A2（补建） |
| AC-07 | 05#A1 |
| AC-08 | 03#A4；05#A2（finish 拒绝） |
| AC-09 | 05#A2 |
| AC-10 | 03#A2 |
| AC-11 | 04#A3 |
| AC-12 | 03#A1、A4–A5 |
| AC-13 | 04#A1 |
| AC-14 | 02#A3（Topic）；03#A6（Ticket） |
| AC-15 | 10#A4–A5 |
| AC-16 | 04#A5 |
| AC-17 | 06#A1 |
| AC-18 | 06#A2 |
| AC-19 | 06#A3–A5 |
| AC-20 | 07#A4（分支）；13#A1（artifact） |
| AC-21 | 04#A4 |
| AC-22 | 13#A2 |
| AC-23 | 07#A5 |
| AC-24 | 07#A6 |
| AC-25 | 02#A2、A5（显式/文档）；03#A2（补建）；05#A5（单 Ticket 完成） |
| AC-26 | 10#A7 |
| AC-27 | 08#A1（旧配置全部入口）；13#A8（新模型全量）；14#A3（本仓配置） |
| AC-28 | 13#A2 |
| AC-29 | 09#A1、A4 |
| AC-30 | 09#A2–A3 |
| AC-31 | 13#A7 |
| AC-32 | 11#A1–A5 |
| AC-33 | 12#A1–A6 |
| AC-34 | 01#A3（基线）；13#A5（函数与上限） |
| AC-35 | 01#A1–A2（真实旧样例）；08#A2–A6（迁移行为） |
| AC-36 | 08#A1 |
| AC-37 | 13#A8 |
| AC-38 | 13#A1 |
| AC-39 | 13#A6 |
| AC-40 | 09#A6 |
| AC-41 | 14#A1–A2 |

## 核心模型与非 AC 约束

- M1 选择与 argv：02、03；artifact 例外与最终命令集合：13。
- M2 全部进入 active 的路径：02 显式、03 自动补建、08 迁移；归档与不可覆盖：02、07、08。
- M3、I-K1/I-K2 与单 Ticket 串行：03、05、06；迁移重新建立定义快照：08。
- M4 材料/结果：04；Ticket 四轮/停止/裁决：06；分支对应规则：07；文档规则：10。
- M5 每条终点及 I-A1/I-A2：02 quick/文档、05 finish/单 Ticket、06 Ticket accept、07 多 Ticket/分支 accept/abandon、08 migrate。
- M6 状态给完整下一命令：02、03、05–07；最终保留/新增/删除全集：13。
- M7 I-1/I-2/I-3/I-4：各 runtime 切片，并由 07 跨路径验证；I-5/I-6：04、06、07、10；I-7：03/05/07；I-8/I-9：08；I-10：02/07/08；I-11：13。
- 第 5 节全部固定摘要标题与知识沉淀：10；runtime 对标题的检查：02、05、07。
- setup 探测/写入与 private 初始化：02；建 release 后清理：09；测量闭包、冻结正文及最终多版本检查：13。
- 范围外宿主安装、其他项目迁移、Stop hook、飞书实测、外部写入均不作为交付。

## Frontier 与验证边界

当前所有 Ticket 未认领，验收均未勾选，状态 ready-for-agent。唯一 frontier：01。依赖图：01→02→03→04→05→06→07→08→09；09→10、11；10→12；10、11、12→13→14。分叉表示没有硬依赖，不授权并行实施。

01 完成后再进入 02；10 与 11 同时就绪时按 sequence 选择 10。本次只检查 Ticket 格式、血缘、引用与图；没有执行源 Spec 的实现验收，也没有生成测试/审查通过记录。
