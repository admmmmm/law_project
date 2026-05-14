<template>
  <div ref="containerRef" class="g6-evidence-graph"></div>
</template>

<script setup lang="ts">
import { Graph, EdgeEvent, NodeEvent } from '@antv/g6';
import { markRaw, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue';

type LayerKind = 'document' | 'passage' | 'raw';
type G6LayoutMode = 'tree' | 'force' | string;
type InteractionProfile = 'safe' | 'standard' | 'force' | 'full';

export interface G6GraphNode {
  id: string;
  text?: string;
  data?: unknown;
  color?: string;
  borderColor?: string;
  borderWidth?: number;
  width?: number;
  height?: number;
  nodeShape?: number;
  x?: number;
  y?: number;
  fixed?: boolean;
}

export interface G6GraphLine {
  id?: string;
  from: string;
  to: string;
  text?: string;
  data?: unknown;
  color?: string;
  lineWidth?: number;
  opacity?: number;
}

const props = defineProps<{
  nodes: G6GraphNode[];
  lines: G6GraphLine[];
  layer: LayerKind;
  layoutMode?: G6LayoutMode;
}>();

const emit = defineEmits<{
  nodeClick: [node: { data?: unknown; id: string }];
  lineClick: [line: { data?: unknown; id: string }];
}>();

const containerRef = ref<HTMLDivElement | null>(null);
const graphRef = shallowRef<any>(null);
let renderSeq = 0;
let lastRenderSignature = '';
let lastPerfSignature = '';
let lastProfileSignature = '';
let renderQueue = Promise.resolve();
let disposed = false;
let fitTimer: number | null = null;
let fallbackProfile: InteractionProfile | null = null;
let pointerErrorCount = 0;

const G6_DEBUG =
  import.meta.env.DEV || (typeof window !== 'undefined' && window.localStorage?.getItem('g6_debug') === 'true');

onMounted(async () => {
  await nextTick();
  window.addEventListener('error', onWindowError);
  scheduleRender();
});

onBeforeUnmount(() => {
  disposed = true;
  window.removeEventListener('error', onWindowError);
  cleanupGraph();
});

watch(
  () => [props.nodes, props.lines, props.layer, props.layoutMode],
  () => scheduleRender(),
  { deep: false, flush: 'post' },
);

defineExpose({
  focusElement,
  resize: () => graphRef.value?.resize?.(),
  exportPng,
});

function scheduleRender() {
  const seq = ++renderSeq;
  renderQueue = renderQueue
    .catch(() => undefined)
    .then(async () => {
      await nextTick();
      if (disposed || seq !== renderSeq) return;
      await renderGraph(seq);
    })
    .catch((error) => {
      if (!disposed) console.warn('[G6EvidenceGraph:renderError]', error);
    });
}

async function renderGraph(seq: number) {
  if (!containerRef.value) return;
  const totalStart = performance.now();
  const normalizeStart = performance.now();
  const safeData = buildSafeGraphData(props.nodes, props.lines);
  const normalizeMs = performance.now() - normalizeStart;

  const validateStart = performance.now();
  validateG6GraphData(safeData);
  const validateMs = performance.now() - validateStart;

  const data = {
    nodes: safeData.nodes,
    edges: safeData.edges,
  };
  const layout = g6Layout();
  const interaction = resolveInteractionProfile({
    activeLayer: props.layer,
    layoutType: layout.type,
    nodes: data.nodes.length,
    edges: data.edges.length,
  });
  const behaviorList = buildG6Behaviors(interaction.profile);
  const pluginList = buildG6Plugins(interaction.profile, data.nodes.length, data.edges.length);
  logInteractionProfile(interaction, behaviorList, pluginList);
  const renderSignature = `${props.layer}:${props.layoutMode}:${data.nodes.length}:${data.edges.length}`;
  if (G6_DEBUG) {
    console.log('[G6EvidenceGraph:beforeRender]', {
      activeLayer: props.layer,
      layoutMode: props.layoutMode,
      layoutType: layout.type,
      nodes: data.nodes.length,
      edges: data.edges.length,
    });
  }

  cleanupGraph();
  if (disposed || seq !== renderSeq) return;
  await nextTick();
  if (!containerRef.value || disposed || seq !== renderSeq) return;

  const createStart = performance.now();
  const graph = markRaw(
    new Graph({
      container: containerRef.value,
      autoResize: true,
      data,
      node: {
        type: (datum: any) => datum.data?.shape || 'circle',
        style: (datum: any) => datum.data?.style || {},
        state: {
          selected: {
            stroke: '#0f766e',
            lineWidth: 4,
            halo: true,
            haloStroke: '#99f6e4',
            haloLineWidth: 12,
          },
          active: {
            stroke: '#2563eb',
            lineWidth: 3,
          },
        },
      },
      edge: {
        type: 'line',
        style: (datum: any) => datum.data?.style || {},
        state: {
          selected: {
            stroke: '#0f766e',
            lineWidth: 4,
          },
          active: {
            stroke: '#2563eb',
            lineWidth: 3,
          },
        },
      },
      layout,
      animation: false,
      behaviors: behaviorList,
      plugins: pluginList,
    }),
  );
  graphRef.value = graph;
  const createGraphMs = performance.now() - createStart;
  bindEvents(graph);

  const renderStart = performance.now();
  await graph.render();
  const renderMs = performance.now() - renderStart;
  if (disposed || seq !== renderSeq || graphRef.value !== graph) return;
  await fitGraphView(graph, seq);
  const previousSignature = lastRenderSignature;
  lastRenderSignature = renderSignature;
  const renderedNodes = graph.getNodeData?.() || [];
  if (G6_DEBUG) {
    console.log('[G6EvidenceGraph:afterLayout]', {
      activeLayer: props.layer,
      layoutMode: props.layoutMode,
      layoutType: layout.type,
      renderSignature,
      previousSignature,
      nodes: renderedNodes.length,
      firstRenderedNodes: renderedNodes.slice(0, 5).map(renderedNodePosition),
    });
  }

  if (G6_DEBUG && lastPerfSignature !== renderSignature) {
    lastPerfSignature = renderSignature;
    console.log('[G6EvidenceGraph:perf]', {
      activeLayer: props.layer,
      layoutMode: props.layoutMode,
      layoutType: layout.type,
      interactionProfile: interaction.profile,
      nodes: data.nodes.length,
      edges: data.edges.length,
      normalizeMs: Math.round(normalizeMs),
      validateMs: Math.round(validateMs),
      createGraphMs: Math.round(createGraphMs),
      renderMs: Math.round(renderMs),
      layoutMs: Math.round(renderMs),
      totalMs: Math.round(performance.now() - totalStart),
      behaviors: behaviorList.map(behaviorName),
      plugins: pluginList.map(pluginName),
    });
  }
}

async function fitGraphView(graph: any, seq: number) {
  if (fitTimer) {
    window.clearTimeout(fitTimer);
    fitTimer = null;
  }
  await new Promise((resolve) => {
    fitTimer = window.setTimeout(resolve, props.layoutMode === 'force' ? 80 : 20);
  });
  fitTimer = null;
  if (disposed || seq !== renderSeq || graphRef.value !== graph) return;
  await graph.fitView?.({ padding: 42, duration: 0 }).catch((error: unknown) => {
    console.warn('[G6EvidenceGraph:fitViewError]', error);
  });
}

function cleanupGraph() {
  if (fitTimer) {
    window.clearTimeout(fitTimer);
    fitTimer = null;
  }
  const graph = graphRef.value;
  graphRef.value = null;
  if (!graph) return;
  try {
    graph.destroy?.();
  } catch (error) {
    console.warn('[G6EvidenceGraph] graph.destroy failed', error);
  }
}

function renderedNodePosition(node: any) {
  const position = graphRef.value?.getElementPosition?.(node.id) || [];
  return {
    id: node.id,
    x: Math.round(position[0] ?? node.style?.x ?? node.x ?? 0),
    y: Math.round(position[1] ?? node.style?.y ?? node.y ?? 0),
    collideRadius: node.data?.size,
  };
}

function bindEvents(graph: any) {
  graph.on(NodeEvent.CLICK, (event: any) => {
    try {
      const id = eventElementId(event);
      if (!id) return;
      graph.setElementState?.(id, ['selected']).catch?.(() => undefined);
      const datum = graph.getNodeData(id);
      emit('nodeClick', { id: String(id), data: datum?.data?.raw });
    } catch (error) {
      logEventError('node:click', event, error);
    }
  });
  graph.on(EdgeEvent.CLICK, (event: any) => {
    try {
      const id = eventElementId(event);
      if (!id) return;
      graph.setElementState?.(id, ['selected']).catch?.(() => undefined);
      const datum = graph.getEdgeData(id);
      emit('lineClick', { id: String(id), data: datum?.data?.raw });
    } catch (error) {
      logEventError('edge:click', event, error);
    }
  });
  graph.on(NodeEvent.POINTER_ENTER, (event: any) => setElementActive(graph, event, true, 'node:pointerenter'));
  graph.on(NodeEvent.POINTER_LEAVE, (event: any) => setElementActive(graph, event, false, 'node:pointerleave'));
  graph.on(EdgeEvent.POINTER_ENTER, (event: any) => setElementActive(graph, event, true, 'edge:pointerenter'));
  graph.on(EdgeEvent.POINTER_LEAVE, (event: any) => setElementActive(graph, event, false, 'edge:pointerleave'));
}

function eventElementId(event: any) {
  return event?.target?.id || event?.target?.get?.('id') || event?.target?.attributes?.id;
}

function eventTargetType(event: any) {
  return event?.targetType || event?.target?.type || event?.target?.attributes?.type || '';
}

function setElementActive(graph: any, event: any, active: boolean, eventName: string) {
  try {
    const id = eventElementId(event);
    if (!id) return;
    graph.setElementState?.(id, active ? ['active'] : []).catch?.(() => undefined);
  } catch (error) {
    logEventError(eventName, event, error);
  }
}

async function focusElement(id: string) {
  if (!graphRef.value || !id) return;
  await graphRef.value.setElementState(id, ['selected'], true).catch(() => undefined);
  await graphRef.value.focusElement(id, { duration: 260 }).catch(() => undefined);
  const zoomResult = graphRef.value.zoomTo?.(1.35, { duration: 180 });
  if (zoomResult && typeof zoomResult.catch === 'function') {
    await zoomResult.catch(() => undefined);
  }
}

async function exportPng(filename = '案件证据地图.png') {
  await nextTick();
  const canvas = containerRef.value?.querySelector('canvas');
  if (!canvas) throw new Error('当前图谱画布还没有准备好。');
  const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/png'));
  if (!blob) throw new Error('当前浏览器无法导出图谱截图。');
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function buildSafeGraphData(inputNodes: G6GraphNode[], inputEdges: G6GraphLine[]) {
  const duplicateNodeIds: string[] = [];
  const seenNodeIds = new Set<string>();
  const normalizedNodes = (Array.isArray(inputNodes) ? inputNodes : [])
    .map((node) => ({ ...node, id: normalizeId(node.id) }))
    .filter((node) => {
      if (!node.id) return false;
      if (seenNodeIds.has(node.id)) {
        duplicateNodeIds.push(node.id);
        return false;
      }
      seenNodeIds.add(node.id);
      return true;
    });

  const nodeIds = new Set(normalizedNodes.map((node) => node.id));
  const invalidEdges: Array<{
    id: string;
    source: string;
    target: string;
    sourceExists: boolean;
    targetExists: boolean;
  }> = [];
  const seenEdgeIds = new Set<string>();
  const duplicateEdgeIds: string[] = [];
  const normalizedEdges = (Array.isArray(inputEdges) ? inputEdges : [])
    .map((line, index) => {
      const source = normalizeId(line.from);
      const target = normalizeId(line.to);
      return {
        ...line,
        id: normalizeId(line.id) || `edge:${source}:${target}:${index}`,
        from: source,
        to: target,
      };
    })
    .filter((line) => {
      const sourceExists = nodeIds.has(line.from);
      const targetExists = nodeIds.has(line.to);
      if (!line.from || !line.to || !sourceExists || !targetExists) {
        invalidEdges.push({
          id: line.id || '',
          source: line.from,
          target: line.to,
          sourceExists,
          targetExists,
        });
        return false;
      }
      if (seenEdgeIds.has(line.id || '')) {
        duplicateEdgeIds.push(line.id || '');
        return false;
      }
      seenEdgeIds.add(line.id || '');
      return true;
    });

  const nodes = normalizedNodes.map((node) => ({
    id: node.id,
    type: node.nodeShape === 1 ? 'rect' : 'circle',
    data: {
      raw: node.data,
      shape: node.nodeShape === 1 ? 'rect' : 'circle',
      size: layoutNodeSize(node),
      style: nodeStyle(node),
    },
    style: {},
  }));

  const edges = normalizedEdges.map((line) => ({
    id: line.id || `edge:${line.from}:${line.to}`,
    source: line.from,
    target: line.to,
    data: {
      raw: line.data,
      style: edgeStyle(line),
    },
  }));

  if (duplicateNodeIds.length || duplicateEdgeIds.length || invalidEdges.length) {
    console.warn('[G6EvidenceGraph:dataRepair]', {
      activeLayer: props.layer,
      layoutMode: props.layoutMode,
      inputNodes: Array.isArray(inputNodes) ? inputNodes.length : 0,
      inputEdges: Array.isArray(inputEdges) ? inputEdges.length : 0,
      outputNodes: nodes.length,
      outputEdges: edges.length,
      duplicateNodeIds: duplicateNodeIds.slice(0, 20),
      duplicateEdgeIds: duplicateEdgeIds.slice(0, 20),
      removedEdges: invalidEdges.length,
      invalidEdges: invalidEdges.slice(0, 20),
    });
  }

  return {
    nodes,
    edges,
    inputNodeCount: Array.isArray(inputNodes) ? inputNodes.length : 0,
    inputEdgeCount: Array.isArray(inputEdges) ? inputEdges.length : 0,
    duplicateNodeIds,
    duplicateEdgeIds,
    invalidEdges,
    removedEdges: invalidEdges.length,
  };
}

function normalizeId(id: unknown) {
  return id == null ? '' : String(id);
}

function validateG6GraphData(data: ReturnType<typeof buildSafeGraphData>) {
  if (!G6_DEBUG) return;
  const nodeIds = new Set<string>();
  const duplicateNodeIds: string[] = [];
  const missingIds: string[] = [];
  for (const node of data.nodes) {
    if (!node.id) missingIds.push('(empty node id)');
    if (nodeIds.has(node.id)) duplicateNodeIds.push(node.id);
    nodeIds.add(node.id);
  }
  const invalidEdges = data.edges
    .filter((edge) => !nodeIds.has(edge.source) || !nodeIds.has(edge.target))
    .map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      sourceExists: nodeIds.has(edge.source),
      targetExists: nodeIds.has(edge.target),
    }));
  const selfLoops = data.edges.filter((edge) => edge.source === edge.target).length;
  const hugePayloadNodes = data.nodes
    .map((node) => ({
      id: node.id,
      bytes: roughJsonSize(node.data?.raw),
    }))
    .filter((item) => item.bytes > 18000)
    .slice(0, 10);
  console.log('[G6EvidenceGraph:validate]', {
    activeLayer: props.layer,
    layoutMode: props.layoutMode,
    renderer: 'G6EvidenceGraph',
    inputNodes: data.inputNodeCount,
    inputEdges: data.inputEdgeCount,
    nodes: data.nodes.length,
    edges: data.edges.length,
    uniqueNodeIds: nodeIds.size,
    duplicateNodeIds: [...data.duplicateNodeIds, ...duplicateNodeIds].slice(0, 20),
    invalidEdges: [...data.invalidEdges, ...invalidEdges].slice(0, 20),
    selfLoops,
    missingIds,
    hugePayloadNodes,
    removedEdges: data.removedEdges,
  });
  if (data.invalidEdges.length || invalidEdges.length) {
    console.warn('[G6EvidenceGraph:invalidEdges]', [...data.invalidEdges, ...invalidEdges].slice(0, 20));
  }
}

