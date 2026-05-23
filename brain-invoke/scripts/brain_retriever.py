#!/usr/bin/env python3
"""
Brain + RAG 联合检索引擎
========================
输入：查询关键词 → 输出：相关知识片段
用法：python3 /opt/data/scripts/brain_retriever.py "Python调试"
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
    # 问题类型
    "调试": "debug debugging error fix", "报错": "error failed crash",
    "错误": "error failed exception", "崩溃": "crash dump",
    "失败": "failed error", "问题": "issue problem bug",
    # 工具/系统
    "ollama": "ollama model llm", "模型": "model llm",
    "大模型": "llm model language model", "脚本": "script python bash",
    "命令行": "cli command terminal", "终端": "terminal shell command",
    "自动化": "automation cron schedule", "cron": "cron schedule automation",
    # 知识管理
    "学习": "learning research study", "知识": "knowledge notes info",
    "知识库": "knowledge base rag brain", "大脑": "brain memory knowledge",
    "神经": "neural connection pathway", "记忆": "memory history context",
    "场景": "scenario case use case", "案例": "case scenario example",
    "推理": "reasoning thinking inference", "思考": "thinking reasoning analysis",
    "排查": "debugging troubleshooting排查", "诊断": "diagnose debug",
    # 架构/设计
    "架构": "architecture design system", "设计": "design pattern architecture",
    "方案": "方案 plan solution design", "系统": "system architecture platform",
    # 数据/分析
    "数据": "data analysis analytics", "分析": "analysis analyze analytics",
    "抓取": "scrape fetch crawl", "爬虫": "scraper crawler spider",
    # 安全
    "安全": "security hack vulnerability", "漏洞": "vulnerability cve exploit",
    "攻击": "attack hack intrusion", "权限": "permission auth access",
    # 文件/磁盘
    "磁盘": "disk storage space volume", "存储": "storage disk volume",
    "文件": "file path directory", "目录": "directory folder path",
}

def expand_query(query: str) -> str:
    """中英文混合查询扩展"""
    expanded = [query]
    q_lower = query.lower()
    for cn, en in CN_TO_EN.items():
        if cn in q_lower:
            expanded.append(en)
    return " ".join(expanded)

# ── 文本处理工具 ────────────────────────────────────────────
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
    meta = {
        "type": "unknown",
        "topic": "",
        "source": "brain"
    }
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
    
    # 从文件名提取主题
    name = Path(filepath).stem
    for sep in ['_', '-']:
        parts = name.replace('_', ' ').replace('-', ' ').split()
        if parts:
            meta["topic"] = ' '.join(parts[:4])
            break
    return meta

# ── 核心检索器 ──────────────────────────────────────────────
class BrainRetriever:
    """Brain 知识库检索器"""
    
    def __init__(self, brain_dir="/opt/data/brain", rebuild=True):
        self.brain_dir = Path(brain_dir)
        self.cache_path = Path("/tmp/brain_bm25_cache.json")
        self.bm25_tool = BM25Retrieval()
        self.chunks = []       # 分块文本
        self.meta = []         # 对应元数据
        self.bm25 = None
        self._load_or_build(rebuild)
    
    def _load_or_build(self, rebuild):
        """加载缓存 or 重新构建"""
        if not rebuild and self.cache_path.exists():
            print("✅ 从缓存加载 brain 索引")
            data = json.load(open(self.cache_path))
            self.chunks = data["chunks"]
            self.meta = data["meta"]
            tokenized = [simple_tokenize(c) for c in self.chunks]
            self.bm25 = self.bm25_tool.build(self.chunks, tokenized)
            return
        
        print("🔨 构建 brain 索引...")
        self._scan_brain()
        self._build_index()
        self._save_cache()
        print(f"   → {len(self.chunks)} 个知识块已索引")
    
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
                    # 跳过索引文件
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
                    print(f"   ⚠️ 读取 {f.name} 失败: {e}")
    
    def _build_index(self):
        """构建 BM25 索引"""
        if not self.chunks:
            print("⚠️ brain 为空，跳过索引构建")
            return
        tokenized = [simple_tokenize(c) for c in self.chunks]
        self.bm25 = self.bm25_tool.build(self.chunks, tokenized)
    
    def _save_cache(self):
        """保存缓存"""
        cache = {"chunks": self.chunks, "meta": self.meta}
        self.cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2))
        print(f"   💾 缓存已保存: {self.cache_path}")
    
    def search(self, query, top_k=5):
        """检索相关知识"""
        if not self.bm25:
            return []
        # 中文→英文扩展，多角度检索
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
    
    def incremental_add(self, title, content, chunk_type="scenario_case"):
        """增量添加新知识块（学习产出回流用）"""
        chunks = chunk_text(content)
        for chunk in chunks:
            self.chunks.append(chunk)
            self.meta.append({
                "file": f"scenarios/cases/{title}.md",
                "type": chunk_type,
                "topic": title,
                "source": "learning_output"
            })
        # 重建索引
        self._build_index()
        self._save_cache()
        print(f"✅ 增量添加 {len(chunks)} 个块: {title}")


# ── 主程序（CLI 模式）───────────────────────────────────────
if __name__ == "__main__":
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "Ollama 学习系统"
    
    # 支持 --rebuild 参数强制重建
    rebuild = "--rebuild" in sys.argv
    if rebuild:
        retriever = BrainRetriever(rebuild=True)
        query = sys.argv[2] if len(sys.argv) > 2 else sys.argv[1] if len(sys.argv) > 1 else ""
        if not query or query == "--rebuild":
            print(f"\n✅ brain缓存已重建: {len(retriever.chunks)} 个知识块")
            sys.exit(0)
    else:
        retriever = BrainRetriever(rebuild=False)
    
    print(f"\n🔍 查询: {query}")
    print("=" * 60)
    
    retriever = BrainRetriever(rebuild=False)
    results = retriever.search(query, top_k=5)
    
    if not results:
        print("无相关结果")
    else:
        for i, r in enumerate(results, 1):
            print(f"\n【{i}】{r['type']} | {r['topic']}")
            print(f"   匹配度: {r['score']:.3f} | 来源: {r['source']}")
            print(f"   {r['text'][:250]}")
    
    print()
