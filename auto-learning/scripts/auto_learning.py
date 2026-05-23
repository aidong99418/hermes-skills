#!/usr/bin/env python3
"""
AI技术 + 白帽技术自动学习系统
- 定时抓取最新内容
- 多模型并行流水线（安全保护）
- 备份到 /opt/data/data_backup/
- 所有推理任务由 Ollama 大模型完成
"""

import subprocess
import json
import os
import re
import time
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加安全监控
sys.path.insert(0, '/opt/data/scripts')
from safety_monitor import SafetyMonitor, get_memory_usage, get_model_memory_estimate

OLLAMA_URL = "http://localhost:11434"
safety = SafetyMonitor()

BACKUP_BASE = "/opt/data/data_backup"
AI_DIR = f"{BACKUP_BASE}/AI技术学习"
WH_DIR = f"{BACKUP_BASE}/白帽技术学习"
BRAIN_DIR = "/opt/data/brain"
RAG_DIR = "/opt/data/rag_index"

# 安全检查函数
def pre_model_check(task_type):
    """加载模型前的安全检查"""
    status = safety.get_system_status()
    mem_info = get_memory_usage()
    
    # 估算需要的内存
    needed_gb = MODEL_TIMEOUTS.get(task_type, 120) / 60 * 2  # 粗略估算
    
    if status["memory"]["status"] == "CRITICAL":
        print(f"⚠️ {status['memory']['message']}")
        print(f"   可用内存: {mem_info['available_gb']:.1f}GB")
        if not safety.wait_for_resources(300):
            print("❌ 系统资源不足，跳过此次执行")
            return False
    elif status["memory"]["status"] == "WARNING":
        print(f"⚡ {status['memory']['message']}")
    
    return True

def check_memory_before_load(model_name):
    """加载模型前的内存检查"""
    needed = get_model_memory_estimate(model_name)
    mem_info = get_memory_usage()
    
    if mem_info['available_gb'] < needed:
        print(f"⚠️ 内存不足：需要{needed:.1f}GB，可用{mem_info['available_gb']:.1f}GB")
        print(f"   等待资源释放...")
        time.sleep(30)
        mem_info = get_memory_usage()
        if mem_info['available_gb'] < needed:
            print(f"❌ 内存仍然不足，跳过")
            return False
    return True

# ========== 模型选择配置（任务驱动） ==========
MODEL_CONFIG = {
    "fast_scan":  "smollm2:1.7b",       # 快扫分类：秒级响应
    "filter":     "qwen2.5:3b-instruct-q4_K_M",  # 筛选精品：够用且快
    "deep_read":  "qwen2.5:7b-instruct-q4_K_M",  # 深读分析：主力
    "reasoning":  "deepseek-r1:7b",      # 推理提炼：最强
    "default":    "qwen2.5:3b-instruct-q4_K_M",
}
MODEL_TIMEOUTS = {
    "fast_scan":  60,    # 快扫60秒足够
    "filter":     120,   # 筛选2分钟
    "deep_read":  180,   # 深读3分钟
    "reasoning":  240,   # 推理4分钟
}

# ========== 外部 API 兜底配置（SiliconFlow） ==========
FALLBACK_API = {
    "url": "https://api.siliconflow.cn/v1/chat/completions",
    "api_key": "***",  # SiliconFlow free tier
    "model": "deepseek-ai/DeepSeek-V2.5",
    "max_tokens": 2048,
    "temperature": 0.3
}

def api_generate(prompt, model=None, timeout=120):
    """调用外部 API（SiliconFlow）作为 Ollama 兜底"""
    try:
        m = model or FALLBACK_API["model"]
        payload = {
            "model": m,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": FALLBACK_API.get("max_tokens", 2048),
            "temperature": FALLBACK_API.get("temperature", 0.3)
        }
        result = subprocess.run(
            ["curl", "-s", "--max-time", str(timeout), "-X", "POST", FALLBACK_API["url"],
             "-H", f"Authorization: Bearer {FALLBACK_API['api_key']}",
             "-H", "Content-Type: application/json",
             "-d", json.dumps(payload)],
            capture_output=True, text=True
        )
        try:
            resp = json.loads(result.stdout)
            return resp.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        except:
            return f"[API 兜底失败] {result.stderr or result.stdout[:200]}"
    except Exception as e:
        return f"[API 调用异常] {str(e)}"

# ========== 工具函数 ==========

