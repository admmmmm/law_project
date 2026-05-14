<template>
  <div class="graph-page">
    <header class="topbar">
      <div>
        <h1>案件证据地图</h1>
        <p>{{ activeCaseId || '未选择案件' }}</p>
      </div>
      <div class="top-actions">
        <button v-for="item in mapLayers" :key="item.key" :class="['btn', { active: mapLayer === item.key }]" @click="setMapLayer(item.key)">
          {{ item.label }}
        </button>
        <button class="btn ghost" :class="{ active: useG6 }" @click="toggleGraphEngine">
          {{ useG6 ? '当前：G6' : '当前：备用' }}
        </button>
        <button class="btn" :disabled="!useG6 || loading" @click="exportGraphPng">导出截图</button>
        <button v-if="mapLayer === 'raw'" class="btn" :disabled="!activeCaseId || loading" @click="runAnalysis">重新分析</button>
        <button class="btn" :disabled="!activeCaseId || loading" @click="reloadLayer">刷新</button>
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
        <template v-if="mapLayer !== 'raw'">
          <div v-if="loading" class="empty-state">正在加载证据地图...</div>
          <div v-else-if="evidenceMap.documents.length === 0" class="empty-state">
            <Network :size="54" />
            <strong>证据地图还是空的</strong>
            <span>先导入证据，再运行分析。</span>
          </div>
          <G6EvidenceGraph
            v-else-if="useG6"
            ref="g6GraphRef"
            class="graph-view"
            :nodes="g6Nodes"
            :lines="g6Lines"
            :layer="mapLayer"
            :layout-mode="layoutMode"
            @node-click="onEvidenceMapNodeClick"
            @line-click="onEvidenceMapLineClick"
          />
          <RelationGraph
            v-else
            :key="graphRenderKey"
            ref="graphRef"
            class="graph-view"
            :options="graphOptions"
            :on-node-click="onEvidenceMapNodeClick"
            :on-line-click="onEvidenceMapLineClick"
          />
          <div v-if="!loading && evidenceMap.documents.length > 0" class="control-card evidence-map-card">
            <div class="control-head">
              <span>{{ mapLayer === 'document' ? '文件层' : '片段层' }}</span>
              <strong>{{ renderedNodeCount }} 个节点，{{ renderedEdgeCount }} 条连接</strong>
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
            <p class="map-hint">
              {{ layerGuide.purpose }}
            </p>
            <div class="mini-legend">
              <span v-for="item in layerGuide.legend" :key="item.label" :style="{ '--legend-color': item.color }">
                {{ item.label }}
              </span>
            </div>
          </div>
        </template>

        <template v-else>
        <div v-if="loading" class="empty-state">正在加载图谱...</div>
        <div v-else-if="graph.nodes.length === 0" class="empty-state">
          <Network :size="54" />
          <strong>图谱还是空的</strong>
          <span>先导入证据，再运行分析。</span>
        </div>
        <G6EvidenceGraph
          v-else-if="useG6"
          ref="g6GraphRef"
          class="graph-view"
          :nodes="g6Nodes"
          :lines="g6Lines"
          layer="raw"
          :layout-mode="layoutMode"
          @node-click="onNodeClick"
          @line-click="onLineClick"
        />
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
            <strong>{{ timelineEnabled ? currentTimelineLabel : '未启用' }}</strong>
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

          <div class="segmented demo-segmented">
            <button
              v-for="item in demoModes"
              :key="item.key"
              :class="{ active: demoMode === item.key }"
              @click="setDemoMode(item.key)"
            >
              {{ item.label }}
            </button>
          </div>
          <p class="map-hint">{{ demoModeHint }}</p>

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

          <label class="timeline-toggle">
            <input v-model="timelineEnabled" type="checkbox" @change="renderTimelineGraph" />
            <span>按时间轴生长</span>
          </label>

          <input
            v-model.number="timelineIndex"
            class="timeline"
            type="range"
            min="0"
            :max="Math.max(timelinePoints.length - 1, 0)"
            step="1"
            :disabled="!timelineEnabled"
            @input="renderTimelineGraph"
          />

          <div class="tag-list">
            <label class="tag-pill select-all">
              <input type="checkbox" :checked="allCategoriesSelected" @change="toggleAllCategories" />
              <span>全选</span>
            </label>
            <label v-for="item in availableCategories" :key="item.key" class="tag-pill">
              <input v-model="selectedCategories" type="checkbox" :value="item.key" @change="renderGraph" />
              <span>{{ item.label }} {{ item.count }}</span>
            </label>
          </div>

          <div class="graph-index">
            <label for="graph-index-select">本轮节点/关系</label>
            <select id="graph-index-select" v-model="selectedIndexValue" @change="focusGraphIndexItem">
              <option value="">选择后在图中高亮</option>
              <option v-for="item in renderedIndexItems" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
            </select>
          </div>
        </div>

        <div v-if="!loading && graph.nodes.length > 0" class="render-note">
          当前渲染 {{ renderedNodeCount }} / {{ graph.nodes.length }} 个节点，{{ renderedEdgeCount }} / {{ graph.edges.length }} 条关系
        </div>
        </template>
      </section>

      <aside class="side-panel">
        <template v-if="mapLayer !== 'raw'">
          <div class="stats">
            <div v-for="item in evidenceLayerStats" :key="item.label">
              <span>{{ item.label }}</span><strong>{{ item.value }}</strong>
            </div>
          </div>

          <section class="panel">
            <h2>当前选择</h2>
            <div v-if="selectedEvidenceMapItem" class="selected-box">
              <strong>{{ selectedEvidenceMapTitle }}</strong>
              <p>{{ selectedEvidenceMapSubtitle }}</p>
              <div class="selected-summary">
                <span v-for="tag in selectedEvidenceMapTags" :key="tag">{{ tag }}</span>
                <p>{{ selectedEvidenceMapSummary }}</p>
              </div>
              <details>
                <summary>查看原始 JSON</summary>
                <pre>{{ selectedEvidenceMapJson }}</pre>
              </details>
              <div class="row-actions">
                <button class="small-btn" @click="fillEditForm">载入维护表单</button>
              </div>
            </div>
            <p v-else class="muted">点击当前层级的节点或连接查看详情。</p>
          </section>

          <section class="panel">
            <h2>{{ layerGuide.title }}</h2>
            <p class="muted">{{ layerGuide.purpose }}</p>
            <div class="legend-list">
              <div v-for="item in layerGuide.legend" :key="item.label">
                <i :style="{ background: item.color }"></i>
                <span>{{ item.label }}</span>
              </div>
            </div>
            <div class="action-list">
              <strong>推荐操作</strong>
              <button v-for="item in layerGuide.actions" :key="item" type="button">{{ item }}</button>
            </div>
          </section>

          <section class="panel">
            <h2>图谱增删改查</h2>
            <p class="muted">维护的是案件原始图谱。文件层、片段层选中项可载入为人工节点草稿。</p>
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
        </template>

        <template v-else>
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
          <h2>{{ layerGuide.title }}</h2>
          <p class="muted">{{ layerGuide.purpose }}</p>
          <div v-if="mapLayer === 'raw'" class="mode-metrics">
            <div><span>当前中心</span><strong>{{ demoMetrics.center || '未选择' }}</strong></div>
            <div v-if="demoMetrics.peer"><span>交叉对象</span><strong>{{ demoMetrics.peer }}</strong></div>
            <div><span>显示规模</span><strong>{{ renderedNodeCount }} 节点 / {{ renderedEdgeCount }} 关系</strong></div>
            <div v-if="demoMetrics.paths"><span>高亮路径</span><strong>{{ demoMetrics.paths }}</strong></div>
            <div v-if="demoMetrics.intersections"><span>交叉节点</span><strong>{{ demoMetrics.intersections }}</strong></div>
          </div>
          <div class="legend-list">
            <div v-for="item in layerGuide.legend" :key="item.label">
              <i :style="{ background: item.color }"></i>
              <span>{{ item.label }}</span>
            </div>
          </div>
          <div class="action-list">
            <strong>推荐操作</strong>
            <button v-for="item in layerGuide.actions" :key="item" type="button">{{ item }}</button>
          </div>
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
        </template>
      </aside>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, shallowRef } from 'vue';
import RelationGraph from 'relation-graph/vue3';
import { Network } from 'lucide-vue-next';
import G6EvidenceGraph, { type G6GraphLine, type G6GraphNode } from '../components/G6EvidenceGraph.vue';
import {
  backendApi,
  type EvidenceMap,
  type EvidenceMapDocument,
  type EvidenceMapDocumentEdge,
  type EvidenceMapPassage,
  type EvidenceMapPassageEdge,
  type GraphEdge,
  type GraphNode,
  type InvestigationGraph,
} from '../api/backend';
import AsyncProgressBar from '../components/AsyncProgressBar.vue';
import { useSimulatedProgress } from '../composables/useSimulatedProgress';
import { currentWorkspaceFromPath } from '../workspace';

type LayoutMode = 'tree' | 'force';
type ViewMode = 'core' | 'evidence' | 'all';
type MapLayer = 'document' | 'passage' | 'raw';
type DemoMode = 'normal' | 'coreNeighborhood' | 'expandedNeighborhood' | 'multiHopPaths' | 'subgraphIntersection';
const DEMO_PRIMARY_NAME_PATTERNS = ['杨周武', '杨承泽', '杨'];
const DEMO_SECONDARY_NAME_PATTERNS = ['王静', '王雨晴', '王'];
type EvidenceMapItem = EvidenceMapDocument | EvidenceMapPassage | EvidenceMapDocumentEdge | EvidenceMapPassageEdge;
type DemoRole = 'seed' | 'peer' | 'hop1' | 'hop2' | 'path' | 'target' | 'shared' | 'groupA' | 'groupB';

