#!/bin/sh

# 立即退出如果任何命令失败
set -e

# --- 保存环境变量 ---
echo ">> Saving environment variables..."
# 只保存合法的环境变量名称（以字母或下划线开头，只包含字母、数字、下划线）
printenv | grep -E '^[a-zA-Z_][a-zA-Z0-9_]*=' | sed 's/^\$$.*\$$$$export \1/g' > /app/env.sh
echo ">> Environment variables saved."
echo " "

# --- 首次运行 ---
echo "================================================="
echo "==      Synology Cert Renewer by Kerwin        =="
echo "================================================="
echo " "

# 在前台启动主程序，使用内部循环定时执行任务，避免容器重启
echo ">> 启动证书续签服务... 容器将持续运行。"
echo "================================================="

# 在前台启动Python脚本，让它自己管理定时任务
. /app/env.sh
exec python /app/src/main_loop.py
