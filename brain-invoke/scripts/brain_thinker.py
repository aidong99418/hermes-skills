#!/usr/bin/env python3
"""
机器猫大脑思考引擎 v2.0
=======================
输入问题 → 判断思考层级 → 三路检索(知识+Skill+神经推荐) → 输出结构化思考结果

v2.0 新增：
  - Skill触发词匹配（brain_retriever.search_all）
  - 神经连接权重更新（skill执行后自动强化）
  - Tier判断优化（参考neural connections）

用法：
  python3 /opt/data/scripts/brain_thinker.py "你的问题"
"""
import sys
import os
import json
import re
import time
from pathlib import Path
from datetime import datetime
import sys
sys.path.insert(0, '/opt/data/scripts')
from model_config import DEEP_MODEL, TEACHER_MODEL, CODER_MODEL
del FAST_MODEL  # 避免向后兼容别名冲突（若存在）
from model_config import FAST_MODEL, CODEGEN_MODEL  # 重新导入别名

# ── 模型变量解析 ──────────────────────────────────────────
_VAR_MAP = {"$DEEP_MODEL": DEEP_MODEL, "$TEACHER_MODEL": TEACHER_MODEL,
            "$CODER_MODEL": CODER_MODEL, "$FAST_MODEL": FAST_MODEL, "$CODEGEN_MODEL": CODEGEN_MODEL}
def resolve_model(var: str) -> str:
    return _VAR_MAP.get(var, var)

# 添加scripts路径
sys.path.insert(0, '/opt/data/scripts')

# ── 思考层级判断（v2.0 优化版）───────────────────────────────
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
    "帮我", "怎么", "如何", "是什么", "有什么区别",
    "报错", "Error", "error", "bug", "崩溃", "闪退",
    "代码", "脚本", "Python", "写代码", "函数",
]

# Skill触发词 → Tier提升映射
SKILL_TIER_BOOST = {
    "安全": 2, "漏洞": 2, "架构": 3, "方案选型": 3,
    "TDD": 1, "测试": 1, "原型": 2, "review": 1,
    "MCP": 2, "安全审计": 2, "压力测试": 3,
}

def detect_tier(question: str) -> int:
    """判断问题属于哪个思考层级（v2.0 + Skill boost）"""
    q = question.lower()

    # tier1优先：明确的动作指令
    tier1_patterns = [
        r"^(帮我)?(看|查|找|显示|列出|打开|执行)[\一下]",
        r"^(帮我)?(看一下|查一下|找一下)",
        r"(现在|当前).*(状态|情况)",
        r".*(剩|还有|多少|在哪)",
    ]
    for p in tier1_patterns:
        if re.search(p, q):
            if not any(kw in q[:10] for kw in ["设计", "架构", "分析", "思考"]):
                return 1

    base_tier = 1

    # tier3优先判断（高风险/复杂）
    for kw in TIER3_KEYWORDS:
        if kw in q:
            return 3

    # Skill boost：某些skill触发词自动提升tier
    for kw, boost_tier in SKILL_TIER_BOOST.items():
        if kw in q:
            base_tier = max(base_tier, boost_tier)
            if boost_tier >= 3:
                return 3

    # tier1次优先：命令行类查询
    tier1_count = sum(1 for kw in TIER1_KEYWORDS if kw in q)
    tier2_count = sum(1 for kw in TIER2_KEYWORDS if kw in q)

    if tier1_count >= 2 and tier2_count == 0:
        return 1

    # tier2判断（需要思考）
    if tier2_count > 0 or any(kw in q for kw in ["为什么", "怎么", "分析", "思考"]):
        return max(base_tier, 2)

    if "?" in question or "？" in question:
        return max(base_tier, 2)

    return 1

