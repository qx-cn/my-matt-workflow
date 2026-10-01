# 独立 round 1 持久证据

原 runtime 快照已按 status:match 正式释放。retained-artifacts.tar.gz 保留逐源 SHA256 核验后的166文件，与已审核快照字节相同。retained-snapshot.json 与原 snapshot.json/content_id 保留；wrapper 只将 artifact 路径映射到临时解包目录，不改原始复现脚本或报告。

重跑：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 .agent/work/workflow-simplification/reviews/independent-evidence/batch-05-07/reproduce-original.py /tmp/batch05-07-original-repro.json
```

预期 driver exit0 表示原缺陷断言成立，内部 accept exit1。仅在临时目录运行当时冻结代码，不测试当前修复或把旧失败描述成现状。
