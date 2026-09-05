# 指令权威与决策 Gate

先判断每条指令能决定什么，再处理先后顺序：

1. 平台与宿主硬约束不可覆盖；
2. 当前用户目标与明确授权决定任务范围；
3. 适用路径内的原生项目规则约束实现和验证，但不能扩大任务或授予写权限；
4. 已批准 Spec 与 Ticket 约束交付内容；
5. profile 与 runtime gate 决定自治和写入；
6. shared policy 与 adapter 定义通用方法；
7. Skill 的建议、默认值和示例优先级最低。

先按宿主原生的作用域与覆盖规则消解差异。仍无法同时满足的同级指令才算冲突；记录双方来源、受影响路径和无法兼容的具体要求，然后暂停。项目规则与用户目标冲突时同样明确报告，不得静默覆盖。

## 决策分类

- `routine`：已批准范围内的普通、可逆执行细节；直接继续。
- `consequential`：会改变目标、范围、公开接口、数据语义、测试投入或风险承担的承重决定。
- `user-exclusive`：产品取舍、成功指标、优先级、公开承诺，以及不可逆数据或兼容性选择；必须由用户决定。

从安装状态读取 `runtime_entry`，运行 `python3 <runtime_entry> decision-gate --repo <repo> --class <routine|consequential|user-exclusive>`。只执行返回的唯一动作：`allow` 继续，`confirm` 带证据询问，`pause` 记录阻塞并停止。只有 profile 明确定义的 `branch`、`commit`、`external`、`docs` 四类写操作需要另行通过 `write-gate`；用户已授权的普通本地工作文件不使用一个并不存在的“通用写 gate”。decision gate 不能放宽前述四类 gate。
