import { createRouter, createWebHistory } from 'vue-router';
import Dashboard from './views/Dashboard.vue';
import Graph from './views/Graph.vue';
import Portrait from './views/Portrait.vue';
import Intelligence from './views/Intelligence.vue';
import Chat from './views/Chat.vue';

const routes = [
  { path: '/', component: Dashboard },
  { path: '/graph', component: Graph },
  { path: '/portrait', component: Portrait },
  { path: '/intelligence', component: Intelligence },
  { path: '/chat', component: Chat },
  { path: '/:pathMatch(.*)*', component: Dashboard }
];

export default createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});
