# OpenHands 构建指南

本文档介绍如何构建和发布 OpenHands 软件代理 SDK。

## 项目结构

本项目是一个使用 `uv` 管理的 Python monorepo，包含四个独立包：

| 包名 | 描述 | 当前版本 |
|------|------|----------|
| `openhands-sdk` | 核心 SDK，用于构建 AI 代理 | 1.11.5 |
| `openhands-tools` | 内置工具集 | 1.11.5 |
| `openhands-workspace` | 工作区实现 | 1.11.5 |
| `openhands-agent-server` | 服务器运行时 | 1.11.5 |

## 版本管理

### 版本升级

所有四个包使用**统一的版本号**。升级版本：

```bash
make set-package-version version=1.12.0
```

这会使用 `uv version --package` 同时更新所有四个包的 `pyproject.toml`：
- `openhands-sdk/pyproject.toml`
- `openhands-tools/pyproject.toml`
- `openhands-workspace/pyproject.toml`
- `openhands-agent-server/pyproject.toml`

### 发布流程

1. **升级版本**：
   ```bash
   make set-package-version version=1.12.0
   ```

2. **提交更改**：
   ```bash
   git add .
   git commit -m "Bump version to 1.12.0"
   git tag v1.12.0
   ```

3. **发布到 PyPI**（通过 GitHub Actions）：
   - 创建 GitHub Release（会自动触发 `pypi-release.yml`）
   - 或手动运行 `Publish all OpenHands packages (uv)` workflow

