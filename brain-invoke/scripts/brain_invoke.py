#!/usr/bin/env python3
"""
brain_thinker 轻量包装 - 让外部脚本/agent快速调用思考引擎
================================================================
用法:
  from brain_invoke import brain_think
  result = brain_think("你的问题")  # 自动判断tier
  
  from brain_invoke import brain_think
  result = brain_think("你的问题", tier=2)  # 强制指定层级

返回结构:
  {
    "tier": 1/2/3,
    "tier_name": "快速通道/思考通道/团队协作",
    "brain_hits": [...],          # brain检索结果
    "external_used": bool,         # 是否触发了外部获取
    "external_answer": str,        # 外部知识结论
    "team_results": [...],         # tier3团队分析结果
    "conclusion": str,             # 最终结论
    "should_save": bool,           # 是否建议沉淀
    "save_target": str,            # 建议沉淀路径
    "thinking_steps": [...],       # 思考步骤日志
  }
"""
import sys
import os
import re
import time
import json
import requests
from pathlib import Path

sys_path = "/opt/data/scripts"
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)

BRAIN_DIR = Path("/opt/data/brain")
CACHE_FILE = Path("/tmp/brain_bm25_cache.json")

# ── Tier判断（与brain_thinker.py同步）───────────────────────
TIER1_KEYWORDS = ["查看", "查", "剩多少", "看看", "有没有", "在不在", "多少", "哪个", "谁在"]
COMPLEX_KEYWORDS = ["为什么", "怎么", "如何", "是不是", "能不能", "是否应该", "分析", "原因", "原理"]
UNCERTAIN_KEYWORDS = ["不太确定", "不确定", "可能", "估计", "大概", "也许"]


def detect_tier(question: str) -> int:
    """判断问题层级"""
    q = question.strip()
    if any(q.startswith(kw) for kw in ["查", "看", "问", "告我", "帮我找"]):
        return 1
    if any(kw in q[:10] for kw in TIER1_KEYWORDS):
        return 1
    if any(kw in q for kw in COMPLEX_KEYWORDS + UNCERTAIN_KEYWORDS):
        return 2
    if len(q) > 50 or q.count(" ") > 8:
        return 2
    return 1


def load_brain_cache():
    """加载brain缓存"""
    if not CACHE_FILE.exists():
        return []
    try:
        with open(CACHE_FILE) as f:
            data = json.load(f)
        return data.get("chunks", [])
    except:
        return []


def search_brain(question: str, top_k: int = 5) -> list:
    """BM25检索brain"""
    chunks = load_brain_cache()
    if not chunks:
        return []
    
    terms = re.findall(r'[\w]{2,}', question.lower())
    scored = []
    for chunk in chunks:
        # chunk可能是字符串或字典
        if isinstance(chunk, dict):
            text = chunk.get("text", "").lower()
            source = chunk.get("source", "")
            chunk_type = chunk.get("type", "")
        else:
            text = str(chunk).lower()
            source = ""
            chunk_type = ""
        
        score = sum(1 for t in terms if t in text)
        if score > 0:
            scored.append((score, text[:200], source, chunk_type))
    
    scored.sort(reverse=True)
    return [{"score": s, "text": t, "source": src, "type": typ}
            for s, t, src, typ in scored[:top_k]]


def fetch_external(question: str) -> str:
    """外部知识获取（带超时保护）"""
    try:
        from external_fetcher import fetch_and_learn
        result = fetch_and_learn(question)
        return result.get("answer", "")
    except Exception as e:
        return f"[外部获取失败: {e}]"


def call_ollama(prompt: str, model: str = "qwen2.5:3b-instruct-q4_K_M", 
                num_predict: int = 200, timeout: int = 60) -> str:
    """调用Ollama（带超时保护）"""
    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, 
                  "options": {"num_predict": num_predict}},
            timeout=timeout
        )
        if resp.status_code == 200:
            return json.loads(resp.text).get("response", "")
    except:
        pass
    return ""