function roughJsonSize(value: unknown) {
  try {
    return JSON.stringify(value ?? '').length;
  } catch {
    return 0;
  }
}

function resolveInteractionProfile(context: {
  activeLayer: LayerKind;
  layoutType: string;
  nodes: number;
  edges: number;
}): { profile: InteractionProfile; reason: string } {
  const requested = normalizeRequestedProfile();
  if (fallbackProfile) return { profile: fallbackProfile, reason: 'recent pointer event error fallback' };
  if (requested === 'safe' || requested === 'standard' || requested === 'full') {
    return { profile: requested, reason: `user requested ${requested}` };
  }
  const smallGraph = context.nodes <= 100 && context.edges <= 300;
  if (context.layoutType === 'd3-force' && smallGraph && context.activeLayer !== 'raw') {
    return { profile: 'force', reason: 'small non-raw d3-force graph' };
  }
  return { profile: 'standard', reason: context.layoutType === 'd3-force' ? 'force graph is too large or raw layer' : 'static layout' };
}

function normalizeRequestedProfile(): InteractionProfile | 'auto' {
  const raw = typeof window !== 'undefined' ? window.localStorage?.getItem('g6_interaction_profile') : '';
  if (raw === 'safe' || raw === 'standard' || raw === 'full') return raw;
  return 'auto';
}

