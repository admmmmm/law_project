<template>
  <div class="progress-box" :class="{ compact }">
    <div class="row-between">
      <strong>{{ label }}</strong>
      <span>{{ Math.round(value) }}%</span>
    </div>
    <div class="progress-track"><div class="progress-fill" :style="{ width: `${Math.max(0, Math.min(100, value))}%` }"></div></div>
    <p v-if="detail" class="muted">{{ detail }}</p>
  </div>
</template>

<script setup lang="ts">
defineProps<{ value: number; label: string; detail?: string; compact?: boolean }>();
</script>

<style scoped>
.progress-box {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #f8fafc;
  padding: 14px;
  display: grid;
  gap: 8px;
}
.progress-box.compact {
  margin-top: 12px;
  padding: 10px;
}
.progress-track {
  height: 8px;
  border-radius: 999px;
  background: #e2e8f0;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: var(--primary);
  transition: width 0.25s ease;
}
</style>

