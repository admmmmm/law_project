<template>
  <div class="page">
    <header class="page-head">
      <div>
        <h1>检察技能库</h1>
        <p>管理可运行、可测试、可导入导出的检察分析技能包。</p>
      </div>
      <div class="actions">
        <label class="btn ghost">
          导入
          <input type="file" accept=".zip,.json,.md" @change="importPack" />
        </label>
        <button class="btn" :disabled="!selected" @click="exportPack">导出</button>
        <button class="btn primary" :disabled="!selected">发布</button>
      </div>
    </header>

    <div v-if="error" class="error">{{ error }}</div>

    <main class="layout">
      <aside class="panel list">
        <div class="panel-head">
          <h2>技能包列表</h2>
          <button class="link" @click="load">刷新</button>
        </div>
        <button v-for="pack in packs" :key="pack.name" :class="['pack-card', { active: pack.name === selectedName }]" @click="selectPack(pack.name)">
          <div>
            <strong>{{ pack.title || pack.name }}</strong>
            <span>{{ pack.enabled ? '已启用' : '已停用' }} · v{{ pack.version || '0.1.0' }}</span>
          </div>
          <p>{{ pack.description || '暂无说明' }}</p>
          <div class="chips">
            <span v-for="item in pack.case_types || []" :key="item">{{ item }}</span>
            <span v-for="item in pack.task_types || []" :key="item">{{ item }}</span>
          </div>
          <small>{{ pack.rules_count ?? 0 }} rules / {{ pack.findings_count ?? 0 }} findings</small>
        </button>
      </aside>

      <section class="panel detail">
        <div class="panel-head">
          <div>
            <h2>{{ selected?.title || selected?.name || '选择技能包' }}</h2>
            <p>{{ selected?.description || '技能包不是普通 prompt，它应当包含可执行规则、示例、测试和回放记录。' }}</p>
          </div>
          <button class="btn primary" :disabled="!selected || !activeCaseId || running" @click="runSelected">运行当前案件</button>
        </div>

        <div class="tabs">
          <button v-for="tab in tabs" :key="tab.key" :class="{ active: activeTab === tab.key }" @click="activeTab = tab.key">{{ tab.label }}</button>
        </div>

        <section v-if="activeTab === 'summary'" class="content-grid">
          <InfoBox title="SKILL.md 摘要" :value="selected?.skill_md || fallbackSkillSummary" />
          <InfoBox title="manifest" :value="pretty(selected?.manifest || selected)" code />
        </section>

        <section v-else-if="activeTab === 'checks'" class="content-grid">
          <InfoBox title="规则检查项" :value="pretty(selected?.checks || [])" code />
          <InfoBox title="finding templates" :value="pretty(selected?.finding_templates || {})" code />
        </section>

        <section v-else-if="activeTab === 'tests'" class="content-grid">
          <InfoBox title="examples" :value="pretty(selected?.examples || [])" code />
          <InfoBox title="test cases" :value="pretty(selected?.test_cases || [])" code />
        </section>

        <section v-else class="content-grid">
          <InfoBox title="run history" :value="pretty(selected?.run_history || [])" code />
          <InfoBox title="本次运行结果" :value="pretty(lastRun || {})" code />
        </section>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, onMounted, ref } from 'vue';
import { backendApi, type RulePackDetail, type RulePackRunResult, type RulePackSummary } from '../api/backend';

const activeCaseId = ref(localStorage.getItem('active_case_id') || '');
const packs = ref<RulePackSummary[]>([]);
const selectedName = ref('');
const detail = ref<RulePackDetail | null>(null);
const lastRun = ref<RulePackRunResult | null>(null);
const activeTab = ref<'summary' | 'checks' | 'tests' | 'history'>('summary');
const running = ref(false);
const error = ref('');

const tabs = [
  { key: 'summary', label: '详情' },
  { key: 'checks', label: '规则检查项' },
  { key: 'tests', label: '测试与回放' },
  { key: 'history', label: '运行记录' },
] as const;

