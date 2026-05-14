# 前端重设计资料整理

本文档基于当前 `law_project/frontend` 真实代码整理，面向后续“重新设计前端信息架构和交互逻辑”的智能体。重点不是评价代码优劣，而是说明当前页面、路由、数据流、核心组件和重设计约束。

## 1. 前端技术栈概览

| 类型 | 当前情况 | 判断依据 |
|---|---|---|
| 前端框架 | Vue 3，使用 `<script setup lang="ts">` | `frontend/package.json`、`frontend/src/main.ts`、各 `.vue` 文件 |
| 构建工具 | Vite 6 | `frontend/package.json` 中 `vite`、`@vitejs/plugin-vue` |
| 路由 | Vue Router，单文件路由配置 | `frontend/src/router.ts` |
| 状态管理 | 未见 Pinia/Vuex；主要使用 Vue `ref/computed/reactive` + `localStorage` | `frontend/src/views/*.vue`、`frontend/src/workspace.ts` |
| UI 组件库 | 未见完整 UI 组件库；主要为自写 CSS/Tailwind 风格类 | `frontend/src/style.css`、各页面 scoped style |
| 图谱可视化 | 同时使用 `relation-graph/vue3` 与 `@antv/g6` | `frontend/package.json`、`frontend/src/views/Graph.vue`、`frontend/src/components/G6EvidenceGraph.vue` |
| 请求封装 | 原生 `fetch` 封装为 `backendApi` | `frontend/src/api/backend.ts` |
| 图标/辅助依赖 | `lucide-vue-next` 已安装；项目中 React 相关依赖也存在，但主应用是 Vue | `frontend/package.json` |
| 自动截图/测试 | Playwright 依赖与截图脚本存在 | `frontend/package.json`、`frontend/scripts/*` |

需要注意：`frontend/src/router` 目录不存在，实际路由在 `frontend/src/router.ts`。`layouts`、`services`、`stores`、`store`、`utils` 目录未见。

---

## 2. src 目录结构摘要

```text
frontend/src
├── api
│   └── backend.ts
├── components
│   ├── AsyncProgressBar.vue
│   ├── G6EvidenceGraph.vue
│   ├── Header.vue
│   └── Sidebar.vue
├── composables
│   └── useSimulatedProgress.ts
├── views
│   ├── Chat.vue
│   ├── Dashboard.vue
│   ├── Graph.vue
│   ├── Intelligence.vue
│   ├── LegalKnowledge.vue
│   ├── Portrait.vue
│   └── SkillLibrary.vue
├── App.vue
├── env.d.ts
├── main.ts
├── router.ts
├── style.css
└── workspace.ts
```

不存在或未见：

- `frontend/src/router/`
- `frontend/src/layouts/`
- `frontend/src/services/`
- `frontend/src/stores/`
- `frontend/src/store/`
- `frontend/src/utils/`
- `frontend/src/main.js`

---

## 3. 当前路由表

真实路由定义来自 `frontend/src/router.ts`。

| 路径 | 页面组件 | 页面名称/推测用途 | 是否案件内页面 | 备注 |
|---|---|---|---|---|
| `/` | `Dashboard.vue` | 案件导入 / 案件工作台 | 否 | 默认首页 |
| `/legal-knowledge` | `LegalKnowledge.vue` | 法律知识库 | 否 | 仅根路径注册 |
| `/graph` | `Graph.vue` | 案件证据地图 | 是，依赖 `active_case_id` | 不带 caseId 的全局入口，内部从 localStorage 取案件 |
| `/portrait` | `Portrait.vue` | 画像报告 / 事实画像 | 是，依赖 `active_case_id` | 不带 caseId 的全局入口 |
| `/intelligence` | `Intelligence.vue` | 智能分析 | 是，依赖 `active_case_id` | 不带 caseId 的全局入口 |
| `/chat` | `Chat.vue` | 证据问答 / RAG 对话 | 是，依赖 `active_case_id` | 调试与问答入口 |
| `/:workspaceId` | `Dashboard.vue` | 某案件或临时工作空间首页 | 是 | `beforeEach` 会解析 workspace 并设置 `active_case_id` |
| `/:workspaceId/graph` | `Graph.vue` | 某案件证据地图 | 是 | 支持普通 caseId 或 `tmp_` 临时合并工作空间 |
| `/:workspaceId/portrait` | `Portrait.vue` | 某案件画像页 | 是 | 依赖 workspace 解析 |
| `/:workspaceId/intelligence` | `Intelligence.vue` | 某案件智能分析 | 是 | 依赖 workspace 解析 |
| `/:workspaceId/chat` | `Chat.vue` | 某案件证据问答 | 是 | 依赖 workspace 解析 |
| `/:pathMatch(.*)*` | `Dashboard.vue` | 兜底页 | 否 | 未注册页面会回到 Dashboard |

重要不一致：

- `SkillLibrary.vue` 存在，但 `router.ts` 未注册 `/skills` 或 `/:workspaceId/skills`。
- `Sidebar.vue` 有“检察技能库”“分析上下文”“设置”入口，但 `router.ts` 没有对应路由；点击后会被兜底到 Dashboard。
- `Sidebar.vue` 的 `linkTo('legal-knowledge')` 在案件工作空间下会生成 `/:workspaceId/legal-knowledge`，但该路由未注册，因此也会落入兜底 Dashboard。

---

## 4. 当前主要页面说明

### 页面：Dashboard.vue

