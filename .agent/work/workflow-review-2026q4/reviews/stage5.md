# 第五段：度量、逃逸缺陷、README与文本量

基线e381f05；范围AC39–43。新增按视角/来源/严重度的发现统计、每批次实际独立派发数、高风险审查及blocking次数、整分支执行与发现统计；未知旧记录不推断为零，旧逐Ticket独立审查另列ticket-legacy。审查历史保留但不重置当前审查预算。

逃逸缺陷入口支持活动与归档Topic，批次/Ticket归属校验，设计审查记录自动带出，未知如实标记；登记不改归档工件。metrics含无完成记录但有逃逸缺陷的Topic及环节分组。README更新批次默认、高风险例外、整分支可选与测试基线；status --human输出中文，JSON兼容保留。

完整段初审派发两次及经现有Agent转派均被agent thread limit拒绝，按Spec例外采用结构化自审。自审发现2 blocking：覆盖旧self_review丢失未知历史、旧逐Ticket审查误计为批次；2 advisory：null发现文件未拒绝、仅准备整分支被标为已执行。全部修复。影响面核对历史预算、归档不可改写、现有命令、中文输出及未施工旧记录兼容；测试对未知与真实零分别断言。

之后派发新上下文stage5_rereview成功，限定修复差异与影响面；未复用旧审查上下文。其独立复审0 blocking/0 advisory，独立43项测试通过（质量度量6、文本量2、批次12、重开12、整分支11）。完整段初审的独立性缺口仍保留，不将本次限定复审记为完整段独立初审。

主Agent最终全套 python3 -m unittest discover -s tests：274 tests / 240.142s / OK；聚焦18项/16.344s/OK。证据stage5-tests.txt、stage5-focused-tests.txt。主链33,919字符，低于35,000，stage5-text.json。无未解决阻断。
