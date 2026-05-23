---
name: glances
description: Glances跨平台系统监控工具技能 — 终端实时查看NAS CPU/内存/磁盘/容器状态，一行命令部署，23k星星。比top/htop更全面。
triggers:
  - 查看系统资源
  - 监控CPU内存
  - NAS资源占用
  - 容器资源监控
  - 终端系统监控
---

# Glances 技能

## 是什么
跨平台系统监控工具，Python写的，一个命令显示CPU/内存/磁盘/网络/容器/进程等全部信息。

## 部署
```bash
# 直接运行（无需Docker）
pip install glances
glances

# Docker部署（Web界面）
docker run -d --name glances \
  -p 61208:61208 -v /var/run/docker.sock:/var/run/docker.sock:ro \
  --restart unless-stopped \
  nicolargo/glances:latest --web

# 访问Web界面
http://NAS_IP:61208
```

## 显示内容
- CPU使用率（每核心）
- 内存和交换分区
- 磁盘I/O和空间
- 网络流量
- 进程列表（可排序）
- Docker容器状态
- RAID/传感器温度

## 常用快捷键
| 键 | 功能 |
|----|------|
| m | 按内存排序 |
| c | 按CPU排序 |
| i | 按I/O排序 |
| d | 显示磁盘I/O |
| n | 显示网络 |
| t | 综合网络+进程 |

## 与NAS的契合点
Docker stats看不到的细节（温度、进程树、per-disk I/O），Glances都能看到。
