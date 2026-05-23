---
name: git-delta
description: Git Delta — 31k⭐ Git diff 语法高亮工具，替代 pager，side-by-side视图 / 单词级diff / git blame 增强
version: 1.0.0
tags: [git, diff, terminal, productivity]
triggers: ["git diff美化", "delta", "git blame增强", "diff阅读工具", "git pager"]
---

# Git Delta — 智能 Git Diff 阅读器

## 一句话定位

`delta` 是一个 Git 输出（diff/blame/log/grep）的语法高亮 pager，替代默认的 `less`，让代码 review 效率大幅提升。

## 核心安装与配置

```bash
# 安装（各系统不同）
# macOS
brew install git-delta
# Linux
sudo apt install git-delta  # 或从 release 下载

# 一行配置 .gitconfig
git config --global core.pager delta
git config --global interactive.diffFilter 'delta --color-only'
git config --global delta.navigate true
git config --global delta.dark true
```

## 核心功能速查

| 功能 | 配置 | 效果 |
|------|------|------|
| 语法高亮 | `delta.dark=true` | 自动检测终端背景色 |
| Side-by-side | `delta.side-by-side=true` | 左右分栏看 diff |
| 行号 | `delta.line-numbers=true` | 显示新旧行号 |
| 单词级 diff | `delta.hunk-header-style= syntax` | 精确显示变更单词 |
| 合并冲突视图 | `delta.merge-conflict-marker-style=above` | 彩色标注冲突区域 |
| Git blame 增强 | `delta.blame-code-color=cyan` | blame 输出语法高亮 |
| N/N 导航 | `delta.navigate=true` | 用 `n/N` 跳转文件/块 |
| 代码复制 | `delta.features=copy-button` | 复制去标记 |
| 仓库链接 | `delta.hyperlinks=true` | commit hash → GitHub 链接 |
| 主题切换 | `delta.theme=GitHub` | 20+ bat 主题可选 |

## 完整 .gitconfig 推荐配置

```gitconfig
[core]
    pager = delta

[interactive]
    diffFilter = delta --color-only

[delta]
    navigate = true
    dark = true
    side-by-side = true
    line-numbers = true
    hyperlinks = true
    hyperlinks.commit-link-format = "https://github.com/aidong99418/hermes-skills/commit/{commit}"
    hyperlinks.file-link-format = "https://github.com/aidong99418/hermes-skills/blob/{commit}/{path}"
    merge-conflict-marker-style = zdiff3
    blame-code-color = cyan

[merge]
    conflictstyle = zdiff3

[delta "decorations"]
    commit-style = bold yellow
    file-style = bold auto
    hunk-header-style = omit
```

## 使用场景

### 1. 看普通 diff
```bash
git diff HEAD~5
```
自动语法高亮 + 单词级变更标注（绿色新增/红色删除）

### 2. Side-by-side Code Review
```bash
git diff --side-by-side HEAD~3
```
适合看大改动的代码，代码审查效率翻倍

### 3. Git Blame 增强
```bash
git blame src/main.py
```
每行显示作者、commit、时间，语法高亮代码内容

### 4. Merge Conflict 解决
```bash
git diff --merge
```
彩色标注冲突区域，清晰区分 ours/theirs

### 5. 彩色 grep
```bash
git grep "TODO" | delta
rg "TODO" | delta --color-only
```
搜索结果语法高亮

### 6. Commit Hash 超链接
```bash
git log --oneline --format="%H %s" | delta
```
点击 commit hash 直接跳转 GitHub

## 主题推荐

```bash
# 查看所有可用主题
delta --show-syntax-themes

# 推荐主题
delta.dark=true          # 自动检测
delta.theme=Dracula      # 固定用 Dracula
delta.theme=One Half Dark  # 简洁双色
```

## 坑

1. **Windows Terminal 需 v1.10+**，旧版可能渲染异常
2. **超长行会自动截断**，配合 `side-by-side` + `line-wrap` 更舒适
3. **非 Git 输出**（如纯 diff 文件），用 `delta some.diff` 直接打开
4. **集成到 `less` 环境变量**：`export DELTA_PAGER=less`，其他工具也能用
5. **与 `diff-so-fancy` 互斥**，二选一，delta 功能更强
