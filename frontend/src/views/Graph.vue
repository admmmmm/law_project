<template>
  <div class="graph-page">
    <header class="topbar">
      <div>
        <h1>证据图谱</h1>
        <p>{{ activeCaseId || '未选择案件' }}</p>
      </div>
      <div class="top-actions">
        <button class="btn" :disabled="!activeCaseId || loading" @click="runAnalysis">重新分析</button>
        <button class="btn" :disabled="!activeCaseId || loading" @click="loadGraph">刷新图谱</button>
      </div>
    </header>

    <div v-if="error" class="error-box">{{ error }}</div>
    <AsyncProgressBar
      v-if="progress.active.value"
      compact
      :value="progress.value.value"
      :label="progress.label.value"
      :detail="progress.detail.value"
    />

    <main v-if="!activeCaseId" class="empty-state">
      <Network :size="54" />
      <strong>还没有选择案件</strong>
      <router-link to="/">回到白板工作台</router-link>
    </main>

    <main v-else class="graph-shell">
      <section class="stage">
        <div v-if="loading" class="empty-state">正在加载图谱...</div>
        <div v-else-if="graph.nodes.length === 0" class="empty-state">
          <Network :size="54" />
          <strong>图谱还是空的</strong>
          <span>先导入证据，再运行分析。</span>
        </div>
        <RelationGraph
          v-else
          :key="graphRenderKey"
          ref="graphRef"
          class="graph-view"
          :options="graphOptions"
          :on-node-click="onNodeClick"
          :on-line-click="onLineClick"
        />

        <div v-if="!loading && graph.nodes.length > 0" class="control-card">
          <div class="control-head">
            <span>时间轴添加证据</span>
            <strong>{{ currentTimelineLabel }}</strong>
          </div>

          <div class="segmented">
            <button
              v-for="item in viewModes"
              :key="item.key"
              :class="{ active: viewMode === item.key }"
              @click="setViewMode(item.key)"
            >
              {{ item.label }}
            </button>
          </div>

          <div class="segmented">
            <button
              v-for="item in layoutModes"
              :key="item.key"
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
            @input="renderTimelineGraph"
          />

          <div class="tag-list">
            <label v-for="item in availableCategories" :key="item.key" class="tag-pill">
              <input v-model="selectedCategories" type="checkbox" :value="item.key" @change="renderGraph" />
              <span>{{ item.label }} {{ item.count }}</span>
            </label>
          </div>
        </div>

        <div v-if="!loading && graph.nodes.length > 0" class="render-note">
          当前渲染 {{ renderedNodeCount }} / {{ graph.nodes.length }} 个节点，{{ renderedEdgeCount }} / {{ graph.edges.length }} 条关系
        </div>
      </section>

      <aside class="side-panel">
        <div class="stats">
          <div><span>节点</span><strong>{{ graph.nodes.length }}</strong></div>
          <div><span>关系</span><strong>{{ graph.edges.length }}</strong></div>
          <div><span>线索</span><strong>{{ graph.clues.length }}</strong></div>
        </div>

        <section class="panel">
          <h2>当前选择</h2>
          <div v-if="selectedKind" class="selected-box">
            <strong>{{ selectedTitle }}</strong>
            <p>{{ selectedSubtitle }}</p>
            <div class="selected-summary">
              <span v-for="tag in selectedTagsDisplay" :key="tag">{{ tag }}</span>
              <p>{{ selectedSummary }}</p>
              <small v-if="selectedEvidenceText">证据：{{ selectedEvidenceText }}</small>
            </div>
            <details>
              <summary>查看原始 JSON</summary>
              <pre>{{ selectedJson }}</pre>
            </details>
            <div class="row-actions">
              <button class="small-btn" @click="fillEditForm">载入编辑</button>
              <button class="small-btn danger" @click="deleteSelected">删除</button>
              <button class="small-btn" @click="verifySelected">标为已核</button>
            </div>
          </div>
          <p v-else class="muted">点击节点或关系查看详情。</p>
        </section>

        <section class="panel">
          <h2>图谱增删改查</h2>
          <div class="form-grid">
            <label>节点ID<input v-model="nodeForm.node_id" placeholder="node:manual:001" /></label>
            <label>节点名称<input v-model="nodeForm.label" placeholder="例如：王静控制账户" /></label>
            <label>节点类型<input v-model="nodeForm.type" placeholder="person / evidence / account" /></label>
            <button class="wide-btn" @click="upsertNode">新增/更新节点</button>
          </div>
          <div class="form-grid mt">
            <label>源节点<input v-model="edgeForm.source_id" placeholder="source node_id" /></label>
            <label>目标节点<input v-model="edgeForm.target_id" placeholder="target node_id" /></label>
            <label>关系<input v-model="edgeForm.relation" placeholder="控制 / 转账 / 通话" /></label>
            <button class="wide-btn" @click="upsertEdge">新增/更新关系</button>
          </div>
        </section>

        <section class="panel">
          <h2>要件核查</h2>
          <div v-for="item in elementChecks" :key="item.key" class="check-item">
            <div>
              <strong>{{ item.title }}</strong>
              <p>{{ item.description }}</p>
            </div>
            <span :class="['status', item.status]">{{ item.label }}</span>
          </div>
        </section>

        <section class="panel">
          <h2>关联路径推荐</h2>
          <div v-for="path in recommendedPaths" :key="path.title" class="path-card">
            <strong>{{ path.title }}</strong>
            <p>{{ path.reason }}</p>
            <span>{{ path.count }} 条候选关系</span>
          </div>
        </section>

        <section class="panel">
          <h2>别名/假名合并建议</h2>
          <div v-if="aliasSuggestions.length === 0" class="muted">暂无明显别名合并建议。</div>
          <div v-for="item in aliasSuggestions" :key="item.title" class="path-card">
            <strong>{{ item.title }}</strong>
            <p>{{ item.reason }}</p>
            <span>{{ item.level }}</span>
          </div>
        </section>

        <section class="panel">
          <h2>风险线索</h2>
          <div v-if="graph.clues.length === 0" class="muted">暂无线索。</div>
          <div v-for="clue in graph.clues" :key="clue.clue_id" class="clue-card">
            <strong>{{ clue.title }}</strong>
            <span>{{ clue.category }} / {{ clue.risk_level }}</span>
            <p>{{ clue.description }}</p>
          </div>
        </section>
      </aside>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue';
