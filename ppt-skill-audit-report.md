# PPT Skill 文档吹牛审计报告

**审计时间**: 2026-06-26
**审计范围**: `/opt/data/skills/productivity/pptx/SKILL.md`, `/opt/data/skills/codex-ppt/SKILL.md`, `/opt/data/skills/productivity/wps-office/SKILL.md`, `/opt/data/skills/knowledge/wps-office/SKILL.md`

---

## 一、`/opt/data/skills/productivity/pptx/SKILL.md` — 严重吹牛

### 1.1 核心问题：声称25种麦肯锡布局，代码里根本没有

**文档声称** (`/opt/data/skills/productivity/pptx/SKILL.md` 第9-34行):

```
## 麦肯锡25种布局
1. add_cover_slide — 封面
2. add_agenda_slide — 目录
3. add_section_header — 章节封面
4. add_two_column_slide — 双栏文本
5. add_three_column_slide — 三栏内容
6. add_text_slide — 单文字页
7. add_image_text_slide — 图文混排        ← 代码里不存在！
8. add_chart_slide — 图表页              ← 代码里不存在！
9. add_table_slide — 表格页              ← 代码里不存在！
10. add_quote_slide — 引言页
11. add_icon_slide — 图标+文字           ← 代码里不存在！
12. add_comparison_slide — 对比页        ← 实际是 add_comparison_table / add_pros_cons
13. add_timeline_slide — 时间轴          ← 实际是 add_phases_chevron_3 等
14. add_process_slide — 流程页           ← 实际是 add_process_flow_horizontal
15. add_metrics_slide — 指标展示         ← 代码里不存在！
16. add_contact_slide — 联系页           ← 代码里不存在！
17. add_pros_cons_slide — 优劣势对比     ← 实际是 add_pros_cons
18. add_statement_slide — 核心理念页     ← 代码里不存在！
19. add_full_image_slide — 全图背景       ← 代码里不存在！
20. add_footer_slide — 页脚页             ← 代码里不存在！
21. add_blank_slide — 空白页             ← 实际是内部 _blank()，非公开API
22. add_split_slide — 分栏带标题          ← 代码里不存在！
23. add_bullet_heavy_slide — 大段文字     ← 代码里不存在！
24. add_header_footer_slide — 页眉页脚   ← 代码里不存在！
25. add_phases_slide — 阶段展示           ← 代码里不存在！实际有 add_phases_chevron_3
```

### 1.2 代码实际情况

**mckinsey-pptx-main 真实导出函数 (共约40个)**:

| 真实函数名 | 存在于 |
|-----------|--------|
| `add_cover_slide` | ✅ structure_slides.py |
| `add_agenda` | ✅ structure_slides.py |
| `add_section_divider` | ✅ structure_slides.py (文档写成 add_section_header) |
| `add_stat_hero` | ✅ structure_slides.py |
| `add_quote_slide` | ✅ structure_slides.py |
| `add_comparison_table` | ✅ comparison_slides.py |
| `add_pros_cons` | ✅ comparison_slides.py |
| `add_two_column_compare` | ✅ comparison_slides.py (不同于文档说的 add_two_column_slide) |
| `add_phases_chevron_3` | ✅ timeline_slides.py |
| `add_phases_table_4` | ✅ timeline_slides.py |
| `add_waves_timeline_4` | ✅ timeline_slides.py |
| `add_gantt_timeline` | ✅ timeline_slides.py |
| `add_process_flow_horizontal` | ✅ process_extras.py |
| `add_funnel` | ✅ process_extras.py |
| `add_kpi_dashboard` | ✅ process_extras.py |
| `add_bubble_chart` | ✅ bubble_chart.py |
| `add_growth_share_matrix` | ✅ bubble_chart.py |
| `add_prioritization_matrix` | ✅ bubble_chart.py |
| `add_column_comparison` | ✅ column_chart.py |
| `add_column_simple_growth` | ✅ column_chart.py |
| `add_stacked_column_chart` | ✅ extra_charts.py |
| `add_grouped_column_chart` | ✅ extra_charts.py |
| `add_line_chart` | ✅ extra_charts.py |
| `add_dark_navy_summary` | ✅ summary_slide.py |
| `add_paragraph_summary` | ✅ executive_summary.py |
| `add_keytakeaway_summary` | ✅ executive_summary.py |
| `add_issue_tree` | ✅ org_charts.py |
| `add_org_chart` | ✅ org_charts.py |
| `add_assessment_table` | ✅ assessment_table.py |

**吹牛条目汇总（文档写了但代码没有）**:

