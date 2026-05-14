<template>
  <div class="graph-page">
    <section class="graph-topbar panel">
      <div>
        <div class="eyebrow">案件证据地图 / {{ currentLayer?.label || layerLabel }}</div>
        <h2 class="page-title">{{ currentLayer?.label || layerLabel }}</h2>
        <p class="muted">按当前图层查看证据结构；图层切换在左侧栏完成。</p>
      </div>
      <div class="graph-search">
        <input
          v-model="searchQuery"
          class="field graph-search-input"
          :placeholder="searchPlaceholder"
          @focus="searchOpen = true"
          @input="searchOpen = true"
          @blur="closeSearchLater"
          @keydown.enter.prevent="focusFirstSuggestion"
        />
        <div v-if="searchOpen && searchSuggestions.length" class="graph-search-menu">
          <button
            v-for="node in searchSuggestions"
            :key="node.id"
            type="button"
            class="graph-search-option"
            @mousedown.prevent="focusSearchNode(node)"
          >
            <strong>{{ node.label || node.id }}</strong>
            <span>{{ suggestionMeta(node) }}</span>
          </button>
        </div>
      </div>
      <div class="actions">
        <button class="btn" :class="{ primary: layoutMode === 'tree' }" @click="layoutMode = 'tree'">树形</button>
        <button class="btn" :class="{ primary: layoutMode === 'force' }" @click="layoutMode = 'force'">力导</button>
        <button class="btn" :disabled="loading || !g6Nodes.length" @click="exportGraph">导出截图</button>
      </div>
    </section>

    <div v-if="error" class="error-state">
      <h2>证据地图加载失败</h2>
      <p class="muted">{{ error }}</p>
      <button class="btn primary" style="margin-top: 12px;" @click="loadMap">重试</button>
    </div>

    <section v-else class="graph-workspace">
      <div class="graph-canvas panel">
        <div v-if="loading" class="empty-state">
          <h2>正在加载案件证据地图...</h2>
        </div>
        <div v-else-if="!nodes.length" class="empty-state">
          <h2>当前图层暂无数据</h2>
          <p class="muted">可以切换其他图层，或重新构建证据地图。</p>
        </div>
        <G6EvidenceGraph
          v-else
          ref="g6Ref"
          :nodes="g6Nodes"
          :lines="g6Lines"
          :layer="activeLayer"
          :layout-mode="layoutMode"
          @node-click="selectG6Node"
          @line-click="selectG6Edge"
        />
        <LegendPanel v-if="activeLayer !== 'raw'" :legend="currentLayer?.legend" :layer="activeLayer" />
      </div>

      <aside class="graph-side panel">
        <section>
          <h3 class="section-title">对象详情</h3>
          <div v-if="!selected" class="side-empty">
            <strong>未选择对象</strong>
            <p class="muted">点击图中的节点或关系，查看详细信息。</p>
          </div>
          <div v-else class="detail-list">
            <div><span>类型</span><strong>{{ selected.kind === 'node' ? '节点' : '关系' }}</strong></div>
            <div><span>ID</span><strong>{{ selected.item.id }}</strong></div>
            <div v-if="selected.kind === 'node'"><span>名称</span><strong>{{ selected.item.label }}</strong></div>
            <div v-if="selected.kind === 'node'"><span>节点类型</span><strong>{{ selected.item.type || '-' }}</strong></div>
            <template v-if="selected.kind === 'edge'">
              <div><span>起点</span><strong>{{ selected.item.source }}</strong></div>
              <div><span>终点</span><strong>{{ selected.item.target }}</strong></div>
              <div><span>关系</span><strong>{{ selected.item.label || selected.item.type || '-' }}</strong></div>
            </template>
            <pre v-if="selected.item.properties" class="properties-pre">{{ pretty(selected.item.properties) }}</pre>
          </div>
        </section>

        <section class="raw-edit" v-if="isRawEditable">
          <h3 class="section-title">原始图谱维护</h3>
          <p class="muted">仅原始图谱层支持维护事实关系。文件证据图和片段证据图保持只读。</p>

          <div class="edit-block">
            <h4>{{ selected?.kind === 'node' ? '编辑节点' : '新增节点' }}</h4>
            <input v-model="nodeForm.label" class="field" placeholder="节点名称" />
            <input v-model="nodeForm.type" class="field" placeholder="节点类型，例如 person" />
            <div class="actions">
              <button class="btn primary" @click="saveNode">{{ selected?.kind === 'node' ? '保存节点' : '新增节点' }}</button>
              <button v-if="selected?.kind === 'node'" class="btn danger" @click="deleteNode">删除节点</button>
            </div>
          </div>

          <div class="edit-block">
            <h4>{{ selected?.kind === 'edge' ? '编辑关系' : '新增关系' }}</h4>
            <input v-model="edgeForm.source" class="field" placeholder="起点节点 ID" />
            <input v-model="edgeForm.target" class="field" placeholder="终点节点 ID" />
            <input v-model="edgeForm.label" class="field" placeholder="关系说明" />
            <input v-model="edgeForm.type" class="field" placeholder="关系类型" />
            <div class="actions">
              <button class="btn primary" @click="saveEdge">{{ selected?.kind === 'edge' ? '保存关系' : '新增关系' }}</button>
              <button v-if="selected?.kind === 'edge'" class="btn danger" @click="deleteEdge">删除关系</button>
            </div>
          </div>
        </section>

        <section v-else class="readonly-note">
          <strong>只读图层</strong>
          <p class="muted">该图层用于查看证据结构，不支持直接编辑。如需维护事实关系，请切换到原始图谱层。</p>
        </section>
      </aside>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import G6EvidenceGraph, { type G6GraphLine, type G6GraphNode } from '../components/G6EvidenceGraph.vue';
