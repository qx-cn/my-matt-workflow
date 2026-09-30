# Ticket 02 交付

## 改动概述

完成 `workflow-simplification-02`：新 setup 写九键 schema 2 配置，默认预览零写入；新 Topic 命令支持显式启动、状态定位、quick 和文档完成。quick 执行全量测试、校验交付摘要、提交与归档，写 kind quick 度量且没有实施记录。private 的主提交排除 `.agent`，shared 可合并代码与元数据。

新模型集中在 `tools/workflow_lib/topic_service.py`，独立于旧 session API。新增 `tests/test_topic_lifecycle.py`；旧公共 setup/overview 测试改为新行为，其他旧模块回归保留到各自删除 Ticket。当前仓库配置仍是 schema 1，施工使用安装 runtime `20260929-234249`。

## 测试结果

- 16 个生命周期 CLI 测试通过，临时 Git 仓库覆盖 shared/private、三种分支情形、Topic 分类与只读归档、旧配置与非法值、缺少摘要节、围栏模板、空测试、失败/修改内容测试、Git 提交失败恢复、私有元数据失败后的单次代码提交、文档完成保留暂存内容。
- 相关旧 setup 测试 5 个、RefreshProject 测试 6 个、work-overview 测试 17 个通过。
- Ticket 声明的 `python3 -m unittest discover -s tests` 最终通过，真实退出码 0。runtime test evidence：`1b8e6d1841e9f8e18e1922210b374206351c122ebdb1a3c4c9ac9c1fb81e94b4`。
- 测试和最终审查绑定同一 code content id：`dc0c6dc2bd60600c885d8f6d27f60d71f880525b02564d35e23e2b25a828bdf9`。
- `git diff --cached --check` 唯一告警来自旧 runtime 清空 Ticket `claimed_by` 时产生的行尾空格；保留 runtime 终态原文，未改写历史记录。实现与测试文件无 whitespace 告警。

## 审查发现与修复

来源为 `self`，不是独立审查。按 my-code-review 在 runtime 冻结快照上做 Code、Spec 两遍审查，覆盖 A1–A6、recovery 和 downstream-owner 探针。

首轮发现 P1：摘要全文正则把围栏代码块里的模板标题计为真实章节，只有模板的摘要也能完成。runtime 登记 finding 后，冻结修复方案并通过 my-review-design 自审；修复只收集围栏外的真实 ATX 标题，并把未配置测试标记写进真实测试结果节。补充 red-green CLI 回归后，重新全量测试、重新冻结复审。

最终 Code、Spec 无当前 Ticket finding，无 blocker；审查 pass evidence：`878d59a26f06882bf2efcafb2a04b7d0b2671105bd549b0d1a05ff04350f47a0`。修复方案 review evidence：`56297d6a80537383ac42ef75c8d788ce43b3e2985c6c104c9f3bd928842cf4c0`。

## 建议

Ticket 03 接入 implement 的 Ticket 定位时，pending Topic 的下一步命令应带所选 ready Ticket 的 `--ticket`，不要套用实施中 Ticket 的省略规则。已作为引用 `workflow-simplification-03#A6` 的 follow-on 登记；接口与后续 owner 见 `handoffs/handoffs-workflow-simplification-02-runtime-foundation.md`。

## 已知问题

当前 Ticket 无未解决 blocker。standard Ticket 收尾、旧 Topic 迁移、命令裁剪、最终指标汇总及仓库配置转换由后续 Ticket 拥有，当前未宣称整个新 workflow 已交付。

## 长期知识沉淀

无。本轮运行状态文件及模块接口属于可逆实现细节，保存于接口交接，不新增长期 ADR。

## 用户介入记录

本轮新增介入 0 次。沿用本会话已确认的 Topic 内自动授权，范围保持 single-ticket；本地提交已授权。未推送、发布、安装或写外部系统。

## 未验证项

未验证进程强制终止/机器掉电恢复、真实宿主安装及其他项目迁移；未执行本轮范围之外的 standard 实施链。仓库已有 `.agent/.matt-workflow.md.swp` 保留原状，不纳入提交。
