# 群晖泛域名证书自动续签工具 (Syno Cert Renewer)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-ready-blue.svg)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)

✨ 一个轻量、稳定、一劳永逸的群晖 NAS 泛域名 SSL 证书解决方案。

本项目旨在通过 Docker，全自动地为你的群晖 NAS 申请并续签由 Let's Encrypt 颁发的**泛域名** SSL 证书，让你彻底告别手动续签的烦恼。

## 核心特性

-   **🚀 全自动**: 首次运行立即申请，之后通过定时任务每天检查，在证书过期前自动续签。
-   **🛡️ 泛域名支持**: 一次申请，`yourdomain.com` 和 `*.yourdomain.com` 全部搞定。
-   **📦 Docker化部署**: 将所有依赖和复杂性封装在 Docker 容器内，保持宿主机环境纯净。
-   **🔧 配置简单**: 所有配置均通过环境变量完成，无需修改任何代码。
-   **☁️ 主流 DNS 支持**: 内置支持**阿里云**和**腾讯云(DNSPod)**的 DNS-API 验证方式。
-   **🔒 安全可靠**: 基于业界标准的 `acme.sh` 脚本，流程透明，安全可靠。

## 工作原理

本工具的核心是一个 Docker 容器，其内部包含：

1.  **`acme.sh`**: 强大的 Let's Encrypt 客户端，负责证书的申请和续签。
2.  **`Python 脚本`**: 作为主控逻辑，负责从环境变量读取配置，调用 `acme.sh`，并将生成的证书文件妥善放置到指定目录。
3.  **`Cron`**: 一个轻量级的定时任务服务，负责每天定时触发 Python 脚本，检查并执行续签任务。

容器启动后，会立即执行一次证书申请流程。同时，它会设定一个每天凌晨3点的定时任务，以确保证书在到期前被自动更新。

## 前提条件

在开始之前，请确保你已具备：

1.  一台运行 DSM 7.x 或更高版本的群晖 NAS。
2.  已在群晖套件中心安装并运行 **Container Manager** (旧版 DSM 中名为 Docker)。
3.  一个属于你自己的域名，并且能够修改其 DNS 解析记录。
4.  拥有该域名所使用的 **阿里云** 或 **腾讯云** 账号，并已获取 API 访问凭证 (AccessKey ID 和 Secret)。

## 部署指南

部署过程分为两步：构建 Docker 镜像，然后在群晖中运行容器。

### 步骤 1: 构建 Docker 镜像

> **你可以选择以下任一方式将镜像弄到你的群晖上。**

#### 方式 A: 在本地电脑构建并推送到 Docker Hub (推荐)

这是最方便的方式，便于多设备部署和分享。

1.  在你的电脑上安装 Docker。
2.  克隆或下载本项目所有文件。
3.  在项目根目录下打开终端，运行构建命令：
    ```bash
    docker build -t your-dockerhub-username/syno-cert-renewer:latest .
    ```
    *(请将 `your-dockerhub-username` 替换为你的 Docker Hub 用户名)*

4.  登录并推送镜像到 Docker Hub：
    ```bash
    docker login
    docker push your-dockerhub-username/syno-cert-renewer:latest
    ```

#### 方式 B: 在本地电脑构建并导出为文件

如果你不想使用 Docker Hub，可以构建后导出，再上传到群晖。

1.  同上，先在本地电脑构建镜像：
    ```bash
    docker build -t syno-cert-renewer:latest .
    ```
2.  将镜像保存为 `.tar` 文件：
    ```bash
    docker save -o syno-cert-renewer.tar syno-cert-renewer:latest
    ```
    现在你得到了一个 `syno-cert-renewer.tar` 文件，可以上传到群晖了。

### 步骤 2: 在群晖 Container Manager 中配置并运行容器

1.  **导入镜像**
    -   **如果使用方式A**: 打开 **Container Manager** -> **注册表**，搜索你刚刚推送的镜像 (`your-dockerhub-username/syno-cert-renewer`)，选中后点击 **下载**。
    -   **如果使用方式B**: 打开 **Container Manager** -> **映像** -> **新增** -> **从文件上传**，然后选择你导出的 `syno-cert-renewer.tar` 文件。

2.  **创建容器**
    -   转到 **映像** 菜单，找到 `syno-cert-renewer:latest` 镜像，选中它并点击 **运行**。

3.  **常规设置**
    -   给你的容器起个名字，例如 `syno-cert-renewer`。
    -   点击 **高级设置**。

4.  **配置卷 (重要！)**
    -   切换到 **卷** 标签页。
    -   点击 **添加文件夹**。
    -   **文件/文件夹**: 在你的 `docker` 共享文件夹下创建一个用于存放证书的目录，例如 `certs`，然后在这里选择它。路径类似于 `/volume1/docker/certs`。
    -   **装载路径**: **必须**填写 `/output`。这是容器内部的路径，程序会将证书文件写入这里。

    ![Volume Mapping Example](https://i.imgur.com/uN8GflW.png) *(这是一个示例图，请根据你的实际路径选择)*

5.  **配置环境变量 (核心！)**
    -   切换到 **环境** 标签页。
    -   参考下表，点击 **新增**，逐一添加所有必要的环境变量。

    | 变量名           | 示例值                          | **说明** |
    | :--------------- | :------------------------------ | :--------------------------------------------------------------------------- |
    | `DOMAIN`         | `yourdomain.com`                | **【必填】** 你的主域名。                                                     |
    | `DNS_API`        | `dns_ali`                       | **【必填】** DNS 提供商。`dns_ali` (阿里云) 或 `dns_dp` (腾讯云 DNSPod)。       |
    | `API_KEY`        | `LTxxxxxxxxxxxxxx`              | **【必填】** 你的 DNS API Key (阿里云的 AccessKey ID 或腾讯云的 DP_Id)。       |
    | `API_SECRET`     | `GZyyyyyyyyyyyyyyyy`            | **【必填】** 你的 DNS API Secret (阿里云的 AccessKey Secret 或腾讯云的 DP_Key)。 |
    | `CERT_OUTPUT_PATH`| `/output`                      | **【保持不变】** 容器内证书输出路径，与上面设置的卷装载路径对应。               |
    | `ACME_EMAIL`     | `your-real-email@gmail.com`     | **【建议填写】** 用于 Let's Encrypt