import LegendPanel from '../components/LegendPanel.vue';
import { backendApi, type EvidenceLayer, type GraphEdge, type GraphNode } from '../api/backend';

type LayerKey = 'document' | 'passage' | 'raw';

const route = useRoute();
const router = useRouter();
const caseId = computed(() => String(route.params.caseId || localStorage.getItem('active_case_id') || ''));
const activeLayer = computed<LayerKey>(() => {
  const value = String(route.query.layer || 'document');
  return value === 'passage' || value === 'raw' ? value : 'document';
});

const loading = ref(false);
const error = ref('');
const layers = ref<Record<LayerKey, EvidenceLayer> | null>(null);
const layoutMode = ref<'tree' | 'force'>('tree');
const selected = ref<{ kind: 'node'; item: GraphNode } | { kind: 'edge'; item: GraphEdge } | null>(null);
const g6Ref = ref<InstanceType<typeof G6EvidenceGraph> | null>(null);
const searchQuery = ref('');
const searchOpen = ref(false);
const nodeForm = reactive({ label: '', type: 'person' });
const edgeForm = reactive({ source: '', target: '', label: '', type: 'fact_relation' });

const currentLayer = computed(() => layers.value?.[activeLayer.value]);
const layerLabel = computed(() => ({ document: '文件证据图', passage: '片段证据图', raw: '原始图谱层' }[activeLayer.value]));
const nodes = computed(() => currentLayer.value?.nodes || []);
const nodeIds = computed(() => new Set(nodes.value.map((node) => node.id)));
const visibleEdges = computed(() => (currentLayer.value?.edges || []).filter((edge) => nodeIds.value.has(edge.source) && nodeIds.value.has(edge.target)));
const isRawEditable = computed(() => activeLayer.value === 'raw' && currentLayer.value?.editable);

