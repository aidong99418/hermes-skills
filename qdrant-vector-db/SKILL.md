---
name: qdrant-vector-db
description: Qdrant 向量数据库 — 31k⭐ 生产级向量相似度搜索引擎，支持密集/稀疏/多向量搜索、payload过滤、REST+gRPC双接口
version: 1.0.0
tags: [vector-database, semantic-search, RAG, embedding]
triggers: ["向量数据库", "Qdrant", "向量搜索", "embedding存储", "语义检索", "RAG向量库"]
---

# Qdrant 向量数据库核心技能

## 核心概念

```
Collection (集合)
  └── Vector Params: 维度(size) + 距离度量(distance)
  └── Points: 向量 + Payload (元数据)
  └── Index: HNSW 索引加速检索
```

**距离度量选择：**
| 度量 | 适用场景 |
|------|---------|
| Cosine | 文本嵌入（normalize后）|
| Dot | 高维密集向量 |
| Euclid | 图像/音频特征 |

## 快速上手

```python
from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")

# 1. 创建 Collection
client.create_collection(
    collection_name="my_docs",
    vectors_config={
        "size": 1536,  # OpenAI embedding 维度
        "distance": "Cosine"
    }
)

# 2. 插入 Points
client.upsert(
    collection_name="my_docs",
    points=[
        {"id": 1, "vector": [0.1, 0.2, ...], "payload": {"text": "文档内容", "source": "report"}},
        {"id": 2, "vector": [0.3, 0.4, ...], "payload": {"text": "另一篇", "source": "blog"}},
    ]
)

# 3. 搜索
results = client.search(
    collection_name="my_docs",
    query_vector=[0.1, 0.2, ...],
    limit=5,
    score_threshold=0.7,
    query_filter=None  # 或 payload 条件过滤
)
```

## 关键决策点

| 场景 | 推荐配置 |
|------|---------|
| RAG 知识库 | Cosine + HNSW (默认) + 1536维 |
| 多模态检索 | Multi-vector (late interaction如ColBERT) |
| 高并发实时搜索 | 启用 quantization (binary/Product/Scalar) |
| 多租户隔离 | Sharding + Tenant isolation |
| 离线/边缘部署 | Qdrant Edge (Python/Rust embedded) |

## Payload 过滤

Qdrant 强大的地方：向量相似度 + 传统过滤结合：

```python
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range

client.search(
    collection_name="my_docs",
    query_vector=query_embedding,
    query_filter=Filter(
        must=[
            FieldCondition(key="source", match=MatchValue(value="report")),
            FieldCondition(key="score", range=Range(gte=0.8)),
        ]
    ),
    limit=10
)
```

支持的过滤条件：MatchValue, MatchAny, MatchExcept, Range, DatetimeRange, GeoRadius, HasId...

## RAG 集成最佳实践

```python
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# Embedding 模型
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# 查询
query_embedding = model.encode("如何优化Python性能").tolist()

results = client.search(
    collection_name="docs",
    query_vector=query_embedding,
    limit=5,
    with_payload=True  # 返回关联文本
)

# 拼接上下文
context = "\n".join([r.payload["text"] for r in results])
prompt = f"根据以下内容回答：\n{context}\n\n问题：如何优化Python性能？"
```

## 性能优化三板斧

### 1. Quantization（量化压缩）
```python
client.update_collection(
    collection_name="my_docs",
    optimizer_config={
        "denoising": {"min_size": 10000, "dead_threshold": 20000}
    },
    quantization_config={
        "scalar": {
            "type": "int8",
            "quantile": 0.99
        }
    }
)
```

### 2. HNSW 参数调优
```python
client.create_collection(
    collection_name="my_docs",
    vectors_config={"size": 1536, "distance": "Cosine"},
    hnsw_config={
        "m": 16,        # 节点邻居数（越大越准越慢）
        "ef_construct": 200  # 构建索引精度
    }
)
```

### 3. Sparse Vector 混合搜索
```python
# 同时搜索密集向量(语义) + 稀疏向量(关键词)
client.search(
    collection_name="my_docs",
    query_vector={
        "dense": dense_embedding,
        "sparse": sparse_vector,  # BM25风格
    },
    limit=10
)
```

## 坑

1. **维度必须与 embedding 模型一致**，OpenAI text-embedding-3-small 是 1536
2. **gRPC 比 REST 快 5-10 倍**，生产环境优先用 gRPC（6334端口）
3. **delete 后不会立即释放空间**，需要 vacuum 或重建索引
4. **Upsert 是全量覆盖**，要增量更新用 `point_id` 指定
5. **Qdrant Cloud 免费额度有限**，生产环境注意成本
6. **Edge 版本功能受限**，不支持分布式和复制