function buildG6Behaviors(profile: InteractionProfile) {
  const base = ['drag-canvas', 'zoom-canvas'];
  if (profile === 'safe') return base;
  const standard = [
    ...base,
    {
      type: 'drag-element',
      enable: (event: any) => behaviorTargetIs(event, 'node'),
      hideEdge: 'none',
    },
    {
      type: 'click-select',
      enable: (event: any) => behaviorTargetIs(event, 'node') || behaviorTargetIs(event, 'edge'),
    },
    {
      type: 'hover-activate',
      enable: (event: any) => behaviorTargetIs(event, 'node') || behaviorTargetIs(event, 'edge'),
    },
  ];
  if (profile === 'force') {
    return [
      ...base,
      {
        type: 'drag-element-force',
        enable: (event: any) => behaviorTargetIs(event, 'node'),
        fixed: true,
        hideEdge: 'none',
      },
      {
        type: 'click-select',
        enable: (event: any) => behaviorTargetIs(event, 'node') || behaviorTargetIs(event, 'edge'),
      },
      {
        type: 'hover-activate',
        enable: (event: any) => behaviorTargetIs(event, 'node') || behaviorTargetIs(event, 'edge'),
      },
    ];
  }
  return standard;
}

function behaviorTargetIs(event: any, type: 'node' | 'edge') {
  const targetType = String(event?.targetType || event?.target?.type || event?.target?.attributes?.type || '');
  return targetType === type || targetType.includes(type);
}

