import { createRouter, createWebHistory } from 'vue-router';
import Dashboard from './views/Dashboard.vue';
import Graph from './views/Graph.vue';
import Portrait from './views/Portrait.vue';
import Intelligence from './views/Intelligence.vue';

const routes = [
  { path: '/', component: Dashboard },
  { path: '/graph', component: Graph },
  { path: '/portrait', component: Portrait },
  { path: '/intelligence', component: Intelligence },
  { path: '/:pathMatch(.*)*', component: Dashboard }
];

export default createRouter({
  history: createWebHistory(),
  routes,
});
