#!/usr/bin/env python3
"""
🧠 机器猫大脑系统触发式实时备份
关键文件变更 → 立即备份 + 即时GitHub推送

触发条件：
  1. 任何brain核心脚本被修改（vim/保存/patch等操作）
  2. neural/working_memory/confidence等数据文件变更
  3. 架构文档被修改

对比上次状态，自动识别变更文件，只备份有变化的。
"""
import os, shutil, glob, json, datetime, subprocess, hashlib
from pathlib import Path

BACKUP_ROOT = "/volume2/数据备份/brain_backup"
GIT_REPO = "/opt/data/external-skills"
STATE_FILE = "/opt/data/brain/performance/backup_state.json"
RETENTION_DAYS = 7

# 需要监控的关键文件（变化时才备份）
KEY_FILES = [
    "/opt/data/scripts/brain_invoke.py",
    "/opt/data/scripts/brain_retriever.py",
    "/opt/data/scripts/brain_thinker.py",
    "/opt/data/scripts/dialog_watchdog.py",
    "/opt/data/scripts/external_fetcher.py",
    "/opt/data/scripts/web_scraper.py",
    "/opt/data/scripts/self_observer.py",
    "/opt/data/brain/neural/connections.json",
    "/opt/data/brain/neural/inference_paths.json",
    "/opt/data/brain/working_memory.json",
    "/opt/data/brain/performance/confidence_tracking.json",
    "/opt/data/brain/performance/feedback_tracking.json",
    "/opt/data/brain/performance/behavior_log.jsonl",
    "/opt/data/brain/brain_architecture_v2.md",
    "/opt/data/brain/brain_architecture.md",
    "/opt/data/rag_index/keyword_index.json",
]

def log(msg, tag="INFO"):
    ts = datetime.datetime.now().strftime("%m-%d %H:%M")
    print(f"[{ts}] [{tag}] {msg}")

def get_file_state(fpath):
    """获取文件的mtime和md5（仅前4KB用于快速比对）"""
    if not os.path.exists(fpath):
        return None
    stat = os.stat(fpath)
    try:
        with open(fpath, "rb") as ff:
            data = ff.read(4096)
        md5 = hashlib.md5(data).hexdigest()[:12]
    except:
        md5 = str(stat.st_size)
    return {"mtime": stat.st_mtime, "size": stat.st_size, "md5": md5}

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def detect_changes():
    """检测哪些文件发生了变化，返回变更列表"""
    current = {f: get_file_state(f) for f in KEY_FILES}
    previous = load_state()
    
    changed = []
    for f in KEY_FILES:
        curr = current[f]
        prev = previous.get(f)
        if curr is None:
            continue  # 文件不存在
        if prev is None or prev["mtime"] != curr["mtime"]:
            changed.append(f)
    
    return changed, current

def backup_changed_files(changed_files):
    """只备份变更的文件"""
    today = datetime.date.today().strftime("%Y%m%d")
    backup_dir = Path(BACKUP_ROOT) / today / "triggered"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    backed = []
    for f in changed_files:
        fname = os.path.basename(f)
        dest = backup_dir / fname
        shutil.copy2(f, dest)
        backed.append(fname)
    
    # 写变更清单
    manifest = {
        "triggered_at": datetime.datetime.now().isoformat(),
        "reason": "file_change",
        "changed_files": backed,
        "count": len(backed),
    }
    manifest_path = backup_dir / "trigger_manifest.json"
    with open(manifest_path, "w") as ff:
        json.dump(manifest, ff, ensure_ascii=False, indent=2)
    
    log(f"📦 变更触发备份: {len(backed)}个文件 → {backup_dir}")
    return backed

