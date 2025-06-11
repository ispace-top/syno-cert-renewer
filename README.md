# 群晖泛域名证书自动续签工具 (Syno Cert Renewer)

✨ 一个采用现代化软件工程实践构建的，灵活、稳定、可扩展的群晖 NAS 泛域名 SSL 证书解决方案。

## 核心特性

-   **🚀 全自动**: 首次运行立即申请，之后通过定时任务自动检查并在证书过期前续签。
-   **🔌 模块化通知**: 采用面向接口的可扩展架构，当前内置**企业微信群机器人**通知，可轻松扩展至钉钉、邮件等。
-   **🔧 高度可配置**: 支持通过环境变量和配置文件进行双重配置，环境变量拥有更高优先级，便于在 Docker 环境中快速部署和覆盖。
-   **🛡️ 泛域名支持**: 一次申请，`yourdomain.com` 和 `*.yourdomain.com` 全部搞定。
-   **📦 专业项目结构**: 所有 Python 源码统一归于 `src` 目录下，结构清晰，便于维护和二次开发。
-   **☁️ 主流 DNS 支持**: 内置支持**阿里云**和**腾讯云(DNSPod)**的 DNS-API 验证方式。
-   **🔒 兼容与可靠**: 基于业界标准的 `acme.sh` 脚本，并特别优化了证书输出格式，完美兼容群晖 DSM 系统导入。

## 项目结构


syno-cert-renewer/
└── src/
├── config/
│   └── config.json              # 默认配置文件
├── notifiers/
│   ├── init.py              # 将 notifiers 声明为 Python 包
│   ├── base_notifier.py         # 通知服务的抽象基类 (接口)
│   ├── notification_manager.py  # 通知管理器，负责分发消息
│   └── wecom_notifier.py        # 企业微信通知的具体实现
└── main.py                      # 主控逻辑脚本
├── Dockerfile                       # 用于构建镜像的说明文件
├── entrypoint.sh                    # Docker 容器的入口脚本
└── README.md                        # 本说明文档


## 如何使用

### 环境变量详解

这是配置此项目最核心的方式。在启动 Docker 容器时，请设置以下环境变量。

| 变量名 | 示例值 | **描述** |
| :--- | :--- | :--- |
| **--- 必填配置 ---** | |
| `DOMAIN` | `yourdomain.com` | 你的主域名。 |
| `DNS_API` | `dns_ali` | DNS 提供商。`dns_ali` (阿里云) 或 `dns_dp` (腾讯云 DNSPod)。 |
| `API_KEY` | `LTxxxxxxxx` | 你的 DNS API Key。 |
| `API_SECRET` | `GZyyyyyyyy` | 你的 DNS API Secret。 |
| `ACME_EMAIL` | `user@example.com` | 用于 Let's Encrypt 账户注册和过期通知的邮箱。 |
| | |
| **--- 可选配置 (通知) ---** | |
| `WECOM_WEBHOOK_URL`| `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=...` | (可选) **企业微信群机器人 Webhook 地址**。优先级高于配置文件。 |
| | |
| **--- 可选配置 (行为与路径) ---** | |
| `CRON_SCHEDULE`| `"0 5 * * *"` | (可选) 自定义定时任务的 Cron 表达式。**默认值: `"0 3 * * *"` (每天凌晨3点)**。 |
| `RENEW_DAYS` | `30` | (可选) 设置证书在到期前多少天进行续签。**默认值: 30**。 |
| `CERT_OUTPUT_PATH`| `/output/live` | (可选) 证书输出路径。**默认值: `/output`**。 |
| `KEY_FILENAME` | `private.key` | (可选) 私钥文件名。**默认值: `privkey.pem`**。 |
| `CERT_FILENAME` | `cert.pem` | (可选) 服务器证书文件名。**默认值: `cert.pem`**。 |
| `CA_FILENAME` | `intermediate.pem`| (可选) 中间证书文件名。**默认值: `ca.pem`**。 |

### `config.json` 配置文件
您也可以通过挂载并修改 `/app/src/config/config.json` 文件来进行配置。**注意：环境变量的优先级总是高于配置文件。**

### 如何在群晖中导入证书
为了确保最佳兼容性，本项目现在会生成三个对群晖有用的文件：
-   `privkey.pem` (私钥)
-   `cert.pem` (证书)
-   `ca.pem` (中间证书)

在群晖 **控制面板 -> 安全性 -> 证书 -> 新增 -> 添加新证书 -> 导入证书** 时，请按以下方式对应：
1.  **私钥**: 选择您生成的 `privkey.pem` 文件。
2.  **证书**: 选择您生成的 `cert.pem` 文件。
3.  **中间证书**: **选择您生成的 `ca.pem` 文件。**

通过这种方式，可以确保群晖系统正确识别证书链，避免导入失败。
