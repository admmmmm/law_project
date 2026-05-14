# frontend_v2 设计验收报告

## 1. frontend_v2 基本信息

- frontend_v2 路径：`frontend_v2`
- 技术栈：Vue 3、Vue Router、Vite、TypeScript、lucide-vue-next。`package.json` 仍保留 React 相关依赖，但当前 `src/main.ts` 使用 Vue 挂载。
- package scripts：`dev`、`build`、`preview`、`clean`、`lint`
- router 文件：`frontend_v2/src/router.ts`
- layout/sidebar 文件：`frontend_v2/src/App.vue`、`frontend_v2/src/components/Sidebar.vue`、`frontend_v2/src/components/CaseSpaceSidebar.vue`、`frontend_v2/src/components/Header.vue`
- views 目录：`frontend_v2/src/views`

## 2. 实际路由表

初检时 `router.ts` 存在 Git 冲突标记，导致路由不可用。冲突两侧分别是旧版 `/graph`、`/portrait`、`/intelligence` 直连页面，以及新版 Workspace / Case Space 路由。

| 路径 | 页面组件 | 用途 | 是否有效 | 问题 |
|---|---|---|---|---|
| `/` | redirect | 进入我的案件 | 修复前无效 | router 冲突 |
| `/cases` | `MyCases.vue` | 我的案件 | 修复前不可编译 | 依赖缺失 API 封装 |
| `/cases/new` | `CreateCase.vue` | 新建案件 | 修复前不可编译 | 依赖缺失 API/进度条组件 |
| `/cases/:caseId` | `CaseOverview.vue` | 案件概览 | 部分实现 | 未接 `/overview` |
| `/cases/:caseId/graph` | `Graph.vue` | 案件证据地图 | 不符合设计 | 静态演示图，未接 `layers` |
| `/cases/:caseId/intelligence` | `Intelligence.vue` | 智能分析入口 | 可作为入口 | 内部仍是旧演示结构，本阶段不改 |
| `/cases/:caseId/portrait` | `Portrait.vue` | 信息画像入口 | 可作为入口 | 内部仍是旧演示结构，本阶段不改 |
| `/skills` | 缺失 | 检察技能库 | 修复前无效 | 缺 `SkillLibrary.vue` |
| `/skills/editor` | `SkillEditor.vue` | 技能编辑 | 部分实现 | 保存暂未接后端 |
| `/skills/:skillName` | `SkillDetail.vue` | 技能详情 | 部分实现 | 依赖 API 封装 |
| `/knowledge/legal` | `KnowledgePage.vue` | 法律知识 | 修复前无效 | 引用缺失 `LegalKnowledge.vue` |
| `/knowledge/practice` | `KnowledgePage.vue` | 实务知识 | 部分实现 | 占位为主 |
| `/settings` | `Settings.vue` | 设置 | 可用 | 占位页 |

## 3. 实际左侧卡片 / 菜单结构

- 工作台菜单目标结构已在 `Sidebar.vue` 的新版冲突分支中出现：我的案件、新建案件、检察技能库、知识库、设置。
- 案件空间菜单在 `CaseSpaceSidebar.vue` 中已基本符合设计：案件概览、案件证据地图、智能分析、信息画像；证据地图含文件证据图、片段证据图、原始图谱层子卡片。
- 修复前 `Sidebar.vue` 带冲突标记，实际不可编译。
- 修复前存在页面有路由但缺组件的问题：`SkillLibrary.vue`、`LegalKnowledge.vue`、`api/backend.ts`、`AsyncProgressBar.vue`、`useSimulatedProgress.ts`。

## 4. 工作台验收

| 需求 | 是否实现 | 证据文件 | 问题 | 建议 |
|---|---|---|---|---|
| 我的案件 | 部分实现 | `views/MyCases.vue` | 依赖缺失 API 封装 | 补 `api/backend.ts` |
| 新建案件两步流程 | 部分实现 | `views/CreateCase.vue` | 依赖缺失进度组件/API | 补依赖，保留流程 |
| 检察技能库 | 未完整实现 | `SkillDetail.vue`、`SkillEditor.vue` | 缺浏览页 | 新增 `SkillLibrary.vue` |
| 浏览技能 | 未实现 | 无 | 缺页面 | 新增列表、搜索、标签筛选 |
| 技能编辑 | 部分实现 | `views/SkillEditor.vue` | 保存为占位 | P0 保持占位可用 |
| 知识库 | 部分实现 | `views/KnowledgePage.vue` | 法律知识组件缺失 | 新增轻量 `LegalKnowledge.vue` |
| 法律知识 | 未实现 | 无 | 组件缺失 | 新增只读/上传入口 |
| 实务知识 | 部分实现 | `views/KnowledgePage.vue` | 静态占位 | P0 可接受 |
| 设置 | 已实现 | `views/Settings.vue` | 占位 | P0 可接受 |

## 5. 案件概览验收

