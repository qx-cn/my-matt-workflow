# Ticket 09 交付记录

状态：completed；七项验收由施工 runtime 投影完成，实施会话已关闭；批准范围仅 Ticket09。Spec revision1 与施工 profile 保持不变。

实现：39个 Skill 合并为32个；精确22条 method/handoff/chain 调用边和11个模型调用入口，ask-matt 路由其余31个。调用元数据由组合清单派生，三宿主按各自语法投影。删除正文复制机制和 portfolio；被合并方法的必要规则保存在共享资源，research 原文只修正迁移后的相对链接。保留8个冻结 Skill 的施工前正文及逐项差异证据。

用户确认的拆分调整：build/preflight/check 不再读取旧 eval 路径；新集合、元数据、链接、调用、共享资源和实际安装产物由 tests 验证。Ticket13 保留旧目录与剩余命令/模块删除及最终集成；Ticket10/11 保留主链与方法语义，不在本次提前实施。

release 自动清理只保留当前、上一版及安装状态引用版本。正式审查发现的自定义宿主引用遗漏与旧正文读取措辞，分别经过两轮受管修复方案、自审、修复和复审闭环；自定义目录场景以真实临时 build/deploy/install 从失败验证到通过。未解决 finding 为零，审查来源为 self，不称为独立审查。

验证：声明的全量命令 `python3 -m unittest discover -s tests` 实际退出码0；36项结构、共享资源、组合与安装专项测试通过。Codex、Cursor、Claude 安装只在临时目录执行，均校验实际安装状态。新集合/元数据/链接缺陷注入拒绝构建；四次 build 校验安装引用保留；冻结8个逐项核对通过。

- test receipt：6c6f72be11fc463d2ee7de0ed540a9753e1e7d3c3f063f84da91226dda307acf
- review receipt：647c9759857597b622f8f129d4ad3559ccfb88fb5d44e341e69befd4564a0aed
- code content：f632e6f720c4e04e2c290db727a9db170b5694bcfa537e1830b4903a823a8c4d

边界：本次只验证结构、打包、调用权限和构建安装行为，不声称模型方法效果提升。未安装到真实宿主，未推送、未写外部系统。旧施工 runtime 为已删除的 portfolio/** 范围匹配要求，暂时保留一个无文件目录；不属于源码或发布件。闭环结束后删除该临时空目录。后续10/11的阻塞依赖解除，本次不领取。
