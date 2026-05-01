<template>
  <div class="h-full flex flex-col bg-slate-100">
    <div class="h-14 bg-white border-b border-slate-200 px-5 flex items-center justify-between shrink-0">
      <div>
        <div class="font-bold text-slate-900">证据图谱</div>
        <div class="text-xs text-slate-500">{{ activeCaseId || '未选择案件' }}</div>
      </div>
      <div class="flex items-center gap-2">
        <button class="btn" :disabled="!activeCaseId || loading" @click="runAnalysis">重新分析</button>
        <button class="btn" :disabled="!activeCaseId || loading" @click="loadGraph">刷新</button>
      </div>
    </div>

    <div v-if="error" class="m-4 p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded">{{ error }}</div>

    <div v-if="!activeCaseId" class="flex-1 grid place-items-center text-center">
      <div>
        <Network class="mx-auto text-slate-300 mb-3" :size="54" />
        <div class="font-bold text-slate-700">还没有选择案件</div>
        <router-link class="text-teal-700 text-sm mt-2 inline-block" to="/">去白板工作台选择案件</router-link>
      </div>
    </div>

    <div v-else class="flex-1 grid grid-cols-[1fr_340px] min-h-0">
      <section class="bg-white min-h-0">
        <div v-if="loading" class="h-full grid place-items-center text-slate-500">正在加载图谱...</div>
        <div v-else-if="graph.nodes.length === 0" class="h-full grid place-items-center text-center">
          <div>
            <Network class="mx-auto text-slate-300 mb-3" :size="54" />
            <div class="font-bold text-slate-700">图谱还是空的</div>
            <p class="text-sm text-slate-500 mt-1">先导入证据，然后运行分析。</p>
          </div>
        </div>
        <RelationGraph
          v-else
          ref="graphRef"
          class="h-full w-full"
          :options="graphOptions"
          :on-node-click="onNodeClick"
          :on-line-click="onLineClick"
        />
      </section>

      <aside class="bg-slate-950 text-white p-4 overflow-auto border-l border-slate-800">
        <div class="grid grid-cols-3 gap-2 mb-4">
          <div class="stat"><span>节点</span><strong>{{ graph.nodes.length }}</strong></div>
          <div class="stat"><span>关系</span><strong>{{ graph.edges.length }}</strong></div>
          <div class="stat"><span>线索</span><strong>{{ graph.clues.length }}</strong></div>
        </div>

        <div class="panel">
          <h3>当前选择</h3>
          <div v-if="selectedLabel" class="mt-2">
            <div class="font-bold">{{ selectedLabel }}</div>
            <div class="text-xs text-slate-400 break-all mt-1">{{ selectedMeta }}</div>
          </div>
          <div v-else class="text-sm text-slate-400">点击节点或关系查看详情。</div>
        </div>

        <div class="panel mt-4">
          <h3>风险线索</h3>
          <div v-if="graph.clues.length === 0" class="text-sm text-slate-400">暂无线索。</div>
          <div v-for="clue in graph.clues" :key="clue.clue_id" class="border-t border-slate-800 py-3 first:border-t-0">
            <div class="font-bold text-sm">{{ clue.title }}</div>
            <div class="text-xs text-slate-400 mt-1">{{ clue.description }}</div>
          </div>
        </div>

        <div class="panel mt-4">
          <h3>聚合说明</h3>
          <p class="text-sm text-slate-400 leading-6">
            流水不再逐笔画节点。后端按主体、对象、关系聚合，边上保留 count、amount_total、time_sample。
          </p>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue';
import RelationGraph from 'relation-graph/vue3';
import { Network } from 'lucide-vue-next';
import { backendApi, type GraphEdge, type GraphNode, type InvestigationGraph } from '../api/backend';

const activeCaseId = ref(localStorage.getItem('active_case_id') || '');
const loading = ref(false);
const error = ref('');
const graphRef = ref<any>(null);
const selectedLabel = ref('');
const selectedMeta = ref('');
const graph = ref<InvestigationGraph>({ case_id: activeCaseId.value, nodes: [], edges: [], clues: [] });

