<template>
  <header class="h-14 bg-white border-b border-slate-200 px-5 flex items-center justify-between shrink-0">
    <div>
      <div class="text-base font-bold text-slate-900">检察侦查画像模型</div>
      <div class="text-xs text-slate-500">案件导入、图谱分析、RAG 检索联调工作台</div>
    </div>
    <div class="flex items-center gap-2 text-xs">
      <span class="h-2 w-2 rounded-full" :class="online ? 'bg-emerald-500' : 'bg-rose-500'"></span>
      <span class="text-slate-600">{{ online ? '后端在线' : '后端未连接' }}</span>
    </div>
  </header>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { backendApi } from '../api/backend';

const online = ref(false);

onMounted(async () => {
  try {
    await backendApi.health();
    online.value = true;
  } catch {
    online.value = false;
  }
});
</script>
