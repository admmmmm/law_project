# 项目文件结构梳理

本项目为“检察侦查智能平台”，采用 Vue3 + Vite + TypeScript 技术栈，结构清晰，便于扩展和维护。以下为主要文件和目录说明：

## 根目录
- `index.html`：应用入口 HTML 文件。
- `package.json`：依赖与脚本配置。
- `tsconfig.json`：TypeScript 配置。
- `vite.config.ts`：Vite 构建工具配置。
- `README.md`：项目说明文档。
- `metadata.json`：元数据配置，可能用于描述项目或 AI 模型。
- `clean-ui.ts`、`convert*.ts`、`fix-*.ts` 等：批量 UI/数据处理/自动化脚本，辅助开发和数据转换。

## src 目录（主源码）
- `App.vue`：根组件，负责整体布局。
- `main.ts`：应用入口，初始化并挂载 Vue 实例。
- `router.ts`：路由配置，管理页面跳转。
- `style.css`：全局样式文件。

### src/components
- `Header.vue`：顶部导航栏组件。
- `Sidebar.vue`：侧边栏组件。

### src/views
- `Dashboard.vue`：仪表盘/首页，展示案件总览等。
- `Graph.vue`：图谱分析页面。
- `Intelligence.vue`：主观意图研判页面。
- `Portrait.vue`：画像分析页面。

## 其他说明
- 根目录下的 `clean-ui.ts`、`convert*.ts`、`fix-*.ts` 等脚本文件，通常用于批量处理 UI、数据转换、模板修复等，不直接参与主业务流程，但对开发和数据维护有重要辅助作用。
- 目录结构清晰，便于功能模块化开发和团队协作。

如需详细了解某个文件或目录的具体作用，可查阅源码注释或联系开发者。

## Run Locally

**Prerequisites:**  Node.js


1. Install dependencies:
   `npm install`
2. Set the `GEMINI_API_KEY` in [.env.local](.env.local) to your Gemini API key
3. Run the app:
   `npm run dev`
