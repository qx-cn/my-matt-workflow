# 实施适配

从当前宿主 install-state.json 读取绝对 runtime_entry，不假设目标仓库自带工具。配置和 Topic 尚未迁移时按 runtime 提示处理，不把施工旧协议当成新工作流。

standard 使用 implement start/test/review/finish/status。start 生成执行简报，Agent 补写实施计划；恢复先读 status，按其当前动作继续。测试用 Ticket 声明命令，审查只消费 runtime 固定材料包，按[审查循环](../review-loop.md)派审查者并提交判断字段。结果 JSON 保留骨架预填身份；修复思路传 notes-file。内容变化后按 status 重新验证，达到停止边界按[找用户的条件](../user-intervention.md)处理。

quick 从已确认需求直接实施、测试、自审，写[交付摘要](../workflow-delivery.md)，不建实施记录。Topic收尾和归档由 runtime 完成。多 Ticket 在批准范围依赖顺序逐张完成，末尾运行 topic test/review 后 topic complete。只有实际测试和审查闭合、适用完成动作成功才能交付；否则报告阻塞与最小恢复输入。
