<template>
  <header class="topbar">
    <AppLogo compact title="检察办案工作台" />
    <div class="topbar-copy">
      <div class="space-label">{{ isCaseSpace ? 'Case Space 案件空间' : 'Workspace 工作台' }}</div>
      <h1>{{ title }}</h1>
      <p>{{ description }}</p>
    </div>
    <div class="topbar-actions">
      <router-link v-if="primaryAction" class="btn primary" :to="primaryAction.to">{{ primaryAction.label }}</router-link>
      <div class="service-pill" :class="{ offline: !online }">
        <span></span>
        {{ online ? '后端服务正常' : '后端未连接' }}
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { backendApi } from '../api/backend';
import AppLogo from './AppLogo.vue';

const route = useRoute();
const online = ref(false);

const title = computed(() => String(route.meta.title || '工作台'));
const description = computed(() => String(route.meta.description || '选择或创建案件，并管理系统级能力。'));
const isCaseSpace = computed(() => route.meta.space === 'case');
const primaryAction = computed(() => route.meta.primaryAction as { label: string; to: string } | undefined);

onMounted(async () => {
  try {
    await backendApi.health();
    online.value = true;
  } catch {
    online.value = false;
  }
});
</script>
