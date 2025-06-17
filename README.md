Synology Cert Renewer
这是一个 Docker 化的工具，用于自动为您的群晖 (Synology) NAS 申请和续签 Let's Encrypt 泛域名证书，并支持自动部署到 DSM 系统以及通过企业微信应用发送通知。

特点
自动化: 设置一次，通过 Cron 定时任务自动续签。

泛域名支持: 使用 DNS Challenge 方式申请 your.domain 和 *.your.domain 的泛域名证书。

Docker化: 干净、隔离、易于部署和迁移。

灵活配置: 通过环境变量或挂载的 config.json 文件进行配置，环境变量优先。

【新】标准企业微信通知: 通过应用消息 (corpid, corpsecret, agentid) 发送通知，而非简单的 Webhook。

【新】自动部署: 可自动将新证书安全地导入到群晖 DSM 的证书库中。

如何使用
1. 准备 DNS API 凭证
本工具使用 acme.sh 的 DNS Challenge 模式。您需要前往您的 DNS 服务商（如 Cloudflare, GoDaddy, DNSPod 等）获取 API 密钥。

请参考 acme.sh - DNS API 列表，找到您的服务商对应的环境变量名称。例如，对于 Cloudflare，您需要 CF_Token 和 CF_Account_ID。

2. 准备企业微信应用参数
本工具通过企业微信的应用消息发送通知。您需要在企业微信后台创建一个应用。

登录 企业微信管理后台。

进入「应用管理」 -> 「应用」 -> 「自建」，点击「创建应用」。

创建应用后，您会得到 AgentId 和 Secret。

在「我的企业」页面，您可以找到 企业ID (CorpID)。

touser 是接收消息的成员ID，@all 表示发送给应用可见范围内的所有人。

3. 编写 docker-compose.yml
version: '3.8'

services:
  cert-renewer:
    image: ispace/syno-cert-renewer:latest # 请替换为您自己的 Docker Hub 镜像或本地构建
    container_name: syno-cert-renewer
    restart: unless-stopped
    volumes:
      # 挂载输出目录，用于存放生成的证书文件
      - ./output:/output 
      # (必须) 挂载一个用于缓存企业微信 access_token 的临时目录
      - ./temp:/temp
      # (可选) 挂载配置文件目录
      - ./config:/config
    environment:
      # --- 基础配置 ---
      - DOMAIN=your.domain.com
      - DNS_API=dns_cf             # 您的 DNS 提供商 API (例如: dns_cf for Cloudflare)
      - ACME_EMAIL=youremail@example.com
      - API_KEY=your_dns_api_key   # 例如 Cloudflare 的 API Token
      - API_SECRET=your_dns_api_secret # 某些提供商需要，例如 Cloudflare 的 Account ID

      # --- (可选) 自动部署到 Synology DSM (密码等敏感信息建议写入 config.json) ---
      - AUTO_DEPLOY_TO_SYNOLOGY=true
      - SYNO_USERNAME=your_dsm_admin_user
      - SYNO_PASSWORD=your_dsm_admin_password
      - SYNO_PORT=5001
      - SYNO_PROTOCOL=https

      # --- (可选) 企业微信通知配置 ---
      - WECOM_CORP_ID=your_corp_id
      - WECOM_CORP_SECRET=your_corp_secret
      - WECOM_AGENT_ID=your_agent_id
      - WECOM_TOUSER=@all # 接收者, @all 表示所有
      
      # --- (可选) 定时任务配置 ---
      - CRON_SCHEDULE=0 3 * * * # 默认每天凌晨3点执行

    cap_add:
      - NET_ADMIN

4. 配置文件 config.json (可选)
您可以创建一个 config.json 文件来管理配置，这对于存放不便暴露在 docker-compose.yml 中的敏感信息（如密码）特别有用。环境变量的优先级高于 config.json。

config/config.json 示例:

{
  "general": {
    "domain": "your.domain.com",
    "dns_api": "dns_cf",
    "acme_email": "youremail@example.com"
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
      "corp_id": "your_corp_id",
      "corp_secret": "your_corp_secret",
      "agent_id": "your_agent_id",
      "touser": "@all"
    }
  }
}

⚠️ 安全警告
启用自动部署功能需要提供您的群晖管理员凭证。将密码等敏感信息以明文形式存储在环境变量或配置文件中都存在安全风险。请确保您的 Docker 主机和配置文件是安全的。强烈建议您为该工具专门创建一个权限受限的群晖管理员账户，并妥善保管您的 config.json 文件权限。

5. 启动容器
# 创建必要的本地目录
mkdir -p ./output ./temp ./config

# 如果使用 config.json，请先创建并编辑它
# nano ./config/config.json 

docker-compose up -d

容器首次启动时会立即执行一次证书申请流程。之后会根据 CRON_SCHEDULE 的设置定时执行。