# CI / 安装后问题修复：独立复审计划

状态：准备完成，等待 root 提供最终只读冻结路径、source-manifest SHA256 和文件数。不能用正在修改的主仓源码形成结论。

## 对象与边界

- 用户给定当前 HEAD 04cd3f0、CI run 37029900314：Python 3.10 为 352 tests / 15 failures，3.14 被 matrix failfast 取消。这是提供的历史证据，准备阶段未自行核验远端 run，不视为 3.14 通过。
- 旧冻结 baseline：/tmp/outcome-compensation-final-01；其原独立报告：/tmp/outcome-compensation-review-final.md。本轮不改写原结论。
- 范围仅 evidence.py / batches.py 的 loader 身份兼容，以及 validator.py 对根运行记录/原始报告 fixture 的排除边界及交叉影响。
- 独立 reviewer 不参与生产修改，不读主仓变动生产源码，不调用 workflow 自身 Skills，不运行全 suite / 真实 host 安装 / deploy。不创建额外 reviewer；保留当前模型配置，不切换模型。
- 收到候选后先核验 manifest SHA256 与逐文件 bytes；读冻结差异，运行必要定向 probes；最后重复全部 hash 核验，保留脚本、命令、退出码、log/json 与发现。无反例后及时收敛。

## Loader 身份、诊断与缓存矩阵

| 控制 | 必须满足的合同 | 证据方式 |
| --- | --- | --- |
| 旧式 `missing (unittest.loader._FailedTest)` | 精确接受为 loader identity，完整 typed dependency 诊断可生成 fingerprint | 完整默认/verbose unittest 报告；直接谓词与 batch compare 两层 |
| 新式 `missing (unittest.loader._FailedTest.missing)` | 精确接受，保留旧版 v3 typed 完整诊断合同 | 当前 Python 真实 loader 输出及同报告 controls |
| 非 loader 包含该字串 | 任意子串、前后垃圾、伪类名、截断括号等不能建立 loader proof | 参数化近似身份：普通 TestCase 名含字串、额外 suffix、`FakeFailedTest`、不完整括号、仅正文包含字串 |
| 全 loader 相同完整缺依赖 | exit 非零、非 unavailable；完整 fingerprint 相同可 known，并披露比较缺口；非 current pass | 两种身份形式的报告比较；必要公共 CLI same-known close 控制 |
| 同 coarse identity 改变诊断 | ModuleNotFoundError 的模块名、调用栈/源码行变化均不能借身份成为 known | 两种身份；全 loader 与一个真实 passing TestCase 的 partial runner |
| 真实 Assertion / RuntimeError | 初始化或实际 TestCase 的真实非零失败不能被当 dependency proof；new failure 阻断 close | 实际 Python 进程异常/测试输出；必要公共 CLI 动态 import、Assertion→close 控制 |
| 缺失完整结构 | 不完整 headers/footer、计数矛盾、未知/重复身份块包含真实失败、非空 stdout 不能凭片段生成 proof | 完整报告的定向删除/变体；保持既有严格结构条件 |
| v3 旧缓存 | 原 v3 loader fingerprint 对相同完整诊断仍有效；此前缓存中没有 fingerprint 的旧式 identity 不可借 coarse equality 自动 known；改变诊断仍 new | 旧冻结实际 v3 receipt + 旧式控制；批次当前性/close 重评；不通过修改缓存制造 pass |
| v1/v2 与旧截断 | 完整日志可按新谓词重算；截断且无完整 fingerprint 不能推出 known/成功 | 复用原 controls 的真实诊断，仅声明旧 schema 迁移夹具；留原日志 |
| 启动缺口 | Python `-m` 缺 runner 和 OS 启动异常仍保留 unavailable；loader wrapper 不声称业务未执行 | 既有窄范围控制按需复用，避免无关矩阵 |

严格谓词判定以完整 failure identity 语法为准；不得仅用 `in` 或放宽任意后缀实现兼容。旧/新 identity 是否需要跨版本互转，只按最终合同判断：同一版本内恢复必须成立；不能把不同原始身份及不同完整诊断擅自归并成业务通过。

本机准备检查未找到 python3.10；python3 可用。最终若仍无 3.10，只能把适配的旧式 stderr 定义为 grammar fixture，不能标作真实 Python 3.10 运行或远端 CI 已修复。实际可用 Python 的 loader/业务反例仍须真实执行。远端 CI 成功需 root 的对应新 run 证据，不能由本地 grammar controls 代替。

## Markdown validator 排除边界矩阵

| 控制 | 预期 |
| --- | --- |
| 根 `.agent/work/<topic>/...` 的原始 review/report：指向 `/tmp` / 临时已消失 fixture | 在授权运行记录命名空间内不阻断源包验证 |
| 根归档 Topic 的对应原始报告 fixture | 仅最终明确授权的根归档命名空间可排除；不能因名称含 archive 任意跳过正式文档 |
| 根 `.agent/matt-workflow.md` 的有效本地链接 | 仍被检查，存在且留在 root 时通过 |
| 根 `.agent/matt-workflow.md` 的缺失、`../` 越 root、绝对外部、symlink 外部目标 | 仍明确拒绝；每个控制独立夹具，避免先遇到其他错误掩盖边界 |
| `.agent/other.md`、README/docs/resources 中正式文档的缺失/逃逸 | 仍明确拒绝，不因 `.agent` 被整体忽略 |
| `docs/.agent/work/...`、近似 `.agent/work-other/...` / 归档近似名 | 根前缀排除不能扩散到嵌套或近似正式路径 |
| 根正式文档引用缺失运行记录目标 | 只排除报告自身的链接扫描，不能豁免正式文档的链接缺失检查 |
| 有效 root 内引用、锚点、外部 HTTPS、既有 fenced/template 占位符 | 保留已有正向合同，不新增无关 Markdown 语法要求 |

优先用 `validate_markdown_references` 在独立最小临时目录检查真实文件/路径；必要时只运行相应定向源包校验入口，不运行会启动 fullsuite 的 check/deploy。检查最终路径选择谓词严格从 root 相对 parts 出发，并保留 destination.resolve 的逃逸与缺失拒绝。

## 交付与判定

最终报告将逐项区分：真实 CLI/真实异常、直接 parser/compare 控制、合成旧 schema/旧式报告输入，以及 root 提供的 CI/fullsuite 证据。合成 review pass 仍仅为门禁输入，不是业务模型验证。

发现具体反例时立即报告触发条件、命令/退出码、冻结定位及最小证据；不修改生产代码。没有问题时以限定范围结论、通过矩阵与前后 hash 收敛，不能宣称全仓/host/所有 Python 版本已验证。
