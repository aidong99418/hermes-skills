---
name: git-delta-integration
description: Git差异高亮工具Delta集成 — 让代码Review效率提升10倍
tags: [git, code-review, productivity]
---

# Git Delta 集成技能

## 安装
```bash
# macOS
brew install git-delta

# Linux (deb)
curl -fsSL https://github.com/dandavison/delta/releases/latest/download/git-delta_amd64.deb -o delta.deb
sudo dpkg -i delta.deb
```

## Git全局配置
```bash
git config --global core.pager delta
git config --global interactive.diffFilter "delta --color-only"
git config --global delta.navigate true
git config --global delta.side-by-side true
git config --global delta.line-numbers true
```

## Hermes + GitHub PR集成
在github-code-review skill中：
```bash
# 替代默认diff输出
gh pr diff {pr_number} | delta --side-by-side

# 对比任意commit
git diff A..B | delta

# 查看stash
git stash show -p | delta
```

## 快捷键
- `j/k` — 上下行
- `n/p` — 下一hunk/上一hunk
- `q` — 退出
- `s` — 同步滚动
