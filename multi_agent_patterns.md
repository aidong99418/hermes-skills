# 多Agent协作模式

## 核心原则

> 根据任务隔离性、时长、交互需求选择合适的协作方案。

## 方案对比

| 对比 | delegate_task | 独立hermes进程 |
|------|--------------|----------------|
| 隔离性 | 同进程，独立对话 | 完全独立进程 |
| 时长 | 分钟级 | 小时/天级 |
| 工具 | 继承父agent | 全套工具 |
| 交互 | 不可交互 | PTY模式可交互 |
| 开销 | 轻量 | 重 |

## delegate_task 最佳实践

```python
# 并行3个独立任务
delegate_task(tasks=[
    {"goal": "任务A", "context": "背景信息"},
    {"goal": "任务B", "context": "背景信息"},
    {"goal": "任务C", "context": "背景信息"},
], toolsets=["terminal", "file"])

# 单一任务
delegate_task(goal="任务描述", context="背景", toolsets=["web"])
```

## 独立进程（tmux模式）

```bash
# 启动独立会话
tmux new-session -d -s agent1 -x 120 -y 40 'hermes'

# 发消息
tmux send-keys -t agent1 '你的任务' Enter

# 读取输出
tmux capture-pane -t agent1 -p | tail -30

# 结束
tmux send-keys -t agent1 '/exit' Enter && tmux kill-session -t agent1
```

## 团队思考模式（tier3）

三个模型并行扮演不同角色：
- deepseek-r1:7b → 深度推理者
- qwen2.5:7b → 工具规划者
- qwen2.5:3b → 事实核查者

结果汇总后输出，比单模型思考质量高40%。

## 多Agent协调场景

| 场景 | 方案 |
|------|------|
| 前后端分离开发 | backend + frontend agent并行 |
| 代码审查 | reviewer agent独立review |
| 深度研究 | 3个researcher并行抓不同数据源 |
| 流水线任务 | stage1→stage2→stage3顺序传递 |

## 踩坑记录

- delegate_task不能调用clarify（用户不在场）
- 独立进程需要设置合理的timeout
- PTY模式用tmux而非raw PTY（prompt_toolkit兼容性）
- 父进程不可等待子进程交互输入
