---
name: portainer
description: Portainer轻量级Docker管理工具技能 — Web界面管理NAS所有容器/镜像/网络/卷，替代命令行docker ps/rm等操作，35k星星。
triggers:
  - 管理Docker容器
  - Web界面管理NAS
  - 容器镜像管理
  - Docker网络配置
---

# Portainer 技能

## 是什么
轻量级Docker Web管理界面，NAS必备工具。

## 一键部署
```bash
docker run -d \
  --name portainer \
  -p 9000:9000 \
  -p 8000:8000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer-data:/data \
  --restart unless-stopped \
  portainer/portainer-ce:latest
```

访问：`http://NAS_IP:9000`，首次设置管理员账号

## 核心功能
- **容器管理**：启停删改、查看日志、进入终端
- **镜像管理**：拉取、删除、构建
- **网络管理**：创建bridge/overlay网络
- **卷管理**：持久化数据管理
- **模板市场**：一键部署常用应用（WordPress/MySQL等）
- **用户权限**：多用户+权限控制

## 与Hermes的配合
- Hermes负责思考和决策（告诉你要做什么）
- Portainer负责可视化执行（点击按钮完成）
- 场景：Hermes分析发现某个容器异常→在Portainer里快速重启

## 坑
- Agent模式（远程管理多台机器）需要额外部署Agent容器
- 大规模部署建议用Portainer Business
