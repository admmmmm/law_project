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
          <strong class="text-base">{{ runStatus }}</strong>
        </div>
      </div>

      <section class="rounded-lg border border-slate-200 bg-white p-5">
        <h2 class="font-bold">分析摘要</h2>
        <p class="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-700">
          {{ analysisSummary }}
        </p>
      </section>

      <section class="grid gap-4 lg:grid-cols-3">
        <article v-for="section in portraitLayers" :key="section.title" class="rounded-lg border border-slate-200 bg-white p-5">
          <h2 class="font-bold">{{ section.title }}</h2>
          <p class="mt-1 text-xs text-slate-500">{{ section.subtitle }}</p>
          <ul class="mt-3 space-y-2 text-sm leading-6 text-slate-700">
            <li v-for="item in section.items" :key="item" class="rounded border border-slate-100 bg-slate-50 p-3">
              {{ item }}
            </li>
          </ul>
        </article>
      </section>

      <section class="rounded-lg border border-slate-200 bg-white p-5">
        <div class="flex items-center justify-between gap-3">
          <h2 class="font-bold">案件级线索</h2>
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
import { computed, onMounted, ref } from 'vue';
import { backendApi, type AnalysisRunResult, type InvestigationGraph } from '../api/backend';

const activeCaseId = ref(localStorage.getItem('active_case_id') || '');
const loading = ref(false);
const error = ref('');
const result = ref<AnalysisRunResult | null>(null);
const graph = ref<InvestigationGraph | null>(null);

const analysisSummary = computed(() => {
  if (result.value?.summary) return result.value.summary;
  if (graph.value?.nodes.length) {
    return `已有图谱结果：${graph.value.nodes.length} 个节点、${graph.value.edges.length} 条关系、${graph.value.clues.length} 条案件级线索。点击“运行分析”可重新生成。`;
  }
  return '暂无分析结果。导入证据后点击“运行分析”。';
});

const runStatus = computed(() => {
  if (loading.value) return '分析中';
  if (result.value?.status) return result.value.status;
  if (graph.value?.nodes.length) return '已有图谱';
  return '未运行';
});

const portraitLayers = computed(() => {
  const currentGraph = graph.value;
  const clues = currentGraph?.clues || [];
  const fund = clues.filter((clue) => clue.category === 'fund_flow').map((clue) => clue.description);
  const duty = clues.filter((clue) => clue.category === 'duty_behavior').map((clue) => clue.description);
  const subjective = clues.filter((clue) => clue.category === 'subjective_state').map((clue) => clue.description);
  const gaps = clues.filter((clue) => clue.category === 'evidence_gap').map((clue) => clue.description);
  const topEntities = topEntityLabels(currentGraph);
  return [
    {
      title: '第一层：基础信息聚合',
      subtitle: '这个人是谁、在哪工作、有什么职权、和谁有关。',
      items: [
        `图谱规模：${currentGraph?.nodes.length || 0} 个节点、${currentGraph?.edges.length || 0} 条关系。`,
        `重点主体/对象：${topEntities.length ? topEntities.join('、') : '待识别'}`,
      ],
    },
    {
      title: '第二层：行为事实还原',
      subtitle: '做了什么、和谁有关、资金怎么流、处置如何变化。',
      items: [...(fund.length ? fund : ['暂无明确资金链条。']), ...(duty.length ? duty : ['暂无明确职务处置链条。'])],
    },
    {
      title: '第三层：主观方面推理',
      subtitle: '知不知道、是否故意、是否徇私、对结果是什么态度。',
      items: [
        ...(subjective.length ? subjective : ['暂未形成足够主观状态线索。']),
        ...(gaps.length ? gaps : ['需要补强能证明明知、请托、利益输送和处置结果之间关系的材料。']),
      ],
    },
  ];
});

onMounted(loadGraph);

async function loadGraph() {
  if (!activeCaseId.value) return;
  try {
    graph.value = await backendApi.getGraph(activeCaseId.value);
  } catch {
    graph.value = null;
  }
}

function topEntityLabels(currentGraph: InvestigationGraph | null) {
  if (!currentGraph) return [];
  const labels = new Map(currentGraph.nodes.filter((node) => node.type !== 'evidence' && node.type !== 'algorithm_provider').map((node) => [node.node_id, node.label]));
  const degree = new Map<string, number>();
  currentGraph.edges.forEach((edge) => {
    if (labels.has(edge.source_id)) degree.set(edge.source_id, (degree.get(edge.source_id) || 0) + 1);
    if (labels.has(edge.target_id)) degree.set(edge.target_id, (degree.get(edge.target_id) || 0) + 1);
  });
  return Array.from(degree.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([id]) => labels.get(id) || id);
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
