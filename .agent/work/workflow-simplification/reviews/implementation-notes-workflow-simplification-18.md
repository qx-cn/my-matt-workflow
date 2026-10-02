# 补偿18施工计划

范围：H-F1/H-F2及直接内容绑定；基线77246b4。直接施工例外，不使用自身Topic/Ticket状态机，不把本记录称runtime receipt。

## 现状核实

- ticket_review.baseline_files/current_files对非blob与目录拒绝，baseline每个内容路径都访问；Gitlink为160000 commit。三个审查入口共享此seam。
- topic_service.content_id对目录只记录missing，原来不绑定子模块HEAD；只允许通过审查而不修正此处会遗漏内容漂移。
- topic_service.status没有Ticket列表，旧active下一步默认complete，branch/batch分别覆盖；ticket_implementation.status已有单票测试/定义/审查恢复判定可复用。

## 影响面

- 冻结文件条目、完整仓库材料、Ticket/批次/整分支三个消费者；新增Gitlink提交指针沿用mode字段，不伪装blob，不联网获取子模块。
- 内容身份消费者：定向/全量测试、增强自审、审查提交/通过、批次close、Topiccomplete。普通文件身份算法保持；旧Gitlink记录可能需重新测试审查，不能继续信任原missing身份。
- Topic状态JSON新增tickets字段；恢复命令复用既有单票status，分支/批次优先级保持。中文renderer列明Ticket与裁决原因。归档仅展示历史，不新增裁决或写入。
- 无存量数据迁移、权限/锁/配置变化、外部网络或宿主更新；Git读取受现有仓库安全边界约束。

## 测试计划

1. 实际Gitlink＋普通修改，三审查路径与闭环各自验证，检查冻结mode/提交身份。
2. 推进子仓HEAD/修改未提交文件，验证原审查失效/拒绝，分别负向测试。
3. 真实支持的v2既有记录（固定旧格式），公开topic status/--human核验对象、原因、下一步；另测新批次/归档隔离。
4. 全量unittest、validate、文本量、历史摘要比较；新上下文审查只读并独立测试。

## 验收对照

- A1 → test_unchanged_gitlink_batch_and_optional_branch_can_close、test_gitlink_high_risk_requires_own_batch_review → ticket_review.baseline_files/current_files。
- A2 → test_gitlink_new_commit_invalidates_tests_and_review_and_dirty_child_rejected；独立真实.git文件/私有.agent探针 → topic_service.gitlinks/content_id、review_snapshot.gitlink_entry。
- A3 → test_restored_v2_stop_has_ticket_reason_and_executable_next_step、test_accepted_legacy_ticket_resumes_ready_successor、归档/文档/缺失记录/批次中文四条测试 → topic_service.status、status_text.render。
- A4 → 全量286项、validate 32、git diff --check、两位新上下文审查及复审、487历史文件SHA逐字核对 → evidence/compensation18/verification.json及两份独立报告。

## 对抗检查

实际公开CLI推进子模块HEAD，旧测试变失效，旧批次审查不能收口；子模块未跟踪文件使test/review拒绝。恢复真正旧v2生成记录，接受第一票后实际执行下一步开始后继。首轮发现后继与batch中文两项阻断，新增测试先失败后通过。最终命令python3 -m unittest discover -s tests -v：286 tests/274.242s/exit0。

## 简洁与约定

复用既有Gitlink clean-tree guard和Ticket status/next_start_command；不复制测试/裁决门禁，不恢复旧默认整分支要求。整理只限本次触及代码，不修改无关文件或环境。首轮两条阻断全部修复；差异复审未发现新问题。

## 已知缺口

只在Python3.14.4运行，未运行3.10和远端CI。冻结Gitlink提交指针，不自动联网获取子模块，不声称审过子仓内部代码。未在真实用户项目验证审查效果。此次没有部署、安装、推送；测试中的安装均发生在临时仓库。直接施工例外下本记录不是runtime收口回执。