def push_to_github(changed_files):
    """把变更的文件同步到herrmes-skills仓库"""
    if not os.path.exists(GIT_REPO):
        log("GitHub仓库未挂载，跳过推送", "SKIP")
        return
    
    # 检查仓库git状态
    try:
        os.chdir(GIT_REPO)
        result = subprocess.run(["git", "status", "--porcelain"], 
                              capture_output=True, text=True, timeout=5)
        if not result.stdout.strip():
            log("GitHub无变更待提交", "SKIP")
            return
    except Exception as e:
        log(f"Git检查失败: {e}", "WARN")
        return
    
    # 复制变更文件到仓库对应目录
    for f in changed_files:
        fname = os.path.basename(f)
        # 根据文件名放到对应skill目录
        dest_base = GIT_REPO
        if fname in ["brain_invoke.py", "brain_thinker.py", "brain_retriever.py"]:
            # 放到brain-invoke skill
            skill_dir = Path(GIT_REPO) / "brain-invoke" / "scripts"
        elif fname == "dialog_watchdog.py":
            skill_dir = Path(GIT_REPO) / "external-fetcher" / "scripts"
        elif fname in ["external_fetcher.py", "web_scraper.py"]:
            skill_dir = Path(GIT_REPO) / "external-fetcher" / "scripts"
        elif fname == "self_observer.py":
            skill_dir = Path(GIT_REPO) / "brain-system-integration" / "scripts"
        elif "connections" in fname or "inference_paths" in fname:
            # JSON配置放到brain-invoke
            skill_dir = Path(GIT_REPO) / "brain-invoke" / "scripts"
        elif "confidence" in fname or "feedback" in fname or "behavior_log" in fname:
            # 性能数据放到brain-system-integration
            skill_dir = Path(GIT_REPO) / "brain-system-integration" / "scripts"
        elif "working_memory" in fname:
            skill_dir = Path(GIT_REPO) / "brain-thinker" / "scripts"
        else:
            skill_dir = Path(GIT_REPO) / "brain-invoke" / "scripts"
        
        skill_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, skill_dir / fname)
    
    # git add + commit + push
    try:
        subprocess.run(["git", "add", "-A"], capture_output=True, timeout=5)
        result = subprocess.run(["git", "status", "--porcelain"],
                              capture_output=True, text=True, timeout=5)
        
        if result.stdout.strip():
            msg = f"🤖 Auto-sync: {', '.join([os.path.basename(f) for f in changed_files[:3]])}"
            if len(changed_files) > 3:
                msg += f" (+{len(changed_files)-3} more)"
            msg += f" @ {datetime.datetime.now().strftime('%m-%d %H:%M')}"
            subprocess.run(["git", "commit", "-m", msg], capture_output=True, timeout=5)
            push_result = subprocess.run(
                ["git", "push", "origin", "master"],
                capture_output=True, text=True, timeout=30
            )
            if push_result.returncode == 0:
                log(f"🚀 GitHub已推送 {len(changed_files)}个变更文件", "OK")
            else:
                log(f"⚠️ GitHub推送失败: {push_result.stderr[:100]}", "WARN")
        else:
            log("GitHub无变更，跳过", "SKIP")
    except subprocess.TimeoutExpired:
        log("GitHub推送超时，跳过", "WARN")
    except Exception as e:
        log(f"GitHub推送异常: {e}", "WARN")

def clean_old():
    """清理超过7天的旧备份"""
    cutoff = datetime.date.today() - datetime.timedelta(days=RETENTION_DAYS)
    for d in glob.glob(str(Path(BACKUP_ROOT) / "202*")):
        date_str = os.path.basename(d)
        try:
            d_date = datetime.datetime.strptime(date_str, "%Y%m%d").date()
            if d_date < cutoff:
                shutil.rmtree(d)
                log(f"🗑️ 清理旧备份: {date_str}", "CLEAN")
        except ValueError:
            pass

def full_backup():
    """每小时完整备份（包含所有文件，不论是否变化）"""
    today = datetime.date.today().strftime("%Y%m%d")
    backup_dir = Path(BACKUP_ROOT) / today / "hourly"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    backed = []
    missing = []
    for f in KEY_FILES:
        fname = os.path.basename(f)
        dest = backup_dir / fname
        if os.path.exists(f):
            shutil.copy2(f, dest)
            backed.append(fname)
        else:
            missing.append(fname)
    
    manifest = {
        "type": "hourly_full",
        "date": today,
        "backed": backed,
        "missing": missing,
        "total": len(backed),
    }
    with open(backup_dir / "manifest.json", "w") as ff:
        json.dump(manifest, ff, ensure_ascii=False, indent=2)
    
    log(f"📦 整点完整备份: {len(backed)}个文件", "OK")
    if missing:
        log(f"⚠️ 缺失: {missing}", "WARN")
    
    clean_old()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--full":
        full_backup()
    else:
        # 触发式检测：只备份变更的文件
        changed, current_state = detect_changes()
        
        if changed:
            log(f"🔔 检测到{len(changed)}个文件变更: {[os.path.basename(f) for f in changed]}", "TRIGGER")
            
            # 1. 立即备份到本地
            backup_changed_files(changed)
            
            # 2. 立即推GitHub
            push_to_github(changed)
            
            # 3. 更新状态
            save_state(current_state)
            
            print(f"\n✅ 触发备份完成: {len(changed)}个文件已备份+推送")
        else:
            # 无变更，检查是否需要整点完整备份
            minute = datetime.datetime.now().minute
            if minute == 0:
                log("整点到，执行完整备份", "SCHEDULED")
                full_backup()
                save_state(current_state)
            else:
                log("无变更，略过", "IDLE")
