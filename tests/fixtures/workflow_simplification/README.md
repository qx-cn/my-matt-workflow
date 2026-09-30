# 施工前基线

源提交：`40e51afc02c1c16d4672a1f82a582d85180fb9e5`。
旧 release：`20260929-234249`。Cursor 主链：**58,213 字符**。
`baseline.json` 保存源提交、旧 runtime 与 release 清单哈希、测量闭包中每个文件的哈希和字符数，以及各 Topic 的预期迁移结果。

## 重建

在仍有该旧 release 的源码仓库运行，目标目录必须不存在：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m tools.capture_legacy_fixtures \
  --repo . \
  --legacy-runtime releases/20260929-234249/runtime/tools/workflow.py \
  --release releases/20260929-234249 \
  --output /tmp/workflow-v1-recapture
```

若旧 release 已清理，从源提交恢复旧源码并用旧构建器生成同内容安装件；不要使用新 runtime 生成旧格式。生成过程使用临时项目和本地 Git，不接触真实宿主安装目录。时间、随机 attempt id 和临时绝对路径不保证逐字重复；状态、测试与审查协议及文本量可复现。

`generation.json` 是调用旧 runtime 的实际 argv、stdout 与退出码。Spec/Ticket 是最小输入文档；配置由旧 `setup --apply` 生成。开始、完成和设计阻塞状态通过旧 CLI 产生；C 的 `revising → revalidated` 先通过旧 `ticket-transition` 校验，再使用旧 runtime 的 `project_ticket` 投影 API。complete 由真实 unittest 与冻结输入校准自审凭证生成；这些只是玩具样例的 self 记录，不是本 Topic 的审查凭证。

## 加载样例

先从 `baseline.bundle` 克隆到临时目录，再把 `legacy_project/` 覆盖到该目录。Bundle 保留旧记录引用的真实基线提交，覆盖后的工作树保留 A–E 的最终旧状态：

| Topic | 旧状态 | 迁移预期 |
|---|---|---|
| A | ready-for-agent、complete、implementing | 补建 standard，进行中 Ticket 可续跑 |
| B | blocked-by-design | needs-user；测试后接受或修订重开 |
| C | revalidated | implementing |
| D | complete | 完成历史保留，标注迁移归档 |
| E | implementing、blocked-by-design | 两张进行中，整个 Topic 无法自动迁移 |

所有旧 Ticket 都没有 `test_commands`。每个 Topic 有分片术语表；旧项目配置为 schema 1/audited。`unfinished_session/` 是原 eval fixture 的完整文件副本，不含后加或伪造的 journal。

记录中的绝对路径是生成时的临时路径（见 `fixture_source_root`），不是秘密或待连接的真实项目。新迁移应读取旧记录中的基线并建立新的实施记录，不把旧路径当成当前项目；complete 的历史文件仍应逐字保留。不改动这些原始 fixture 来适配新实现。加载和测试只写临时目录。

测量包含旧 requirement-analysis；读取各 Skill 的 `SKILL.md` 和相对链接可到达的同目录 Markdown，循环只访问一次，按全文内容去重，再求 Python 字符串长度。代码围栏中的示例链接不形成 Markdown 引用边，但围栏全文仍计入字符数；外部链接及跨 Skill 目录链接不纳入闭包。未来的 35,000 上限由后续 Ticket 验证。
