---
name: cron-api-channel-contention-diagnosis
description: Cron定时任务抢云端API通道导致用户消息响应变慢的诊断与修复
triggers:
  - 飞书/微信响应时间突然变慢（>100秒平均）
  - 用户反馈"卡了"但日志无明显报错
  - 排查模型能力/网络/队列后无果
version: 1.0
---

# Cron任务与API通道争用诊断

## 核心发现（2026-06-03）
**Cron的8个定时任务全在抢wisemodel云端API通道**，导致用户消息被挤到队列后面。关闭cron后响应时间从平均200秒→9.4秒，快了20倍。

## 诊断流程

### 第一步：隔离实验（最快路径）
```bash
service cron stop
# 观察5分钟内新消息响应时间是否改善
# 如果改善>50%，指向API通道争用
```

### 第二步：数据验证
```bash
# 对比cron开/关时的响应时间分布
grep "response ready.*feishu" /opt/data/logs/agent.log | \
  awk -F'time=' '{gsub(/[^0-9.].*/,"",$2); t+=$2; c++} END{print "平均: " t/c "秒, 总: " c}'
```

### 第三步：确认争用源
```bash
# 查看当前cron任务频率
crontab -l | grep -v "^#"

# 看cron任务有没有在调云端API
grep -r "wisemodel\|minimax\|openai" \
  /opt/data/cron/ /opt/data/scripts/ 2>/dev/null | head -10
```

## 关键教训
- **日志推理的陷阱**：只分析日志说"本地模型没参与"→证据不足就下结论
- **董哥朴素实验法**："关掉看看"→9.4秒→铁证。经验观察 + 隔离实验 > 日志推理
- 对比：cron开时平均200秒，cron关后9.4秒，差20倍

## 根本解决方案

### 方案A：限速（推荐）
给cron任务加API并发限制，限制同时只有2-3个任务调用API

### 方案B：错峰
错开cron执行时间（避免整点同时触发）

### 方案C：独立通道
cron任务走独立API账号，与用户消息分离；或降级到本地Ollama模型

### 方案D：临时观察
先关cron几天，确认是根因后再设计限速方案

## 验证
cron关后5分钟内，新飞书消息响应时间应该普遍<60秒。
