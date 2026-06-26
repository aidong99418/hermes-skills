---
name: deputy-worker-exception-protection
description: Deputy Worker 进程异常保护修复 — 防止超时/执行异常杀死整个 worker 进程。触发：deputy_worker 反复崩溃重启、派工队列堆积无人消费。
---

# Deputy Worker 异常保护修复

## 触发场景
deputy_worker.py 进程反复崩溃，每次崩溃后 PID 变化（被 supervisor 重新拉起），导致派工队列无人消费而堆积。

## 根因
```
第309行 execute_task() 调用
  → subprocess.run() 执行外部命令超时
  → 抛出 subprocess.TimeoutExpired 异常
  → 第352行外层 except Exception 捕获
  → 进程退出 (sys.exit)
```

关键代码段（修复前）：
```python
# 第309行
result = execute_task(task)  # 超时/异常 → 抛出

# 第352行
except Exception as e:
    logger.error(f"执行异常: {e}")
    save_error_result(task_id, str(e))
    sys.exit(1)  # ← 这里杀死了整个进程！
```

## 修复方案
在 `execute_task()` 调用处加 try-except，超时/异常只标记任务失败，进程继续处理下一个：

```python
# 第309行改为：
try:
    result = execute_task(task)  # 可能超时/抛异常
except (subprocess.TimeoutExpired, Exception) as e:
    result = None
    error_msg = str(e)
    logger.warning(f"任务 {task_id} 执行异常: {error_msg}")
    # 标记任务 done，异常信息写入 raw_result
    mark_task_done(task_id, raw_result=[f"执行异常: {error_msg}"])
    continue  # ← 继续处理下一个任务，不退出进程
```

## 关键原则
- **主循环进程不能因单个任务异常而退出**
- 异常只影响当前任务，不影响整个 worker
- 超时 = 任务失败，不是 worker 崩溃

## 验证方法
```bash
# 1. 启动 worker
nohup python3 /opt/data/secretary/deputy_worker.py > /opt/data/logs/secretary/deputy_worker.log 2>&1 &
echo $! > /tmp/deputy_worker.pid

# 2. 写入一个必然超时的测试任务
cat >> /opt/data/secretary/dispatch_board.json << 'EOF'
{"task_id":"test_timeout_001","type":"bash","command":"sleep 60","priority":1,"status":"pending","created_at":"2026-06-23T00:00:00Z","to":"deputy_worker"}
EOF

# 3. 等待30秒，检查 worker 是否存活
sleep 35
ps -p $(cat /tmp/deputy_worker.pid) && echo "进程存活 ✅" || echo "进程已崩溃 ❌"

# 4. 检查任务是否被标记为 done（而非卡在 processing）
python3 -c "import json; d=json.load(open('/opt/data/secretary/dispatch_board.json')); print([t for t in d if 'test_timeout' in t.get('task_id','')])"
```

## 修复位置
`/opt/data/secretary/deputy_worker.py` 第309-320行附近

## 相关文件
- `/opt/data/secretary/deputy_worker.py` — 任务执行器
- `/opt/data/secretary/dispatch_board.json` — 派工板
- `/opt/data/secretary/result_board.json` — 结果板
- `/opt/data/logs/secretary/deputy_worker.log` — 运行日志
