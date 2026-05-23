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
    "brain_hits": [...],
    "external_used": bool,
    "external_answer": str,
    "team_results": [...],
    "conclusion": str,
    "should_save": bool,
    "save_target": str,
    "thinking_steps": [...],
    "self_observation": {...},    # 新增：自我观测数据
    "working_memory": {...},       # 新增：工作记忆
  }
"""
import sys
import os
import re
import time
import json
import requests
from pathlib import Path
from datetime import datetime

sys_path = "/opt/data/scripts"
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)

BRAIN_DIR = Path("/opt/data/brain")
CACHE_FILE = Path("/tmp/brain_bm25_cache.json")
WORKING_MEMORY = BRAIN_DIR / "working_memory.json"
OBSERVATION_LOG = BRAIN_DIR / "self_observation.jsonl"

# ── Tier判断（增强版，减少误判）─────────────────────────────
TIER1_KEYWORDS = ["查看", "查", "剩多少", "看看", "有没有", "在不在", "多少", "哪个", "谁在", "帮我看", "现在"]
# "怎么/如何"只在开头时是tier1（直接问），中间出现是tier2（请求推荐/解决方案）
TIER3_KEYWORDS = ["设计", "架构", "方案", "哪个好", "权衡", "取舍", "漏洞", "攻击", "可行性", "新领域", "整体", "全局", "迁移", "重构", "颠覆"]
COMPLEX_KEYWORDS = ["为什么", "怎么", "如何", "是不是", "能不能", "是否应该", "分析", "原因", "原理", "思考", "区别", "推荐", "优化", "异常", "错误", "bug", "调试", "最佳实践", "最好", "策略", "方案", "报错", "失败", "问题", "搞不定", "不行", "不对"]
UNCERTAIN_KEYWORDS = ["不太确定", "不确定", "可能", "估计", "大概", "也许"]


def detect_tier(question: str, context: dict = None) -> int:
    """判断问题层级（增强版，减少误判）"""
    q = question.strip()
    ql = q.lower()

    # tier3优先判断（高风险/复杂问题）
    if any(kw in ql for kw in TIER3_KEYWORDS):
        return 3

    # 动作指令结果词列表（出现这些词=请求解决方案→tier2，不出现=tier1）
    result_words = ["解决", "修复", "部署", "配置", "实现", "优化", "设置", "分析", "诊断",
                    "调试", "排查", "重构", "迁移", "评估", "设计", "规划", "评估", "改造"]

    # tier1：动作指令开头 + 不含result_word → tier1
    action_starts = ["帮我", "查", "看", "找", "显示", "列出", "打开", "执行", "告诉我", "告我", "怎么", "如何", "为啥"]
    if any(q.startswith(kw) for kw in action_starts):
        # 包含result_word → tier2（请求解决方案）
        if any(rw in q for rw in result_words):
            return 2
        # 不含result_word → tier1（直接操作指令）
        return 1

    # tier1：极短问句(≤12字)且是查看类
    if len(q) <= 12 and any(kw in q for kw in ["查", "看", "问", "找"]):
        return 1

    # tier1：命令行类
    cmd_patterns = [r"^(ls|cat|ps|df|grep|find|curl|wget|git)\s", r"\b(ls|cat|ps|df)\b"]
    if any(re.search(p, ql) for p in cmd_patterns):
        return 1

    # tier2：包含思考类关键词
    if any(kw in q for kw in COMPLEX_KEYWORDS + UNCERTAIN_KEYWORDS):
        return 2

    # tier2：问题长度较长
    if len(q) > 40 or q.count(" ") > 8:
        return 2

    # tier2：包含问号
    if "?" in question or "？" in question:
        return 2

    # tier2：参考上下文
    if context and context.get("current_goal"):
        return 2

    return 1


def load_working_memory() -> dict:
    """加载工作记忆，自动从旧版迁移到新版"""
    if WORKING_MEMORY.exists():
        try:
            with open(WORKING_MEMORY) as f:
                old = json.load(f)
            # 旧版迁移（v1.0字段不同）
            new = {
                "current_goal": old.get("context", {}).get("current_topic") or "",
                "discussed_topics": [],
                "session_id": old.get("session", {}).get("id") or "",
                "last_updated": old.get("updated") or "",
                # 保留旧数据供诊断用
                "_legacy": old,
            }
            return new
        except Exception as e:
            print(f"load_working_memory警告: {e}，使用默认", file=sys.stderr)
    return {"current_goal": "", "discussed_topics": [], "session_id": "", "last_updated": ""}


def save_working_memory(wm: dict):
    """保存工作记忆"""
    wm["last_updated"] = datetime.now().isoformat()
    try:
        with open(WORKING_MEMORY, "w") as f:
            json.dump(wm, f, ensure_ascii=False, indent=2)
    except:
        pass


def log_observation(obs: dict):
    """记录自我观测日志"""
    try:
        with open(OBSERVATION_LOG, "a") as f:
            f.write(json.dumps(obs, ensure_ascii=False) + "\n")
    except:
        pass


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

    # 中英文分开提取：英文按\w+，中文每个字+两字词组
    en_terms = re.findall(r'[a-z0-9]+', question.lower())
    cn_chars = re.findall(r'[\u4e00-\u9fff]', question)
    # 两字中文词组
    cn_bigrams = [question[i:i+2] for i in range(len(question)-1)
                  if '\u4e00' <= question[i] <= '\u9fff' and '\u4e00' <= question[i+1] <= '\u9fff']
    terms = en_terms + cn_chars + cn_bigrams
    scored = []
    for chunk in chunks:
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
            # Ollama API返回NDJSON（每行一个JSON片段），需逐行拼接response
            lines = resp.text.strip().split('\n')
            return ''.join(
                json.loads(l).get('response', '') for l in lines if l.strip()
            )
    except:
        pass
    return ""


def team_delegate(question: str) -> list:
    """tier3团队派发（3个模型真实并行）"""
    import concurrent.futures

    tasks = [
        ("推理专家", "qwen2.5:3b-instruct-q4_K_M", f"简答：{question}"),
        ("工具专家", "qwen2.5:7b-instruct-q4_K_M", f"简答：{question}"),
        ("打工仔", "qwen2.5:3b-instruct-q4_K_M", f"简答：{question}"),
    ]

    results = []
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(call_ollama, prompt, model, 100, 30): (name, model)
            for name, model, prompt in tasks
        }
        done = False
        while not done:
            try:
                for future in concurrent.futures.as_completed(futures, timeout=45):
                    name, model = futures[future]
                    took = round((time.time() - start) * 1000)
                    try:
                        answer = future.result()
                        if answer:
                            results.append({
                                "model": name, "answer": answer[:200],
                                "took_ms": took, "success": True
                            })
                        else:
                            results.append({
                                "model": name, "answer": "", "took_ms": took, "success": False
                            })
                    except Exception as ex:
                        results.append({
                            "model": name, "answer": f"失败: {ex}", "took_ms": took, "success": False
                        })
                    if len(results) >= len(tasks):
                        done = True
                        break
            except concurrent.futures.TimeoutError:
                done = True  # 超时的直接放弃，继续返回已有结果
                break

    elapsed = time.time() - start
    # 记录自我观测
    log_observation({
        "time": datetime.now().isoformat(),
        "type": "tier3_delegate",
        "question": question[:100],
        "team_size": len(tasks),
        "results_count": len(results),
        "success_count": sum(1 for r in results if r.get("success")),
        "elapsed_sec": round(elapsed, 2),
    })
    return results


def update_working_memory(question: str, wm: dict):
    """更新工作记忆：从问题中提取上下文"""
    ql = question.lower()

    # 提取目标主题
    topic_markers = ["优化", "修复", "解决", "实现", "配置", "部署", "设计", "分析"]
    for marker in topic_markers:
        if marker in ql:
            idx = ql.index(marker)
            topic = question[max(0, idx-15):idx+20].strip()
            if wm["current_goal"] and topic not in wm["discussed_topics"]:
                if topic not in wm["discussed_topics"]:
                    wm["discussed_topics"].append(topic)
            elif not wm["current_goal"]:
                wm["current_goal"] = topic

    # 长度限制
    if len(wm["discussed_topics"]) > 10:
        wm["discussed_topics"] = wm["discussed_topics"][-10:]


def get_confidence_for_chunk(chunk_id: str) -> float:
    """
    返回知识块置信度（0.1-1.0）
    综合：base_conf × 时间衰减 + 使用次数加成 - 失败惩罚
    """
    CONF_FILE = BRAIN_DIR / "performance" / "confidence_tracking.json"
    if not CONF_FILE.exists():
        return 0.7

    conf_data = json.loads(CONF_FILE.read_text())
    if chunk_id not in conf_data:
        return 0.7  # 未知知识，保守估计

    c = conf_data[chunk_id]
    base = c["base_conf"]
    # 时间衰减：每天-1%，最低0.5
    try:
        age_days = (datetime.now() - datetime.fromisoformat(c.get("created", "2026-05-01"))).days
    except:
        age_days = 7
    decay = max(0.5, 1 - age_days * 0.01)
    conf = base * decay
    # 使用次数加成
    conf += min(0.1, c.get("times_used", 0) * 0.02)
    # 失败惩罚
    conf -= min(0.3, c.get("times_failed", 0) * 0.2)

    return round(min(1.0, max(0.1, conf)), 2)


def record_feedback(question: str, answer_summary: str, useful: bool,
                    source: str = "wechat", knowledge_used: list = None) -> dict:
    """
    记录用户反馈：有帮助→权重+1，无帮助→权重-1或标记需改进
    """
    FB_FILE = BRAIN_DIR / "performance" / "feedback_tracking.json"
    FB_FILE.parent.mkdir(parents=True, exist_ok=True)

    data = json.loads(FB_FILE.read_text()) if FB_FILE.exists() else {
        "feedbacks": [], "stats": {"total": 0, "useful": 0, "not_useful": 0}
    }

    entry = {
        "answer_id": f"ans_{int(time.time()*1000)}",
        "question": question[:200],
        "answer_summary": answer_summary[:200],
        "feedback": "useful" if useful else "not_useful",
        "source": source,
        "result": "positive" if useful else "negative",
        "used_knowledge": knowledge_used or [],
        "timestamp": datetime.now().isoformat(),
    }
    data["feedbacks"].append(entry)
    data["stats"]["total"] += 1
    if useful:
        data["stats"]["useful"] += 1
    else:
        data["stats"]["not_useful"] += 1

    FB_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    # 同步更新neural connections权重
    NEURAL_FILE = BRAIN_DIR / "neural" / "connections.json"
    if knowledge_used and NEURAL_FILE.exists():
        try:
            nd = json.loads(NEURAL_FILE.read_text())
            for kb in knowledge_used:
                for conn in nd.get("connections", []):
                    if kb in str(conn.get("source", "")) or kb in str(conn.get("target", "")):
                        conn["weight"] = conn.get("weight", 1.0) + (1 if useful else -0.5)
                        conn["hit_count"] = conn.get("hit_count", 0) + 1
                        conn["last_used"] = datetime.now().isoformat()[:10]
            json.dump(nd, open(NEURAL_FILE, "w"), ensure_ascii=False, indent=2)
        except:
            pass

    rate = data["stats"]["useful"] / max(1, data["stats"]["total"])
    return {"recorded": True, "total": data["stats"]["total"], "useful_rate": round(rate, 2)}


def recommend_skills(question: str, brain_hits: list = None) -> list:
    """
    基于问题+检索结果推荐相关skills
    规则：关键词匹配 → 返回对应skill列表
    """
    SKILL_MAP = {
        "ollama": ["ollama-model-manager", "ollama-brain-teacher"],
        "模型": ["ollama-model-manager", "ollama-auto-learning"],
        "brain": ["brain-retriever", "brain-system-maintenance"],
        "知识": ["brain-retriever", "knowledge-box-retrieval"],
        "检索": ["brain-retriever", "knowledge-box-retrieval"],
        "视频": ["ai-video-factory", "douyin-video-pipeline"],
        "制作": ["ai-video-factory"],
        "docker": ["synology-nas-container-debugging"],
        "容器": ["synology-nas-container-debugging"],
        "nas": ["synology-nas-container-debugging"],
        "学习": ["auto-learning", "ollama-auto-learning"],
        "arxiv": ["arxiv", "arxiv-nvd-cve-scraper"],
        "安全": ["arxiv-nvd-cve-scraper"],
        "cve": ["arxiv-nvd-cve-scraper"],
        "调试": ["ollama-auto-learning-debug", "systematic-debugging"],
        "bug": ["systematic-debugging"],
        "memory": ["hermes-long-term-memory", "memory-compression"],
        "记忆": ["hermes-long-term-memory"],
        "session": ["session-history-recovery"],
        "代码": ["codex", "claude-code"],
        "架构": ["architecture-diagram", "brain-team-architecture"],
        "设计": ["brain-team-architecture"],
        "创作": ["creative-ideation", "songwriting-and-ai-music"],
        "音乐": ["songwriting-and-ai-music"],
        "笔记": ["obsidian"],
    }

    ql = question.lower()
    rec = []
    for kw, skills in SKILL_MAP.items():
        if kw in ql:
            for s in skills:
                if s not in rec:
                    rec.append(s)

    # 如果brain命中了特定内容，也推荐相关skill
    if brain_hits:
        hit_texts = " ".join(h.get("text", "").lower() for h in brain_hits)
        for kw, skills in SKILL_MAP.items():
            if kw in hit_texts and kw not in ql:
                for s in skills:
                    if s not in rec:
                        rec.append(s)

    return rec


def brain_think(question: str, tier: int = None, timeout: int = 90,
                save_to_brain: bool = True) -> dict:
    """
    核心入口：思考引擎 v2.0
    自动判断层级 → 检索brain → 按需外部获取/团队派发 → 自我观测 → 返回结论
    """
    start_time = time.time()
    wm = load_working_memory()
    tier = tier or detect_tier(question, wm)
    tier_names = {1: "⚡快速通道", 2: "🧠思考通道", 3: "🔴团队协作"}

    result = {
        "question": question,
        "tier": tier,
        "tier_name": tier_names.get(tier, "思考通道"),
        "brain_hits": [],
        "brain_hit_count": 0,
        "brain_max_score": 0.0,
        "external_used": False,
        "external_answer": "",
        "team_results": [],
        "conclusion": "",
        "should_save": False,
        "save_target": "",
        "thinking_steps": [],
        "self_observation": {},
        "working_memory": wm,
        "recommended_skills": [],
        "confidence": 0.0,
    }

    # ── Tier 1: 直接回答（不检索）─────────────────────────────
    if tier == 1:
        result["thinking_steps"].append("【tier1】简单任务，直接执行")
        result["conclusion"] = "[tier1快速响应]"
        elapsed = time.time() - start_time
        result["self_observation"] = {
            "elapsed_ms": round(elapsed * 1000),
            "tier": 1,
            "skipped_brain": True,
            "reason": "tier1简单问题，跳过检索",
        }
        log_observation({
            "time": datetime.now().isoformat(),
            "type": "tier1_response",
            "question": question[:100],
            "elapsed_ms": round(elapsed * 1000),
        })
        return result

    # ── Tier 2 & 3: 检索brain ────────────────────────────────
    result["thinking_steps"].append(f"【tier{tier}】检索brain...")
    brain_hits = search_brain(question)
    result["brain_hits"] = brain_hits
    result["brain_hit_count"] = len(brain_hits)
    result["brain_max_score"] = brain_hits[0]["score"] if brain_hits else 0.0

    has_enough = len(brain_hits) > 0 and brain_hits[0]["score"] >= 5

    # tier3 跳过外部获取，直接走团队协作（外部查询太慢，不值得等）
    if tier == 3:
        result["thinking_steps"].append(
            f"  【tier3优先】跳过外部查询，直接启动团队分析..."
        )
    elif has_enough:
        result["thinking_steps"].append(
            f"  ✅ brain命中{len(brain_hits)}条，最高分{brain_hits[0]['score']}"
        )
        log_observation({
            "time": datetime.now().isoformat(),
            "type": "brain_hit",
            "question": question[:100],
            "tier": tier,
            "hit_count": len(brain_hits),
            "max_score": brain_hits[0]["score"],
        })
    else:
        result["thinking_steps"].append(
            f"  ⚠️ brain命中{len(brain_hits)}条(最高{brain_hits[0]['score'] if brain_hits else 0})，触发外部获取..."
        )
        ext_answer = fetch_external(question)
        if ext_answer:
            result["external_used"] = True
            result["external_answer"] = ext_answer
            result["thinking_steps"].append("  ✅ 外部知识获取成功")
            log_observation({
                "time": datetime.now().isoformat(),
                "type": "external_fetch",
                "question": question[:100],
                "tier": tier,
                "had_brain_hits": len(brain_hits),
            })
        else:
            result["thinking_steps"].append("  ⚠️ 外部获取无结果")
            log_observation({
                "time": datetime.now().isoformat(),
                "type": "no_answer",
                "question": question[:100],
                "tier": tier,
            })

    # ── Tier 3: 团队派发（真实并行）──────────────────────────
    if tier == 3:
        result["thinking_steps"].append("【tier3】启动团队协作...")
        team = team_delegate(question)
        result["team_results"] = team
        result["thinking_steps"].append(f"  → 收到{len(team)}个视角的分析")
        # 汇总团队结论
        good = [t for t in team if t.get("success") and t.get("answer")]
        if good:
            result["conclusion"] = "【团队共识】" + " | ".join(
                f"{t['model']}：{t['answer'][:120]}" for t in good[:3]
            )

    # ── 生成结论 ───────────────────────────────────────────
    if result["external_answer"]:
        result["conclusion"] = result["external_answer"][:500]
    elif brain_hits:
        result["conclusion"] = f"brain检索到相关知识({len(brain_hits)}条)，详见下方"
    else:
        result["conclusion"] = "无相关记录，建议手动查询"

    # ── 知识沉淀建议 ────────────────────────────────────────
    if result["external_used"] and result["external_answer"]:
        result["should_save"] = True
        today = datetime.now().strftime("%Y%m%d")
        result["save_target"] = f"brain/scenarios/external_learn_{today}.md"
        result["thinking_steps"].append("💾 建议沉淀到brain")

    # ── 更新工作记忆 ────────────────────────────────────────
    update_working_memory(question, wm)
    save_working_memory(wm)
    result["working_memory"] = wm

    # ── 自我观测总览 ────────────────────────────────────────
    elapsed = time.time() - start_time
    result["self_observation"] = {
        "elapsed_ms": round(elapsed * 1000),
        "tier": tier,
        "brain_hit_count": len(brain_hits),
        "brain_max_score": result["brain_max_score"],
        "external_used": result["external_used"],
        "team_results_count": len(result["team_results"]),
        "should_save": result["should_save"],
        "working_memory_updated": bool(wm.get("current_goal")),
    }

    # 自我观测：完整记录
    log_observation({
        "time": datetime.now().isoformat(),
        "type": "brain_think_complete",
        "question": question[:100],
        "tier": tier,
        "brain_hits": len(brain_hits),
        "max_score": result["brain_max_score"],
        "external": result["external_used"],
        "team": len(result["team_results"]),
        "elapsed_ms": round(elapsed * 1000),
    })

    return result


# ── CLI模式（测试用）────────────────────────────────────────
if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Python异常处理方法"
    print(f"\n🧠 brain_think v2.0: {q}\n")
    r = brain_think(q)
    print(f"层级: {r['tier_name']}")
    print(f"brain命中: {r['brain_hit_count']}条 (最高{r['brain_max_score']})")
    print(f"外部获取: {'是' if r['external_used'] else '否'}")
    if r['team_results']:
        print(f"团队分析: {len(r['team_results'])}个视角")
    if r.get('working_memory', {}).get('current_goal'):
        print(f"工作记忆目标: {r['working_memory']['current_goal']}")
    print(f"耗时: {r['self_observation']['elapsed_ms']}ms")
    print(f"结论: {r['conclusion'][:200]}")