- 文件路径：`frontend/src/views/Dashboard.vue`
- 路由路径：`/`、`/:workspaceId`
- 页面用途：案件管理、案件创建、罪名选择、证据批量导入、运行分析、进入图谱/画像/智能分析。
- 用户能做什么：
  - 新建默认案件或自定义案件。
  - 选择、删除案件。
  - 选择罪名模板。
  - 通过文件夹或压缩包导入证据。
  - 运行分析并进入案件证据地图。
  - 进入法律知识库、图谱、画像、智能分析。
- 主要状态变量：
  - `cases`
  - `offenseTemplates`
  - `selectedCaseId`
  - `batchResult`
  - `analysisSummary`
  - `importInProgress`
  - `customCase`
  - `loading/error`
- 主要调用 API：
  - `backendApi.listCases`
  - `backendApi.createCase`
  - `backendApi.createCustomCase`
  - `backendApi.deleteCase`
  - `backendApi.updateCase`
  - `backendApi.listOffenseTemplates`
  - `backendApi.ingestBatch`
  - `backendApi.ingestArchive`
  - `backendApi.runAnalysis`
- 依赖的核心组件：无复杂子组件，主要自写页面逻辑。
- 页面复杂度评价：高。
- 是否适合作为主流程页面：适合，但需要拆分“案件管理”和“证据导入”。
- 是否更适合作为高级/调试页面：否，是主流程入口。
- 重设计建议：
  - 改成“案件工作台”首屏，突出 3 个核心动作：选择案件、导入证据、进入分析。
  - 罪名选择应留在案件基础信息区，不与导入按钮混在一起。
  - 导入结果和分析运行结果可以折叠，避免首页过重。

### 页面：Graph.vue

- 文件路径：`frontend/src/views/Graph.vue`
- 路由路径：`/graph`、`/:workspaceId/graph`
- 页面用途：案件证据地图、原始事实图谱、图谱筛选、图谱维护、G6/RelationGraph 切换、演示视角。
- 用户能做什么：
  - 切换文件层、片段层、原始层。
  - 切换 RelationGraph / G6。
  - 切换树形 / 力导布局。
  - 运行分析、刷新图谱。
  - 按标签筛选节点/关系。
  - 使用核心邻域、邻域扩展、多跳召回、子图交叉等演示视角。
  - 查看选中节点/边详情。
  - 新增/更新/删除/标记已核节点和关系。
  - 导出截图。
- 主要状态变量：
  - `mapLayer`
  - `layoutModeByLayer`
  - `layoutMode`
  - `useG6`
  - `viewMode`
  - `demoMode`
  - `graph`
  - `evidenceMap`
  - `selectedNode`
  - `selectedLine`
  - 各类筛选、编辑表单和渲染数据。
- 主要调用 API：
  - `backendApi.getEvidenceMap`
  - `backendApi.getGraph`
  - `backendApi.getMergedGraph`
  - `backendApi.runAnalysis`
  - `backendApi.applyGraphIntervention`
- 依赖的核心组件：
  - `relation-graph/vue3`
  - `frontend/src/components/G6EvidenceGraph.vue`
- 页面复杂度评价：极高。
- 是否适合作为主流程页面：适合保留一个“证据地图”主入口，但当前页面承担太多职责。
- 是否更适合作为高级/调试页面：其中 G6、高级布局、维护表单、演示模式都更适合高级视图。
- 重设计建议：
  - 拆成“证据地图浏览”“原始图谱维护”“高级图谱实验/截图模式”三个层次。
  - 普通用户默认只看证据地图和少量推荐视角。
  - 图谱维护和性能调试不要直接暴露在主路径首屏。

### 页面：Intelligence.vue

- 文件路径：`frontend/src/views/Intelligence.vue`
- 路由路径：`/intelligence`、`/:workspaceId/intelligence`
- 页面用途：智能分析会话，包括假设验证、可疑资金流两类对话式分析。
- 用户能做什么：
  - 在“假设验证 / 可疑资金流”模式之间切换。
  - 新建分析会话。
  - 继续追问。
  - 删除会话。
  - 输入 `@` 选择证据，插入标准 evidence mention。
  - 展开检索与调用细节。
  - 点击有支撑的句子打开证据溯源抽屉。
- 主要状态变量：
  - `activeCaseId`
  - `activeMode`
  - `threads`
  - `threadDetail`
  - `selectedThreadId`
  - `evidence`
  - `showNewThread`
  - `newTitle/newQuestion`
  - `followup`
  - `mentionSuggestions`
  - `selectedSentence`
  - `retrievalDetails`
- 主要调用 API：
  - `backendApi.listAnalysisThreads`
  - `backendApi.createAnalysisThread`
  - `backendApi.getAnalysisThread`
  - `backendApi.addAnalysisThreadMessage`
  - `backendApi.deleteAnalysisThread`
  - `backendApi.listEvidence`
  - `backendApi.getRetrievalSession`
- 依赖的核心组件：无独立聊天组件，页面内部实现消息、检索详情和溯源抽屉。
- 页面复杂度评价：高。
- 是否适合作为主流程页面：适合。
- 是否更适合作为高级/调试页面：检索细节应默认折叠，详细工具调用更适合开发者/高级模式。
- 重设计建议：
  - 把“任务输入”“历史会话”“分析结果”“证据溯源”做成更清晰的四区布局。
  - `@证据` 已实现；`@技能包` 未见独立选择器和解析逻辑，不应在主 UI 中暗示完整实现，除非后续补齐。

### 页面：Portrait.vue

