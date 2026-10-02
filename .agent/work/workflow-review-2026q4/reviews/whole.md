# 整体审查

独立新上下文whole_review，只读，不使用施工/审查Skill；范围c4809cc44a99def8433ec84ea47968038416de16..fe48f48。独立全量 python3 -m unittest discover -s tests：274项，233.254s，OK，退出0。另独立真实Go临时仓库、两个unittest临时Git仓库探针。

3 blocking、0 advisory，均在tools/workflow_lib/batches.py旧版150–186行：

1. Go只按测试名合并，缺package身份。基线example.com/probe/a.TestSame失败，当前新增b.TestSame失败，比较new_failures=[]，批次可错误放行。违反AC25/I2。
2. 任意ModuleNotFoundError把整命令视为无法运行。基线test_missing缺依赖但test_behavior实际通过，当前test_behavior新增FAIL仍被整命令跳过，new_failures=[]、unverified保留命令。违反AC25/26/I2；根本无法运行不等于部分执行。
3. pytest失败正则误捕unittest汇总FAILED (failures=2)。当前修好一个已知失败，比较将(failures=1)当作新增用例而错误阻断。违反AC25。

修复：Go按包结果绑定失败用例且保留失败包（含build failed）；pytest正则排除括号汇总；环境识别判断实际测试执行，部分缺依赖保留可运行结果进行基线比较。旧已误标partial baseline根据存储输出恢复比较。追加三个回归，含真实unittest公共CLI收口和部分缺依赖新增阻断。

新上下文whole_rereview复审通过，原3 blocking及本轮1 advisory均修复，无剩余blocking/advisory。独立实际Go/unittest/exit127包装器/缺失可执行程序探针均通过。最终定向命令python3 -B -m unittest discover -s tests -p test_batches.py：15项，39.608s，OK，退出0。独立全套277项/296.729s/OK/退出0，启动于最后的存量Go和退出码precedence补充之前，不声称为最终代码完整全测；最终差异由定向和实际探针验证。最终两个源码哈希已由主Agent复核，记录evidence/whole-rereview.json。pytest未安装，只有格式边界检查。

复审另报1 advisory：存量Go基线裸测试名与新包身份不兼容，即使未变也可能误报新增。影响面内低成本修复：从已存原始Go包结果重新解析，不以裸名跨包宽松等同；新增旧基线未变/新增b两边界断言。若旧输出尾部截断，继续保守阻断并在最终报告披露。

环境边界补充：真实包装器执行unittest后退出127时仍按可执行结果比较；缺失可执行文件仍无法验证。独立复审者已实际探针验证两种路径。

主Agent最终固定版本全套：python3 -m unittest discover -s tests，277项/258.039s/OK/退出0；15项批次定向/43.564s/OK。日志evidence/whole-final-tests.txt、whole-final-batch-tests.txt。git diff --check与workflow.py validate通过；主链文本仍33,919字符。全部修复后两个源码哈希与独立复审一致。
