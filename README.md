群晖泛域名证书自动续签工具 (Syno Cert Renewer)
✨ 一个采用现代化软件工程实践构建的，灵活、稳定、可扩展的群晖 NAS 泛域名 SSL 证书解决方案。

核心特性
🚀 全自动: 首次运行立即申请，之后通过定时任务自动检查并在证书过期前续签。

🔌 企业级通知: 通过企业微信内部应用发送通知，更安全、更专业，可直接触达指定成员。

🔧 高度可配置: 支持通过环境变量和配置文件进行双重配置，环境变量拥有更高优先级。

🛡️ 泛域名支持: 一次申请，yourdomain.com 和 *.yourdomain.com 全部搞定。

📦 专业项目结构: 所有 Python 源码统一归于 src 目录下，结构清晰，便于维护。

☁️ 主流 DNS 支持: 内置支持阿里云和**腾讯云(DNSPod)**的 DNS-API 验证方式。

🔒 兼容与可靠: 基于业界标准的 acme.sh 脚本，并优化了证书输出格式，完美兼容群晖 DSM 系统导入。

如何配置企业微信应用通知
从简单的 Webhook 升级到应用通知，需要您在企业微信后台进行一些配置。

获取企业 ID (CORP_ID)

登录 企业微信管理后台。

进入 我的企业 -> 企业信息。

在页面底部可以找到 企业ID，复制它。

创建应用并获取凭证

进入 应用管理 -> 应用 -> 创建应用。

上传一个应用logo，填写应用名称（例如“SSL证书助手”），选择可见范围（哪些部门或员工可以看到此应用）。

创建完成后，进入应用详情页。您可以在这里找到：

AgentId: 这就是 AGENT_ID。

Secret: 这就是 CORP_SECRET。请妥善保管。

获取接收者 ID (TO_USER)

进入 通讯录。

点击任意一个成员，在他/她的详情页，"账号"一栏就是该成员的 ID（比如 Kerwin）。

您可以指定多个用户，用 | 分隔，例如 "User1|User2"。

您也可以使用 @all 来向应用可见范围内的所有人发送。

环境变量详解
变量名

示例值

描述

--- 必填配置 ---





DOMAIN

yourdomain.com

你的主域名。

DNS_API

dns_ali

DNS 提供商。dns_ali 或 dns_dp。

API_KEY

LTxxxxxxxx

DNS API Key。

API_SECRET

GZyyyyyyyy

DNS API Secret。

ACME_EMAIL

user@example.com

Let's Encrypt 注册邮箱。







--- 企业微信应用通知配置 ---





CORP_ID

wwxxxxxxxxxxxxxx

(可选) 企业ID。启用应用通知的必填项之一。

CORP_SECRET

xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

(可选) 应用 Secret。启用应用通知的必填项之一。

AGENT_ID

1000001

(可选) 应用 AgentId。启用应用通知的必填项之一。

TO_USER

Kerwin 或 @all

(可选) 消息接收者ID。默认为 @all。







--- 其他可选配置 ---





CRON_SCHEDULE

"0 5 * * *"

(可选) 定时任务的 Cron 表达式。默认: "0 3 * * *"。

RENEW_DAYS

30

(可选) 证书到期前续签的天数。默认: 30。

注意: THUMB_ID 和 AUTHOR 这两个参数，在当前使用的 textcard 消息类型中不受支持，应用本身的名称和图标将作为发送者标识，因此已从实现中移除，以保持简洁。

部署与使用
部署步骤与之前相同，只需在启动 Docker 容器时，配置好上述新的环境变量即可。

更新项目文件。

清理旧环境 (docker rm ... 和 docker rmi ...)。

重新构建镜像 (docker build -t syno-cert-renewer:latest .)。

使用新的环境变量运行容器。