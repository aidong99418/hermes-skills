#!/usr/bin/env python3
"""
机器猫大脑思考引擎 v1.0
=======================
输入问题 → 判断思考层级 → 执行推理路径 → 输出结构化思考结果

用法：
  python3 /opt/data/scripts/brain_thinker.py "你的问题"
"""
import sys
import os
import json
import re
from pathlib import Path

# 添加scripts路径
sys.path.insert(0, '/opt/data/scripts')

# ── 思考层级判断 ─────────────────────────────────────────────
TIER1_KEYWORDS = [
    "几点了", "现在", "时间", "日期", "在哪", "文件", "目录",
    "查看", "看一下", "帮我看", "ls", "cat", "ps", "df",
    "状态", "运行", "日志", "配置", "端口"
]
TIER3_KEYWORDS = [
    "设计", "架构", "方案", "怎么选", "哪个好", "权衡", "取舍",
    "安全", "攻击", "漏洞", "权限", "能实现吗", "可行性",
    "我没遇到过", "新领域", "整体", "全局"
]
TIER2_KEYWORDS = [
    "思考", "想一想", "分析一下", "区别", "原理", "为什么",
    "应该", "推荐", "优化", "还有什么", "不确定", "拿不准",
    "帮我", "怎么", "如何", "是什么", "有什么区别"
]

def detect_tier(question: str) -> int:
    """判断问题属于哪个思考层级"""
    q = question.lower()
    
    # ── tier1优先：明确的动作指令 ─────────────────────────────
    tier1_patterns = [
        r"^(帮我)?(看|查|找|显示|列出|打开|执行)[\一下]",
        r"^(帮我)?(看一下|查一下|找一下)",
        r"(现在|当前).*(状态|情况)",
        r".*(剩|还有|多少|在哪)",
    ]
    for p in tier1_patterns:
        if re.search(p, q):
            # 确认不是复杂问题（复杂词不在句首）
            if not any(kw in q[:10] for kw in ["设计", "架构", "分析", "思考"]):
                return 1
    
    # tier3优先判断（高风险/复杂）
    for kw in TIER3_KEYWORDS:
        if kw in q:
            return 3
    
    # tier1次优先：命令行类查询
    tier1_count = sum(1 for kw in TIER1_KEYWORDS if kw in q)
    tier2_count = sum(1 for kw in TIER2_KEYWORDS if kw in q)
    
    if tier1_count >= 2 and tier2_count == 0:
        return 1
    
    # tier2判断（需要思考）
    if tier2_count > 0 or any(kw in q for kw in ["为什么", "怎么", "分析", "思考"]):
        return 2
    
    # 包含问号但没有明显复杂特征的 → tier2
    if "?" in question or "？" in question:
        return 2
    
    return 1

