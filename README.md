# Synology Cert Renewer

[![GitHub Release](https://img.shields.io/github/v/release/ispace-top/syno-cert-renewer?style=for-the-badge&logo=github)](https://github.com/ispace-top/syno-cert-renewer/releases)
  [![Docker Image Build Status](https://img.shields.io/github/actions/workflow/status/ispace-top/syno-cert-renewer/docker-image.yml?branch=main&label=Docker%20Image&logo=docker&style=for-the-badge)](https://github.com/ispace-top/syno-cert-renewer/actions/workflows/docker-image.yml)
  [![Docker Pulls](https://img.shields.io/docker/pulls/wapedkj/syno-cert-renewer?style=for-the-badge&logo=docker)](https://hub.docker.com/r/wapedkj/syno-cert-renewer)
  [![Docker Image Version](https://img.shields.io/docker/v/wapedkj/syno-cert-renewer/latest?style=for-the-badge&label=docker%20image%20version)](https://hub.docker.com/r/wapedkj/syno-cert-renewer/tags)
---

这是一个强大且易于部署的 Docker 化工具，专为群晖 (Synology) NAS 用户设计。它能自动为您申请和续签 Let's Encrypt 泛域名证书，支持自动部署到 DSM 系统，并通过企业微信应用发送通知，确保您的证书始终有效，且重要信息不遗漏。

## ✨ 特点概览

* **全自动化**: 一次设置，通过 Cron 定时任务实现证书的自动续签，省心省力。

* **智能检查**: 每次运行前，首先通过 `openssl` 检查域名现有证书的有效期。仅当证书即将到期时（可配置天数）才执行续签流程，最大限度避免了因频繁申请而导致的 Let's Encrypt 速率限制。

* **泛域名支持**: 利用 DNS Challenge 模式，轻松申请 `your.domain` 和 `*.your.domain` 的泛域名证书。

* **Docker 部署**: 提供干净、隔离、高度可移植的运行环境，部署和迁移极为简便。

* **灵活配置**: 支持通过环境变量或挂载 `config.json` 文件进行配置，环境变量优先级更高，方便集成到不同环境。

* **企业微信通知**: 集成标准企业微信应用消息通知 (支持 `corpid`, `corpsecret`, `agentid`)，而非简单的 Webhook，确保消息送达可靠。

* **自动部署 DSM**: 自动化将新签发的证书安全导入到群晖 DSM 的证书库中，无需手动操作。

* **群晖兼容**: 生成群晖所需的三个独立证书文件（私钥、证书、中间证书），确保完全兼容 DSM 证书导入要求。

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
    image: wapedkj/syno-cert-renewer:latest # 推荐使用最新的官方镜像
    container_name: syno-cert-renewer
    restart: always # 推荐使用 always 策略以确保服务持续运行
    volumes:
      # (必须) 使用命名卷来持久化 acme.sh 的程序和数据，Docker将自动为您管理
      - acme_sh_data:/root/.acme.sh
      
      # (必须) 挂载输出目录，用于在主机上直接获取生成的证书文件
      - ./output:/output 
      
      # (必须) 挂载一个用于缓存企业微信 access_token 的临时目录
      - ./temp:/temp

      # (可选) 如果您希望使用文件进行配置，请取消此行的注释
      # - ./config:/config
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
      - SYNO_HOSTNAME=192.168.1.100     # 群晖 DSM IP 地址或域名
      - SYNO_PORT=5001                  # 群晖 DSM 端口 (HTTP: 5000, HTTPS: 5001)
      - SYNO_SCHEME=https               # 群晖 DSM 访问协议 (http 或 https)
      - SYNO_CERTIFICATE=               # 证书描述名称 (空为默认证书)
      - SYNO_CREATE=1                   # 允许创建新证书 (1: 允许, 0: 不允许)

      # --- (可选) 企业微信通知配置 ---
      - WECOM_CORP_ID=your_corp_id      # 企业微信企业 ID
      - WECOM_CORP_SECRET=your_corp_secret # 企业微信应用 Secret
      - WECOM_AGENT_ID=your_agent_id    # 企业微信应用 AgentId
      - WECOM_TOUSER=@all               # 消息接收者 (可为成员ID, 部门ID, 或 @all)
      
      # --- (可选) 定时与检查配置 ---
      - CRON_SCHEDULE=0 3 * * * # Cron 表达式，默认每天凌晨3点执行。格式: 分 时 日 月 周
      - RENEW_DAYS_BEFORE_EXPIRY=30 # 证书过期前多少天开始尝试续签，默认30天

# 在文件末尾声明命名卷
volumes:
  acme_sh_data:
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
    "cert_output_path": "/output",
    "renew_days_before_expiry": 30
  },
  "synology": {
    "auto_deploy": true,
    "username": "your_dsm_admin_user",
    "password": "your_dsm_admin_password",
    "hostname": "192.168.1.100",
    "port": 5001,
    "scheme": "https",
    "certificate": "",
    "create": "1"
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
# 首先创建用于输出证书和缓存文件的本地目录
mkdir -p ./output ./temp

# 如果您选择使用 config.json，请先创建 config 目录和文件
# mkdir ./config
# nano ./config/config.json 

# 启动 Docker 容器 (首次启动会立即执行证书申请流程)
docker-compose up -d
```

容器首次启动后，会立即执行一次证书的检查与申请流程。此后，它将根据您在 `CRON_SCHEDULE` 环境变量中设置的定时任务表达式（默认为每天凌晨3点）自动执行证书续签。

## 📋 证书文件输出

工具会在输出目录（默认 `./output`）中生成群晖所需的证书文件：

```
output/
├── privkey.pem    # 私钥文件（无密码保护）
├── cert.pem       # 证书文件（仅包含域名证书）
├── chain.pem      # 中间证书文件
└── fullchain.pem  # 完整证书链（证书+中间证书，备用）
```

### 群晖 DSM 导入说明

在群晖 DSM 中手动导入证书时：
- **私钥**: 使用 `privkey.pem`
- **证书**: 使用 `cert.pem` 
- **中间证书**: 使用 `chain.pem`

所有证书文件均为 X.509 PEM 格式，私钥支持 ECC 和 RSA 格式且无密码保护，完全符合群晖要求。

## 🔧 群晖自动部署故障排除

如果群晖自动部署功能不生效，请按以下步骤排查：

### 1. 检查必要的配置参数
确保以下环境变量或配置文件中都已正确设置：
```bash
AUTO_DEPLOY_TO_SYNOLOGY=true
SYNO_USERNAME=your_admin_user      # 群晖管理员账户
SYNO_PASSWORD=your_admin_password  # 群晖管理员密码
SYNO_HOSTNAME=192.168.1.100       # 群晖 IP 地址
SYNO_PORT=5001                    # DSM 端口
SYNO_SCHEME=https                 # 访问协议
SYNO_CREATE=1                     # 允许创建新证书
```

### 2. 网络连通性测试
从容器内测试是否能访问群晖 DSM：
```bash
# 测试网络连通性
curl -k https://192.168.1.100:5001

# 检查 DSM 登录接口
curl -k -X POST https://192.168.1.100:5001/webapi/auth.cgi \
  -d "api=SYNO.API.Auth" \
  -d "version=2" \
  -d "method=login" \
  -d "account=your_admin_user" \
  -d "passwd=your_admin_password"
```

### 3. 常见问题解决

**问题 1：频繁重复申请证书 / 被 Let's Encrypt 限制**
- **根本原因**: `acme.sh` 的状态没有被持久化。
- **解决方案**: 检查您的 `docker-compose.yml` 文件，确保您已按照文档说明，正确使用了名为 `acme_sh_data` 的**命名卷 (Named Volume)** 来持久化 `/root/.acme.sh` 目录。这是确保 `acme.sh` 能够记住已申请证书的关键。

**问题 2：认证失败**
- 确认用户名和密码正确
- 检查用户是否有管理员权限
- 如果启用了 2FA，需要先在浏览器登录并勾选"记住此设备"

**问题 3：证书部署失败**
- 确保设置了 `SYNO_CREATE=1` 以允许创建新证书
- 检查证书描述是否冲突（`SYNO_CERTIFICATE` 参数）
- 验证网络连通性和端口是否正确

**问题 4：部署成功但未生效**
- 检查 DSM 中证书是否已导入
- 确认服务是否已重启使用新证书
- 手动重启相关服务（如 Web Station、VPN Server 等）

### 4. 调试模式
启用详细日志来诊断问题：
```bash
# 在环境变量中添加
DEBUG=1
```

或手动执行部署命令查看详细输出：
```bash
/root/.acme.sh/acme.sh --deploy -d your.domain.com --deploy-hook synology_dsm --debug 2
```

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
