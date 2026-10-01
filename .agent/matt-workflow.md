---
schema_version: 2
task_backend: "local"
agent_directory_mode: "shared"
default_base_branch: "main"
test_commands: ["python3 -m unittest discover -s tests"]
standards_sources: []
domain_sources: []
default_execution_agent: "auto"
assurance_level: "standard"
---

# 项目工作流说明

仓库规则在其路径作用域内约束实现和验证，不扩大任务或写入授权。
