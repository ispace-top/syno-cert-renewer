# Synology Cert Renewer

[![GitHub Release](https://img.shields.io/github/v/release/ispace-top/syno-cert-renewer?style=for-the-badge&logo=github)](https://github.com/ispace-top/syno-cert-renewer/releases)
[![Docker Image Build Status](https://img.shields.io/github/actions/workflow/status/ispace-top/syno-cert-renewer/docker-image.yml?branch=main&label=Docker%20Image&logo=docker&style=for-the-badge)](https://github.com/ispace-top/syno-cert-renewer/actions/workflows/docker-image.yml)
[![Docker Pulls](https://img.shields.io/docker/pulls/ispace/syno-cert-renewer?style=for-the-badge&logo=docker)](https://hub.docker.com/r/ispace/syno-cert-renewer)

---

这是一个强大且易于部署的 Docker 化工具，专为群晖 (Synology) NAS 用户设计。它能自动为您申请和续签 Let's Encrypt 泛域名证书，支持自动部署到 DSM 系统，并通过企业微信应用发送通知，确保您的证书始终有效，且重要信息不遗漏。

## ✨ 特点概览

* **全自动化**: 一次设置，通过 Cron 定时任务实现证书的自动续签，省心省力。

* **泛域名支持**: 利用 DNS Challenge 模式，轻松申请 `your.domain` 和 `*.your.domain` 的泛域名证书。

* **Docker 部署**: 提供干净、隔离、高度可移植的运行环境，部署和迁移极为简便。

* **灵活配置**: 支持通过环境变量或挂载 `config.json` 文件进行配置，环境变量优先级更高，方便集成到不同环境。

* **企业微信通知**: 集成标准企业微信应用消息通知 (支持 `corpid`, `corpsecret`, `agentid`)，而非简单的 Webhook，确保消息送达可靠。

* **自动部署 DSM**: 自动化将新签发的证书安全导入到群晖 DSM 的证书库中，无需手动操作。

## 🚀 如何使用

### 1. 准备 DNS API 凭证

本工具依赖 `acme.sh` 的 DNS Challenge 模式来验证域名所有权。您需要从您的 DNS 服务商（例如 Cloudflare, GoDaddy, DNSPod 等）获取相应的 API 密钥。

请查阅 [acme.sh - DNS API 文档](https://github.com/acmesh-official/acme.sh/wiki/dnsapi)，找到您的服务商所需的环境变量名称。例如，对于 Cloudflare，您可能需要 `CF_Token` 和 `CF_Account_ID`。

### 2. 准备企业微信应用参数 (可选)

如果您希望接收证书续签通知，需要在企业微信后台创建一个应用。

1. 登录 [企业微信管理后台](https://work.weixin.com/)。

2. 导航至「应用管理」 -> 「应用」 -> 「自建」，点击「创建应用」。

3. 创建应用后，您将获得 `AgentId` 和 `Secret`。

4. 在「我的企业」页面，您可以找到您的 `企业ID (CorpID)`。

5. `touser` 参数用于指定消息接收者，`@all` 表示发送给应用可见范围内的所有成员。

### 3. 编写 `docker-compose.yml` 文件

推荐使用 `docker-compose` 来管理您的容器，这使得配置和启动过程更加简洁。

创建一个 `docker-compose.yml` 文件，并根据您的实际情况进行修改：

```yaml
version: '3.8'

services:
  cert-renewer:
    image: ispace/syno-cert-renewer:latest # 推荐使用最新的官方镜像
    container_name: syno-cert-renewer
    restart: unless-stopped
    volumes:
      # 挂载输出目录，用于存放生成的证书文件。重要！
      - ./output:/output 
      # (必须) 挂载一个用于缓存企业微信 access_token 的临时目录。重要！
      - ./temp:/temp
      # (可选) 挂载配置文件目录。如果使用 config.json，则需要此项。
      - ./config:/config
    environment:
      # --- 基础配置 (必填项) ---
      - DOMAIN=your.domain.com          # 您的主域名 (例如: example.com)
      - DNS_API=dns_cf                  # 您的 DNS 提供商 API 类型 (例如: dns_cf for Cloudflare, dns_dp for DNSPod)
      - ACME_EMAIL=youremail@example.com # 您的电子邮件地址，用于 Let's Encrypt 注册和通知

      # --- DNS API 凭证 (根据您的 DNS_API 类型填写) ---
      # 例如：Cloudflare:
      # - CF_Token=your_cloudflare_api_token
      # - CF_Account_ID=your_cloudflare_account_id
      # 例如：DNSPod:
      # - DP_Id=your_dnspod_id
      # - DP_Key=your_dnspod_key

      # --- (可选) 自动部署到 Synology DSM 配置 ---
      # ⚠️ 敏感信息如密码，强烈建议放入 config.json 而非环境变量
      - AUTO_DEPLOY_TO_SYNOLOGY=true    # 设置为 true 启用自动部署
      - SYNO_USERNAME=your_dsm_admin_user # 群晖管理员用户名
      - SYNO_PASSWORD=your_dsm_admin_password # 群晖管理员密码
      - SYNO_PORT=5001                  # 群晖 DSM 端口 (例如: 5001 for HTTPS)
      - SYNO_PROTOCOL=https             # 群晖 DSM 访问协议 (http 或 https)

      # --- (可选) 企业微信通知配置 ---
      - WECOM_CORP_ID=your_corp_id      # 企业微信企业 ID
      - WECOM_CORP_SECRET=your_corp_secret # 企业微信应用 Secret
      - WECOM_AGENT_ID=your_agent_id    # 企业微信应用 AgentId
      - WECOM_TOUSER=@all               # 消息接收者 (可为成员ID, 部门ID, 或 @all)
      
      # --- (可选) 定时任务配置 ---
      - CRON_SCHEDULE=0 3 * * * # Cron 表达式，默认每天凌晨3点执行。格式: 分 时 日 月 周

    # 容器需要网络管理员权限才能执行 DNS Challenge
    cap_add:
      - NET_ADMIN
```

### 4. 配置文件 `config.json` (可选，但推荐用于敏感信息)

您可以通过挂载 `config.json` 文件来管理配置，这对于存放敏感信息（如密码）尤其推荐。请注意，**环境变量的优先级总是高于 `config.json` 中的配置**。

在 `./config/config.json` 路径下创建您的配置文件，例如：

```json
{
  "general": {
    "domain": "your.domain.com",
    "dns_api": "dns_cf",
    "acme_email": "youremail@example.com",
    "cert_output_path": "/output"
  },
  "synology": {
    "auto_deploy": true,
    "username": "your_dsm_admin_user",
    "password": "your_dsm_admin_password",
    "port": 5001,
    "protocol": "https"
  },
  "notifiers": {
    "wecom": {
      "corp_id": "your_corp_id_from_config",
      "corp_secret": "your_corp_secret_from_config",
      "agent_id": "your_agent_id_from_config",
      "touser": "@all"
    }
  }
}
```

> ### ⚠️ **安全警告**
>
> 启用自动部署功能需要提供您的群晖**管理员**凭证。将密码等敏感信息以明文形式存储在环境变量或配置文件中都存在潜在的安全风险。请确保您的 Docker 主机和配置文件是安全的。**强烈建议您为该工具专门创建一个权限受限的群晖管理员账户，并严格管理您的 `config.json` 文件权限，防止未经授权的访问。**

### 5. 启动容器

在 `docker-compose.yml` 文件所在的目录执行以下命令：

```bash
# 首先创建必要的本地目录，用于挂载数据
mkdir -p ./output ./temp ./config

# 如果您选择使用 config.json，请先创建并编辑它
# nano ./config/config.json 

# 启动 Docker 容器 (首次启动会立即执行证书申请流程)
docker-compose up -d
```

容器首次启动后，会立即执行一次证书的检查与申请流程。此后，它将根据您在 `CRON_SCHEDULE` 环境变量中设置的定时任务表达式（默认为每天凌晨3点）自动执行证书续签。

## 🛠️ 项目结构速览

```
.
├── .github/                       # GitHub Actions 工作流
│   └── workflows/
│       ├── docker-image.yml       # Docker 镜像构建和推送流程
│       └── docker-publish.yml     # Docker 镜像发布流程 (与 docker-image.yml 功能类似，可能用于不同目的)
├── entrypoint.sh                  # 容器启动脚本，用于初始化并设置 cron 任务
├── src/                           # 核心 Python 源代码
│   ├── config/
│   │   ├── config.json            # 示例配置文件
│   │   └── docker-compose.yml     # 示例 docker-compose 配置
│   ├── config_manager.py          # 负责配置加载和管理 (环境变量覆盖文件配置)
│   ├── main.py                    # 主程序入口，协调证书申请、部署和通知流程
│   └── notifiers/                 # 通知模块
│       ├── base_notifier.py       # 通知器抽象基类
│       ├── notification_manager.py # 通知分发管理
│       └── wecom_notifier.py      # 企业微信通知具体实现
└── README.md                      # 本文档
```

## 💖 贡献与支持

欢迎各种形式的贡献，包括但不限于 Bug 报告、功能请求、代码提交或文档改进。如果您觉得这个项目对您有帮助，请考虑给项目一个 Star！

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。

---
