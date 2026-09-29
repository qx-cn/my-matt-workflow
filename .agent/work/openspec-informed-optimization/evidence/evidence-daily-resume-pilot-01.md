# 日常接续试点：Trader `trader-v1`

状态：第 3 项的只读同状态对照。2026-09-29 在同一 Trader 工作树上运行，不修改 Trader 文件；改动前使用 `openspec-spec-revision-index-v1` release 的 runtime，改动后使用本仓库工作树 runtime。

## 任务与观察

目标是找出当前实施单元及下一动作，同时看见不能忽略的异常。两个版本均执行 `work-overview --repo /Users/sherly/CS/wsp/trader --topic trader-v1`，并用 `--json` 核对来源。该主题当时有 38 张 Ticket、38 条可解析会话和 14 条问题；Ticket 20 的活动 journal 与当前 claim 匹配，来源校验为 `match`。其余活动旧 journal 与当前 claim 不符或来源已失效；历史 Spec 和若干旧 journal 也存在格式问题。

| 观察点 | 改动前 | 改动后 |
| --- | --- | --- |
| 文本输出 | 97 行，含 38 张 Ticket、38 条会话 | 36 行，列出 8 张未完成 Ticket、5 条活动会话；30 张已完成 Ticket 与 33 条历史会话显示数量，详情仍在 JSON |
| 下一步所在行 | 第 83 行，只提示检查状态问题 | 第 22 行，指向 Ticket 20 的活动 journal 和 `continue-implementation` |
| 状态异常 | 14 条可见 | 同样 14 条可见；顶层仍为 `needs-attention` |
| 找出当前会话所需人工筛选 | 从会话列表及 Ticket claim 中交叉查找 | 从下一步直接定位，再按需查看异常 |

旧 `next-ticket --repo ... --feature trader-v1` 返回 `approved-scope-missing`，不能替代实施会话接续。这是该项目 profile 的授权范围要求，未因总览而放宽。

## 解释与边界

改动后仅在**唯一**活动 journal 同时匹配 implementing Ticket claim、来源校验为 `match`，且该 claim 没有重复 journal 时，优先显示运行时给出的下一动作。其他问题继续列出，`needs-attention` 保留；这个提示不准许跳过 Ticket、写入或收据门禁。若当前 claim 重复、来源失效或找不到唯一匹配，仍要求检查冲突。文本视图压缩已完成和历史记录，机器视图保留全量路径和状态。

这是同一状态下的接续可发现性与人工筛选量对照，并非真人计时实验。命令耗时约 0.1 秒且差异不具解释力；尚无遗漏验收、误读率、长期重复维护量或交付效果的数据。第 4 项需继续记录这些限制，不能将本结果写成实际交付效率已提高。