- 文件路径：`frontend/src/views/Portrait.vue`
- 路由路径：`/portrait`、`/:workspaceId/portrait`
- 页面用途：事实画像、人物关系画像、行为还原、规则命中、文件母图概览、证据溯源。
- 用户能做什么：
  - 生成/刷新事实画像。
  - 查看人物关系和行为还原叙述。
  - 查看并点击画像事实句做溯源。
  - 展开检索过程。
  - 查看文件母图节点、运行默认规则包、查看 findings。
  - 查看智能分析页采纳的疑点候选。
- 主要状态变量：
  - `activeCaseId`
  - `facts`
  - `traceOpen`
  - `selectedFact`
  - `traceEvidence`
  - `adoptedSuspicion`
  - `retrievalDetail`
  - `documentMother`
  - `ruleRuns`
  - `selectedMotherNode`
  - `selectedFinding`
- 主要调用 API：
  - `backendApi.getPortraitFacts`
  - `backendApi.getDocumentMotherGraph`
  - `backendApi.rebuildDocumentMotherGraph`
  - `backendApi.runRulePack`
  - `backendApi.getRetrievalSession`
  - `backendApi.getEvidenceDetail`
- 依赖的核心组件：无外部画像组件，页面内部实现卡片、规则、溯源。
- 页面复杂度评价：高。
- 是否适合作为主流程页面：适合，但应拆分“面向用户画像”和“文件母图/规则调试”。
- 是否更适合作为高级/调试页面：文件母图、规则运行细节、检索会话详情更适合高级区。
- 重设计建议：
  - 普通画像页只保留：目标对象、人物关系、行为事实、疑点提示、证据支撑。
  - 文件母图与规则调试迁移到“分析上下文/技能库/证据结构”高级页。

### 页面：Chat.vue

- 文件路径：`frontend/src/views/Chat.vue`
- 路由路径：`/chat`、`/:workspaceId/chat`
- 页面用途：证据问答 / RAG 对话。
- 用户能做什么：
  - 输入问题。
  - 调用后端问答接口。
  - 查看回答与来源片段。
- 主要状态变量：
  - `activeCaseId`
  - `draft`
  - `messages`
  - `loading/error`
- 主要调用 API：
  - `backendApi.chatAnalysis`
- 依赖的核心组件：无。
- 页面复杂度评价：中。
- 是否适合作为主流程页面：可作为“证据问答”辅助入口。
- 是否更适合作为高级/调试页面：目前更像调试/轻量问答。
- 重设计建议：
  - 可并入智能分析为“快速问答”模式，避免和 Intelligence 重复。

### 页面：LegalKnowledge.vue

- 文件路径：`frontend/src/views/LegalKnowledge.vue`
- 路由路径：`/legal-knowledge`
- 页面用途：法律知识库浏览、流程材料上传、检索。
- 用户能做什么：
  - 查看罪名模板。
  - 查看办案流程材料。
  - 新增流程/知识内容。
  - 上传知识材料。
  - 输入问题检索法律知识。
- 主要状态变量：
  - `offenseTemplates`
  - `procedureFlows`
  - `selectedOffenseId`
  - `query`
  - `result`
  - `newKnowledge`
  - `loading/error`
- 主要调用 API：
  - `backendApi.listOffenseTemplates`
  - `backendApi.listProcedureFlows`
  - `backendApi.createProcedureFlow`
  - `backendApi.uploadProcedureFlow`
  - `backendApi.retrieveLegalKnowledge`
- 依赖的核心组件：无。
- 页面复杂度评价：中。
- 是否适合作为主流程页面：不适合作为办案主流程；适合作为知识管理辅助页。
- 是否更适合作为高级/调试页面：普通用户可浏览；编辑/上传功能更适合管理员。
- 重设计建议：
  - 分成“只读知识浏览”和“知识维护上传”两种权限/模式。
  - 修正侧边栏工作空间路径与 router 不一致问题。

### 页面：SkillLibrary.vue

- 文件路径：`frontend/src/views/SkillLibrary.vue`
- 路由路径：当前未在 `router.ts` 注册。
- 页面用途：检察技能包列表、详情、规则检查项、测试/回放、导入导出、运行当前案件。
- 用户能做什么：
  - 查看规则包列表。
  - 选择技能包查看详情。
  - 查看 `SKILL.md` 摘要、manifest、checks、finding templates、examples、test cases、run history。
  - 对当前案件运行规则包。
  - 导入/导出技能包。
- 主要状态变量：
  - `activeCaseId`
  - `packs`
  - `selectedName`
  - `detail`
  - `lastRun`
  - `activeTab`
  - `running/error`
- 主要调用 API：
  - `backendApi.listRulePacks`
  - `backendApi.getRulePack`
  - `backendApi.runRulePack`
  - `backendApi.importRulePack`
  - `backendApi.exportRulePack`
- 依赖的核心组件：页面内部定义 `InfoBox`。
- 页面复杂度评价：中。
- 是否适合作为主流程页面：不适合作为普通办案主流程。
- 是否更适合作为高级/调试页面：适合作为“知识与技能”高级管理页。
- 重设计建议：
  - 先补路由再纳入导航。
  - 与智能分析页的 `@技能包` 关系需要明确：当前该页面是规则包管理，智能分析输入区未见完整 `@技能包` 选择器。

### 缺失但侧边栏存在的页面

