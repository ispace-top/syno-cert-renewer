# 群晖泛域名证书自动续签工具 (Syno Cert Renewer)

✨ 一个采用现代化软件工程实践构建的，灵活、稳定、可扩展的群晖 NAS 泛域名 SSL 证书解决方案。

## 核心特性

-   **🚀 全自动**: 首次运行立即申请，之后通过定时任务自动检查并在证书过期前续签。
-   **🔌 企业级通知**: 通过**企业微信内部应用**发送通知，更安全、更专业。
-   **🔧 终极灵活配置**: 支持**环境变量**和**外部挂载配置文件**两种方式，**所有参数**均可在任一方式中配置，环境变量拥有更高优先级。
-   **🛡️ 泛域名支持**: 一次申请，`yourdomain.com` 和 `*.yourdomain.com` 全部搞定。
-   **📦 专业项目结构**: 所有 Python 源码统一归于 `src` 目录下，结构清晰。
-   **☁️ 主流 DNS 支持**: 内置支持**阿里云**和**腾讯云(DNSPod)**。
-   **🔒 兼容与可靠**: 基于 `acme.sh` 脚本，并优化了证书输出格式，完美兼容群晖 DSM。

---

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


---

## 如何使用

### 配置方式详解

本项目提供了两种配置方式，**环境变量的优先级总是高于配置文件**。这意味着如果一个配置项（如 `DOMAIN`）同时在环境变量和 `config.json` 中设置，程序将**使用环境变量的值**。

#### 方式一：通过挂载外部 `config.json` 文件 (推荐)

这是最清晰、最便于管理的配置方式。您只需维护一个 `config.json` 文件即可。

1.  **在您的群晖上创建一个 `config.json` 文件**。
    例如，在 `/volume1/docker/syno-cert-renewer/` 目录下创建 `config.json`。

2.  **文件内容示例 (完整版)**:
    ```json
    {
      "general": {
        "domain": "yourdomain.com",
        "dns_api": "dns_dp",
        "api_key": "YOUR_DP_ID",
        "api_secret": "YOUR_DP_TOKEN",
        "acme_email": "your-email@example.com",
        "renew_days": 30
      },
      "certificate": {
        "output_path": "/output",
        "key_filename": "privkey.pem",
        "cert_filename": "cert.pem",
        "ca_filename": "ca.pem"
      },
      "notifiers": {
        "wecom": {
          "corp_id": "YOUR_CORP_ID",
          "corp_secret": "YOUR_CORP_SECRET",
          "agent_id": "YOUR_AGENT_ID",
          "to_user": "@all"
        }
      }
    }
    ```

3.  **在启动容器时挂载文件**。
    在您的 `docker run` 命令中加入 `-v` 参数：
    ```bash
    docker run -d \
      --name syno-cert-renewer \
      -v /volume1/docker/syno-cert-renewer/config.json:/config/config.json \
      -v /volume1/docker/certs:/output \
      syno-cert-renewer:latest
    ```
    - `-v` 右边的 `/config/config.json` 是容器内固定路径，**请不要修改**。

#### 方式二：通过环境变量

如果您不想使用配置文件，或者只想覆盖一两个特定参数，可以使用环境变量。

| 变量名 | **描述** |
| :--- | :--- |
| **--- 核心配置 ---** |
| `DOMAIN` | 你的主域名。 |
| `DNS_API` | DNS 提供商: `dns_ali` 或 `dns_dp`。 |
| `API_KEY` | DNS API Key。 |
| `API_SECRET` | DNS API Secret。 |
| `ACME_EMAIL` | Let's Encrypt 注册邮箱。 |
| **--- 企业微信应用通知配置 ---** |
| `CORP_ID` | 企业ID。 |
| `CORP_SECRET`| 应用 Secret。 |
| `AGENT_ID` | 应用 AgentId。 |
| `TO_USER` | 消息接收者ID。 |
| **--- 其他可选配置 ---** |
| `CRON_SCHEDULE`| 定时任务的 Cron 表达式。**注意：此项只能通过环境变量配置。** 默认: `"0 3 * * *"`。 |
| `RENEW_DAYS` | 证书到期前续签的天数。默认: 30。 |
| `CERT_OUTPUT_PATH`| 证书输出路径。默认: `/output`。 |
| `KEY_FILENAME` | 私钥文件名。默认: `privkey.pem`。 |
| `CERT_FILENAME` | 服务器证书文件名。默认: `cert.pem`。 |
| `CA_FILENAME` | 中间证书文件名。默认: `ca.pem`。 |

---
### 如何配置企业微信应用通知

1.  **获取企业 ID (CORP_ID)**
    * 登录 [企业微信管理后台](https://work.weixin.qq.com/wework_admin/frame)。
    * 进入 **我的企业 -> 企业信息**。
    * 在页面底部可以找到 **企业ID**，复制它。

2.  **创建应用并获取凭证**
    * 进入 **应用管理 -> 应用 -> 创建应用**。
    * 上传一个应用logo，填写应用名称（例如“SSL证书助手”），选择可见范围。
    * 创建完成后，进入应用详情页。您可以在这里找到：
        * **AgentId**: 这就是 `AGENT_ID`。
        * **Secret**: 这就是 `CORP_SECRET`。

3.  **获取接收者 ID (TO_USER)**
    * 进入 **通讯录**。
    * 点击任意一个成员，在他/她的详情页，"账号"一栏就是该成员的 ID。
    * 您可以指定多个用户，用 `|` 分隔，例如 `"User1|User2"`。
    * 您也可以使用 `@all` 来向应用可见范围内的所有人发送。

---
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
