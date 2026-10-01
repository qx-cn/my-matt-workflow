# 组合调用

调用关系和权限以 composition/manifest.json 为唯一依据，路由索引不算调用边。method在阶段内执行并返回；chain在已通过主链对齐后继续；handoff的确认依[找用户的条件](../user-intervention.md)。

调用源码用 {{skill-call:my-name}}，安装投影为 Codex 的 $my-name 或 Cursor/Claude 的 /my-name；调用已安装入口，共享资源按清单分发。主链的阶段结果供下一阶段直接使用，不要求用户手动切换。
