import { createRouter, createWebHistory } from 'vue-router';
import Dashboard from './views/Dashboard.vue';
import Graph from './views/Graph.vue';
import Portrait from './views/Portrait.vue';
import Intelligence from './views/Intelligence.vue';
import Chat from './views/Chat.vue';
import LegalKnowledge from './views/LegalKnowledge.vue';
import { resolveWorkspace } from './workspace';

const routes = [
  { path: '/', component: Dashboard },
  { path: '/legal-knowledge', component: LegalKnowledge },
  { path: '/graph', component: Graph },
  { path: '/portrait', component: Portrait },
  { path: '/intelligence', component: Intelligence },
  { path: '/chat', component: Chat },
  { path: '/:workspaceId', component: Dashboard },
  { path: '/:workspaceId/graph', component: Graph },
  { path: '/:workspaceId/portrait', component: Portrait },
  { path: '/:workspaceId/intelligence', component: Intelligence },
  { path: '/:workspaceId/chat', component: Chat },
  { path: '/:pathMatch(.*)*', component: Dashboard }
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

router.beforeEach((to) => {
  const workspace = resolveWorkspace(String(to.params.workspaceId || ''));
  if (workspace) {
    localStorage.setItem('active_workspace_id', workspace.workspaceId);
    localStorage.setItem('active_case_id', workspace.baseCaseId);
  }
});

export default router;
