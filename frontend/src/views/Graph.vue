<template>
  <div class="h-full flex flex-col bg-slate-100 text-slate-900">
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
      <section class="graph-stage min-h-0">
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
          :key="graphRenderKey"
          ref="graphRef"
          class="graph-view h-full w-full"
          :options="graphOptions"
          :on-node-click="onNodeClick"
          :on-line-click="onLineClick"
        />
        <div v-if="!loading && graph.nodes.length > 0" class="graph-controls">
          <div class="control-head">
            <span>时间轴添加证据</span>
            <strong>{{ currentTimelineLabel }}</strong>
          </div>
          <div class="mode-row">
            <button
              v-for="item in viewModes"
              :key="item.key"
              class="mode-btn"
              :class="{ active: viewMode === item.key }"
              @click="setViewMode(item.key)"
            >
              {{ item.label }}
            </button>
          </div>
          <div class="mode-row">
            <button
              v-for="item in layoutModes"
              :key="item.key"
              class="mode-btn layout"
              :class="{ active: layoutMode === item.key }"
              @click="setLayoutMode(item.key)"
            >
              {{ item.label }}
            </button>
          </div>
          <input
            v-model.number="timelineIndex"
            class="timeline"
            type="range"
            min="0"
            :max="Math.max(timelinePoints.length - 1, 0)"
            step="1"
            @input="renderGraph"
          />
          <div class="tag-list">
            <label v-for="item in availableCategories" :key="item.key" class="tag-item">
              <input v-model="selectedCategories" type="checkbox" :value="item.key" @change="renderGraph" />
              <span>{{ item.label }} {{ item.count }}</span>
            </label>
          </div>
        </div>
        <div v-if="!loading && graph.nodes.length > 0" class="graph-note">
          当前渲染 {{ renderedNodeCount }} / {{ graph.nodes.length }} 个节点，{{ renderedEdgeCount }} / {{ graph.edges.length }} 条关系
        </div>
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
const graphRenderKey = ref(0);
const renderedNodeCount = ref(0);
const renderedEdgeCount = ref(0);
const timelineIndex = ref(0);
const timelinePoints = ref<string[]>(['全部时间']);
const selectedCategories = ref<string[]>([]);
const viewMode = ref<'core' | 'evidence' | 'all'>('core');
const layoutMode = ref<'tree' | 'center' | 'circle' | 'force'>('tree');
const MAX_RENDER_NODES = 260;
const MAX_RENDER_EDGES = 520;

const viewModes = [
  { key: 'core', label: '核心邻域' },
  { key: 'evidence', label: '证据链' },
  { key: 'all', label: '全量筛选' },
] as const;

const layoutModes = [
  { key: 'tree', label: '树形' },
  { key: 'center', label: '中心' },
  { key: 'circle', label: '环形' },
  { key: 'force', label: '力导' },
] as const;

const FILTER_TAGS = [
  { key: 'bank_flow_evidence', label: '流水证据' },
  { key: 'case_evidence', label: '案情文书' },
  { key: 'person', label: '人物' },
  { key: 'organization', label: '机构/公司' },
  { key: 'fund_account', label: '资金对象' },
  { key: 'fund_flow', label: '资金往来' },
  { key: 'duty_behavior', label: '职务行为' },
  { key: 'subjective_state', label: '主观状态' },
  { key: 'repeated_relation', label: '重复关系' },
  { key: 'time_mapped', label: '有时间映射' },
  { key: 'clue_related', label: '线索相关' },
  { key: 'algorithm', label: '算法节点' },
  { key: 'memory', label: '人工记忆' },
  { key: 'other', label: '其他' },
];

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
  defaultNodeFontColor: '#0f172a',
  backgroundColor: '#f8fafc',
  layouts: [
    {
      label: 'tree',
      layoutName: 'tree',
      from: 'left',
      min_per_width: 220,
      max_per_width: 420,
      min_per_height: 42,
      max_per_height: 90,
    },
  ],
};

const nodeMap = computed(() => new Map(graph.value.nodes.map((node) => [node.node_id, node])));
const availableCategories = computed(() => {
  const counts = new Map<string, number>();
  graph.value.nodes.forEach((node) => itemTags(node).forEach((tag) => addCount(counts, tag)));
  graph.value.edges.forEach((edge) => itemTags(edge).forEach((tag) => addCount(counts, tag)));
  return FILTER_TAGS.filter((item) => counts.has(item.key)).map((item) => ({ ...item, count: counts.get(item.key) || 0 }));
});
const currentTimelineLabel = computed(() => timelinePoints.value[timelineIndex.value] || '全部时间');

onMounted(loadGraph);

