---
name: brain-system-integration
description: 机器猫大脑系统集成与维护 — 将brain_thinker/external_fetcher/auto_learning打通成一套能用的思考系统。踩坑记录：chunk格式/超时/rebuild时机的实践经验。
triggers:
  - 大脑系统不工作/报错
  - 外部获取超时/挂死
  - brain缓存不更新
  - 模型冷启动问题
  - 需要把brain_thinker集成到其他脚本
---

# 机器猫大脑系统集成与维护

## 核心文件清单

| 文件 | 作用 | 入口 |
|------|------|------|
| `brain_thinker.py` | 三层思考引擎（tier1/2/3+外部获取+团队派发） | CLI: `python3 brain_thinker.py "问题" --tier 2` |
| `brain_invoke.py` | 轻量包装，一行调用 | `from brain_invoke import brain_think; r = brain_think("问题")` |
| `external_fetcher.py` | 外部知识获取（ArXiv+HN+SO→Ollama分析→写brain） | 被brain_thinker调用 |
| `auto_learning.py` | 每日自动学习，写brain+rebuild | cron任务 |
| `brain_retriever.py` | BM25检索核心，支持--rebuild | `python3 brain_retriever.py --rebuild` |
| `ollama_model_manager.py` | 模型保活+降级+健康检查 | `python3 ollama_model_manager.py --check` |

## 踩坑记录（必读）

### 1. brain缓存chunk格式
- **chunk是字符串数组，不是字典数组**
  ```python
  # ✅ 正确
  chunks = data.get("chunks", [])  # list[str]
  text = chunk if isinstance(chunk, str) else chunk.get("text", "")

  # ❌ 错误 - chunk没有.get()方法
  text = chunk.get("text", "")
  ```

### 2. external_fetcher返回结构
- `fetch_and_learn()` 返回 `{"answer": str, "sources": dict, "saved": bool}`，不是字符串
- 判断有没有数据要这样：
  ```python
  data_sources = sources.get("arxiv", []) + sources.get("hn", []) + sources.get("web", [])
  if len(data_sources) == 0:  # 不能用 sum(len(v) for v in sources.values()) 因为还有raw_question字符串
    return {"answer": "", "sources": sources, "saved": False}
  ```

### 3. 外部获取0结果时不调Ollama
- ArXiv超时30秒（15秒太短容易超时）
- 0结果时直接跳过分析，不浪费Ollama调用

### 4. 写brain后自动rebuild
- external_fetcher写完brain后自动调用 `brain_retriever.py --rebuild`
- auto_learning早已有这个逻辑
- rebuild是30秒超时的subprocess调用，有try/except保护

### 5. tier3团队派发
- 用 `concurrent.futures.ThreadPoolExecutor` 并行调用3个模型
- 3个模型都要加载才能用，否则会timeout
- qwen2.5:7b没预加载时首调会冷启动

### 6. qwen2.5:7b冷启动问题
- 该模型未在默认保活列表（太大）
- 首次调用时冷启动可能超过timeout
- 解决方案：使用时用 `ollama_model_manager.py --warmup` 预热，或在critical时刻用tier=2

## 三层思考触发条件

```
tier1：查看/查/剩多少/看看（开头或含） + 长度<20字 → 直接答
tier2：为什么/怎么/如何/分析 + 长度>30字 → brain检索 + 外部获取
tier3：重大决策/架构选型/多方案比较 → 3模型并行团队派发
```

## 快速验证命令

```bash
# 检查模型状态
python3 ollama_model_manager.py --check

# 测试brain检索
python3 brain_thinker.py "Python异常处理" --tier 2

# 测试轻量调用
python3 brain_invoke.py "Python异常处理"

# 重建缓存
python3 brain_retriever.py --rebuild

# 手动触发外部获取
python3 external_fetcher.py "Python KeyError"
```

## 常见故障排查

| 症状 | 原因 | 解决方案 |
|------|------|----------|
| brain检索返回空 | 缓存不存在或损坏 | `brain_retriever.py --rebuild` |
| 外部获取0结果 | ArXiv超时/网络问题 | 加大timeout或跳过ArXiv |
| tier3派发全部失败 | 模型未加载 | `ollama_model_manager.py --warmup` |
| import brain_invoke报错 | 路径问题 | 确认在 `/opt/data/scripts/` 目录 |
