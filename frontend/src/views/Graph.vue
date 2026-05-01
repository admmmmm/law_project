<template>
  <div class="h-full flex flex-col bg-slate-950 text-white">
    <div class="h-14 border-b border-slate-800 px-5 flex items-center justify-between shrink-0">
      <div>
        <div class="font-bold">证据图谱</div>
        <div class="text-xs text-slate-400">{{ activeCaseId || '未选择案件' }}</div>
      </div>
      <div class="flex items-center gap-2">
        <button class="toolbar-btn" :disabled="!activeCaseId" @click="runAnalysis">重新分析</button>
        <button class="toolbar-btn" :disabled="!activeCaseId" @click="loadGraph">刷新图谱</button>
      </div>
    </div>

    <div v-if="error" class="m-4 p-3 bg-rose-950 border border-rose-800 text-rose-100 rounded">{{ error }}</div>

    <div v-if="!activeCaseId" class="flex-1 grid place-items-center text-center">
      <div>
        <Network class="mx-auto text-slate-600 mb-3" :size="50" />
        <div class="font-bold text-slate-200">还没有选择案件</div>
        <router-link to="/" class="text-teal-300 text-sm mt-2 inline-block">去案件导入页创建或选择案件</router-link>
      </div>
    </div>

    <div v-else-if="loading" class="flex-1 grid place-items-center text-slate-400">正在读取图谱...</div>

    <div v-else class="flex-1 grid grid-cols-[1fr_340px] min-h-0">
      <section class="relative overflow-hidden">
        <svg class="w-full h-full" viewBox="0 0 1000 720">
          <defs>
            <radialGradient id="nodeGlow">
              <stop offset="0%" stop-color="#2dd4bf" stop-opacity="0.9" />
              <stop offset="100%" stop-color="#0f172a" stop-opacity="0.1" />
            </radialGradient>
          </defs>
          <g stroke="#334155" stroke-width="1.2">
            <line
              v-for="edge in positionedEdges"
              :key="edge.edge_id"
              :x1="edge.source.x"
              :y1="edge.source.y"
              :x2="edge.target.x"
              :y2="edge.target.y"
            />
          </g>
          <g>
            <g
              v-for="node in positionedNodes"
              :key="node.node_id"
              class="cursor-pointer"
              @click="selectedNodeId = node.node_id"
            >
              <circle :cx="node.x" :cy="node.y" :r="node.type === 'evidence' ? 34 : 24" fill="url(#nodeGlow)" />
              <circle
                :cx="node.x"
                :cy="node.y"
                :r="node.type === 'evidence' ? 22 : 15"
                :fill="nodeColor(node.type)"
                :stroke="selectedNodeId === node.node_id ? '#facc15' : '#94a3b8'"
                stroke-width="2"
              />
              <text :x="node.x" :y="node.y + 42" text-anchor="middle" fill="#cbd5e1" font-size="12">
                {{ shortLabel(node.label) }}
              </text>
            </g>
          </g>
        </svg>

        <div v-if="graph.nodes.length === 0" class="absolute inset-0 grid place-items-center text-center">
          <div>
            <Network class="mx-auto text-slate-600 mb-3" :size="54" />
            <div class="font-bold text-slate-200">图谱还是空的</div>
            <p class="text-sm text-slate-400 mt-1">先导入证据，然后运行分析。</p>
          </div>
        </div>
      </section>

      <aside class="border-l border-slate-800 bg-slate-900 p-4 overflow-auto">
        <div class="grid grid-cols-3 gap-2 mb-4">
          <div class="stat"><span>节点</span><strong>{{ graph.nodes.length }}</strong></div>
          <div class="stat"><span>关系</span><strong>{{ graph.edges.length }}</strong></div>
          <div class="stat"><span>线索</span><strong>{{ graph.clues.length }}</strong></div>
        </div>

        <section v-if="selectedNode" class="panel">
          <h3>{{ selectedNode.label }}</h3>
          <p class="text-xs text-slate-400 font-mono break-all">{{ selectedNode.node_id }}</p>
          <div class="mt-3 text-sm text-slate-300">类型：{{ selectedNode.type }}</div>
        </section>

        <section class="panel mt-4">
          <h3>风险线索</h3>
          <div v-if="graph.clues.length === 0" class="text-sm text-slate-400">暂无线索。</div>
          <div v-for="clue in graph.clues" :key="clue.clue_id" class="border-t border-slate-800 py-3 first:border-t-0">
            <div class="font-bold text-sm">{{ clue.title }}</div>
            <div class="text-xs text-slate-400 mt-1">{{ clue.description }}</div>
          </div>
        </section>

        <section class="panel mt-4">
          <h3>关系样本</h3>
          <div v-if="graph.edges.length === 0" class="text-sm text-slate-400">暂无关系。</div>
          <div v-for="edge in graph.edges.slice(0, 12)" :key="edge.edge_id" class="text-xs border-t border-slate-800 py-2 first:border-t-0">
            <span class="text-teal-300">{{ labelOf(edge.source_id) }}</span>
            <span class="text-slate-500"> --{{ edge.relation }}-> </span>
            <span class="text-sky-300">{{ labelOf(edge.target_id) }}</span>
          </div>
        </section>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { Network } from 'lucide-vue-next';
