# Ticket 08 验证记录

范围：tools/**、tests/**；原始 v1 样例只读，迁移仅在临时 clone 中执行。本次 scope 只含 08。

## TDD

同会话从公开 CLI 逐片实施：migrate 预览先因无此命令 red，再得到零写入摘要 green；apply 先因未实现 red，再验证备份、状态、历史与提交；Topic 门禁先返回 pending red，再标需要迁移；B 接受先 IndexError red，再在测试门通过后可完成。原始 fixture 未重写。

最终回归由受管 code-review 固定两项 finding，repair-plan 经 my-review-design self pass 后实施。配置缺少 test_commands 与非法数值的两个子场景保存实际 red（KeyError/TypeError）和 green；CLI preview 返回 unresolved，apply 拒绝且逐文件哈希不变。overview v2 fixture 补显式测试声明，保留缺字段旧格式拒绝门禁。

## 已运行的针对性证据

- 修复后 migration：13 tests，exit 0，见 migration-08-repair-green.log。
- overview：17 tests，exit 0（同会话命令输出）。
- implementation 相关：40 tests，exit 0；最初迁移与 Topic lifecycle 分别 12/18 tests，exit 0。这些是针对性观察，不替代最终 runtime 声明全量证据。
- 首次声明全量 runtime test receipt 135d5d1972a5aded9291da439e6566290019bfffcaac9a935fd2f880c50ed131 为 fail/exit 1；诊断将失败定位到旧 overview 测试样例及其嵌套 source-copy check。历史失败保留，不改写为通过。

## 边界

本文件如实记录同会话 red/green，runtime 不对 red 历史签发 receipt。完成只使用随后绑定最终内容的全量 test receipt 和 code-review pass。未在用户其他项目迁移、未部署真实宿主、未推送。
