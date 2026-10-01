Review-Snapshot: 020573b6e2892257b2846dfbbae26b68801cb06b39962944cf93134f6b10b517
Base: 08e58eb2ac9743f06faf295031b4d4ff3e0a402d
Head: 07bafb3092405476ce65e8cc2496a72eae833956
Review-Scope: change-only

## Code

[P1][high] 普通 build 无法保护自定义安装根引用的 release — tools/workflow.py:553-554

基线支持 install --agent-home 自定义根。自动清理只检查固定宿主，普通 build 的 parser 又没有 --agent-home，因而旧版一旦不再是 previous 就被删除。正式 baseline 实际构建及自定义安装的 old-r1 验证有效；当前代码构建 new-r3 后删除 old-r1，verify_installed_state 及后续 install 均失败。probes.log、base-probe.log、race-probe.log 和实际 CLI 参数拒绝日志可复核。应让构建获知受支持的安装根，并对未能证明无引用的 release 保守处理。覆盖 AC-40。

[P1][high] 清理使用构建开始时的过期安装引用 — tools/workflow_lib/release.py:719-723

引用集合在耗时 source_gate 前读取；安装只持有宿主 install 锁，不受构建 releases 锁约束。source_gate 期间安装旧版成功，清理仍按旧集合删除该 release。正式 baseline 构建 r3 时安装 r1 后全部保留；当前代码对同一根构建 r4，gate 内安装 baseline r2 并验证成功，随后删除 r2，receipt 立即失效（base-race.log、current-formal-race.log）。应对安装与读取引用/删除建立共同同步边界。覆盖 AC-40。

## Spec

No findings.

已从冻结 Spec 第7/11节及 Ticket09重新建立需求映射；后续10/11/12/13的正文语义与最终集成要求未当作09缺陷。完整 coverage 与实际测试见 result-09.json。

Code: P0=0 / P1=2 / P2=0；blocker=2。Spec: P0=0 / P1=0 / P2=0；blocker=0。

实际 Python 3.14.4 完整 411 tests 通过；三宿主临时 build/install/verify、源码缺陷注入与安装篡改探针完成。Python3.10未验证。所有证据仅来自冻结 snapshot与专属临时副本。
