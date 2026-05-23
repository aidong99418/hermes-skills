# AI前端审美设计原则（taste-skill）

## 核心三旋钮

AI生成UI时的可调参数，基线值：(8, 6, 4)

| 旋钮 | 范围 | 含义 |
|------|------|------|
| DESIGN_VARIANCE | 1-10 | 布局多样性：1=对称整洁，10=艺术混乱 |
| MOTION_INTENSITY | 1-10 | 动效强度：1=静态，10=电影级动效 |
| VISUAL_DENSITY | 1-10 | 视觉密度：1=画廊级留白，10=仪表盘级紧凑 |

## 防AI审美偏见7条铁律

1. **禁用AI紫色/霓虹风**：不能用紫蓝渐变发光按钮，用中性底色+单一高对比色（Emerald/Electric Blue/Deep Rose）
2. **禁用Inter字体**：要用Geist/Outfit/Satoshi等独特字体，仪表盘只用Sans-Serif
3. **禁用居中Hero布局**（DESIGN_VARIANCE>4时）：强制用分屏/左右不对称
4. **卡片少用**：数据密集界面用border-t/divide-y分組，不用卡片盒子
5. **全交互状态**：必须实现Loading骨架屏/Empty状态/Error状态/Tactile按压反馈
6. **Liquid Glass效果**：backdrop-blur时要加1px内边框和内阴影模拟物理折射
7. **禁用纯黑**：永远不用#000000，用Off-Black/Zinc-950/Charcoal

## 字体层级
- **标题**：text-4xl md:text-6xl tracking-tighter leading-none，用Geist/Outfit/Satoshi
- **正文**：text-base text-gray-600 leading-relaxed max-w-[65ch]
- **仪表盘禁用Serif**：只用Sans-Serif配对（Geist + Geist Mono 或 Satoshi + JetBrains Mono）

## 布局规则
- 页面容器：`max-w-[1400px] mx-auto` 或 `max-w-7xl`
- Hero全高用`min-h-[100dvh]`（不用h-screen，iOS Safari会跳动）
- 不用复杂flexbox数学，用CSS Grid（`grid grid-cols-1 md:grid-cols-3 gap-6`）
- 禁用3栏等宽卡片布局，改用2栏Zig-Zag或不对称网格

## 动效规则
- 始终用Framer Motion的Spring Physics（`stiffness: 100, damping: 20`），禁用linear easing
- 不用`window.addEventListener('scroll')`，用Framer Motion hooks
- 列表/网格用staggerChildren顺序入场动画
- 按钮按下用`-translate-y-[1px]`或`scale-[0.98]`物理反馈

## 性能红线
- grain/noise滤镜只能用在`pointer-events-none`的伪元素上
- 动画只用transform和opacity，不用top/left/width/height
- 图标用@phosphor-icons/react或@radix-ui/react-icons，统一strokeWidth

## AI内容防假
- 禁用John Doe/Sarah Chan等假名，用真实创意姓名
- 禁用SVG鸡蛋头像，用真实风格占位图
- 禁用99.99%/50%等假数字，用自然凌乱数据（47.2%）
- 禁用Acme/Nexus等虚假品牌名

> 来源：[Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) 3400+ stars，AI前端反Slop框架
