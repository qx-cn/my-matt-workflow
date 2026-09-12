---
schema_version: 1
task_backend: local
agent_directory_mode: private
default_base_branch: main
branch_policy: confirm
commit_policy: allow
external_write_policy: deny
docs_writeback: confirm
humanizer_policy: deny
composition_policy: manual
work_scope_policy: ready-frontier
decision_policy: ask
default_execution_agent: auto
max_repair_rounds: 1
test_commands: ["python3 -m unittest -v"]
review_commands: ["python3 review.py"]
standards_sources: []
domain_sources: []
---