const g6Nodes = computed<G6GraphNode[]>(() => nodes.value.map(toG6Node));
const g6Lines = computed<G6GraphLine[]>(() => visibleEdges.value.map(toG6Line));
const searchPlaceholder = computed(() => {
  if (activeLayer.value === 'document') return '搜索文件、阶段、证明事项';
  if (activeLayer.value === 'passage') return '搜索片段、实体、原文摘要';
  return '搜索人物、账户、机构、事件节点';
});
const searchSuggestions = computed(() => {
  const query = normalizeText(searchQuery.value);
  const candidates = [...nodes.value]
    .filter((node) => !query || searchableText(node).includes(query))
    .sort((a, b) => searchScore(b, query) - searchScore(a, query));
  return candidates.slice(0, 10);
});

onMounted(loadMap);
watch(() => route.query.layer, () => {
  selected.value = null;
  searchQuery.value = '';
  searchOpen.value = false;
  syncRouteLayer();
});
watch(selected, syncForms);

async function loadMap() {
  if (!caseId.value) return;
  loading.value = true;
  error.value = '';
  try {
    const data = await backendApi.getEvidenceMap(caseId.value);
    layers.value = data.layers || null;
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    loading.value = false;
  }
}

function syncRouteLayer() {
  if (!['document', 'passage', 'raw'].includes(String(route.query.layer || ''))) {
    router.replace({ query: { ...route.query, layer: 'document' } });
  }
}

function toG6Node(node: GraphNode): G6GraphNode {
  const shapeRect = activeLayer.value !== 'raw' || node.type === 'document' || node.type === 'passage';
  const label = node.label || node.id;
  const typeColor = nodeColor(node);
  return {
    id: node.id,
    text: label,
    data: node,
    color: typeColor.fill,
    borderColor: typeColor.stroke,
    borderWidth: selected.value?.kind === 'node' && selected.value.item.id === node.id ? 3.5 : 1.8,
    width: shapeRect ? Math.max(180, Math.min(320, label.length * 10 + 44)) : 78,
    height: shapeRect ? (activeLayer.value === 'passage' ? 96 : 82) : 78,
    nodeShape: shapeRect ? 1 : 0,
  };
}

function toG6Line(edge: GraphEdge): G6GraphLine {
  return {
    id: edge.id,
    from: edge.source,
    to: edge.target,
    text: edge.label || edge.type || '',
    data: edge,
    color: edgeColor(edge),
    lineWidth: selected.value?.kind === 'edge' && selected.value.item.id === edge.id ? 3.2 : 1.4,
    opacity: activeLayer.value === 'raw' ? 0.74 : 0.82,
  };
}

function selectG6Node(payload: { data?: unknown; id: string }) {
  const item = (payload.data as GraphNode | undefined) || nodes.value.find((node) => node.id === payload.id);
  if (item) selectNode(item);
}

function selectG6Edge(payload: { data?: unknown; id: string }) {
  const item = (payload.data as GraphEdge | undefined) || visibleEdges.value.find((edge) => edge.id === payload.id);
  if (item) selectEdge(item);
}

function selectNode(node: GraphNode) {
  selected.value = { kind: 'node', item: node };
}

function selectEdge(edge: GraphEdge) {
  selected.value = { kind: 'edge', item: edge };
}

async function focusSearchNode(node: GraphNode) {
  searchQuery.value = node.label || node.id;
  searchOpen.value = false;
  selectNode(node);
  await nextTick();
  await g6Ref.value?.focusElement?.(node.id);
}

function focusFirstSuggestion() {
  const first = searchSuggestions.value[0];
  if (first) void focusSearchNode(first);
}

function closeSearchLater() {
  window.setTimeout(() => {
    searchOpen.value = false;
  }, 140);
}

function normalizeText(value: unknown) {
  return String(value ?? '').trim().toLowerCase();
}

function searchableText(node: GraphNode) {
  const props = node.properties || {};
  return normalizeText([
    node.id,
    node.label,
    node.type,
    node.layer,
    node.summary,
    props.doc_type,
    props.process_stage,
    props.proof_purpose,
    props.text_preview,
    props.entities,
    props.evidence_id,
  ].join(' '));
}

