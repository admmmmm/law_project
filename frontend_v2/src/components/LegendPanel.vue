<template>
  <div class="legend-panel" :class="`legend-${layer || 'default'}`">
    <strong>图例</strong>
    <div v-if="nodeTypes.length || edgeTypes.length" class="legend-groups">
      <div v-if="nodeTypes.length" class="legend-group">
        <span class="legend-title">节点</span>
        <span v-for="item in nodeTypes" :key="`node-${item.type}`" class="legend-item">
          <i class="node-dot"></i>{{ item.label || item.type }}
        </span>
      </div>
      <div v-if="edgeTypes.length" class="legend-group">
        <span class="legend-title">关系</span>
        <span v-for="item in edgeTypes" :key="`edge-${item.type}`" class="legend-item">
          <i class="edge-line"></i>{{ item.label || item.type }}
        </span>
      </div>
    </div>
    <span v-else class="muted">当前图层暂无可显示图例。</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { LegendItem } from '../api/backend';

const props = defineProps<{ legend?: { node_types?: LegendItem[]; edge_types?: LegendItem[] }; layer?: 'document' | 'passage' | 'raw' }>();
const nodeTypes = computed(() => props.legend?.node_types || []);
const edgeTypes = computed(() => props.legend?.edge_types || []);
</script>

<style scoped>
.legend-panel {
  border-top: 1px solid var(--line);
  background: #ffffff;
  padding: 10px 12px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  font-size: 12px;
}
.legend-groups {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.legend-group {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.legend-title {
  color: var(--muted);
  font-weight: 900;
}
.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: #334155;
  font-weight: 800;
}
.node-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: var(--primary);
}
.edge-line {
  width: 16px;
  height: 2px;
  background: #64748b;
}
.legend-document .node-dot {
  background: #0f766e;
}
.legend-document .edge-line {
  background: #10b981;
}
.legend-passage .node-dot {
  background: #2563eb;
}
.legend-passage .edge-line {
  background: #60a5fa;
}
</style>
