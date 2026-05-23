---
name: xlsx
description: 处理电子表格文件的任何任务。触发：打开/编辑/修复.xlsx/.xlsm/.csv/.tsv文件（加列/计算公式/格式化/清理脏数据）；从零创建电子表格；转换表格格式；在电子表格文件中查找替换；财务建模。需要输出电子表格文件时使用。
triggers:
  - "excel"
  - "xlsx"
  - "电子表格"
  - "spreadsheet"
  - "表格"
  - "财务模型"
---

# XLSX creation, editing, and analysis

## 重要要求

### 字体
- 所有交付物使用一致的专业字体（如Arial），除非用户另有说明

### 零公式错误
- **每个Excel文件必须有零公式错误** (#REF!, #DIV/0!, #VALUE!, #N/A, #NAME?)

### 保留现有模板
- 修改文件时研究和匹配现有格式、样式和约定
- 永远不要对有既定模式的文件施加标准化格式
- 现有模板约定**永远**优先于本指南

---

## 输出质量标准

### 金融模型配色规范（除非另有说明）

| 颜色 | 含义 |
|------|------|
| **蓝色文本 (RGB: 0,0,255)** | 硬编码输入，用户会改动的数字 |
| **黑色文本 (RGB: 0,0,0)** | 所有公式和计算 |
| **绿色文本 (RGB: 0,128,0)** | 同一工作簿内从其他工作表拉取的链接 |
| **红色文本 (RGB: 255,0,0)** | 外部链接到其他文件的链接 |
| **黄色背景 (RGB: 255,255,0)** | 需要注意的关键假设或需要更新的单元格 |

### 数字格式标准

- **年份**：格式化为文本字符串（如 "2024" 而非 "2,024"）
- **货币**：使用 `$#,##0` 格式；在表头注明单位（如 "Revenue ($mm)"）
- **零值**：格式化为 "–"（包括百分比）
- **百分比**：默认 `0.0%` 格式（一位小数）
- **倍数**：格式化为 0.0x（EV/EBITDA、P/E等估值倍数）
- **负数**：用括号 (123) 而非减号 -123

### 假设放置规则
- 将所有假设（增长率、利润率、倍数等）放在独立的假设单元格
- 公式中使用单元格引用而非硬编码值
- 示例：`=B5*(1+$B$6)` 而不是 `=B5*1.05`

---

## 工具选择

| 工具 | 适用场景 |
|------|----------|
| **pandas** | 数据分析、大量操作、简单数据导出 |
| **openpyxl** | 复杂格式化、公式、Excel特定功能 |

---

## 使用 openpyxl

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

wb = Workbook()
sheet = wb.active

# 添加数据
sheet['A1'] = 'Hello'
sheet['B1'] = 'World'
sheet.append(['Row', 'of', 'data'])

# 添加公式（用Excel公式，不是Python计算）
sheet['B2'] = '=SUM(A1:A10)'

# 格式化
sheet['A1'].font = Font(bold=True, color='0000FF')  # 蓝色=输入
sheet['B2'].font = Font(color='000000')             # 黑色=公式
sheet['A1'].fill = PatternFill('solid', start_color='FFFF00')  # 黄色背景=关键假设

# 列宽
sheet.column_dimensions['A'].width = 20

wb.save('output.xlsx')
```

### 编辑现有文件
```python
from openpyxl import load_workbook

wb = load_workbook('existing.xlsx')
sheet = wb.active

sheet['A1'] = 'New Value'
sheet.insert_rows(2)
sheet.delete_cols(3)

wb.save('modified.xlsx')
```

---

## 公式重算（使用公式后必须执行）

openpyxl创建的文件公式以字符串保存，但无计算值。**必须**用脚本重算：

```bash
python3 /opt/data/scripts/xlsx/recalc.py output.xlsx
```

脚本返回JSON：
```json
{
  "status": "success",           // 或 "errors_found"
  "total_errors": 0,
  "total_formulas": 42,
  "error_summary": {              // 仅在发现错误时存在
    "#REF!": {
      "count": 2,
      "locations": ["Sheet1!B5", "Sheet1!C10"]
    }
  }
}
```

如果状态是 `errors_found`，修复错误后重新运行重算脚本。

---

## 公式验证检查清单

### 必须验证
- [ ] 测试2-3个样本引用，确认正确取值
- [ ] 确认列映射正确（如列64 = BL，不是BK）
- 记住Excel行是1索引的

### 常见陷阱
- [ ] **NaN处理**：用 `pd.notna()` 检查空值
- [ ] **远右列**：FY数据常在列50+
- [ ] **除零**：除法前检查分母（#DIV/0!）
- [ ] **错误引用**：验证所有引用指向目标单元格（#REF!）
- [ ] **跨工作表引用**：格式为 `Sheet1!A1`

### 测试策略
- [ ] **从小开始**：先在2-3个单元格测试公式，再全面应用
- [ ] **验证依赖**：检查公式引用的所有单元格存在
- [ ] **测边界情况**：包含零、负数和超大值
