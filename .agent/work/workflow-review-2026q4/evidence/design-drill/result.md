# 独立设计审查演练结果

新上下文 design_drill 读取原始玩具 Spec/service.py 与新 my-review-design 方法，未修改玩具。一次全面审查，未复审。未提供施工者预期结论；继承主Agent模型/思考档位。

## 承重断言核验表

- 缺失key返回None：与现状不符，service.py:3–5 直接 store[key]，空dict实测KeyError，关联D1。
- 所有消费者用KeyError：无法完整核实，只有service.py:4注释，没有消费者实现。
- 写路径共用invoice:v1：已核实，service.py:2,6–8，锁服务实现未知。
- 改invoice:write仍支持逐实例发布/随时回滚：与现状不符，关联D2，两代锁键不共同互斥。
- 持久性保障：无法核实，store实现缺失。
- 每日最多三张发票：无法核实，Spec无已决业务资料，关联S2。

## 审查发现

D1 blocking/correctness：spec.md:4,7；service.py:3–5。消费者删除except后，read_invoice({},'missing')抛KeyError，无法走None判断。实际执行确认。应更正事实、选择保留异常契约或有兼容安排的接口修改。

D2 blocking/impact：spec.md:7,13；service.py:2,6–8。旧实例持invoice:v1，新实例可同时持invoice:write并进入写区，混合发布/回滚失去共同排他。没有声称复现持久化丢失更新（store和锁服务未知）。更小方案是保留旧键。

D3 blocking/spec-challenge：spec.md:7；service.py:5,8。read_invoice({'present':None},'present')返回None（实测）；如None允许作为值，将被新契约判缺失。材料没有消费者，后续覆盖的影响尚未知，应交用户决定是否需要区分，不自行裁决。

## 已考察但排除的风险

- 现有写入完全未加锁：service.py:7–8在锁内，排除。
- 必须表迁移：没有表结构变更，不能虚构；store持久语义未知。
- 三张限额已有实现被破坏：代码无计数限额，排除该断言，但语义需确认。
- 必须改写接口才能判断缺失：已有KeyError契约足够，未证必要性。

## 待用户确认的需求语义假设

S1 None是否有效值，存量及写入来源是否满足限制；S2每日三张是否采纳，以及时区/计数事件/失败撤销占额。

## 命中与局限

预期三项均命中：错误接口事实有核验不符+发现；锁改名混合版本有impact发现；不可代码验证业务规则列待确认。额外D3是一次演练产生的语义风险，未扩大/修改玩具以追求命中。演练不证明真实项目模型审查质量稳定提升。
