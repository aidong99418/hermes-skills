#!/usr/bin/env python3
"""
🧠 自我观测器 - 行为日志记录与分析
===============================
职责：
1. 记录每次行为（tier判断、响应时间、成功率）
2. 统计brain检索命中率
3. 生成每日质量报告
4. 识别异常模式（连续失败、tier误判）

文件位置：/opt/data/brain/performance/
  - behavior_log.jsonl     # 行为日志（追加）
  - brain_retriever_metrics.json  # 检索指标
  - self_observer_report_{date}.json  # 每日报告

用法：
  python3 self_observer.py              # 记录当前状态
  python3 self_observer.py --report     # 生成每日报告
  python3 self_observer.py --analyze    # 分析最近100条记录
"""
import json, sys, os, time
from pathlib import Path
from datetime import datetime, date
from collections import defaultdict

BASE = Path("/opt/data/brain/performance")
BEHAVIOR_LOG = BASE / "behavior_log.jsonl"
RETRIEVER_METRICS = BASE / "brain_retriever_metrics.json"
REPORT_DIR = BASE / "reports"
REPORT_DIR.mkdir(exist_ok=True)

# ── 记录行为 ──────────────────────────────────────────────
def log_behavior(
    question: str,
    detected_tier: int,
    actual_tier: int = None,
    elapsed_ms: int = 0,
    brain_hit_count: int = 0,
    brain_max_score: float = 0.0,
    brain_used: bool = True,
    external_used: bool = False,
    team_used: bool = False,
    success: bool = True,
    error_msg: str = "",
    source: str = "auto",
):
    """
    记录一次完整的行为事件到 behavior_log.jsonl
    """
    entry = {
        "timestamp": datetime.now().isoformat(),
        "question_preview": question[:100],
        "detected_tier": detected_tier,
        "actual_tier": actual_tier,       # 用户/人工标记，可后续补充
        "tier_correct": (detected_tier == actual_tier) if actual_tier else None,
        "elapsed_ms": elapsed_ms,
        "brain_hit_count": brain_hit_count,
        "brain_max_score": brain_max_score,
        "brain_used": brain_used,
        "external_used": external_used,
        "team_used": team_used,
        "success": success,
        "error": error_msg,
        "source": source,
        # 质量指标
        "speed_grade": "fast" if elapsed_ms < 1000 else "normal" if elapsed_ms < 5000 else "slow",
        "brain_hit_rate": brain_hit_count / max(1, brain_hit_count + (0 if brain_used else 1)),
        # 隐式：tier1应<1s，tier2应<5s，tier3应<15s
        "time_ok": (
            elapsed_ms < 1000 if detected_tier == 1 else
            elapsed_ms < 5000 if detected_tier == 2 else
            elapsed_ms < 15000
        ),
    }

    with open(BEHAVIOR_LOG, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # 同时更新检索指标
    _update_retriever_metrics(brain_hit_count, brain_max_score, brain_used)
    
    return entry


def _update_retriever_metrics(hit_count: int, max_score: float, brain_used: bool):
    """更新brain检索指标（简单移动平均）"""
    metrics = {}
    if RETRIEVER_METRICS.exists():
        try:
            metrics = json.loads(RETRIEVER_METRICS.read_text())
        except:
            metrics = {}

    today = date.today().isoformat()
    if today not in metrics:
        metrics[today] = {
            "total_queries": 0,
            "total_hits": 0,
            "total_score": 0.0,
            "queries_with_hits": 0,
            "avg_score": 0.0,
        }

    m = metrics[today]
    m["total_queries"] += 1
    m["total_score"] += max_score
    if brain_used:
        m["total_hits"] += hit_count
    if max_score > 0:
        m["queries_with_hits"] += 1
    m["avg_score"] = round(m["total_score"] / max(1, m["total_queries"]), 2)
    m["hit_rate"] = round(m["queries_with_hits"] / max(1, m["total_queries"]), 3)

    RETRIEVER_METRICS.write_text(json.dumps(metrics, ensure_ascii=False, indent=2))


# ── 分析最近记录 ──────────────────────────────────────────
def analyze_recent(n: int = 100):
    """分析最近N条行为日志"""
    if not BEHAVIOR_LOG.exists():
        print("❌ 暂无行为日志")
        return

    entries = []
    try:
        lines = BEHAVIOR_LOG.read_text().strip().split("\n")
        for line in reversed(lines[-n:]):
            try:
                entries.append(json.loads(line))
            except:
                continue
        entries.reverse()
    except:
        print("❌ 读取日志失败")
        return

    if not entries:
        print("❌ 暂无数据")
        return

    total = len(entries)
    
    # 基础统计
    tier_counts = defaultdict(int)
    speed_counts = defaultdict(int)
    success_count = 0
    time_ok_count = 0
    brain_hits = []
    tier_correct = []
    elapsed_list = []
    errors = []

    for e in entries:
        tier_counts[e["detected_tier"]] += 1
        speed_counts[e["speed_grade"]] += 1
        if e["success"]: success_count += 1
        if e.get("error"): errors.append(e["error"])
        if e.get("time_ok"): time_ok_count += 1
        brain_hits.append(e["brain_hit_count"])
        elapsed_list.append(e["elapsed_ms"])
        if e.get("tier_correct") is not None:
            tier_correct.append(e["tier_correct"])

    # 检索命中率（从metrics）
    hit_rate = "N/A"
    if RETRIEVER_METRICS.exists():
        try:
            metrics = json.loads(RETRIEVER_METRICS.read_text())
            today_key = max(metrics.keys())
            hit_rate = f"{metrics[today_key].get('hit_rate', 0)*100:.1f}%"
        except:
            pass

    # 置信度（从confidence_tracking）
    conf_avg = "N/A"
    conf_file = BASE / "confidence_tracking.json"
    if conf_file.exists():
        try:
            data = json.loads(conf_file.read_text())
            if data:
                confs = [v.get("base_conf", 0.7) for v in data.values()]
                conf_avg = f"{sum(confs)/len(confs):.2f}"
        except:
            pass

    # OOM/错误统计
    error_count = len(errors)

    print(f"""
╔══════════════════════════════════════╗
║  🧠 自我观测报告（最近{total}条）       ║
╚══════════════════════════════════════╝

📊 行为分布
  tier1: {tier_counts[1]}次  tier2: {tier_counts[2]}次  tier3: {tier_counts[3]}次

⚡ 响应速度
  快速(fast): {speed_counts['fast']}  正常(normal): {speed_counts['normal']}  慢(slow): {speed_counts['slow']}
  达标率: {time_ok_count}/{total} = {time_ok_count*100//total}%

🔍 Brain检索
  今日命中率: {hit_rate}
  平均命中数: {sum(brain_hits)/max(1,len(brain_hits)):.1f}
  最高分: {max(brain_hits) if brain_hits else 0}

🎯 Tier判断准确率
  已标注: {len(tier_correct)}/{total}
  正确: {sum(tier_correct)}/{len(tier_correct)} = {sum(tier_correct)*100//max(1,len(tier_correct))}% (需人工标注actual_tier)

⏱ 响应时间
  平均: {sum(elapsed_list)//max(1,len(elapsed_list))}ms
  最快: {min(elapsed_list)}ms  最慢: {max(elapsed_list)}ms

📈 系统健康
  成功率: {success_count}/{total} = {success_count*100//total}%
  错误数: {error_count}
  置信度均值: {conf_avg}

📋 目标进度
  tier准确率: {'✅ >90%' if tier_correct and sum(tier_correct)/len(tier_correct) > 0.9 else '⚠️ 需提升'}
  brain命中率: {'✅ >80%' if hit_rate != 'N/A' and float(hit_rate.rstrip('%')) > 80 else '⚠️ 需提升'}
""")

    if errors:
        print(f"⚠️ 最近错误: {errors[:3]}")


# ── 生成每日报告 ──────────────────────────────────────────
def generate_daily_report():
    """生成当日报告并存档"""
    today = date.today().isoformat()
    report_file = REPORT_DIR / f"self_observer_report_{today}.json"
    
    # 读取今日所有日志
    today_entries = []
    try:
        if BEHAVIOR_LOG.exists():
            for line in BEHAVIOR_LOG.read_text().strip().split("\n"):
                try:
                    e = json.loads(line)
                    if e["timestamp"].startswith(today):
                        today_entries.append(e)
                except:
                    continue
    except:
        pass

    report = {
        "date": today,
        "total_interactions": len(today_entries),
        "generated_at": datetime.now().isoformat(),
    }

    if today_entries:
        tier_counts = defaultdict(int)
        success = 0
        elapsed_total = 0
        brain_hits_total = 0
        queries_with_brain = 0
        time_ok = 0
        errors = []

        for e in today_entries:
            tier_counts[e["detected_tier"]] += 1
            if e["success"]: success += 1
            elapsed_total += e["elapsed_ms"]
            brain_hits_total += e["brain_hit_count"]
            if e["brain_used"]: queries_with_brain += 1
            if e.get("time_ok"): time_ok += 1
            if e.get("error"): errors.append(e["error"])

        n = len(today_entries)
        report.update({
            "tier_distribution": dict(tier_counts),
            "success_rate": round(success/n, 3),
            "avg_response_ms": round(elapsed_total/n),
            "time_ok_rate": round(time_ok/n, 3),
            "brain_avg_hits": round(brain_hits_total/n, 2),
            "brain_hit_rate": round(queries_with_brain/n, 3) if n > 0 else 0,
            "error_count": len(errors),
            "errors": list(set(errors))[:5],
        })

        # 达标判断
        report["goals"] = {
            "tier_accuracy_90": "✅ 达标" if False else "⚠️ 待验证（需actual_tier标注）",
            "brain_hit_rate_80": "✅ 达标" if report["brain_hit_rate"] >= 0.8 else "⚠️ 需提升",
            "avg_response_time": "✅ 达标" if report["avg_response_ms"] < 5000 else "⚠️ 偏慢",
        }

    report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"📄 报告已生成: {report_file}")
    return report