function searchScore(node: GraphNode, query: string) {
  const label = normalizeText(node.label || node.id);
  let score = 0;
  if (query && label.includes(query)) score += 80;
  if (query && normalizeText(node.id).includes(query)) score += 40;
  if (activeLayer.value === 'document') {
    score += node.type === 'document' ? 40 : 0;
    score += node.properties?.process_stage ? 14 : 0;
    score += node.properties?.proof_purpose ? 10 : 0;
  } else if (activeLayer.value === 'passage') {
    score += node.type === 'passage' ? 40 : 0;
    score += Array.isArray(node.properties?.entities) ? 18 : 0;
    score += Number(node.properties?.triple_count || 0);
  } else {
    const type = normalizeText(node.type);
    if (type.includes('person')) score += 60;
    if (type.includes('account') || type.includes('money') || type.includes('transaction')) score += 44;
    if (type.includes('organization')) score += 34;
    if (type.includes('event') || type.includes('document')) score += 22;
  }
  return score;
}

function suggestionMeta(node: GraphNode) {
  const props = node.properties || {};
  if (activeLayer.value === 'document') {
    return [props.doc_type, props.process_stage, node.type].filter(Boolean).join(' / ') || '文件';
  }
  if (activeLayer.value === 'passage') {
    const count = props.triple_count != null ? `${props.triple_count} 条关系` : '';
    const entities = Array.isArray(props.entities) ? props.entities.slice(0, 3).join('、') : '';
    return [count, entities].filter(Boolean).join(' / ') || '片段';
  }
  return node.type || '节点';
}

function nodeColor(node: GraphNode) {
  const type = String(node.type || '').toLowerCase();
  if (activeLayer.value === 'document' || type.includes('document')) return { fill: '#ecfdf5', stroke: '#0f766e' };
  if (activeLayer.value === 'passage' || type.includes('passage')) return { fill: '#eff6ff', stroke: '#2563eb' };
  if (type.includes('person')) return { fill: '#fff7ed', stroke: '#ea580c' };
  if (type.includes('account') || type.includes('money') || type.includes('transaction')) return { fill: '#fffbeb', stroke: '#d97706' };
  if (type.includes('organization')) return { fill: '#f0fdfa', stroke: '#0f766e' };
  if (type.includes('time')) return { fill: '#f8fafc', stroke: '#64748b' };
  return { fill: '#ffffff', stroke: '#64748b' };
}

function edgeColor(edge: GraphEdge) {
  const value = `${edge.type || ''} ${edge.label || ''}`.toLowerCase();
  if (/转账|资金|金额|money|bank|transaction/.test(value)) return '#f59e0b';
  if (/通话|短信|通信|call|message/.test(value)) return '#3b82f6';
  if (/证据|文书|document|contains|extract/.test(value)) return '#10b981';
  if (/审批|批准|指派|职务|authority|duty/.test(value)) return '#8b5cf6';
  if (/人物|亲属|同事|关系|person/.test(value)) return '#ef4444';
  return '#64748b';
}

function syncForms() {
  if (selected.value?.kind === 'node') {
    nodeForm.label = selected.value.item.label || '';
    nodeForm.type = selected.value.item.type || 'person';
  }
  if (selected.value?.kind === 'edge') {
    edgeForm.source = selected.value.item.source || '';
    edgeForm.target = selected.value.item.target || '';
    edgeForm.label = selected.value.item.label || '';
    edgeForm.type = selected.value.item.type || 'fact_relation';
  }
}

async function saveNode() {
  const isUpdate = selected.value?.kind === 'node';
  const id = isUpdate ? selected.value.item.id : `${nodeForm.type || 'node'}:${Date.now().toString(36)}`;
  await runAction(isUpdate ? 'update_node' : 'create_node', { id, label: nodeForm.label, type: nodeForm.type, properties: {} });
}

