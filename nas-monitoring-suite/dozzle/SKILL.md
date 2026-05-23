---
name: dozzle
description: Dozzle实时Docker日志查看器技能 — 浏览器实时流式查看NAS上所有容器日志，支持搜索、轻量级、零配置。14k星星。
triggers:
  - 查看Docker日志
  - 容器日志聚合
  - 实时日志监控
  - 查看容器报错
  - Docker调试
---

# Dozzle 技能

## 是什么
浏览器实时查看Docker所有容器日志的工具，支持搜索、流式推送、轻量级。

## 一键部署
```bash
docker run --name dozzle \
  -d --restart unless-stopped \
  -p 9999:8080 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  amir20/dozzle:latest
```

访问：`http://NAS_IP:9999`

## 核心优势
- **零配置**：自动发现所有容器
- **实时流**：WebSocket推送日志，无需刷新
- **搜索过滤**：支持关键词过滤
- **极轻量**：~50MB内存
- **多容器对比**：同时看多个容器日志

## 与Hermes对比
- Hermes负责分析和决策
- Dozzle负责实时查看和调试
- 两者互补，Hermes查到异常→去Dozzle看具体日志

## 坑
- 默认无认证，建议内网使用或加Nginx Basic Auth
- 日志保留由Docker daemon控制，Dozzle不持久化

## 星数
14k+ ⭐ | amir20/dozzle