const activeCaseId = ref(localStorage.getItem('active_case_id') || '');
const workspace = computed(() => currentWorkspaceFromPath());
const loading = ref(false);
const error = ref('');
const progress = useSimulatedProgress();
const graphRef = ref<any>(null);
const g6GraphRef = ref<InstanceType<typeof G6EvidenceGraph> | null>(null);
const graphRenderKey = ref(0);
const graph = ref<InvestigationGraph>({ case_id: activeCaseId.value, nodes: [], edges: [], clues: [] });
const evidenceMap = ref<EvidenceMap>(emptyEvidenceMap());
const mapLayer = ref<MapLayer>('document');
const selectedEvidenceMapItem = ref<EvidenceMapItem | null>(null);
const selectedKind = ref<'node' | 'edge' | ''>('');
const selectedNode = ref<GraphNode | null>(null);
const selectedEdge = ref<GraphEdge | null>(null);
const renderedNodeCount = ref(0);
const renderedEdgeCount = ref(0);
const renderedNodes = ref<GraphNode[]>([]);
const renderedEdges = ref<GraphEdge[]>([]);
const selectedIndexValue = ref('');
const timelineEnabled = ref(false);
const timelineIndex = ref(0);
const timelinePoints = ref<string[]>(['全部时间']);
const selectedCategories = ref<string[]>([]);
const viewMode = ref<ViewMode>('core');
const demoMode = ref<DemoMode>('normal');
const demoFocusNodeIds = ref(new Set<string>());
const demoFocusEdgeIds = ref(new Set<string>());
const demoNodeRoles = ref(new Map<string, DemoRole>());
const demoEdgeRoles = ref(new Map<string, string>());
const demoMetrics = ref({ mode: '常规视图', center: '', peer: '', paths: 0, intersections: 0 });
const layoutModeByLayer = reactive<Record<MapLayer, LayoutMode>>({
  document: 'force',
  passage: 'force',
  raw: 'force',
});
const layoutMode = computed({
  get: () => layoutModeByLayer[mapLayer.value],
  set: (mode: LayoutMode) => {
    layoutModeByLayer[mapLayer.value] = mode;
  },
});
const useG6 = ref(true);
const g6Nodes = shallowRef<G6GraphNode[]>([]);
const g6Lines = shallowRef<G6GraphLine[]>([]);
const MAX_RENDER_NODES = 220;
const MAX_RENDER_EDGES = 420;

const mapLayers = [
  { key: 'document', label: '文件层' },
  { key: 'passage', label: '片段层' },
  { key: 'raw', label: '原始图谱层' },
] as const;

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
  { key: 'core', label: '核心筛选' },
  { key: 'evidence', label: '证据链' },
  { key: 'all', label: '全量筛选' },
] as const;

const demoModes = [
  { key: 'normal', label: '常规视图' },
  { key: 'coreNeighborhood', label: '核心邻域' },
  { key: 'expandedNeighborhood', label: '邻域扩展' },
  { key: 'multiHopPaths', label: '多跳召回' },
  { key: 'subgraphIntersection', label: '子图交叉' },
] as const;