| 入口 | 侧边栏路径 | 真实页面/路由 | 结论 |
|---|---|---|---|
| 检察技能库 | `linkTo('skills')` | 有 `SkillLibrary.vue`，无 router 注册 | 入口存在但不可达或落入 Dashboard |
| 分析上下文 | `linkTo('analysis-context')` | 未见 `AnalysisContextDebug.vue`，无 router 注册 | 入口受 localStorage 控制，但页面缺失 |
| 设置 | `linkTo('settings')` | 未见 `Settings.vue`，无 router 注册 | 入口存在但页面缺失 |

---

## 5. 图谱页面专项分析

### 相关文件

- 页面入口：`frontend/src/views/Graph.vue`
- G6 组件：`frontend/src/components/G6EvidenceGraph.vue`
- RelationGraph 使用：`frontend/src/views/Graph.vue` 内直接引入 `relation-graph/vue3`

### 当前模式

图谱页当前至少包含以下维度：

- 图层：`document`、`passage`、`raw`
- 渲染器：RelationGraph 与 G6EvidenceGraph
- 布局：`tree`、`force`
- 原始层视角/演示模式：核心邻域、邻域扩展、多跳召回、子图交叉等
- 过滤：按节点类型/关系类型/时间线/选择项等过滤
- 维护：新增/更新/删除/标为已核

### 主要状态与调用关系

`Graph.vue` 中的关键位置：

- `mapLayer`：当前图层，约在 `Graph.vue:416`
- `viewMode`、`demoMode`：原始层展示模式，约在 `Graph.vue:430-431`
- `layoutModeByLayer` / `layoutMode`：各图层布局状态，约在 `Graph.vue:437-442`
- `useG6`：是否使用 G6，约在 `Graph.vue:448`
- `setMapLayer`：切图层，约在 `Graph.vue:799`
- `toggleGraphEngine`：切 RelationGraph/G6，约在 `Graph.vue:817`
- `renderCurrentLayer`：统一渲染分发，约在 `Graph.vue:834`
- `renderEvidenceMapLayer`：文件层/片段层渲染，约在 `Graph.vue:953`
- `buildEvidenceLayerGraph`：构建文件层/片段层图数据，约在 `Graph.vue:987`
- `renderRawGraph` / 原始图构建：约在 `Graph.vue:834-942`、`Graph.vue:1212` 后
- `buildCoreNeighborhoodSubgraph`：约在 `Graph.vue:1348`
- `buildExpandedNeighborhoodSubgraph`：约在 `Graph.vue:1370`
- `buildMultihopPathSubgraph`：约在 `Graph.vue:1410`
- `buildIntersectionSubgraph`：约在 `Graph.vue:1438`
- `setLayoutMode`：约在 `Graph.vue:1824`
- 图谱人工干预：`upsertNode/upsertEdge/deleteSelected/verifySelected` 约在 `Graph.vue:1904` 后

数据流大致为：

```text
active_case_id / workspaceId
  -> backendApi.getEvidenceMap(caseId) 或 backendApi.getGraph(caseId)
  -> Graph.vue 构建当前图层 graphData
  -> 根据 useG6 传给 G6EvidenceGraph 或 RelationGraph
  -> 节点/边点击事件回传 Graph.vue
  -> 右侧详情/维护表单展示
```

### RelationGraph 与 G6 职责区别

- RelationGraph：旧版/经典图谱，较稳定，承载原始图谱维护、筛选和基本展示。
- G6EvidenceGraph：高级/实验图谱视图，承担更强的布局、截图、节点拖拽和高级交互需求。

### G6 稳定性机制

`frontend/src/components/G6EvidenceGraph.vue` 中已有下列机制：

- `buildSafeGraphData`：渲染前规范节点/边，过滤非法边。
- `validateG6GraphData`：开发日志校验节点 ID、重复、无效边等。
- `cleanupGraph` + `onBeforeUnmount`：销毁 G6 实例、timer、observer。
- `shallowRef` + `markRaw`：避免 Vue 深代理 G6 实例。
- `resolveInteractionProfile`：按图层、布局和规模选择 safe/standard/force/full 交互配置。
- `buildG6Behaviors`：构建 drag-canvas、zoom-canvas、drag-element、click-select、hover-activate、drag-element-force 等行为。
- `buildG6Plugins`：按条件开启 grid/minimap 等插件。
- 性能日志：`[G6EvidenceGraph:perf]`、`[G6EvidenceGraph:interactionProfile]`。

### 图谱页是否过于复杂

是。当前 `Graph.vue` 同时承担：

- 证据地图展示
- 原始图谱浏览
- 图层切换
- 渲染器切换
- 布局切换
- 原始图谱分析视角
- 节点/关系筛选
- 图谱人工编辑
- G6/RelationGraph 兼容
- 性能调试日志
- 截图导出

拆分建议：

1. 主流程默认页：只保留“案件证据地图 + 推荐视角 + 基本详情”。
2. 原始图谱维护：单独入口，保留 CRUD、标为已核、JSON 详情。
3. 高级图谱视图：单独切换或开发者入口，承载 G6、布局调试、截图模式。
4. 演示视角：核心邻域/多跳路径/子图交叉可以作为“推荐视角”，不要和底层维护功能混在一起。

---

## 6. 智能分析页面专项分析

