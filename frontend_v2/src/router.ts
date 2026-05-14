import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';
import MyCases from './views/MyCases.vue';
import CreateCase from './views/CreateCase.vue';
import CaseOverview from './views/CaseOverview.vue';
import Graph from './views/Graph.vue';
import Portrait from './views/Portrait.vue';
import Intelligence from './views/Intelligence.vue';
import SkillLibrary from './views/SkillLibrary.vue';
import SkillDetail from './views/SkillDetail.vue';
import SkillEditor from './views/SkillEditor.vue';
import KnowledgePage from './views/KnowledgePage.vue';
import Settings from './views/Settings.vue';
import { resolveWorkspace } from './workspace';

function activeCasePath(page = '') {
  const caseId = localStorage.getItem('active_case_id') || localStorage.getItem('active_workspace_id');
  return caseId ? `/cases/${caseId}${page}` : '/cases';
}

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/cases' },
  {
    path: '/cases',
    component: MyCases,
    meta: {
      title: '我的案件',
      description: '查看已有案件，选择一个案件进入案件空间，或创建新的案件。',
      primaryAction: { label: '新建案件', to: '/cases/new' },
    },
  },
  {
    path: '/cases/new',
    component: CreateCase,
    meta: {
      title: '新建案件',
      description: '创建案件并导入初始证据。系统将围绕该案件构建证据地图，并支持后续智能分析和信息画像。',
    },
  },
  {
    path: '/cases/:caseId',
    component: CaseOverview,
    meta: {
      title: '案件概览',
      description: '围绕当前案件查看处理状态、证据导入情况，并进入证据地图、智能分析和信息画像。',
      space: 'case',
    },
  },
  {
    path: '/cases/:caseId/graph',
    component: Graph,
    meta: { title: '案件证据地图', description: '查看文件证据图、片段证据图和原始图谱层。', space: 'case' },
  },
  {
    path: '/cases/:caseId/analysis',
    component: Intelligence,
    meta: { title: '智能分析', description: '基于证据地图和知识库开展可溯源分析。', space: 'case' },
  },
  { path: '/cases/:caseId/intelligence', redirect: (to) => `/cases/${String(to.params.caseId)}/analysis` },
  {
    path: '/cases/:caseId/portrait',
    component: Portrait,
    meta: { title: '信息画像', description: '梳理涉案人员关系、行为链条和画像结论。', space: 'case' },
  },
  {
    path: '/skills',
    component: SkillLibrary,
    meta: {
      title: '检察技能库 / 浏览技能',
      description: '浏览和管理可复用的检察分析技能，用于指导智能分析、规则检查和画像生成。',
    },
  },
  {
    path: '/skills/editor',
    component: SkillEditor,
    meta: {
      title: '检察技能库 / 技能编辑',
      description: '编辑技能说明、检查项、输出模板和示例。',
    },
  },
  {
    path: '/skills/:skillName',
    component: SkillDetail,
    meta: {
      title: '检察技能库 / 技能详情',
      description: '展示某一个技能包的完整说明、适用场景、检查项、输出格式和示例。',
    },
  },
  {
    path: '/skills/:skillName/edit',
    component: SkillEditor,
    meta: {
      title: '检察技能库 / 技能编辑',
      description: '编辑技能说明、检查项、输出模板和示例。',
    },
  },
  {
    path: '/knowledge/legal',
    component: KnowledgePage,
    props: { kind: 'legal' },
    meta: {
      title: '知识库 / 法律知识',
      description: '维护罪名模板、法律条文、构成要件、证据标准和办案流程规范。',
    },
  },
  {
    path: '/knowledge/practice',
    component: KnowledgePage,
    props: { kind: 'practice' },
    meta: {
      title: '知识库 / 实务知识',
      description: '维护办案经验、审查清单、类案经验和实务风险提示。',
    },
  },
  {
    path: '/settings',
    component: Settings,
    meta: { title: '设置', description: '系统显示、调试开关和默认行为配置。' },
  },
  { path: '/legal-knowledge', redirect: '/knowledge/legal' },
  { path: '/graph', redirect: () => activeCasePath('/graph') },
  { path: '/portrait', redirect: () => activeCasePath('/portrait') },
  { path: '/intelligence', redirect: () => activeCasePath('/analysis') },
  { path: '/:workspaceId/graph', redirect: (to) => `/cases/${String(to.params.workspaceId)}/graph` },
  { path: '/:workspaceId/portrait', redirect: (to) => `/cases/${String(to.params.workspaceId)}/portrait` },
  { path: '/:workspaceId/intelligence', redirect: (to) => `/cases/${String(to.params.workspaceId)}/analysis` },
  { path: '/:workspaceId', redirect: (to) => `/cases/${String(to.params.workspaceId)}` },
  { path: '/:pathMatch(.*)*', redirect: '/cases' },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

router.beforeEach((to) => {
  const caseId = String(to.params.caseId || '');
  if (caseId) {
    localStorage.setItem('active_workspace_id', caseId);
    localStorage.setItem('active_case_id', caseId);
    return;
  }
  const workspace = resolveWorkspace(String(to.params.workspaceId || ''));
  if (workspace) {
    localStorage.setItem('active_workspace_id', workspace.workspaceId);
    localStorage.setItem('active_case_id', workspace.baseCaseId);
  }
});

export default router;
