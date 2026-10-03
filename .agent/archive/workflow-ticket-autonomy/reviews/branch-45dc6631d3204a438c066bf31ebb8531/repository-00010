# 工作产物存储

项目内工作产物写入 `.agent/work/<topic>/<type>/`，文件名 `<type>-<topic>-<time-or-sequence>.<extension>`；topic/type为路径安全单段。写入前解析目标绝对路径，默认新增而不覆盖历史；用户指定其他安全位置时尊重该选择。授权遵循[用户决定与授权](../user-intervention.md)。

`.agent/matt-workflow.md` 的 agent_directory_mode 决定归属：private 是无 remote 的个人嵌套 Git，shared 由主仓库跟踪；两者都不修改主仓库忽略规则。`.agent/CONTEXT.md` 保存项目术语，`.agent/adr/` 保存难以撤回的决定；handoffs/prototypes/researches/learning/architecture-reports 分别保存相应工件。非项目交接用临时目录，非项目学习按安装配置的学习目录，未配置用当前目录。

产物保留影响下一步的来源、阶段、未知和证据边界；不复制无关材料或敏感信息。本地保存、提交、发送、发布是不同动作，文件生成不自授权其他动作。
