<template>
  <aside class="w-56 bg-slate-950 text-slate-100 h-screen shrink-0 flex flex-col">
    <div class="px-5 h-14 flex items-center border-b border-slate-800 font-bold">侦查中台</div>
    <nav class="p-3 space-y-4 text-sm overflow-auto">
      <section>
        <div class="nav-group">案件工作台</div>
        <router-link class="nav-link" active-class="nav-active" :to="linkTo('')">案件导入</router-link>
        <router-link class="nav-link" active-class="nav-active" :to="linkTo('graph')">案件证据地图</router-link>
        <router-link class="nav-link" active-class="nav-active" :to="linkTo('portrait')">画像报告</router-link>
        <router-link class="nav-link" active-class="nav-active" :to="linkTo('intelligence')">智能分析</router-link>
      </section>

      <section>
        <div class="nav-group">知识与技能</div>
        <router-link class="nav-link" active-class="nav-active" :to="linkTo('skills')">检察技能库</router-link>
        <router-link class="nav-link" active-class="nav-active" :to="linkTo('legal-knowledge')">法律知识库</router-link>
      </section>

      <section>
        <div class="nav-group">调试与维护</div>
        <router-link class="nav-link" active-class="nav-active" :to="linkTo('chat')">证据问答</router-link>
        <router-link v-if="showContextDebug" class="nav-link" active-class="nav-active" :to="linkTo('analysis-context')">分析上下文</router-link>
        <router-link class="nav-link" active-class="nav-active" :to="linkTo('graph', { layer: 'raw' })">原始图谱维护</router-link>
        <router-link class="nav-link" active-class="nav-active" :to="linkTo('settings')">设置</router-link>
      </section>
    </nav>
    <div class="mt-auto p-4 text-xs text-slate-400 border-t border-slate-800">
      adm 整合分支<br />
      Backend: <span class="font-mono">:8000</span><br />
      Frontend: <span class="font-mono">:5173</span>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();
const workspaceId = computed(() => String(route.params.workspaceId || localStorage.getItem('active_workspace_id') || '').trim());
const showContextDebug = ref(false);

onMounted(() => {
  showContextDebug.value = localStorage.getItem('devMode') === 'true' && localStorage.getItem('showAnalysisContextDebug') === 'true';
  window.addEventListener('storage', () => {
    showContextDebug.value = localStorage.getItem('devMode') === 'true' && localStorage.getItem('showAnalysisContextDebug') === 'true';
  });
});

function linkTo(page: string, query?: Record<string, string>) {
  const id = workspaceId.value;
  const path = !id ? (page ? `/${page}` : '/') : (page ? `/${id}/${page}` : `/${id}`);
  if (!query) return path;
  const params = new URLSearchParams(query);
  return `${path}?${params.toString()}`;
}
</script>

<style scoped>
.nav-link {
  display: block;
  border-radius: 8px;
  padding: 10px 12px;
  color: rgb(203 213 225);
}
.nav-group {
  padding: 4px 12px 6px;
  color: rgb(100 116 139);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.08em;
}
.nav-link:hover,
.nav-active {
  background: rgb(30 41 59);
  color: white;
}
</style>
