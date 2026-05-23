#!/usr/bin/env python3
"""
Brain + RAG + Skill 三路联合检索引擎 v2.0
=========================================
输入：查询关键词 → 输出：知识命中 + Skill推荐
新增：Skill触发词匹配 + 神经连接权重更新
"""
import os
import json
import re
from pathlib import Path

# ── BM25 检索器 ────────────────────────────────────────────
class BM25Retrieval:
    """轻量级 BM25 检索（rank-bm25 实现）"""
    def __init__(self):
        try:
            from rank_bm25 import BM25Okapi
            self.BM25Okapi = BM25Okapi
            self.available = True
        except ImportError:
            self.available = False
            print("⚠️ rank-bm25 未安装，跳过 BM25")

    def build(self, chunks, tokenized_chunks):
        if not self.available:
            return None
        return self.BM25Okapi(tokenized_chunks)

    def search(self, bm25, chunks, tokenized_query, top_k=5):
        if bm25 is None:
            return []
        scores = bm25.get_scores(tokenized_query)
        ranked = sorted(zip(scores, chunks), key=lambda x: -x[0])
        return [(score, text) for score, text in ranked[:top_k] if score > 0]

# ── 中文→英文查询扩展 ────────────────────────────────────────
CN_TO_EN = {
    "调试": "debug debugging error fix", "报错": "error failed crash",
    "错误": "error failed exception", "崩溃": "crash dump",
    "失败": "failed error", "问题": "issue problem bug",
    "ollama": "ollama model llm", "模型": "model llm",
    "大模型": "llm model language model", "脚本": "script python bash",
    "命令行": "cli command terminal", "终端": "terminal shell command",
    "自动化": "automation cron schedule", "cron": "cron schedule automation",
    "学习": "learning research study", "知识": "knowledge notes info",
    "知识库": "knowledge base rag brain", "大脑": "brain memory knowledge",
    "神经": "neural connection pathway", "记忆": "memory history context",
    "场景": "scenario case use case", "案例": "case scenario example",
    "推理": "reasoning thinking inference", "思考": "thinking reasoning analysis",
    "排查": "debugging troubleshooting", "诊断": "diagnose debug",
    "架构": "architecture design system", "设计": "design pattern architecture",
    "方案": "plan solution design", "系统": "system architecture platform",
    "数据": "data analysis analytics", "分析": "analysis analyze analytics",
    "抓取": "scrape fetch crawl", "爬虫": "scraper crawler spider",
    "安全": "security hack vulnerability", "漏洞": "vulnerability cve exploit",
    "攻击": "attack hack intrusion", "权限": "permission auth access",
    "磁盘": "disk storage space volume", "存储": "storage disk volume",
    "文件": "file path directory", "目录": "directory folder path",
    "测试": "test testing tdd unittest", "安全审计": "security audit vulnerability",
    "审查": "review code review", "代码": "code coding programming",
}

def expand_query(query: str) -> str:
    """中英文混合查询扩展"""
    expanded = [query]
    q_lower = query.lower()
    for cn, en in CN_TO_EN.items():
        if cn in q_lower:
            expanded.append(en)
    return " ".join(expanded)

def simple_tokenize(text):
    """中英文混合分词"""
    tokens = re.findall(r'[\w\u4e00-\u9fff]+', text.lower())
    return [t for t in tokens if len(t) >= 2]

def chunk_text(text, max_chars=400):
    """按句子分块，保留结构"""
    sentences = re.split(r'([。！？\n]|\n\n)', text)
    chunks, current = [], ""
    for i in range(0, len(sentences)-1, 2):
        s = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else "")
        if len(current) + len(s) > max_chars and current:
            chunks.append(current.strip())
            current = s
        else:
            current += s
    if current.strip():
        chunks.append(current.strip())
    return chunks

def extract_metadata(filepath):
    """从路径和文件名提取元信息"""
    path = str(filepath)
    meta = {"type": "unknown", "topic": "", "source": "brain"}
    if "reasoning_patterns" in path or "patterns" in path:
        meta["type"] = "reasoning_pattern"
    elif "scenarios" in path or "cases" in path:
        meta["type"] = "scenario_case"
    elif "tool_templates" in path:
        meta["type"] = "tool_template"
    elif "problem_types" in path:
        meta["type"] = "problem_type"
    elif "neural" in path:
        meta["type"] = "neural_connection"
    name = Path(filepath).stem
    for sep in ['_', '-']:
        parts = name.replace('_', ' ').replace('-', ' ').split()
        if parts:
            meta["topic"] = ' '.join(parts[:4])
            break
    return meta

