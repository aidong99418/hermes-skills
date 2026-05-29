#!/opt/hermes/.venv/bin/python3
"""
对话流自动触发brain_think - 文件监控方案
原理：cron每分钟检查sessions目录，文件mtime变化→读最新用户消息→brain_think→存档
不依赖inotify/agent核心，纯外部轮询
"""
import sys, json, time
from pathlib import Path

# 关键修复：scripts 目录 append 到末尾（不抢在 stdlib/dist-packages 之前）
# 这样避免 scripts/requests.py、scripts/email.py 等 shadow 文件劫持导入
scripts_dir = str(Path(__file__).parent)
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)
from brain_invoke import brain_think, record_feedback, recommend_skills

SESSIONS_DIR = Path("/opt/data/sessions")
STATE_FILE = Path("/opt/data/brain/performance/dialog_watchdog_state.json")
OUTPUT_DIR = Path("/opt/data/brain/performance/dialog_insights")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_mtime": 0, "last_file": "", "last_user_msg": ""}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False))

def get_latest_session():
    """找最新的session文件"""
    files = sorted(SESSIONS_DIR.glob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        return None
    return files[0]

def extract_last_user_message(filepath):
    """从jsonl读最后一条user消息"""
    try:
        lines = filepath.read_text(errors='ignore').strip().split('\n')
        for line in reversed(lines):
            entry = json.loads(line)
            if entry.get('role') == 'user':
                return entry.get('content', '')[:500]  # 截取前500字
    except:
        pass
    return ""

def main():
    state = load_state()
    latest = get_latest_session()
    if not latest:
        print("无session文件")
        return

    mtime = latest.stat().st_mtime
    # 检查文件是否更新
    if mtime <= state["last_mtime"]:
        print(f"无新消息 (文件未更新)")
        return

    # 提取最新用户消息
    user_msg = extract_last_user_message(latest)
    if not user_msg or user_msg == state["last_user_msg"]:
        print(f"无新用户消息或内容相同: {user_msg[:50]!r}")
        # 更新mtime但不触发brain_think
        save_state({**state, "last_mtime": mtime, "last_file": str(latest)})
        return

    print(f"检测到新对话: {latest.name}")
    print(f"用户: {user_msg[:80]!r}")

    # 调用brain_think
    try:
        result = brain_think(user_msg, save_to_brain=True)
        print(f"tier: {result['tier']} {result['tier_name']}")
        print(f"brain命中: {result['brain_hit_count']}条")
        print(f"置信度: {result.get('confidence', 'N/A')}")
        print(f"耗时: {result['self_observation'].get('elapsed_ms', '?')}ms")

        # 保存洞察结果
        insight = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "session": latest.name,
            "question": user_msg,
            "tier": result["tier"],
            "brain_hit_count": result["brain_hit_count"],
            "brain_max_score": result["brain_max_score"],
            "should_save": result["should_save"],
            "conclusion_preview": result["conclusion"][:200] if result["conclusion"] else "",
            "recommended_skills": result.get("recommended_skills", []),
        }
        out_file = OUTPUT_DIR / f"insight_{int(mtime*1000)}.json"
        out_file.write_text(json.dumps(insight, ensure_ascii=False, indent=2))
        print(f"洞察已存档: {out_file.name}")

        # 记录到行为日志
        log_file = OUTPUT_DIR / "insights_log.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(insight, ensure_ascii=False) + "\n")

    except Exception as e:
        print(f"brain_think失败: {e}")

    # 更新状态
    save_state({
        "last_mtime": mtime,
        "last_file": str(latest),
        "last_user_msg": user_msg,
    })

if __name__ == "__main__":
    main()