function buildG6Plugins(profile: InteractionProfile, nodeCount: number, edgeCount: number) {
  const disabled = typeof window !== 'undefined' && window.localStorage?.getItem('g6_minimap') === 'false';
  const enableMiniMap = !disabled && nodeCount <= 500 && edgeCount <= 1000;
  return enableMiniMap ? ['grid-line', 'minimap'] : ['grid-line'];
}

function logInteractionProfile(
  interaction: { profile: InteractionProfile; reason: string },
  behaviors: unknown[],
  plugins: unknown[],
) {
  const signature = `${props.layer}:${props.layoutMode}:${interaction.profile}:${behaviors.map(behaviorName).join(',')}:${plugins.map(pluginName).join(',')}`;
  if (signature === lastProfileSignature) return;
  lastProfileSignature = signature;
  if (!G6_DEBUG) return;
  console.log('[G6EvidenceGraph:interactionProfile]', {
    activeLayer: props.layer,
    layoutMode: props.layoutMode,
    layoutType: g6Layout().type,
    nodes: props.nodes.length,
    edges: props.lines.length,
    selectedProfile: interaction.profile,
    reason: interaction.reason,
    behaviors: behaviors.map(behaviorName),
    plugins: plugins.map(pluginName),
  });
}

function behaviorName(behavior: any) {
  return typeof behavior === 'string' ? behavior : behavior?.type || 'unknown';
}