import RelationGraph from 'relation-graph/vue3';
import { Network } from 'lucide-vue-next';
import { backendApi, type GraphEdge, type GraphNode, type InvestigationGraph } from '../api/backend';
import AsyncProgressBar from '../components/AsyncProgressBar.vue';
import { useSimulatedProgress } from '../composables/useSimulatedProgress';

type LayoutMode = 'tree' | 'center' | 'circle' | 'force';
type ViewMode = 'core' | 'evidence' | 'all';

const activeCaseId = ref(localStorage.getItem('active_case_id') || '');
const loading = ref(false);
const error = ref('');
const progress = useSimulatedProgress();
const graphRef = ref<any>(null);
const graphRenderKey = ref(0);
const graph = ref<InvestigationGraph>({ case_id: activeCaseId.value, nodes: [], edges: [], clues: [] });
const selectedKind = ref<'node' | 'edge' | ''>('');
const selectedNode = ref<GraphNode | null>(null);
const selectedEdge = ref<GraphEdge | null>(null);
const renderedNodeCount = ref(0);
const renderedEdgeCount = ref(0);
const timelineIndex = ref(0);
const timelinePoints = ref<string[]>(['全部时间']);
const selectedCategories = ref<string[]>([]);
const viewMode = ref<ViewMode>('core');
const layoutMode = ref<LayoutMode>('center');
const MAX_RENDER_NODES = 220;
const MAX_RENDER_EDGES = 420;

const nodeForm = reactive<GraphNode>({
  node_id: '',
  label: '',
  type: 'manual',
  properties: {},
  evidence_ids: [],
  manually_verified: true,
});

const edgeForm = reactive<GraphEdge>({
  edge_id: '',
  source_id: '',
  target_id: '',
  relation: '',
  confidence: 0.8,
  properties: {},
  evidence_ids: [],
  manually_verified: true,
});

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
  { key: 'evidence', label: '证据文档' },
  { key: 'person', label: '人物' },
  { key: 'organization', label: '机构/公司' },
  { key: 'account', label: '账户/资金对象' },
  { key: 'bank_flow', label: '资金流水' },
  { key: 'call_record', label: '通话/短信' },
  { key: 'law_document', label: '执法文书' },
  { key: 'duty_behavior', label: '职务行为' },
  { key: 'subjective_state', label: '主观状态' },
  { key: 'alias_candidate', label: '别名候选' },
  { key: 'time_mapped', label: '有时间映射' },
  { key: 'clue_related', label: '线索相关' },
  { key: 'manual', label: '人工添加' },
  { key: 'algorithm', label: '算法节点' },
  { key: 'other', label: '其他' },
];

const graphOptions = {
  debug: false,
  allowShowZoomMenu: true,
  allowShowFullscreenMenu: true,
  allowAutoLayoutIfSupport: true,
  defaultNodeShape: 0,
  defaultLineShape: 6,
  defaultJunctionPoint: 'border',
  defaultNodeWidth: 76,
  defaultNodeHeight: 76,
  defaultLineColor: '#64748b',
  defaultLineWidth: 1.4,
  defaultShowLineLabel: true,
  defaultNodeFontColor: '#0f172a',
  defaultLineFontColor: '#334155',
  backgroundColor: '#f8fafc',
  layouts: [layoutConfig('center')],
};

