---
name: v1-v016-isolation-verification
description: V1 ↔ V016文件系统隔离验证——inode检查法，纠正旧session错误结论
triggers:
  - 验证V1和V016是否共用文件
  - 确认文件系统隔离状态
  - 排查数据打架问题
---

# V1 ↔ V016 隔离验证方法

## 验证方法（inode检查法）

```python
import os

paths = {
    "V1 connections.json": "/opt/data/brain/neural/connections.json",
    "V016 connections.json": "/volume1/docker/hermes-文件路径/hermes016/brain/neural/connections.json",
    "V1 skills": "/opt/data/skills",
    "V016 skills": "/volume1/docker/hermes-文件路径/hermes016/skills",
    "V1 brain": "/opt/data/brain",
    "V016 brain": "/volume1/docker/hermes-文件路径/hermes016/brain",
}

for name, path in paths.items():
    try:
        st = os.stat(path)
        print(f"{name}: inode={st.st_ino}")
    except Exception as e:
        print(f"{name}: 不存在 - {e}")
```

## 判断标准
- **inode相同** = 同一物理文件 = 共用（问题）
- **inode不同** = 完全独立文件 = 隔离（正常）

## 已知结果（2026-06-22实测）

| 检测项 | V1 inode | V016 inode | 结论 |
|--------|----------|------------|------|
| connections.json | 37693195 | 37905487 | ✅ 独立 |
| skills目录 | 37757019 | 37893068 | ✅ 独立 |
| brain目录 | 37752907 | 37901067 | ✅ 独立 |

## 关键教训
- **不要相信跨session的旧结论**。上次session说"共用inode=37693195"，今天重新验证发现是错的。
- 物理底层都是ext4同一磁盘，但**目录路径不同=inode不同=完全隔离**。
- 检查隔离要用`os.stat()`取真实inode，不能看目录路径或文件内容是否相似。

## 架构含义
- V1数据 → `/opt/data/`（ext4物理盘）
- V016数据 → `/volume1/docker/hermes-文件路径/hermes016/`（同一物理盘的不同目录）
- 两个系统同时读写同一磁盘不同目录，不打架，因为文件级inode完全不同