- 页面文件路径：`frontend/src/views/Intelligence.vue`
- 用户输入：新建会话输入框 `analysis-input`；继续追问输入框。
- 案件上下文：通过 `active_case_id` 或 workspace 的 `baseCaseId` 绑定当前案件。
- @ 机制：代码中 `updateMentionSuggestions` 使用正则匹配 `@...`，`insertMention` 插入 `@[证据标题](证据ID)`。当前可确认的是 `@证据`；未见完整 `@技能包` 选择器。
- 调用 API：
  - `listAnalysisThreads`
  - `createAnalysisThread`
  - `getAnalysisThread`
  - `addAnalysisThreadMessage`
  - `deleteAnalysisThread`
  - `getRetrievalSession`
  - `listEvidence`
- 检索过程展示：
  - 每条消息可显示 `tool_call_summary`。
  - `details[data-testid="retrieval-session"]` 用于展开检索步骤。
  - 支持 tool label、参数格式化、片段压缩显示。
- 证据溯源：
  - `GroundedSentence` 句子按钮带 `data-testid="evidence-citation"`。
  - 点击后打开 `data-testid="provenance-modal"` 溯源抽屉。
- 是否适合作为核心主流程页面：适合。
- 当前交互复杂度：中高。会话列表、模式切换、新建、追问、证据 mention、检索详情、溯源都在一个页面。
- 重设计建议：
  - 入口文案按“分析任务”组织，而不是暴露过多技术过程。
  - 检索详情默认折叠，作为“可复核过程”入口。
  - 将“假设验证”和“可疑资金流”设计成任务模板卡，而非仅 tab。
  - 若要支持 `@技能包`，需补前端选择器、后端解析、展示状态，不要与现有 `@证据` 混淆。

---

## 7. 画像页面专项分析

- 页面文件路径：`frontend/src/views/Portrait.vue`
- 画像类型：
  - 人物关系叙述
  - 行为事实还原
  - 规则命中 findings
  - 文件母图节点摘要
  - 采纳疑点候选
- API：
  - `getPortraitFacts`
  - `getDocumentMotherGraph`
  - `rebuildDocumentMotherGraph`
  - `runRulePack`
  - `getRetrievalSession`
  - `getEvidenceDetail`
- 支撑事实和溯源：
  - 画像事实 `PortraitFact` 含 evidence ids、source passages 等字段。
  - 叙述句通过 `bestFactForText` 尝试匹配候选事实。
  - 点击句子后打开溯源面板。
- 与图谱页/分析页联动：
  - 图谱页提供证据地图和原始图关系。
  - 智能分析页采纳疑点存入 `localStorage` 后画像页读取 `adopted_suspicion:${caseId}`。
  - 画像页也可运行规则包并展示 findings。
- 重设计建议：
  - 主画像页面只展示业务向结果：人物关系、行为还原、疑点、补证建议、证据支撑。
  - 文件母图和规则包运行详情迁移为“证据结构/技能库/上下文调试”。
  - “生成画像报告”和“事实画像”如果并存，需要统一命名。

---

## 8. 法律知识库与技能包页面分析

### 法律知识库

- 页面路径：`frontend/src/views/LegalKnowledge.vue`
- 路由：`/legal-knowledge`
- 数据结构：
  - 罪名模板 `OffenseTemplateSummary`
  - 办案流程 `ProcedureFlowSummary`
  - 检索结果 `TraceResult`
- 是否可编辑：支持新增流程知识、上传知识文件。
- 是否只是展示：不是，包含上传和新增。
- 是否与智能分析联动：通过后端法律知识检索间接联动；前端未见直接从 Intelligence 页进入法律知识选择。
- 是否适合普通用户主流程：只读浏览适合；上传/维护应归管理员或高级功能。
- 重设计建议：
  - 分离“法律知识浏览”和“知识维护”。
  - 路由需要支持工作空间或统一从根路径打开。

### 检察技能库

- 页面路径：`frontend/src/views/SkillLibrary.vue`
- 路由：当前未注册。
- 数据结构：
  - 规则包 summary/detail
  - SKILL.md 摘要
  - manifest/checks/finding templates/examples/test cases/run history
  - run result findings/not_triggered/data_gaps
- 是否可编辑：支持导入/导出；未见页面内编辑器。
- 是否只是展示：不是，可运行当前案件规则包。
- 是否与智能分析联动：后端上有规则包 API；前端 Intelligence 未见完整技能包选择器。当前 `@` 是证据 mention。
- 是否支持 @技能包：当前代码未见明确支持。
- 是否适合普通用户主流程：不适合，应放“知识与技能”高级功能。
- 重设计建议：
  - 先补路由和导航一致性。
  - 若要让普通用户使用技能，应在智能分析页暴露简化版“分析模板/技能卡”，不要让用户直接看 checks JSON。

---

## 9. API 调用关系整理

统一封装：`frontend/src/api/backend.ts`，`API_PREFIX = ${import.meta.env.BASE_URL}api/v1`，底层使用 `fetch`。

