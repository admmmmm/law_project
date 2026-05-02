<template>
  <div class="h-full overflow-auto bg-slate-100 p-6 text-slate-900">
    <section class="mx-auto max-w-6xl space-y-4">
      <div class="rounded-lg border border-slate-200 bg-white p-5">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 class="text-xl font-bold">智能分析</h1>
            <p class="mt-1 text-sm text-slate-500">白板页：只负责触发后端分析，并展示返回的图谱统计和线索。</p>
          </div>
          <button class="btn-primary" :disabled="!activeCaseId || loading" @click="runAnalysis">
            {{ loading ? '分析中...' : '运行分析' }}
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

      <div class="grid gap-4 md:grid-cols-4">
        <div class="stat-card">
          <span>节点</span>
          <strong>{{ graph?.nodes.length ?? 0 }}</strong>
        </div>
        <div class="stat-card">
          <span>关系</span>
          <strong>{{ graph?.edges.length ?? 0 }}</strong>
        </div>
        <div class="stat-card">
          <span>线索</span>
          <strong>{{ graph?.clues.length ?? 0 }}</strong>
        </div>
        <div class="stat-card">
          <span>状态</span>
          <strong class="text-base">{{ result?.status || '未运行' }}</strong>
        </div>
      </div>

      <section class="rounded-lg border border-slate-200 bg-white p-5">
        <h2 class="font-bold">分析摘要</h2>
        <p class="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-700">
          {{ result?.summary || '暂无分析结果。导入证据后点击“运行分析”。' }}
        </p>
      </section>

      <section class="rounded-lg border border-slate-200 bg-white p-5">
        <div class="flex items-center justify-between gap-3">
          <h2 class="font-bold">风险线索</h2>
          <router-link class="text-sm font-bold text-teal-700" to="/graph">查看证据图谱</router-link>
        </div>
        <div v-if="!graph?.clues.length" class="mt-3 text-sm text-slate-500">暂无线索。</div>
        <div v-else class="mt-3 divide-y divide-slate-100">
          <article v-for="clue in graph.clues" :key="clue.clue_id" class="py-3">
            <div class="flex flex-wrap items-center gap-2">
              <h3 class="font-bold">{{ clue.title }}</h3>
              <span class="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{{ clue.category }}</span>
              <span class="rounded px-2 py-0.5 text-xs font-bold" :class="riskClass(clue.risk_level)">
                {{ clue.risk_level }}
              </span>
            </div>
            <p class="mt-1 text-sm leading-6 text-slate-600">{{ clue.description }}</p>
            <p class="mt-1 text-xs text-slate-400">证据：{{ clue.evidence_ids.join(', ') || '无' }}</p>
          </article>
        </div>
      </section>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { backendApi, type AnalysisRunResult, type InvestigationGraph } from '../api/backend';

const activeCaseId = ref(localStorage.getItem('active_case_id') || '');
const loading = ref(false);
const error = ref('');
const result = ref<AnalysisRunResult | null>(null);
const graph = ref<InvestigationGraph | null>(null);

onMounted(loadGraph);

async function loadGraph() {
  if (!activeCaseId.value) return;
  try {
    graph.value = await backendApi.getGraph(activeCaseId.value);
  } catch {
    graph.value = null;
  }
}

async function runAnalysis() {
  if (!activeCaseId.value) return;
  loading.value = true;
  error.value = '';
  try {
    result.value = await backendApi.runAnalysis(activeCaseId.value);
    graph.value = result.value.graph;
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    loading.value = false;
  }
}

function riskClass(level: string) {
  if (level === 'high') return 'bg-rose-100 text-rose-700';
  if (level === 'low') return 'bg-emerald-100 text-emerald-700';
  return 'bg-amber-100 text-amber-700';
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
.stat-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: white;
  padding: 16px;
}
.stat-card span {
  display: block;
  color: #64748b;
  font-size: 13px;
}
.stat-card strong {
  display: block;
  margin-top: 6px;
  font-size: 28px;
  line-height: 1;
}
</style>
