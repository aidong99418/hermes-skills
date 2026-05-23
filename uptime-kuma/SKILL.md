---
name: uptime-kuma
description: Uptime Kuma — 自托管监控工具，监控服务/容器/网站可用性，支持HTTP/TCP/PING/DNS/端口/关键词监控和告警通知。触发：NAS服务监控、API可用性告警。
version: 1.0.0
tags: [uptime-kuma, monitoring, uptime, status-page, self-hosted]
triggers: ["Uptime Kuma", "服务监控", "可用性告警", "状态页", "自托管监控"]
---

# Uptime Kuma 架构参考

## 核心定位
Uptime Kuma = 开源自托管监控（52k⭐），监控任意HTTP/TCP/端口/DNS，阈值告警，支持状态页展示。

## Docker部署

```bash
docker run -d \
  --name uptime-kuma \
  --restart unless-stopped \
  -p 3001:3001 \
  -v uptime-kuma-data:/app/data \
  -v /var/run/docker.sock:/var/run/docker.sock \
  louislam/uptime-kuma:1

# 访问 http://NAS-IP:3001
# 首次注册管理员账号
```

## 支持的监控类型

| 类型 | 说明 |
|------|------|
| HTTP(s) | 返回码/响应时间/关键词匹配 |
| TCP Port | 端口连通性 |
| Ping | ICMP可用性 |
| DNS | DNS解析/记录验证 |
| Steam | 游戏服务器 |
| Docker Container | 容器运行状态 |
| Push | 主动推送心跳 |

## 告警通知

```bash
# 支持的渠道
# 飞书 / Telegram / Slack / Discord / Email / Webhook / 钉钉 / 企业微信 等
```

## NAS场景最佳实践

```bash
# Docker Container监控（监控本机容器）
# 设置 --network=host 或 DOCKER_HOST 环境变量

# 监控局域网设备
# 新增监控 → HTTP(s) → 目标填 http://192.168.1.100:端口/path

# 公众状态页（给用户看）
# 状态页 → 创建公开状态页 → 填入品牌名称和域名
```

## 与Glances对比

| 维度 | Uptime Kuma | Glances |
|------|-------------|---------|
| 定位 | 被动监控+告警 | 主动查看实时状态 |
| 界面 | Web | 终端/Web |
| 告警 | ✅主动通知 | ❌仅视觉告警 |
| 历史记录 | ✅ | ❌ |

两者互补：Uptime Kuma后台监控告警，Glances随时查看详情。