async function loadGraph() {
  if (!activeCaseId.value) return;
  loading.value = true;
  error.value = '';
  try {
    graph.value = await backendApi.getGraph(activeCaseId.value);
    syncTimelineAndTags();
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    loading.value = false;
  }
  await nextTick();
  renderGraph();
}

async function runAnalysis() {
  if (!activeCaseId.value) return;
  loading.value = true;
  error.value = '';
  try {
    await backendApi.runAnalysis(activeCaseId.value);
    graph.value = await backendApi.getGraph(activeCaseId.value);
    syncTimelineAndTags();
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    loading.value = false;
  }
  await nextTick();
  renderGraph();
}

function renderGraph() {
  if (!graphRef.value || graph.value.nodes.length === 0) return;
  graphOptions.layouts = [layoutConfig(layoutMode.value)];
  const visible = buildRenderableGraph();
  renderedNodeCount.value = visible.nodes.length;
  renderedEdgeCount.value = visible.edges.length;
  const jsonData = {
    rootId: visible.nodes[0]?.node_id,
    nodes: visible.nodes.map(toRelationNode),
    lines: visible.edges.map(toRelationLine),
  };
  graphRef.value.setJsonData(jsonData, (graphInstance: any) => {
    graphInstance.doLayout();
    graphInstance.moveToCenter();
    graphInstance.zoomToFit();
  });
}

function buildRenderableGraph() {
  const categorySet = new Set(selectedCategories.value);
  const cutoff = timelinePoints.value[timelineIndex.value] || '';
  const hasCutoff = Boolean(cutoff && cutoff !== '全部时间');
  const allowedByTime = (value: string | null) => !hasCutoff || !value || value <= cutoff;
  const timeNodes = graph.value.nodes.filter((node) => allowedByTime(itemDate(node)) && selectedByTags(node, categorySet));
  const timeNodeIds = new Set(timeNodes.map((node) => node.node_id));
  const selectedEdges = graph.value.edges.filter(
    (edge) => selectedByTags(edge, categorySet) && allowedByTime(itemDate(edge)) && timeNodeIds.has(edge.source_id) && timeNodeIds.has(edge.target_id),
  );
  const filteredNodes = timeNodes;
  const filteredNodeIds = new Set(filteredNodes.map((node) => node.node_id));
  let filteredEdges = selectedEdges.filter((edge) => filteredNodeIds.has(edge.source_id) && filteredNodeIds.has(edge.target_id));

  const modeLimitedIds = modeNodeIds(filteredNodes, filteredEdges);
  const modeNodes = filteredNodes.filter((node) => modeLimitedIds.has(node.node_id));
  const modeNodeIdSet = new Set(modeNodes.map((node) => node.node_id));
  filteredEdges = filteredEdges.filter((edge) => modeNodeIdSet.has(edge.source_id) && modeNodeIdSet.has(edge.target_id));

  if (modeNodes.length <= MAX_RENDER_NODES && filteredEdges.length <= MAX_RENDER_EDGES) {
    return { nodes: modeNodes, edges: filteredEdges };
  }

  const clueEvidenceIds = new Set(graph.value.clues.flatMap((clue) => clue.evidence_ids));
  const degree = new Map<string, number>();
  filteredEdges.forEach((edge) => {
    degree.set(edge.source_id, (degree.get(edge.source_id) || 0) + 1);
    degree.set(edge.target_id, (degree.get(edge.target_id) || 0) + 1);
  });

  const scoredNodes = modeNodes
    .map((node) => ({
      node,
      score:
        (node.type === 'evidence' ? 0 : 100) +
        (clueEvidenceIds.has(node.node_id) ? 80 : 0) +
        (degree.get(node.node_id) || 0),
    }))
    .sort((a, b) => b.score - a.score);

  const selectedIds = new Set(scoredNodes.slice(0, MAX_RENDER_NODES).map((item) => item.node.node_id));
  const nodes = modeNodes.filter((node) => selectedIds.has(node.node_id));
  const edges = filteredEdges
    .filter((edge) => selectedIds.has(edge.source_id) && selectedIds.has(edge.target_id))
    .sort((a, b) => Number(b.properties?.count || 1) - Number(a.properties?.count || 1))
    .slice(0, MAX_RENDER_EDGES);

  return { nodes, edges };
}

