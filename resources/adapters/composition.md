# 组合调用

调用关系与调用权限以 `composition/manifest.json` 为唯一依据；路由索引不算调用边。

- `method`：在当前阶段内调用对应 Skill，执行后返回调用方。
- `handoff`：主链之外的阶段交接，调用前向用户确认一次。
- `chain`：主链交接，在已确认的对齐点之后自动进行。

调用方用宿主语法调用已安装的 Skill。源码中的 `{{skill-call:my-name}}` 由安装投影转换为 Codex 的 `$my-name` 或 Cursor/Claude 的 `/my-name`。被调用方是独立安装入口，不向调用方复制方法正文；共享资源按资源清单打包。