const graphOptions = {
  debug: false,
  allowSwitchLineShape: true,
  allowSwitchJunctionPoint: true,
  defaultNodeShape: 1,
  defaultLineShape: 6,
  defaultJunctionPoint: 'border',
  defaultNodeWidth: 118,
  defaultNodeHeight: 42,
  defaultLineColor: '#64748b',
  defaultLineWidth: 1.5,
  layouts: [
    {
      label: 'center',
      layoutName: 'force',
      maxLayoutTimes: 220,
    },
  ],
};

const nodeMap = computed(() => new Map(graph.value.nodes.map((node) => [node.node_id, node])));

onMounted(loadGraph);

async function loadGraph() {
  if (!activeCaseId.value) return;
  loading.value = true;
  error.value = '';
  try {
    graph.value = await backendApi.getGraph(activeCaseId.value);
    await nextTick();
    renderGraph();
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    loading.value = false;
  }
}

async function runAnalysis() {
  if (!activeCaseId.value) return;
  loading.value = true;
  error.value = '';
  try {
    await backendApi.runAnalysis(activeCaseId.value);
    graph.value = await backendApi.getGraph(activeCaseId.value);
    await nextTick();
    renderGraph();
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    loading.value = false;
  }
}

function renderGraph() {
  if (!graphRef.value || graph.value.nodes.length === 0) return;
  const jsonData = {
    rootId: graph.value.nodes[0]?.node_id,
    nodes: graph.value.nodes.map(toRelationNode),
    lines: graph.value.edges.map(toRelationLine),
  };
  graphRef.value.setJsonData(jsonData);
}

function toRelationNode(node: GraphNode) {
  return {
    id: node.node_id,
    text: trim(node.label, 18),
    data: node,
    color: nodeColor(node.type),
    borderColor: node.type === 'evidence' ? '#0f766e' : '#334155',
    fontColor: '#0f172a',
    width: node.type === 'evidence' ? 150 : 118,
    height: node.type === 'evidence' ? 52 : 42,
    nodeShape: 1,
  };
}

function toRelationLine(edge: GraphEdge) {
  const count = edge.properties?.count ? ` x${edge.properties.count}` : '';
  const amount = edge.properties?.amount_total ? ` ¥${edge.properties.amount_total}` : '';
  return {
    id: edge.edge_id,
    from: edge.source_id,
    to: edge.target_id,
    text: trim(`${edge.relation}${count}${amount}`, 28),
    data: edge,
    color: edgeColor(edge),
    lineWidth: edge.properties?.count && Number(edge.properties.count) > 1 ? 2.5 : 1.2,
  };
}

function onNodeClick(node: { data?: GraphNode }) {
  if (!node.data) return;
  selectedLabel.value = node.data.label;
  selectedMeta.value = `${node.data.type} / ${node.data.node_id}`;
}

function onLineClick(line: { data?: GraphEdge }) {
  if (!line.data) return;
  const source = nodeMap.value.get(line.data.source_id)?.label || line.data.source_id;
  const target = nodeMap.value.get(line.data.target_id)?.label || line.data.target_id;
  selectedLabel.value = `${source} -> ${target}`;
  selectedMeta.value = `${line.data.relation} / ${JSON.stringify(line.data.properties || {})}`;
}

function nodeColor(type: string) {
  if (type === 'evidence') return '#ccfbf1';
  if (type === 'transaction') return '#dbeafe';
  return '#f8fafc';
}

function edgeColor(edge: GraphEdge) {
  if (edge.relation.includes('资金') || edge.relation.includes('转账') || edge.relation.includes('交易')) return '#2563eb';
  return '#64748b';
}

function trim(text: string, length: number) {
  return text.length > length ? `${text.slice(0, length)}...` : text;
}
</script>

<style scoped>
.btn {
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 7px 11px;
  font-size: 13px;
  font-weight: 700;
}
.btn:disabled {
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
  font-weight: 800;
  margin-bottom: 8px;
}
</style>