function pluginName(plugin: any) {
  return typeof plugin === 'string' ? plugin : plugin?.type || 'unknown';
}

function logEventError(eventName: string, event: any, error: unknown) {
  const err = error instanceof Error ? error : new Error(String(error));
  console.warn('[G6EvidenceGraph:eventError]', {
    eventName,
    activeLayer: props.layer,
    layoutMode: props.layoutMode,
    interactionProfile: fallbackProfile || 'auto',
    targetType: eventTargetType(event),
    targetId: eventElementId(event),
    message: err.message,
    stack: err.stack,
  });
}

function onWindowError(event: ErrorEvent) {
  const message = String(event.message || '');
  const stack = String(event.error?.stack || '');
  if (!/pointermove|onPointerMove|drag-element-force|hover-activate/i.test(`${message}\n${stack}`)) return;
  pointerErrorCount += 1;
  console.warn('[G6EvidenceGraph:eventError]', {
    eventName: 'window:error',
    activeLayer: props.layer,
    layoutMode: props.layoutMode,
    interactionProfile: fallbackProfile || 'auto',
    targetType: '',
    targetId: '',
    message,
    stack,
  });
  if (pointerErrorCount >= 3 && fallbackProfile !== 'safe') {
    fallbackProfile = 'safe';
    console.warn('[G6EvidenceGraph:interactionFallback]', {
      activeLayer: props.layer,
      layoutMode: props.layoutMode,
      reason: 'consecutive pointermove errors',
      fallbackProfile,
    });
    scheduleRender();
  }
}

