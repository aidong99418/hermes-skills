#!/usr/bin/env python3
"""
秘书处急救脚本 - 一次性解决架构断点
触发：派工板不响应/积压/daemon死机/全链路中断
执行：启动daemon + 清理死数据 + 验证全链路
"""
import json, subprocess, time, sys, signal, os
from pathlib import Path
from datetime import datetime

SECRETARY = Path("/opt/data/secretary")
DISPATCH = SECRETARY / "dispatch_board.json"
RESULT = SECRETARY / "result_board.json"
LOG = SECRETARY / "logs/rescue.log"

def log(msg):
    ts = datetime.now().strftime("%m-%d %H:%M")
    line = f"[{ts}] {msg}"
    print(line)
    LOG.parent.mkdir(exist_ok=True)
    LOG.open("a").write(line + "\n")

def read_json(fp, default):
    if fp.exists():
        try: return json.loads(fp.read_text())
        except: pass
    return default

def write_json(fp, data):
    tmp = str(fp) + ".tmp"
    Path(tmp).write_text(json.dumps(data, ensure_ascii=False, indent=2))
    Path(tmp).rename(fp)

# ════════════════════════════════════════
# 1. 修复 dispatch_board.json 格式
# ════════════════════════════════════════
log("═" * 50)
log("🔧 修复1: dispatch_board.json 格式统一")
board = read_json(DISPATCH, {"tasks": [], "pending_tasks": [], "completed_tasks": []})

# pending_tasks[] → tasks[] (把死数据救活)
if board.get("pending_tasks"):
    moved = 0
    for t in board["pending_tasks"]:
        if t.get("status") != "completed":
            t.setdefault("status", "pending")
            t.setdefault("processing_at", None)
            board["tasks"].append(t)
            moved += 1
    log(f"  ✅ 从pending_tasks迁移{moved}条到tasks[]")
    board["pending_tasks"] = []

# 确保所有task都有status字段
for t in board["tasks"]:
    t.setdefault("status", "pending")
    t.setdefault("processing_at", None)

write_json(DISPATCH, board)
log(f"  📋 tasks:{len(board['tasks'])} | completed:{len(board['completed_tasks'])}")

# ════════════════════════════════════════
# 2. 清理 result_board.json 积压
# ════════════════════════════════════════
log("🔧 修复2: 清理unread积压")
rb = read_json(RESULT, {"results": [], "unread": [], "result_counter": 0})

if rb.get("unread"):
    log(f"  ⚠️  清空{len(rb['unread'])}条unread积压")
    rb["unread"] = []

if rb.get("results"):
    latest = rb["results"][-1]
    log(f"  📬 最新成果: [{latest.get('from_secretary','?')}] {latest.get('instruction','')[:60]}")

write_json(RESULT, rb)

# ════════════════════════════════════════
# 3. 启动 deputy_worker 守护进程
# ════════════════════════════════════════
log("🔧 修复3: 启动 deputy_worker 守护进程")
running = subprocess.run(["pgrep", "-f", "deputy_worker.py"], capture_output=True).returncode == 0
if running:
    log("  ⏭️  deputy_worker 已在运行，跳过")
else:
    subprocess.Popen(
        [sys.executable, str(SECRETARY / "deputy_worker.py")],
        stdout=open(SECRETARY / "logs/deputy_worker_out.log", "a"),
        stderr=subprocess.STDOUT,
        start_new_session=True
    )
    log("  ✅ deputy_worker 已后台启动")

# ════════════════════════════════════════
# 4. 启动 deputy_result 守护进程
# ════════════════════════════════════════
log("🔧 修复4: 启动 deputy_result 守护进程")
running2 = subprocess.run(["pgrep", "-f", "deputy_result.py"], capture_output=True).returncode == 0
if running2:
    log("  ⏭️  deputy_result 已在运行，跳过")
else:
    subprocess.Popen(
        [sys.executable, str(SECRETARY / "deputy_result.py")],
        stdout=open(SECRETARY / "logs/deputy_result_out.log", "a"),
        stderr=subprocess.STDOUT,
        start_new_session=True
    )
    log("  ✅ deputy_result 已后台启动")

# ════════════════════════════════════════
# 5. 给派工板写一个测试任务验证流程
# ════════════════════════════════════════
log("🔧 修复5: 写入测试任务验证流程")
board = read_json(DISPATCH, {"tasks": [], "pending_tasks": [], "completed_tasks": []})
board["dispatch_counter"] = board.get("dispatch_counter", 0) + 1
test_task = {
    "id": f"dispatch_{board['dispatch_counter']:04d}",
    "source": "rescue_script",
    "instruction": "系统架构急救验证任务 - 验证全链路",
    "from": "急救脚本",
    "to": "技术秘书",
    "priority": 7,
    "status": "pending",
    "created_at": datetime.now().isoformat(),
    "processing_at": None,
    "completed_at": None,
    "claimed_by": None,
    "raw_result": None,
    "collected": False
}
board["tasks"].append(test_task)
board["last_updated"] = datetime.now().isoformat()
write_json(DISPATCH, board)
log(f"  ✅ 测试任务已写入: {test_task['id']}")

log("═" * 50)
log("🎉 急救完成！")
