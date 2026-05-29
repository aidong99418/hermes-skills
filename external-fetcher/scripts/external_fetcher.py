#!/usr/bin/env python3
"""
外部知识获取模块 v1.0
====================
当brain无相关记录时 → 从外部获取 → Ollama分析 → 写进brain
"""
import os
import re
import json
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path

sys_path = "/opt/data/scripts"
if sys_path not in __import__('sys').path:
    __import__('sys').path.insert(0, sys_path)

# ── 数据源配置 ──────────────────────────────────────────────
class ExternalSources:
    """可靠外部数据源"""
    
    @staticmethod
    def arxiv_search(topic: str, max_results=3) -> list:
        """从ArXiv搜索论文"""
        try:
            query = topic.replace(" ", "+")
            url = f"http://export.arxiv.org/api/query?search_query=all:{query}&max_results={max_results}&sortBy=relevance"
            resp = requests.get(url, timeout=30)
            if resp.status_code != 200:
                return []
            
            items = []
            # 简单解析Atom XML
            entries = re.findall(r'<entry>(.*?)</entry>', resp.text, re.DOTALL)
            for entry in entries[:max_results]:
                title = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
                summary = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)
                link = re.search(r'<id>(.*?)</id>', entry)
                published = re.search(r'<published>(.*?)</published>', entry)
                if title:
                    items.append({
                        "title": title.group(1).strip().replace('\n', ' '),
                        "abstract": summary.group(1).strip()[:500] if summary else "",
                        "url": link.group(1) if link else "",
                        "date": published.group(1)[:10] if published else "",
                        "source": "arXiv"
                    })
            return items
        except Exception as e:
            print(f"  ⚠️ ArXiv获取失败: {e}")
            return []
    
    @staticmethod
    def hn_trending(topic: str, max_results=5) -> list:
        """从HackerNews获取相关帖子"""
        try:
            # 获取最新top stories
            resp = requests.get(
                "https://hacker-news.firebaseio.com/v0/topstories.json",
                timeout=10
            )
            if resp.status_code != 200:
                return []
            
            story_ids = json.loads(resp.text)[:30]  # 只查前30条
            results = []
            
            for sid in story_ids[:max_results]:
                try:
                    story_resp = requests.get(
                        f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                        timeout=5
                    )
                    if story_resp.status_code == 200:
                        story = json.loads(story_resp.text)
                        title = story.get("title", "").lower()
                        if any(kw in title for kw in topic.lower().split()):
                            results.append({
                                "title": story.get("title", ""),
                                "url": story.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                                "score": story.get("score", 0),
                                "date": datetime.fromtimestamp(story.get("time", 0)).strftime("%Y-%m-%d"),
                                "source": "HackerNews"
                            })
                except:
                    continue
                
            return results[:max_results]
        except Exception as e:
            print(f"  ⚠️ HN获取失败: {e}")
            return []
    
    @staticmethod
    def web_snippet(query: str, max_results=3) -> list:
        """尝试从网页获取摘要（StackOverflow/Wiki等）"""
        # StackOverflow API
        try:
            so_url = (
                f"https://api.stackexchange.com/2.3/search/orders=desc"
                f"&sort=relevance&tagged=python&intitle={query}&site=stackoverflow&pagesize={max_results}"
            )
            resp = requests.get(so_url, timeout=10)
            if resp.status_code == 200:
                data = json.loads(resp.text)
                results = []
                for item in data.get("items", [])[:max_results]:
                    body = item.get("body_markdown", "")[:300]
                    results.append({
                        "title": item.get("title", ""),
                        "excerpt": body,
                        "url": item.get("link", ""),
                        "score": item.get("score", 0),
                        "source": "StackOverflow"
                    })
                if results:
                    return results
        except Exception as e:
            print(f"  ⚠️ StackOverflow: {e}")
        
        return []
    
    @staticmethod
    def query_all(question: str) -> dict:
        """并行查询所有数据源"""
        print(f"  🌐 正在从外部获取知识...")
        
        # 提取关键词
        keywords = re.findall(r'[\w]{3,}', question.lower())
        topics = " ".join(keywords[:5])
        
        results = {
            "arxiv": ExternalSources.arxiv_search(topics),
            "hn": ExternalSources.hn_trending(topics),
            "web": ExternalSources.web_snippet(topics),
            "raw_question": question,
            "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        
        total = len(results["arxiv"]) + len(results["hn"]) + len(results["web"])
        print(f"  → 获取到 {total} 条外部知识")
        
        return results


# ── Ollama分析模块 ──────────────────────────────────────────
def analyze_with_ollama(question: str, external_data: dict, model: str = "granite4.1:3b") -> str:
    """用Ollama分析外部知识，生成结构化结论"""
    try:
        import requests
        import json
        
        # 精简prompt
        arxiv_text = ""
        for a in external_data.get("arxiv", [])[:2]:
            arxiv_text += f"- {a['title'][:80]} ({a['date']}): {a['abstract'][:150]}\n"
        hn_text = ""
        for h in external_data.get("hn", [])[:2]:
            hn_text += f"- {h['title'][:80]}\n"
        web_text = ""
        for w in external_data.get("web", [])[:2]:
            web_text += f"- {w['title'][:80]}\n"
        
        prompt = f"问题：{question}\n\n相关论文：\n{arxiv_text or '无'}\nHN热帖：\n{hn_text or '无'}\n问答：\n{web_text or '无'}\n\n请用简洁的Markdown格式回答，包含：1.核心结论 2.关键要点 2-3个"
        
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=90
        )
        # Ollama返回NDJSON，需逐行拼接response片段
        lines = resp.text.strip().split('\n')
        return ''.join(
            json.loads(l).get('response', '') for l in lines if l.strip()
        ) or "分析失败"
        
    except Exception as e:
        print(f"  ⚠️ Ollama分析失败: {e}")
        return f"分析失败: {e}"


