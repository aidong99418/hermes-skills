# Cron任务静默模式设计

> 来源：hermes-addons best-practices | 存入：2026-05-26

## 核心原则

用户不需要知道系统正常运行，只有出问题时才打扰。

## 三种交付模式

| 模式 | deliver参数 | 行为 |
|------|------------|------|
| 静默 | `local` | 只写本地文件，不推送 |
| 通知 | `origin` 或 `weixin` | 推送到微信 |
| 自用 | 无（cron内部使用） | 不交付 |

## 静默模式的好处

- 不打扰用户屏幕/微信
- 日志供后续排查
- 紧急问题时可回溯

## 已静默化的任务

所有cron任务已改为`deliver=local`：
- dialog_watchdog（每分钟监控）
- brain_backup_trigger（整点触发）
- auto_learning（每日学习）
- web_scraper（每日抓取）
- ollama_model_manager（保活）
- 等其他cron任务

## 紧急情况才通知

以下情况才切换回weixin通知：
1. 连续3次cron执行失败
2. 系统磁盘接近满
3. Ollama服务彻底宕机
4. 备份推送失败

## 实现方式

```python
# cron任务执行结果
result = {
    "status": "success",  # 或 "failed"
    "message": "...",
    "files_changed": ["..."]
}
# 只在failed时推weixin
```

## 静默监控场景

适合静默的cron：
- 日志分析/归档
- 缓存清理
- 健康检查（频繁）
- 自动学习/抓取
- 备份（频繁）
- 模型warmup

不适合静默的cron：
- 提醒类任务（用户主动设的）
- 故障告警（需要立即处理）
