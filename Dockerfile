# 使用轻量级的 Python Alpine 镜像作为基础
FROM python:3.11-alpine

# 在一个指令层中完成所有软件包的更新和安装
RUN apk update && apk upgrade && \
    apk add --no-cache \
    curl \
    socat \
    busybox-extras \
    git \
    openssl

# 安装 Python 的 requests 库，用于发送 Webhook 通知
RUN pip install requests

# 直接从 GitHub 克隆 acme.sh 的代码仓库
RUN git clone https://github.com/acmesh-official/acme.sh.git /root/.acme.sh

# 为我们的应用程序设置主工作目录
WORKDIR /app

# 复制项目的所有组件到容器中
COPY src/ ./src/
COPY entrypoint.sh .

# 给予入口脚本执行权限
RUN chmod +x entrypoint.sh

# 设置容器的入口点
ENTRYPOINT ["/app/entrypoint.sh"]
