---
name: cron-quality-audit-workflow
description: Cron质量告警诊断与死任务清理工作流。触发：cron质量追踪均分<85或收到含⚠️的质量报告。步骤：读报告→交叉映射→三分法→算收益→验证后处置。
triggers: ["调度", "cron", "定时"]
---

# Cron质量告警诊断与死任务清理工作流

触发：cron质量追踪均分<85、或收到Cron Job质量报告含⚠️告警时激活。

## 核心文件

| 文件 | 用途 |
|------|------|
| `/opt/data/brain/neural/cron_quality_report.json` | 质量报告原始数据（分数/成功率/失败次数/趋势） |
| `/opt/data/brain/neural/cron_quality_trend.jsonl` | 历史趋势（趋势线） |
| `/opt/data/cron/jobs.json` | job ID→name的映射表 |
| `/opt/data/cron/output/<job_id>/` | 每个job的cron输出目录 |

## 诊断步骤

### 第1步：读质量报告（一眼定生死）

```python
import json
with open('/opt/data/brain/neural/cron_quality_report.json') as f:
    data = json.load(f)
jobs = data['jobs']
warning_jobs = [j for j in jobs if j['score'] < 80]
healthy_jobs = [j for j in jobs if j['score'] >= 80]
print(f"⚠️ {len(warning_jobs)}个告警 | ✅ {len(healthy_jobs)}个健康 | 均分{data['avg_score']}")
```

### 第2步：job ID交叉映射（知道谁是谁）

```python
with open('/opt/data/cron/jobs.json') as f:
    job_map = {j['id']: {'name': j.get('name',''), 'schedule': j.get('schedule',{}).get('display',''), 'status': j.get('status','')} 
               for j in json.load(f).get('jobs', [])}
```

### 第3步：分三类（治本方案）

| 类型 | 特征 | 方案 |
|------|------|------|
| **死任务** | output目录最后运行时间距今>7天 | 直接从jobs.json删除 |
| **半失败** | 成功率40-70%，output目录有运行记录 | 诊断失败原因，修脚本 |
| **历史拖累** | 成功率>90%，但失败总数高 | 暂不动（算法问题，不值得改） |

### 第4步：算收益（决策依据）

死任务删掉后均分提升：
```python
dead_sum = sum(j['score'] for j in dead_jobs)
alive_sum = sum(j['score'] for j in jobs if j not in dead_jobs)
new_avg = alive_sum / (len(jobs) - len(dead_jobs))
print(f"删{len(dead_jobs)}个死任务：均分 {data['avg_score']} → {new_avg}")
```

### 第5步：验证output目录（必须用mtime判断）

死任务判断必须用output目录实际最后运行时间，不能只看cron_quality_report的`latest_run`。

```bash
ls -lt /opt/data/cron/output/<job_id>/ | head -3
# 看最后运行时间和文件大小
```

## 三类处置规范

### 死任务处置
1. 确认output目录最后时间 > 7天前
2. 从jobs.json中删除job记录
3. 更新cron system（`cronjob action=remove job_id=xxx`）
4. 归档output目录到 `/opt/data/backups/cron_dead_<date>/`

### 半失败任务处置
1. 读最近3次失败的output，看错误模式
2. 常见失败原因：脚本路径变化、依赖模块缺失、文件权限、OOM
3. 修复后用`cronjob action=run`测试
4. 观察3次成功才认定修复完成

## 典型案例（2026-06-05）

| job | 分数 | 类型 | 处置 |
|-----|------|------|------|
| 仔仔日志诊断 | 56 | 死任务 | 删，提升2分 |
| 学习健康守护 | 54 | 死任务 | 删，提升1分 |
| 每日MEMORY备份 | 60 | 死任务 | 删，提升0.8分 |
| 白日梦引擎 | 64 | 半失败 | 修脚本 |

## 注意事项
- 先诊断再操作，不凭分数猜测运行状态
- 死任务判断必须看output目录mtime，不是jobs.json里的latest_run
- 半失败任务先修再删，脚本能跑就不删