const nodeMap = computed(() => new Map(graph.value.nodes.map((node) => [node.node_id, node])));
const currentTimelineLabel = computed(() => timelinePoints.value[timelineIndex.value] || '全部时间');
const selectedTitle = computed(() => selectedNode.value?.label || selectedEdge.value?.relation || '');
const selectedSubtitle = computed(() => {
  if (selectedNode.value) return `${selectedNode.value.type} / ${selectedNode.value.node_id}`;
  if (!selectedEdge.value) return '';
  const source = nodeMap.value.get(selectedEdge.value.source_id)?.label || selectedEdge.value.source_id;
  const target = nodeMap.value.get(selectedEdge.value.target_id)?.label || selectedEdge.value.target_id;
  return `${source} -> ${target}`;
});
const selectedJson = computed(() => JSON.stringify(selectedNode.value || selectedEdge.value || {}, null, 2));
const selectedTagsDisplay = computed(() => {
  const item = selectedNode.value || selectedEdge.value;
  if (!item) return [];
  return itemTags(item).map((tag) => FILTER_TAGS.find((entry) => entry.key === tag)?.label || tag);
});
const selectedEvidenceText = computed(() => {
  const ids = (selectedNode.value || selectedEdge.value)?.evidence_ids || [];
  return ids.slice(0, 4).join('，');
});
const selectedSummary = computed(() => {
  if (selectedNode.value) {
    const node = selectedNode.value;
    const props = node.properties || {};
    const preview = String(props.preview || props.passage || '').trim();
    return preview || `节点类型：${node.type}。关联证据 ${node.evidence_ids.length} 份。`;
  }
  if (selectedEdge.value) {
    const edge = selectedEdge.value;
    const source = nodeMap.value.get(edge.source_id)?.label || edge.source_id;
    const target = nodeMap.value.get(edge.target_id)?.label || edge.target_id;
    const count = edge.properties?.count ? `，出现 ${edge.properties.count} 次` : '';
    const amount = edge.properties?.amount_total ? `，金额合计 ${edge.properties.amount_total}` : '';
    return `${source} -> ${edge.relation} -> ${target}${count}${amount}。关联证据 ${edge.evidence_ids.length} 份。`;
  }
  return '';
});

const availableCategories = computed(() => {
  const counts = new Map<string, number>();
  graph.value.nodes.forEach((node) => itemTags(node).forEach((tag) => addCount(counts, tag)));
  graph.value.edges.forEach((edge) => itemTags(edge).forEach((tag) => addCount(counts, tag)));
  return FILTER_TAGS.filter((item) => counts.has(item.key)).map((item) => ({ ...item, count: counts.get(item.key) || 0 }));
});

const elementChecks = computed(() => {
  const nodes = graph.value.nodes;
  const edges = graph.value.edges;
  return [
    makeCheck('主体要件', '司法工作人员身份、职务权限、经办范围。', nodes.some((node) => /杨周武|派出所|公安|司法|检察|法院/.test(node.label))),
    makeCheck('客观行为', '立案、拘留、调解、撤案、释放等处置链条。', edges.some(isDutyEdge) || nodes.some((node) => /立案|拘留|释放|撤销|调解|报告/.test(node.label))),
    makeCheck('主观方面', '明知、徇私动机、请托、利益输送。', edges.some(isSubjectiveEdge) || graph.value.clues.some((clue) => /主观|明知|徇私|动机/.test(clue.title + clue.description))),
    makeCheck('证据关联', '证据是否能回到要件和图谱路径。', edges.some((edge) => edge.evidence_ids.length > 0) || nodes.some((node) => node.evidence_ids.length > 0)),
  ];
});

const recommendedPaths = computed(() => [
  {
    title: '资金流与执法处置交叉路径',
    reason: '优先看请托人、过桥账户、目标人员控制账户与撤案/释放/调解节点是否前后呼应。',
    count: graph.value.edges.filter((edge) => isFundEdge(edge) || isDutyEdge(edge)).length,
  },
  {
    title: '通话联系与文书变更路径',
    reason: '优先看关键处置前后通话、短信、询问笔录与文书时间是否能互相印证。',
    count: graph.value.edges.filter((edge) => itemTags(edge).includes('call_record') || isDutyEdge(edge)).length,
  },
  {
    title: '别名账户到真人路径',
    reason: '优先看同账号、同手机号、同设备、现金取存闭环与证人陈述中的控制关系。',
    count: aliasSuggestions.value.length,
  },
]);

const aliasSuggestions = computed(() => {
  const suggestions: Array<{ title: string; reason: string; level: string }> = [];
  const accountNodes = graph.value.nodes.filter((node) => itemTags(node).includes('account') || /账户|银行卡|微信|支付宝|控制/.test(node.label));
  accountNodes.slice(0, 8).forEach((node) => {
    const related = graph.value.edges.filter((edge) => edge.source_id === node.node_id || edge.target_id === node.node_id);
    if (related.length >= 2 || /控制|马甲|假名|别名|曾用|代持/.test(node.label + JSON.stringify(node.properties))) {
      suggestions.push({
        title: `${node.label} 可能需要身份合并复核`,
        reason: `该对象关联 ${related.length} 条关系。若同时出现实名账号、手机号、证言或资金闭环，应进入人工确认。`,
        level: related.length >= 4 ? '高置信建议' : '低置信线索',
      });
    }
  });
  return suggestions;
});

onMounted(loadGraph);

async function loadGraph() {
  if (!activeCaseId.value) return;
  await withGraphLoading(
    async () => {
      graph.value = await backendApi.getGraph(activeCaseId.value);
      syncTimelineAndTags(true);
    },
    {
      label: '正在加载图谱',
      detail: '读取案件节点、关系和线索数据',
      successLabel: '图谱已刷新',
    },
  );
  await nextTick();
  renderGraph();
}

async function runAnalysis() {
  if (!activeCaseId.value) return;
  await withGraphLoading(
    async () => {
      await backendApi.runAnalysis(activeCaseId.value);
      graph.value = await backendApi.getGraph(activeCaseId.value);
      syncTimelineAndTags();
    },
    {
      label: '正在重新分析案件',
      detail: '后端正在重建图谱、线索和时间轴视图',
      successLabel: '图谱分析已完成',
    },
  );
  await nextTick();
  renderGraph();
}