const selected = computed(() => detail.value || packs.value.find((item) => item.name === selectedName.value) || null);
const fallbackSkillSummary = computed(() => selected.value ? `${selected.value.name}\n${selected.value.description || ''}` : '暂无技能包详情。');

onMounted(load);

async function load() {
  error.value = '';
  try {
    packs.value = await backendApi.listRulePacks();
    if (!selectedName.value && packs.value[0]) await selectPack(packs.value[0].name);
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
}

async function selectPack(name: string) {
  selectedName.value = name;
  detail.value = null;
  lastRun.value = null;
  try {
    detail.value = await backendApi.getRulePack(name);
  } catch {
    detail.value = packs.value.find((item) => item.name === name) as RulePackDetail | null;
  }
}

async function runSelected() {
  if (!selectedName.value || !activeCaseId.value) return;
  running.value = true;
  error.value = '';
  try {
    lastRun.value = await backendApi.runRulePack(activeCaseId.value, selectedName.value);
    activeTab.value = 'history';
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    running.value = false;
  }
}

async function importPack(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;
  try {
    await backendApi.importRulePack(file);
    await load();
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
}

async function exportPack() {
  if (!selectedName.value) return;
  try {
    const blob = await backendApi.exportRulePack(selectedName.value);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedName.value}.zip`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
}

function pretty(value: unknown) {
  return JSON.stringify(value ?? {}, null, 2);
}

const InfoBox = defineComponent({
  props: { title: { type: String, required: true }, value: { type: String, required: true }, code: Boolean },
  setup(props) {
    return () => h('article', { class: 'info-box' }, [
      h('h3', props.title),
      props.code ? h('pre', props.value) : h('p', props.value),
    ]);
  },
});
</script>

<style scoped>
.page { height: 100%; overflow: auto; padding: 20px; background: #f1f5f9; color: #0f172a; }
.page-head, .panel-head, .actions, .tabs { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
h1, h2, h3, p { margin: 0; }
.page-head p, .panel-head p, .pack-card p, .pack-card span, small { color: #64748b; }
.layout { display: grid; grid-template-columns: 360px minmax(0, 1fr); gap: 16px; margin-top: 18px; }
.panel { background: #fff; border: 1px solid #dbe3ee; border-radius: 14px; padding: 16px; }
.list { display: grid; align-content: start; gap: 10px; }
.pack-card { display: grid; gap: 8px; text-align: left; border: 1px solid #dbe3ee; border-radius: 12px; background: #fff; padding: 12px; color: #0f172a; }
.pack-card.active { border-color: #0f766e; background: #ecfdf5; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chips span { border-radius: 999px; background: #e2e8f0; padding: 4px 8px; font-size: 11px; font-weight: 800; }
.btn, .link { border: 1px solid #cbd5e1; border-radius: 10px; background: #fff; color: #0f172a; padding: 9px 13px; font-weight: 800; }
.btn.primary { background: #0f766e; border-color: #0f766e; color: #fff; }
.btn.ghost input { display: none; }
.tabs { justify-content: flex-start; margin: 16px 0; }
.tabs button { border: 1px solid #cbd5e1; border-radius: 999px; background: #fff; padding: 8px 12px; font-weight: 900; }
.tabs button.active { background: #ccfbf1; border-color: #0f766e; color: #115e59; }
.content-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.info-box { border: 1px solid #dbe3ee; border-radius: 12px; background: #f8fafc; padding: 14px; min-height: 220px; }
.info-box p, .info-box pre { margin-top: 10px; white-space: pre-wrap; line-height: 1.7; }
.info-box pre { max-height: 520px; overflow: auto; font-size: 12px; }
.error { margin-top: 12px; color: #b91c1c; font-weight: 800; }
@media (max-width: 980px) { .layout, .content-grid { grid-template-columns: 1fr; } }
</style>
