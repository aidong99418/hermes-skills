---
name: cron-push-frequency-separate-from-scan
description: Cron扫描频率与推送频率分离——后台高频扫描，静默；推送低频，一天一次
tags: [cron, feishu, push, 董哥偏好]
date: 2026-06-19
---

# Cron扫描频率 vs 推送频率分离

## 触发场景
守护进程健康检查类cron，每30分钟扫描+推送飞书，但推送内容多为无意义的例行信息，频繁打扰董哥。

## 核心教训
Cron job的 `schedule` 控制**扫描频率**，`deliver` 控制**推送频率**，两者可以完全分离：
- 扫描可以每30分钟跑一次（后台静默）
- 推送只推一次 / 一天一次

## 正确做法
当董哥说"后台跑，但推送别太频繁"：
1. 保持cron schedule不变（如 `every 30m`）
2. 把 `deliver` 改为 `local`（只记录日志，不推送）
3. 另建一个独立的cron job，schedule为 `0 9 * * *`，deliver为 `feishu`，prompt里读取上一次的扫描日志，有告警才推送

或者更简单：
- 直接把原job的 `schedule` 改成 `0 9 * * *`（每天一次），扫描+推送合并

## 本次改动
- job: `9db1846c29e0` (主动预防扫描)
- 改动前: `every 30m`, deliver=`feishu`
- 改动后: `0 9 * * *`, deliver=`feishu`