function nodeStyle(node: G6GraphNode) {
  const isRect = node.nodeShape === 1;
  const size = visualNodeSize(node);
  return {
    size,
    radius: isRect ? 12 : undefined,
    fill: node.color || '#ffffff',
    stroke: node.borderColor || '#64748b',
    lineWidth: node.borderWidth || 1.8,
    shadowColor: 'rgba(15, 23, 42, 0.12)',
    shadowBlur: props.layer === 'raw' ? 8 : 14,
    label: true,
    labelText: node.text || node.id,
    labelPlacement: isRect ? 'center' : 'center',
    labelFill: '#0f172a',
    labelFontSize: props.layer === 'raw' ? 12 : 13,
    labelFontWeight: 800,
    labelWordWrap: true,
    labelMaxWidth: isRect ? Math.max(120, (node.width || 180) - 18) : 76,
    labelTextAlign: 'center',
    labelTextBaseline: 'middle',
  };
}

function edgeStyle(line: G6GraphLine) {
  const hasLabel = Boolean(line.text);
  return {
    stroke: line.color || '#64748b',
    lineWidth: line.lineWidth || 1.2,
    opacity: line.opacity ?? 0.72,
    endArrow: true,
    label: hasLabel,
    labelText: line.text || '',
    labelFontSize: 11,
    labelFill: '#334155',
    labelBackground: true,
    labelBackgroundFill: '#ffffff',
    labelBackgroundOpacity: 0.85,
    labelPadding: [2, 4],
  };
}

