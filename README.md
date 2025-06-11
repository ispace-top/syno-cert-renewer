# 群晖泛域名证书自动续签工具 (Syno Cert Renewer)

✨ 一个采用现代化软件工程实践构建的，灵活、稳定、可扩展的群晖 NAS 泛域名 SSL 证书解决方案。

## 核心特性

-   **🚀 全自动**: 首次运行立即申请，之后通过定时任务自动检查并在证书过期前续签。
-   **🔌 模块化通知**: 采用面向接口的可扩展架构，当前内置**企业微信群机器人**通知，可轻松扩展至钉钉、飞书、邮件等。
-   **🔧 高度可配置**: 支持通过环境变量和配置文件进行双重配置，环境变量拥有更高优先级，便于在 Docker 环境中快速部署和覆盖。
-   **🛡️ 泛域名支持**: 一次申请，`yourdomain.com` 和 `*.yourdomain.com` 全部搞定。
-   **📦 专业项目结构**: 所有 Python 源码统一归于 `src` 目录下，结构清晰，便于维护和二次开发。
-   **☁️ 主流 DNS 支持**: 内置支持**阿里云**和**腾讯云(DNSPod)**的 DNS-API 验证方式。
-   **🔒 兼容与可靠**: 基于业界标准的 `acme.sh` 脚本，并特别优化了证书输出格式，完美兼容群晖 DSM 系统导入。

## 项目结构


syno-cert-renewer/
├── src/
│   ├── config/
│   │   └── config.json              # 默认配置文件
│   ├── notifiers/
│   │   ├── init.py              # 将 notifiers 声明为 Python 包
│   │   ├── base_notifier.py         # 通知服务的抽象基类 (接口)
│   │   ├── notification_manager.py  # 通知管理器，负责分发消息
│   │   └── wecom_notifier.py        # 企业微信通知的具体实现
│   └── main.py                      # 主控逻辑脚本
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
| `WECOM_WEBHOOK_URL`| `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=...` | (可选) **企业微信群机器人 Webhook 地址**。配置后将启用企业微信通知。 |
| | |
| **--- 可选配置 (行为与路径) ---** | |
| `CRON_SCHEDULE`| `"0 5 * * *"` | (可选) 自定义定时任务的 Cron 表达式。**默认值: `"0 3 * * *"` (每天凌晨3点)**。 |
| `RENEW_DAYS` | `30` | (可选) 设置证书在到期前多少天进行续签。**默认值: 30**。 |
| `CERT_OUTPUT_PATH`| `/output/live` | (可选) 证书输出路径。**默认值: `/output`**。 |
| `KEY_FILENAME` | `private.key` | (可选) 私钥文件名。**默认值: `privkey.pem`**。 |
| `FULLCHAIN_FILENAME`|`chain.pem`| (可选) 全链证书文件名。**默认值: `fullchain.pem`**。 |
| `CERT_FILENAME` | `cert.pem` | (可选) 服务器证书文件名。**默认值: `cert.pem`**。 |
| `CA_FILENAME` | `intermediate.pem`| (可选) 中间证书文件名。**默认值: `ca.pem`**。 |

### `config.json` 配置文件

项目内置一个默认的配置文件。**注意：环境变量的优先级总是高于配置文件。** 这意味着如果一个配置项同时在环境变量和 `config.json` 中设置，程序将使用环境变量的值。

### 如何配置企业微信通知

1.  在您的企业微信中，选择一个群聊。
2.  点击右上角的群设置 (···) -> **群机器人** -> **添加机器人**。
3.  给机器人起一个名字，例如“证书小助手”，然后点击**添加**。
4.  在下一个页面，您会看到一个 `Webhook` 地址。**复制**这个完整的地址。
5.  在启动 Docker 容器时，将这个地址作为 `WECOM_WEBHOOK_URL` 环境变量的值传入即可。

### 如何在群晖中导入证书

为了确保最佳兼容性，本项目现在会生成四个关键文件。在群晖 **控制面板 -> 安全性 -> 证书 -> 新增 -> 添加新证书 -> 导入证书** 时，请按以下方式对应：

1.  **私钥**: 选择您生成的 `privkey.pem` 文件。
2.  **证书**: 选择您生成的 `cert.pem` 文件。
3.  **中间证书**: **选择您生成的 `ca.pem` 文件。**

通过这种方式，可以确保群晖系统正确识别证书链，避免导入失败。

## 部署步骤

1.  **准备文件**: 确保您本地的项目文件结构与本文档描述的一致（`config` 和 `notifiers` 目录都在 `src` 内部）。
2.  **清理旧环境 (推荐)**:
    ```bash
    docker rm -f syno-cert-renewer
    docker rmi syno-cert-renewer:latest
    ```
3.  **重新构建镜像**: 在项目根目录下执行：
    ```bash
    docker build -t syno-cert-renewer:latest .
    ```
4.  **运行容器**: 使用 `docker run` 命令或通过群晖 Container Manager 界面，配置好您需要的环境变量后，启动容器。

## 如何扩展通知方式 (开发者)

得益于新的模块化设计，添加新的通知方式非常简单：

1.  在 `src/notifiers` 目录下，创建一个新的 `your_notifier.py` 文件。
2.  在该文件中，创建一个继承自 `BaseNotifier` 的新类（`from .base_notifier import BaseNotifier`）。
3.  实现 `send(self, status: str, domain: str, details: str = "")` 方法，编写您自己的通知逻辑。
4.  在 `src/notifiers/notification_manager.py` 的 `_discover_notifiers` 方法中，导入并实例化您的新类。
5.  重新构建 Docker 镜像即可！
