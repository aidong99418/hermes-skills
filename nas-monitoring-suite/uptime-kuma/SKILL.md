---
name: uptime-kuma
description: Uptime Kuma自托管监控工具技能 — 部署到NAS监控服务/容器/网站可用性，支持HTTP/TCP/Ping/DNS检测，漂亮Dashboard，告警推送。37k星星，最佳NAS监控方案。
triggers:
  - 监控服务可用性
  - NAS健康检查
  - 网站监控告警
  - 容器存活检测
  - 定时健康检查
  - 服务器监控
---

# Uptime Kuma 技能

## 是什么
自托管网站/服务监控工具，类似UptimeRobot，支持HTTP(s)/TCP/Ping/DNS检测，有漂亮Dashboard和告警。

## 在NAS上部署
```bash
# Docker一键部署
docker run -d \
  --name uptime-kuma \
  -p 3001:3001 \
  -v uptime-kuma-data:/app/data \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --restart unless-stopped \
  louislam/uptime-kuma:latest
```

访问：`http://NAS_IP:3001`（首次需注册管理员账号）

## 核心功能

### 监控类型
| 类型 | 用法 |
|------|------|
| HTTP(s) | 监控网站，支持检查关键词是否出现 |
| TCP | 监控端口（数据库Redis/MySQL等） |
| Ping | 监控服务器存活 |
| DNS | 监控域名解析 |
| Docker | 监控容器是否在运行 |

### 告警渠道
- Gotify（自建推送）✅
- Telegram Bot ✅
- 邮件 ✅
- Webhook ✅
- Slack/Discord ✅

### 监控Ollama示例
```
名称: Ollama服务
类型: HTTP(s)
URL: http://localhost:11434/api/tags
间隔: 1分钟
超时: 10秒
预期关键词: "models"
```

## 与Hermes集成
配合`machine-cat-guardian` skill，在监控告警时触发Hermes通知微信。

## 坑
- 首次部署建议绑定域名+反向代理启用HTTPS
- Docker socket挂载让Kuma能检测其他容器

## 星数
37k+ ⭐ | louislam/uptime-kuma
