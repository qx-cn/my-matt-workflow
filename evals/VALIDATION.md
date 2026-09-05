# 验证层级

本目录区分三种不能互相替代的证据：

1. `static` / `unit`：验证源树结构、确定性 runtime 和测试代码。
2. `deterministic-contract`：`evals/scenarios/` 与历史命名的 `workflow.py smoke` 验证结构化契约及源 SHA；它不能证明模型实际遵循 Skill，也不能冒充真实业务 smoke。
3. `fresh-agent-smoke`：让未参与实现的 Agent 在隔离项目中读取已构建 release，只凭给定输入完成工作，并保存原始输出、模型/宿主、release、结果与失败原因。只有这一层能作为 Agent 行为证据；真实业务项目仍需另行 smoke。

`python3 tools/workflow.py check` 的 `valid` 只覆盖前两层。没有 fresh-agent 或真实项目运行记录时，报告必须写“未运行”，不得推断通过。

## Astra 行为证据

`evals/agent-smokes/astra-behavior-suite.json` 定义 Astra 的代表性行为场景，`evals/agent-smokes/astra-evidence.schema.json` 定义记录形状。实际运行结果属于任务产物，不进入源码 release；用下列命令校验：

```sh
python3 tools/workflow.py validate-agent-evidence <evidence.json> --require-complete
```

`--require-complete` 只要求每个场景都有记录，不等于全部通过。结果中的 `statuses` 才是通过、失败、阻塞与证据不足的实际分布。标为 `pass` 的场景必须使用 `gpt-6-astra`，提供原始输出，并让每项 rubric 观测都为 `true`；额度、宿主沙箱或会话中断导致无法观察完整链路时，使用 `blocked` 或 `inconclusive`，不得补写成通过。
