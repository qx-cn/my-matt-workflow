#!/usr/bin/env bash
# 人在回路的复现循环。
# 复制本文件、编辑以下步骤，然后运行。
# Agent 运行脚本；用户在终端中遵循提示操作。
#
# 用法：
#   bash hitl-loop.template.sh
#
# 两个辅助函数：
#   step "<instruction>"          → 显示说明，等待 Enter
#   capture VAR "<question>"      → 显示问题，将响应读入 VAR
#
# 最后会以 KEY=VALUE 输出捕获值，供 Agent 解析。

set -euo pipefail

step() {
  printf '\n>>> %s\n' "$1"
  read -r -p "    [完成后按 Enter] " _
}

capture() {
  local var="$1" question="$2" answer
  printf '\n>>> %s\n' "$question"
  read -r -p "    > " answer
  printf -v "$var" '%s' "$answer"
}

# --- 在下方编辑 ---------------------------------------------------------

step "打开 http://localhost:3000 并登录应用。"

capture ERRORED "点击“导出”按钮。是否抛出错误？(y/n)"

capture ERROR_MSG "粘贴错误信息（或输入“none”）："

# --- 在上方编辑 ---------------------------------------------------------

printf '\n--- 已捕获 ---\n'
printf 'ERRORED=%s\n' "$ERRORED"
printf 'ERROR_MSG=%s\n' "$ERROR_MSG"
