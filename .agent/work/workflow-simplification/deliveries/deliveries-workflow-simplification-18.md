# workflow-simplification-18 补偿交付

已修复上个Topic完成性审查发现的H-F1/H-F2两个P1。以77246b4为施工基线；沿原Spec的直接施工例外，新建补偿18，不改写原17张已完成Ticket或原Spec/run/review/交付历史，不迁移或归档原Topic。

## 改动概述

- Gitlink审查：三类材料（高风险Ticket、批次、可选整分支）保留mode160000及正式提交指针。内容身份绑定子模块HEAD；未提交子树修改拒绝测试/审查；普通文件和私有.agent例外保持。
- 旧会话恢复：Topic状态新增逐Ticket状态与停止原因，复用单票恢复门禁；前票接受后选择可开始的后继，新批次与整分支优先级保持。中文renderer兼容Topic对象列表与批次字符串列表。

## 验收对照

| 验收 | 满足及证据 |
|---|---|
| A1 三审查路径可处理未改Gitlink并收口 | tests/test_completion_compensation.py中unchanged_gitlink及gitlink_high_risk两条真实CLI测试；首审额外验证.git文件常规子模块 |
| A2 Gitlink身份变化/脏子树拦截、其他路径不回归 | gitlink_new_commit测试；首审独立Gitlink/private.agent探针；最终全量含普通文件、符号链接、可执行位测试 |
| A3 旧会话停止/后继恢复及新批次中文兼容 | restored_v2_stop、accepted_legacy_ticket、archived_stopped_history、document_and_batch、missing_legacy_record、batch_human测试；复审实际解析并执行next_command |
| A4 测试、独立审查、历史保留 | 最终286 tests通过、validate 32、diff check；首审2阻断均修复，新上下文复审0发现；施工前487历史文件SHA逐个比对changed=[] |

## 测试结果

- python3 -m unittest discover -s tests -v：286 tests，274.242s，OK，exit0。
- python3 -m unittest discover -s tests -p test_completion_compensation.py：9 tests，16.452s，OK，exit0。
- python3 tools/workflow.py validate：VALID skills=32，exit0。
- git diff --check：exit0。
- 主链Cursor投影闭包：33,919字符，75可达文件/31独立内容，低于35,000。
- 首轮作者及独立全量均为284 tests/1 failure（batch中文回归），如实保留；修复后全量286 tests通过。新增两条回归先失败后通过，Gitlink初始用例也先失败后通过。

## 审查发现与修复

- 原完成性独立审查：H-F1（状态恢复）、H-F2（Gitlink审查）均修复；历史H-F3重复审查规则已由Q4解决，本次不重复实施。
- 新上下文compensation18_review：2 blocking、0 advisory。R18-F1是旧会话前票接受后未选择后继的残留；R18-F2是新增renderer误读批次字符串数组的回归，均已修复。独立首审全量284 tests/285.579s/exit1；额外Gitlink/private.agent探针通过。
- 另一新上下文compensation18_rereview：只看上述修复差异及影响面；0 blocking、0 advisory；独立执行52项相关测试及额外公开CLI探针通过，源码SHA最终复核匹配。没有用自审代替。

独立原始报告在reviews/review-workflow-simplification-18-01.md、18-02.md。证据目录evidence/compensation18保留实际探针、日志、修复差异、源码SHA、最终全量日志与verification.json。报告中的/tmp原路径由该目录保留相应副本；首轮和复审事实各自独立，不把测试fixture的independent pass当成模型独立审查。

## 历史与范围

施工前487个历史文件逐字摘要不变；首审另将483个HEAD已有历史文件与git show 77246b4逐字核对。只新增补偿Ticket18及本次工件。Gitlink提交绑定是修复审查准入直接需要的完整性保护，不改变等级、对齐点、安装/release/部署机制。收口时仅更新本票状态/复选框/证据链接，未变更审查所依据的验收定义。

## 未验证项

Python3.10及远端CI未运行；不声称已在真实项目提高审查效果。材料绑定Gitlink提交指针，不自动联网获取子仓，不声称递归审过子仓源码。新源码尚未安装或部署到宿主；本次不推送。全部部署/安装相关自动测试只使用临时目录。此次直接施工不产生runtime Topic完成回执，旧Topic保持原历史位置。
