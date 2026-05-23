---
name: docx
description: 创建、编辑、读取和操作Word文档(.docx)。触发词：Word文档、.docx、生成报告/备忘录/信函/模板、制作专业文档（目录/标题/页码/页眉）、提取或重组docx内容、在Word文件中查找替换、处理追踪修订或批注、将内容转换为精美的Word文档。
triggers:
  - "word"
  - "docx"
  - "Word文档"
  - "生成报告"
  - "备忘录"
  - "信函"
  - "编辑文档"
---

# DOCX creation, editing, and analysis

## 概述

.docx 文件本质是一个ZIP压缩包，内含XML文件。

## 快速参考

| 任务 | 方法 |
|------|------|
| 读取/分析内容 | `pandoc` 或解包后读原始XML |
| 创建新文档 | 使用 `docx-js`（见下文） |
| 编辑现有文档 | 解包 → 编辑XML → 重新打包 |

### 读取内容
```bash
# 带追踪修订的文本提取
pandoc --track-changes=all document.docx -o output.md

# 原始XML访问
python3 scripts/office/unpack.py document.docx unpacked/
```

### 接受追踪修订
```bash
python3 scripts/accept_changes.py input.docx output.docx
```

---

## 创建新文档

用 JavaScript 生成 .docx 文件，然后验证。安装：`npm install -g docx`

### 关键规则

1. **设置页面尺寸** - docx-js默认A4，美式文档用US Letter (12240 x 15840 DXA)
2. **横版：传竖版尺寸** - docx-js内部会交换宽高
3. **永远不要用 `\n`** - 用独立的 Paragraph 元素
4. **永远不要用 unicode bullet** - 用 `LevelFormat.BULLET` 配 numbering config
5. **PageBreak 必须在 Paragraph 里** - 独立创建会产生无效XML
6. **ImageRun 必须有 type** - 总是指定 png/jpg 等
7. **表格必须用 DXA 宽度** - 永远不用 `WidthType.PERCENTAGE`（Google Docs不兼容）
8. **表格需要双重宽度** - `columnWidths` 数组 AND 每个 cell 的 `width`，两者必须匹配
9. **总是加 cell margins** - `margins: { top: 80, bottom: 80, left: 120, right: 120 }`
10. **用 `ShadingType.CLEAR`** - 永远不要用 SOLID 做表格底纹

### 页面尺寸（DXA单位，1440 DXA = 1英寸）

| 纸张 | 宽度 | 高度 | 内容宽度（1"边距） |
|------|------|------|-------------------|
| US Letter | 12,240 | 15,840 | 9,360 |
| A4（默认） | 11,906 | 16,838 | 9,026 |

### 基本结构
```javascript
const { Document, Packer, Paragraph, TextRun, HeadingLevel,
        Header, Footer, PageNumber, PageBreak } = require('docx');

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 24 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 240, after: 240 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 180, after: 180 }, outlineLevel: 1 } },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    headers: { default: new Header({ children: [new Paragraph("Header")] }) },
    footers: { default: new Footer({ children: [new Paragraph({
      children: [new TextRun("Page "), new TextRun({ children: [PageNumber.CURRENT] })]
    })] }) },
    children: [
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("标题")] }),
      new Paragraph({ children: [new TextRun("正文内容")] }),
    ]
  }]
});

Packer.toBuffer(doc).then(buffer => fs.writeFileSync("output.docx", buffer));
```

### 列表（NEVER用unicode bullet）
```javascript
new Document({
  numbering: {
    config: [
      { reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ]
  },
  sections: [{
    children: [
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun("Bullet item")] }),
      new Paragraph({ numbering: { reference: "numbers", level: 0 }, children: [new TextRun("Numbered item")] }),
    ]
  }]
});
```

### 表格（关键规则）
```javascript
const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };

new Table({
  width: { size: 9360, type: WidthType.DXA },      // 总是用DXA
  columnWidths: [4680, 4680],                        // 必须等于table width
  rows: [
    new TableRow({
      children: [
        new TableCell({
          borders,
          width: { size: 4680, type: WidthType.DXA },  // cell width必须匹配
          shading: { fill: "D5E8F0", type: ShadingType.CLEAR }, // CLEAR不是SOLID
          margins: { top: 80, bottom: 80, left: 120, right: 120 },
          children: [new Paragraph({ children: [new TextRun("Cell")] })]
        })
      ]
    })
  ]
})
```

### 图片
```javascript
new Paragraph({
  children: [new ImageRun({
    type: "png", // 必须：png, jpg, jpeg, gif, bmp, svg
    data: fs.readFileSync("image.png"),
    transformation: { width: 200, height: 150 },
    altText: { title: "Title", description: "Desc", name: "Name" } // 三个都必须
  })]
})
```

### 分页符
```javascript
new Paragraph({ children: [new PageBreak()] })
```

### 目录
```javascript
// 关键：标题必须用 HeadingLevel，不能用自定义样式
new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-3" })
```

---

## 编辑现有文档

### Step 1: 解包
```bash
python3 scripts/office/unpack.py document.docx unpacked/
```

### Step 2: 编辑XML

编辑 `unpacked/word/` 下的文件。使用"智能引号"处理新内容：
- `&#x2018;` → ' (左单)
- `&#x2019;` → ' (右单/撇号)
- `&#x201C;` → " (左双)
- `&#x201D;` → " (右双)

**追踪修订**（插入）：
```xml
<w:ins w:id="1" w:author="Claude" w:date="2025-01-01T00:00:00Z">
  <w:r><w:t>inserted text</w:t></w:r>
</w:ins>
```

**追踪修订**（删除）：
```xml
<w:del w:id="2" w:author="Claude" w:date="2025-01-01T00:00:00Z">
  <w:r><w:delText>deleted text</w:delText></w:r>
</w:del>
```

### Step 3: 打包
```bash
python3 scripts/office/pack.py unpacked/ output.docx --original document.docx
```
