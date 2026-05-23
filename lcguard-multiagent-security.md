# LCGuard: 多Agent KV通信安全防护

> 核心来源: arXiv 2605.22786 | 2026-05-21 | Asif et al.

## 核心发现

### 问题：KV缓存通信是"隐式侧信道"

多Agent通过KV缓存共享中间状态（推理过程、上下文）效率很高，但KV里藏着：
- 原始输入上下文（可能含敏感数据）
- 中间推理状态（Agent思维过程）
- Agent特定信息（行为模式）

这些不会显式出现在文本输出里，但通过KV传播出去了——相当于"隐式侧信道"。

```
文本通信: Agent A → "已完成分析" → Agent B  ✓ 可审计
KV通信:   Agent A的推理state → 共享KV → Agent B  ✗ 盲区
```

### LCGuard方案：KV安全门卫

在KV共享前加Guard层，过滤敏感内容：
1. **敏感度检测** - 扫描KV中的敏感token
2. **梯度门控** - 只让安全token参与注意力计算
3. **隐私预算** - 限制每个Agent能看到多少其他Agent的KV

```python
class LCGUARD:
    def sanitize_kv(self, kv_cache, target_agent):
        sanitized = self.sensitivity_filter(kv_cache)
        return self.privacy_budget(sanitized, target_agent)
```

## 对机器猫系统的启发

| LCGuard发现 | 机器猫现状 | 改进方向 |
|---------|---------|---------|
| KV传播=隐式信息泄漏 | 多Agent间通过brain间接共享状态 | Brain中的信息需要分级权限 |
| 显式通信可审计，隐式不行 | 工具调用结果直接进上下文 | 敏感工具返回结果要sanitize |
| Guard层必须加在共享点 | 无通信安全层 | 为brain/记忆共享加安全边界 |

## 核心原则

1. **信息共享必须显式可审计**——隐式传播=安全盲区
2. **敏感信息分级**——不是所有工具返回都该进Agent上下文
3. **共享点=安全门**——brain/记忆/KV共享处必须设Guard

---
*提炼自Hermes学习系统 | 2026-05-23*