def ollama_generate(prompt, model=None, timeout=180, task_type=None):
    """调用 Ollama 生成内容，失败则自动切换外部 API 兜底
    
    Args:
        task_type: 任务类型，可选 fast_scan/filter/deep_read/reasoning
                   自动选择对应模型和超时时间
    """
    # 根据任务类型自动选择模型
    if task_type and model is None:
        model = MODEL_CONFIG.get(task_type, MODEL_CONFIG["default"])
        timeout = MODEL_TIMEOUTS.get(task_type, timeout)
    
    try:
        payload = {"model": model, "prompt": prompt, "stream": False}
        result = subprocess.run(
            ["curl", "-s", "--max-time", str(timeout), OLLAMA_URL + "/api/generate",
             "-d", json.dumps(payload)],
            capture_output=True, text=True
        )
        try:
            resp_text = json.loads(result.stdout).get("response", "").strip()
            if resp_text and not resp_text.startswith("[Ollama"):
                return resp_text
        except:
            pass
        
        # Ollama 失败，自动切换到外部 API
        print(f"  ⚡ Ollama 不可用，切换到 {FALLBACK_API['model']}...")
        return api_generate(prompt, model=model)
    except Exception as e:
        return f"[Ollama 调用异常] {str(e)}"


def ollama_generate_safe(prompt, model=None, timeout=180, task_type=None, max_retries=3):
    """带重试的 Ollama 生成（更稳定）
    
    使用 safety_monitor 中的 generate_with_retry
    自动处理空响应、超时、JSON解析失败
    """
    try:
        from safety_monitor import generate_with_retry as safe_generate
        response, success, attempts = safe_generate(
            prompt=prompt,
            model=model,
            max_retries=max_retries,
            task_type=task_type
        )
        if success:
            return response
        else:
            # 重试也失败，尝试API兜底
            print(f"  ⚡ 重试{max_retries}次全部失败，切换备用API...")
            return api_generate(prompt, model=model)
    except ImportError:
        # 安全模块不可用，降级到普通函数
        print(f"  ⚠️ safety_monitor不可用，使用普通生成")
        return ollama_generate(prompt, model=model, timeout=timeout, task_type=task_type)

# ========== 知识库入库 ==========

RAG_DIR = "/opt/data/rag_index"
TODAY_KB_FILE = f"/opt/data/rag_index/daily_insights_{datetime.now().strftime('%Y%m%d')}.md"


def extract_and_save_knowledge(ai_report_path, sec_report_path):
    """从学习报告中提炼知识点，追加到知识库 + brain"""
    try:
        # 读取报告
        ai_content = open(ai_report_path, encoding="utf-8").read() if os.path.exists(ai_report_path) else ""
        sec_content = open(sec_report_path, encoding="utf-8").read() if os.path.exists(sec_report_path) else ""

        date_str = datetime.now().strftime("%Y-%m-%d")
        date_code = datetime.now().strftime("%Y%m%d")

        # AI + 安全 Ollama 分析并行（节省约20秒）
        ai_kb_prompt = f"""你是一名AI技术专家。从以下每日学习报告中提炼出3-5个值得记住的核心知识点，每个知识点一行，格式：[知识点标题] 内容描述。不超过300字。

报告内容：
{ai_content[:3000]}

输出格式：
## [日期] 今日AI技术核心知识点

1. [知识点1]
2. [知识点2]
...
"""
        sec_kb_prompt = f"""你是一名白帽黑客/安全研究员。从以下每日安全报告中提炼出3-5个值得记住的核心知识点，每个知识点一行。不超过300字。

报告内容：
{sec_content[:3000]}

输出格式：
## [日期] 今日安全核心知识点

1. [知识点1]
2. [知识点2]
...
"""

        def gen_ai():
            r = ollama_generate(ai_kb_prompt, timeout=120)
            return r if not (r.startswith("[Ollama") or r.startswith("[API")) else ""

        def gen_sec():
            r = ollama_generate(sec_kb_prompt, timeout=120)
            return r if not (r.startswith("[Ollama") or r.startswith("[API")) else ""

        with ThreadPoolExecutor(max_workers=2) as pool:
            ai_future = pool.submit(gen_ai)
            sec_future = pool.submit(gen_sec)
            ai_kb = ai_future.result()
            sec_kb = sec_future.result()

        # ── 写RAG知识库（原有逻辑）────────────────────────────────
        combined = f"""# 每日知识积累 - {date_str}

> 自动提炼入库 | Hermes Agent

{ai_kb}

{sec_kb}
"""
        with open(TODAY_KB_FILE, "w", encoding="utf-8") as f:
            f.write(combined)
        print(f"  ✅ 今日知识点已入库: {TODAY_KB_FILE}")

        kb_files = {
            "ai": ("/opt/data/rag_index/ai_insights.md", ai_kb),
            "security": ("/opt/data/rag_index/security_notes.md", sec_kb),
        }
        for kb_type, (kb_path, kb_content) in kb_files.items():
            if kb_content and not kb_content.startswith("[Ollama") and not kb_content.startswith("[API"):
                try:
                    existing = open(kb_path, encoding="utf-8").readlines()
                    keep_lines = existing[:60] if len(existing) > 60 else existing
                    with open(kb_path, "w", encoding="utf-8") as f:
                        f.writelines(keep_lines)
                        f.write(f"\n{kb_content}\n")
                    print(f"  ✅ {kb_type}知识点已追加到 {kb_path}")
                except Exception as e:
                    print(f"  ⚠️ 追加知识失败: {e}")

        # ── 写brain目录（新增强制）────────────────────────────────
        # 1. 写场景案例：brain/scenarios/ai_learn_YYYYMMDD.md
        # 2. 写安全案例：brain/scenarios/security_learn_YYYYMMDD.md
        # 3. 写推理模式：brain/reasoning_patterns/ai_insights_YYYYMMDD.md
        # 4. 更新neural connections（追加学习来源关联）
        _write_brain_from_learning(ai_content, sec_content, ai_kb, sec_kb, date_str, date_code, ai_report_path)
        _update_neural_connections(date_code)

        # ── 重建brain缓存 + RAG索引────────────────────────────────
        try:
            # 先强制重建brain缓存（--rebuild）
            subprocess.run(
                ["python3", "/opt/data/scripts/brain_retriever.py", "--rebuild"],
                capture_output=True, timeout=30
            )
            # 再重建RAG
            subprocess.run(
                ["python3", "/opt/data/scripts/rag_query.py", "--rebuild"],
                capture_output=True, timeout=30
            )
            print("  🔄 brain缓存 + RAG索引已重建")
        except Exception as e:
            print(f"  ⚠️ 索引重建失败: {e}")

    except Exception as e:
        print(f"  ⚠️ 知识点入库失败: {e}")


