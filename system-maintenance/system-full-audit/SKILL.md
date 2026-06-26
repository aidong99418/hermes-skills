---
name: system-full-audit
description: 系统全身检查与清理流水线 — 逐字扫描所有模块，发现重复/废弃/冲突并自动修复。触发：用户说"做全身检查"、"系统诊断"、"清理重复"。
triggers: ["架构", "用户说", "系统"]
version: 1.0
---

# 系统全身检查与清理流水线

## 执行步骤

### 1. 目录扫描
```bash
# 检查核心目录
ls -la /opt/data/secretary/          # 秘书处
ls -la /opt/data/秘书/*.py         # 秘书秘书
ls -la /opt/data/scripts/            # scripts目录
find /opt/data/skills -name "*.md"   # skills文档

# 检查进程
ps aux | grep -E "(run.py|secretary|秘书)" | grep -v grep

# 检查cronjobs
cronjob list
```

### 2. 识别5类常见问题

| 问题类型 | 检查方法 | 修复方式 |
|---------|---------|---------|
| **废弃目录** | 目录存在但cron从未触发 | 移动到 `_old_xxx_YYYYMMDD/` |
| **重复脚本** | 多目录同名文件，内容相同 | 保留一个，更新所有引用 |
| **重复cronjob** | 多个cron跑同一脚本 | 保留频率最合适的，pause其他 |
| **功能重叠** | 13个学习任务 → 实际只有3-4个独立功能 | 合并由统一调度器接管，暂停旧的 |
| **推送未配置** | webhook为空但cron在跑 | 记录问题，验证脚本能正常执行 |

### 3. 验证检查清单

```bash
# 验证删除/移动
ls /opt/data/secretary/

# 验证cron已暂停
cronjob list | grep enabled

# 验证引用已更新
grep -r "旧路径" /opt/data/scripts/*.py

# 测试关键脚本（push_results.py已于2026-05-29清理）
```

## 常见修复操作

### ⚠️ `http.py` 覆盖标准库（批量cron报 ModuleNotFoundError）
**症状**：多个cron任务同时报错 `ModuleNotFoundError: No module named 'http.client'` / `No module named 'requests'`

**根因**：`/opt/data/scripts/http.py` 与Python标准库 `http` 包同名，导入时优先找到 `scripts/http.py`，覆盖标准库，httpx/urllib3/requests全部挂。

**诊断**：
```bash
/opt/hermes/.venv/bin/python3 -c "import http.client"   # 报错即中招
/opt/hermes/.venv/bin/python3 -c "import requests"       # 报错即中招
```

**修复**：重命名文件解除覆盖
```bash
mv /opt/data/scripts/http.py /opt/data/scripts/http_volcano.py
# 验证
/opt/hermes/.venv/bin/python3 -c "import requests; print('OK')"
```

**预防**：避免在 `/opt/data/scripts/` 下创建与Python标准库同名的文件（`http.py`、`typing.py`、`pathlib.py` 等）。

### 僵尸进程诊断
**症状**：`ps aux` 显示 `<defunct>`，CPU 0%

**诊断**：`ps aux | grep defunct`

**风险**：通常无害，父进程退出后init自动回收。PID 1下大量僵尸才需关注。

**清理**：僵尸无法手动kill，等待父进程退出即可。

### 删除废弃目录（先备份后删除）
```bash
mkdir -p /opt/data/secretary/_old_backup_$(date +%Y%m%d)
mv /opt/data/secretary/废弃目录 /opt/data/secretary/_old_backup_$(date +%Y%m%d)/
```

### 暂停重复cronjob
```bash
# 两个相同任务，保留推微信的
cronjob pause <job_id_不推微信的>
```

### 合并office工具（三套变一套）
```bash
# 1. 比较内容
python3 -c "
import os
d1 = open('/opt/data/scripts/pptx_TEMP/office/pack.py').read()
d2 = open('/opt/data/scripts/xlsx/office/pack.py').read()
print('相同' if d1==d2 else '不同')
"

# 2. 保留docx_TEMP，更新引用
patch /opt/data/scripts/office_skills_dispatcher.py \
  -e 's|pptx_TEMP|docx_TEMP|g' \
  -e 's|xlsx/|docx_TEMP/|g'
```

### 迁移文件隔离（已完成）
**状态**：/opt/data/scripts/migrations/ 已隔离175个迁移文件（hex格式hash_ 和数字前缀001_）。
隔离已完成，scripts目录不再被migration文件污染。不需要再处理。

