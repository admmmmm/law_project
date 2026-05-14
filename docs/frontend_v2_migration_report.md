# frontend_v2 迁移报告

## 1. 本轮迁移目标

本轮只处理 `frontend_v2`，保留旧 `frontend` 不动，后端主链路不动。目标是把旧前端中已经较成熟的图谱、智能分析、信息画像能力迁入新工作台 / 案件空间结构。

## 2. 迁移来源

| 能力 | 旧前端来源 | 迁入位置 | 说明 |
|---|---|---|---|
| G6 图谱内核 | `frontend/src/components/G6EvidenceGraph.vue` | `frontend_v2/src/components/G6EvidenceGraph.vue` | 迁移图谱渲染、布局、交互、安全数据修复、生命周期清理、导出截图能力。 |
| 智能分析页面 | `frontend/src/views/Intelligence.vue` | `frontend_v2/src/views/Intelligence.vue` | 迁移分析会话、追问、@证据、检索轨迹、句子级溯源等内部逻辑。 |
| 信息画像页面 | `frontend/src/views/Portrait.vue` | `frontend_v2/src/views/Portrait.vue` | 迁移人物关系、行为事实、事实溯源、检索轨迹、规则与文件节点折叠细节。 |

## 3. frontend_v2 修改文件

| 文件 | 修改内容 |
|---|---|
| `frontend_v2/package.json` | 新增 `@antv/g6` 依赖，用于高级图谱视图。 |
| `frontend_v2/package-lock.json` | 通过 `npm install` 同步锁文件。 |
| `frontend_v2/src/components/G6EvidenceGraph.vue` | 迁入旧 G6 核心；保留闭合校验、无效边过滤、实例销毁、导出 PNG、交互 profile。调试日志默认不在普通界面显示。 |
| `frontend_v2/src/views/Graph.vue` | 用 G6 图谱替换原轻量 SVG 占位图；保留 v2 左侧图层切换、顶部树形/力导/导出截图、图例、右侧详情、raw 层编辑限制。 |
| `frontend_v2/src/views/Intelligence.vue` | 迁入旧分析页面，并改为优先读取 route params 的 `caseId`。 |
| `frontend_v2/src/views/Portrait.vue` | 迁入旧画像页面，并改为优先读取 route params 的 `caseId`；智能分析入口改为 `/cases/:caseId/analysis`。 |
| `frontend_v2/src/api/backend.ts` | 补齐分析会话、画像事实、检索 session、文件节点、规则包运行等 API 类型和方法。 |
| `frontend_v2/src/router.ts` | 新增主路由 `/cases/:caseId/analysis`，保留 `/cases/:caseId/intelligence` 兼容重定向。 |
| `frontend_v2/src/components/AppLogo.vue` | 新增内联 SVG 剑形 Logo。 |
| `frontend_v2/src/components/Sidebar.vue` | 工作台品牌区使用剑形 Logo。 |
| `frontend_v2/src/components/Header.vue` | 顶部栏加入紧凑 Logo。 |
| `frontend_v2/src/components/CaseSpaceSidebar.vue` | 案件空间品牌区使用剑形 Logo，智能分析入口切到 `/analysis`。 |
| `frontend_v2/src/components/CaseSpaceNav.vue` | 智能分析链接切到 `/analysis`。 |

## 4. G6 图谱状态

已完成：

- `frontend_v2` 证据地图不再使用轻量 SVG 占位实现。
- 图谱区域使用迁移后的 `G6EvidenceGraph`。
- 使用后端 `GET /api/v1/cases/{case_id}/evidence-map` 的 `layers.document / layers.passage / layers.raw`。
- 图层切换仍由左侧栏完成，顶部只保留当前图谱名称、树形、力导、导出截图。
- `document / passage` 图层只读，不展示编辑区。
- `raw` 图层展示维护区，调用 `POST /api/v1/cases/{case_id}/graph/raw/actions`。
- 保留 G6 稳定性机制：节点 ID 规范化、无效边过滤、实例销毁、避免重复实例、避免 `Node already exists` 和 pointermove 异常风暴。

边界：

- 当前仅迁移图谱内核，没有把旧 `Graph.vue` 外围复杂筛选、调试面板、性能日志和演示模式搬入 v2。
- G6 控制台调试日志默认只在开发或 `localStorage.g6_debug=true` 时输出。

## 5. 智能分析迁移状态

已完成：

- 页面路由保持在案件空间内：`/cases/:caseId/analysis`。
- 保留分析输入、会话卡片、继续追问、删除会话、@证据、检索轨迹折叠展示、句子级溯源抽屉。
- `caseId` 优先从 route params 读取，兼容 `localStorage.active_case_id`。

边界：

- 当前没有新增完整的前端技能包选择器；`@...` 主要仍用于 @证据，任务文本可表达技能约束。
- 检索轨迹仍依赖后端已保存的 retrieval session。

## 6. 信息画像迁移状态

已完成：

- 页面路由保持在案件空间内：`/cases/:caseId/portrait`。
- 保留人物关系、行为事实、支撑事实、事实句点击溯源、检索轨迹折叠展示。
- 规则运行、文件节点等高级内容保持折叠或侧栏打开，不作为主路径强入口。

边界：

- 未新增资金画像、反侦查画像、跨案画像等尚未严格产品化的强入口。
- 画像内容质量仍取决于后端画像事实接口与已保存检索结果。

## 7. Logo 状态

已完成：

- 新增 `frontend_v2/src/components/AppLogo.vue`。
- 使用内联 SVG 绘制稳重风格剑形剪影。
- 工作台侧栏、案件空间侧栏和顶部栏均已接入。

## 8. 构建与检查

在 `frontend_v2` 下执行：

```powershell
npm install
npm run build
npm run lint
```

结果：

- `npm install`：通过。
- `npm run build`：通过。
- `npm run lint`：通过。

注意：

- 构建提示主 chunk 超过 500 kB，原因是 G6 与现有依赖体积较大。当前不影响运行，后续可通过路由级动态导入拆包。

## 9. 剩余问题

1. `frontend_v2/package.json` 仍保留部分 React 相关依赖，后续可清理。
2. 智能分析和画像页面已迁移成熟逻辑，但视觉风格还没有完全统一到 v2 新设计系统。
3. 旧版 G6 内核已稳定迁入，但高级图谱的筛选/邻域/路径演示功能没有进入 v2 主界面。
4. 技能包前端选择器仍是后续增强点。
5. 大体积 chunk 建议后续通过动态导入优化。