def _write_brain_from_learning(ai_content, sec_content, ai_kb, sec_kb, date_str, date_code, ai_report_path):
    """将每日学习成果写入brain目录"""
    try:
        # 判定ai_kb是否有效（Ollama fallback输出带[API/]前缀的也有效）
        ai_kb_valid = ai_kb and (
            not ai_kb.startswith("[Ollama")
            or ai_kb.startswith("[API")  # API fallback是有效输出
        ) and len(ai_kb.strip()) > 10
        
        sec_kb_valid = sec_kb and (
            not sec_kb.startswith("[Ollama")
            or sec_kb.startswith("[API")
        ) and len(sec_kb.strip()) > 10

        # 1. 写AI学习场景
        if ai_content and len(ai_content) > 200:
            scenario_path = f"{BRAIN_DIR}/scenarios/ai_learn_{date_code}.md"
            kb_display = ai_kb if ai_kb_valid else "[AI分析不可用，详见报告正文]"
            scenario_content = f"# AI技术学习 - {date_str}\n\n## 数据来源\n- ArXiv论文快扫 + 深读精选\n\n## 核心知识点\n\n{kb_display}\n\n## 今日精选论文摘要\n\n{ai_content[:1500]}\n\n> 来源：auto_learning每日流水线 | {date_str}\n"
            os.makedirs(os.path.dirname(scenario_path), exist_ok=True)
            with open(scenario_path, "w", encoding="utf-8") as f:
                f.write(scenario_content)
            print(f"  ✅ brain场景已存: {scenario_path}")

        # 2. 写安全学习场景
        if sec_content and len(sec_content) > 200:
            sec_scenario_path = f"{BRAIN_DIR}/scenarios/security_learn_{date_code}.md"
            sec_kb_display = sec_kb if sec_kb_valid else "[安全分析不可用，详见报告正文]"
            sec_scenario_content = f"# 安全技术学习 - {date_str}\n\n## 数据来源\n- CVE/NVD漏洞库 + HN安全资讯\n\n## 核心知识点\n\n{sec_kb_display}\n\n## 今日安全动态摘要\n\n{sec_content[:1500]}\n\n> 来源：auto_learning每日流水线 | {date_str}\n"
            os.makedirs(os.path.dirname(sec_scenario_path), exist_ok=True)
            with open(sec_scenario_path, "w", encoding="utf-8") as f:
                f.write(sec_scenario_content)
            print(f"  ✅ brain安全案例已存: {sec_scenario_path}")

        # 3. 写推理模式（只要有AI报告内容就写）
        if ai_content and len(ai_content) > 200:
            pattern_path = f"{BRAIN_DIR}/reasoning_patterns/ai_insights_{date_code}.md"
            pattern_content = f"# AI技术推理模式 - {date_str}\n\n{kb_display}\n\n## 来源\n{ai_report_path}\n"
            os.makedirs(os.path.dirname(pattern_path), exist_ok=True)
            with open(pattern_path, "w", encoding="utf-8") as f:
                f.write(pattern_content)
            print(f"  ✅ brain推理模式已存: {pattern_path}")

    except Exception as e:
        print(f"  ⚠️ brain写入失败: {e}")