| API 函数/调用位置 | HTTP 方法 | 路径 | 用途 | 被哪些页面使用 |
|---|---|---|---|---|
| `health` | GET | `/health` | 后端在线状态 | `Header.vue` |
| `listCases` | GET | `/cases` | 案件列表 | `Dashboard.vue` |
| `createCase` | POST | `/cases` | 创建默认案件 | `Dashboard.vue` |
| `createCustomCase` | POST | `/cases` | 创建自定义案件 | `Dashboard.vue` |
| `updateCase` | PATCH | `/cases/{caseId}` | 更新案件罪名等 | `Dashboard.vue` |
| `deleteCase` | DELETE | `/cases/{caseId}` | 删除案件 | `Dashboard.vue` |
| `ingestText` | POST | `/cases/{caseId}/ingestions/text` | 文本导入 | 当前主要页面未见直接使用 |
| `ingestFile` | POST | `/cases/{caseId}/ingestions/files` | 单文件导入 | 当前主要页面未见直接使用 |
| `ingestBatch` | POST | `/cases/{caseId}/ingestions/batch` | 文件夹批量导入 | `Dashboard.vue` |
| `ingestArchive` | POST | `/cases/{caseId}/ingestions/archive` | 压缩包导入 | `Dashboard.vue` |
| `listEvidence` | GET | `/cases/{caseId}/evidence` | 证据列表 | `Intelligence.vue` |
| `getEvidenceDetail` | GET | `/cases/{caseId}/evidence/{evidenceId}` | 证据原文详情 | `Portrait.vue` |
| `runAnalysis` | POST | `/cases/{caseId}/analysis/run` | 运行分析/建图 | `Dashboard.vue`、`Graph.vue` |
| `traceAnalysis` | POST | `/cases/{caseId}/analysis/trace` | PPR/溯源检索 | API 封装存在，当前页面少量或未显式使用 |
| `chatAnalysis` | POST | `/cases/{caseId}/analysis/chat` | 证据问答 | `Chat.vue` |
| `getPortraitFacts` | POST | `/cases/{caseId}/analysis/portrait-facts?force=...` | 画像事实 | `Portrait.vue` |
| `runSuspicionAnalysis` | POST | `/cases/{caseId}/analysis/suspicion` | 疑点分析 | API 封装存在，当前主用线程 API |
| `listAnalysisThreads` | GET | `/cases/{caseId}/analysis/threads` | 智能分析会话列表 | `Intelligence.vue` |
| `createAnalysisThread` | POST | `/cases/{caseId}/analysis/threads` | 新建会话 | `Intelligence.vue` |
| `getAnalysisThread` | GET | `/cases/{caseId}/analysis/threads/{threadId}` | 会话详情 | `Intelligence.vue` |
| `addAnalysisThreadMessage` | POST | `/cases/{caseId}/analysis/threads/{threadId}/messages` | 继续追问 | `Intelligence.vue` |
| `deleteAnalysisThread` | DELETE | `/cases/{caseId}/analysis/threads/{threadId}` | 删除会话 | `Intelligence.vue` |
| `getRetrievalSession` | GET | `/cases/{caseId}/analysis/retrieval-sessions/{sessionId}` | 检索过程详情 | `Intelligence.vue`、`Portrait.vue` |
| `getDocumentMotherGraph` | GET | `/cases/{caseId}/document-mother-graph` | 文件母图 | `Portrait.vue` |
| `rebuildDocumentMotherGraph` | POST | `/cases/{caseId}/document-mother-graph/rebuild` | 重建文件母图 | `Portrait.vue` |
| `listRulePacks` | GET | `/analysis-skills/rule-packs` | 技能包列表 | `SkillLibrary.vue` |
| `getRulePack` | GET | `/analysis-skills/rule-packs/{skillName}` | 技能包详情 | `SkillLibrary.vue` |
| `importRulePack` | POST | `/analysis-skills/import` | 导入技能包 | `SkillLibrary.vue` |
| `exportRulePack` | GET | `/analysis-skills/{skillName}/export` | 导出技能包 | `SkillLibrary.vue` |
| `runRulePack` | POST | `/cases/{caseId}/analysis/rule-packs/{packName}/run` | 运行规则包 | `SkillLibrary.vue`、`Portrait.vue` |
| `getLegalKnowledgeIndex` | GET | `/legal-knowledge/index` | 法律知识索引 | API 封装存在 |
| `listLegalCrimes` | GET | `/legal-knowledge/crimes` | 罪名模板 | API 封装存在 |
| `listLegalProcesses` | GET | `/legal-knowledge/processes` | 流程模板 | API 封装存在 |
| `uploadLegalKnowledge` | POST | `/legal-knowledge/upload` | 上传法律知识 | API 封装存在 |
| `listAnalysisContexts` | GET | `/cases/{caseId}/analysis/contexts` | 分析上下文列表 | API 封装存在；未见页面 |
| `getAnalysisContext` | GET | `/cases/{caseId}/analysis/contexts/{contextId}` | 分析上下文详情 | API 封装存在；未见页面 |
| `getGraph` | GET | `/cases/{caseId}/graph` | 原始调查图谱 | `Graph.vue` |
| `getEvidenceMap` | GET | `/cases/{caseId}/evidence-map` | 三层证据地图数据 | `Graph.vue` |
| `getMergedGraph` | POST | `/cases/{caseId}/graph/merged` | 临时合并案件图谱 | `Graph.vue` |
| `applyGraphIntervention` | PATCH | `/cases/{caseId}/graph/interventions` | 图谱人工增删改核 | `Graph.vue` |
| `generatePortrait` | POST | `/cases/{caseId}/reports/portrait` | 画像报告 | API 封装存在 |
| `getLatestPortrait` | GET | `/cases/{caseId}/reports/portrait/latest` | 最新画像报告 | API 封装存在 |
| `listOffenseTemplates` | GET | `/legal-knowledge/offense-templates` | 罪名模板下拉 | `Dashboard.vue`、`LegalKnowledge.vue` |
| `createProcedureFlow` | POST | `/legal-knowledge/procedure-flows` | 新增流程知识 | `LegalKnowledge.vue` |
| `uploadProcedureFlow` | POST | `/legal-knowledge/procedure-flows/upload` | 上传流程知识 | `LegalKnowledge.vue` |
| `retrieveLegalKnowledge` | POST | `/legal-knowledge/retrieve` | 法律知识检索 | `LegalKnowledge.vue` |

