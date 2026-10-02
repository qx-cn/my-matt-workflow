# 安装 / 升级校验精简分析

证据基于 固定审查单元（持久来源索引见 `../evidence/extension-source-manifest.json`） 的 `source_path → snapshot_path` 固定映射；content_id 为 `e37074a3d70f4215d62fdb0f8a0cae14138c5477f7f6b2afa1618de6e845ecea`。下文行号均为映射对应的原始路径行号。只读分析，没有运行 build / install / deploy / 全量测试；次数是主路径静态调用计数，不是耗时实测，测试内部的构建和安装、错误恢复与自动清理不计入。

## 结论

能精简，而且有明确的重复工作。优先合并同一操作中的全量测试、发布包验证和跨宿主投影；保留快照、写锁、目录所有权、安装前后内容验证和回滚。这些改动可减少重复执行和维护分叉；实际更新提速需要测量，不能由此宣称模型能力提高。

原 Spec `specs-workflow-outcome-optimization-01.md:55` 明确说“本次不改变 release/install 的公开交付机制”。所以这是新分析所得的扩展范围，应补充 Spec 的交付效率部分；原 Spec 未覆盖这些优化。

## 当前命令职责与真实重复

- `validate`：调用静态源树验证。`tools/workflow.py:116-121`。
- `check`：只运行 `python -m unittest discover -s tests`，静态和行为测试通过测试套件间接覆盖。`tools/workflow_lib/check.py:9-14`；README:134。不能将“check”笼统理解成源码 / release / 宿主都已验证。
- `build`：取得稳定快照，静态 preflight、运行 check、构建 release、切换 current、引用感知清理。`tools/workflow.py:190-205`、`tools/workflow_lib/release.py:748-807`。
- `install`：安装现有 release，不运行全量 unittest；外层与内层均 verify release，再验证已有安装、构建 staging、替换与核对最终内容。`tools/workflow_lib/installer.py:901-923,698-732,789-898`。
- `deploy`：先 check；验证当前 release、临时构建整份候选产物判断能否复用；不能复用时再 build（其内部再次 check），最后 install。`tools/workflow.py:365-392`。
- `doctor`：静态源树验证、验证 current release、临时构建候选产物比较、逐宿主验证。`tools/workflow_lib/doctor.py:26-47,107-134`。

README:124-131 是命令示例清单，不是要求每次依次跑全部命令。不能把用户手工串联所有命令造成的成本全部归咎于程序。

限定正常成功、稳定源码、无重试、无残留事务、无待清理 release、完整 target manifests 的主路径计数：

| 操作 | 全量 unittest 次数 | verify_release 次数 | 三宿主整树投影复制次数 |
|---|---:|---:|---:|
| install，宿主未安装 | 0 | 2 | 6 |
| install，已有同 release 的 v2 安装 | 0 | 3 | 9 |
| deploy，当前 release 与源码相同，已有同 release 的 v2 安装 | 1 | 4 | 15 |
| doctor，H 个有效 v2 宿主都引用当前 release | 0 | 1 + H | 3 × (1 + H) + 3 |
| deploy，源码改变需要新建 release | 2 | 依旧版本及宿主状态而变 | 依路径而变 |

计数推导：

1. 每次 verify_release 都校验全 release 的文件清单与 SHA，再按 codex / cursor / claude 三个目标分别复制整套 Skill、投影、重新计算清单（`installer.py:284-377,412-471`；`projection.py:10`）。portable 不复制。
2. install 外层 `installer.py:909` 一次、内层 `installer.py:706` 一次；已有 v2 安装经 `installer.py:732 → 182-190` 再一次。若旧安装指向不同 release，第三次检查的是旧 release，不应称为新 release 被检查三次。
3. deploy 可复用路径另加 `workflow.py:376` 一次。随后 `release_matches_source → source_manifest → _stage_release_tree → _manifest_for_staged_tree` 又构建一次完整临时产物并复制三宿主投影（`release.py:659-683,638-656,537-621,496-524`）。所以已有相同版本宿主时为 `4 × 3 + 3 = 15`。这是校验产生的投影复制；实际安装 staging 的一套复制另计。
4. doctor 的每个宿主经 `verify_installed_state` 又验证 source release，多个宿主引用同一 release 也没有共享验证结果（`doctor.py:38,76`；`installer.py:190`）。
5. deploy 不能复用时，`workflow.py:367` 先 check，`workflow.py:385-389 → 190-205 → release.py:762-764` 再 check；build 单独运行只有后者一轮。两者不是精确相同路径（活源树与快照），但首次运行不提供最后打包快照之外的必要保证，可将权威检查收敛到一次稳定快照。