async function withGraphLoading(
  task: () => Promise<void>,
  options: {
    label: string;
    detail?: string;
    successLabel?: string;
  },
) {
  loading.value = true;
  error.value = '';
  progress.start({
    label: options.label,
    detail: options.detail,
  });
  try {
    await task();
    await progress.finish({
      label: options.successLabel || `${options.label}完成`,
      detail: '图谱界面已同步刷新',
    });
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
    progress.fail();
  } finally {
    loading.value = false;
  }
}

function renderGraph() {
  if (!graphRef.value || graph.value.nodes.length === 0) return;
  graphOptions.layouts = [layoutConfig(layoutMode.value)];
  const visible = buildRenderableGraph();
  renderedNodeCount.value = visible.nodes.length;
  renderedEdgeCount.value = visible.edges.length;
  const positioned = layoutMode.value === 'tree' ? visible.nodes : applySpreadPositions(visible.nodes, visible.edges, layoutMode.value);
  const jsonData = {
    rootId: pickRootId(positioned, visible.edges),
    nodes: positioned.map(toRelationNode),
    lines: visible.edges.map(toRelationLine),
  };
  graphRef.value.setOptions(graphOptions, true);
  graphRef.value.setJsonData(jsonData, (instance: any) => {
    if (layoutMode.value === 'tree') instance.doLayout();
    instance.moveToCenter();
    instance.zoomToFit();
  });
}

async function renderTimelineGraph() {
  graphRenderKey.value += 1;
  await nextTick();
  renderGraph();
}

function buildRenderableGraph() {
  const categorySet = new Set(selectedCategories.value);
  const cutoff = timelinePoints.value[timelineIndex.value] || '';
  const hasCutoff = Boolean(cutoff && cutoff !== '全部时间');
  const allowedByTime = (value: string | null) => !hasCutoff || Boolean(value && value <= cutoff);
  const datedNodeIds = new Set(graph.value.nodes.filter((node) => allowedByTime(itemDate(node))).map((node) => node.node_id));
  const timeEdges = graph.value.edges.filter((edge) => {
    const edgeDateAllowed = allowedByTime(itemDate(edge));
    if (!edgeDateAllowed) return false;
    datedNodeIds.add(edge.source_id);
    datedNodeIds.add(edge.target_id);
    return true;
  });
  const timeNodes = graph.value.nodes.filter((node) => datedNodeIds.has(node.node_id));
  const directNodeIds = new Set(timeNodes.filter((node) => selectedByTags(node, categorySet)).map((node) => node.node_id));
  const directEdgeIds = new Set(timeEdges.filter((edge) => selectedByTags(edge, categorySet)).map((edge) => edge.edge_id));
  const includedNodeIds = new Set(directNodeIds);
  timeEdges.forEach((edge) => {
    if (directEdgeIds.has(edge.edge_id)) {
      includedNodeIds.add(edge.source_id);
      includedNodeIds.add(edge.target_id);
    }
  });
  const filteredNodes = timeNodes.filter((node) => includedNodeIds.has(node.node_id));
  let filteredEdges = timeEdges.filter(
    (edge) =>
      directEdgeIds.has(edge.edge_id) ||
      (includedNodeIds.has(edge.source_id) && includedNodeIds.has(edge.target_id) && (directNodeIds.has(edge.source_id) || directNodeIds.has(edge.target_id))),
  );

  const modeIds = modeNodeIds(filteredNodes, filteredEdges);
  const modeNodes = filteredNodes.filter((node) => modeIds.has(node.node_id));
  const modeNodeIdsSet = new Set(modeNodes.map((node) => node.node_id));
  filteredEdges = filteredEdges.filter((edge) => modeNodeIdsSet.has(edge.source_id) && modeNodeIdsSet.has(edge.target_id));

  if (modeNodes.length <= MAX_RENDER_NODES && filteredEdges.length <= MAX_RENDER_EDGES) {
    return { nodes: modeNodes, edges: filteredEdges };
  }

  const degree = new Map<string, number>();
  filteredEdges.forEach((edge) => {
    degree.set(edge.source_id, (degree.get(edge.source_id) || 0) + 1);
    degree.set(edge.target_id, (degree.get(edge.target_id) || 0) + 1);
  });
  const clueIds = clueRelatedNodeIds();
  const selectedIds = new Set(
    modeNodes
      .map((node) => ({ node, score: (degree.get(node.node_id) || 0) + (clueIds.has(node.node_id) ? 80 : 0) + (node.type === 'evidence' ? 10 : 30) }))
      .sort((a, b) => b.score - a.score)
      .slice(0, MAX_RENDER_NODES)
      .map((item) => item.node.node_id),
  );
  return {
    nodes: modeNodes.filter((node) => selectedIds.has(node.node_id)),
    edges: filteredEdges
      .filter((edge) => selectedIds.has(edge.source_id) && selectedIds.has(edge.target_id))
      .sort((a, b) => Number(b.properties?.count || 1) - Number(a.properties?.count || 1))
      .slice(0, MAX_RENDER_EDGES),
  };
}