# ── 思考引擎 v2.0 ─────────────────────────────────────────────
def think(question: str, tier: int, disable_external: bool = False,
          async_mode: bool = True) -> dict:
    """执行思考流程 v2.0（知识+Skill双路检索）"""
    result = {
        "question": question,
        "tier": tier,
        "tier_name": ["", "快速通道", "思考通道", "团队协作"][tier],
        "thinking_steps": [],
        "brain_hits": [],
        "skill_matches": [],        # v2.0 新增
        "neural_suggestions": [],   # v2.0 新增
        "recommended_skill": None,  # v2.0 新增：推荐执行的skill
        "conclusion": "",
        "knowledge_to_save": None
    }

    if tier == 1:
        result["thinking_steps"].append("【快速通道】问题简单直接，无需深度思考")
        result["conclusion"] = "直接执行工具或回答"
        return result

    # ── Tier 2 & 3：三路检索（brain知识 + Skill触发 + 神经推荐）──
    try:
        from brain_retriever import BrainRetriever
        retriever = BrainRetriever(rebuild=False)

        # 使用 v2.0 search_all 三路并行
        search_result = retriever.search_all(question, user_tier=tier, top_k=8)

        result["brain_hits"] = search_result["brain_hits"][:5]
        result["semantic_hits"] = search_result.get("semantic_hits", [])  # E阶段：语义向量
        result["skill_matches"] = search_result["skill_matches"]
        result["neural_suggestions"] = search_result["neural_suggestions"]

        # 思考过程记录
        if result["brain_hits"]:
            top = result["brain_hits"][0]
            method = top.get("method", "bm25")
            method_emoji = {"bm25": "📝", "vector": "🔢", "fused": "⚡"}
            result["thinking_steps"].append(
                f"【brain检索】找到 {len(result['brain_hits'])} 条 (总{search_result['total_brain_chunks']}块)"
                f" {method_emoji.get(method,'📝')}{method}优先"
            )
            result["thinking_steps"].append(
                f"  → 最高匹配: {top['source']} ({top['score']:.3f})"
            )
        else:
            result["thinking_steps"].append(f"【brain检索】无相关记录 (总{search_result['total_brain_chunks']}块)")

        if result["skill_matches"]:
            best = result["skill_matches"][0]
            result["thinking_steps"].append(
                f"【Skill命中】{best['name']} (score={best['score']:.1f}) "
                f"触发词:{best['triggers_matched']} → 激活节点:{best['activates_nodes']}"
            )
            # 推荐执行的skill
            result["recommended_skill"] = {
                "name": best["name"],
                "file": best.get("file", ""),
                "score": best["score"],
                "triggers_matched": best["triggers_matched"],
                "activates_nodes": best["activates_nodes"],
                "strengthens": best.get("strengthens", []),
                "source": best.get("source", ""),
                "description": best.get("description", ""),
            }

            # 神经节点推断
            if result["neural_suggestions"]:
                names = [s["name"] for s in result["neural_suggestions"][:3]]
                result["thinking_steps"].append(f"【神经推荐】相关Skill: {', '.join(names)}")
        else:
            result["thinking_steps"].append(f"【Skill匹配】无skill命中 (总{search_result['total_skills']}个)")

    except Exception as e:
        result["thinking_steps"].append(f"【三路检索】失败: {e}")

    # ── Tier 2 & 3：外部知识获取（brain+skill都不足时）────────
    if tier >= 2 and not disable_external:
        has_enough = (
            len(result["brain_hits"]) >= 1 and result["brain_hits"][0]["score"] > 5.0
        ) or len(result["skill_matches"]) >= 1

        if not has_enough:
            result["thinking_steps"].append("🌐 brain+skill均不足，触发外部获取...")
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

    # ── Tier 3：团队协作思考（v3.0 异步派工）────────────────────
    if tier == 3 and not disable_external:
        result["thinking_steps"].append("【团队协作】派3个Worker后台分析...")

        if async_mode:
            # v3.0 新增：异步派工，不等待
            try:
                sys.path.insert(0, '/opt/data/scripts')
                from async_dispatcher import classify_question, dispatch, TaskType
                
                task_type, reason = classify_question(question)
                disp = dispatch(question, TaskType.DEEP, session_id="brain_thinker")

                from async_dispatcher import WORKER_CONFIG, TaskType as ADTaskType

                result["thinking_steps"].append(f"  → {reason}")
                # 生成用户可见的派工卡
                worker_lines = []
                for name in disp.get("workers", []):
                    cfg = WORKER_CONFIG.get(name, {})
                    emoji = cfg.get("emoji", "🔧")
                    role = cfg.get("role", "")
                    model_raw = cfg.get("model", "")
                    model = resolve_model(model_raw)
                    worker_lines.append(f"{emoji} {name} · {role} → `{model}`")

                card = (
                    f"\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🛠 **已派工**（任务ID: `{disp['task_id'][:8]}`）\n"
                    + "\n".join(f"   {line}" for line in worker_lines)
                    + f"\n   └ ⏱ 完成后微信推送给你\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━"
                )
                # 写入共享文件，gateway会在回复末尾注入这张卡
                try:
                    Path("/tmp/hermes_dispatch_card.txt").write_text(card)
                except Exception:
                    pass
                result["thinking_steps"].append(card)
                result["team_results"] = [{"task_id": disp["task_id"], "status": "async_dispatched",
                                           "workers": disp["workers"], "card": card}]
            except Exception as e:
                result["thinking_steps"].append(f"⚠️ 派工失败，回退同步模式: {e}")
                async_mode = False  # 回退

            # 同步等待模式（async_mode=False 时执行，供CLI测试）
            if not async_mode:
                team_tasks = [
                    {"name": "推理专家", "model": "$DEEP_MODEL",
                     "temperature": 0.7, "num_ctx": 8192,
                     "prompt": f"请深入分析这个问题，给出逻辑推理：{question}\n请从多个角度分析利弊。"},
                    {"name": "工具专家", "model": "$CODEGEN_MODEL",
                     "prompt": f"请从实际执行角度分析：{question}\n考虑技术可行性和实现路径。"},
                    {"name": "打工仔", "model": "$FAST_MODEL",
                     "prompt": f"请从数据/事实角度分析：{question}\n有哪些已知案例和数据支撑？"}
                ]

                try:
                    import requests
                    from concurrent.futures import ThreadPoolExecutor, as_completed

                    def call_model(task):
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
                                return {"name": task["name"], "model": task["model"],
                                        "result": data.get("response", "")[:200],
                                        "elapsed_ms": elapsed, "success": True}
                            else:
                                return {"name": task["name"], "model": task["model"],
                                        "result": f"HTTP {resp.status_code}",
                                        "elapsed_ms": elapsed, "success": False}
                        except Exception as e:
                            return {"name": task["name"], "model": task["model"],
                                    "result": str(e), "elapsed_ms": 0, "success": False}

                    team_results = []
                    with ThreadPoolExecutor(max_workers=3) as executor:
                        futures = {executor.submit(call_model, task): task for task in team_tasks}
                        for future in as_completed(futures):
                            r = future.result()
                            team_results.append(r)
                            status = "✅" if r["success"] else "❌"
                            result["thinking_steps"].append(
                                f"  {status} {r['name']}({r['model']}): {r['elapsed_ms']}ms"
                            )

                    result["team_results"] = team_results

                except Exception as e:
                    result["thinking_steps"].append(f"⚠️ 团队协作失败: {e}")

    # ── 结论生成（v2.0 优先推荐skill + 激活扩散建议）────────
    # 激活扩散建议（新增C阶段）
    spread_text = ""
    try:
        if tier >= 2:
            from brain_activation_engine import activate as neural_activate
            spread = neural_activate(question, max_hops=3, top_k=5)
            if spread:
                lines = ["", "🔗 相关知识域推荐："]
                for sa in spread:
                    bar = "█" * max(1, int(sa['activation'] * 12))
                    lines.append(f"   {sa['name']:<28} {sa['activation']:.2f} {bar}")
                spread_text = "\n".join(lines)
    except Exception:
        pass

    # 激活扩散思考步骤记录
    if tier >= 2 and spread_text:
        result["thinking_steps"].append(f"【激活扩散】发现{len(spread) if 'spread' in dir() else '相关'}个关联知识域")

    # ── 结论生成（无skill时也展示扩散结果）──────────────────
    # E阶段增强结论：当BM25无结果但语义强时，展示语义结果
    semantic_conclusion = ""
    if not result["brain_hits"] and result.get("semantic_hits"):
        top_sem = result["semantic_hits"][0]
        if top_sem["score"] >= 0.6:
            semantic_conclusion = (
                f"\n\n【语义向量补充】\n"
                f"  语义检索在 brain 中找到相关文档：\n"
                f"  📄 {top_sem['source']} (相似度 {top_sem['score']:.2f})\n"
                f"  {top_sem['text'][:200]}..."
            )

    if result["recommended_skill"]:
        skill = result["recommended_skill"]
        result["conclusion"] = (
            f"🎯 推荐执行Skill: **{skill['name']}**\n"
            f"   触发词: {', '.join(skill['triggers_matched'])}\n"
            f"   描述: {skill['description']}\n"
            f"   激活神经节点: {' → '.join(skill['activates_nodes'])}\n"
            f"   神经权重将在skill执行后自动强化{spread_text}"
        )
    elif result.get("external_answer"):
        result["conclusion"] = f"【来自外部知识】\n{result['external_answer'][:500]}{spread_text}{semantic_conclusion}"
        if result.get("knowledge_saved"):
            result["conclusion"] += "\n\n💾 已存入brain，下次可直接检索"
    elif result["brain_hits"]:
        top = result["brain_hits"][0]
        result["conclusion"] = (
            f"检索到相关知识：{top['source']}（匹配度{top['score']:.1f}），"
            f"可作为参考。\n建议：引用brain知识，结合当前问题具体分析。{spread_text}"
        )
    else:
        # BM25无结果 → 尝试用语义向量结论兜底
        if semantic_conclusion:
            result["conclusion"] = (
                f"BM25未命中，语义向量找到相关文档：\n"
                f"（相似度{result['semantic_hits'][0]['score']:.2f}）{semantic_conclusion}"
            )
        else:
            result["conclusion"] = "brain+skill均无相关记录，已尝试外部获取，请查看上方结果" + spread_text

    return result

