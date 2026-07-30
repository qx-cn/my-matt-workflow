---
name: my-teach
description: 围绕长期学习目标设计可跨会话持续的短课程
disable-model-invocation: true
---

# My Teach

先确认学习主题属于当前项目还是独立学习：

- 项目学习：`.agent/work/<topic>/learning/`，其中的课程与记录文件名携带 `learning-<topic>-<time-or-sequence>` 前缀；
- 独立学习：安装配置指定的个人学习目录；未配置时使用当前工作目录。

工作区包含：

- `MISSION.md`：学习动机和目标；
- `RESOURCES.md`：高可信一手资源；
- `learning-records/`：长期学习记录；
- `lessons/`：每次一个小而完整的离线 HTML 课程；
- `reference/`：便于复习的压缩参考；
- `assets/`：离线共享样式和交互组件；
- `NOTES.md`：教学偏好。

每课只提供一个可验证的小成果，结合检索练习、间隔和真实反馈循环。HTML 不依赖 CDN。改变 Mission 前必须确认并记录原因。

> 项目策略优先：读取 `.agent/matt-workflow.md` 的已解析生效策略；缺键或空值按 `strict-control`。本 Skill 中要求询问、确认、停止或限制后续工作的表述，除绝对安全底线外，均服从该生效策略。绝对安全底线始终不变：不得 Force Push、改写 Git 历史、执行破坏性 Git 操作，或向外部服务发送敏感信息。
