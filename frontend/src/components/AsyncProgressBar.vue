<template>
  <section class="progress-shell" :class="{ compact }" role="status" aria-live="polite">
    <div class="progress-meta">
      <div>
        <strong>{{ label }}</strong>
        <p v-if="detail">{{ detail }}</p>
      </div>
      <span>{{ percent }}%</span>
    </div>
    <div class="progress-track" aria-hidden="true">
      <div class="progress-fill" :style="{ width: `${clampedValue}%` }" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(
  defineProps<{
    value: number;
    label: string;
    detail?: string;
    compact?: boolean;
  }>(),
  {
    detail: '',
    compact: false,
  },
);

const clampedValue = computed(() => Math.max(0, Math.min(100, props.value)));
const percent = computed(() => Math.round(clampedValue.value));
</script>

<style scoped>
.progress-shell {
  display: grid;
  gap: 10px;
  padding: 14px 16px;
  border: 1px solid #bfdbd3;
  border-radius: 12px;
  background:
    linear-gradient(135deg, rgba(15, 118, 110, 0.08), rgba(255, 255, 255, 0.95)),
    #ffffff;
}

.progress-shell.compact {
  padding: 10px 12px;
  gap: 8px;
}

.progress-meta {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  color: #134e4a;
}

.progress-meta strong {
  display: block;
  font-size: 14px;
  font-weight: 800;
}

.progress-meta p,
.progress-meta span {
  margin: 0;
  font-size: 12px;
  color: #0f766e;
}

.progress-meta span {
  min-width: 40px;
  text-align: right;
  font-weight: 800;
}

.progress-track {
  height: 10px;
  border-radius: 999px;
  overflow: hidden;
  background: rgba(15, 118, 110, 0.12);
  box-shadow: inset 0 0 0 1px rgba(15, 118, 110, 0.06);
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  background:
    linear-gradient(90deg, #0f766e, #14b8a6 55%, #5eead4),
    #14b8a6;
  background-size: 180% 100%;
  animation: progressShift 1.4s linear infinite;
  transition: width 220ms ease;
}

@keyframes progressShift {
  from {
    background-position: 0 0;
  }

  to {
    background-position: 180% 0;
  }
}
</style>