这些次数显示确定的重复 I/O 和测试启动，不足以计算节省百分比。仍需对真实仓库记录各阶段耗时，再决定下一步优化。

## 最小改法与顺序

1. **先合并全量测试**：deploy 需要新包时，在实际构建的稳定快照上只跑一次 check；去掉前面活源树的完整 suite。静态验证可以供路由快速失败，但不得再隐藏触发第二轮 suite。
2. **再合并同操作的发布包验证**：把权威 verify 放在保护发布引用的锁内，向内部 install / installed-state 校验传递已验证上下文；doctor 在一次调用内按发布包身份共享验证。仅把当前外层 verify 的布尔结果带到锁内不够，会留下检查后文件变化的窗口。安装 staging 与最终目标的字节清单验证继续执行。
3. **改投影算法**：对确定性的 metadata / Markdown 投影，直接计算投影后的文件清单，避免为了验证而复制整套树三次。先验证与旧磁盘投影完全等价；真实安装只 staging 所选宿主，完整跨宿主投影回归由发布检查承担。无需新增服务或数据库。
4. **让无变化更新短路**：比较 release 保存的构建输入摘要；相同且发布验证有效时复用 release，不为 source-match 临时打包。若目标安装与所选 release / projection 一致且实际托管内容校验通过，返回 current，跳过重写。仍检查用户是否改过安装内容，不能只看 release_id。
5. **对外压缩操作**：保留清晰的 `deploy --target ...` 单入口；输出 source / release / requested host 的状态与执行过的校验。支持一次选多个宿主时共享一次发布检查，各宿主仍独立锁和事务。安装失败不把其他宿主写成已成功。

## 触发与证据原则

- 已验证 release 安装到另一宿主：发布包完整性 + 目标投影 / 目录所有权 + staging 与安装后清单；无需重新跑源码 unittest（现版 install 已遵守这一点）。
- 相同输入再次 deploy：可复用绑定同一输入的成功检查证据，核实 release 与目标宿主实际内容，避免重跑全套测试 / 临时打包。
- 初次建立证据、runtime / installer / build / projection / schema / composition 或资源依赖关系变化、测试本身与检查配置变化：完整 check；具体变更需对应故障恢复、投影和兼容测试。
- 纯 Skill / resource 正文变化：静态格式、引用及产物验证仍执行；是否只跑受影响测试需要先有明确、可验证的依赖边界。第一版优化可继续一次完整 check，不急于新增易漏判的测试选择器。真实语言质量另外通过行为任务验证。

若增加成功检查 receipt，至少绑定：规范化路径与内容摘要（包含新增 / 删除和链接身份）、构建器与校验器代码 / 协议版本、参与测试的源码与测试 / 配置、Python / 依赖环境身份、命令与结果、构建 upstream 参数；投影另绑定目标和投影器。不能只绑定 Git HEAD、时间戳或 release_id。区分“产物等价摘要”和“测试证据摘要”：正文未改变输出不代表测试 / 校验器改动后旧 check 仍有效。

无需一开始就做跨进程缓存平台：先合并单次调用上下文与全量测试，收益已可核验。若后来持久化 receipt，变更后失效，发布仍从该摘要所指的同一稳定快照生成；打包期间内容变化必须拒绝或重试。

## 不应删除的保护

- 稳定快照绑定验证与打包：`release.py:94-114,754-784`。前后清单比较用于防止验证 A 却发布 B；不要把所有 hash 一概算浪费。
- 发布 / 引用 / 宿主写锁：`release.py:733,875`，`installer.py:915-916`。跨宿主可以协调共享只读结果，不能无锁并发写同一目录。
- 路径与 symlink 检查、托管目录所有权、已存在同名用户内容保护、恢复日志、备份与回滚：`installer.py:544-696,729-783,815-898`。
- staging 与最终安装清单：`installer.py:795-800,851-867`。验证源 release 不证明复制和宿主投影成功。
- 源码、发布包、每个宿主状态仍分别报告：只需要一个操作入口，不应把多个独立事实折成一句“成功”。

## 建议追加的验收

- 源码变化的正常 deploy 全量 suite 恰好一次，检查和打包使用相同快照。
- 无变化更新有可验证的短路结果，不复制重写目标；篡改 release / installed Skill 必须被发现。
- 多宿主引用同 release，在同调用内共享发布验证，各宿主内容独立验证；所有失效条件有覆盖。
- 投影的新清单算法与旧目录投影输出字节等价；任一目标损坏不会因缓存复用漏报。
- 安装中断、并发更新、源码变动、旧格式 receipt、非托管同名目录等原有保护继续通过。
- 比较基线与候选的真实更新耗时、suite 次数、投影复制次数、重复验证次数，不预先承诺百分比。
