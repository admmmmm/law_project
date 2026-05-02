<template>
  <div class="h-full overflow-auto bg-slate-100 p-6 text-slate-900">
    <section class="mx-auto max-w-5xl space-y-4">
      <div class="rounded-lg border border-slate-200 bg-white p-5">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 class="text-xl font-bold">画像报告</h1>
            <p class="mt-1 text-sm text-slate-500">白板页：调用后端报告接口，直接展示当前报告内容。</p>
          </div>
          <button class="btn-primary" :disabled="!activeCaseId || loading" @click="generateReport">
            {{ loading ? '生成中...' : '生成画像报告' }}
          </button>
        </div>
        <div class="mt-4 text-sm">
          <span class="text-slate-500">当前案件：</span>
          <span class="font-mono">{{ activeCaseId || '未选择案件' }}</span>
        </div>
        <p v-if="!activeCaseId" class="mt-3 rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          请先到“案件导入”页新建或选择案件。
        </p>
        <p v-if="error" class="mt-3 rounded border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{{ error }}</p>
      </div>

      <section v-if="!report" class="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
        暂无报告。运行智能分析后，再生成画像报告效果更完整。
      </section>

      <section v-else class="rounded-lg border border-slate-200 bg-white p-6">
        <div class="border-b border-slate-200 pb-4">
          <h2 class="text-lg font-bold">{{ report.title }}</h2>
          <p class="mt-1 text-xs text-slate-500">
            报告 ID：{{ report.report_id }} / 生成时间：{{ formatTime(report.generated_at) }}
          </p>
        </div>

        <div class="mt-5 space-y-5">
          <article v-for="section in report.sections" :key="section.title">
            <h3 class="font-bold">{{ section.title }}</h3>
            <ul class="mt-2 space-y-2 text-sm leading-6 text-slate-700">
              <li v-for="item in section.items" :key="item" class="rounded border border-slate-100 bg-slate-50 p-3">
                {{ item }}
              </li>
            </ul>
          </article>
        </div>

        <div class="mt-6 rounded-lg border border-teal-100 bg-teal-50 p-4">
          <h3 class="font-bold text-teal-900">参考建议</h3>
          <ul class="mt-2 space-y-2 text-sm leading-6 text-teal-900">
            <li v-for="item in report.suggestions" :key="item">{{ item }}</li>
          </ul>
        </div>
      </section>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { backendApi, type PortraitReport } from '../api/backend';

const activeCaseId = ref(localStorage.getItem('active_case_id') || '');
const loading = ref(false);
const error = ref('');
const report = ref<PortraitReport | null>(null);

async function generateReport() {
  if (!activeCaseId.value) return;
  loading.value = true;
  error.value = '';
  try {
    report.value = await backendApi.generatePortrait(activeCaseId.value);
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    loading.value = false;
  }
}

function formatTime(value: string) {
  return new Date(value).toLocaleString();
}
</script>

<style scoped>
.btn-primary {
  border-radius: 6px;
  background: #0f766e;
  color: white;
  padding: 9px 14px;
  font-size: 14px;
  font-weight: 800;
}
.btn-primary:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
</style>
