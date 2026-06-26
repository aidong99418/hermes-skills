---
name: nas-clock-drift-16h
description: NAS时钟偏差16小时问题诊断与修复，2026-06-10凌晨发现
tags: [nas, cron, clock, bug]
---

# NAS时钟偏差16小时 - 问题诊断与修复

**发现时间：** 2026-06-10 凌晨  
**严重性：** 高（影响Cron调度）

## 症状

- `date` 显示 CST: `Wed Jun 10 04:18:12 CST 2026`（凌晨4点）
- UTC时间: `Wed Jun 10 20:18:12 UTC 2026`（晚上8点）
- **差值：16小时**（CST比UTC慢16小时）
- Hermes scheduler cron任务全部失效：
  - 04:05任务 → 系统认为"已过"
  - 20:10任务 → 系统认为"13小时后"

## 根因

NAS硬件时钟或NTP同步损坏，CST时区偏移错误。

## 修复方案

### 方案1：修复NAS系统时钟（推荐）
```bash
# 手动同步NTP
sudo ntpdate pool.ntp.org

# 或设置硬件时钟
sudo hwclock --systohc --utc
sudo timedatectl set-timezone Asia/Shanghai
```

### 方案2：绕过Cron，用@hourly
在 jobs.json 中避免精确分钟，改用 `"cron": "@hourly"` 或 `"cron": "0 * * * *"`（每整点）降低时间精度依赖。

### 方案3：事件驱动替代Cron（最稳）
监控类任务 → watchdog文件监控替代定时轮询  
健康类任务 → daemon常驻+阈值触发  
只有真正需要精确时间点才用cron

## 影响范围

- `hermes_cron` jobs.json 所有任务可能调度异常
- 依赖系统时间的功能（派工板超时清理、result_board TTL等）可能失效
- 大蓝图P0自动化任务排了cron但未触发，需修复后手动验证

## 验证命令

```bash
# 查时钟
date
hwclock -r

# 查hermes cron任务状态
cat /opt/data/cron/jobs.json | python3 -c "import json,sys; [print(j['name'],j.get('last_run_at')) for j in json.load(sys.stdin)['jobs']]"
```

## 状态

- 发现：2026-06-10 04:18
- 等待：董哥睡醒后手动修复NAS时钟，再验证大蓝图P0任务