function modeNodeIds(nodes: GraphNode[], edges: GraphEdge[]) {
  const ids = new Set(nodes.map((node) => node.node_id));
  if (viewMode.value === 'all') return ids;

  const clueIds = clueRelatedNodeIds();
  if (viewMode.value === 'evidence') {
    const evidenceIds = new Set(
      nodes
        .filter((node) => node.type === 'evidence' || clueIds.has(node.node_id) || itemDate(node))
        .map((node) => node.node_id),
    );
    edges.forEach((edge) => {
      if (evidenceIds.has(edge.source_id) || evidenceIds.has(edge.target_id) || edge.evidence_ids.some((id) => clueIds.has(`doc:${id}`))) {
        evidenceIds.add(edge.source_id);
        evidenceIds.add(edge.target_id);
      }
    });
    return evidenceIds;
  }

  const degree = new Map<string, number>();
  edges.forEach((edge) => {
    degree.set(edge.source_id, (degree.get(edge.source_id) || 0) + 1);
    degree.set(edge.target_id, (degree.get(edge.target_id) || 0) + 1);
  });
  const seeds = nodes
    .filter((node) => node.type !== 'evidence' && node.type !== 'algorithm_provider')
    .sort((a, b) => (degree.get(b.node_id) || 0) - (degree.get(a.node_id) || 0))
    .slice(0, 6)
    .map((node) => node.node_id);
  const coreIds = new Set(seeds);
  edges.forEach((edge) => {
    if (coreIds.has(edge.source_id) || coreIds.has(edge.target_id)) {
      coreIds.add(edge.source_id);
      coreIds.add(edge.target_id);
    }
  });
  return coreIds.size ? coreIds : ids;
}

function syncTimelineAndTags() {
  const dates = new Set<string>();
  graph.value.nodes.forEach((node) => {
    const date = itemDate(node);
    if (date) dates.add(date);
  });
  graph.value.edges.forEach((edge) => {
    const date = itemDate(edge);
    if (date) dates.add(date);
  });
  const sortedDates = Array.from(dates).sort();
  timelinePoints.value = sortedDates.length ? sortedDates : ['全部时间'];
  timelineIndex.value = Math.max(timelinePoints.value.length - 1, 0);
  selectedCategories.value = availableCategories.value.map((item) => item.key);
}

function setViewMode(mode: 'core' | 'evidence' | 'all') {
  viewMode.value = mode;
  renderGraph();
}

async function setLayoutMode(mode: 'tree' | 'center' | 'circle' | 'force') {
  layoutMode.value = mode;
  graphRenderKey.value += 1;
  await nextTick();
  renderGraph();
}

function layoutConfig(mode: 'tree' | 'center' | 'circle' | 'force') {
  if (mode === 'tree') {
    return {
      label: 'tree',
      layoutName: 'tree',
      from: 'left',
      min_per_width: 220,
      max_per_width: 420,
      min_per_height: 42,
      max_per_height: 90,
    };
  }
  if (mode === 'circle') {
    return { label: 'circle', layoutName: 'circle' };
  }
  if (mode === 'force') {
    return {
      label: 'force',
      layoutName: 'force',
      maxLayoutTimes: 260,
      force_node_repulsion: 1.8,
      force_line_elastic: 0.6,
    };
  }
  return { label: 'center', layoutName: 'center', layoutDirection: 'v' };
}

function selectedByTags(item: GraphNode | GraphEdge, selected: Set<string>) {
  return itemTags(item).some((tag) => selected.has(tag));
}

function itemTags(item: GraphNode | GraphEdge) {
  if ('relation' in item) return edgeTags(item);
  return nodeTags(item);
}

function nodeTags(node: GraphNode) {
  const tags: string[] = [];
  if (node.type === 'algorithm_provider') tags.push('algorithm');
  if (node.type === 'confirmed_memory') tags.push('memory');
  if (node.type === 'transaction') tags.push('fund_account');
  if (node.type === 'evidence') tags.push(isBankItem(node) ? 'bank_flow_evidence' : 'case_evidence');
  if (looksLikeOrganization(node.label)) tags.push('organization');
  if (looksLikePerson(node.label)) tags.push('person');
  if (clueRelatedNodeIds().has(node.node_id)) tags.push('clue_related');
  if (itemDate(node)) tags.push('time_mapped');
  if (tags.length === 0) tags.push('other');
  return tags;
}

function edgeTags(edge: GraphEdge) {
  const tags: string[] = [];
  if (clueRelatedEdge(edge)) tags.push('clue_related');
  if (edge.properties?.count && Number(edge.properties.count) > 1) tags.push('repeated_relation');
  if (itemDate(edge)) tags.push('time_mapped');
  if (isFundEdge(edge)) tags.push('fund_flow');
  if (isDutyEdge(edge)) tags.push('duty_behavior');
  if (isSubjectiveEdge(edge)) tags.push('subjective_state');
  if (tags.length === 0) tags.push('other');
  return tags;
}

function clueRelatedNodeIds() {
  return new Set(graph.value.clues.flatMap((clue) => clue.evidence_ids.map((id) => `doc:${id}`)));
}

function clueRelatedEdge(edge: GraphEdge) {
  const clueIds = clueRelatedNodeIds();
  return edge.evidence_ids.some((id) => clueIds.has(`doc:${id}`));
}

