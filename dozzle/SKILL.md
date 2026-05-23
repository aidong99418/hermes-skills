---
name: dozzle
description: Dozzle — 实时Docker日志查看器，浏览器流式查看NAS所有容器日志，支持搜索，零配置。触发：查看容器日志、调试Docker问题。
version: 1.0.0
tags: [dozzle, docker, log, realtime, monitoring]
triggers: ["Dozzle", "容器日志", "实时日志", "Docker调试"]
---

# Dozzle 架构参考

## 核心定位
Dozzle = 实时Docker日志浏览器（24k⭐），一行命令部署，浏览器里流式看所有容器日志，支持搜索过滤。

## Docker一行部署

```bash
docker run -d \
  --name dozzle \
  --restart unless-stopped \
  -p 8080:8080 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  amir20/dozzle:latest

# 访问 http://NAS-IP:8080
```

## 核心功能

| 功能 | 说明 |
|------|------|
| 实时流式 | WebSocket推送，日志实时刷新 |
| 全容器列表 | 所有运行中容器一目了然 |
| 日志搜索 | 关键词过滤，高亮匹配 |
| 容器筛选 | 按名称过滤指定容器 |
| 终端模拟 | 浏览器里看日志格式 |
| 零配置 | 无需数据库，不占资源 |

## 常用参数

```bash
docker run -d \
  --name dozzle \
  -p 8080:8080 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e DOZZLE_NO_ANALYTICS=true \    # 禁用匿名统计
  amir20/dozzle:latest
```

## 与Portainer日志对比

| 工具 | 复杂度 | 实时流 | 全文搜索 | 资源占用 |
|------|--------|--------|---------|---------|
| Dozzle | ⭐ | ✅实时 | ✅ | 极低 |
| Portainer | ⭐⭐ | 轮询 | ❌ | 中等 |

Dozzle专注日志，Portainer管全局，选Dozzle看日志更爽。