# ── Skill执行后回调 ──────────────────────────────────────────
def on_skill_used(skill_name: str, neural_data: dict = None):
    """
    当某个skill被实际执行时调用此函数
    效果：更新 connections.json 突触权重，让神经通路变强
    """
    if not neural_data:
        # 尝试从skill_neural.json获取
        try:
            neural = json.load(open("/opt/data/brain/neural/skill_neural.json"))
            for s in neural.get("skills", []):
                if s["name"] == skill_name:
                    neural_data = s
                    break
        except:
            pass

    if neural_data:
        try:
            from brain_retriever import BrainRetriever
            r = BrainRetriever(rebuild=False)
            r.update_neural_on_skill_use(skill_name, neural_data)
            print(f"✅ 神经权重已更新: {skill_name}")
        except Exception as e:
            print(f"⚠️ 神经更新失败: {e}")

# ── 知识沉淀建议 ─────────────────────────────────────────────
def suggest_save(question: str, answer: str, tier: int) -> dict:
    """判断答案是否值得沉淀到brain"""
    suggestion = {"should_save": False, "target": "", "content": ""}

    if tier == 1:
        return suggestion

    if len(answer) > 200 and tier >= 2:
        if any(kw in question.lower() for kw in ["错误", "报错", "bug", "error"]):
            suggestion["should_save"] = True
            suggestion["target"] = "problem_types/debugging.md"
            suggestion["content"] = f"## 问题：{question}\n\n**症状：**\n**根因：**\n**解决：**\n{answer[:300]}\n"
        elif any(kw in question.lower() for kw in ["怎么", "如何", "实现", "写"]):
            suggestion["should_save"] = True
            suggestion["target"] = "scenarios/solution_未分类_20260523.md"
            suggestion["content"] = f"## 问题：{question}\n\n**解决方案：**\n{answer[:400]}\n"

    return suggestion