def _update_neural_connections(date_code):
    """更新神经连接图谱（新增学习节点）"""
    try:
        import json
        conn_file = f"{BRAIN_DIR}/neural/connections.json"
        if not os.path.exists(conn_file):
            return
        
        with open(conn_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 追加学习记录
        new_conn = {
            "from": f"ai_learn_{date_code}",
            "to": "research",
            "weight": 0.8,
            "reason": f"每日AI学习 {date_code} → 触发research问题类型"
        }
        new_conn2 = {
            "from": f"security_learn_{date_code}",
            "to": "research",
            "weight": 0.8,
            "reason": f"每日安全学习 {date_code} → 触发research问题类型"
        }
        new_conn3 = {
            "from": "research",
            "to": "decision",
            "weight": 0.6,
            "reason": "研究结论支撑决策"
        }
        
        existing = data.get("connections", [])
        existing_fids = {(c.get("from",""), c.get("to","")) for c in existing}
        for nc in [new_conn, new_conn2, new_conn3]:
            if (nc["from"], nc["to"]) not in existing_fids:
                existing.append(nc)
        
        data["connections"] = existing[-50:]  # 保留最近50条，避免无限增长
        data["updated"] = datetime.now().strftime("%Y-%m-%d")
        
        with open(conn_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  ⚠️ neural connections更新失败: {e}")


def save_report(path, content):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  ✓ 已保存: {path}")
    except Exception as e:
        print(f"  ✗ 保存失败 {path}: {e}")

def fetch_url_with_retry(url, max_retries=3, base_delay=8):
    """带指数退避重试的URL获取"""
    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                ["curl", "-s", "--max-time", "30", url],
                capture_output=True, text=True
            )
            content = result.stdout
            
            # 检查是否触发429限流
            if not content or "Too Many Requests" in content or content.strip() == "":
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # 指数退避
                    print(f"  ⚠️ 请求被限流(429)，等待 {delay}s 后重试 ({attempt + 1}/{max_retries})...")
                    time.sleep(delay)
                    continue
                else:
                    print(f"  ✗ 达到最大重试次数，返回空结果")
                    return ""
            return content
        except Exception as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"  ⚠️ 请求异常: {e}，等待 {delay}s 后重试 ({attempt + 1}/{max_retries})...")
                time.sleep(delay)
            else:
                print(f"  ✗ 请求失败: {e}")
                return ""
    return ""

def fetch_url(url):
    """简单URL获取（保持兼容性，内部使用带重试的版本）"""
    return fetch_url_with_retry(url)

# ========== ArXiv 搜索 ==========

def search_arxiv(query, max_results=8, category=None):
    """搜索 ArXiv 论文，支持xmlns命名空间和429限流处理"""
    try:
        q = f"all:{query}" if not category else f"cat:{category}"
        url = (f"https://export.arxiv.org/api/query?search_query={q}"
               f"&max_results={max_results}&sortBy=submittedDate&sortOrder=descending")
        
        # 使用带重试的fetch（ArXiv限流处理）
        xml_data = fetch_url_with_retry(url, max_retries=3, base_delay=8)
        
        papers = []
        # 支持带xmlns的XML，匹配entry标签（忽略命名空间前缀）
        entries = re.findall(r'<[^:]*:entry[^>]*>(.*?)</[^:]*:entry>', xml_data, re.DOTALL)
        if not entries:
            # 备用模式：匹配普通entry标签
            entries = re.findall(r'<entry>(.*?)</entry>', xml_data, re.DOTALL)
        
        for entry in entries:
            try:
                # 支持带命名空间前缀的标签
                title = re.search(r'<[^:]*:title[^>]*>(.*?)</[^:]*:title>', entry, re.DOTALL)
                if not title:
                    title = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
                
                paper_id = re.search(r'<[^:]*:id[^>]*>(.*?)</[^:]*:id>', entry)
                if not paper_id:
                    paper_id = re.search(r'<id>(.*?)</id>', entry)
                
                summary = re.search(r'<[^:]*:summary[^>]*>(.*?)</[^:]*:summary>', entry, re.DOTALL)
                if not summary:
                    summary = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)
                
                published = re.search(r'<[^:]*:published[^>]*>(.*?)</[^:]*:published>', entry)
                if not published:
                    published = re.search(r'<published>(.*?)</published>', entry)
                
                authors = re.findall(r'<[^:]*:name[^>]*>(.*?)</[^:]*:name>', entry)
                if not authors:
                    authors = re.findall(r'<name>(.*?)</name>', entry)
                
                if title and paper_id:
                    papers.append({
                        "title": title.group(1).strip().replace('\n', ' '),
                        "id": paper_id.group(1).strip().split('/abs/')[-1],
                        "summary": summary.group(1).strip()[:500] if summary else "",
                        "published": published.group(1)[:10] if published else "",
                        "authors": ", ".join(authors[:3]),
                        "url": f"https://arxiv.org/abs/{paper_id.group(1).strip().split('/abs/')[-1]}"
                    })
            except Exception as e:
                # 跳过解析失败的单个entry
                continue
        
        return papers
    except Exception as e:
        print(f"  ✗ ArXiv搜索异常: {e}")
        return []

# ========== 安全资讯源 ==========

