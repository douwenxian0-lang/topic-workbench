# 小红书图文 · 图卡制作流程（info-card-systems 技能）

每套图卡 = 本目录下一个文件夹，渲染出的 PNG 自动上工作台看板。

## 怎么做（对 WorkBuddy 说一句话即可）

- 「帮我把 articles/ 里的某篇文章做成小红书图卡」
- 「做一套图卡：主题 xxx，用索引体」
- 触发词：**做图卡 / 小红书图文 / 资讯卡片 / 快报体 / 索引体 / 卡片体**

Agent 会走 info-card-systems 技能（装在 ~/.workbuddy/skills/info-card-systems）：
① 拆页面计划 → ② 选体系（快报体=单条结论 / 卡片体=场景分类 / 索引体=榜单清单）→ ③ 先写文案 → ④ 复制种子模板改内容 → ⑤ 渲染出图。

## 目录约定

```
social-cards/
└── <套名>/            ← 一个文件夹 = 一套图卡
    ├── index.html     ← 技能产出的页面（可留可删）
    └── output/        ← render.mjs 输出的 PNG（看板自动收录）
```

- 看板取 output/ 里第 1 张当封面，页数自动统计
- 文件夹里放 `status.txt`（写：制作中 / 待发布 / 已发布）可标状态
- 手动渲染：`node ~/.workbuddy/skills/info-card-systems/scripts/render.mjs <套名文件夹>`
