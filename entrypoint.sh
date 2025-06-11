#!/bin/sh

# 立即退出如果任何命令失败
set -e

# --- 首次运行 ---
echo "================================================="
echo "==      Synology Cert Renewer by Kerwin        =="
echo "================================================="
echo " "
echo ">> 容器启动，立即执行一次证书检查与申请..."
# 直接执行 python 脚本
python /app/src/main.py

# --- 设置 Cron 定时任务 ---
echo " "
echo ">> 设置定时续签任务..."
# 清理旧的 cron 设置
rm -f /etc/crontabs/root

# 设置默认的 Cron 表达式 (每天凌晨 3:00)
DEFAULT_CRON_SCHEDULE="0 3 * * *"

# 使用用户提供的 CRON_SCHEDULE 环境变量，如果未提供则使用默认值
CRON_JOB_SCHEDULE="${CRON_SCHEDULE:-$DEFAULT_CRON_SCHEDULE}"

# 创建一个新的 crontab 文件
# 将标准输出和错误输出都重定向到 docker 日志
echo "$CRON_JOB_SCHEDULE python /app/src/main.py >> /proc/1/fd/1 2>>/proc/1/fd/2" > /etc/crontabs/root

echo ">> 定时任务已设置为: '$CRON_JOB_SCHEDULE'"
echo " "
echo ">> 启动 cron 服务... 容器将持续运行。"
echo "================================================="

# 在前台启动 crond 服务，这样容器就不会退出
# -f: foreground
# -l 8: log level (8=debug)
exec crond -f -l 8