# ── CLI主程序 ────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="机器猫大脑思考引擎 v2.0")
    parser.add_argument("question", nargs="*", help="要思考的问题")
    parser.add_argument("--tier", type=int, help="强制指定层级(1/2/3)")
    parser.add_argument("--no-external", action="store_true", help="禁用外部获取")
    parser.add_argument("--skill-test", action="store_true", help="测试skill匹配")
    parser.add_argument("--async", dest="async_mode", action="store_true", help="异步派工模式（默认关闭，CLI测试用同步）")
    parser.add_argument("--sync", dest="sync_mode", action="store_true", help="同步等待模式（CLI默认，等3个模型跑完）")
    args = parser.parse_args()

    question = " ".join(args.question) if args.question else ""
    if not question:
        print("用法: python3 brain_thinker.py \"你的问题\" [--tier 2] [--no-external]")
        sys.exit(1)

    # Skill测试模式
    if args.skill_test:
        from brain_retriever import BrainRetriever
        r = BrainRetriever(rebuild=False)
        result = r.search_all(question, user_tier=2, top_k=5)
        print(f"\n🔍 Skill测试: {question}")
        print(f"   brain知识: {len(result['brain_hits'])} 条")
        print(f"   Skill命中: {len(result['skill_matches'])} 个")
        for s in result['skill_matches']:
            print(f"   → {s['name']} (score={s['score']}) 触发:{s['triggers_matched']} 激活:{s['activates_nodes']}")
        sys.exit(0)

    tier = args.tier or detect_tier(question)
    tier_names = ["", "⚡快速通道", "🧠思考通道", "🔴团队协作"]

    print(f"\n{'='*60}")
    print(f"🧠 机器猫思考引擎 v2.0")
    print(f"{'='*60}")
    print(f"问题：{question}")
    print(f"层级：{tier_names[tier]}")
    print()

    # CLI默认: 同步等待(sync)，--async 切换为异步派工
    async_mode = args.async_mode and not args.sync_mode

    result = think(question, tier, disable_external=args.no_external,
                   async_mode=async_mode)

    print("📝 思考过程：")
    for step in result["thinking_steps"]:
        print(f"  {step}")
    print()

    if result["brain_hits"]:
        print("📚 brain命中：")
        for i, h in enumerate(result["brain_hits"][:3], 1):
            method_tag = f"[{h.get('method','bm25')}]" if h.get('method') else ""
            print(f"  【{i}】{h['type']} | {h['source']} | 匹配度:{h['score']:.1f} {method_tag}")
            print(f"      {h['text'][:120]}...")
        print()

    # E阶段：展示语义向量检索结果
    if result.get("semantic_hits"):
        print("🔍 语义向量检索：")
        for i, h in enumerate(result["semantic_hits"][:3], 1):
            bar = "█" * max(1, int(h['score'] * 15))
            print(f"  【{i}】{h['score']:.3f} {bar} ({h['type']})")
            print(f"      📄 {h['source']}")
            print(f"      {h['text'][:100]}...")
        print()

    if result["skill_matches"]:
        print("🎯 Skill命中：")
        for s in result["skill_matches"][:3]:
            print(f"  【{s['name']}】score={s['score']:.1f} | 触发:{s['triggers_matched']} | 激活:{s['activates_nodes']}")
            print(f"     {s.get('description', '')}")
        print()

    if result.get("external_answer"):
        print("📡 外部知识结论:")
        print(f"  {result['external_answer'][:300]}")
        print()

    if result.get("team_results"):
        print("🔴 团队分析结果:")
        for tr in result["team_results"]:
            print(f"  【{tr['name']}】{tr['result'][:150]}...")
        print()

    print("💡 结论：")
    print(f"  {result['conclusion']}")
    print()