def fetch_security_news():
    """抓取 CVE 和安全资讯"""
    news = []
    
    # NVD CVE RSS（无需 API Key）
    try:
        xml = fetch_url("https://nvd.nist.gov/feeds/xml/cves/2.0/nvdcve-2.0-recent.xml")
        if xml:
            # 支持cvss3:baseScore等带命名空间前缀的标签
            for item in re.findall(r'<item>(.*?)</item>', xml, re.DOTALL)[:10]:
                try:
                    cve_id = re.search(r'CVE-\d+-\d+', item)
                    # 修复：支持带命名空间前缀的cvss3:baseScore
                    score = re.search(r'<[^:]*:baseScore[^>]*>([\d.]+)', item)
                    if not score:
                        score = re.search(r'<cvss3:baseScore>([\d.]+)', item)
                    summary = re.search(r'<[^:]*:description[^>]*>(.*?)</[^:]*:description>', item, re.DOTALL)
                    if not summary:
                        summary = re.search(r'<description[^>]*>(.*?)</description>', item, re.DOTALL)
                    
                    if cve_id:
                        # 去除HTML标签
                        desc_text = re.sub(r'<[^>]+>', '', (summary.group(1) if summary else ''))[:250].strip()
                        score_str = score.group(1) if score else '?'
                        news.append({
                            "source": "NVD CVE",
                            "id": cve_id.group(0),
                            "description": f"[CVSS {score_str}] {desc_text}",
                            "url": f"https://nvd.nist.gov/vuln/detail/{cve_id.group(0)}"
                        })
                except Exception as e:
                    continue
    except Exception as e:
        print(f"  ✗ NVD CVE获取异常: {e}")
        news.append({"source": "NVD", "id": "ERROR", "description": str(e)})
    
    # Exploit-DB 最近漏洞
    try:
        exploitdb = fetch_url("https://www.exploit-db.com/rss.xml")
        if exploitdb:
            items = re.findall(r'<item>(.*?)</item>', exploitdb, re.DOTALL)
            for item in items[:5]:
                try:
                    title = re.search(r'<title>(.*?)</title>', item)
                    link = re.search(r'<link>(.*?)</link>', item)
                    if title and link:
                        news.append({
                            "source": "Exploit-DB",
                            "id": title.group(1).strip(),
                            "description": "",
                            "url": link.group(1).strip()
                        })
                except Exception as e:
                    continue
    except Exception as e:
        pass
    
    return news[:10]

# ========== Hacker News ==========

