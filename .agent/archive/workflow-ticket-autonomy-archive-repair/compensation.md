# 已收口冻结材料的补偿修复

compensates: workflow-ticket-autonomy-01 / Topic workflow-ticket-autonomy
baseline: 56adc4e

原Ticket/Topic、审查manifest与输入字节保持不变。归档后的真实doctor失败：review-loop-rules.md原始相对链接被当作项目文档链接，user-intervention.md不在该命名blob旁。

修复仅让validator识别归档中已经登记、身份绑定且完整字节校验通过的runtime审查输入blob。普通归档文档、配置、近似目录仍严格校验链接；未登记/身份错误/损坏冻结材料不能获得豁免。最新manifest优先使用记录中的原始sha256；历史记录必须匹配原unit/content/round并逐文件校验。

驗收：真实归档doctor valid、现有普通archive坏链接拒绝不变、未登记/篡改/越界输入拒绝。独立冻结差异复审、全量与发布门禁，完成后报告真实状态。此小补偿采用quick Topic工作记录，但完整源码门禁与独立冻结审查保持，未更改项目assurance配置或原完成历史。
