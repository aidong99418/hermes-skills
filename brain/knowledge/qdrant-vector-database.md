# Qdrant 向量数据库

## 概述
Qdrant是19k stars的生产级向量数据库，相比Chroma更强——支持过滤、聚类、分布式、分片复制。比Pinecone便宜且完全本地化。

## 核心优势 vs Chroma
| 特性 | Chroma | Qdrant |
|------|--------|--------|
| 部署 | 单机轻量 | 支持分布式集群 |
| 过滤 | 基础 | 复杂多维过滤 |
| 分片复制 | ❌ | ✅ |
| 性能 | 中等 | 优化过的大规模检索 |
| Python SDK | ✅ | ✅ 更完善 |
| Rust实现 | ❌ | ✅ 高性能 |

## 快速开始
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import numpy as np

# 方式1: 内存模式（开发用）
client = QdrantClient(":memory:")

# 方式2: 本地文件（生产用）
client = QdrantClient(path="./qdrant_storage")

# 方式3: 远程服务
client = QdrantClient(host="localhost", port=6333)

# 创建Collection
client.create_collection(
    collection_name="articles",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
)

# 插入向量
points = [
    PointStruct(
        id=1,
        vector=np.random.rand(1536).tolist(),
        payload={"title": "文章标题", "content": "文章内容"}
    )
]
client.upsert(collection_name="articles", points=points)

# 检索
results = client.search(
    collection_name="articles",
    query_vector=np.random.rand(1536).tolist(),
    limit=5,
    score_threshold=0.7,
    query_filter={"must": [{"key": "category", "match": {"value": "tech"}}]}
)
```

## 高级功能
### 1. 过滤查询
```python
from qdrant_client.models import Filter, FieldCondition, MatchValue

results = client.search(
    collection_name="articles",
    query_vector=query_vec,
    query_filter=Filter(
        must=[
            FieldCondition(key="category", match=MatchValue(value="tech")),
            FieldCondition(key="year", range={"gte": 2023})
        ]
    ),
    limit=10
)
```

### 2. 分组检索
```python
results = client.search_groups(
    collection_name="articles",
    query_vector=query_vec,
    group_by="author",
    limit=3,
    group_size=2
)
```

### 3. 混合搜索（稀疏+密集）
```python
client.search(
    collection_name="articles",
    query_vector=query_vec,
    sparse_vector={
        "indices": [0, 5, 10],
        "values": [0.1, 0.8, 0.5]
    },
    limit=10
)
```

## Docker部署（生产）
```bash
docker run -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage \
    qdrant/qdrant
```

## Hermes集成方案
在Hermes的local-rag-knowledge-base skill中，替换Chroma为Qdrant：
1. 安装: `pip install qdrant-client`
2. 初始化client指向本地/远程Qdrant服务
3. 向量维度匹配embedding模型（text-embedding-3-small=1536）
4. 利用Qdrant的过滤能力做分类RAG

## 关键洞察
1. **Qdrant比Chroma更适合生产环境**——分布式+过滤+复制是刚需
2. **本地部署只需`docker run`**——5分钟跑起来
3. **Python SDK非常完善**——基本覆盖所有API
4. **过滤条件是RAG精准化的关键**——不只是相似度排名
5. **group_by可以解决"同一来源多条检索"问题**

## 相关文档
- 主库: qdrant/qdrant (19k stars)
- Python SDK: qdrant/qdrant-client (10k stars, 10KB README)