def team_delegate(question: str) -> list:
    """tier3团队派发（3个模型并行）"""
    import concurrent.futures
    
    tasks = [
        ("推理专家", "deepseek-r1:7b", f"深入分析并推理：{question}"),
        ("工具专家", "qwen2.5:7b-instruct-q4_K_M", f"从实际执行角度分析：{question}"),
        ("打工仔", "qwen2.5:3b-instruct-q4_K_M", f"从事实数据角度分析：{question}"),
    ]
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(call_ollama, prompt, model, 150, 60): name
            for name, model, prompt in tasks
        }
        for future in concurrent.futures.as_completed(futures, timeout=90):
            name = futures[future]
            try:
                result = future.result()
                if result:
                    results.append({"name": name, "result": result[:200]})
            except:
                pass
    return results


def brain_think(question: str, tier: int = None, timeout: int = 90) -> dict:
    """
    核心入口：思考引擎
    自动判断层级 → 检索brain → 按需外部获取/团队派发 → 返回结论
    """
    tier = tier or detect_tier(question)
    tier_names = {1: "⚡快速通道", 2: "🧠思考通道", 3: "🔴团队协作"}
    
    result = {
        "question": question,
        "tier": tier,
        "tier_name": tier_names.get(tier, "思考通道"),
        "brain_hits": [],
        "external_used": False,
        "external_answer": "",
        "team_results": [],
        "conclusion": "",
        "should_save": False,
        "save_target": "",
        "thinking_steps": [],
    }
    
    # Tier 1: 直接回答
    if tier == 1:
        result["thinking_steps"].append("【tier1】简单任务，直接执行")
        result["conclusion"] = "[tier1快速响应]"
        return result
    
    # Tier 2 & 3: 检索brain
    result["thinking_steps"].append(f"【tier{tier}】检索brain...")
    brain_hits = search_brain(question)
    result["brain_hits"] = brain_hits
    
    has_enough = len(brain_hits) > 0 and brain_hits[0]["score"] > 5
    
    if has_enough:
        result["thinking_steps"].append(f"  ✅ brain命中{len(brain_hits)}条，最高分{brain_hits[0]['score']}")
    else:
        result["thinking_steps"].append("  ⚠️ brain无相关记录，触发外部获取...")
        ext_answer = fetch_external(question)
        if ext_answer:
            result["external_used"] = True
            result["external_answer"] = ext_answer
            result["thinking_steps"].append("  ✅ 外部知识获取成功")
        else:
            result["thinking_steps"].append("  ⚠️ 外部获取无结果")
    
    # Tier 3: 团队派发
    if tier == 3:
        result["thinking_steps"].append("【tier3】启动团队协作...")
        team = team_delegate(question)
        result["team_results"] = team
        result["thinking_steps"].append(f"  → 收到{len(team)}个视角的分析")
    
    # 生成结论
    if result["external_answer"]:
        result["conclusion"] = result["external_answer"][:500]
    elif brain_hits:
        result["conclusion"] = f"brain检索到相关知识({len(brain_hits)}条)，详见下方"
    else:
        result["conclusion"] = "无相关记录，建议手动查询"
    
    # 知识沉淀建议
    if result["external_used"] and result["external_answer"]:
        result["should_save"] = True
        from datetime import datetime
        today = datetime.now().strftime("%Y%m%d")
        result["save_target"] = f"brain/scenarios/external_learn_{today}.md"
        result["thinking_steps"].append("💾 建议沉淀到brain")
    
    return result


# ── CLI模式（测试用）────────────────────────────────────────
if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Python异常处理方法"
    print(f"\n🧠 brain_think: {q}\n")
    r = brain_think(q)
    print(f"层级: {r['tier_name']}")
    print(f"brain命中: {len(r['brain_hits'])}条")
    print(f"外部获取: {'是' if r['external_used'] else '否'}")
    if r['team_results']:
        print(f"团队分析: {len(r['team_results'])}个视角")
    print(f"结论: {r['conclusion'][:200]}")