| 需求 | 是否实现 | 证据文件 | 问题 | 建议 |
|---|---|---|---|---|
| 当前案件信息 | 部分实现 | `CaseOverview.vue` | 从案件列表反查，不稳 | 接 `/overview` |
| 统计卡片 | 部分实现 | `CaseOverview.vue` | 统计字段少 | 使用 overview.stats |
| 已导入证据列表 | 部分实现 | `CaseOverview.vue` | 未显示 NAME / BRIEF / ID | 使用 overview.recent_evidence |
| 点击证据详情 | 未实现 | `CaseOverview.vue` | 无详情接口调用 | 接 `/evidence/{evidence_id}` |
| 推荐下一步 | 部分实现 | `CaseOverview.vue` | 前端自行推断 | 使用 overview.next_step |
| 空状态 / 错误状态 | 部分实现 | `CaseOverview.vue` | 基本可用 | 保留并增强 |
| 是否接入 `/overview` | 未实现 | `CaseOverview.vue` | 仍调用 listCases/listEvidence | P0 必修 |

## 6. 案件证据地图验收

| 需求 | 是否实现 | 证据文件 | 问题 | 建议 |
|---|---|---|---|---|
| 左侧三个子图层 | 已实现 | `CaseSpaceSidebar.vue` | 无明显问题 | 保留 |
| 顶部不放图层切换 | 未实现 | `Graph.vue` | 当前是静态演示布局 | 重写 P0 图谱页 |
| 顶部只有树形 / 力导 / 导出截图 | 未实现 | `Graph.vue` | 顶部是跨案碰撞等按钮 | 替换为设计要求 |
| 图谱图例 | 部分实现 | `Graph.vue` | 静态错误图例 | 接 layers.legend |
| 图例随图层变化 | 未实现 | `Graph.vue` | 无真实图层 | 新增 `LegendPanel.vue` |
| 右侧信息栏简化 | 未实现 | `Graph.vue` | 大段演示文案 | 改为选中详情 |
| 节点/边选中详情 | 未实现 | `Graph.vue` | 静态不可选 | SVG 节点/边点击 |
| 原始图谱层编辑 | 未实现 | `Graph.vue` | 无 CRUD | 只在 raw 层显示维护区 |
| 文件/片段图只读 | 未实现 | `Graph.vue` | 无真实层级控制 | 根据 `editable` 控制 |
| 调试信息隐藏 | 不适用 | `Graph.vue` | 当前没有 G6 调试字段，但有演示噪声 | 重写页面 |

## 7. 智能分析 / 信息画像入口

`Intelligence.vue` 和 `Portrait.vue` 存在，但仍是旧演示式页面。本阶段只保证路由入口可达，不重做内部结构。

## 8. 最大差距

### P0 必须修

1. `router.ts`、`Sidebar.vue`、`Header.vue`、`style.css` 冲突标记导致构建失败。
2. 缺失 `api/backend.ts` 等共享依赖。
3. 缺失 `SkillLibrary.vue`、`LegalKnowledge.vue`。
4. 案件概览未接 `/overview`。
5. 证据地图未接 `/evidence-map.layers`，仍是静态图。
6. 证据地图图例、右侧详情、raw 层 CRUD 缺失。

### P1 建议修

1. 智能分析和画像页仍然像旧技术 demo。
2. package 里 React 依赖与 Vue 项目定位不一致。
3. 技能编辑保存、知识库上传仍是占位。

### P2 后续优化

1. 接入更成熟图谱可视化组件。
2. 统一错误提示、加载骨架屏、toast。
3. 增强移动端和宽屏适配。

## 9. 效果评价

1. frontend_v2 的目标结构已经在局部代码中出现，但修复前不可构建。
2. 页面理念比旧版更清楚，但 Graph 页和分析/画像页仍明显是技术演示。
3. 案件概览需要接后端 overview 才像单案首页。
4. 证据地图需要使用 layers 结构后才能真正简化。
5. 最不适合演示的是当前 `Graph.vue` 静态暗色演示页和智能分析/画像的旧占位内容。

## 10. P0 修复结果

- 已清理 `router.ts`、`Sidebar.vue`、`Header.vue`、`style.css` 中的冲突标记。
- 已补齐 `api/backend.ts`、`AsyncProgressBar.vue`、`useSimulatedProgress.ts` 等缺失依赖。
- 已新增 `SkillLibrary.vue` 和 `LegalKnowledge.vue`，保证工作台入口均有真实页面。
- `CaseOverview.vue` 已改为优先调用 `GET /api/v1/cases/{case_id}/overview`，并展示 stats、next_step、recent_evidence；点击证据会调用详情接口。
- `Graph.vue` 已从静态演示图改为调用 `GET /api/v1/cases/{case_id}/evidence-map`，使用 `layers.document/passage/raw`。
- 证据地图图层切换由左侧 `CaseSpaceSidebar.vue` 的 query 控制；顶部只保留树形、力导、导出截图。
- 新增 `LegendPanel.vue`，图例读取当前 layer 的 legend。
- 原始图谱层才显示新增/编辑/删除节点和关系；文件证据图、片段证据图保持只读提示。
- `npm run build` 通过。
- `npm run lint` 通过。