# ── 思考引擎 ─────────────────────────────────────────────────
def think(question: str, tier: int, disable_external: bool = False) -> dict:
    """执行思考流程"""
    result = {
        "question": question,
        "tier": tier,
        "tier_name": ["", "快速通道", "思考通道", "团队协作"][tier],
        "thinking_steps": [],
        "brain_hits": [],
        "rag_hits": [],
        "conclusion": "",
        "knowledge_to_save": None
    }
    
    if tier == 1:
        result["thinking_steps"].append("【快速通道】问题简单直接，无需深度思考")
        result["conclusion"] = "直接执行工具或回答"
        return result
    
    # ── Tier 2 & 3：检索brain ─────────────────────────────────
    try:
        from brain_retriever import BrainRetriever
        retriever = BrainRetriever(rebuild=False)
        
        # 多角度检索
        queries = [question, question]
        
        all_hits = []
        seen_texts = set()
        for q in queries:
            hits = retriever.search(q, top_k=8)
            for h in hits:
                if h["text"][:80] not in seen_texts:
                    seen_texts.add(h["text"][:80])
                    all_hits.append(h)
        
        # 排序去重
        all_hits.sort(key=lambda x: -x["score"])
        result["brain_hits"] = all_hits[:5]
        
        if all_hits:
            result["thinking_steps"].append(
                f"【brain检索】找到 {len(result['brain_hits'])} 条相关知识"
            )
            for h in result["brain_hits"][:3]:
                result["thinking_steps"].append(
                    f"  → {h['source']} (匹配度:{h['score']:.1f})"
                )
        else:
            result["thinking_steps"].append("【brain检索】无相关记录")
            
    except Exception as e:
        result["thinking_steps"].append(f"【brain检索】失败: {e}")

    # ── Tier 2 & 3：外部知识获取（brain不足时）────────────────
    if tier >= 2 and not disable_external:
        has_enough_brain = (
            len(result["brain_hits"]) >= 1 and
            result["brain_hits"][0]["score"] > 5.0
        )
        
        if not has_enough_brain:
            result["thinking_steps"].append("🌐 brain知识不足，触发外部获取...")
            try:
                from external_fetcher import fetch_and_learn
                ext_result = fetch_and_learn(question)
                result["external_data"] = ext_result["sources"]
                result["thinking_steps"].append(
                    f"🌐 获取到 {len(ext_result['sources']['arxiv'])} 篇ArXiv，"
                    f"{len(ext_result['sources']['hn'])} 条HN，"
                    f"{len(ext_result['sources']['web'])} 条SO"
                )
                result["external_answer"] = ext_result["answer"]
                result["knowledge_saved"] = ext_result["saved"]
            except Exception as e:
                result["thinking_steps"].append(f"⚠️ 外部获取失败: {e}")

    # ── Tier 3：团队协作思考 ───────────────────────────────────
    if tier == 3 and not disable_external:
        result["thinking_steps"].append("【团队协作】启动多角度分析...")
        
        # 派发子问题给各模型（并行）
        team_tasks = [
            {
                "name": "推理专家",
                "model": "deepseek-r1:7b",
                "prompt": f"请深入分析这个问题，给出逻辑推理：{question}\n请从多个角度分析利弊。"
            },
            {
                "name": "工具专家",
                "model": "qwen2.5:7b-instruct-q4_K_M", 
                "prompt": f"请从实际执行角度分析：{question}\n考虑技术可行性和实现路径。"
            },
            {
                "name": "打工仔",
                "model": "qwen2.5:3b-instruct-q4_K_M",
                "prompt": f"请从数据/事实角度分析：{question}\n有哪些已知案例和数据支撑？"
            }
        ]
        
        try:
            import requests
            import json
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            def call_model(task):
                """并行调用单个模型"""
                try:
                    start = time.time()
                    resp = requests.post(
                        "http://localhost:11434/api/generate",
                        json={"model": task["model"], "prompt": task["prompt"],
                              "stream": False, "options": {"num_predict": 150}},
                        timeout=60
                    )
                    elapsed = int((time.time() - start) * 1000)
                    if resp.status_code == 200:
                        data = json.loads(resp.text)
                        return {
                            "name": task["name"],
                            "model": task["model"],
                            "result": data.get("response", "")[:200],
                            "elapsed_ms": elapsed,
                            "success": True
                        }
                    else:
                        return {
                            "name": task["name"],
                            "model": task["model"],
                            "result": f"HTTP {resp.status_code}",
                            "elapsed_ms": elapsed,
                            "success": False
                        }
                except Exception as e:
                    return {
                        "name": task["name"],
                        "model": task["model"],
                        "result": str(e),
                        "elapsed_ms": 0,
                        "success": False
                    }

            # 真实并行执行（3个模型同时调用）
            team_results = []
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {executor.submit(call_model, task): task for task in team_tasks}
                for future in as_completed(futures):
                    r = future.result()
                    team_results.append(r)
                    if r["success"]:
                        result["thinking_steps"].append(
                            f"  ✅ {r['name']}({r['model']}): {r['elapsed_ms']}ms"
                        )
                    else:
                        result["thinking_steps"].append(
                            f"  ❌ {r['name']}: {r['result']}"
                        )

            result["team_results"] = team_results
            result["thinking_steps"].append(f"  → 并行汇总 {len(team_results)} 个视角（总耗时=max(各模型)）")
            
        except Exception as e:
            result["thinking_steps"].append(f"⚠️ 团队协作失败: {e}")

    # ── 结论生成 ─────────────────────────────────────────────
    if result.get("external_answer"):
        result["conclusion"] = f"【来自外部知识】\n{result['external_answer'][:500]}"
        if result.get("knowledge_saved"):
            result["conclusion"] += "\n\n💾 已存入brain，下次可直接检索"
    elif result["brain_hits"]:
        top = result["brain_hits"][0]
        result["conclusion"] = (
            f"检索到相关知识：{top['source']}（匹配度{top['score']:.1f}），"
            f"可作为参考。\n"
            f"建议：引用brain知识，结合当前问题具体分析。"
        )
    else:
        result["conclusion"] = "brain无相关记录，已尝试外部获取，请查看上方结果"

    return result