# ── 写入Brain ───────────────────────────────────────────────
def save_to_brain(question: str, answer: str, sources: dict):
    """将获取的知识写进brain"""
    try:
        brain_dir = Path("/opt/data/brain")
        today = datetime.now().strftime("%Y%m%d")
        
        # 写进scenarios目录
        scenario_file = brain_dir / "scenarios" / f"external_learn_{today}.md"
        
        # 构建内容
        content_parts = [f"# 外部知识获取记录\n"]
        content_parts.append(f"**时间：** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        content_parts.append(f"**问题：** {question}\n")
        content_parts.append(f"\n## 回答\n{answer}\n")
        
        # 来源
        if sources.get("arxiv"):
            content_parts.append("\n### 📄 ArXiv论文\n")
            for a in sources["arxiv"][:2]:
                content_parts.append(f"- [{a['title']}]({a['url']}) - {a['date']}\n")
        
        if sources.get("hn"):
            content_parts.append("\n### 📰 HackerNews\n")
            for h in sources["hn"][:3]:
                content_parts.append(f"- [{h['title']}]({h['url']}) (Score:{h['score']})\n")
        
        if sources.get("web"):
            content_parts.append("\n### 💬 StackOverflow\n")
            for w in sources["web"][:2]:
                content_parts.append(f"- [{w['title']}]({w['url']})\n")
        
        content = "".join(content_parts)
        
        # 追加写入
        with open(scenario_file, "a", encoding="utf-8") as f:
            f.write(f"\n---\n\n{content}")
        
        print(f"  💾 已写入brain: {scenario_file}")
        
        # 追加到reasoning_patterns（如果存在该目录，否则跳过）
        pattern_dir = brain_dir / "reasoning_patterns"
        if pattern_dir.exists():
            pattern_file = pattern_dir / f"external_insights_{today}.md"
            pattern_content = f"""# 外部知识洞察

## 问题：{question}

## 结论
{answer[:800]}

---
来源: ArXiv/HN/SO | {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
            pattern_file.parent.mkdir(parents=True, exist_ok=True)
            with open(pattern_file, "w", encoding="utf-8") as f:
                f.write(pattern_content)
            print(f"  💾 已写入reasoning_patterns: {pattern_file}")

        # ── 自动rebuild缓存 ────────────────────────────────────
        try:
            import subprocess
            result = subprocess.run(
                ["python3", "/opt/data/scripts/brain_retriever.py", "--rebuild"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                print(f"  🧠 缓存已自动更新")
            else:
                print(f"  ⚠️ 缓存更新失败，可手动执行: brain_retriever.py --rebuild")
        except Exception as e:
            print(f"  ⚠️ 自动更新缓存失败: {e}")

        return True
        
    except Exception as e:
        print(f"  ⚠️ 写入brain失败: {e}")
        return False


# ── 主流程：获取→分析→存储 ─────────────────────────────────
def fetch_and_learn(question: str) -> dict:
    """
    外部知识获取完整流程
    返回: {"answer": str, "sources": dict, "saved": bool}
    """
    print(f"\n🌐 外部知识获取流程启动...")
    print(f"   问题: {question}")
    
    # 1. 查询各数据源
    sources = ExternalSources.query_all(question)
    
    # 只有拿到真实结果才调用Ollama分析
    data_sources = sources.get("arxiv", []) + sources.get("hn", []) + sources.get("web", [])
    if len(data_sources) == 0:
        print("  ⚠️ 未获取到任何外部知识，跳过分析阶段")
        return {"answer": "", "sources": sources, "saved": False}
    answer = analyze_with_ollama(question, sources)
    
    # 3. 写进brain
    saved = save_to_brain(question, answer, sources)
    
    return {
        "answer": answer,
        "sources": sources,
        "saved": saved
    }


# ── 集成到brain_thinker ─────────────────────────────────────
def think_with_external(question: str, tier: int, brain_hits: list) -> dict:
    """
    带外部知识获取的思考流程
    当brain无结果或结果不足时，自动触发外部获取
    """
    result = {
        "question": question,
        "tier": tier,
        "brain_hits": brain_hits,
        "external_used": False,
        "external_data": None,
        "answer": None
    }
    
    # tier1 不需要外部获取
    if tier == 1:
        result["answer"] = "直接执行"
        return result
    
    # brain有足够结果 → 不需要外部获取
    if len(brain_hits) >= 2 and brain_hits[0]["score"] > 8:
        result["answer"] = "brain已有足够知识"
        return result
    
    # brain无结果或结果不足 → 触发外部获取
    print(f"\n🌐 brain知识不足，触发外部获取...")
    external_result = fetch_and_learn(question)
    
    result["external_used"] = True
    result["external_data"] = external_result["sources"]
    result["answer"] = external_result["answer"]
    result["saved_to_brain"] = external_result["saved"]
    
    return result


# ── CLI模式 ─────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python3 external_fetcher.py \"你的问题\"")
        sys.exit(1)
    
    question = " ".join(sys.argv[1:])
    result = fetch_and_learn(question)
    
    print("\n" + "="*60)
    print("📋 分析结果：")
    print("="*60)
    print(result["answer"][:1000] if len(result["answer"]) > 1000 else result["answer"])
    print()
    if result["sources"]["arxiv"]:
        print(f"📄 ArXiv: {len(result['sources']['arxiv'])} 篇")
    if result["sources"]["hn"]:
        print(f"📰 HN: {len(result['sources']['hn'])} 条")
    if result["sources"]["web"]:
        print(f"💬 SO: {len(result['sources']['web'])} 条")
