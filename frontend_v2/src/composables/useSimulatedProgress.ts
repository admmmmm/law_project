import { ref } from 'vue';

export function useSimulatedProgress() {
  const active = ref(false);
  const value = ref(0);
  const label = ref('');
  const detail = ref('');
  let timer: number | undefined;

  function stopTimer() {
    if (timer) window.clearInterval(timer);
    timer = undefined;
  }

  function start(payload: { label: string; detail?: string }) {
    stopTimer();
    active.value = true;
    value.value = 12;
    label.value = payload.label;
    detail.value = payload.detail || '';
    timer = window.setInterval(() => {
      value.value = Math.min(86, value.value + Math.max(1, Math.random() * 8));
    }, 350);
  }

  async function finish(payload?: { label?: string; detail?: string }) {
    stopTimer();
    value.value = 100;
    if (payload?.label) label.value = payload.label;
    if (payload?.detail) detail.value = payload.detail;
    await new Promise((resolve) => window.setTimeout(resolve, 260));
    active.value = false;
  }

  function fail() {
    stopTimer();
    active.value = false;
  }

  return { active, value, label, detail, start, finish, fail };
}