# ── 知识沉淀建议 ─────────────────────────────────────────────
def suggest_save(question: str, answer: str, tier: int) -> dict:
    """判断答案是否值得沉淀到brain"""
    suggestion = {"should_save": False, "target": "", "content": ""}
    
    if tier == 1:
        return suggestion
    
    # tier2/3 且答案较长 → 值得保存
    if len(answer) > 200 and tier >= 2:
        # 判断类型
        if any(kw in question.lower() for kw in ["错误", "报错", "bug", "error"]):
            suggestion["should_save"] = True
            suggestion["target"] = "problem_types/debugging.md"
            suggestion["content"] = f"## 问题：{question}\n\n**症状：**\n**根因：**\n**解决：**\n{answer[:300]}\n"
        elif any(kw in question.lower() for kw in ["怎么", "如何", "实现", "写"]):
            suggestion["should_save"] = True
            suggestion["target"] = "scenarios/solution_未分类_20260523.md"
            suggestion["content"] = f"## 问题：{question}\n\n**解决方案：**\n{answer[:400]}\n"
    
    return suggestion

# ── CLI主程序 ───────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="机器猫大脑思考引擎")
    parser.add_argument("question", nargs="*", help="要思考的问题")
    parser.add_argument("--tier", type=int, help="强制指定层级(1/2/3)")
    parser.add_argument("--no-external", action="store_true", help="禁用外部获取")
    args = parser.parse_args()
    
    question = " ".join(args.question) if args.question else ""
    if not question:
        print("用法: python3 brain_thinker.py \"你的问题\"")
        sys.exit(1)
    
    # 1. 判断层级
    tier = args.tier or detect_tier(question)
    tier_names = ["", "⚡快速通道", "🧠思考通道", "🔴团队协作"]
    print(f"\n{'='*60}")
    print(f"🧠 机器猫思考引擎")
    print(f"{'='*60}")
    print(f"问题：{question}")
    print(f"层级：{tier_names[tier]}")
    print()
    
    # 2. 执行思考
    result = think(question, tier, disable_external=args.no_external)
    
    # 3. 输出思考过程
    print("📝 思考过程：")
    for step in result["thinking_steps"]:
        print(f"  {step}")
    print()
    
    # 4. 输出brain命中
    if result["brain_hits"]:
        print("📚 brain命中：")
        for i, h in enumerate(result["brain_hits"][:3], 1):
            print(f"  【{i}】{h['type']} | {h['source']}")
            print(f"      匹配度：{h['score']:.1f}")
            print(f"      {h['text'][:150]}...")
        print()
    
    # 5. 外部获取结论
    if result.get("external_answer"):
        print("📡 外部知识结论:")
        print(f"  {result['external_answer'][:300]}")
        print()
    
    # 6. 团队协作结论（tier3）
    if result.get("team_results"):
        print("🔴 团队分析结果:")
        for tr in result["team_results"]:
            print(f"  【{tr['name']}】{tr['result'][:150]}...")
        print()
    
    # 7. 输出结论
    print("💡 结论：")
    print(f"  {result['conclusion']}")
    print()
    
    # 8. 知识沉淀建议
    suggestion = result.get("brain_write_suggestion")
    if not suggestion:
        suggestion = suggest_save(question, result["conclusion"], tier)
    if suggestion.get("should_save"):
        print("💾 建议沉淀到：", suggestion["target"])
    
    print()