async function deleteNode() {
  if (selected.value?.kind !== 'node') return;
  if (!confirm('删除节点会影响相关关系，是否确认？')) return;
  await runAction('delete_node', { id: selected.value.item.id });
}

async function saveEdge() {
  const isUpdate = selected.value?.kind === 'edge';
  const id = isUpdate ? selected.value.item.id : `edge:${Date.now().toString(36)}`;
  await runAction(isUpdate ? 'update_edge' : 'create_edge', { id, source: edgeForm.source, target: edgeForm.target, label: edgeForm.label, type: edgeForm.type, properties: {} });
}

async function deleteEdge() {
  if (selected.value?.kind !== 'edge') return;
  if (!confirm('删除关系后将从原始图谱中移除，是否确认？')) return;
  await runAction('delete_edge', { id: selected.value.item.id });
}

async function runAction(action: string, payload: Record<string, unknown>) {
  error.value = '';
  try {
    await backendApi.runRawGraphAction(caseId.value, action, payload);
    selected.value = null;
    await loadMap();
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
}

async function exportGraph() {
  try {
    await g6Ref.value?.exportPng?.(`${caseId.value}_${layerLabel.value}.png`);
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
}

function pretty(value: unknown) {
  return JSON.stringify(value, null, 2);
}
</script>

<style scoped>
.graph-page {
  min-height: 100%;
  padding: 20px;
  display: grid;
  gap: 16px;
}
.graph-topbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.graph-search {
  position: relative;
  min-width: 280px;
  max-width: 420px;
  flex: 1;
}
.graph-search-input {
  width: 100%;
  min-height: 40px;
  background: #f8fafc;
}
.graph-search-menu {
  position: absolute;
  z-index: 20;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  max-height: 320px;
  overflow: auto;
  border: 1px solid var(--line-strong);
  border-radius: 10px;
  background: #ffffff;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.16);
  padding: 6px;
}
.graph-search-option {
  width: 100%;
  border: 0;
  border-radius: 8px;
  background: transparent;
  text-align: left;
  padding: 10px;
  display: grid;
  gap: 3px;
  color: var(--text);
}
.graph-search-option:hover {
  background: var(--primary-soft);
}
.graph-search-option strong {
  font-size: 13px;
  line-height: 1.35;
}
.graph-search-option span {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.35;
}
.graph-workspace {
  min-height: 680px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 330px;
  gap: 16px;
}
.graph-canvas {
  min-height: 680px;
  padding: 0;
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  overflow: hidden;
}
.graph-canvas :deep(.g6-evidence-graph) {
  width: 100%;
  height: 620px;
  min-height: 620px;
  background:
    linear-gradient(#eef2f7 1px, transparent 1px),
    linear-gradient(90deg, #eef2f7 1px, transparent 1px),
    #fbfdff;
  background-size: 28px 28px;
}
.graph-side {
  min-height: 680px;
  overflow: auto;
  display: grid;
  gap: 16px;
  align-content: start;
}
.side-empty {
  border: 1px dashed var(--line-strong);
  border-radius: 8px;
  padding: 18px;
  background: #f8fafc;
}
.detail-list {
  display: grid;
  gap: 8px;
}
.detail-list div {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px;
  background: #f8fafc;
}
.detail-list span {
  display: block;
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 4px;
}
.detail-list strong {
  word-break: break-word;
}
.properties-pre {
  white-space: pre-wrap;
  word-break: break-word;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #0f172a;
  color: #e2e8f0;
  padding: 10px;
  font-size: 12px;
}
.raw-edit,
.readonly-note,
.edit-block {
  border-top: 1px solid var(--line);
  padding-top: 14px;
  display: grid;
  gap: 10px;
}
.edit-block h4 {
  margin: 0;
}
</style>
