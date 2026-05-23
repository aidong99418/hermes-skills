---
name: continue-ide
description: Continue AI编程助手 — VSCode/JetBrains插件，22k⭐，LLM+codebase RAG，多文件编辑，prompt chaining。触发：代码补全、代码库问答、IDE AI助手、Cursor替代。
version: 1.0.0
tags: [IDE, coding-assistant, RAG, multi-file-edit, VSCode]
triggers: ["Continue", "IDE AI助手", "代码库问答", "Cursor替代", "多文件编辑", "codebase RAG"]
---

# Continue IDE 架构设计参考

## 核心定位
Continue = AI编程助手IDE插件（22k⭐），让LLM深度理解整个代码库，支持跨文件编辑、代码补全、问答搜索。是Cursor/Windsurf等AI IDE的核心架构参考。

## 核心架构

```
┌──────────────────────────────────────────────────┐
│              Continue VSCode/JetBrains 插件       │
└──────────────────────┬───────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Embeddings  │ │   Codebase   │ │   LLM API    │
│   服务层      │ │   Index      │ │   调度层     │
│ (句子向量)    │ │ (语义索引)    │ │ (多模型切换) │
└──────────────┘ └──────────────┘ └──────────────┘
         │             │             │
         └─────────────┼─────────────┘
                       ▼
              ┌─────────────────┐
              │  Context Forge   │
              │  上下文构建引擎   │
              │  （智能选取相关代码）│
              └─────────────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
   代码补全      代码编辑        问答对话
```

## Codebase RAG（代码库语义索引）

这是Continue最核心的能力——让LLM"理解"整个代码库：

### 索引策略

```python
class CodebaseIndex:
    # 1. 文件级索引
    def index_file(self, file_path: str):
        chunks = self.chunk_code(file_path)  # 按函数/类分块
        embeddings = self.embed(chunks)       # 向量化
        return self.vector_db.upsert(embeddings)

    # 2. 语义搜索
    def search(self, query: str, top_k: int = 10) -> list[CodeChunk]:
        query_emb = self.embed(query)
        return self.vector_db.search(query_emb, top_k)

    # 3. 增量更新（git diff驱动）
    def update_from_diff(self, diff: str):
        changed_files = parse_git_diff(diff)
        for f in changed_files:
            self.reindex(f)
```

### Context Forge（上下文构建）

```python
class ContextForge:
    """智能选取最相关的代码片段作为上下文"""
    def build(self, task: str, max_tokens: int = 8000) -> str:
        # 1. 语义搜索相关代码
        chunks = self.codebase.search(task, top_k=20)
        # 2. 按依赖关系排序（import graph）
        ordered = self.topological_sort(chunks)
        # 3. 按token上限截断
        return self.truncate(ordered, max_tokens)
```

## 多模型调度

```python
class ModelRouter:
    MODELS = {
        "fast": "claude-haiku",      # 代码补全（快）
        "balanced": "gpt-4o-mini",   # 日常编辑（均衡）
        "powerful": "claude-sonnet-4", # 复杂重构（强）
    }

    def select(self, task: str) -> str:
        if is_simple_completion(task):
            return self.MODELS["fast"]
        elif is_complex_refactor(task):
            return self.MODELS["powerful"]
        return self.MODELS["balanced"]
```

## 多文件编辑模式

### Prompt Chaining

```python
# 一个任务拆解为多个LLM调用链
class PromptChain:
    def edit_across_files(self, task: str, files: list[str]):
        # Step 1: 理解任务意图
        plan = self.llm.call("分析任务", task)
        # Step 2: 逐文件修改（保持上下文）
        for f in files:
            context = self.build_context(f, plan)
            self.llm.edit(f, context)
        # Step 3: 验证一致性
        self.verify_changes(files)
```

## Slash Commands（斜杠命令）

```python
# 用户输入 /review → 触发代码审查流程
SLASH_COMMANDS = {
    "/review": ReviewCommand(),      # 代码审查
    "/explain": ExplainCommand(),    # 代码解释
    "/edit": EditCommand(),          # 编辑选中代码
    "/test": TestCommand(),          # 生成测试
    "/refactor": RefactorCommand(),  # 重构建议
}
```

## 与本项目的契合点

| Continue特性 | 本项目借鉴点 |
|-------------|------------|
| Codebase RAG | 可对接本项目RAG知识库 |
| Context Forge | 上下文构建策略（token控制） |
| 多模型调度 | 按任务复杂度选模型 |
| Slash Commands | 可迁移为/hermes的斜杠命令 |
| Prompt Chaining | 多步骤任务的链式调用 |

## 快速启动

```bash
# VSCode插件市场搜索 "Continue" 安装
# 或手动安装
git clone https://github.com/continuedev/continue
cd continue
npm install && npm run build

# 配置 .continue/config.py
cat > ~/.continue/config.py << 'EOF'
from continuedev.lib.llm import LLM
from continuedev.lib.embeddings import OpenAIEmbeddings

config = {
    "models": [{
        "provider": "openai",
        "model": "gpt-4o-mini",
        "api_key": "xxx",
    }],
    "embeddings": OpenAIEmbeddings(api_key="xxx"),
}
EOF
```

## 坑/注意事项

1. **大代码库索引慢**：初次索引需要扫描全量代码，可配置.gitignore减少范围
2. **Embedding成本**：代码向量化有成本，用本地embedding（nomic-embed-text）省钱
3. **多文件编辑一致性问题**：Prompt Chaining跨文件修改容易破坏依赖
4. **Token上下文限制**：Codebase太大需要分级索引（目录级→文件级→函数级）
5. **JetBrains支持不完整**：VSCode插件功能最全

## 配置示例

```python
# .continue/config.py 完整配置
from continuedev.lib.llm import OllamaLLM

config = {
    "allow_dangerous_commands": False,
    "models": [{
        "provider": "ollama",
        "model": "codellama:13b",
        "api_base": "http://localhost:11434",
    }],
    "embeddings": {
        "provider": "ollama",
        "model": "nomic-embed-text",
    },
    "indexing": {
        "exclude": ["node_modules", "__pycache__", ".git"],
        "batch_size": 50,
    },
}
```