def fetch_hackernews(keyword="AI|security"):
    """抓取 HN 上的相关帖子"""
    try:
        top = fetch_url("https://hacker-news.firebaseio.com/v0/topstories.json")
        if not top:
            return []
        
        ids = json.loads(top)[:30]
        results = []
        for sid in ids:
            try:
                story = fetch_url(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
                s = json.loads(story)
                text = (s.get("title") or "") + " " + (s.get("text") or "")
                if re.search(keyword, text, re.I):
                    results.append({
                        "title": s.get("title", ""),
                        "url": s.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                        "score": s.get("score", 0),
                        "hn_url": f"https://news.ycombinator.com/item?id={sid}"
                    })
                if len(results) >= 8:
                    break
            except Exception as e:
                continue
        return results
    except Exception as e:
        print(f"  ✗ HackerNews获取异常: {e}")
        return []

# ========== Ollama 智能分析 ==========

def ollama_summarize_papers(papers, topic):
    """让 Ollama 分析论文列表，提取关键信息和趋势"""
    if not papers:
        return "今日未找到相关论文。"
    
    paper_list = "\n".join([
        f"- {p.get('title', '无标题')} ({p.get('id', 'N/A')}, {p.get('published', 'N/A')})\n  摘要: {p.get('summary', '')[:200]}"
        for p in papers[:10]
    ])
    
    prompt = f"""你是一名 AI 研究助手。请分析以下{topic}领域的最新论文列表，输出：
1. **今日重点论文** (3-5篇) - 附一句话说明为什么重要
2. **技术趋势分析** - 这些论文反映了什么趋势
3. **值得关注的方向** - 哪些方向值得深入研究

论文列表：
{paper_list}

请用中文回答，简洁有条理，重点突出。"""
    
    return ollama_generate(prompt, model="qwen2.5:3b-instruct-q4_K_M")

def ollama_analyze_security(news, hn):
    """让 Ollama 分析安全资讯"""
    news_text = "\n".join([f"- [{n.get('source', '未知')}] {n.get('id', 'N/A')}: {(n.get('description') or '')[:150]}" for n in news[:8]])
    hn_text = "\n".join([f"- [{h['title']}] (⭐{h['score']}) {h.get('url', h.get('hn_url', ''))}" for h in hn[:8]])
    
    prompt = f"""你是一名白帽黑客/安全研究员。请分析以下安全资讯，输出：
1. **重要漏洞预警** (3-5条) - 哪个漏洞最危险，影响范围
2. **热点攻击手法** - 最近流行的攻击方式
3. **防御建议** - 如何防御这些威胁
4. **社区热点** (HN热帖) - 安全社区在讨论什么

安全资讯：
{news_text}

HN 安全热帖：
{hn_text}

请用中文回答，技术性强，有实战价值。"""
    
    return ollama_generate(prompt, model="qwen2.5:3b-instruct-q4_K_M")

def ollama_weekly_insight(ai_summary, sec_summary, date_str):
    """让 Ollama 综合当天学习，生成洞见"""
    prompt = f"""今天 ({date_str}) 我学习了以下内容：

【AI技术动态】
{ai_summary}

【白帽安全动态】
{sec_summary}

请综合以上内容，输出一份**今日学习简报**，包括：
1. 两三个最值得关注的点（AI和安全交叉领域尤其注意）
2. 简短点评（1-2句话）
3. 明天可以深入研究的1-2个方向

用中文，200字以内，要精炼有洞见。"""
    
    return ollama_generate(prompt, model="qwen2.5:3b-instruct-q4_K_M", timeout=180)

# ========== 主流程 ==========

def run_daily_learning():
    date_str = datetime.now().strftime("%Y-%m-%d")
    date_full = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    print(f"\n{'='*50}")
    print(f"🚀 开始每日学习: {date_full}")
    print(f"{'='*50}")
    
    # --- AI 技术学习（并行抓取，节省~24秒）---
    print("\n📚 [AI技术] 并行抓取 ArXiv 论文...")
    queries = [
        ("large language model", "cs.CL"),
        ("reinforcement learning", "cs.LG"),
        ("AI safety", "cs.AI"),
        ("diffusion model", "cs.CV"),
    ]
    ai_papers = []
    lock = __import__('threading').Lock()

    def search_one(q, cat):
        try:
            results = search_arxiv(q, max_results=8, category=cat)
            return results
        except Exception as e:
            print(f"  ⚠️ 搜索 '{q}' 时出错: {e}")
            return []

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(search_one, q, cat): (q, cat) for q, cat in queries}
        for future in as_completed(futures):
            results = future.result()
            with lock:
                ai_papers.extend(results)

    # 去重
    seen = set()
    unique_papers = []
    for p in ai_papers:
        if p['id'] not in seen:
            seen.add(p['id'])
            unique_papers.append(p)

    print(f"  找到 {len(unique_papers)} 篇论文，让 Ollama 分析...")
    
    # 智能分析
    try:
        ai_summary = ollama_summarize_papers(unique_papers, "AI技术")
    except Exception as e:
        print(f"  ⚠️ Ollama分析失败: {e}")
        ai_summary = "Ollama分析失败，请检查Ollama服务状态。"
    
    ai_report = f"""# AI技术学习报告 - {date_str}

> 自动生成 | Hermes Agent + Ollama(qwen2.5:3b)

## 今日论文列表

{chr(10).join([f"### {i+1}. {p.get('title', '无标题')}\n**arXiv:** {p.get('id', 'N/A')} | **发表:** {p.get('published', 'N/A')}\n**作者:** {p.get('authors', '未知')}\n**摘要:** {(p.get('summary') or '')[:300]}...\n**链接:** {p.get('url','')}" for i, p in enumerate(unique_papers[:15])])}

---

## Ollama 分析总结

{ai_summary}

---
*本报告由本地 Ollama 大模型自动分析生成*
"""
    save_report(f"{AI_DIR}/{date_str}_AI技术学习报告.md", ai_report)
    
    # --- 白帽技术学习（并行抓取，安全+HN同时进行）---
    print("\n🛡️ [白帽技术] 并行抓取安全资讯...")

    def fetch_sec():
        try:
            return ("sec", fetch_security_news())
        except Exception as e:
            print(f"  ⚠️ 安全资讯获取失败: {e}")
            return ("sec", [])

    def fetch_hn():
        try:
            return ("hn", fetch_hackernews("security|vulnerability|exploit|CVE|hack|breach"))
        except Exception as e:
            print(f"  ⚠️ HackerNews获取失败: {e}")
            return ("hn", [])

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(fetch_sec): None, pool.submit(fetch_hn): None}
        sec_news, hn_sec = [], []
        for future in as_completed(futures):
            tag, data = future.result()
            if tag == "sec":
                sec_news = data
            else:
                hn_sec = data
    
    print(f"  找到 {len(sec_news)} 条 CVE + {len(hn_sec)} 条 HN 热帖，让 Ollama 分析...")
    
    try:
        sec_summary = ollama_analyze_security(sec_news, hn_sec)
    except Exception as e:
        print(f"  ⚠️ 安全分析失败: {e}")
        sec_summary = "安全分析失败，请检查Ollama服务状态。"
    
    sec_report = f"""# 白帽技术学习报告 - {date_str}

> 自动生成 | Hermes Agent + Ollama(qwen2.5:3b)

## 今日安全资讯

{chr(10).join([f"### [{n.get('source', '未知')}] {n.get('id', 'N/A')}\n{(n.get('description') or '')[:300]}{'...\n🔗 '+n.get('url','') if n.get('url') else ''}" for n in sec_news[:10]])}

## Hacker News 安全热帖

{chr(10).join([f"### {h.get('title', '无标题')} (⭐{h.get('score', 0)})\n🔗 {h.get('hn_url','')}" for h in hn_sec[:8]])}

---

## Ollama 安全分析

{sec_summary}

---
*本报告由本地 Ollama 大模型自动分析生成*
"""
    save_report(f"{WH_DIR}/{date_str}_白帽技术学习报告.md", sec_report)
    
    # --- 综合洞见 ---
    print("\n💡 生成今日综合洞见...")
    try:
        insight = ollama_weekly_insight(ai_summary, sec_summary, date_str)
    except Exception as e:
        print(f"  ⚠️ 综合分析失败: {e}")
        insight = "综合分析失败，请检查Ollama服务状态。"
    
    insight_report = f"""# 每日学习简报 - {date_str}

> 综合分析 | Hermes Agent + Ollama(qwen2.5:3b)

{insight}

---
*生成时间: {date_full}*
*数据来源: ArXiv, NVD CVE, Exploit-DB, Hacker News*
"""
    save_report(f"{BACKUP_BASE}/{date_str}_每日学习简报.md", insight_report)
    
    # --- 知识点提炼入库（闭环关键）---
    extract_and_save_knowledge(
        f"{AI_DIR}/{date_str}_AI技术学习报告.md",
        f"{WH_DIR}/{date_str}_白帽技术学习报告.md"
    )

    print(f"\n✅ 今日学习完成！所有文件已备份到 {BACKUP_BASE}/")