# ── 被动记录（被brain_invoke.py调用）──────────────────────
def log_from_brain_result(result: dict):
    """从brain_think返回结果中提取数据并记录"""
    return log_behavior(
        question=result.get("question", ""),
        detected_tier=result.get("tier", 1),
        elapsed_ms=result.get("self_observation", {}).get("elapsed_ms", 0),
        brain_hit_count=result.get("brain_hit_count", 0),
        brain_max_score=result.get("brain_max_score", 0.0),
        brain_used=result.get("tier", 1) > 1,
        external_used=result.get("external_used", False),
        team_used=bool(result.get("team_results")),
        success=bool(result.get("conclusion")),
        source="brain_invoke",
    )


# ── CLI入口 ──────────────────────────────────────────────
if __name__ == "__main__":
    args = sys.argv[1:]

    if "--report" in args:
        generate_daily_report()
    elif "--analyze" in args:
        n = 100
        try:
            idx = args.index("-n")
            n = int(args[idx+1])
        except:
            pass
        analyze_recent(n)
    elif "--log" in args:
        # 手动记录: --log "问题" tier 耗时_ms 命中数 最高分
        question = args[args.index("--log")+1] if len(args) > 1 else ""
        tier = int(args[args.index("--tier")+1]) if "--tier" in args else 1
        elapsed = int(args[args.index("--elapsed")+1]) if "--elapsed" in args else 0
        hits = int(args[args.index("--hits")+1]) if "--hits" in args else 0
        score = float(args[args.index("--score")+1]) if "--score" in args else 0.0
        log_behavior(question, tier, elapsed_ms=elapsed, brain_hit_count=hits, brain_max_score=score)
        print("✅ 已记录")
    else:
        # 默认：分析最近100条
        print("用法:")
        print("  python3 self_observer.py                    # 分析最近100条")
        print("  python3 self_observer.py --report           # 生成每日报告")
        print("  python3 self_observer.py --analyze -n 50    # 分析最近50条")
        print("  python3 self_observer.py --log 问题 --tier 2 --elapsed 1200 --hits 3 --score 5.0")
        analyze_recent(100)
