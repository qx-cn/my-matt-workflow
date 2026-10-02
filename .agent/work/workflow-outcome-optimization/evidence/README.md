# 本轮证据与复现

审查基线：源码 `c10906c`，当前宿主 runtime `20261002-093849`。原审查单元 content_id 和 522 文件的路径/hash/大小保存在 `source-manifest.json`。`retained-source.zip` 保留公共 CLI 探针所需的 176 个精确输入文件；每次复现先逐文件核验 sha256，不依赖已经释放的临时快照。

在任意目录运行：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 /Users/sherly/CS/wsp/ai/my-matt-workflow/.agent/work/workflow-outcome-optimization/evidence/runtime-probe.py
```

脚本在自己创建的临时目录使用本仓库 BatchTests 的公共 CLI seam；不会改变 workspace 源码、真实项目或外部系统。运行约 5.5 秒，输出 `/tmp/my-matt-quality-runtime-reproduced.json`。交付时保存的同名 JSON 是本轮实际结果，路径/timestamp 可能随重跑改变。

预期现版结果：

- 当前某全量命令退出 1，但基线不可运行，`new_failures=[]`，批次“已收口”。
- 自审登记 blocking/correctness 与 blocking/spec-challenge 两种发现后，finish 均得到 complete。
- pass/无发现仍因同区间修改或体积越阈值返回停止理由。

最后两项审查停止只用精确 AST 函数探针，没有执行完整停止 CLI 链。review pass 是明确的合成测试回执，不是真独立模型审查。探针证明机械行为，不证明真实 Agent 一定遗漏故障，也不证明候选版效果更优。

其他 JSON 保存原始 baseline/current、finish 状态及已修旧解析问题的有限探针。新版本验收需要对候选源码运行相应回归，不能只重跑这个固定旧版归档就声称修好。

本轮未运行完整测试或模型效果对照。源码审查与 SPEC 的 content match 收据、独立 SPEC 审查结果在本目录及 reviews 中保存；它们与未来源码测试、release、安装状态分别报告。

Revision 2：`r2-source-manifest.json` / `r2-source-finalize.json` 保存七项能力源审核身份与 match；`r2-spec-manifest.json` / `r2-spec-finalize.json` 保存新增合同独立设计审核身份与 match。临时 snapshot 已释放，manifest 保留路径与摘要作溯源；原文持续保留在当前源码及 Topic 历史文档，不能把旧临时路径当仍可读。`r2-verification.json` 是本次文档交付核验，不是实现或效果试验结果。

用户请求的 revision 2 复审：`r2-rereview-manifest.json` 保存 279 件固定输入，`r2-rereview-finalize.json` 为 match/released，`r2-rereview-verification.json` 保存范围、覆盖与 Spec 未变更核验。临时 snapshot 已释放；正式分工报告保存在 reviews/design-04-* 对应文件。
