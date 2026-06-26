---
name: v016-auto-restart-fix
description: V016 Gateway自动重启问题的根因诊断与修复
triggers:
  - V016自动重启
  - V16一直重启
  - gateway不断重启
  - hermes-v016 restart loop
---

# V016 自动重启修复

## 症状
V016 Gateway 不断收到 SIGTERM 然后被 Systemd/Docker 自动拉起，日志显示：
```
Received SIGTERM — initiating shutdown
Exiting with code 1 (signal-initiated shutdown without restart request)
so systemd Restart=on-failure can revive the gateway.
```

## 根因
`docker-compose.yaml` 里配置了 `restart: unless-stopped`，NAS Docker 守护策略会自动拉起容器。

## 修复

找到 docker-compose.yaml：
```bash
find /volume1/docker -name "docker-compose*.yml"
```

把 `restart: unless-stopped` 改成 `restart: "no"`（gateway 和 dashboard 两个服务都要改）

然后让容器彻底停下：
```bash
cd /volume1/docker/hermes-文件路径/hermes016 && docker compose down
```

## 关键文件
- `/volume1/docker/hermes-文件路径/hermes016/docker-compose.yaml`

## 验证
- `docker ps` 确认没有 hermes-v016 容器在跑
- 日志不再有新条目

## 注意
- 停容器后不会自动拉起
- 需要手动 `docker compose up -d` 启动