4. **自动依赖升级 PR**：
   - 发布成功后，`version-bump-prs.yml` 会自动为以下仓库创建版本升级 PR：
     - [OpenHands](https://github.com/All-Hands-AI/OpenHands)
     - [OpenHands-CLI](https://github.com/OpenHands/openhands-cli)

## 构建命令

### 1. 开发环境设置

```bash
make build
```

这将：
- 检查 uv 版本
- 使用 `uv sync --dev` 安装所有依赖
- 安装 pre-commit hooks

### 2. 构建 Python 包（wheel/sdist）

使用 `uv build` 构建各个包：

```bash
# 构建所有包
uv build --package openhands-sdk
uv build --package openhands-tools
uv build --package openhands-workspace
uv build --package openhands-agent-server

# 或使用循环
for pkg in openhands-sdk openhands-tools openhands-workspace openhands-agent-server; do
    uv build --package "$pkg"
done
```

构建产物位于各包的 `dist/` 目录下：
- `openhands-sdk/dist/`
- `openhands-tools/dist/`
- `openhands-workspace/dist/`
- `openhands-agent-server/dist/`

### 3. 构建 agent-server 可执行文件

```bash
make build-server
```

这将使用 PyInstaller 构建 agent-server 可执行文件，输出到 `dist/agent-server/`。

**注意**：这与 Docker 镜像构建不同。如果需要构建 Docker 镜像，请参考下一节。

### 4. 发布到 PyPI

```bash
# 设置版本
make set-package-version version=1.2.3

# 构建并发布
uv build --package openhands-sdk
uv build --package openhands-tools
uv build --package openhands-workspace
uv build --package openhands-agent-server
uv publish --token <your-pypi-token>
```

## Makefile 命令汇总

| 命令 | 描述 |
|------|------|
| `make build` | 设置开发环境（安装依赖 + hooks） |
| `make build-server` | 构建 agent-server 可执行文件 |
| `make format` | 格式化代码 |
| `make lint` | 代码检查 |
| `make clean` | 清理缓存文件 |
| `make set-package-version version=x.x.x` | 设置包版本 |

## 依赖管理

项目使用 `uv` 作为包管理工具。根目录 `pyproject.toml` 定义了工作区配置：

```toml
[tool.uv.workspace]
members = [
    "openhands-sdk",
    "openhands-tools",
    "openhands-workspace",
    "openhands-agent-server"
]
```

各包之间的依赖通过 `tool.uv.sources` 在工作区内解析。

## Docker 镜像构建

### 背景说明

`software-agent-sdk` 构建的 Docker 镜像用于 OpenHands 的 Sandbox 组件。当在 OpenHands 前端选择 SPEC_DRIVEN（规范驱动）模式时，Sandbox 中的 agent server 需要能够识别和反序列化 `SupervisorAgent`。

**重要**：每次修改 `openhands-sdk` 或 `openhands-agent-server` 的代码后，都需要重新构建 Docker 镜像，否则 Sandbox 中的 agent server 将无法使用新代码。

### 构建目标

项目支持四种构建目标：

| 目标 | 描述 | 适用场景 |
|------|------|----------|
| `binary` | 完整的二进制镜像（包含 PyInstaller 构建的可执行文件） | 生产环境 |
| `binary-minimal` | 最小化二进制镜像 | 生产环境（资源受限） |
| `source` | 源码模式镜像 | 开发/调试 |
| `source-minimal` | 最小化源码镜像 | 开发/调试 |

### 构建命令

#### 方式一：使用 Python 脚本（推荐）

```bash
# 进入 SDK 目录
cd software-agent-sdk/

# 构建二进制镜像（本地加载）
python -m openhands.agent_server.docker.build \
    --target binary \
    --image your-registry/openhands-agent-server:custom \
    --platforms linux/amd64 \
    --load

# 或推送到远程仓库
python -m openhands.agent_server.docker.build \
    --target binary \
    --image your-registry/openhands-agent-server:custom \
    --platforms linux/amd64 \
    --push
```

#### 方式二：使用环境变量

```bash
# 设置环境变量
export IMAGE="your-registry/openhands-agent-server:custom"
export TARGET="binary"
export PLATFORMS="linux/amd64"
export LOAD=1  # 本地加载

# 运行构建
python -m openhands.agent_server.docker.build
```

### 构建参数说明

| 参数 | 环境变量 | 说明 | 默认值 |
|------|----------|------|--------|
| `--target` | `TARGET` | 构建目标 | `binary` |
| `--image` | `IMAGE` | 镜像名称/标签 | 必需 |
| `--platforms` | `PLATFORMS` | 目标平台 | `linux/amd64,linux/arm64` |
| `--arch` | `ARCH` | 架构后缀 | 空 |
| `--push` | `PUSH=1` | 推送到远程 | 本地加载 |
| `--load` | `LOAD=1` | 本地加载 | 否 |
| `--build-ctx-only` | - | 仅创建构建上下文 | 否 |
| `--versioned-tag` | - | 包含版本标签 | 否 |

### 使用新镜像

#### 1. 本地测试

构建完成后，镜像会被加载到本地 Docker：

```bash
# 查看镜像
docker images | grep openhands-agent-server

# 测试运行
docker run -p 8000:8000 your-registry/openhands-agent-server:custom
```

#### 2. 在 OpenHands 中使用

需要在 OpenHands 配置中指定新镜像。修改 sandbox 配置或环境变量：

```bash
# 通过环境变量指定（取决于部署方式）
export AGENT_SERVER_IMAGE="your-registry/openhands-agent-server:custom"
```

#### 3. 推送到镜像仓库

```bash
# 推送到 Docker Hub
docker push your-registry/openhands-agent-server:custom

# 或推送到私有仓库
docker push your-private-registry/openhands-agent-server:custom
```

### 故障排查

#### 问题：Sandbox 返回 422 错误

**症状**：选择 SPEC_DRIVEN 模式时出现 "422 Unprocessable Entity" 错误。

**原因**：Sandbox 中的 agent server 镜像没有包含最新的 SupervisorAgent 代码。

**解决方案**：
1. 确保已按照上述步骤重新构建镜像
2. 确保 Sandbox 使用的是新构建的镜像（而非旧镜像）
3. 验证本地代码已正确修改：
   ```bash
   # 检查 SupervisorAgent 是否存在
   python -c "from openhands.sdk.agent.supervisor import SupervisorAgent; print('OK')"
   ```

#### 问题：镜像构建失败

**检查项**：
1. Docker 是否已安装并运行
2. 是否有足够的磁盘空间
3. 网络是否正常（需要拉取基础镜像）

### 自动化构建（CI/CD）

在 GitHub Actions 中构建：

```yaml
- name: Build agent-server image
  run: |
    python -m openhands.agent_server.docker.build \
      --target binary \
      --image ghcr.io/${{ github.repository }}/agent-server:${{ github.sha }} \
      --platforms linux/amd64 \
      --push
  env:
    PUSH: 1
```
