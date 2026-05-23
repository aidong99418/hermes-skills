---
name: pdf
description: PDF处理完整技能——合并/拆分/OCR/加水印/加密/创建/表格提取。触发词：PDF报告、PDF转换、PDF编辑、生成PDF、导出PDF。源：anthropics/skills，脚本路径：/opt/data/scripts/pdf/
triggers:
  - PDF
  - pdf
  - PDF报告
  - PDF转换
  - PDF编辑
  - 生成PDF
  - 导出PDF
  - 合并PDF
  - 拆分PDF
  - PDF加密
  - PDF解密
  - PDF签名
  - PDF提取文字
  - PDF提取表格
skills:
  - name: pdf
    source: anthropics/skills
---

# PDF 技能

## 快速参考

| 任务 | 工具 | 命令/代码 |
|------|------|-----------|
| 合并PDF | pypdf | `writer.add_page(page)` |
| 拆分PDF | pypdf | 逐页写出 |
| 提取文字 | pdfplumber | `page.extract_text()` |
| 提取表格 | pdfplumber | `page.extract_tables()` |
| 创建PDF | reportlab | Canvas或Platypus |
| 命令行合并 | qpdf | `qpdf --empty --pages ...` |
| OCR扫描件 | pytesseract | 转图片后OCR |
| PDF表单填充 | pypdf/pdftk | 见表单脚本 |

## 依赖

```bash
pip install pypdf pdfplumber reportlab pytesseract Pillow pdf2image
apt install poppler-utils qpdf tesseract-ocr tesseract-ocr-chi-sim
```

## 常用操作

### 合并PDF
```python
from pypdf import PdfWriter, PdfReader

writer = PdfWriter()
for pdf_file in ["doc1.pdf", "doc2.pdf"]:
    reader = PdfReader(pdf_file)
    for page in reader.pages:
        writer.add_page(page)

with open("merged.pdf", "wb") as output:
    writer.write(output)
```

### 拆分PDF
```python
reader = PdfReader("input.pdf")
for i, page in enumerate(reader.pages):
    writer = PdfWriter()
    writer.add_page(page)
    with open(f"page_{i+1}.pdf", "wb") as output:
        writer.write(output)
```

### 提取文字
```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        print(text)
```

### 提取表格
```python
import pdfplumber, pandas as pd

with pdfplumber.open("document.pdf") as pdf:
    all_tables = []
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            if table:
                df = pd.DataFrame(table[1:], columns=table[0])
                all_tables.append(df)
    combined_df = pd.concat(all_tables, ignore_index=True)
    combined_df.to_excel("tables.xlsx", index=False)
```

### 创建PDF
```python
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

doc = SimpleDocTemplate("report.pdf", pagesize=letter)
styles = getSampleStyleSheet()
story = []
story.append(Paragraph("报告标题", styles['Title']))
story.append(Spacer(1, 12))
story.append(Paragraph("正文内容", styles['Normal']))
doc.build(story)
```

> ⚠️ **注意**: ReportLab内置字体不支持Unicode下标/上标（如H₂O），需用 `<sub>` / `<super>` XML标签替代。

### 命令行工具
```bash
# 提取文字
pdftotext -layout input.pdf output.txt

# 合并
qpdf --empty --pages file1.pdf file2.pdf -- merged.pdf

# 解密
qpdf --password=mypassword --decrypt encrypted.pdf decrypted.pdf

# 转图片（OCR前置）
pdftoppm -jpeg -r 200 input.pdf slide
```

## 本地脚本

| 脚本 | 用途 |
|------|------|
| `/opt/data/scripts/pdf/convert_pdf_to_images.py` | PDF转图片 |
| `/opt/data/scripts/pdf/check_fillable_fields.py` | 检查PDF表单字段 |
| `/opt/data/scripts/pdf/extract_form_structure.py` | 提取表单结构 |
| `/opt/data/scripts/pdf/fill_fillable_fields.py` | 填充表单字段 |

## 注意事项

- 扫描件PDF需要OCR（pytesseract）
- 涉及中文PDF需安装 `tesseract-ocr-chi-sim`
- PDF加密用 `writer.encrypt("userpw", "ownerpw")`
- 复杂表格建议用 pdfplumber 的 `page.extract_tables()` 而不是正则