### Python标准库shadow分析（2026-05-30实测）
**发现5个shadow文件，但不可删除**：
```
code.py    - 37个内部引用
html.py    - 7个内部引用
platform.py - 5个内部引用
resource.py - 12个内部引用
time.py    - 562个内部引用（最高危！）
```
**诊断方法**：
```bash
# 方法1：用Python stdlib_module_names检测
python3 -c "import os,sys; stdlib=set(sys.stdlib_module_names); shadowed=[f for f in os.listdir('/opt/data/scripts') if f.endswith('.py') and f[:-3] in stdlib and not f.startswith('_')]; print(shadowed)"

# 方法2：检查引用数量（决定能否安全删除）
grep -rl "from scripts import time\|import time" /opt/data/scripts/*.py | wc -l
```
**结论**：time.py被引用562次，动不得。安全清理只处理：废弃目录、重复文件、失效符号链接。

### Port 18643冲突误报
**症状**：gateway_restart.log显示 `OSError [Errno 98] address already in use`  
**结论**：这是Gateway上次重启时的错误日志，不代表当前问题。当前Gateway正常运行在端口18643（PID 1），无需处理。

### self_observer_wrapper.sh路径错误
**症状**：cron任务报错"No inference provider"（prompt模式）  
**根因**：cron引用 `/opt/data/scripts/self_observer_wrapper.sh`，实际文件在 `cron_wrappers/` 子目录  
**修复**：
```bash
ln -sf cron_wrappers/self_observer_wrapper.sh /opt/data/scripts/self_observer_wrapper.sh
```

### 4个cron报"No inference provider"（暂不处理）
**根因**：这4个cron用prompt模式运行，会走Agent推理，但cron后台无推理环境配置  
**涉及任务**：每日元学习/短视频营销学习/自进化每日报告/herrmes-skills同步  
**说明**：需要深入理解cron执行环境和模型配置才能安全修复。当前状态不影响核心功能，暂保留。

## 器官命名规范（2026-05-28确认）
- Worker-A = 👃 鼻子·情报秘书
- Worker-B = 🫚 肝脏·学习秘书
- Worker-C = ✋ 手掌·文秘
- Worker-D = 🫀 心脏·策略秘书
- Hermes = 大脑（不能重复叫大脑）

## 修复优先级
1. **安全清理** - 删除废弃目录（无风险）
2. **停用重复** - pause重复cron（可恢复）
3. **合并重复** - 三套变一套（需更新引用）
4. **验证推送** - 确认webhook配置

---

## NAS磁盘垃圾清理工作流（2026-05-30实测）

### ⚠️ 铁律：先识别活代码，再清理死代码
**典型错误**：对着废弃代码做升级/迁移。活代码判断标准：
- cron近期有输出？→ 活
- jsonl文件有最近写入？→ 活
- 有进程在跑？→ 活
- 外部被引用？→ 活

### 第一步：识别真实占用
```bash
# 磁盘占用TOP分布
du -sh /opt/data/*/ | sort -rh | head -15

# 临时目录
du -sh /tmp/*/ | sort -rh
du -sh /opt/data/cron/output/

# 大文件扫描（>100MB）
find /opt/data -type f -size +100M 2>/dev/null
```

### 第二步：识别活 vs 死
```bash
# 活跃jsonl（3天内有写入）
find /opt/data/brain -name "*.jsonl" -mtime -3 -exec wc -l {} \;

# cron输出活跃度
ls -lt /opt/data/cron/output/ | head -10

# 进程检查
ps aux | grep <进程名> | grep -v grep

# 脚本引用检查
grep -r "<目录名>" /opt/data/scripts/ /opt/data/cron/ 2>/dev/null | head -5
```

### 第三步：安全判定分类

| 类别 | 判定标准 | 行动 |
|------|---------|------|
| **立即可清** | 无进程 + 无引用 + 残留物（安装包/缓存/下载残留） | 直接rm -rf |
| **谨慎清理** | 无进程 + 无引用 + 但有真实数据（旧备份/旧输出） | 先看内容，再决定 |
| **需董哥确认** | 历史对话记录 / 有引用但不确定用途 | 不动，等确认 |

### 已验证可立即清理的类型（零风险）

| 垃圾类型 | 典型路径 | 理由 |
|---------|---------|------|
| **pip http缓存** | `/opt/data/home/.cache/pip/http-v2/` | 2.9GB，pip下次自动重建 |
| **pip unpack残留** | `/tmp/pip-unpack-*` | pip自己的临时目录 |
| **下载残留** | `/tmp/<软件名>*/` | 程序已装到/usr/local/bin/ |
| **浏览器安装包** | `/tmp/camoufox*/` | 用完的zip，无进程 |
| **DELETE标记目录** | `external-skills/*-DELETE/` | 100%废弃，无活跃引用 |
| **neural旧备份** | `neural_network_v3.5_backup_YYYYMMDD/` | 确认无引用后可清 |

### 已验证必须保留的活跃模块

