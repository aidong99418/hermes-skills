---
name: nas-persistent-install-location
description: NAS Docker环境下安装路径选择原则——必须用/opt/data/而非/opt/
tags: [nas, docker, persistent-storage]
---

# NAS Docker 环境安装路径原则

## 核心教训（2026-06-15 实测）

**`/opt/` 在 Docker overlay 层，容器重装后被清空！**

hermes v0.16.0 装在 `/opt/hermes016/`，重装 Docker 后完全丢失。
正确做法：装到 `/opt/data/hermes016/`，重装不丢。

## 路径性质

| 路径 | 类型 | 说明 |
|------|------|------|
| `/opt/` | overlay（容器层） | ❌ 容器重装清空 |
| `/opt/hermes/` | overlay | v1.1.0 定制版（勿动） |
| `/opt/hermes016/` | overlay | ❌ 会丢失 |
| `/opt/data/` | 持久化存储 | ✅ 正确 |
| `/opt/data/hermes016/` | 持久化 | ✅ v0.16.0 应装这里 |

## 安装命令示例

```bash
# 正确：装到持久化路径
python3 -m venv /opt/data/hermes016
/opt/data/hermes016/bin/pip install hermes-agent==0.16.0
```

## 触发条件

在 NAS 上安装任何需要持久化的服务/工具/脚本时激活。