# ── Skill触发词匹配器 ───────────────────────────────────────
class SkillMatcher:
    """基于skill_neural.json的触发词匹配器"""

    def __init__(self, neural_path="/opt/data/brain/neural/skill_neural.json"):
        self.neural_path = Path(neural_path)
        self.skills = []
        self._load()

    def _load(self):
        if self.neural_path.exists():
            data = json.load(open(self.neural_path))
            self.skills = data.get("skills", [])
        else:
            self.skills = []

    def reload(self):
        """热重载（skill增删后调用）"""
        self._load()

    def match(self, query: str, user_tier: int = 1) -> list:
        """
        匹配用户查询与skill触发词
        返回: [{name, score, triggers_matched, activates_nodes, file, min_tier}, ...]
        """
        if not self.skills:
            return []

        q_lower = query.lower()
        results = []

        for skill in self.skills:
            min_tier = skill.get("min_tier", 1)
            if user_tier < min_tier:
                continue

            triggers = skill.get("triggers", [])
            matched = [t for t in triggers if t.lower() in q_lower]

            if matched:
                score = len(matched) * 10.0
                results.append({
                    "name": skill["name"],
                    "score": round(score, 3),
                    "triggers_matched": matched,
                    "activates_nodes": skill.get("activates_nodes", []),
                    "strengthens": skill.get("strengthens", []),
                    "file": skill.get("file", ""),
                    "source": skill.get("source", ""),
                    "min_tier": min_tier,
                    "description": skill.get("description", ""),
                })

        results.sort(key=lambda x: -x["score"])
        return results

    def get_skill_by_name(self, name: str) -> dict | None:
        for s in self.skills:
            if s["name"] == name:
                return s
        return None

# ── 神经连接权重更新器 ──────────────────────────────────────
class NeuralUpdater:
    """skill执行后更新connections.json的突触权重"""

    def __init__(self, connections_path="/opt/data/brain/neural/connections.json"):
        self.connections_path = Path(connections_path)
        self.data = {}
        self._load()

    def _load(self):
        if self.connections_path.exists():
            self.data = json.load(open(self.connections_path))

    def update(self, skill_name: str, neural_data: dict):
        """根据skill执行结果更新连接权重"""
        strengthens = neural_data.get("strengthens", [])
        if not strengthens:
            return

        connections = self.data.get("connections", [])

        for st in strengthens:
            from_node = st["from"]
            to_node = st["to"]
            delta = st.get("delta", 0.1)

            found = False
            for conn in connections:
                if conn.get("from") == from_node and conn.get("to") == to_node:
                    conn["weight"] = min(1.0, conn["weight"] + delta)
                    reason = conn.get("reason", "")
                    conn["reason"] = f"{reason} | skill {skill_name} +{delta}"
                    found = True
                    break

            if not found:
                connections.append({
                    "from": from_node,
                    "to": to_node,
                    "weight": min(1.0, 0.5 + delta),
                    "reason": f"skill {skill_name} 首次激活"
                })

        self.data["connections"] = connections
        self.data["updated"] = datetime.now().strftime("%Y-%m-%d")

        with open(self.connections_path, 'w') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def suggest_skills_for_nodes(self, nodes: list) -> list:
        """根据激活的神经节点推荐相关skill"""
        neural_path = Path("/opt/data/brain/neural/skill_neural.json")
        if not neural_path.exists():
            return []

        data = json.load(open(neural_path))
        suggestions = []
        seen = set()
        for skill in data.get("skills", []):
            activates = skill.get("activates_nodes", [])
            for node in nodes:
                if node in activates and skill["name"] not in seen:
                    suggestions.append({
                        "name": skill["name"],
                        "activates": activates,
                        "description": skill.get("description", "")
                    })
                    seen.add(skill["name"])
                    break
        return suggestions[:5]

from datetime import datetime

