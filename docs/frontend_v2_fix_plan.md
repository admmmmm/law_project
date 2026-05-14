# frontend_v2 P0 修复计划

## P0：必须先修

- [x] 清理路由与布局冲突标记
  - 文件：`frontend_v2/src/router.ts`、`frontend_v2/src/components/Sidebar.vue`、`frontend_v2/src/components/Header.vue`、`frontend_v2/src/style.css`
  - 原因：存在 Git conflict marker，构建必失败。
  - 修复建议：保留 Workspace + Case Space 分支，删除旧前端直连菜单。

- [x] 补齐缺失前端依赖文件
  - 文件：`frontend_v2/src/api/backend.ts`、`frontend_v2/src/components/AsyncProgressBar.vue`、`frontend_v2/src/composables/useSimulatedProgress.ts`
  - 原因：多个页面已引用但文件不存在。
  - 修复建议：补最小可用封装，优先真实后端 API，失败时抛出清晰错误。

- [x] 补齐工作台页面入口
  - 文件：`frontend_v2/src/views/SkillLibrary.vue`、`frontend_v2/src/views/LegalKnowledge.vue`
  - 原因：路由引用缺失页面。
  - 修复建议：实现 P0 浏览/占位页面。

- [x] 案件概览接入 `/overview`
  - 文件：`frontend_v2/src/views/CaseOverview.vue`
  - 原因：旧逻辑从案件列表和证据列表拼概览。
  - 修复建议：优先调用 `GET /api/v1/cases/{case_id}/overview`，展示 stats、next_step、recent_evidence。

- [x] 案件证据地图接入 `layers`
  - 文件：`frontend_v2/src/views/Graph.vue`、`frontend_v2/src/components/LegendPanel.vue`
  - 原因：当前 Graph 是静态演示图。
  - 修复建议：使用 `layers.document/passage/raw`，图层切换由左侧 query 控制，顶部只保留树形/力导/导出截图。

- [x] 原始图谱层编辑范围收紧
  - 文件：`frontend_v2/src/views/Graph.vue`
  - 原因：设计要求 document/passage 只读，raw 可编辑。
  - 修复建议：只在 `activeLayer === 'raw'` 且 `editable === true` 显示维护区，调用 `/graph/raw/actions`。

- [x] 隐藏普通用户不该看到的调试项
  - 文件：`frontend_v2/src/views/Graph.vue`
  - 原因：普通界面不应出现 G6/RelationGraph/renderSignature 等技术字段。
  - 修复建议：P0 页面不展示技术渲染器切换和内部日志。

## P1：建议修

- [x] 智能分析页改成真实会话工作台。
- [x] 信息画像页接真实 portrait facts / report。
- [ ] 技能编辑保存能力接后端导入/导出 API。
- [ ] 法律知识库上传接后端 upload API。
- [ ] 清理 `package.json` 中非必要 React 依赖。

## P2：后续优化

- [x] 图谱画布接入稳定高级可视化组件。
- [ ] 增加全局 toast / confirm / loading 组件。
- [ ] 引入统一表单校验和错误码展示。
- [ ] 适配 `/jcmx` 部署前缀的路径和静态资源策略。

## P0 修复结果

已完成：

1. 修复路由、侧栏、顶部栏、全局样式中的合并冲突。
2. 补齐缺失 API 封装和公共组件。
3. 工作台入口均有真实路由：我的案件、新建案件、检察技能库、知识库、设置。
4. 案件空间入口均可达：案件概览、案件证据地图、智能分析、信息画像。
5. 案件概览已接 `/overview`，证据详情已接 `/evidence/{evidence_id}`。
6. 案件证据地图已接 `/evidence-map.layers`。
7. 图谱图例已随当前图层变化。
8. raw 层维护区已接 `/graph/raw/actions`。
9. document / passage 层不显示编辑区。
10. 普通界面不再展示 G6EvidenceGraph、RelationGraph、renderSignature、dataRepair 等技术字段。

构建结果：

- `npm run build`：通过。
- `npm run lint`：通过。

仍需后续处理：

1. `Intelligence.vue` 已迁入旧前端成熟会话逻辑，入口为 `/cases/:caseId/analysis`，旧 `/intelligence` 路径保留重定向。
2. `Portrait.vue` 已迁入旧前端画像事实逻辑，入口为 `/cases/:caseId/portrait`。
3. 图谱画布已从轻量 SVG 占位替换为迁移后的 G6 图谱内核。
4. 技能编辑保存、法律知识上传仍是占位入口。
5. `package.json` 仍保留 React 相关依赖，后续可清理。

## 本轮迁移补充结果

已完成：

1. 从旧前端迁移 `G6EvidenceGraph.vue` 到 `frontend_v2/src/components/G6EvidenceGraph.vue`。
2. `Graph.vue` 已接入 G6，保留 v2 的左侧图层切换、顶部布局按钮、图例和 raw 层编辑约束。
3. 从旧前端迁移 `Intelligence.vue`，改为 route params 优先读取 caseId。
4. 从旧前端迁移 `Portrait.vue`，改为 route params 优先读取 caseId，并把智能分析入口改为 `/cases/:caseId/analysis`。
5. 新增 `AppLogo.vue` 剑形内联 SVG，并接入 Sidebar/Header/CaseSpaceSidebar。
6. 补齐 `backendApi` 的分析会话、画像、检索 session、文件节点和规则包方法。

验证：

- `npm install`：通过。
- `npm run build`：通过。
- `npm run lint`：通过。

仍需后续处理：

1. 统一迁入页面的视觉语言，使智能分析和画像页更贴近 v2 工作台风格。
2. 增加真正的前端技能包选择器，而不是只依靠任务文本表达技能约束。
3. 对 G6 相关页面做动态导入，降低首屏 bundle 体积。
