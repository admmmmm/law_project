<template>
  <aside class="sidebar case-sidebar">
    <div class="brand-row">
      <AppLogo title="案件空间" :subtitle="caseTitle" />
    </div>

    <div class="case-sidebar-back">
      <router-link class="nav-card active-soft" to="/cases">
        <span><b>返回我的案件</b><small>回到工作台继续选案或建案</small></span>
      </router-link>
    </div>

    <nav class="nav-cards">
      <router-link class="nav-card" :class="{ active: isOverview }" :to="`/cases/${caseId}`">
        <span><b>案件概览</b><small>查看案件状态、证据列表和下一步</small></span>
      </router-link>

      <button class="nav-card" :class="{ active: isGraph }" @click="expandedGraph = !expandedGraph">
        <span><b>案件证据地图</b><small>查看证据结构与事实关系</small></span>
      </button>
      <div v-if="expandedGraph" class="subnav">
        <router-link :class="{ active: isGraph && activeLayer === 'document' }" :to="graphTo('document')">文件证据图</router-link>
        <router-link :class="{ active: isGraph && activeLayer === 'passage' }" :to="graphTo('passage')">片段证据图</router-link>
        <router-link :class="{ active: isGraph && activeLayer === 'raw' }" :to="graphTo('raw')">原始图谱层</router-link>
      </div>

      <router-link class="nav-card" :class="{ active: route.path.endsWith('/analysis') || route.path.endsWith('/intelligence') }" :to="`/cases/${caseId}/analysis`">
        <span><b>智能分析</b><small>围绕证据开展辅助分析</small></span>
      </router-link>

      <router-link class="nav-card" :class="{ active: route.path.endsWith('/portrait') }" :to="`/cases/${caseId}/portrait`">
        <span><b>信息画像</b><small>查看人物关系与行为画像</small></span>
      </router-link>
    </nav>
  </aside>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRoute } from 'vue-router';
import AppLogo from './AppLogo.vue';

const route = useRoute();
const caseId = computed(() => String(route.params.caseId || localStorage.getItem('active_case_id') || ''));
const caseTitle = computed(() => localStorage.getItem(`case_title:${caseId.value}`) || `当前案件：${caseId.value}`);
const isOverview = computed(() => route.path === `/cases/${caseId.value}`);
const isGraph = computed(() => route.path.endsWith('/graph'));
const activeLayer = computed(() => {
  const value = String(route.query.layer || 'document');
  return value === 'passage' || value === 'raw' ? value : 'document';
});
const expandedGraph = ref(false);

function graphTo(layer: 'document' | 'passage' | 'raw') {
  return `/cases/${caseId.value}/graph?layer=${layer}`;
}
</script>
