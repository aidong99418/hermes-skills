
## 2026-06-08 凌晨三层架构修复

### 问题
- wisemodel主 + 备用provider双通道冲突，每次guardian扫描后providers基准线被强制恢复
- minimax-cn备用导致崩溃（固化为铁律：不动minimax-cn备用配置）
- 三层路由实际上是单provider配置，没有真正的provider双通道

### 修复内容
1. 清理config/guardian_state.json里错误的providers基准线（系统用custom_providers不需要顶级providers字段）
2. 三层架构保持：L1 wisemodel/L2云端并发/L3 Ollama，无provider双通道切换
3. 新增MiniMax-CN备用模型（custom_providers第二个入口，非provider切换）

### 最终配置
```
custom_providers:
- name: 始智Ai
  base_url: https://open.ospreyai.cn/v1
  api_key: wisemodel-gbngcikewhrtirhoamio
  model: minimax-m2.5-highspeed
  models:
    minimax-m2.5-highspeed:
      context_length: 192000
- name: MiniMax-CN
  base_url: https://open.minimaxi.com/v1
  api_key: sk-cp-e7ypQtEjYCaxxSqEsbrQJkER3KZvdSkZxIa-I3fjmBSEMn1imMsc8x0ozVjY9ISoFahahWwoc_52iIFHF1F4YQsW1Rxmw_yBATj7wYP1lUmYmGfbwZQSNkM
  model: MiniMax-M2.7
  models:
    MiniMax-M2.7:
      context_length: 100000
```

### 铁律
- ✅ 不走providers/fallback_providers双通道（死锁风险）
- ✅ 备用走custom_providers模型层面，不走provider切换
