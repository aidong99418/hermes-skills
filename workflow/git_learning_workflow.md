# GitHub技能学习 → 本地模型同步工作流

## 触发条件

- 用户说\"把Git里的好东西都学习掌握\"
- 仓库有重大更新需要同步

## 执行步骤

### Step 1: 克隆/拉取仓库
```bash
cd /opt/data/external-skills
git pull  # 已有
# 或
git clone https://github.com/aidong99418/herrmes-skills.git
```

### Step 2: 扫描所有skill文件
```bash
find . -name "SKILL.md" -o -name "*.py" | grep -v __pycache__
```

### Step 3: 并行读取核心skill
用delegate_task并行读取所有SKILL.md，提取：
- 目的和核心能力
- 关键API/命令
- 踩坑记录
- 创新点

### Step 4: 提炼知识写brain
按以下模板写入brain目录：
- 工具使用 → `brain/tool_templates/{tool_name}.md`
- 架构设计 → `brain/architecture/{name}.md`
- 推理模式 → `brain/reasoning_pattern/{pattern}.md`
- 原则规范 → `brain/principles/{principle}.md`
- 知识总结 → `brain/knowledge/{topic}.md`

### Step 5: 重建索引
```bash
python3 /opt/data/scripts/brain_retriever.py --rebuild
```

### Step 6: 验证检索
```python
from brain_retriever import BrainRetriever
r = BrainRetriever()
for label, keyword in tests:
    results = r.search(keyword, top_k=2)
    assert len(results) > 0, f"FAIL: {label}"
```

### Step 7: 写入skill文档
```python
skill_manage(action='create', category='brain',
  name='{repo}-digest',
  content='# {Repo} 精华摘要\n\n...')
```

### Step 8: 推送到hermes-addons
```bash
cd /opt/data/hermes-addons
git add . && git commit -m "feat: add {name} knowledge"
git push
```

## 关键坑

1. **GitHub网络慢** → token放进URL加速
2. **Token无效** → 先`curl api.github.com/user`验证
3. **中文检索失败** → 多语言关键词都要测试
4. **索引重建慢** → 用`--rebuild`而非删除重装
5. **知识散落** → 统一按架构/原则/工具分类存放

## 知识分类存放规范

```
brain/
├── principles/      # 核心原则（静默模式等）
├── knowledge/       # 知识总结（模型分层等）
├── reasoning_pattern/  # 推理模式（自进化、多Agent等）
├── workflow/        # 工作流（Git学习工作流等）
├── tool_templates/  # 工具模板（MCP集成等）
└── architecture/    # 架构设计
```