import { backendApi, type GraphNode, type InvestigationGraph } from '../api/backend';

type PositionedNode = GraphNode & { x: number; y: number };

const activeCaseId = ref(localStorage.getItem('active_case_id') || '');
const loading = ref(false);
const error = ref('');
const selectedNodeId = ref('');
const graph = ref<InvestigationGraph>({ case_id: activeCaseId.value, nodes: [], edges: [], clues: [] });

onMounted(loadGraph);

const positionedNodes = computed<PositionedNode[]>(() => {
  const count = Math.max(graph.value.nodes.length, 1);
  const centerX = 500;
  const centerY = 350;
  const radius = count > 12 ? 285 : 230;
  return graph.value.nodes.map((node, index) => {
    if (node.type === 'evidence') {
      return { ...node, x: centerX, y: 110 + index * 58 };
    }
    const angle = (Math.PI * 2 * index) / count;
    return { ...node, x: centerX + Math.cos(angle) * radius, y: centerY + Math.sin(angle) * radius };
  });
});

const positionedEdges = computed(() => {
  const map = new Map(positionedNodes.value.map((node) => [node.node_id, node]));
  return graph.value.edges
    .map((edge) => ({ ...edge, source: map.get(edge.source_id), target: map.get(edge.target_id) }))
    .filter((edge): edge is typeof edge & { source: PositionedNode; target: PositionedNode } => Boolean(edge.source && edge.target));
});

const selectedNode = computed(() => graph.value.nodes.find((node) => node.node_id === selectedNodeId.value));

async function loadGraph() {
  if (!activeCaseId.value) return;
  loading.value = true;
  error.value = '';
  try {
    graph.value = await backendApi.getGraph(activeCaseId.value);
    selectedNodeId.value = graph.value.nodes[0]?.node_id || '';
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    loading.value = false;
  }
}

async function runAnalysis() {
  if (!activeCaseId.value) return;
  await backendApi.runAnalysis(activeCaseId.value);
  await loadGraph();
}

function nodeColor(type: string) {
  if (type === 'evidence') return '#0f766e';
  if (type === 'transaction') return '#2563eb';
  if (type === 'fact') return '#9333ea';
  return '#475569';
}

function shortLabel(label: string) {
  return label.length > 12 ? `${label.slice(0, 12)}...` : label;
}

function labelOf(nodeId: string) {
  return graph.value.nodes.find((node) => node.node_id === nodeId)?.label || nodeId;
}
</script>

<style scoped>
.toolbar-btn {
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 7px 11px;
  color: #cbd5e1;
  font-size: 13px;
}
.toolbar-btn:disabled {
  opacity: 0.45;
}
.stat {
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 8px;
  padding: 10px;
}
.stat span {
  display: block;
  color: #94a3b8;
  font-size: 12px;
}
.stat strong {
  display: block;
  color: white;
  font-size: 22px;
}
.panel {
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 8px;
  padding: 14px;
}
.panel h3 {
  font-weight: 700;
  margin-bottom: 8px;
}
</style>
