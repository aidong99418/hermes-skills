---
name: cron-debug-nuclear-clear
description: Cron 排雷诊断与修复规范 — 解决"No inference provider"报错 + 模型调度配置优化
triggers:
  - Cron 任务报错 "No inference provider"
  - 系统不稳定需要全盘排雷
  - 全局模型调度策略调整
version: 1.0
---

# Cron 排雷诊断与修复规范

## 诊断步骤

### Step 1: 从错误日志定位根因
```bash
grep -r "No inference" /opt/data/logs/ 2>/dev/null | tail -20
```
找出具体任务名 → 再从 `jobs.json` 定位 job id。

### Step 2: 检查 jobs.json provider 配置
```python
import json
data = json.load(open('/opt/data/cron/jobs.json'))
for j in data['jobs']:
    if not j.get('provider') and j.get('enabled'):
        print(j['name'], j['id'])
```

### Step 3: 理解 scheduler 调度行为（铁律）
- **所有 cron 任务都走 AI 模型推理**（有 script 也只注入 context）
- scheduler.py 587行 `from run_agent import AIAgent` — 无例外
- `resolve_runtime_provider()` → provider=null → `get_inference_provider()` → 报错
- wisemodel 凭证在 `config.yaml` 的 `custom_providers`，不在 `.env`
- 纯数据采集脚本（无 prompt 无 skills，deliver=local）**仍会触发 AI 推理**

### Step 4: 分类与最优配置
| 任务性质 | deliver | provider | model |
|----------|---------|----------|-------|
| 后台数据采集/学习（不推用户） | local | **local** | qwen2.5:7b |
| 前台推送董哥（特助类） | weixin/origin | **wisemodel** | minimax-m2.5-highspeed |

**铁律：后台任务绝对不调用云端 API，只有特助推送才能用 wisemodel API。**

### Step 5: 批量修复 jobs.json
```python
import json
with open('/opt/data/cron/jobs.json') as f:
    data = json.load(f)

for job in data['jobs']:
    if not job.get('enabled'):
        continue
    deliver = job.get('deliver', '')
    if deliver in ('weixin', 'origin'):
        job['provider'] = 'wisemodel'
        job['model'] = 'minimax-m2.5-highspeed'
    else:
        job['provider'] = 'local'
        job['model'] = 'qwen2.5:7b'

with open('/opt/data/cron/jobs.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

### Step 6: 验证修复
```bash
# 检查配置结果
python3 -c "
import json
d = json.load(open('/opt/data/cron/jobs.json'))
print('wisemodel:', sum(1 for j in d['jobs'] if j.get('provider')=='wisemodel'))
print('local:', sum(1 for j in d['jobs'] if j.get('provider')=='local'))
print('null(disabled):', sum(1 for j in d['jobs'] if not j.get('provider')))
"

# 验证 wisemodel API 连通性
curl -s --max-time 10 \
  -H "Authorization: Bearer wisemodel-gbngcikewhrtirhoamio" \
  -H "Content-Type: application/json" \
  -d '{"model":"minimax-m2.5-highspeed","messages":[{"role":"user","content":"hi"}],"max_tokens":5}' \
  "https://open.ospreyai.cn/v1/chat/completions"
```

## 关键文件路径
- jobs.json: `/opt/data/cron/jobs.json`
- config.yaml: `/opt/data/config.yaml` (wisemodel 凭证在此)
- errors.log: `/opt/data/logs/errors.log`
- scheduler: `/opt/hermes/cron/scheduler.py`
- runtime_provider: `/opt/hermes/hermes_cli/runtime_provider.py`

## 陷阱警示
- ❌ 不要只修报错最频繁的几个任务，要扫描全部 jobs
- ❌ 纯脚本任务（script-only）不等于不需要 AI — scheduler 仍会调用模型
- ❌ wisemodel 凭证不在 `.env`，在 `config.yaml` 的 `custom_providers`
- ✅ disabled 任务可以保留 null provider（不影响）