const layoutModes = [
  { key: 'tree', label: '树形' },
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

const allCategoriesSelected = computed(() => {
  const available = availableCategories.value.map((item) => item.key);
  return available.length > 0 && available.every((key) => selectedCategories.value.includes(key));
});

const evidenceLayerEdgeCount = computed(() =>
  mapLayer.value === 'document' ? evidenceMap.value.document_edges.length : evidenceMap.value.passage_edges.length,
);
const evidenceLayerStats = computed(() => {
  if (mapLayer.value === 'document') {
    const stages = new Set(evidenceMap.value.documents.map((doc) => doc.process_stage).filter(Boolean));
    const reviewCount = evidenceMap.value.documents.filter((doc) => doc.quality_status !== 'ok').length;
    return [
      { label: '证据文件', value: evidenceMap.value.documents.length },
      { label: '流程阶段', value: stages.size },
      { label: '关键连接', value: evidenceMap.value.document_edges.filter((edge) => edge.visible_by_default).length },
      { label: '待复核', value: reviewCount },
    ];
  }
  const entityCount = new Set(evidenceMap.value.passages.flatMap((passage) => passage.entities)).size;
  const citedCount = evidenceMap.value.passages.filter((passage) => passage.referenced_by_report).length;
  return [
    { label: '证据片段', value: evidenceMap.value.passages.length },
    { label: '共享实体', value: entityCount },
    { label: '片段连接', value: evidenceMap.value.passage_edges.filter((edge) => edge.visible_by_default).length },
    { label: '被引用', value: citedCount },
  ];
});
const g6GraphKey = computed(() =>
  `g6:${mapLayer.value}:${layoutMode.value}:${g6Nodes.value.length}:${g6Lines.value.length}`,
);
const layerGuide = computed(() => {
  if (mapLayer.value === 'document') {
    return {
      title: '文件层怎么看',
      purpose: '查看证据文件、流程阶段和材料之间的聚合关系，适合先建立卷宗结构感。',
      actions: ['按流程阶段看材料', '点击文件查看证明事项', '关注权限链与流程相邻边'],
      legend: [
        { label: '流程主干', color: '#0f766e' },
        { label: '权限链', color: '#dc2626' },
        { label: '共同核查', color: '#7c3aed' },
        { label: '共享实体', color: '#64748b' },
      ],
    };
  }
  if (mapLayer.value === 'passage') {
    return {
      title: '片段层怎么看',
      purpose: '查看证据原文片段，定位片段之间的共享实体和引用入口。',
      actions: ['按文件分组看片段', '点击片段看原文', '关注共享人物或共享事项'],
      legend: [
        { label: '同文件相邻', color: '#94a3b8' },
        { label: '共享实体', color: '#4f46e5' },
        { label: '共同核查', color: '#7c3aed' },
      ],
    };
  }
  return {
    title: `${demoMetrics.value.mode}怎么看`,
    purpose: rawModePurpose.value,
    actions: rawModeActions.value,
    legend: [
      { label: '人物关系', color: '#ef4444' },
      { label: '资金关系', color: '#f59e0b' },
      { label: '通信关系', color: '#3b82f6' },
      { label: '证据文书', color: '#10b981' },
      { label: '职务行为', color: '#8b5cf6' },
      { label: '时间节点', color: '#64748b' },
    ],
  };
});
const rawModePurpose = computed(() => {
  if (demoMode.value === 'coreNeighborhood') return '查看当前对象直接关联的人员、资金、通信、文书和行为节点，适合快速判断直接关系。';
  if (demoMode.value === 'expandedNeighborhood') return '从当前对象向外扩展 2 跳关系，适合发现间接联系人、间接资金关系和外围线索。';
  if (demoMode.value === 'multiHopPaths') return '展示当前对象到关键节点之间的若干高价值路径，适合发现关系链条。';
  if (demoMode.value === 'subgraphIntersection') return '比较两个对象或主题子图之间的共同节点与桥接路径，适合发现碰撞线索。';
  return '查看人物、资金、通信、文书和行为之间的事实关系，适合做核心节点、路径和交叉关系分析。';
});
const rawModeActions = computed(() => {
  if (demoMode.value === 'coreNeighborhood') return ['手动选择中心节点', '切换人物/资金/通信标签', '点击边查看证据'];
  if (demoMode.value === 'expandedNeighborhood') return ['展开二跳关系', '观察外围联系人', '对比一跳和二跳边'];
  if (demoMode.value === 'multiHopPaths') return ['选择目标节点', '查看路径编号', '沿路径打开证据'];
  if (demoMode.value === 'subgraphIntersection') return ['选择另一个对象', '查看交叉节点', '检查桥接路径'];
  return ['先看核心邻域', '再看多跳召回', '最后做子图交叉'];
});
const demoModeHint = computed(() => {
  if (demoMode.value === 'coreNeighborhood') return '只展示当前对象的一跳直接关系，适合快速看清它直接关联了谁。';
  if (demoMode.value === 'expandedNeighborhood') return '从当前对象扩展到二跳，区分直接关系和外围关系。';
  if (demoMode.value === 'multiHopPaths') return '抽取 3 到 5 条高价值路径，突出从对象到资金、通信、文书或关键人物的关系链。';
  if (demoMode.value === 'subgraphIntersection') return '比较两个对象或主题子图，把共同节点和桥接路径放在中间。';
  return '常规视图保留当前筛选和布局，适合看全局结构。';
});
const selectedEvidenceMapTitle = computed(() => {
  const item = selectedEvidenceMapItem.value;
  if (!item) return '';
  if ('doc_type' in item) return item.title;
  if ('text_preview' in item) return `片段 ${item.passage_index + 1}`;
  return 'label' in item ? item.label : item.type;
});
const selectedEvidenceMapSubtitle = computed(() => {
  const item = selectedEvidenceMapItem.value;
  if (!item) return '';
  if ('doc_type' in item) return `${item.doc_type} / ${item.process_stage}`;
  if ('text_preview' in item) return docTitle(item.parent_doc_id);
  return '连接';
});
const selectedEvidenceMapTags = computed(() => {
  const item = selectedEvidenceMapItem.value;
  if (!item) return [];
  if ('map_tags' in item) return item.map_tags;
  if ('entities' in item) return item.entities.slice(0, 8);
  if ('shared_entities' in item) return item.shared_entities;
  return [];
});
const selectedEvidenceMapSummary = computed(() => {
  const item = selectedEvidenceMapItem.value;
  if (!item) return '';
  if ('proof_purpose' in item) return item.proof_purpose || item.summary;
  if ('text_preview' in item) return item.text || item.text_preview;
  if ('reason' in item) return item.reason;
  return '';
});
const selectedEvidenceMapJson = computed(() =>
  selectedEvidenceMapItem.value ? JSON.stringify(selectedEvidenceMapItem.value, null, 2) : '',
);

const renderedIndexItems = computed(() => {
  const nodeItems = renderedNodes.value
    .slice()
    .sort((a, b) => a.type.localeCompare(b.type, 'zh-Hans-CN') || a.label.localeCompare(b.label, 'zh-Hans-CN'))
    .map((node) => ({
      value: `node:${node.node_id}`,
      label: `节点｜${trim(node.label, 24)}｜${node.type}`,
    }));
  const edgeItems = renderedEdges.value
    .slice()
    .sort((a, b) => a.relation.localeCompare(b.relation, 'zh-Hans-CN') || relationText(a).localeCompare(relationText(b), 'zh-Hans-CN'))
    .map((edge) => ({
      value: `edge:${edge.edge_id}`,
      label: `关系｜${trim(relationText(edge), 36)}`,
    }));
  return [...nodeItems, ...edgeItems];
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

onMounted(async () => {
  await Promise.all([loadEvidenceMap(), loadGraph()]);
  await nextTick();
  renderCurrentLayer();
});

async function loadEvidenceMap() {
  if (!activeCaseId.value) return;
  evidenceMap.value = await backendApi.getEvidenceMap(activeCaseId.value);
}

async function reloadLayer() {
  if (mapLayer.value === 'raw') {
    await loadGraph();
    return;
  }
  loading.value = true;
  error.value = '';
  try {
    await loadEvidenceMap();
    await nextTick();
    renderEvidenceMapLayer();
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    loading.value = false;
  }
}

function setMapLayer(layer: MapLayer) {
  if (layer !== 'raw' && evidenceMap.value.documents.length > 0) {
    applyEvidenceLayerData(layer);
  }
  mapLayer.value = layer;
  selectedEvidenceMapItem.value = null;
  selectedKind.value = '';
  selectedNode.value = null;
  selectedEdge.value = null;
  console.log('[GraphPage:setLayer]', {
    activeLayer: layer,
    layoutMode: layoutModeByLayer[layer],
    renderer: useG6.value ? 'G6EvidenceGraph' : 'RelationGraph',
  });
  if (layer === 'raw') nextTick(() => renderGraph());
  else if (!useG6.value) nextTick(() => renderEvidenceMapLayer(layer));
}

async function toggleGraphEngine() {
  useG6.value = !useG6.value;
  localStorage.setItem('graph_engine', useG6.value ? 'g6' : 'relation');
  graphRenderKey.value += 1;
  await nextTick();
  renderCurrentLayer();
}

async function exportGraphPng() {
  try {
    const layerLabel = mapLayers.find((item) => item.key === mapLayer.value)?.label || '图谱';
    await g6GraphRef.value?.exportPng?.(`案件证据地图-${layerLabel}-${new Date().toISOString().slice(0, 10)}.png`);
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
}

function renderCurrentLayer(layer: MapLayer = mapLayer.value) {
  console.log('[GraphPage:renderCurrentLayer]', {
    activeLayer: layer,
    layoutMode: layoutModeByLayer[layer],
    renderer: useG6.value ? 'G6EvidenceGraph' : 'RelationGraph',
  });
  if (layer === 'raw') renderGraph();
  else renderEvidenceMapLayer(layer);
}

async function loadGraph() {
  if (!activeCaseId.value) return;
  await withGraphLoading(
    async () => {
      graph.value = workspace.value?.temporary
        ? await backendApi.getMergedGraph(workspace.value.baseCaseId, workspace.value.selectedCaseIds)
        : await backendApi.getGraph(activeCaseId.value);
      syncTimelineAndTags(true);
    },
    {
      label: '正在加载图谱',
      detail: '读取案件节点、关系和线索数据',
      successLabel: '图谱已刷新',
    },
  );
  await nextTick();
  if (mapLayer.value === 'raw') renderGraph();
}

async function runAnalysis() {
  if (!activeCaseId.value) return;
  if (workspace.value?.temporary) {
    await loadGraph();
    return;
  }
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
  if (mapLayer.value === 'raw') renderGraph();
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
  if (graph.value.nodes.length === 0) return;
  graphOptions.layouts = [layoutConfig(layoutMode.value)];
  const visible = buildRenderableGraph();
  renderedNodeCount.value = visible.nodes.length;
  renderedEdgeCount.value = visible.edges.length;
  renderedNodes.value = visible.nodes;
  renderedEdges.value = visible.edges;
  if (selectedIndexValue.value && !renderedIndexItems.value.some((item) => item.value === selectedIndexValue.value)) {
    selectedIndexValue.value = '';
  }
  const positioned = layoutMode.value === 'tree' ? visible.nodes : applySpreadPositions(visible.nodes, visible.edges, layoutMode.value);
  const jsonData = {
    rootId: pickRootId(positioned, visible.edges),
    nodes: positioned.map(toRelationNode),
    lines: visible.edges.map(toRelationLine),
  };
  checkGraphPageData('raw', jsonData.nodes, jsonData.lines);
  g6Nodes.value = jsonData.nodes;
  g6Lines.value = jsonData.lines;
  console.log('[GraphPage:renderRawGraph]', {
    activeLayer: 'raw',
    layoutMode: layoutMode.value,
    nodes: jsonData.nodes.length,
    edges: jsonData.lines.length,
    firstNodes: jsonData.nodes.slice(0, 5).map((node) => ({ id: node.id, x: node.x, y: node.y })),
  });
  if (useG6.value) return;
  if (!graphRef.value) return;
  setRelationGraphOptions(graphOptions);
  graphRef.value.setJsonData(jsonData, (instance: any) => {
    if (layoutMode.value === 'tree') instance.doLayout();
    instance.moveToCenter();
    instance.zoomToFit();
    if (selectedIndexValue.value) {
      window.setTimeout(() => focusGraphIndexItem(false), 80);
    }
  });
}

async function renderEvidenceMapLayer(layer: Exclude<MapLayer, 'raw'> = mapLayer.value === 'raw' ? 'document' : mapLayer.value) {
  if (evidenceMap.value.documents.length === 0) return;
  const data = applyEvidenceLayerData(layer);
  console.log('[GraphPage:renderEvidenceMapLayer]', {
    activeLayer: layer,
    layoutMode: layoutMode.value,
    nodes: data.nodes.length,
    edges: data.lines.length,
    firstNodes: data.nodes.slice(0, 5).map((node) => ({ id: node.id, x: node.x, y: node.y })),
  });
  if (useG6.value) return;
  graphOptions.layouts = [layoutConfig(layoutMode.value)];
  graphRenderKey.value += 1;
  await nextTick();
  if (!graphRef.value) return;
  setRelationGraphOptions(graphOptions);
  graphRef.value.setJsonData(data, (instance: any) => {
    instance.moveToCenter();
    instance.zoomToFit();
  });
}

function applyEvidenceLayerData(layer: Exclude<MapLayer, 'raw'>) {
  const data = buildEvidenceLayerGraph(layer);
  checkGraphPageData(layer, data.nodes, data.lines);
  renderedNodeCount.value = data.nodes.length;
  renderedEdgeCount.value = data.lines.length;
  renderedNodes.value = [];
  renderedEdges.value = [];
  g6Nodes.value = data.nodes;
  g6Lines.value = data.lines;
  return data;
}

function buildEvidenceLayerGraph(layer: Exclude<MapLayer, 'raw'> = mapLayer.value === 'raw' ? 'document' : mapLayer.value) {
  if (layer === 'passage') {
    const passageIdMap = new Map<string, string>();
    const nodes = evidenceMap.value.passages.map((passage, index) => ({
      id: evidenceGraphNodeId('passage', passage.id, index, passage.evidence_id),
      text: passageNodeText(passage),
      data: passage,
      color: passage.referenced_by_report ? '#e0e7ff' : '#f5f7ff',
      borderColor: passage.referenced_by_report ? '#4338ca' : '#6366f1',
      borderWidth: passage.referenced_by_report ? 3 : 1.8,
      nodeShape: 1,
      width: 238,
      height: 104,
      ...passageLayerPosition(passage, index),
      fixed: true,
    })).map((node, index) => {
      const passage = evidenceMap.value.passages[index];
      registerEvidenceId(passageIdMap, passage.id, node.id);
      registerEvidenceId(passageIdMap, passage.evidence_id, node.id);
      return node;
    });
    const nodeIds = new Set(nodes.map((node) => node.id));
    const lines = evidenceMap.value.passage_edges
      .map((edge) => ({
        edge,
        source: resolveEvidenceId(passageIdMap, edge.source),
        target: resolveEvidenceId(passageIdMap, edge.target),
      }))
      .filter(({ source, target, edge }) => source && target && nodeIds.has(source) && nodeIds.has(target) && edge.visible_by_default)
      .map((edge) => ({
        id: evidenceGraphEdgeId('passage-edge', edge.edge.id, edge.source, edge.target),
        from: edge.source,
        to: edge.target,
        text: passageEdgeText(edge.edge),
        data: edge.edge,
        color: evidenceEdgeColor(edge.edge.type),
        lineWidth: evidenceLineWidth(edge.edge.type, edge.edge.weight),
      }));
    return { rootId: nodes[0]?.id, nodes, lines };
  }

  const docIdMap = new Map<string, string>();
  const nodes = evidenceMap.value.documents.map((doc, index) => ({
    id: evidenceGraphNodeId('doc', doc.evidence_id || doc.id, index, doc.title),
    text: documentNodeText(doc),
    data: doc,
    color: documentStageVisual(doc).bg,
    borderColor: doc.quality_status === 'ok' ? documentStageVisual(doc).border : '#f59e0b',
    borderWidth: doc.finding_count > 0 || doc.quality_status !== 'ok' ? 3 : 1.8,
    nodeShape: 1,
    width: 246,
    height: 118,
    ...documentLayerPosition(doc, index),
    fixed: true,
  })).map((node, index) => {
    const doc = evidenceMap.value.documents[index];
    registerEvidenceId(docIdMap, doc.id, node.id);
    registerEvidenceId(docIdMap, doc.evidence_id, node.id);
    return node;
  });
  const nodeIds = new Set(nodes.map((node) => node.id));
  const lines = evidenceMap.value.document_edges
    .map((edge) => ({
      edge,
      source: resolveEvidenceId(docIdMap, edge.source),
      target: resolveEvidenceId(docIdMap, edge.target),
    }))
    .filter(({ source, target, edge }) => source && target && nodeIds.has(source) && nodeIds.has(target) && edge.visible_by_default)
    .map((edge) => ({
      id: evidenceGraphEdgeId('doc-edge', edge.edge.id, edge.source, edge.target),
      from: edge.source,
      to: edge.target,
      text: evidenceEdgeTypeLabel(edge.edge.type),
      data: edge.edge,
      color: evidenceEdgeColor(edge.edge.type),
      lineWidth: evidenceLineWidth(edge.edge.type, edge.edge.weight),
    }));
  return { rootId: nodes[0]?.id, nodes, lines };
}

function evidenceGraphNodeId(prefix: string, rawId: unknown, index: number, fallback?: unknown) {
  const raw = String(rawId || fallback || index).replace(/\s+/g, '_');
  return `${prefix}:${raw}:${index}`;
}

function evidenceGraphEdgeId(prefix: string, rawId: unknown, source: string, target: string) {
  return `${prefix}:${String(rawId || `${source}->${target}`).replace(/\s+/g, '_')}`;
}

function registerEvidenceId(map: Map<string, string>, raw: unknown, normalized: string) {
  const key = String(raw || '');
  if (!key || map.has(key)) return;
  map.set(key, normalized);
}

function resolveEvidenceId(map: Map<string, string>, raw: unknown) {
  return map.get(String(raw || '')) || '';
}

function checkGraphPageData(layer: MapLayer, nodes: G6GraphNode[], lines: G6GraphLine[]) {
  const ids = new Set<string>();
  const duplicates: string[] = [];
  nodes.forEach((node) => {
    if (ids.has(node.id)) duplicates.push(node.id);
    ids.add(node.id);
  });
  const invalidEdges = lines
    .filter((line) => !ids.has(line.from) || !ids.has(line.to))
    .slice(0, 20)
    .map((line) => ({
      id: line.id,
      source: line.from,
      target: line.to,
      sourceExists: ids.has(line.from),
      targetExists: ids.has(line.to),
    }));
  const summary = {
    activeLayer: layer,
    renderer: useG6.value ? 'G6EvidenceGraph' : 'RelationGraph',
    nodes: nodes.length,
    edges: lines.length,
    uniqueNodeIds: ids.size,
    duplicateNodeIds: duplicates.length,
    invalidEdges: invalidEdges.length,
    firstDuplicateIds: duplicates.slice(0, 20),
    firstInvalidEdges: invalidEdges,
  };
  if (duplicates.length || invalidEdges.length) console.warn('[GraphPage:graphDataCheck]', summary);
  else console.log('[GraphPage:graphDataCheck]', summary);
}

function documentLayerPosition(doc: EvidenceMapDocument, index: number) {
  const order = ['接警', '受案登记', '伤情鉴定/送检', '立案', '强制措施', '释放', '调解/撤案', '检察侦查', '事故后果', '履职监管', '未归类'];
  const stage = Math.max(order.indexOf(doc.process_stage), 0);
  return { x: stage * 330, y: (index % 5) * 158 + Math.floor(index / 5) * 860 };
}

function passageLayerPosition(passage: EvidenceMapPassage, index: number) {
  const docIds = [...new Set(evidenceMap.value.passages.map((item) => item.parent_doc_id))];
  const docIndex = Math.max(docIds.indexOf(passage.parent_doc_id), 0);
  const localIndex = evidenceMap.value.passages
    .filter((item) => item.parent_doc_id === passage.parent_doc_id)
    .findIndex((item) => item.id === passage.id);
  return {
    x: docIndex * 318,
    y: Math.max(localIndex, index % 4) * 132 + Math.floor(docIndex / 5) * 680,
  };
}

function evidenceEdgeTypeLabel(type: string) {
  const labels: Record<string, string> = {
    PROCESS_NEXT: '流程相邻',
    SHARED_ENTITY: '共享实体',
    SUPPORTS_SAME_FINDING: '共同支撑核查项',
    AUTHORITY_CHAIN: '权限链',
    SAME_DOCUMENT_ORDER: '同文件相邻片段',
  };
  return labels[type] || type;
}

function evidenceEdgeColor(type: string) {
  if (type === 'PROCESS_NEXT') return '#0f766e';
  if (type === 'SUPPORTS_SAME_FINDING') return '#7c3aed';
  if (type === 'AUTHORITY_CHAIN') return '#dc2626';
  if (type === 'SAME_DOCUMENT_ORDER') return '#94a3b8';
  return '#64748b';
}

function evidenceLineWidth(type: string, weight = 0.5) {
  const base = type === 'PROCESS_NEXT' || type === 'AUTHORITY_CHAIN' || type === 'SUPPORTS_SAME_FINDING' ? 2.7 : 1.25;
  return Math.max(base, Math.min(3.4, base + weight * 0.7));
}

function documentNodeText(doc: EvidenceMapDocument) {
  const status = doc.quality_status === 'ok' ? '' : '｜待复核';
  return `${doc.doc_type || '证据材料'}｜${doc.process_stage || '未归类'}${status}\n${trim(doc.title, 20)}\n${doc.passage_count}片段 / ${doc.triple_count}关系 / ${doc.finding_count}核查`;
}

function passageNodeText(passage: EvidenceMapPassage) {
  const entities = passage.entities.slice(0, 2).join('、');
  const entityLine = entities ? `实体：${trim(entities, 18)}` : docTitle(passage.parent_doc_id);
  return `片段 ${passage.passage_index + 1}｜${passage.triple_count}关系\n${trim(passage.text_preview, 34)}\n${entityLine}`;
}

function passageEdgeText(edge: EvidenceMapPassageEdge) {
  if (edge.shared_entities?.length) return `共同出现：${edge.shared_entities.slice(0, 2).join('、')}`;
  return evidenceEdgeTypeLabel(edge.type);
}

function documentStageVisual(doc: EvidenceMapDocument) {
  const colors: Record<string, { bg: string; border: string }> = {
    接警: { bg: '#eff6ff', border: '#2563eb' },
    受案登记: { bg: '#eff6ff', border: '#2563eb' },
    '伤情鉴定/送检': { bg: '#fff7ed', border: '#ea580c' },
    立案: { bg: '#ecfdf5', border: '#0f766e' },
    强制措施: { bg: '#fef3c7', border: '#d97706' },
    释放: { bg: '#fef2f2', border: '#dc2626' },
    '调解/撤案': { bg: '#f5f3ff', border: '#7c3aed' },
    检察侦查: { bg: '#f0fdfa', border: '#0891b2' },
    事故后果: { bg: '#f8fafc', border: '#475569' },
    履职监管: { bg: '#f1f5f9', border: '#334155' },
  };
  return colors[doc.process_stage] || { bg: '#ffffff', border: '#64748b' };
}

function onEvidenceMapNodeClick(node: { data?: unknown }) {
  if (!node.data) return;
  selectedEvidenceMapItem.value = node.data as EvidenceMapItem;
}

function onEvidenceMapLineClick(line: { data?: unknown }) {
  if (!line.data) return;
  selectedEvidenceMapItem.value = line.data as EvidenceMapItem;
}

function docTitle(docId: string) {
  return evidenceMap.value.documents.find((doc) => doc.id === docId)?.title || docId;
}

async function renderTimelineGraph() {
  graphRenderKey.value += 1;
  await nextTick();
  renderGraph();
}

function buildRenderableGraph() {
  const categorySet = new Set(selectedCategories.value);
  const cutoff = timelinePoints.value[timelineIndex.value] || '';
  const hasCutoff = timelineEnabled.value && Boolean(cutoff && cutoff !== '全部时间');
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
  const visibleNodeIds = new Set(directNodeIds);
  timeEdges.forEach((edge) => {
    if (!directEdgeIds.has(edge.edge_id)) return;
    visibleNodeIds.add(edge.source_id);
    visibleNodeIds.add(edge.target_id);
  });
  const filteredNodes = timeNodes.filter((node) => visibleNodeIds.has(node.node_id));
  let filteredEdges = timeEdges.filter(
    (edge) =>
      directEdgeIds.has(edge.edge_id) ||
      (directNodeIds.has(edge.source_id) && directNodeIds.has(edge.target_id)),
  );

  const modeIds = demoMode.value === 'normal' ? modeNodeIds(filteredNodes, filteredEdges) : new Set(filteredNodes.map((node) => node.node_id));
  const modeNodes = filteredNodes.filter((node) => modeIds.has(node.node_id));
  const modeNodeIdsSet = new Set(modeNodes.map((node) => node.node_id));
  filteredEdges = filteredEdges.filter((edge) => modeNodeIdsSet.has(edge.source_id) && modeNodeIdsSet.has(edge.target_id));
  const demoGraph = applyDemoMode(modeNodes, filteredEdges);
  const visibleNodes = demoGraph.nodes;
  filteredEdges = demoGraph.edges;

  if (visibleNodes.length <= MAX_RENDER_NODES && filteredEdges.length <= MAX_RENDER_EDGES) {
    return { nodes: visibleNodes, edges: filteredEdges };
  }

  const degree = new Map<string, number>();
  filteredEdges.forEach((edge) => {
    degree.set(edge.source_id, (degree.get(edge.source_id) || 0) + 1);
    degree.set(edge.target_id, (degree.get(edge.target_id) || 0) + 1);
  });
  const clueIds = clueRelatedNodeIds();
  const selectedIds = new Set(
    visibleNodes
      .map((node) => ({ node, score: (degree.get(node.node_id) || 0) + (clueIds.has(node.node_id) ? 80 : 0) + (node.type === 'evidence' ? 10 : 30) }))
      .sort((a, b) => b.score - a.score)
      .slice(0, MAX_RENDER_NODES)
      .map((item) => item.node.node_id),
  );
  forceSelectedIndexIds(selectedIds);
  const selectedEdgeId = selectedIndexValue.value.startsWith('edge:') ? selectedIndexValue.value.slice(5) : '';
  return {
    nodes: visibleNodes.filter((node) => selectedIds.has(node.node_id)),
    edges: filteredEdges
      .filter((edge) => selectedIds.has(edge.source_id) && selectedIds.has(edge.target_id))
      .sort((a, b) => Number(b.edge_id === selectedEdgeId) - Number(a.edge_id === selectedEdgeId) || Number(b.properties?.count || 1) - Number(a.properties?.count || 1))
      .slice(0, MAX_RENDER_EDGES),
  };
}

function forceSelectedIndexIds(selectedIds: Set<string>) {
  if (!selectedIndexValue.value) return;
  const [kind, ...rest] = selectedIndexValue.value.split(':');
  const id = rest.join(':');
  if (kind === 'node') {
    selectedIds.add(id);
    return;
  }
  const edge = graph.value.edges.find((item) => item.edge_id === id);
  if (!edge) return;
  selectedIds.add(edge.source_id);
  selectedIds.add(edge.target_id);
}

function applyDemoMode(nodes: GraphNode[], edges: GraphEdge[]) {
  demoFocusNodeIds.value = new Set();
  demoFocusEdgeIds.value = new Set();
  demoNodeRoles.value = new Map();
  demoEdgeRoles.value = new Map();
  demoMetrics.value = { mode: '常规视图', center: '', peer: '', paths: 0, intersections: 0 };
  if (demoMode.value === 'normal') return { nodes, edges };
  const seed = selectedNode.value?.node_id || selectedNodeFromIndex() || pickDemoSeed(nodes, edges);
  if (!seed) return { nodes, edges };
  if (demoMode.value === 'coreNeighborhood') return buildCoreNeighborhoodSubgraph(nodes, edges, seed);
  if (demoMode.value === 'expandedNeighborhood') return buildExpandedNeighborhoodSubgraph(nodes, edges, seed);
  if (demoMode.value === 'multiHopPaths') return buildMultihopPathSubgraph(nodes, edges, seed);
  return buildIntersectionSubgraph(nodes, edges, seed);
}

function selectedNodeFromIndex() {
  if (!selectedIndexValue.value.startsWith('node:')) return '';
  return selectedIndexValue.value.slice(5);
}

function pickDemoSeed(nodes: GraphNode[], edges: GraphEdge[]) {
  const degree = degreeMap(edges);
  const preferred = pickPreferredDemoNode(nodes, DEMO_PRIMARY_NAME_PATTERNS, '', degree);
  if (preferred) return preferred;
  return nodes
    .filter(isPersonNode)
    .sort((a, b) => (degree.get(b.node_id) || 0) - (degree.get(a.node_id) || 0))[0]?.node_id
    || nodes.sort((a, b) => (degree.get(b.node_id) || 0) - (degree.get(a.node_id) || 0))[0]?.node_id
    || '';
}

function pickPreferredDemoNode(nodes: GraphNode[], patterns: string[], excludeId = '', degree = new Map<string, number>()) {
  const candidates = nodes.filter((node) => node.node_id !== excludeId);
  const personCandidates = candidates.filter(isPersonNode);
  for (const pattern of patterns) {
    const matchedPerson = personCandidates
      .filter((node) => demoNodeText(node).includes(pattern))
      .sort((a, b) => (degree.get(b.node_id) || 0) - (degree.get(a.node_id) || 0))[0];
    if (matchedPerson) return matchedPerson.node_id;
  }
  for (const pattern of patterns) {
    const matched = candidates
      .filter((node) => demoNodeText(node).includes(pattern))
      .sort((a, b) => (degree.get(b.node_id) || 0) - (degree.get(a.node_id) || 0))[0];
    if (matched) return matched.node_id;
  }
  return '';
}

function demoNodeText(node: GraphNode) {
  return `${node.label || ''} ${node.node_id || ''} ${node.type || ''}`;
}

function isPersonNode(node: GraphNode) {
  return itemTags(node).includes('person') || node.type === 'person';
}

function buildCoreNeighborhoodSubgraph(nodes: GraphNode[], edges: GraphEdge[], seed: string) {
  const seedNode = nodes.find((node) => node.node_id === seed);
  const oneHopEdges = edges
    .filter((edge) => edge.source_id === seed || edge.target_id === seed)
    .sort(edgeImportanceSort)
    .slice(0, 24);
  const selected = new Set<string>([seed]);
  oneHopEdges.forEach((edge) => {
    selected.add(edge.source_id);
    selected.add(edge.target_id);
    demoEdgeRoles.value.set(edge.edge_id, '一跳关系');
  });
  const selectedNodes = nodes.filter((node) => selected.has(node.node_id));
  selectedNodes.forEach((node) => demoNodeRoles.value.set(node.node_id, node.node_id === seed ? 'seed' : 'hop1'));
  demoMetrics.value = { mode: '核心邻域', center: seedNode?.label || seed, peer: '', paths: 0, intersections: 0 };
  markDemoFocus(new Set([seed]), oneHopEdges, [seed]);
  return {
    nodes: applyDemoPositions(selectedNodes, oneHopEdges, seed, 'coreNeighborhood'),
    edges: oneHopEdges,
  };
}

function buildExpandedNeighborhoodSubgraph(nodes: GraphNode[], edges: GraphEdge[], seed: string) {
  const seedNode = nodes.find((node) => node.node_id === seed);
  const hop = hopDistances(seed, edges, 2);
  const selected = new Set(
    [...hop.entries()]
      .filter(([, distance]) => distance <= 2)
      .map(([id]) => id),
  );
  const oneHop = new Set([...hop.entries()].filter(([, distance]) => distance === 1).map(([id]) => id));
  const twoHop = new Set([...hop.entries()].filter(([, distance]) => distance === 2).map(([id]) => id));
  const selectedEdges = edges
    .filter((edge) => selected.has(edge.source_id) && selected.has(edge.target_id))
    .sort((a, b) => {
      const ar = Math.min(hop.get(a.source_id) || 9, hop.get(a.target_id) || 9);
      const br = Math.min(hop.get(b.source_id) || 9, hop.get(b.target_id) || 9);
      return ar - br || edgeImportanceSort(a, b);
    })
    .slice(0, 90);
  const used = new Set<string>([seed]);
  selectedEdges.forEach((edge) => {
    used.add(edge.source_id);
    used.add(edge.target_id);
    const maxHop = Math.max(hop.get(edge.source_id) || 0, hop.get(edge.target_id) || 0);
    demoEdgeRoles.value.set(edge.edge_id, maxHop <= 1 ? '一跳关系' : '二跳关系');
  });
  const selectedNodes = rankDemoNodes(nodes.filter((node) => used.has(node.node_id)), selectedEdges).slice(0, 55);
  selectedNodes.forEach((node) => {
    const id = node.node_id;
    demoNodeRoles.value.set(id, id === seed ? 'seed' : oneHop.has(id) ? 'hop1' : twoHop.has(id) ? 'hop2' : 'path');
  });
  const nodeIds = new Set(selectedNodes.map((node) => node.node_id));
  const finalEdges = selectedEdges.filter((edge) => nodeIds.has(edge.source_id) && nodeIds.has(edge.target_id));
  demoMetrics.value = { mode: '邻域扩展', center: seedNode?.label || seed, peer: '', paths: 0, intersections: 0 };
  markDemoFocus(new Set([seed, ...oneHop]), finalEdges.filter((edge) => demoEdgeRoles.value.get(edge.edge_id) === '一跳关系'), [seed]);
  return {
    nodes: applyDemoPositions(selectedNodes, finalEdges, seed, 'expandedNeighborhood', hop),
    edges: finalEdges,
  };
}

function buildMultihopPathSubgraph(nodes: GraphNode[], edges: GraphEdge[], seed: string) {
  const seedNode = nodes.find((node) => node.node_id === seed);
  const targets = pickPathTargets(nodes, edges, seed).slice(0, 5);
  const paths = targets
    .map((target) => shortestPath(seed, target, edges, 4))
    .filter((path): path is string[] => Boolean(path && path.length > 1))
    .slice(0, 5);
  const pathEdgeIds = new Set<string>();
  const selectedNodeIds = new Set<string>([seed]);
  paths.forEach((path, index) => {
    path.forEach((id, step) => {
      selectedNodeIds.add(id);
      demoNodeRoles.value.set(id, id === seed ? 'seed' : step === path.length - 1 ? 'target' : 'path');
    });
    pathEdges(path, edges).forEach((edge) => {
      pathEdgeIds.add(edge.edge_id);
      demoEdgeRoles.value.set(edge.edge_id, `路径 ${index + 1}`);
    });
  });
  const selectedEdges = edges.filter((edge) => pathEdgeIds.has(edge.edge_id));
  markDemoFocus(selectedNodeIds, selectedEdges, [seed, ...targets]);
  demoMetrics.value = { mode: '多跳召回', center: seedNode?.label || seed, peer: '', paths: paths.length, intersections: 0 };
  return {
    nodes: applyPathPositions(nodes.filter((node) => selectedNodeIds.has(node.node_id)), selectedEdges, paths),
    edges: selectedEdges,
  };
}

function buildIntersectionSubgraph(nodes: GraphNode[], edges: GraphEdge[], seed: string) {
  const other = pickIntersectionPeer(nodes, edges, seed);
  if (!other) return buildExpandedNeighborhoodSubgraph(nodes, edges, seed);
  const first = bfsNodeIds(seed, edges, 2);
  const second = bfsNodeIds(other, edges, 2);
  const shared = new Set([...first].filter((id) => second.has(id)));
  shared.add(seed);
  shared.add(other);
  const selectedEdges = edges.filter(
    (edge) =>
      (shared.has(edge.source_id) && shared.has(edge.target_id)) ||
      ((edge.source_id === seed || edge.target_id === seed || edge.source_id === other || edge.target_id === other) &&
        (shared.has(edge.source_id) || shared.has(edge.target_id))),
  ).sort(edgeImportanceSort).slice(0, 75);
  const selectedIds = new Set<string>([seed, other]);
  selectedEdges.forEach((edge) => {
    selectedIds.add(edge.source_id);
    selectedIds.add(edge.target_id);
    const inShared = shared.has(edge.source_id) && shared.has(edge.target_id);
    demoEdgeRoles.value.set(edge.edge_id, inShared ? '交叉关系' : '桥接路径');
  });
  const seedOnly = differenceSet(first, second);
  const otherOnly = differenceSet(second, first);
  nodes.forEach((node) => {
    if (!selectedIds.has(node.node_id)) return;
    if (node.node_id === seed) demoNodeRoles.value.set(node.node_id, 'seed');
    else if (node.node_id === other) demoNodeRoles.value.set(node.node_id, 'peer');
    else if (shared.has(node.node_id)) demoNodeRoles.value.set(node.node_id, 'shared');
    else if (seedOnly.has(node.node_id)) demoNodeRoles.value.set(node.node_id, 'groupA');
    else if (otherOnly.has(node.node_id)) demoNodeRoles.value.set(node.node_id, 'groupB');
  });
  markDemoFocus(shared, selectedEdges.filter((edge) => shared.has(edge.source_id) && shared.has(edge.target_id)), [seed, other]);
  const seedLabel = nodes.find((node) => node.node_id === seed)?.label || seed;
  const peerLabel = nodes.find((node) => node.node_id === other)?.label || other;
  demoMetrics.value = { mode: '子图交叉', center: seedLabel, peer: peerLabel, paths: 0, intersections: shared.size };
  return {
    nodes: applyIntersectionPositions(rankDemoNodes(nodes.filter((node) => selectedIds.has(node.node_id)), selectedEdges).slice(0, 60), seed, other),
    edges: selectedEdges,
  };
}

function bfsNodeIds(seed: string, edges: GraphEdge[], maxDepth: number) {
  const ids = new Set<string>([seed]);
  let frontier = new Set<string>([seed]);
  for (let depth = 0; depth < maxDepth; depth += 1) {
    const next = new Set<string>();
    edges.forEach((edge) => {
      if (frontier.has(edge.source_id)) next.add(edge.target_id);
      if (frontier.has(edge.target_id)) next.add(edge.source_id);
    });
    next.forEach((id) => ids.add(id));
    frontier = next;
    if (frontier.size === 0) break;
  }
  return ids;
}

function hopDistances(seed: string, edges: GraphEdge[], maxDepth: number) {
  const distances = new Map<string, number>([[seed, 0]]);
  let frontier = new Set<string>([seed]);
  for (let depth = 1; depth <= maxDepth; depth += 1) {
    const next = new Set<string>();
    edges.forEach((edge) => {
      if (frontier.has(edge.source_id) && !distances.has(edge.target_id)) next.add(edge.target_id);
      if (frontier.has(edge.target_id) && !distances.has(edge.source_id)) next.add(edge.source_id);
    });
    next.forEach((id) => distances.set(id, depth));
    frontier = next;
  }
  return distances;
}

function pickPathTargets(nodes: GraphNode[], edges: GraphEdge[], seed: string) {
  const reachable = bfsNodeIds(seed, edges, 4);
  const degree = degreeMap(edges);
  return nodes
    .filter((node) => node.node_id !== seed && reachable.has(node.node_id))
    .map((node) => ({
      node,
      score:
        relationValue(node) +
        (degree.get(node.node_id) || 0) * 0.5 +
        (DEMO_SECONDARY_NAME_PATTERNS.some((pattern) => demoNodeText(node).includes(pattern)) ? 20 : 0),
    }))
    .sort((a, b) => b.score - a.score)
    .map((item) => item.node.node_id);
}

function relationValue(node: GraphNode) {
  const tags = itemTags(node);
  if (DEMO_SECONDARY_NAME_PATTERNS.some((pattern) => demoNodeText(node).includes(pattern))) return 90;
  if (tags.includes('account') || tags.includes('bank_flow')) return 80;
  if (tags.includes('call_record')) return 70;
  if (tags.includes('law_document') || node.type === 'evidence') return 65;
  if (tags.includes('duty_behavior') || tags.includes('subjective_state')) return 60;
  if (tags.includes('person')) return 55;
  return 20;
}

function shortestPath(start: string, target: string, edges: GraphEdge[], maxDepth: number) {
  const adjacency = new Map<string, string[]>();
  edges.forEach((edge) => {
    if (!adjacency.has(edge.source_id)) adjacency.set(edge.source_id, []);
    if (!adjacency.has(edge.target_id)) adjacency.set(edge.target_id, []);
    adjacency.get(edge.source_id)?.push(edge.target_id);
    adjacency.get(edge.target_id)?.push(edge.source_id);
  });
  const queue: string[][] = [[start]];
  const visited = new Set<string>([start]);
  while (queue.length) {
    const path = queue.shift() || [];
    const last = path[path.length - 1];
    if (last === target) return path;
    if (path.length > maxDepth + 1) continue;
    const nextNodes = (adjacency.get(last) || []).sort((a, b) => relationValue(nodeMap.value.get(b) || ({ node_id: b, label: b, type: '', properties: {}, evidence_ids: [], manually_verified: false } as GraphNode)) - relationValue(nodeMap.value.get(a) || ({ node_id: a, label: a, type: '', properties: {}, evidence_ids: [], manually_verified: false } as GraphNode)));
    for (const next of nextNodes) {
      if (visited.has(next)) continue;
      visited.add(next);
      queue.push([...path, next]);
    }
  }
  return null;
}

function pathEdges(path: string[], edges: GraphEdge[]) {
  const result: GraphEdge[] = [];
  for (let index = 0; index < path.length - 1; index += 1) {
    const a = path[index];
    const b = path[index + 1];
    const edge = edges
      .filter((item) => (item.source_id === a && item.target_id === b) || (item.source_id === b && item.target_id === a))
      .sort(edgeImportanceSort)[0];
    if (edge) result.push(edge);
  }
  return result;
}

function differenceSet(a: Set<string>, b: Set<string>) {
  return new Set([...a].filter((id) => !b.has(id)));
}

function applyDemoPositions(nodes: GraphNode[], edges: GraphEdge[], seed: string, mode: DemoMode, hop = new Map<string, number>()) {
  const byRole = (role: DemoRole) => nodes.filter((node) => demoNodeRoles.value.get(node.node_id) === role);
  if (mode === 'coreNeighborhood') {
    return positionRadial(nodes, seed, 0, 0, 300);
  }
  if (mode === 'expandedNeighborhood') {
    return nodes.map((node) => {
      const distance = hop.get(node.node_id) || 0;
      if (node.node_id === seed) return withPosition(node, 0, 0);
      const group = distance <= 1 ? byRole('hop1') : byRole('hop2');
      const index = Math.max(group.findIndex((item) => item.node_id === node.node_id), 0);
      const radius = distance <= 1 ? 260 : 520;
      const angle = (index / Math.max(group.length, 1)) * Math.PI * 2 - Math.PI / 2 + (distance === 2 ? 0.16 : 0);
      return withPosition(node, Math.cos(angle) * radius, Math.sin(angle) * radius);
    });
  }
  return applySpreadPositions(nodes, edges, 'force');
}

function positionRadial(nodes: GraphNode[], seed: string, cx: number, cy: number, radius: number) {
  const rest = nodes.filter((node) => node.node_id !== seed).sort((a, b) => relationValue(b) - relationValue(a));
  return nodes.map((node) => {
    if (node.node_id === seed) return withPosition(node, cx, cy);
    const index = Math.max(rest.findIndex((item) => item.node_id === node.node_id), 0);
    const angle = (index / Math.max(rest.length, 1)) * Math.PI * 2 - Math.PI / 2;
    return withPosition(node, cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius);
  });
}

function applyPathPositions(nodes: GraphNode[], edges: GraphEdge[], paths: string[][]) {
  const positions = new Map<string, { x: number; y: number }>();
  const rowGap = 210;
  const colGap = 280;
  paths.forEach((path, row) => {
    const y = (row - (paths.length - 1) / 2) * rowGap;
    path.forEach((id, col) => {
      if (!positions.has(id)) positions.set(id, { x: col * colGap, y });
      else {
        const current = positions.get(id)!;
        positions.set(id, { x: Math.min(current.x, col * colGap), y: (current.y + y) / 2 });
      }
    });
  });
  const fallback = positionRadial(nodes.filter((node) => !positions.has(node.node_id)), '', 460, 0, 260);
  return nodes.map((node) => {
    const pos = positions.get(node.node_id) || (fallback.find((item) => item.node_id === node.node_id)?.properties as any) || { x: 0, y: 0 };
    return withPosition(node, Number(pos.x) || 0, Number(pos.y) || 0);
  });
}

function applyIntersectionPositions(nodes: GraphNode[], seed: string, other: string) {
  const groups: Record<string, GraphNode[]> = {
    groupA: nodes.filter((node) => demoNodeRoles.value.get(node.node_id) === 'groupA'),
    groupB: nodes.filter((node) => demoNodeRoles.value.get(node.node_id) === 'groupB'),
    shared: nodes.filter((node) => demoNodeRoles.value.get(node.node_id) === 'shared' && node.node_id !== seed && node.node_id !== other),
  };
  const positioned: GraphNode[] = [];
  const pushRadial = (items: GraphNode[], cx: number, cy: number, radius: number) => {
    positionRadial(items, '', cx, cy, radius).forEach((node) => positioned.push(node));
  };
  nodes.forEach((node) => {
    if (node.node_id === seed) positioned.push(withPosition(node, -420, 0));
    if (node.node_id === other) positioned.push(withPosition(node, 420, 0));
  });
  pushRadial(groups.groupA, -420, 0, 240);
  pushRadial(groups.groupB, 420, 0, 240);
  pushRadial(groups.shared, 0, 0, 210);
  return nodes.map((node) => positioned.find((item) => item.node_id === node.node_id) || withPosition(node, 0, 0));
}

function withPosition(node: GraphNode, x: number, y: number) {
  return {
    ...node,
    properties: {
      ...node.properties,
      x: Math.round(x),
      y: Math.round(y),
      fixed: true,
    },
  };
}

function pickIntersectionPeer(nodes: GraphNode[], edges: GraphEdge[], seed: string) {
  const seedNeighbors = bfsNodeIds(seed, edges, 1);
  const degree = degreeMap(edges);
  const preferred = pickPreferredDemoNode(nodes, DEMO_SECONDARY_NAME_PATTERNS, seed, degree);
  if (preferred) return preferred;
  return nodes
    .filter((node) => node.node_id !== seed && isPersonNode(node))
    .map((node) => ({ node, shared: [...bfsNodeIds(node.node_id, edges, 1)].filter((id) => seedNeighbors.has(id)).length }))
    .sort((a, b) => b.shared - a.shared || (degree.get(b.node.node_id) || 0) - (degree.get(a.node.node_id) || 0))[0]?.node.node_id || '';
}

function degreeMap(edges: GraphEdge[]) {
  const degree = new Map<string, number>();
  edges.forEach((edge) => {
    degree.set(edge.source_id, (degree.get(edge.source_id) || 0) + 1);
    degree.set(edge.target_id, (degree.get(edge.target_id) || 0) + 1);
  });
  return degree;
}

function markDemoFocus(nodes: Set<string>, edges: GraphEdge[], seeds: string[]) {
  const nodeIds = new Set(nodes);
  seeds.forEach((id) => nodeIds.add(id));
  demoFocusNodeIds.value = nodeIds;
  demoFocusEdgeIds.value = new Set(edges.map((edge) => edge.edge_id));
}

function rankDemoNodes(nodes: GraphNode[], edges: GraphEdge[]) {
  const degree = degreeMap(edges);
  return nodes.sort(
    (a, b) =>
      Number(demoFocusNodeIds.value.has(b.node_id)) - Number(demoFocusNodeIds.value.has(a.node_id)) ||
      (degree.get(b.node_id) || 0) - (degree.get(a.node_id) || 0) ||
      Number(itemTags(b).includes('person')) - Number(itemTags(a).includes('person')),
  );
}

function edgeImportanceSort(a: GraphEdge, b: GraphEdge) {
  return (
    Number(isMainRelation(b)) - Number(isMainRelation(a)) ||
    Number(demoFocusEdgeIds.value.has(b.edge_id)) - Number(demoFocusEdgeIds.value.has(a.edge_id)) ||
    Number(b.properties?.count || 1) - Number(a.properties?.count || 1)
  );
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
    demoMode.value = 'normal';
  }
}

function setViewMode(mode: ViewMode) {
  viewMode.value = mode;
  renderGraph();
}

function setDemoMode(mode: DemoMode) {
  demoMode.value = mode;
  if (mode !== 'normal' && !selectedNode.value) {
    const seedId = pickDemoSeed(graph.value.nodes, graph.value.edges);
    const seed = graph.value.nodes.find((node) => node.node_id === seedId);
    if (seed) {
      selectedKind.value = 'node';
      selectedNode.value = seed;
      selectedEdge.value = null;
      selectedIndexValue.value = `node:${seed.node_id}`;
    }
  }
  renderGraph();
}

function toggleAllCategories(event: Event) {
  const checked = Boolean((event.target as HTMLInputElement).checked);
  selectedCategories.value = checked ? availableCategories.value.map((item) => item.key) : [];
  renderGraph();
}

function focusGraphIndexItem(updateSelection: boolean | Event = true) {
  if (!selectedIndexValue.value) return;
  const shouldUpdateSelection = updateSelection !== false;
  const [kind, ...rest] = selectedIndexValue.value.split(':');
  const id = rest.join(':');
  const instance = graphRef.value?.getInstance?.();
  if (kind === 'node') {
    const node = renderedNodes.value.find((item) => item.node_id === id);
    if (!node) return;
    if (shouldUpdateSelection) {
      selectedKind.value = 'node';
      selectedNode.value = node;
      selectedEdge.value = null;
    }
    if (useG6.value) {
      g6GraphRef.value?.focusElement(id);
      return;
    }
    instance?.setCheckedNode?.(id);
    instance?.focusNodeById?.(id);
    return;
  }
  if (kind === 'edge') {
    const edge = renderedEdges.value.find((item) => item.edge_id === id);
    if (!edge) return;
    if (shouldUpdateSelection) {
      selectedKind.value = 'edge';
      selectedEdge.value = edge;
      selectedNode.value = null;
    }
    if (useG6.value) {
      g6GraphRef.value?.focusElement(id);
      return;
    }
    instance?.setCheckedLine?.(id);
    instance?.focusNodeById?.(edge.source_id);
  }
}

async function setLayoutMode(mode: LayoutMode) {
  const activeLayer = mapLayer.value;
  layoutModeByLayer[activeLayer] = mode;
  console.log('[GraphPage:setLayoutMode]', {
    activeLayer,
    layoutMode: mode,
    renderer: useG6.value ? 'G6EvidenceGraph' : 'RelationGraph',
  });
  await nextTick();
  if (useG6.value) return;
  if (!useG6.value) graphRenderKey.value += 1;
  renderCurrentLayer(activeLayer);
}

function layoutConfig(mode: LayoutMode) {
  if (mode === 'tree') return { layoutName: 'tree', from: 'left', min_per_width: 220, max_per_width: 420, min_per_height: 84 };
  if (mode === 'force') return { layoutName: 'force', maxLayoutTimes: 1400, force_node_repulsion: 14, force_line_elastic: 0.08 };
  return { layoutName: 'force', maxLayoutTimes: 1400, force_node_repulsion: 14, force_line_elastic: 0.08 };
}

function setRelationGraphOptions(options: typeof graphOptions) {
  const instance = graphRef.value?.getInstance?.();
  if (instance?.setOptions) {
    instance.setOptions(options);
    return;
  }
  graphRef.value?.setOptions?.(options, true);
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
  if (selectedEvidenceMapItem.value && !selectedNode.value && !selectedEdge.value) {
    const item = selectedEvidenceMapItem.value as any;
    Object.assign(nodeForm, {
      node_id: `manual:${String(item.id || Date.now())}`,
      label: selectedEvidenceMapTitle.value || String(item.id || '人工节点'),
      type: 'manual',
      properties: {
        source_layer: mapLayer.value,
        source_id: item.id,
        source_type: item.type,
        summary: selectedEvidenceMapSummary.value,
      },
      evidence_ids: item.evidence_id ? [item.evidence_id] : [],
      manually_verified: true,
    });
    return;
  }
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
  if (node.tags?.length) return [...new Set(node.tags)];
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
  if (edge.tags?.length) return [...new Set(edge.tags)];
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
    item.timestamp,
    item.time_range?.[0],
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
  const degree = nodeDegree(node.node_id);
  const isCore = isImportant || degree >= 4 || itemTags(node).includes('clue_related');
  const isDemoFocus = demoFocusNodeIds.value.has(node.node_id);
  const role = demoNodeRoles.value.get(node.node_id);
  const roleStyle = demoNodeStyle(role);
  return {
    id: node.node_id,
    text: isEvidence ? evidenceNodeText(node) : trim(node.label, 10),
    data: node,
    type: node.type,
    color: roleStyle.bg || (isDemoFocus ? '#fff7ed' : nodeColor(node)),
    borderColor: roleStyle.border || (isDemoFocus ? '#ea580c' : nodeBorderColor(node)),
    borderWidth: roleStyle.width || (isDemoFocus ? 4.2 : isCore ? 3.4 : 1.8),
    fontColor: '#0f172a',
    width: role === 'seed' || role === 'peer' ? 112 : role === 'target' || role === 'shared' ? 100 : isEvidence ? 146 : isDemoFocus || isCore ? 98 : 72,
    height: role === 'seed' || role === 'peer' ? 112 : role === 'target' || role === 'shared' ? 100 : isEvidence ? 76 : isDemoFocus || isCore ? 98 : 72,
    nodeShape: isEvidence ? 1 : 0,
    x: typeof node.properties?.x === 'number' ? node.properties.x : undefined,
    y: typeof node.properties?.y === 'number' ? node.properties.y : undefined,
    fixed: Boolean(node.properties?.fixed),
  };
}

function toRelationLine(edge: GraphEdge) {
  const count = edge.properties?.count ? ` x${edge.properties.count}` : '';
  const amount = edge.properties?.amount_total ? ` ￥${edge.properties.amount_total}` : '';
  const main = isMainRelation(edge);
  const isDemoFocus = demoFocusEdgeIds.value.has(edge.edge_id);
  const role = demoEdgeRoles.value.get(edge.edge_id);
  const pathColor = role?.startsWith('路径') ? pathPalette(role) : '';
  return {
    id: edge.edge_id,
    from: edge.source_id,
    to: edge.target_id,
    text: role?.startsWith('路径') ? `${role}：${trim(edge.relation, 10)}` : main || isDemoFocus ? trim(`${edge.relation}${count}${amount}`, 24) : '',
    data: edge,
    color: pathColor || (isDemoFocus ? edgeColor(edge) : edgeColor(edge)),
    lineWidth: role?.startsWith('路径') ? 4.2 : isDemoFocus ? 3.8 : main ? (edge.properties?.count && Number(edge.properties.count) > 1 ? 2.8 : 2.1) : 0.9,
    opacity: role === '二跳关系' ? 0.42 : isDemoFocus || main ? 1 : 0.32,
  };
}

function relationText(edge: GraphEdge) {
  const source = nodeMap.value.get(edge.source_id)?.label || edge.source_id;
  const target = nodeMap.value.get(edge.target_id)?.label || edge.target_id;
  const count = edge.properties?.count ? ` x${edge.properties.count}` : '';
  return `${source} --${edge.relation}${count}--> ${target}`;
}

function onNodeClick(node: { data?: unknown }) {
  if (!node.data) return;
  const data = node.data as GraphNode;
  selectedKind.value = 'node';
  selectedNode.value = data;
  selectedEdge.value = null;
  selectedIndexValue.value = `node:${data.node_id}`;
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

function onLineClick(line: { data?: unknown }) {
  if (!line.data) return;
  const data = line.data as GraphEdge;
  selectedKind.value = 'edge';
  selectedEdge.value = data;
  selectedNode.value = null;
  selectedIndexValue.value = `edge:${data.edge_id}`;
}

function nodeColor(node: GraphNode) {
  if (node.type === 'evidence') return '#dff7f3';
  if (itemTags(node).includes('account')) return '#fef3c7';
  if (itemTags(node).includes('call_record')) return '#dbeafe';
  if (itemTags(node).includes('law_document')) return '#ccfbf1';
  if (itemTags(node).includes('organization')) return '#e2e8f0';
  if (itemTags(node).includes('person')) return '#fee2e2';
  if (itemTags(node).includes('duty_behavior')) return '#ede9fe';
  return '#f8fafc';
}

function nodeBorderColor(node: GraphNode) {
  if (itemTags(node).includes('alias_candidate')) return '#f59e0b';
  if (node.type === 'evidence') return '#0f766e';
  if (itemTags(node).includes('account')) return '#d97706';
  if (itemTags(node).includes('call_record')) return '#2563eb';
  if (itemTags(node).includes('law_document')) return '#0f766e';
  if (itemTags(node).includes('organization')) return '#475569';
  if (itemTags(node).includes('person')) return '#dc2626';
  if (itemTags(node).includes('duty_behavior')) return '#7c3aed';
  return '#64748b';
}

function edgeColor(edge: GraphEdge) {
  if (isFundEdge(edge)) return '#f59e0b';
  if (/电话|通话|短信|联系|微信/.test(edge.relation)) return '#3b82f6';
  if (isSubjectiveEdge(edge)) return '#ef4444';
  if (isDutyEdge(edge)) return '#8b5cf6';
  if (/证据|文书|决定|通知|报告|笔录|鉴定/.test(edge.relation)) return '#10b981';
  if (/时间|日期|发生|形成/.test(edge.relation)) return '#64748b';
  return '#94a3b8';
}

function demoNodeStyle(role?: DemoRole) {
  if (role === 'seed') return { bg: '#fff7ed', border: '#ea580c', width: 5 };
  if (role === 'peer') return { bg: '#eff6ff', border: '#2563eb', width: 5 };
  if (role === 'hop1') return { bg: '#fef3c7', border: '#f59e0b', width: 3.8 };
  if (role === 'hop2') return { bg: '#f8fafc', border: '#94a3b8', width: 2 };
  if (role === 'path') return { bg: '#f5f3ff', border: '#8b5cf6', width: 3.2 };
  if (role === 'target') return { bg: '#ecfdf5', border: '#10b981', width: 4.4 };
  if (role === 'shared') return { bg: '#fee2e2', border: '#dc2626', width: 4.8 };
  if (role === 'groupA') return { bg: '#eff6ff', border: '#3b82f6', width: 2.8 };
  if (role === 'groupB') return { bg: '#fff7ed', border: '#f97316', width: 2.8 };
  return {};
}

function pathPalette(role: string) {
  const palettes = ['#ef4444', '#3b82f6', '#10b981', '#8b5cf6', '#f59e0b'];
  const match = role.match(/\d+/);
  const index = match ? Number(match[0]) - 1 : 0;
  return palettes[((index % palettes.length) + palettes.length) % palettes.length];
}

function isMainRelation(edge: GraphEdge) {
  return isFundEdge(edge) || isDutyEdge(edge) || isSubjectiveEdge(edge) || /电话|通话|短信|请托|指派|批准|释放|调解|拘留|立案|收受|转账/.test(edge.relation);
}

function nodeDegree(nodeId: string) {
  return graph.value.edges.reduce((count, edge) => count + Number(edge.source_id === nodeId || edge.target_id === nodeId), 0);
}

function trim(text: string, length: number) {
  return text.length > length ? `${text.slice(0, length)}...` : text;
}

function makeCheck(title: string, description: string, passed: boolean) {
  return { key: title, title, description, status: passed ? 'ok' : 'gap', label: passed ? '已有支撑' : '待补强' };
}

function emptyEvidenceMap(): EvidenceMap {
  return { case_id: activeCaseId.value, documents: [], passages: [], triples: [], document_edges: [], passage_edges: [], containment_edges: [], warnings: [] };
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
    linear-gradient(90deg, rgba(15, 118, 110, 0.035) 0 1px, transparent 1px 100%),
    linear-gradient(180deg, rgba(15, 23, 42, 0.035) 0 1px, transparent 1px 100%),
    radial-gradient(circle at 20% 20%, rgba(15, 118, 110, 0.08), transparent 28%),
    radial-gradient(circle at 80% 60%, rgba(79, 70, 229, 0.08), transparent 24%),
    #f8fafc;
  background-size: 46px 46px, 46px 46px, auto, auto, auto;
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
  width: min(520px, calc(100% - 32px));
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
.map-hint {
  margin-top: 8px;
  color: #475569;
  font-size: 12px;
  line-height: 1.5;
}
.mini-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}
.mini-legend span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  background: #ffffff;
  color: #334155;
  padding: 4px 8px;
  font-size: 11px;
  font-weight: 800;
}
.mini-legend span::before {
  content: '';
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: var(--legend-color);
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
  margin: 8px 0 12px;
  accent-color: #0f766e;
}
.timeline:disabled {
  opacity: 0.45;
}
.timeline-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  color: #334155;
  font-size: 12px;
  font-weight: 900;
}
.timeline-toggle input {
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
.graph-index {
  display: grid;
  gap: 6px;
  margin-top: 10px;
}
.graph-index label {
  color: #475569;
  font-size: 12px;
  font-weight: 900;
}
.graph-index select {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #0f172a;
  padding: 8px 10px;
  font-size: 13px;
  font-weight: 800;
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
  grid-template-columns: repeat(2, 1fr);
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
.legend-list {
  display: grid;
  gap: 7px;
  margin-top: 10px;
}
.legend-list div {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #cbd5e1;
  font-size: 12px;
  font-weight: 800;
}
.legend-list i {
  width: 22px;
  height: 4px;
  border-radius: 999px;
}
.action-list {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #23324b;
}
.action-list strong {
  width: 100%;
  color: #ffffff;
  font-size: 12px;
}
.action-list button {
  border: 1px solid #2f4567;
  border-radius: 999px;
  background: #0b1220;
  color: #cbd5e1;
  padding: 5px 8px;
  font-size: 11px;
  font-weight: 800;
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