| 目录 | 大小 | 理由 |
|------|------|------|
| `models/` | 8GB | Ollama GGUF模型文件 |
| `秘书/秘书_f_config/` | 14MB | 配置监控工具，changes.log活跃 |
| `gems/downloads/browser_use` | 572KB | 实际使用的精简版 |
| `brain/` | 59MB | 记忆系统核心，有jsonl活跃写入 |
| `sessions/` | 1.5GB+ | 历史对话记录 |
| `venv/` | 125MB | Python环境 |
| `cron/output/` | 74MB+ | cron实时输出缓存 |

### 僵尸进程判断
```bash
ps aux | grep defunct    # 看数量和年龄
ps aux | awk '$8=="Z"{print $3}' | sort | uniq -c | sort -rn  # PPID分组
```
- PPID=0：历史孤儿，可忽略
- PPID=1且多：容器PID 1问题，需重启容器
- 新僵尸持续产生：父进程fork/wait bug，需修复脚本

---

## 执行器卡死任务诊断（2026-06-03实测）

### 典型症状
- 任务`status=pending`+`processing_at=时间戳`，但永远不完成
- 日志只显示心跳"无待执行任务"
- 多次手动重写派工板无效

### 根因
`deputy_worker.py` line 167过滤逻辑：
```python
pending = [t for t in tasks if t.get("status") == "pending" and not t.get("processing_at")]
```
任务一旦被认领（`processing_at`已设），执行器就认为"正在处理"，永不重捡。

**触发条件**：模型OOM/超时/死循环时，任务卡在`processing`状态无法恢复。

### 诊断三板斧
```bash
# 1. 看派工板状态
python3 -c "
import json
d = json.load(open('/opt/data/secretary/dispatch_board.json'))
for t in d['tasks']:
    if t.get('status') == 'pending' and t.get('processing_at'):
        print(f'卡死任务: {t.get(\"task_id\",\"?\")[:40]}')
        print(f'  processing_at: {t.get(\"processing_at\")}')
"

# 2. 看worker日志
tail -20 /opt/data/secretary/logs/deputy_worker.log

# 3. 看worker进程状态
ps aux | grep deputy_worker | grep -v grep
cat /tmp/deputy_worker.lock
```

### 修复：STUCK_MINUTES自动恢复
在`deputy_worker.py`主循环加自动恢复：
```python
STUCK_MINUTES = 15  # processing超过此时间则重置

while True:
    # 自动恢复卡死任务
    now = datetime.now()
    for t in tasks:
        pt = t.get("processing_at")
        if pt and t.get("status") == "pending":
            try:
                elapsed = (now - dt.fromisoformat(pt)).total_seconds()
                if elapsed > STUCK_MINUTES * 60:
                    t.pop("processing_at", None)
                    t.pop("claimed_by", None)
                    log(f"🔄 恢复卡死任务", "WARN")
            except: pass
```

### 手动紧急修复
```python
python3 -c "
import json
d = json.load(open('/opt/data/secretary/dispatch_board.json'))
for t in d['tasks']:
    if t.get('task_id') == '目标task_id':
        t['status'] = 'pending'
        t.pop('processing_at', None)
        t.pop('claimed_by', None)
json.dump(d, open('/opt/data/secretary/dispatch_board.json','w'), ensure_ascii=False, indent=2)
print('已重置')
"
```

---

## 任务resources字段分批执行（2026-06-03）

### 典型症状
执行器输出空洞："请提供资源信息"，模型看不到`resources`字段。

### 根因
`deputy_worker.py`的`execute_task()`直接拼接`instructions`，不处理`resources`字段：
```python
instruction = "\n".join(task.get("instructions", []))
# resources字段被完全忽略！
```

### 解决：split_into_batches + execute_batched
```python
BATCH_SIZE = 3  # 每批最多3个资源

def split_into_batches(task):
    resources = task.get("resources", [])
    if len(resources) <= BATCH_SIZE:
        return [task]
    
    instructions = task.get("instructions", [])
    batches = []
    total = (len(resources) + BATCH_SIZE - 1) // BATCH_SIZE  # 向上取整
    for i in range(0, len(resources), BATCH_SIZE):
        chunk = resources[i:i+BATCH_SIZE]
        sub = {**task, "resources": chunk}
        base = instructions[0] if instructions else task.get("instruction", "")
        range_hint = f"（这是第{i//BATCH_SIZE+1}批，共{total}批，分析这{len(chunk)}个资源）"
        sub["instructions"] = [base + range_hint] + instructions[1:]
        batches.append(sub)
    return batches

def execute_batched(task):
    batches = split_into_batches(task)
    results = []
    for batch in batches:
        results.append(call_ollama(...))
    return {
        **task,
        "status": "done",
        "completed_at": ts(),
        "raw_result": "\n\n".join(results),
    }
```

