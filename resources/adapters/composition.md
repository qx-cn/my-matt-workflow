# 组合调用

调用关系以 composition/manifest.json 为唯一依据，授权以共享用户决定规则为唯一依据，路由索引不算调用边。method在阶段内执行并返回；chain在已通过主链对齐后继续；handoff的确认依[找用户的条件](../user-intervention.md)。

调用源码用 {{skill-call:my-name}}，安装投影为 Codex 的 $my-name 或 Cursor/Claude 的 /my-name；调用已安装入口，共享资源按清单分发。主链的阶段结果供下一阶段直接使用，不要求用户手动切换。

先识别用户所需产物和阶段止点，复用已确认需求与授权；只要求 Spec/Ticket 时在该阶段交付。chain/handoff 不自授权下一阶段，已经覆盖的批准不重复申请。
