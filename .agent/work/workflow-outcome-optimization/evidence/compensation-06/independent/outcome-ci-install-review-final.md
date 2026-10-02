# CI / 安装后问题修复独立复审

结论：**限定范围内未发现阻断问题。旧/新版 unittest loader 格式兼容成立，严格失败门禁未退化；Markdown 排除仅限根 `.agent/work`，其他正式文档仍拒绝缺失和逃逸链接。** 本结论针对指定冻结字节；不代表 Python 3.10 CI、真实 host 安装或全仓业务验证已经通过。

## 对象与完整性

- 候选：`/tmp/outcome-ci-install-final-01`；旧冻结：`/tmp/outcome-compensation-final-01`。
- 开始：`2026-10-02T16:05:24.015529+00:00`；结束：`2026-10-02T16:09:56.609118+00:00`。
- 前后 `source-manifest.json` SHA256 均为 `00f4a151d8bdbb1280734ec1a0748d0561ffc7b63d4a6257d4e32aeeae060c55`，逐项核验均为 **285 文件、0 不匹配**。
- 与旧冻结清单逐项比较：仅 `tools/workflow_lib/evidence.py`、`batches.py`、`validator.py` 三个文件改变；仅新增 `tests/test_loader_report_compatibility.py`、`tests/test_validator_markdown_scope.py`，无删除。
- 独立 reviewer 未参与生产修改，未读主仓变动生产源码，未调用 workflow 自身 Skills，未启动 fullsuite、deploy 或真实 host install。作者两份说明仅作为声明读取，验证脚本和 controls 独立构造。

## 独立证据与结果

**7/7 函数/实际进程控制组、2/2 公共 CLI 控制组通过。** 保留 21 次真实测试进程的命令/stdout/stderr/exit、48 次真实公共 CLI 调用，以及 23 个 Markdown 路径控制。组数不是全量 suite 测试数，函数判定不伪记为 CLI 运行。

| 范围 | 独立控制 | 结果 |
| --- | --- | --- |
| 严格 loader 身份 | 两种完整合法 identity；伪类名、正文子串、无括号、括号截断、额外尾文本、带空白伪后缀等 9 个近似 identity | 合法接受，近似拒绝；谓词为完整 fullmatch，不是任意字串查找 |
| 实际旧式格式 | `/usr/bin/python3` 3.9.6，真实 all-loader 默认输出及 partial+verbose 输出 | 旧式 `_FailedTest)` 正确识别；all-loader 不误记为执行测试；partial 的真实 passing TestCase 被观测 |
| 实际新式格式 | Python 3.14.4，真实 all-loader verbose 输出及 partial 默认输出 | `_FailedTest.test_missing)` 正确识别；与旧式合同一致 |
| 相同完整 typed 诊断 | 两个版本的 baseline/current 同诊断 | 非 unavailable、非零退出；可 known；全 loader 保留 unverified 比较缺口，未记为 current pass |
| 同 identity 改变诊断 | 每个实际 runner 分别改缺失模块、改调用栈/源码行、改为真实初始化 AssertionError | 全 loader / partial 都形成 new failure，不能借 loader 名 become known；非 unavailable |
| 完整结构与 duplicate | 从真实报告构造旧/新格式 grammar controls；非空 stdout、错误计数、缺 footer、同 identity 第二块为真实 Assertion | 不生成 dependency proof；duplicate 中真实失败不能被第一块缺依赖掩盖 |
| 截断旧 v3 | 无完整 fingerprint 的截断缓存，与完整当前报告比较 | known 为空、new 非空；不从尾日志推断成功 |
| 旧 v3 空 fingerprint | 保留真实原始输出/exit/environment，重建原误分类派生字段 `execution_observed=true`、`comparison_eligible=true`、fingerprint 空 | 两种实际输出格式在 compare 中均被重评为 uncertain/new；公共 CLI close exit 1 |
| 真实公共 CLI 业务反例 | 两个 configured runner 下调用 `selected_plugin()` 的真实动态 import；真实 `assert 7 == 8`；marker 证明进入初始化逻辑 | 每个反例 close exit 1，即使提供合成 review pass 也不放行 |
| 公共 CLI 正向修复 | 实际 `RepairedBehavior.test_actual_value` 验证 `3+4 == 7` | 真实 `Ran 1 test`、测试 exit 0；刷新 test/review 后 close exit 0 |
| validator 根排除 | 根 `.agent/work` 的失效绝对原始报告链接和嵌套临时项目缺失链接 | 排除成立，校验通过 |
| validator 正式边界 | `.agent/matt-workflow.md`、`.agent/policy.md`、`.agent/archive`、docs、tests/fixtures、嵌套 `docs/.agent/work`、`.agent/work-other` | 每个缺失链接和 root 逃逸链接分别拒绝 |
| validator 其他保护 | 正式配置绝对逃逸、symlink 外部目标、正式 README 引用缺失 runtime 文件 | 明确拒绝；排除报告扫描没有豁免引用它的正式文档 |
| validator 正例 | 有效根内链接、锚点、HTTPS、fenced 示例 | 既有合同保留 |

