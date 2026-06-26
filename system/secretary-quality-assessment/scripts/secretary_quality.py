#!/usr/bin/env python3
"""
秘书处效果自评估器——对result_board任务评分，驱动派工决策学习
触发：评估秘书处任务质量/发现0字结果/优化派工模型分配
"""
import json, sys, os
from datetime import datetime

RESULTS_PATH = "/opt/data/secretary/result_board.json"

def 评分单个任务(task):
    """5维度×权重评分"""
    score = 50  # 基础分
    result = task.get("result", {})
    metadata = task.get("metadata", {})
    
    # 维度1: 结果完整性(30%)
    result_len = len(str(result.get("content", "")))
    if result_len == 0:
        score -= 30
    elif result_len < 50:
        score -= 10
    elif result_len > 200:
        score += 10

    # 维度2: 推送状态(25%)
    status = task.get("status", "")
    if status == "pushed":
        score += 25
    elif status == "pending_push":
        score -= 15

    # 维度3: 执行效率(20%)
    timeout = task.get("timeout", 0)
    actual = task.get("execution_time", 0)
    if timeout > 0 and actual > 0:
        ratio = actual / timeout
        if ratio < 0.3:
            score += 5
        elif ratio > 0.9:
            score -= 5

    # 维度4: 指令遵循(15%)——代理分
    agent_score = result.get("agent_score", 0.5)
    score += (agent_score - 0.5) * 40

    # 维度5: 秘书身份(10%)
    claimed = task.get("claimed_by", "")
    if claimed in ["深度分析", "知识问答", "代码生成", "情报秘书"]:
        score += 10
    elif not claimed or claimed in ["qwen2.5:3b", "unknown"]:
        score -= 10

    return max(0, min(100, round(score)))

def 评估所有结果():
    """批量评估并输出报告"""
    if not os.path.exists(RESULTS_PATH):
        print("结果板不存在")
        return {}

    with open(RESULTS_PATH) as f:
        data = json.load(f)

    results = data.get("results", [])
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    scored = 0
    total_score = 0
    type_scores = {}

    for r in results:
        s = 评分单个任务(r)
        r["quality_score"] = s
        scored += 1
        total_score += s

        task_type = r.get("metadata", {}).get("task_type", "unknown")
        if task_type not in type_scores:
            type_scores[task_type] = {"sum": 0, "count": 0}
        type_scores[task_type]["sum"] += s
        type_scores[task_type]["count"] += 1

    avg = round(total_score / scored) if scored > 0 else 0

    # 写回结果板（加quality_score字段）
    with open(RESULTS_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 打印报告
    print(f"[{now}] 质量评估完成: {scored}条, 均分{avg}")
    for t, v in sorted(type_scores.items(), 
                       key=lambda x: x[1]["sum"] / max(1, x[1]["count"])):
        avg_t = round(v["sum"] / v["count"])
        bar = "█" * (avg_t // 10) + "░" * (10 - avg_t // 10)
        print(f"  {t}: [{bar}] {avg_t}分 ({v['count']}条)")

    return {"avg": avg, "scored": scored, "type_scores": type_scores}

if __name__ == "__main__":
    评估所有结果()