# ── 核心检索器 ──────────────────────────────────────────────
class BrainRetriever:
    """Brain + Skill 三路联合检索器 v2.0"""

    def __init__(self, brain_dir="/opt/data/brain", rebuild=True):
        self.brain_dir = Path(brain_dir)
        self.cache_path = Path("/tmp/brain_bm25_cache.json")
        self.bm25_tool = BM25Retrieval()
        self.chunks = []
        self.meta = []
        self.bm25 = None
        self._load_or_build(rebuild)
        # Skill + Neural 扩展
        self.skill_matcher = SkillMatcher()
        self.neural_updater = NeuralUpdater()

    def _load_or_build(self, rebuild):
        """加载缓存 or 重新构建"""
        if not rebuild and self.cache_path.exists():
            data = json.load(open(self.cache_path))
            self.chunks = data["chunks"]
            self.meta = data["meta"]
            tokenized = [simple_tokenize(c) for c in self.chunks]
            self.bm25 = self.bm25_tool.build(self.chunks, tokenized)
            return

        self._scan_brain()
        self._build_index()
        self._save_cache()

    def _scan_brain(self):
        """扫描 brain 目录"""
        patterns = ["**/*.md", "**/*.json", "**/*.txt"]
        for pat in patterns:
            for f in self.brain_dir.glob(pat):
                if f.name.startswith('.'):
                    continue
                try:
                    content = f.read_text(encoding='utf-8')
                    if len(content) < 50:
                        continue
                    if f.name in ['index.json', 'connections.json', 'inference_paths.json']:
                        if f.stat().st_size < 5000:
                            continue
                    chunks = chunk_text(content)
                    for chunk in chunks:
                        self.chunks.append(chunk)
                        self.meta.append({
                            "file": str(f.relative_to(self.brain_dir)),
                            **extract_metadata(f)
                        })
                except Exception as e:
                    pass

    def _build_index(self):
        """构建 BM25 索引"""
        if not self.chunks:
            return
        tokenized = [simple_tokenize(c) for c in self.chunks]
        self.bm25 = self.bm25_tool.build(self.chunks, tokenized)

    def _save_cache(self):
        """保存缓存"""
        cache = {"chunks": self.chunks, "meta": self.meta}
        self.cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2))

    def search(self, query, top_k=5):
        """检索相关知识"""
        if not self.bm25:
            return []
        expanded = expand_query(query)
        tokenized = simple_tokenize(expanded)
        results = self.bm25_tool.search(self.bm25, self.chunks, tokenized, top_k)
        output = []
        seen = set()
        for score, text in results:
            idx = self.chunks.index(text)
            key = self.meta[idx]['file'] + text[:50]
            if key in seen:
                continue
            seen.add(key)
            output.append({
                "score": round(score, 3),
                "text": text[:300],
                "source": f"brain/{self.meta[idx]['file']}",
                "type": self.meta[idx]['type'],
                "topic": self.meta[idx]['topic']
            })
        return output

    def match_skills(self, query: str, user_tier: int = 1) -> list:
        """匹配skill触发词（与brain知识并行）"""
        return self.skill_matcher.match(query, user_tier)

    def update_neural_on_skill_use(self, skill_name: str, neural_data: dict):
        """skill执行后更新神经连接权重"""
        self.neural_updater.update(skill_name, neural_data)

    def get_skill_recommendations(self, nodes: list) -> list:
        """基于激活的神经节点推荐skill"""
        return self.neural_updater.suggest_skills_for_nodes(nodes)

    def search_all(self, query: str, user_tier: int = 1, top_k: int = 5) -> dict:
        """
        三路并行检索（知识 + Skill + 神经推荐）
        返回统一的结构化结果
        """
        brain_hits = self.search(query, top_k)
        skill_matches = self.match_skills(query, user_tier)

        # 神经节点推断
        all_nodes = set()
        for s in skill_matches:
            all_nodes.update(s.get("activates_nodes", []))
        neural_suggestions = self.get_skill_recommendations(list(all_nodes)) if all_nodes else []

        return {
            "brain_hits": brain_hits,
            "skill_matches": skill_matches,
            "neural_suggestions": neural_suggestions,
            "total_brain_chunks": len(self.chunks),
            "total_skills": len(self.skill_matcher.skills)
        }

    def incremental_add(self, title, content, chunk_type="scenario_case"):
        """增量添加新知识块"""
        chunks = chunk_text(content)
        for chunk in chunks:
            self.chunks.append(chunk)
            self.meta.append({
                "file": f"scenarios/cases/{title}.md",
                "type": chunk_type,
                "topic": title,
                "source": "learning_output"
            })
        self._build_index()
        self._save_cache()


# ── 主程序（CLI 模式）───────────────────────────────────────
if __name__ == "__main__":
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "代码报错怎么debug"
    rebuild = "--rebuild" in sys.argv

    retriever = BrainRetriever(rebuild=rebuild)

    print(f"\n🔍 查询: {query}")
    print("=" * 60)

    result = retriever.search_all(query, user_tier=2, top_k=5)

    print(f"📚 brain知识: {len(result['brain_hits'])} 条命中")
    for h in result['brain_hits'][:3]:
        print(f"   [{h['score']:.1f}] {h['type']} | {h['text'][:100]}...")

    print(f"\n🎯 Skill匹配: {len(result['skill_matches'])} 个skill命中")
    for s in result['skill_matches']:
        print(f"   [{s['score']:.1f}] {s['name']} | 触发:{s['triggers_matched']} | 激活:{s['activates_nodes']}")

    if result['neural_suggestions']:
        print(f"\n🧠 神经推荐: {len(result['neural_suggestions'])} 个相关skill")
        for ns in result['neural_suggestions']:
            print(f"   → {ns['name']}: {ns['description']}")