**注意**：`total_batches = (len(resources) + BATCH_SIZE - 1) // BATCH_SIZE` 用向上取整，不用 `len//BATCH_SIZE+1`。

### 验证
```python
# 6个资源应拆成2批（不是3批）
batches = split_into_batches({'task_id':'x','instructions':['分析'],'resources':[{'id':i} for i in range(1,7)]})
print(len(batches))  # 应输出2
```

---

## hermes_auto_clean.py接入规范（2026-06-03实测）

### 完整落地三步
1. **cron触发**：每天03:00执行
   ```bash
   crontab -l | grep auto_clean || echo "0 3 * * * /usr/bin/python3 /opt/data/scripts/hermes_auto_clean.py >> /opt/data/logs/auto_clean.log 2>&1" | crontab -
   ```
2. **免疫层监控**：在`/opt/data/auto_healing.py`的`DETECTION_RULES`加一项
   ```python
   "system_clean": {
       "name": "系统自净化cron",
       "check_cmd": "crontab -l 2>/dev/null | grep 'hermes_auto_clean' > /dev/null && echo HEALTHY || echo MISSING",
       "auto_fix": True,
       "fix_cmd": "echo '0 3 * * * ...' | crontab -",
       "healthy_pattern": "^HEALTHY$",
       "severity": "low",
   },
   ```
3. **验证**：健康分100/100包含该项

### session文件清理教训（2026-06-03）
- cron频繁产生session快照，sessions/目录可达12,747个文件
- **保留期30天太长**，应改为**7天**
- `clean_old_sessions()`需覆盖**两个位置**：sessions/目录 + 根目录`session_*.json`
- 首次运行清理5,122个文件，释放626.3MB

### 清理优先级（安全顺序）
1. ① `__pycache__` + `.pyc`（Python缓存，自动重建）
2. ② `.pytest_cache`（测试缓存）
3. ③ 旧会话（>7天归档）
4. ④ 旧日志（>7天压缩，>30天删除）
5. ⑤ 空目录（递归清理）
6. ⑥ 积压备份（保留最近4个）

---

## 全链路Agent架构审计（2026-06-03实测）

### 触发条件
用户说"全链路审计"、"架构扫描"。

### 三分类框架

| 类别 | 审计内容 | 典型问题 |
|------|---------|---------|
| **标点/文本** | 全角/半角、引号、括号、特殊符号 | 中文标点、正则转义 |
| **数据孤岛** | JSON文件间引用断裂、数据不同步 | 双版本数据、路径错位、文档与实际不符 |
| **架构链路** | Ollama→Gateway→器官→秘书处→推送 | 字段不兼容、断点无降级 |

### 快速扫描脚本（execute_code执行）

```python
import json, pathlib

# 1. evolution_state 版本检查
es = json.load(open('/opt/data/brain/neural/evolution_state.json'))
print(f"evolve版本: {es.get('version')} | 节点: {len(es.get('nodes',{}))}")

# 2. MEMORY路径准确性
mem = open('/opt/data/memories/MEMORY.md').read()
for path in ['/opt/data/neural_network/', '/opt/data/brain/neural/']:
    exists = pathlib.Path(path).exists()
    print(f"{path}: {'存在' if exists else '不存在'} | MEMORY中: {'有' if path in mem else '无'}")

# 3. organ文档 vs 实际文件数
actual = set(p.stem for p in pathlib.Path('/opt/data/organs').glob('*.py'))
doc_organs = set()
try:
    doc = json.load(open('/opt/data/brain/memory_bank/organ_system_v2.json'))
    doc_organs = set(o['name'] for o in doc.get('organs',[]))
except: pass
print(f"实际器官: {len(actual)} | 文档记录: {len(doc_organs)} | 差集: {actual-doc_organs}")

# 4. 派工板字段完整性
db = json.load(open('/opt/data/secretary/dispatch_board.json'))
issues = []
for t in db.get('tasks',[])[:10]:
    if 'task_id' not in t and 'id' not in t:
        issues.append(f"缺少id: {str(t)[:60]}")
print(f"派工板: {len(issues)}个问题" if issues else "✅ 字段完整")
```

### 已发现并修复的问题（2026-06-03）

| 问题 | 修复 |
|------|------|
| evolution_state双版本分流（v3.0在根目录，v4.0在activation_engine_data/） | v3路径替换为v4内容，节点228→23949，大小1.66→9.6MB |
| MEMORY.md路径`/opt/data/neural_network/`不存在 | 改为`/opt/data/brain/neural/` |
| MEMORY.md器官数8（实际13） | 补充完整列表 |
| organ_system_v2.json器官数10（实际13） | 重写为v3.0，13器官全记录 |