function modeNodeIds(nodes: GraphNode[], edges: GraphEdge[]) {
  const ids = new Set(nodes.map((node) => node.node_id));
  if (viewMode.value === 'all') return ids;
  if (viewMode.value === 'evidence') {
    const evidenceIds = new Set(nodes.filter((node) => node.type === 'evidence' || itemDate(node)).map((node) => node.node_id));
    edges.forEach((edge) => {
      if (evidenceIds.has(edge.source_id) || evidenceIds.has(edge.target_id)) {
        evidenceIds.add(edge.source_id);
        evidenceIds.add(edge.target_id);
      }
    });
    return evidenceIds.size ? evidenceIds : ids;
  }

  const degree = new Map<string, number>();
  edges.forEach((edge) => {
    degree.set(edge.source_id, (degree.get(edge.source_id) || 0) + 1);
    degree.set(edge.target_id, (degree.get(edge.target_id) || 0) + 1);
  });
  const seeds = nodes
    .filter((node) => node.type !== 'evidence' && node.type !== 'algorithm_provider')
    .sort((a, b) => (degree.get(b.node_id) || 0) - (degree.get(a.node_id) || 0))
    .slice(0, 8)
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

function syncTimelineAndTags(resetControls = true) {
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
  if (resetControls) {
    timelineIndex.value = Math.max(timelinePoints.value.length - 1, 0);
    selectedCategories.value = availableCategories.value.map((item) => item.key);
  }
}

function setViewMode(mode: ViewMode) {
  viewMode.value = mode;
  renderGraph();
}

async function setLayoutMode(mode: LayoutMode) {
  layoutMode.value = mode;
  graphRenderKey.value += 1;
  await nextTick();
  renderGraph();
}

function layoutConfig(mode: LayoutMode) {
  if (mode === 'tree') return { layoutName: 'tree', from: 'left', min_per_width: 180, max_per_width: 360, min_per_height: 56 };
  if (mode === 'force') return { layoutName: 'force', maxLayoutTimes: 900, force_node_repulsion: 8, force_line_elastic: 0.18 };
  return { layoutName: 'center', distance_coefficient: mode === 'circle' ? 1.4 : 1.0 };
}

function applySpreadPositions(nodes: GraphNode[], edges: GraphEdge[], mode: LayoutMode) {
  const degree = new Map<string, number>();
  edges.forEach((edge) => {
    degree.set(edge.source_id, (degree.get(edge.source_id) || 0) + 1);
    degree.set(edge.target_id, (degree.get(edge.target_id) || 0) + 1);
  });
  const ordered = [...nodes].sort((a, b) => (degree.get(b.node_id) || 0) - (degree.get(a.node_id) || 0));
  const center = ordered[0];
  const rest = ordered.slice(1);
  const minGap = mode === 'force' ? 170 : 145;
  const ringSize = Math.max(10, Math.ceil(Math.sqrt(Math.max(rest.length, 1)) * 4));
  return nodes.map((node) => {
    if (center && node.node_id === center.node_id) {
      return { ...node, properties: { ...node.properties, x: 0, y: 0, fixed: true } };
    }
    const rank = Math.max(rest.findIndex((item) => item.node_id === node.node_id), 0);
    const ring = Math.floor(rank / ringSize) + 1;
    const indexInRing = rank % ringSize;
    const itemsInRing = Math.min(ringSize, rest.length - (ring - 1) * ringSize);
    const angle = (indexInRing / Math.max(itemsInRing, 1)) * Math.PI * 2 + ring * 0.23;
    const radius = mode === 'circle' ? Math.max(260, rest.length * 15) : 180 + ring * minGap;
    return {
      ...node,
      properties: {
        ...node.properties,
        x: Math.round(Math.cos(angle) * radius),
        y: Math.round(Math.sin(angle) * radius),
        fixed: true,
      },
    };
  });
}

function pickRootId(nodes: GraphNode[], edges: GraphEdge[]) {
  const degree = new Map<string, number>();
  edges.forEach((edge) => {
    degree.set(edge.source_id, (degree.get(edge.source_id) || 0) + 1);
    degree.set(edge.target_id, (degree.get(edge.target_id) || 0) + 1);
  });
  return [...nodes].sort((a, b) => (degree.get(b.node_id) || 0) - (degree.get(a.node_id) || 0))[0]?.node_id;
}

async function upsertNode() {
  if (!activeCaseId.value || !nodeForm.label.trim()) return;
  const node: GraphNode = {
    ...nodeForm,
    node_id: nodeForm.node_id.trim() || `manual:node:${Date.now()}`,
    label: nodeForm.label.trim(),
    type: nodeForm.type.trim() || 'manual',
    manually_verified: true,
  };
  graph.value = await backendApi.applyGraphIntervention(activeCaseId.value, { action: 'upsert_node', node, reason: '人工维护图谱节点' });
  syncTimelineAndTags();
  await nextTick();
  renderGraph();
}

async function upsertEdge() {
  if (!activeCaseId.value || !edgeForm.source_id || !edgeForm.target_id || !edgeForm.relation.trim()) return;
  const edge: GraphEdge = {
    ...edgeForm,
    edge_id: edgeForm.edge_id || `manual:edge:${Date.now()}`,
    relation: edgeForm.relation.trim(),
    confidence: 0.85,
    manually_verified: true,
  };
  graph.value = await backendApi.applyGraphIntervention(activeCaseId.value, { action: 'upsert_edge', edge, reason: '人工维护图谱关系' });
  syncTimelineAndTags();
  await nextTick();
  renderGraph();
}

async function deleteSelected() {
  if (!activeCaseId.value || !selectedKind.value) return;
  const targetId = selectedNode.value?.node_id || selectedEdge.value?.edge_id;
  if (!targetId) return;
  graph.value = await backendApi.applyGraphIntervention(activeCaseId.value, {
    action: selectedKind.value === 'node' ? 'delete_node' : 'delete_edge',
    target_id: targetId,
    reason: '人工删除图谱项',
  });
  selectedKind.value = '';
  selectedNode.value = null;
  selectedEdge.value = null;
  syncTimelineAndTags();
  await nextTick();
  renderGraph();
}

async function verifySelected() {
  if (!activeCaseId.value || !selectedKind.value) return;
  const targetId = selectedNode.value?.node_id || selectedEdge.value?.edge_id;
  if (!targetId) return;
  graph.value = await backendApi.applyGraphIntervention(activeCaseId.value, {
    action: selectedKind.value === 'node' ? 'verify_node' : 'verify_edge',
    target_id: targetId,
    reason: '人工核验',
  });
  await nextTick();
  renderGraph();
}

function fillEditForm() {
  if (selectedNode.value) Object.assign(nodeForm, selectedNode.value);
  if (selectedEdge.value) Object.assign(edgeForm, selectedEdge.value);
}

function selectedByTags(item: GraphNode | GraphEdge, selected: Set<string>) {
  if (selected.size === 0) return false;
  return itemTags(item).some((tag) => selected.has(tag));
}

function itemTags(item: GraphNode | GraphEdge) {
  return 'relation' in item ? edgeTags(item) : nodeTags(item);
}

function nodeTags(node: GraphNode) {
  const text = `${node.label} ${node.type} ${JSON.stringify(node.properties || {})}`;
  const tags: string[] = [];
  if (node.type === 'evidence') tags.push('evidence');
  if (node.type === 'algorithm_provider') tags.push('algorithm');
  if (node.manually_verified || node.type === 'manual') tags.push('manual');
  if (/账户|银行卡|微信|支付宝|资金|现金|交易|流水|bank|account/i.test(text)) tags.push('account', 'bank_flow');
  if (/电话|通话|短信|微信聊天|call|sms/i.test(text)) tags.push('call_record');
  if (/立案|拘留|释放|撤销|调解|报告|笔录|鉴定|文书|决定|通知/.test(text)) tags.push('law_document');
  if (/别名|假名|马甲|曾用|控制账户|代持/.test(text)) tags.push('alias_candidate');
  if (looksLikeOrganization(node.label)) tags.push('organization');
  if (looksLikePerson(node.label)) tags.push('person');
  if (clueRelatedNodeIds().has(node.node_id)) tags.push('clue_related');
  if (itemDate(node)) tags.push('time_mapped');
  if (tags.length === 0) tags.push('other');
  return [...new Set(tags)];
}

function edgeTags(edge: GraphEdge) {
  const text = `${edge.relation} ${JSON.stringify(edge.properties || {})}`;
  const tags: string[] = [];
  if (isFundEdge(edge)) tags.push('bank_flow');
  if (/电话|通话|短信|联系|微信/.test(text)) tags.push('call_record');
  if (isDutyEdge(edge)) tags.push('duty_behavior', 'law_document');
  if (isSubjectiveEdge(edge)) tags.push('subjective_state');
  if (/别名|假名|控制|代持|同一|马甲/.test(text)) tags.push('alias_candidate');
  if (edge.manually_verified) tags.push('manual');
  if (clueRelatedEdge(edge)) tags.push('clue_related');
  if (itemDate(edge)) tags.push('time_mapped');
  if (tags.length === 0) tags.push('other');
  return [...new Set(tags)];
}

function clueRelatedNodeIds() {
  return new Set(graph.value.clues.flatMap((clue) => clue.evidence_ids.map((id) => `doc:${id}`)));
}

function clueRelatedEdge(edge: GraphEdge) {
  const clueIds = clueRelatedNodeIds();
  return edge.evidence_ids.some((id) => clueIds.has(`doc:${id}`));
}

function isFundEdge(edge: GraphEdge) {
  const text = `${edge.relation} ${JSON.stringify(edge.properties || {})}`;
  return /资金|交易|转账|收款|付款|金额|现金|ATM|取现|存入|入账|支出|收入|流水|bank|flow/i.test(text);
}

function isDutyEdge(edge: GraphEdge) {
  return /职务|履职|办理|立案|拘留|释放|调解|撤销|审批|执法|调查|报告|决定|通知|处置|包庇|追诉/.test(edge.relation);
}

function isSubjectiveEdge(edge: GraphEdge) {
  return /明知|故意|徇私|隐瞒|放任|授意|串通|请托|动机|徇私枉法/.test(edge.relation);
}

function looksLikeOrganization(label: string) {
  return /公司|银行|委员会|派出所|公安|政府|法院|检察|中心|医院|分局|支行|集团|股份|科技|办公室/.test(label);
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

function toRelationNode(node: GraphNode) {
  const isEvidence = node.type === 'evidence';
  const isImportant = itemTags(node).some((tag) => ['person', 'account', 'alias_candidate'].includes(tag));
  return {
    id: node.node_id,
    text: isEvidence ? evidenceNodeText(node) : trim(node.label, 10),
    data: node,
    type: node.type,
    color: nodeColor(node),
    borderColor: nodeBorderColor(node),
    borderWidth: isImportant ? 3 : 2,
    fontColor: '#0f172a',
    width: isEvidence ? 138 : 82,
    height: isEvidence ? 70 : 82,
    nodeShape: isEvidence ? 1 : 0,
    x: typeof node.properties?.x === 'number' ? node.properties.x : undefined,
    y: typeof node.properties?.y === 'number' ? node.properties.y : undefined,
    fixed: Boolean(node.properties?.fixed),
  };
}

function toRelationLine(edge: GraphEdge) {
  const count = edge.properties?.count ? ` x${edge.properties.count}` : '';
  const amount = edge.properties?.amount_total ? ` ￥${edge.properties.amount_total}` : '';
  return {
    id: edge.edge_id,
    from: edge.source_id,
    to: edge.target_id,
    text: trim(`${edge.relation}${count}${amount}`, 24),
    data: edge,
    color: edgeColor(edge),
    lineWidth: edge.properties?.count && Number(edge.properties.count) > 1 ? 2.4 : 1.3,
  };
}

function onNodeClick(node: { data?: GraphNode }) {
  if (!node.data) return;
  selectedKind.value = 'node';
  selectedNode.value = node.data;
  selectedEdge.value = null;
}

function evidenceNodeText(node: GraphNode) {
  const code = evidenceCode(node.label) || evidenceCode(node.node_id) || '证据';
  const title = evidenceShortTitle(node.label, node.properties?.preview);
  return title ? `${code}\n${title}` : code;
}

function evidenceCode(value: unknown) {
  const match = String(value || '').match(/证据\s*\d+(?:-\d+)?/);
  return match ? match[0].replace(/\s+/g, '') : '';
}

function evidenceShortTitle(label: string, preview: unknown) {
  const source = `${label}\n${String(preview || '')}`;
  const withoutExt = source.replace(/\.(md|docx?|pdf|txt)$/i, '');
  const title = withoutExt
    .replace(/^证据\s*\d+(?:-\d+)?[_\s-]*/, '')
    .split(/\n|：|:/)
    .map((item) => item.trim())
    .find((item) => item && !/^证据\s*\d+(?:-\d+)?$/.test(item));
  if (!title) return '';
  return trim(title.replace(/[《》（）()]/g, ''), 12);
}

function onLineClick(line: { data?: GraphEdge }) {
  if (!line.data) return;
  selectedKind.value = 'edge';
  selectedEdge.value = line.data;
  selectedNode.value = null;
}

function nodeColor(node: GraphNode) {
  if (node.type === 'evidence') return '#dff7f3';
  if (itemTags(node).includes('account')) return '#dbeafe';
  if (itemTags(node).includes('person')) return '#fee2e2';
  return '#f8fafc';
}

function nodeBorderColor(node: GraphNode) {
  if (itemTags(node).includes('alias_candidate')) return '#f59e0b';
  if (node.type === 'evidence') return '#0f766e';
  if (itemTags(node).includes('account')) return '#2563eb';
  if (itemTags(node).includes('person')) return '#dc2626';
  return '#64748b';
}

function edgeColor(edge: GraphEdge) {
  if (isFundEdge(edge)) return '#2563eb';
  if (isSubjectiveEdge(edge)) return '#dc2626';
  if (isDutyEdge(edge)) return '#0f766e';
  return '#64748b';
}

function trim(text: string, length: number) {
  return text.length > length ? `${text.slice(0, length)}...` : text;
}

function makeCheck(title: string, description: string, passed: boolean) {
  return { key: title, title, description, status: passed ? 'ok' : 'gap', label: passed ? '已有支撑' : '待补强' };
}
</script>

<style scoped>
.graph-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #eef3f7;
  color: #0f172a;
}
.topbar {
  height: 64px;
  flex-shrink: 0;
  background: #ffffff;
  border-bottom: 1px solid #d8e1ea;
  padding: 0 22px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.topbar h1 {
  font-size: 18px;
  font-weight: 900;
}
.topbar p {
  margin-top: 2px;
  color: #64748b;
  font-size: 12px;
}
.top-actions {
  display: flex;
  gap: 8px;
}
.btn,
.small-btn,
.wide-btn {
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #0f172a;
  border-radius: 7px;
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 800;
}
.btn:disabled {
  opacity: 0.45;
}
.small-btn {
  padding: 6px 9px;
  font-size: 12px;
}
.small-btn.danger {
  border-color: #fecaca;
  color: #b91c1c;
}
.wide-btn {
  width: 100%;
  background: #0f766e;
  color: #ffffff;
  border-color: #0f766e;
}
.error-box {
  margin: 12px;
  padding: 10px 12px;
  border: 1px solid #fecdd3;
  background: #fff1f2;
  color: #be123c;
  border-radius: 8px;
}
.graph-shell {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 380px;
}
.stage {
  position: relative;
  min-height: 0;
  background:
    radial-gradient(circle at 20% 20%, rgba(15, 118, 110, 0.08), transparent 28%),
    radial-gradient(circle at 80% 60%, rgba(37, 99, 235, 0.08), transparent 24%),
    #f8fafc;
}
.graph-view {
  width: 100%;
  height: 100%;
}
.empty-state {
  height: 100%;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 10px;
  color: #64748b;
  text-align: center;
}
.empty-state strong {
  color: #334155;
}
.empty-state a {
  color: #0f766e;
  font-weight: 800;
}
.control-card {
  position: absolute;
  left: 16px;
  top: 16px;
  width: min(620px, calc(100% - 32px));
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.96);
  padding: 12px;
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.12);
}
.control-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
  font-weight: 900;
}
.control-head strong {
  color: #0f766e;
}
.segmented {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}
.segmented button {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #f8fafc;
  color: #334155;
  padding: 7px 11px;
  font-size: 12px;
  font-weight: 900;
}
.segmented button.active {
  border-color: #0f766e;
  background: #ccfbf1;
  color: #115e59;
}
.timeline {
  width: 100%;
  margin: 12px 0;
  accent-color: #0f766e;
}
.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.tag-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  background: #ffffff;
  color: #334155;
  padding: 5px 9px;
  font-size: 12px;
  font-weight: 800;
}
.tag-pill input {
  accent-color: #0f766e;
}
.render-note {
  position: absolute;
  left: 16px;
  bottom: 16px;
  max-width: 420px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.94);
  color: #334155;
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 800;
  pointer-events: none;
}
.side-panel {
  background: #0f172a;
  color: #ffffff;
  overflow: auto;
  padding: 14px;
  border-left: 1px solid #1e293b;
}
.stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}
.stats div,
.panel {
  background: #111c31;
  border: 1px solid #23324b;
  border-radius: 9px;
}
.stats div {
  padding: 10px;
}
.stats span {
  display: block;
  color: #94a3b8;
  font-size: 12px;
}
.stats strong {
  font-size: 24px;
  color: #ffffff;
}
.panel {
  padding: 13px;
  margin-bottom: 12px;
}
.panel h2 {
  font-size: 15px;
  font-weight: 900;
  margin-bottom: 10px;
}
.muted {
  color: #94a3b8;
  font-size: 13px;
  line-height: 1.6;
}
.selected-box strong,
.path-card strong,
.clue-card strong,
.check-item strong {
  display: block;
  color: #ffffff;
  font-size: 13px;
}
.selected-box p,
.path-card p,
.clue-card p,
.check-item p {
  color: #a8b5c9;
  font-size: 12px;
  line-height: 1.55;
  margin-top: 5px;
}
.selected-box pre {
  max-height: 180px;
  overflow: auto;
  margin: 8px 0;
  padding: 8px;
  border-radius: 7px;
  background: #0b1220;
  color: #cbd5e1;
  font-size: 11px;
  white-space: pre-wrap;
}
.selected-box details {
  margin: 8px 0;
}
.selected-box summary {
  cursor: pointer;
  color: #7dd3fc;
  font-size: 12px;
  font-weight: 800;
}
.selected-summary {
  margin-top: 8px;
  border: 1px solid #23324b;
  border-radius: 8px;
  background: #0b1220;
  padding: 8px;
}
.selected-summary span {
  display: inline-block;
  margin: 0 5px 5px 0;
  border-radius: 999px;
  background: #134e4a;
  color: #99f6e4;
  padding: 3px 7px;
  font-size: 11px;
  font-weight: 900;
}
.selected-summary small {
  display: block;
  margin-top: 6px;
  color: #7dd3fc;
  font-size: 11px;
  line-height: 1.5;
}
.row-actions {
  display: flex;
  gap: 8px;
}
.form-grid {
  display: grid;
  gap: 8px;
}
.form-grid.mt {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #23324b;
}
.form-grid label {
  display: grid;
  gap: 4px;
  color: #94a3b8;
  font-size: 12px;
  font-weight: 800;
}
.form-grid input {
  border: 1px solid #334155;
  border-radius: 7px;
  background: #0b1220;
  color: #ffffff;
  padding: 7px 8px;
}
.check-item {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  align-items: start;
  padding: 9px 0;
  border-top: 1px solid #23324b;
}
.check-item:first-of-type {
  border-top: 0;
}
.status {
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 11px;
  font-weight: 900;
  white-space: nowrap;
}
.status.ok {
  background: #134e4a;
  color: #99f6e4;
}
.status.gap {
  background: #451a03;
  color: #fdba74;
}
.path-card,
.clue-card {
  padding: 10px 0;
  border-top: 1px solid #23324b;
}
.path-card:first-of-type,
.clue-card:first-of-type {
  border-top: 0;
}
.path-card span,
.clue-card span {
  display: inline-block;
  margin-top: 6px;
  color: #7dd3fc;
  font-size: 11px;
  font-weight: 900;
}
.graph-view :deep(.relation-graph),
.graph-view :deep(.rel-map),
.graph-view :deep(.rel-map-canvas),
.graph-view :deep(.rel-map-background) {
  background: transparent !important;
  color: #0f172a !important;
}
.graph-view :deep(.c-node-text),
.graph-view :deep(.c-node-name),
.graph-view :deep(.rel-node-text) {
  color: #0f172a !important;
  fill: #0f172a !important;
  font-weight: 900;
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
</style>