function isBankItem(node: GraphNode) {
  const text = `${node.label} ${node.properties?.source_type || ''} ${node.properties?.preview || ''}`;
  return /流水|银行|微信|支付宝|交易|转账|收款|付款|csv|xlsx|bank|flow|transaction/i.test(text);
}

function isFundEdge(edge: GraphEdge) {
  const text = `${edge.relation} ${edge.properties?.amount_total || ''} ${edge.properties?.amount || ''}`;
  return /资金|交易|收入|支出|转账|收款|付款|金额|入|出|借|贷/.test(text);
}

function isDutyEdge(edge: GraphEdge) {
  return /职务|履职|办理|立案|拘留|释放|调解|审批|执法|调查|报告|决定/.test(edge.relation);
}

function isSubjectiveEdge(edge: GraphEdge) {
  return /明知|故意|徇私|隐瞒|放任|授意|串通|请托/.test(edge.relation);
}

function looksLikeOrganization(label: string) {
  return /公司|银行|委员会|派出所|公安|政府|法院|检察|中心|局|所|支行|集团|股份|科技/.test(label);
}

function looksLikePerson(label: string) {
  return /^[\u4e00-\u9fa5]{2,4}$/.test(label) && !looksLikeOrganization(label);
}

function addCount(map: Map<string, number>, key: string) {
  map.set(key, (map.get(key) || 0) + 1);
}

function itemDate(item: GraphNode | GraphEdge) {
  const properties = item.properties || {};
  const candidates = [
    properties.time,
    properties.date,
    properties.time_sample,
    properties.created_at,
    'label' in item ? item.label : '',
    'relation' in item ? item.relation : '',
    properties.preview,
  ];
  for (const value of candidates) {
    const parsed = normalizeDate(value);
    if (parsed) return parsed;
  }
  return null;
}

function normalizeDate(value: unknown) {
  if (value === null || value === undefined) return null;
  const text = String(value);
  const match = text.match(/(19|20)\d{2}[年/-]?\d{1,2}([月/-]?\d{1,2})?/);
  if (!match) return null;
  const parts = match[0].replace(/[年月]/g, '-').replace(/日/g, '').replace(/\//g, '-').split('-').filter(Boolean);
  const year = parts[0];
  const month = (parts[1] || '01').padStart(2, '0');
  const day = (parts[2] || '01').padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function categoryLabel(key: string) {
  const labels: Record<string, string> = {
    evidence: '证据文档',
    entity: '人物/主体',
    transaction: '资金/交易',
    algorithm_provider: '算法节点',
    confirmed_memory: '人工记忆',
  };
  return labels[key] || key;
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
  background: #ffffff;
  color: #0f172a;
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
.graph-stage {
  position: relative;
  background: #f8fafc;
  color: #0f172a;
}
.graph-view {
  width: 100%;
  height: 100%;
  background: #f8fafc;
}
.graph-view :deep(.relation-graph),
.graph-view :deep(.rel-map),
.graph-view :deep(.rel-map-canvas),
.graph-view :deep(.rel-map-background) {
  background: #f8fafc !important;
  color: #0f172a !important;
}
.graph-view :deep(.c-node-text),
.graph-view :deep(.c-node-name),
.graph-view :deep(.rel-node-text) {
  color: #0f172a !important;
  fill: #0f172a !important;
  font-weight: 800;
  text-shadow: 0 1px 0 #ffffff;
}
.graph-view :deep(.c-rg-line-text),
.graph-view :deep(.rel-line-text) {
  color: #334155 !important;
  fill: #334155 !important;
  paint-order: stroke;
  stroke: #ffffff;
  stroke-width: 3px;
}
.graph-note {
  position: absolute;
  left: 16px;
  top: 198px;
  max-width: 520px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.92);
  color: #334155;
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 700;
  pointer-events: none;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
}
.graph-controls {
  position: absolute;
  left: 16px;
  top: 16px;
  width: min(560px, calc(100% - 32px));
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.95);
  color: #0f172a;
  padding: 12px;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.1);
}
.control-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
  font-weight: 800;
}
.control-head strong {
  color: #0f766e;
}
.mode-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}
.mode-btn {
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #f8fafc;
  color: #334155;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 800;
}
.mode-btn.active {
  border-color: #0f766e;
  background: #ccfbf1;
  color: #115e59;
}
.mode-btn.layout.active {
  border-color: #2563eb;
  background: #dbeafe;
  color: #1e40af;
}
.timeline {
  width: 100%;
  margin: 10px 0;
  accent-color: #0f766e;
}
.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.tag-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  background: #ffffff;
  color: #334155;
  padding: 5px 9px;
  font-size: 12px;
  font-weight: 700;
}
.tag-item input {
  accent-color: #0f766e;
}
</style>
