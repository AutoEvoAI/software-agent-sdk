

根据文档，**是的，OpenHands V1 的 runtime 依赖 software-agent-sdk 构建的 agent-server 镜像**。

## 如何构建新的 agent-server 镜像

根据 SDK 文档，有以下方式：

### 方式 1：DockerDevWorkspace 自动构建（推荐本地开发）

这是 SDK 官方提供的本地构建方式：

```python
from openhands.workspace import DockerDevWorkspace

with DockerDevWorkspace(
    base_image="nikolaik/python-nodejs:python3.12-nodejs22",
    host_port=8011,
    platform="linux/amd64",
    target="source",  # 从本地 SDK 源码构建
) as workspace:
    # 镜像已自动构建并启动
    result = workspace.execute_command("echo hello")
```

但这**只能在 SDK 编程方式下使用**，不能直接给 OpenHands GUI 用。

### 方式 2：手动 docker build（给 OpenHands GUI 用）

SDK 仓库中有 `openhands-agent-server/` 目录包含 Dockerfile。你可以手动构建：

```bash
cd software-agent-sdk

# 查看 Dockerfile 位置
ls openhands-agent-server/

# 手动构建镜像
docker build -t my-agent-server:dev \
    -f openhands-agent-server/Dockerfile .
```

然后在 OpenHands GUI 中使用：

```bash
docker run -it --rm --pull=always \
    -e AGENT_SERVER_IMAGE_REPOSITORY=my-agent-server \
    -e AGENT_SERVER_IMAGE_TAG=dev \
    -p 3000:3000 \
    docker.all-hands.dev/all-hands-ai/openhands:latest
```

### 方式 3：官方预构建镜像（不修改 SDK）

如果你没有修改 SDK，直接用官方镜像：

```bash
# OpenHands V1 默认使用
ghcr.io/openhands/agent-server:main-python
ghcr.io/openhands/agent-server:latest-python
```

### 总结流程

```
修改 software-agent-sdk 代码
        ↓
在 SDK 仓库中 docker build（openhands-agent-server/Dockerfile）
        ↓
生成新的 agent-server 镜像（如 my-agent-server:dev）
        ↓
配置 OpenHands GUI：
  AGENT_SERVER_IMAGE_REPOSITORY=my-agent-server
  AGENT_SERVER_IMAGE_TAG=dev
        ↓
启动 OpenHands GUI，使用你修改后的 runtime
```

**注意**：文档中没有提供独立的 `make build-image` 脚本，你需要查看 `openhands-agent-server/` 目录下的 Dockerfile 来确认具体的构建命令和参数。

```suggestions
(Docker Sandbox)[/sdk/guides/agent-server/docker-sandbox]
(Custom Tools with Remote Server)[/sdk/guides/agent-server/custom-tools]
(Configuration Options)[/openhands/usage/advanced/configuration-options]
```





根据文档，以下是 software-agent-sdk 项目的意义和独立原因：

## software-agent-sdk 的意义

根据 SDK 架构文档，software-agent-sdk 是 **OpenHands 的核心引擎层**，提供构建 software agents 的底层 API。

### 架构分层

```
┌─────────────────────────────────────────┐
│  OpenHands GUI / CLI / 自定义客户端      │  ← 消费者层
├─────────────────────────────────────────┤
│  Software Agent SDK                      │  ← 核心引擎
│  - Agent API (LLM, Tools, Conversation) │
│  - Workspace (Local/Docker/Remote)      │
│  - Agent Server (Runtime)               │
└─────────────────────────────────────────┘
```

### 为什么独立出来

根据文档描述的设计理念：

**1. 解耦核心与界面**
- SDK 是**引擎**，OpenHands GUI/CLI 是**消费者**
- GUI、CLI、自定义客户端都通过 SDK API 构建
- 分离后各自可以独立迭代

**2. 支持多种使用方式**
SDK 独立后，开发者可以：
- 用 **OpenHands GUI** 做交互式开发
- 用 **CLI** 做命令行自动化
- 用 **Python SDK** 编程式构建自定义 agent 应用
- 构建完全自定义的客户端

**3. 灵活的 Workspace 架构**
SDK 提供三种 workspace 类型：

| Workspace | 说明 |
|---|---|
| `LocalWorkspace` | 直接在本地执行，无隔离 |
| `DockerWorkspace` | 预构建镜像，隔离执行 |
| `DockerDevWorkspace` | 从源码构建，本地开发 |

**4. 可复用性**
独立 SDK 让第三方可以：
- 基于 SDK 构建自己的 agent 产品
- 自定义工具（custom tools）
- 集成到现有工作流中
- 不依赖 OpenHands GUI

### 简单类比

就像 **Chromium（引擎）** 和 **Chrome（浏览器）** 的关系：
- `software-agent-sdk` = 引擎（核心能力）
- `OpenHands` = 产品（GUI + 用户体验）

```suggestions
(SDK Architecture Overview)[/sdk/arch/overview]
(Workspace Architecture)[/sdk/arch/workspace]
(SDK Getting Started)[/sdk/getting-started]
```