function g6Layout() {
  const config = layerLayoutConfig();
  if (props.layoutMode === 'tree') {
    return {
      type: 'dagre',
      rankdir: 'LR',
      nodeSize: nodeSizeAccessor,
      nodesep: config.treeNodeSep,
      ranksep: config.treeRankSep,
      controlPoints: true,
      animation: false,
    };
  }
  return {
    type: 'd3-force',
    animation: false,
    preventOverlap: true,
    collide: {
      radius: nodeSizeAccessor,
      strength: config.collideStrength,
      iterations: config.collideIterations,
    },
    manyBody: {
      strength: config.forceNodeStrength,
      distanceMin: config.forceDistanceMin,
      distanceMax: config.forceDistanceMax,
    },
    link: {
      distance: config.forceLinkDistance,
      strength: config.forceEdgeStrength,
      iterations: 2,
    },
    center: {
      strength: config.centerStrength,
    },
    iterations: config.forceIterations,
    alphaDecay: config.alphaDecay,
    alphaMin: config.alphaMin,
    velocityDecay: config.velocityDecay,
  };
}

function nodeSizeAccessor(datum: any) {
  return datum?.data?.size || datum?.size || 128;
}

function layerLayoutConfig() {
  if (props.layer === 'document') {
    return {
      treeNodeSep: 120,
      treeRankSep: 260,
      forceSpacing: 42,
      forceLinkDistance: 360,
      forceNodeStrength: -560,
      forceEdgeStrength: 0.052,
      forceIterations: 240,
      forceDistanceMin: 80,
      forceDistanceMax: 980,
      collideStrength: 1,
      collideIterations: 5,
      centerStrength: 0.045,
      alphaDecay: 0.085,
      alphaMin: 0.025,
      velocityDecay: 0.72,
    };
  }
  if (props.layer === 'passage') {
    return {
      treeNodeSep: 110,
      treeRankSep: 240,
      forceSpacing: 46,
      forceLinkDistance: 330,
      forceNodeStrength: -720,
      forceEdgeStrength: 0.04,
      forceIterations: 300,
      forceDistanceMin: 96,
      forceDistanceMax: 1100,
      collideStrength: 1,
      collideIterations: 6,
      centerStrength: 0.035,
      alphaDecay: 0.08,
      alphaMin: 0.025,
      velocityDecay: 0.74,
    };
  }
  return {
    treeNodeSep: 150,
    treeRankSep: 260,
    forceSpacing: 62,
    forceLinkDistance: 340,
    forceNodeStrength: -1220,
    forceEdgeStrength: 0.024,
    forceIterations: 380,
    forceDistanceMin: 72,
    forceDistanceMax: 1320,
    collideStrength: 1,
    collideIterations: 7,
    centerStrength: 0.026,
    alphaDecay: 0.075,
    alphaMin: 0.024,
    velocityDecay: 0.78,
  };
}

function visualNodeSize(node: G6GraphNode) {
  const isRect = node.nodeShape === 1;
  const text = node.text || node.id;
  if (isRect) {
    const lineCount = Math.max(1, text.split('\n').length);
    const longestLine = text.split('\n').reduce((max, line) => Math.max(max, line.length), 0);
    const width = Math.max(node.width || 180, Math.min(320, longestLine * 9 + 32));
    const height = Math.max(node.height || 82, Math.min(168, lineCount * 22 + 34));
    return [width, height];
  }
  const base = node.width || 72;
  const textBoost = Math.min(34, Math.max(0, text.length - 8) * 2.2);
  const importantBoost = (node.borderWidth || 0) >= 3 ? 14 : 0;
  return Math.max(72, Math.min(136, base + textBoost + importantBoost));
}

function layoutNodeSize(node: G6GraphNode) {
  const size = visualNodeSize(node);
  if (Array.isArray(size)) {
    const [width, height] = size;
    return Math.ceil(Math.sqrt(width * width + height * height)) + layerPadding();
  }
  return size + layerPadding();
}

function layerPadding() {
  if (props.layer === 'raw') return 34;
  if (props.layer === 'passage') return 42;
  return 46;
}
</script>

<style scoped>
.g6-evidence-graph {
  width: 100%;
  height: 100%;
}

.g6-evidence-graph :deep(.g6-minimap),
.g6-evidence-graph :deep(.g6-minimap-container) {
  right: 16px !important;
  bottom: 16px !important;
  left: auto !important;
  top: auto !important;
  border: 1px solid rgba(15, 23, 42, 0.16);
  border-radius: 8px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.14);
}
</style>
