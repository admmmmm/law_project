<template>
  <div class="app-logo" :class="{ collapsed, compact }" aria-label="系统标识">
    <span class="sword-mark" aria-hidden="true">
      <svg viewBox="0 0 48 48" role="img">
        <path class="blade" d="M29.9 3.8 34 8 18.8 30.2l-3-3L29.9 3.8Z" />
        <path class="edge" d="M34 8 38.8 12.8 21.8 33.2l-3-3L34 8Z" />
        <path class="guard" d="M12.3 25.7 22.3 35.7 19.8 38.2 9.8 28.2l2.5-2.5Z" />
        <path class="grip" d="M8.8 31.1 16.9 39.2 13.5 42.6 5.4 34.5l3.4-3.4Z" />
        <circle class="pommel" cx="5.5" cy="42.5" r="2.4" />
      </svg>
    </span>
    <span v-if="!collapsed" class="logo-copy">
      <strong>{{ title }}</strong>
      <small v-if="subtitle">{{ subtitle }}</small>
    </span>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  collapsed?: boolean;
  compact?: boolean;
  title?: string;
  subtitle?: string;
}>();
</script>

<style scoped>
.app-logo {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.app-logo.collapsed,
.app-logo.compact {
  gap: 0;
}
.sword-mark {
  width: 38px;
  height: 38px;
  flex: 0 0 38px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: #0f766e;
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.24);
}
.sword-mark svg {
  width: 28px;
  height: 28px;
}
.blade {
  fill: #f8fafc;
}
.edge {
  fill: #d9f99d;
  opacity: .88;
}
.guard,
.grip,
.pommel {
  fill: #102a43;
}
.logo-copy {
  display: grid;
  min-width: 0;
  line-height: 1.2;
}
.logo-copy strong {
  color: #0f172a;
  font-size: 14px;
  white-space: nowrap;
}
.logo-copy small {
  color: #64748b;
  font-size: 12px;
  white-space: nowrap;
}
</style>