---

## 10. 状态管理与数据流

### 状态管理方式

未见 Pinia/Vuex。当前主要依赖：

- 页面内 `ref/reactive/computed`
- `localStorage`
  - `active_case_id`
  - `active_workspace_id`
  - `active_analysis_thread_id`
  - `workspace:{workspaceId}`
  - 若干页面缓存和调试开关
- `workspace.ts` 解析普通案件 ID 与 `tmp_` 临时合并工作空间。

### caseId 传递

```text
router.beforeEach
  -> resolveWorkspace(route.params.workspaceId)
  -> localStorage.active_workspace_id = workspace.workspaceId
  -> localStorage.active_case_id = workspace.baseCaseId
  -> 各页面读取 localStorage.active_case_id
```

### 图谱数据流

```text
路由 / localStorage active_case_id
  -> Graph.vue loadEvidenceMap/loadGraph
  -> backendApi.getEvidenceMap / getGraph / getMergedGraph
  -> Graph.vue 根据 mapLayer、layoutMode、filters 构建可渲染数据
  -> RelationGraph 或 G6EvidenceGraph
  -> nodeClick/lineClick 回传
  -> Graph.vue 右侧详情与维护表单
```

### 智能分析数据流

```text
active_case_id
  -> Intelligence.vue loadThreads(mode)
  -> listAnalysisThreads
  -> selectThread
  -> getAnalysisThread
  -> 消息中包含 grounded_sentences / retrieval_session_id
  -> 点击句子打开 provenance drawer
  -> 展开 retrieval details 时 getRetrievalSession
```

### 画像数据流

```text
active_case_id
  -> Portrait.vue refreshFacts(force)
  -> getPortraitFacts
  -> relationship_narrative / behavior_narrative / facts
  -> narrativeSentenceParagraphs 将文段切句并匹配事实
  -> 点击句子打开溯源面板
  -> getEvidenceDetail 获取原文详情
```

### 状态问题

- 多页面都直接读取 `localStorage.active_case_id`，缺少统一 store。
- Sidebar 的 workspace-aware `linkTo` 与 router 注册不完全一致，导致部分链接不可达。
- 图谱页内部状态过多，容易出现渲染器、图层、布局、筛选之间互相影响。
- 智能分析和画像的 retrieval session 展示逻辑各自实现，存在重复。

---

## 11. 当前导航和用户流程

### 当前导航结构

`frontend/src/components/Sidebar.vue` 将导航分成：

```text
案件工作台
  - 案件导入
  - 案件证据地图
  - 画像报告
  - 智能分析

知识与技能
  - 检察技能库
  - 法律知识库

调试与维护
  - 证据问答
  - 分析上下文（devMode + showAnalysisContextDebug）
  - 原始图谱维护
  - 设置
```

### 当前可能的用户路径

1. 进入 Dashboard。
2. 新建或选择案件。
3. 选择罪名。
4. 导入文件夹或压缩包。
5. 运行分析。
6. 进入案件证据地图。
7. 查看图谱或进入画像页。
8. 在智能分析页新建分析会话。
9. 点击分析/画像结果做证据溯源。

### 当前导航问题

- 页面主次已经有分组意识，但路由没有完全同步。
- 检察技能库、设置、分析上下文入口目前不完整。
- 法律知识库只有根路径路由，workspace 下链接会失效。
- 图谱页按钮和概念过多，普通用户很难判断下一步。
- 调试功能与主流程功能仍有混杂，例如图谱页同时承担维护、展示、演示、性能调试。
- 缺少一个统一“案件工作台详情页”承接案件基本信息、证据状态、推荐下一步。

---

## 12. 组件复杂度与重复组件

| 组件 | 文件路径 | 用途 | 被哪些页面使用 | 复杂度 | 是否建议保留/拆分/合并 |
|---|---|---|---|---|---|
| `Sidebar.vue` | `frontend/src/components/Sidebar.vue` | 侧边栏导航 | `App.vue` | 中 | 保留，但需与 router 对齐 |
| `Header.vue` | `frontend/src/components/Header.vue` | 顶部标题与后端在线状态 | `App.vue` | 低 | 保留 |
| `G6EvidenceGraph.vue` | `frontend/src/components/G6EvidenceGraph.vue` | G6 高级图谱渲染 | `Graph.vue` | 高 | 保留为高级图谱组件；继续封装交互 profile |
| `AsyncProgressBar.vue` | `frontend/src/components/AsyncProgressBar.vue` | 模拟进度条 | 需进一步查调用；可能用于导入/分析长任务 | 低 | 可保留为通用加载组件 |

重复或应抽取的逻辑：

- Intelligence 与 Portrait 都有 retrieval session 展示逻辑。
- Intelligence 与 Portrait 都有 grounded sentence / provenance drawer 逻辑。
- Graph.vue 内部同时有 RelationGraph 和 G6 转换逻辑，可拆为 adapter。
- 多页面各自维护 active case，可抽统一 composable。

---

## 13. 当前前端的主要问题总结

### 信息架构问题

- 核心办案流程和技术调试入口混在一起。
- SkillLibrary 页面存在但路由缺失。
- 设置页、分析上下文页有导航入口但页面缺失。
- 案件、工作空间、临时合并分析的概念没有在 UI 上明确解释。

### 交互问题

