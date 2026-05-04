import { onBeforeUnmount, ref } from 'vue';

interface ProgressOptions {
  label: string;
  detail?: string;
  initialValue?: number;
  maxAutoValue?: number;
}

export function useSimulatedProgress() {
  const active = ref(false);
  const value = ref(0);
  const label = ref('');
  const detail = ref('');

  let timer: ReturnType<typeof setInterval> | null = null;
  let resetTimer: ReturnType<typeof setTimeout> | null = null;
  let maxAutoValue = 92;

  function clearTimers() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
    if (resetTimer) {
      clearTimeout(resetTimer);
      resetTimer = null;
    }
  }

  function resetState() {
    active.value = false;
    value.value = 0;
    label.value = '';
    detail.value = '';
  }

  function start(options: ProgressOptions) {
    clearTimers();
    active.value = true;
    label.value = options.label;
    detail.value = options.detail || '';
    value.value = options.initialValue ?? 8;
    maxAutoValue = options.maxAutoValue ?? 92;

    timer = setInterval(() => {
      const remaining = maxAutoValue - value.value;
      if (remaining <= 0.2) return;
      const increment = Math.max(remaining * 0.14, 0.5);
      value.value = Math.min(maxAutoValue, Number((value.value + increment).toFixed(1)));
    }, 240);
  }

  function update(options: Partial<Pick<ProgressOptions, 'label' | 'detail'>>) {
    if (options.label) label.value = options.label;
    if (typeof options.detail === 'string') detail.value = options.detail;
  }

  async function finish(options?: { label?: string; detail?: string }) {
    if (options?.label) label.value = options.label;
    if (typeof options?.detail === 'string') detail.value = options.detail;
    clearTimers();
    value.value = 100;
    resetTimer = setTimeout(() => {
      resetState();
    }, 320);
    await new Promise((resolve) => setTimeout(resolve, 220));
  }

  function fail(options?: { label?: string; detail?: string }) {
    if (options?.label) label.value = options.label;
    if (typeof options?.detail === 'string') detail.value = options.detail;
    clearTimers();
    resetState();
  }

  onBeforeUnmount(() => {
    clearTimers();
  });

  return {
    active,
    value,
    label,
    detail,
    start,
    update,
    finish,
    fail,
  };
}
