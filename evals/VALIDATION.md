# 验证层级

本目录区分三种不能互相替代的证据：

1. `static` / `unit`：验证源树结构、确定性 runtime 和测试代码。
2. `deterministic-contract`：`evals/scenarios/` 与历史命名的 `workflow.py smoke` 验证结构化契约及源 SHA；它不能证明模型实际遵循 Skill，也不能冒充真实业务 smoke。
3. `fresh-agent-smoke`：让未参与实现的 Agent 在隔离项目中读取已构建 release，只凭给定输入完成工作，并保存原始输出、模型/宿主、release、结果与失败原因。只有这一层能作为 Agent 行为证据；真实业务项目仍需另行 smoke。

`python3 tools/workflow.py check` 的 `valid` 只覆盖前两层。没有 fresh-agent 或真实项目运行记录时，报告必须写“未运行”，不得推断通过。

## Agent 行为证据

`evals/agent-smokes/astra-behavior-suite.json` 定义代表性行为场景，`evals/agent-smokes/astra-evidence.schema.json` 定义记录形状；这些历史文件名和 suite id 为兼容已有证据而保留，不表示验证必须使用 Astra。实际运行结果属于任务产物，不进入源码 release；用下列命令校验：

```sh
python3 tools/workflow.py validate-agent-evidence <evidence.json> --require-complete
```

`--require-complete` 只要求每个场景都有记录，不等于全部通过。结果中的 `statuses` 才是通过、失败、阻塞与证据不足的实际分布。标为 `pass` 的场景必须记录实际模型、提供原始输出，并让每项 rubric 观测都为 `true`；额度、宿主沙箱或会话中断导致无法观察完整链路时，使用 `blocked` 或 `inconclusive`，不得补写成通过。

默认使用当前 Agent/模型完成验证。不得仅为提高证据等级而切换到更强、更贵的模型、提高 reasoning effort 或改变服务档位；任何这类模型升级都必须先说明成本影响并取得用户明确确认。模型能力越强，越可能认真执行 Skill、MDC 与项目规则中的每一行，因此兼容强模型的正确方式是逐行审视必要性、消除重复与冲突、保留可观察约束，而不是强制用某个强模型测试。
