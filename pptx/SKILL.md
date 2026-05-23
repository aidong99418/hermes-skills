---
name: pptx
description: PowerPoint演示文稿技能——创建/编辑/读取/模板处理。触发词：PPT、PowerPoint、演示文稿、pptx、幻灯片、演讲稿、汇报PPT。源：anthropics/skills，脚本路径：/opt/data/scripts/pptx/
triggers:
  - PPT
  - PowerPoint
  - 演示文稿
  - pptx
  - 幻灯片
  - 演讲稿
  - 汇报PPT
skills:
  - name: pptx
    source: anthropics/skills
---

# PPTX 技能

## 快速参考

| 任务 | 工具 |
|------|------|
| 读取/分析内容 | `python -m markitdown presentation.pptx` |
| 编辑/修改模板 | unpack → 编辑 → pack 流程 |
| 从零创建 | pptxgenjs |
| 缩略图预览 | `/opt/data/scripts/pptx/add_slide.py` |

## 依赖

```bash
pip install python-pptx markitdown Pillow
# 从零创建才需要:
npm install -g pptxgenjs
```

## 工作流

### 读取内容
```bash
# 文本提取
python -m markitdown presentation.pptx

# 生成缩略图
python /opt/data/scripts/pptx/add_slide.py input.pptx --thumbnails

# 解包查看XML
python3 /opt/data/scripts/pptx/office/unpack.py presentation.pptx unpacked/
```

### 编辑已有PPT
1. 解包：`python3 /opt/data/scripts/pptx/office/unpack.py input.pptx unpacked/`
2. 编辑XML内容
3. 清理：`python3 /opt/data/scripts/pptx/office/clean.py unpacked/`
4. 打包：`python3 /opt/data/scripts/pptx/office/pack.py unpacked/ output.pptx`

### 从零创建
使用 pptxgenjs：
```bash
# 先安装 Node.js pptxgenjs
npm install -g pptxgenjs

# 创建脚本后运行
node create_slides.js
```

## 设计规范（重要）

### 配色方案
| 主题 | 主色 | 辅色 | 强调色 |
|------|------|------|--------|
| Midnight Executive | `1E2761` 深蓝 | `CADCFC` 冰蓝 | `FFFFFF` 白 |
| Forest & Moss | `2C5F2D` 森林 | `97BC62` 苔藓 | `F5F5F5` 奶油 |
| Coral Energy | `F96167` 珊瑚 | `F9E795` 金 | `2F3C7E` 藏青 |
| Ocean Gradient | `065A82` 深蓝 | `1C7293` 青 | `21295C` 午夜 |

### 排版
- 标题: 36-44pt 加粗
- 正文: 14-16pt
- 边距 ≥ 0.5"
- 避免纯文字幻灯片——必须有视觉元素（图标/图片/图表）

### 必须避免
- ❌ 纯文字幻灯片
- ❌ 蓝色主题通配（颜色要匹配内容）
- ❌ 平均分配颜色权重
- ❌ 标题下划线（AI生成特征）
- ❌ 文字与背景低对比度

## QA（必须执行）

```bash
# 内容检查
python -m markitdown output.pptx | grep -iE "xxxx|lorem|ipsum|placeholder"

# 视觉检查：转图片
python3 /opt/data/scripts/pptx/office/soffice.py --headless --convert-to pdf output.pptx
pdftoppm -jpeg -r 150 output.pdf slide
```

> ⚠️ 视觉QA用subagent来做，避免视觉疲劳盲区。必须经过"生成→截图→检查→修复→再检查"循环才能宣布完成。