- 图谱页模式过多：图层、渲染器、布局、视角、筛选、维护、截图都在一页。
- 智能分析的“新建会话 / 历史会话 / 追问 / 检索详情 / 溯源”信息密度较高。
- 画像页混合了用户结果和内部结构调试。

### 视觉层级问题

- 图谱页当前最容易压倒用户注意力，应优先展示推荐视角。
- 调试日志和高级按钮不应作为普通用户默认认知负担。
- 检索与调用细节应作为“可复核过程”，不是结果主视觉。

### 代码结构问题

- `Graph.vue` 体积极大，职责过多。
- 页面间重复实现检索详情、证据溯源、active case 管理。
- 路由、侧边栏、页面文件不同步。

### 演示风险

- G6 高级视图虽然已有稳定性机制，但仍应作为高级/实验视图而非唯一主视图。
- 未注册路由的侧边栏入口在演示时会显得“点了没反应”。
- `@技能包` 如未补齐，不应在页面上暗示已完整支持。

---

## 14. 前端重设计建议草案

建议围绕“检察侦查办案流程”组织，而不是围绕技术模块堆页面。

### 主流程

1. 案件工作台
   - 对应当前 `Dashboard.vue`
   - 承担案件选择、案件基本信息、罪名选择、导入状态、推荐下一步。
2. 证据接入
   - 从 `Dashboard.vue` 拆出或在 Dashboard 内作为清晰步骤。
   - 显示导入文件、处理进度、失败文件、证据数量。
3. 证据地图
   - 对应当前 `Graph.vue` 的普通地图视图。
   - 默认使用稳定视图，只保留文件层/片段层/原始层与推荐视角。
4. 智能分析
   - 对应当前 `Intelligence.vue`
   - 用任务模板组织：假设验证、可疑资金、行为画像、补证建议等。
5. 信息画像
   - 对应当前 `Portrait.vue`
   - 展示人物关系、行为还原、疑点、证据支撑。
6. 报告生成
   - 当前报告 API 存在，但前端主入口不够突出。
   - 可从 Portrait 拆出“生成正式报告”页。
7. 溯源复核
   - 可作为全局抽屉/通用组件，不应每页重复实现。

### 辅助功能

1. 法律知识库
   - 对应 `LegalKnowledge.vue`
   - 普通用户看模板，管理员维护材料。
2. 检察技能包
   - 对应 `SkillLibrary.vue`
   - 需要先补路由；作为高级功能。
3. 检索轨迹 / Agentic RAG sessions
   - 当前在 Intelligence/Portrait 中以 details 方式出现。
   - 可做成开发者页或高级复核页。
4. 分析上下文调试页
   - API 封装存在，页面未见。
   - 仅开发者模式显示。
5. G6 高级图谱视图
   - 放在证据地图的高级开关中。
6. 系统设置
   - 当前 sidebar 有入口，页面未见。
   - 可管理 devMode、显示调试入口、图谱默认引擎等。

---

## 15. 建议提供给另一个智能体的文件清单

### 必读文件

- `frontend/src/router.ts`
- `frontend/src/App.vue`
- `frontend/src/components/Sidebar.vue`
- `frontend/src/api/backend.ts`
- `frontend/src/views/Dashboard.vue`
- `frontend/src/views/Graph.vue`
- `frontend/src/views/Intelligence.vue`
- `frontend/src/views/Portrait.vue`
- `frontend/src/workspace.ts`

### 次要文件

- `frontend/src/components/G6EvidenceGraph.vue`
- `frontend/src/views/LegalKnowledge.vue`
- `frontend/src/views/SkillLibrary.vue`
- `frontend/src/views/Chat.vue`
- `frontend/src/components/Header.vue`
- `frontend/src/components/AsyncProgressBar.vue`
- `frontend/src/composables/useSimulatedProgress.ts`
- `frontend/src/style.css`

### 可选文件

- `frontend/package.json`
- `frontend/scripts/*`
- `frontend/playwright.config.*`（如需截图/测试）
- `frontend/dist` 不建议作为重设计依据。

---

## 16. 不确定项

1. `SkillLibrary.vue` 是否原计划已经对外开放：页面存在、API 存在，但 router 未注册。
2. `Settings.vue` 与 `AnalysisContextDebug.vue` 是否曾存在于其他分支：当前 `frontend/src/views` 未见。
3. `@技能包` 是否计划近期实现：当前 Intelligence 中可确认的是 `@证据` mention。
4. `Chat.vue` 是否还应保留独立页面：它与 Intelligence 的问答能力有重叠。
5. G6 是否应成为默认图谱引擎：当前代码默认 `useG6 = true`，但从产品稳态看更适合作为高级视图或演示视图。
6. 临时合并工作空间 `tmp_` 是否要对普通用户显式展示：当前 `workspace.ts` 支持，但 UI 说明不足。
7. 法律知识库是否面向普通检察官可编辑：当前前端允许新增/上传，权限边界未在前端体现。
8. 画像页中的文件母图和规则运行是否应继续放在画像页：从产品上更适合迁到高级/上下文页面。

---

## 给后续重设计的最短结论

当前前端已经有比较完整的能力原型，但信息架构上“主流程、专家功能、调试功能”仍混在一起。最大问题不是页面不够多，而是核心用户路径不够克制：`Dashboard.vue` 和 `Graph.vue` 承担过多职责，`Intelligence.vue` 与 `Portrait.vue` 又各自重复实现检索细节与溯源。建议重设计时先统一案件工作台和导航，再把图谱高级能力、技能包、上下文调试从普通办案主流程中拆出去。