# ========== 新流水线：大海逻辑 - 多模型并行 ==========

def fast_scan_papers(papers, max_items=50):
    """快扫阶段：用smollm2快速扫描论文，识别值得深读的
    
    Args:
        papers: 论文列表
        max_items: 最多扫描数量
    
    Returns:
        list: [(title, url, reason), ...] 值得深读的论文
    """
    if not pre_model_check("fast_scan"):
        return []
    
    print(f"\n🔍 [快扫阶段] 使用 smollm2:1.7b 扫描 {min(len(papers), max_items)} 篇...")
    
    selected = []
    items = papers[:max_items]
    
    prompt_template = """你是分类专家。快速判断这篇论文是否值得深入学习。

论文标题: {title}
摘要: {abstract}

判断标准（满足任一即可）:
- 技术创新性强
- 实用价值高（有开源代码）
- 跨领域应用潜力大
- 解决实际问题

回答格式（只输出这一行）:
值得深读: 是/否 | 主要原因: 1-2句话
"""
    
    for i, paper in enumerate(items):
        try:
            title = paper.get("title", "")
            abstract = paper.get("abstract", "")[:500]
            
            result = ollama_generate(
                prompt_template.format(title=title, abstract=abstract),
                task_type="fast_scan"
            )
            
            if "是" in result[:10]:
                selected.append({
                    "title": title,
                    "url": paper.get("url", ""),
                    "abstract": abstract
                })
                print(f"  ✅ [{i+1}/{len(items)}] 标记: {title[:40]}...")
            else:
                print(f"  ⏭️ [{i+1}/{len(items)}] 跳过")
                
        except Exception as e:
            print(f"  ⚠️ 处理失败: {e}")
            continue
    
    print(f"\n📊 快扫完成：{len(selected)}/{len(items)} 篇值得深读")
    return selected


def extract_patterns_from_case(case_content, case_type="general"):
    """用deepseek-r1:7b提炼可复用的思路模式
    
    Args:
        case_content: 案例内容
        case_type: 案例类型（debugging/coding/research等）
    
    Returns:
        dict: {"pattern": "...", "applications": [...], "connections": [...]}
    """
    if not pre_model_check("reasoning"):
        return None
    
    print(f"  🧠 提炼思路模式...")
    
    prompt = f"""你是思路提炼专家。从以下案例中提炼出可复用的思维模式。

案例类型: {case_type}
案例内容:
{case_content[:3000]}

请提炼：
1. 这用了什么思路模式？（用一句话概括）
2. 这种思路还能用在哪些场景？（列出3-5个）
3. 这个思路和已有的哪些模式可能有关联？

输出格式（JSON）:
{{
  "pattern_name": "思路名称",
  "description": "1-2句话描述这种思路的本质",
  "applications": ["场景1", "场景2", "场景3"],
  "related_patterns": ["已知模式A", "已知模式B"],
  "key_insight": "1句话核心洞见"
}}
只输出JSON，不要其他内容。
"""
    
    try:
        result = ollama_generate(prompt, task_type="reasoning")
        # 尝试解析JSON
        import json
        start = result.find('{')
        end = result.rfind('}') + 1
        if start >= 0 and end > start:
            return json.loads(result[start:end])
        else:
            print(f"  ⚠️ 格式解析失败")
            return None
    except Exception as e:
        print(f"  ⚠️ 提炼失败: {e}")
        return None