| 文档声称 | 代码实际情况 |
|---------|--------------|
| `add_section_header` | ❌ 不存在（实际是 `add_section_divider`） |
| `add_two_column_slide` | ❌ 不存在（实际是 `add_two_column_compare`，参数不同） |
| `add_three_column_slide` | ❌ 根本不存在 |
| `add_text_slide` | ❌ 根本不存在 |
| `add_image_text_slide` | ❌ **根本不存在！会话记录 itself 记录了这个问题** |
| `add_chart_slide` | ❌ 根本不存在（只有具体图表函数如 add_bubble_chart） |
| `add_table_slide` | ❌ 根本不存在（只有 add_assessment_table） |
| `add_icon_slide` | ❌ 根本不存在 |
| `add_comparison_slide` | ❌ 不存在（实际是 add_comparison_table / add_pros_cons） |
| `add_timeline_slide` | ❌ 根本不存在（实际是 add_phases_chevron_3 等多个函数） |
| `add_process_slide` | ❌ 根本不存在（实际是 add_process_flow_horizontal） |
| `add_metrics_slide` | ❌ 根本不存在（实际是 add_kpi_dashboard） |
| `add_contact_slide` | ❌ 根本不存在 |
| `add_pros_cons_slide` | ❌ 不存在（实际是 add_pros_cons） |
| `add_statement_slide` | ❌ 根本不存在 |
| `add_full_image_slide` | ❌ **根本不存在！会话记录已确认** |
| `add_footer_slide` | ❌ 根本不存在 |
| `add_blank_slide` | ❌ 根本不存在（内部有 _blank 但非公开API） |
| `add_split_slide` | ❌ 根本不存在 |
| `add_bullet_heavy_slide` | ❌ 根本不存在 |
| `add_header_footer_slide` | ❌ 根本不存在 |
| `add_phases_slide` | ❌ 根本不存在（实际是 add_phases_chevron_3） |

### 1.3 脚本文件状态

| 文件 | 状态 |
|------|------|
| `/opt/data/scripts/gen_intro_ppt.py` | ✅ 存在，796行，包含真实MC布局调用 |
| `/opt/data/scripts/ppt_layouts.py` | ✅ 存在，226行，封装调用MC库函数 |
| `/opt/data/scripts/add_image_text_slide` | ❌ **不存在** |
| `/opt/data/scripts/add_full_image_slide` | ❌ **不存在** |

---

## 二、`/opt/data/skills/productivity/wps-office/SKILL.md` (knowledge版) — 吹牛

**文档声称** (第108-124行):

```
### 3.3 25种MC布局
| # | 布局类型 | # | 布局类型 |
|---|----------|---|----------|
| 1 | 封面 | 14 | 金字塔 |
| 2 | 目录 | 15 | 矩阵 |
| 3 | 章节 | 16 | 流程图 |
| 4 | 过渡页 | 17 | SWOT |
| 5 | 文字 | 18 | 波特五力 |
| 6 | 大数字 | 19 | 甘特图 |
| 7 | 图片 | 20 | 饼图 |
| 8 | 两栏对比 | 21 | 柱状图 |
| 9 | 三栏对比 | 22 | 折线图 |
| 10 | 四宫格 | 23 | 地图 |
| 11 | 六宫格 | 24 | 表单 |
| 12 | 时间轴 | 25 | 结束页 |
| 13 | 循环图 | | |
```

**问题**:
- 这不是函数名列表，而是"布局类型"名称，但仍然存在问题
- `SWOT`、`波特五力`、`金字塔`、`矩阵`、`流程图`、`地图`、`表单` — 这些在mckinsey库里都不是独立函数名
- 文档说 `gen_intro_ppt.py` 有"25种MC布局"，但该脚本调用的MC库函数数量远少于25个，且没有任何一个叫"SWOT"或"波特五力"的函数

---

## 三、`/opt/data/skills/productivity/pptx/SKILL.md` 吹牛条目统计

| 吹牛类型 | 数量 |
|---------|------|
| 根本不存在的函数名 | ~20个 |
| 存在但名字错误的 | ~5个 |
| 实际存在的函数 | ~5个（add_cover_slide, add_agenda, add_quote_slide, add_stat_hero, add_pros_cons 等） |

**结论**: 文档声称25种布局，实际可对应的真实函数约5-8个（且部分名字对不上），其余全部是吹牛。

---

## 四、`/opt/data/skills/codex-ppt/SKILL.md` — 基本属实

该skill文档描述的是一套**基于AI图片生成+PPT组装的工作流**，脚本文件:
- `prepare_slide_prompts.py` ✅ 存在
- `assemble_ppt.py` ✅ 存在

没有明显的"吹牛"条目，文档描述与代码功能基本吻合。

---

## 五、建议

1. **立即修正** `/opt/data/skills/productivity/pptx/SKILL.md` — 删除所有不存在的函数名，改为列出实际存在的函数
2. **立即修正** `/opt/data/skills/knowledge/wps-office/SKILL.md` 第3.3节 — 删除"25种MC布局"表格中不存在的条目
3. 如果需要 `add_image_text_slide` 和 `add_full_image_slide`，需要**实际开发**这些功能，不能只写在文档里
