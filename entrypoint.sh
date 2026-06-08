#!/bin/sh

set -e

# 设置默认时区为Asia/Shanghai，除非已设置
if [ -z "$TZ" ]; then
  TZ="Asia/Shanghai"
fi

# 设置时区
ln -sf "/usr/share/zoneinfo/$TZ" /etc/localtime
echo "$TZ" > /etc/timezone

# 创建环境变量脚本
echo "#!/bin/sh" > /app/env.sh

# 只保存合法的环境变量名称（以字母或下划线开头，只包含字母、数字、下划线）
printenv | grep -E '^[a-zA-Z_][a-zA-Z0-9_]*=' | awk -F'=' '{print "export " $1 "=\"" $2 "\""}' >> /app/env.sh

chmod +x /app/env.sh

# 启动主程序
if [ "$1" = "loop" ]; then
  echo "Starting in loop mode..."
  exec python /app/src/main_loop.py
else
  echo "Starting in single run mode..."
  exec python /app/src/main.py
fi