## 实现判断

`loader_failure_identity()` 对完整身份作锚定匹配，支持旧类身份和新版带 method 的类身份；evidence 的 execution/loader-only/fingerprint 消费者及 batches 的 coarse-identity 消费者共同使用它。此次兼容没有增加 loader startup 免责：业务初始化仍可能执行，ModuleNotFoundError 与 wrapper 本身都不证明环境不可用。

v3 typed 完整诊断 hash 算法没有变化。因此保留 proof version 3 本身不构成漏洞；旧 3.10 误分类收据的空 fingerprint 不能建立 matching-loader，新的 coarse 识别使其成为 uncertain/new。本轮用真实输出重建该旧派生分类，并在公共 CLI 验证 close 拒绝；并未只检查新建记录。

validator 只增加对 repository-root `.agent/work` 子树的扫描排除，没有整体排除 `.agent`，没有排除 `.agent/archive` 或 `tests/fixtures`，没有改变链接 destination.resolve 后的 root 逃逸和文件存在性检查。独立 23 个路径控制覆盖了这些边界。最终合同比准备时归档排除的可能性更窄，本轮按用户最终要求保留根 `.agent/archive` 校验。

## 命令、退出码与原始证据

```text
python3 -B /tmp/outcome-ci-install-review-probe.py /tmp/outcome-ci-install-final-01 /tmp/outcome-ci-install-review-probe.json
# process exit 0; 7 groups pass
python3 -B /tmp/outcome-ci-install-review-cli.py /tmp/outcome-ci-install-final-01 /tmp/outcome-ci-install-review-cli.json
# process exit 0; 2 groups pass
```

公共 workflow CLI 的宿主解释器为 Python 3.14.4；配置的测试 runner 分别是 `/usr/bin/python3` 3.9.6 和 `python3` 3.14.4。两组各 24 次公共 CLI 调用，关键退出码均为：旧 v3 cache close=1，dynamic close=1，Assertion close=1，真实 passing repair close=0。每条真实命令与原始输出均在 JSON 中保存。

- [独立函数/进程探针](/tmp/outcome-ci-install-review-probe.py)、[日志](/tmp/outcome-ci-install-review-probe.log)、[原始函数/进程与路径证据](/tmp/outcome-ci-install-review-probe.json)。
- [独立公共 CLI 探针](/tmp/outcome-ci-install-review-cli.py)、[CLI 日志](/tmp/outcome-ci-install-review-cli.log)、[原始 CLI/退出证据](/tmp/outcome-ci-install-review-cli.json)。
- [结果摘要](/tmp/outcome-ci-install-review-summary.json)、[开始核验](/tmp/outcome-ci-install-review-start.json)、[结束核验](/tmp/outcome-ci-install-review-end.json)。
- 所有本轮证据文件的 SHA256：[证据清单](/tmp/outcome-ci-install-review-evidence-manifest.json)。

## 证据边界

Python 3.9.6 是实际旧 loader 格式证据，**不是 Python 3.10 pass**；本机未运行 3.10，也未把 3.9 workflow runner 控制声明为整个 workflow 在 3.9 的完整验证。精确 Python 3.10/3.14 GitHub CI 结果由新 run 单独证明，本轮未等待或自行核验该新 run。旧 run 37029900314 的 3.10 failures 与 3.14 failfast cancellation 来自提供的诊断声明，本轮不将 cancellation 解读为通过。

duplicate/截断以及旧缓存派生字段是明确的受控输入；实际 Python 的动态 import/Assertion 和 passing TestCase 均真正执行。合成 review pass 仅为门禁输入，不是真实模型 reviewer 业务验证。本轮没有安装、发布或 deploy 状态结论，也不重写原补偿复审报告或已完成历史。
