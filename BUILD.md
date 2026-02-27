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