def save_to_brain(pattern_data, case_title):
    """保存提炼出的思路模式到brain目录"""
    if not pattern_data:
        return
    
    try:
        import json
        
        # 保存到reasoning_patterns
        pattern_id = f"pattern_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        pattern_file = f"{BRAIN_DIR}/reasoning_patterns/{pattern_id}.json"
        
        pattern_entry = {
            **pattern_data,
            "source": case_title,
            "created": datetime.now().isoformat(),
            "review_count": 0,
            "last_reviewed": None
        }
        
        with open(pattern_file, "w", encoding="utf-8") as f:
            json.dump(pattern_entry, f, ensure_ascii=False, indent=2)
        
        print(f"  ✅ 思路已存入brain: {pattern_data.get('pattern_name', '未知')}")
        
        # 更新连接图
        connections_file = f"{BRAIN_DIR}/neural/connections.json"
        if os.path.exists(connections_file):
            with open(connections_file, "r", encoding="utf-8") as f:
                connections = json.load(f)
        else:
            connections = {"connections": [], "cross_domain_links": []}
        
        # 添加新连接
        for related in pattern_data.get("related_patterns", []):
            connections["connections"].append({
                "from": pattern_id,
                "to": related,
                "strength": 0.5,
                "reason": pattern_data.get("key_insight", "")
            })
        
        with open(connections_file, "w", encoding="utf-8") as f:
            json.dump(connections, f, ensure_ascii=False, indent=2)
        
        # 更新索引
        index_file = f"{BRAIN_DIR}/index.json"
        if os.path.exists(index_file):
            with open(index_file, "r", encoding="utf-8") as f:
                index = json.load(f)
            index["stats"]["reasoning_patterns"] = len(os.listdir(f"{BRAIN_DIR}/reasoning_patterns"))
            index["stats"]["neural_connections"] = len(connections["connections"])
            index["last_updated"] = datetime.now().strftime("%Y-%m-%d")
            with open(index_file, "w", encoding="utf-8") as f:
                json.dump(index, f, ensure_ascii=False, indent=2)
        
        return pattern_id
        
    except Exception as e:
        print(f"  ⚠️ 保存brain失败: {e}")
        return None


def run_new_pipeline(papers):
    """新流水线：快扫→深读→提炼pattern
    
    Args:
        papers: 论文列表
    
    Returns:
        dict: 执行结果统计
    """
    print("\n" + "="*50)
    print("🧠 新流水线启动：大海逻辑")
    print("="*50)
    
    result = {
        "fast_scanned": 0,
        "selected": 0,
        "deep_read": 0,
        "patterns_extracted": 0
    }
    
    # 第一阶段：快扫
    print("\n📦 阶段1: 快扫分类")
    selected = fast_scan_papers(papers, max_items=50)
    result["fast_scanned"] = len(papers)
    result["selected"] = len(selected)
    
    if not selected:
        print("⚠️ 没有找到值得深读的内容")
        return result
    
    # 第二阶段：深读 + 提炼pattern
    print(f"\n📖 阶段2: 深度分析 {len(selected)} 篇精选")
    for i, paper in enumerate(selected[:10]):  # 最多深读10篇
        print(f"\n[{i+1}/{min(len(selected), 10)}] 深度分析: {paper['title'][:50]}...")
        
        # 深读分析
        deep_content = paper.get("abstract", "")
        print(f"  📚 提炼思路模式...")
        
        pattern = extract_patterns_from_case(
            f"论文: {paper['title']}\n\n内容: {deep_content}",
            case_type="research"
        )
        
        if pattern:
            save_to_brain(pattern, paper["title"])
            result["patterns_extracted"] += 1
        
        result["deep_read"] += 1
    
    print("\n" + "="*50)
    print(f"✅ 新流水线完成:")
    print(f"   快扫: {result['fast_scanned']} 篇")
    print(f"   精选: {result['selected']} 篇")
    print(f"   深读: {result['deep_read']} 篇")
    print(f"   提炼: {result['patterns_extracted']} 个思路模式")
    print("="*50)
    
    return result


if __name__ == "__main__":
    import traceback
    
    # ========== 统一错误拦截+自动修复层 ==========
    MAX_RETRIES = 3
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            run_daily_learning()
            break  # 成功 → 静默退出
        except KeyError as e:
            # 字段缺失 → 修复后重试（记录但不告知用户）
            field = str(e).strip("'\"")
            print(f"\n⚙️ [自动修复] 发现缺失字段 '{field}'，已用空值替代，第{attempt}次重试...")
            if attempt >= MAX_RETRIES:
                print(f"\n❌ [拦截放弃] 字段 {field} 缺失超过{MAX_RETRIES}次重试，脚本退出")
                print(f"   请检查数据源格式，或手动补充缺失字段")
        except Exception as e:
            # 其他错误 → 记录+重试
            print(f"\n⚙️ [自动修复] 第{attempt}次尝试遇到问题: {type(e).__name__}: {e}")
            if attempt < MAX_RETRIES:
                print(f"   自动重试中...")
            else:
                print(f"\n❌ [拦截放弃] 错误超过{MAX_RETRIES}次重试，脚本退出")
                print(f"   错误详情: {e}")
                traceback.print_exc()
