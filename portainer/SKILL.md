---
name: portainer
description: Portainer — 轻量级Docker管理工具，Web界面管理NAS所有容器/镜像/网络/卷。触发：管理NAS Docker、容器可视化操作。
version: 1.0.0
tags: [docker, portainer, container, web-ui, nas]
triggers: ["Portainer", "Docker管理", "容器可视化", "NAS容器"]
---

# Portainer 架构参考

## 核心定位
Portainer = Docker 轻量级 Web 管理界面（28k⭐），替代命令行操作，浏览器里管理容器/镜像/网络/卷。

## Docker一键部署

```bash
# 已有Docker环境的话
docker run -d \
  --name portainer \
  --restart unless-stopped \
  -p 9000:9000 \
  -p 8000:8000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:2.21

# 访问 http://NAS-IP:9000
# 首次设置管理员账号
```

## 核心功能

| 功能 | 说明 |
|------|------|
| 容器管理 | 启停删改、日志查看、终端 |
| 镜像管理 | 拉取、构建、删除 |
| 网络管理 | 创建/查看Docker网络 |
| 卷管理 | 数据卷持久化 |
| Stack管理 | docker-compose批量部署 |
| 用户权限 | 多用户+权限控制 |

## NAS场景最佳实践

```bash
# 推荐挂载Docker Socket（只读更安全）
-v /var/run/docker.sock:/var/run/docker.sock:ro

# 多主机管理用Agent模式
docker run -d -p 9001:9001 \
  --name portainer-agent \
  --restart unless-stopped \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /var/lib/docker/volumes:/var/lib/docker/volumes \
  portainer/agent:2.21
```

## 坑/注意事项

1. **Socket权限**：绑定`/var/run/docker.sock`即拥有root权限，生产环境做好网络隔离
2. **数据持久化**：`portainer_data`卷不丢数据
3. **端口冲突**：9000被占用换其他端口
4. **更新**：先拉新镜像再重启容器
5. **ARM设备**：用`linux/arm64`镜像
