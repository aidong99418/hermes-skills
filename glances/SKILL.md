---
name: glances
description: Glances — 跨平台系统监控工具，终端实时查看CPU/内存/磁盘/网络/进程，支持Web模式。触发：NAS资源监控、系统状态查看。
version: 1.0.0
tags: [glances, monitoring, system, cpu, memory, disk, network]
triggers: ["Glances", "系统监控", "资源查看", "NAS监控"]
---

# Glances 架构参考

## 核心定位
Glances = 跨平台系统监控（23k⭐），终端里实时看CPU/内存/磁盘/网络/进程，一行命令，支持Web模式远程看。

## Docker一行部署

```bash
docker run -d \
  --name glances \
  --restart unless-stopped \
  -p 61208:61208 \
  -v /proc:/host/proc:ro \
  -v /sys:/host/sys:ro \
  -v /etc:/host/etc:ro \
  nicolargo/glances:latest-full

# 终端模式（进容器）
docker exec -it glances glances

# Web模式访问 http://NAS-IP:61208
```

## 核心功能

| 监控项 | 说明 |
|--------|------|
| CPU | 使用率、各核心、温度（需lm-sensors） |
| 内存 | 总量/使用/可用 |
| 磁盘I/O | 读写速度 |
| 磁盘空间 | 各分区使用率 |
| 网络 | 上下行速度 |
| 进程 | CPU/内存排序，TOP N |
| 警报 | 阈值超限高亮告警 |
| Docker | 容器状态一览 |

## Web模式（NAS推荐）

```bash
docker run -d \
  --name glances \
  -p 61208:61208 \
  -v /proc:/host/proc:ro \
  -v /sys:/host/sys:ro \
  -v /etc:/host/etc:ro \
  nicolargo/glances:latest-full \
  glances --webserver --bind 0.0.0.0
```

## 与其他监控对比

| 工具 | 界面 | 实时 | Docker | 告警 |
|------|------|------|--------|------|
| Glances | 终端/Web | ✅ | ✅ | ✅阈值 |
| htop | 终端 | ✅ | ❌ | ❌ |
| top | 终端 | ✅ | ❌ | ❌ |
| UptimeKuma | Web | ✅ | 被动 | ✅主动 |

Glances适合主动盯盘，UptimeKuma适合后台告警。
