<template>
  <div class="case-page">
    <div class="shell">
      <header class="page-head">
        <div>
          <h1>案件管理</h1>
          <p>选择案件、导入材料、运行分析，然后进入对应案件工作区。</p>
        </div>
        <div class="head-actions">
          <button class="secondary head-action" @click="openLegalKnowledge">法律知识库</button>
          <button class="primary head-action" :disabled="loading" @click="createCase">新建默认案件</button>
        </div>
      </header>

      <AsyncProgressBar
        v-if="progress.active.value"
        :value="progress.value.value"
        :label="progress.label.value"
        :detail="progress.detail.value"
      />

      <section class="case-layout">
        <aside class="case-sidebar">
          <div class="panel-head">
            <div>
              <h2>案件列表</h2>
              <p>{{ cases.length }} 个案件</p>
            </div>
            <button class="secondary small" :disabled="loading" @click="loadCases">刷新</button>
          </div>
          <div class="case-list">
            <button
              v-for="item in cases"
              :key="item.case_id"
              class="case-row"
              :class="{ active: item.case_id === selectedCaseId }"
              @click="selectCase(item.case_id)"
            >
              <strong>{{ item.title }}</strong>
              <span>{{ statusLabel(item.status) }} · {{ item.evidence_count }} 份证据</span>
              <code>{{ item.case_id }}</code>
            </button>
          </div>

          <div class="new-case">
            <div class="panel-head compact-head">
              <h2>新建案件</h2>
              <button class="secondary small" :disabled="loading" @click="resetCustomCase">清空</button>
            </div>
            <label>
              案件名称
              <input v-model="customCase.title" class="field" placeholder="例如：杨周武徇私枉法案" />
            </label>
            <label>
              办案人
              <input v-model="customCase.owner" class="field" placeholder="可选" />
            </label>
            <label>
              涉嫌罪名
              <select v-model="customCase.offenseId" class="field">
                <option value="">留空：先按事实分析</option>
                <option v-for="item in offenseTemplates" :key="item.offense_id" :value="item.offense_id">
                  {{ item.name }}
                </option>
              </select>
            </label>
            <label>
              案件说明
              <textarea v-model="customCase.description" class="field textarea" placeholder="简要写明案由、对象、材料范围。"></textarea>
            </label>
            <button class="primary" :disabled="!customCase.title.trim() || loading" @click="createCustomCase">创建并切换</button>
          </div>
        </aside>

        <main class="case-main">
          <section class="case-profile">
            <div>
              <p class="eyebrow">当前案件</p>
              <h2>{{ selectedCase?.title || '未选择案件' }}</h2>
              <p class="hint">案件 ID：{{ selectedCaseId || '-' }}</p>
              <div v-if="selectedCase" class="offense-line">
                <span>涉嫌罪名</span>
                <select :value="selectedCase.offense_id || ''" class="field compact-select" :disabled="loading" @change="onOffenseChange">
                  <option value="">留空：事实分析</option>
                  <option v-for="item in offenseTemplates" :key="item.offense_id" :value="item.offense_id">
                    {{ item.name }}
                  </option>
                </select>
              </div>
            </div>
            <div class="quick-actions">
              <button class="secondary" :disabled="!selectedCaseId" @click="openWorkspace('graph')">证据图谱</button>
              <button class="secondary" :disabled="!selectedCaseId" @click="openWorkspace('portrait')">画像页</button>
              <button class="secondary" :disabled="!selectedCaseId" @click="openWorkspace('intelligence')">智能分析</button>
              <button class="danger" :disabled="!selectedCaseId || loading" @click="deleteSelectedCase">删除案件</button>
            </div>
          </section>

          <section class="status-strip">
            <div><b>{{ selectedCase ? statusLabel(selectedCase.status) : '-' }}</b><span>状态</span></div>
            <div><b>{{ currentEvidenceCount }}</b><span>证据材料</span></div>
            <div><b>{{ currentTripleCount }}</b><span>三元组</span></div>
            <div><b>{{ currentSkippedCount }}</b><span>跳过文件</span></div>
          </section>

          <section class="work-grid">
            <div class="card">
              <h2>材料导入</h2>
              <input ref="folderInput" class="hidden-input" type="file" multiple webkitdirectory @change="onFolderChange" />
              <input ref="zipInput" class="hidden-input" type="file" accept=".zip" @change="onZipChange" />
              <button class="secondary" :disabled="!selectedCaseId || loading" @click="folderInput?.click()">选择文件夹</button>
              <button class="secondary" :disabled="!selectedCaseId || loading" @click="zipInput?.click()">选择压缩包</button>
              <p class="hint">支持 txt / md / csv / xlsx / json / pdf / docx / zip。</p>
            </div>

            <div class="card">
              <h2>分析入口</h2>
              <button class="primary" :disabled="!selectedCaseId || loading" @click="runAnalysis">运行分析并进图谱</button>
              <p class="hint">{{ analysisSummary || '导入后点击分析。' }}</p>
            </div>
          </section>

          <section class="card">
            <h2>导入状态</h2>
            <AsyncProgressBar
              v-if="loading || importInProgress"
              compact
              :value="progress.active.value ? progress.value.value : 16"
              :label="progress.active.value ? progress.label.value : '正在处理导入任务'"
              :detail="progress.active.value ? progress.detail.value : '请保持当前页面，等待后端完成解析'"
            />
            <div v-else-if="batchResult || currentEvidenceCount > 0">
              <div class="stats">
                <div><b>{{ currentImportedCount }}</b><span>已导入</span></div>
                <div><b>{{ currentSkippedCount }}</b><span>已跳过</span></div>
                <div><b>{{ currentTripleCount }}</b><span>三元组</span></div>
              </div>
              <p v-if="!batchResult" class="hint status-note">这是后端案件列表返回的已导入证据数量，不展示任何演示数据。</p>
              <div v-if="batchResult?.skipped.length" class="skipped">
                <div class="font-bold">跳过文件</div>
                <div v-for="item in batchResult.skipped.slice(0, 8)" :key="item.filename">
                  {{ item.filename }}：{{ item.reason }}
                </div>
              </div>
            </div>
            <div v-else class="hint">还没有导入。本页不展示任何演示数据。</div>
            <div v-if="error" class="error">{{ error }}</div>
          </section>
        </main>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { backendApi, type BatchIngestionResult, type CaseSummary, type OffenseTemplateSummary } from '../api/backend';
import AsyncProgressBar from '../components/AsyncProgressBar.vue';
import { useSimulatedProgress } from '../composables/useSimulatedProgress';

const router = useRouter();
const cases = ref<CaseSummary[]>([]);
const offenseTemplates = ref<OffenseTemplateSummary[]>([]);
const selectedCaseId = ref(localStorage.getItem('active_case_id') || '');
const batchResult = ref<BatchIngestionResult | null>(null);
const analysisSummary = ref('');
const importInProgress = ref(false);
const loading = ref(false);
const error = ref('');
const progress = useSimulatedProgress();
const folderInput = ref<HTMLInputElement | null>(null);
const zipInput = ref<HTMLInputElement | null>(null);
const customCase = ref({
  title: '',
  description: '',
  legalBasis: '',
  offenseId: '',
  owner: '',
});

const selectedCase = computed(() => cases.value.find((item) => item.case_id === selectedCaseId.value));
const currentEvidenceCount = computed(() => selectedCase.value?.evidence_count || 0);
const totalTriples = computed(() => batchResult.value?.results.reduce((sum, item) => sum + (item.extraction?.triples.length || 0), 0) || 0);
const currentImportedCount = computed(() => batchResult.value?.imported_count ?? currentEvidenceCount.value);
const currentSkippedCount = computed(() => batchResult.value?.skipped_count ?? 0);
const currentTripleCount = computed(() => (batchResult.value ? totalTriples.value : '-'));

onMounted(async () => {
  restoreDashboardState();
  await loadOffenseTemplates();
  await loadCases();
});

function dashboardCacheKey(caseId = selectedCaseId.value) {
  return caseId ? `jcmx:dashboard:v1:${caseId}` : '';
}

function restoreDashboardState() {
  batchResult.value = null;
  analysisSummary.value = '';
  importInProgress.value = false;
  const cacheKey = dashboardCacheKey();
  if (!cacheKey) return;
  const cached = sessionStorage.getItem(cacheKey);
  if (!cached) return;
  try {
    const parsed = JSON.parse(cached) as {
      batchResult?: BatchIngestionResult | null;
      analysisSummary?: string;
      importInProgress?: boolean;
    };
    batchResult.value = parsed.batchResult ?? null;
    analysisSummary.value = parsed.analysisSummary || '';
    importInProgress.value = Boolean(parsed.importInProgress);
  } catch {
    sessionStorage.removeItem(cacheKey);
  }
}

function persistDashboardState() {
  const cacheKey = dashboardCacheKey();
  if (!cacheKey) return;
  sessionStorage.setItem(
    cacheKey,
    JSON.stringify({
      batchResult: batchResult.value,
      analysisSummary: analysisSummary.value,
      importInProgress: importInProgress.value,
    }),
  );
}

async function loadCases() {
  cases.value = await backendApi.listCases();
  if (!selectedCaseId.value && cases.value[0]) {
    selectedCaseId.value = cases.value[0].case_id;
    persistCase();
  }
}

async function loadOffenseTemplates() {
  try {
    offenseTemplates.value = await backendApi.listOffenseTemplates();
  } catch {
    offenseTemplates.value = [];
  }
}

async function createCase() {
  await withLoading(
    async () => {
      const item = await backendApi.createCase('杨周武徇私枉法案', '批量导入证据、流水和案情材料的联调案件。');
      await loadCases();
      selectedCaseId.value = item.case_id;
      persistCase();
    },
    {
      label: '正在创建案件',
      detail: '准备案件卡片与本地分析空间',
      successLabel: '案件已创建',
    },
  );
}

async function createCustomCase() {
  const title = customCase.value.title.trim();
  if (!title) return;
  await withLoading(
    async () => {
      const item = await backendApi.createCustomCase({
        title,
        description: customCase.value.description.trim() || null,
        legal_basis: selectedOffenseName(customCase.value.offenseId),
        offense_id: customCase.value.offenseId || null,
        owner: customCase.value.owner.trim() || null,
      });
      await loadCases();
      selectedCaseId.value = item.case_id;
      persistCase();
      resetCustomCase();
    },
    {
      label: '正在创建自定义案件',
      detail: '保存案件标题、案情说明与负责人信息',
      successLabel: '自定义案件已创建',
    },
  );
}

async function deleteSelectedCase() {
  if (!selectedCaseId.value || !selectedCase.value) return;
  const ok = window.confirm(`确定删除案件「${selectedCase.value.title}」吗？该操作会删除证据、图谱、报告和记忆。`);
  if (!ok) return;
  await withLoading(
    async () => {
      const deletedId = selectedCaseId.value;
      await backendApi.deleteCase(deletedId);
      sessionStorage.removeItem(dashboardCacheKey(deletedId));
      if (localStorage.getItem('active_case_id') === deletedId) {
        localStorage.removeItem('active_case_id');
      }
      if (localStorage.getItem('active_workspace_id') === deletedId) {
        localStorage.removeItem('active_workspace_id');
      }
      selectedCaseId.value = '';
      batchResult.value = null;
      analysisSummary.value = '';
      await loadCases();
      if (cases.value[0]) {
        selectedCaseId.value = cases.value[0].case_id;
        persistCase();
      }
    },
    {
      label: '正在删除案件',
      detail: '清理案件、证据、图谱、报告和记忆',
      successLabel: '案件已删除',
    },
  );
}

function resetCustomCase() {
  customCase.value = {
    title: '',
    description: '',
    legalBasis: '',
    offenseId: '',
    owner: '',
  };
}

async function onOffenseChange(event: Event) {
  if (!selectedCaseId.value) return;
  const offenseId = (event.target as HTMLSelectElement).value;
  await withLoading(
    async () => {
      await backendApi.updateCase(selectedCaseId.value, {
        offense_id: offenseId || null,
        legal_basis: selectedOffenseName(offenseId),
      });
      await loadCases();
    },
    {
      label: '正在保存罪名选择',
      detail: offenseId ? '后续分析会参考对应法律知识库' : '后续分析将按证据事实进行',
      successLabel: '罪名选择已保存',
    },
  );
}

function selectedOffenseName(offenseId: string) {
  if (!offenseId) return null;
  return offenseTemplates.value.find((item) => item.offense_id === offenseId)?.name || offenseId;
}

function persistCase() {
  localStorage.setItem('active_case_id', selectedCaseId.value);
  localStorage.setItem('active_workspace_id', selectedCaseId.value);
  restoreDashboardState();
}

function selectCase(caseId: string) {
  selectedCaseId.value = caseId;
  persistCase();
}

function statusLabel(status: string) {
  return {
    created: '已建案',
    data_ingested: '已导入',
    analyzed: '已分析',
  }[status] || status || '未知';
}

function openWorkspace(page: string) {
  if (!selectedCaseId.value) return;
  router.push(`/${selectedCaseId.value}/${page}`);
}

function openLegalKnowledge() {
  router.push('/legal-knowledge');
}

async function onFolderChange(event: Event) {
  const input = event.target as HTMLInputElement;
  const files = Array.from(input.files || []);
  if (!selectedCaseId.value || files.length === 0) return;
  importInProgress.value = true;
  persistDashboardState();
  await withLoading(
    async () => {
      batchResult.value = await backendApi.ingestBatch(selectedCaseId.value, files);
      importInProgress.value = false;
      persistDashboardState();
      await loadCases();
      input.value = '';
    },
    {
      label: '正在导入证据',
      detail: `已提交 ${files.length} 个文件，正在等待后端解析与抽取`,
      successLabel: '证据导入完成',
    },
  );
}

async function onZipChange(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!selectedCaseId.value || !file) return;
  importInProgress.value = true;
  persistDashboardState();
  await withLoading(
    async () => {
      batchResult.value = await backendApi.ingestArchive(selectedCaseId.value, file);
      importInProgress.value = false;
      persistDashboardState();
      await loadCases();
      input.value = '';
    },
    {
      label: '正在导入压缩包',
      detail: `正在处理 ${file.name} 并抽取案件证据`,
      successLabel: '压缩包导入完成',
    },
  );
}

async function runAnalysis() {
  if (!selectedCaseId.value) return;
  await withLoading(
    async () => {
      const result = await backendApi.runAnalysis(selectedCaseId.value);
      analysisSummary.value = result.summary;
      persistDashboardState();
      await router.push(`/${selectedCaseId.value}/graph`);
    },
    {
      label: '正在运行分析',
      detail: '后端正在抽取关系、构建图谱并生成线索',
      successLabel: '分析完成，正在进入图谱',
    },
  );
}

async function withLoading(
  task: () => Promise<void>,
  progressOptions?: {
    label: string;
    detail?: string;
    successLabel?: string;
  },
) {
  loading.value = true;
  error.value = '';
  if (progressOptions) {
    progress.start({
      label: progressOptions.label,
      detail: progressOptions.detail,
    });
  }
  try {
    await task();
    if (progressOptions) {
      await progress.finish({
        label: progressOptions.successLabel || `${progressOptions.label}完成`,
        detail: '界面数据已刷新',
      });
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
    importInProgress.value = false;
    persistDashboardState();
    progress.fail();
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.case-page {
  height: 100%;
  overflow: auto;
  background: #f1f5f9;
  color: #0f172a;
  padding: 20px;
}

.shell {
  max-width: 1280px;
  margin: 0 auto;
  display: grid;
  gap: 16px;
}

.page-head,
.card {
  border: 1px solid #cbd5e1;
  background: #ffffff;
  border-radius: 8px;
  padding: 18px;
}

.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.head-action {
  width: auto;
  min-width: 140px;
}

.head-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.case-layout {
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.case-sidebar,
.case-main,
.case-profile,
.status-strip {
  min-width: 0;
}

.case-sidebar {
  display: grid;
  gap: 12px;
}

.panel-head,
.case-profile {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.panel-head h2,
.compact-head h2 {
  margin-bottom: 0;
}

.panel-head p {
  margin-top: 3px;
}

.case-list,
.new-case,
.case-profile,
.status-strip {
  border: 1px solid #cbd5e1;
  background: #ffffff;
  border-radius: 8px;
  padding: 12px;
}

.case-list {
  display: grid;
  gap: 8px;
  max-height: 420px;
  overflow: auto;
}

.case-row {
  width: 100%;
  text-align: left;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
  padding: 10px;
}

.case-row.active {
  border-color: #0f766e;
  background: #ecfdf5;
}

.case-row strong,
.case-row span,
.case-row code {
  display: block;
}

.offense-line {
  display: grid;
  grid-template-columns: 72px minmax(180px, 260px);
  align-items: center;
  gap: 10px;
  margin-top: 12px;
  color: #334155;
  font-size: 13px;
  font-weight: 800;
}

.compact-select {
  min-height: 36px;
}

.case-row span,
.case-row code {
  margin-top: 4px;
  color: #64748b;
  font-size: 12px;
}

.new-case {
  display: grid;
  gap: 10px;
}

.new-case label {
  color: #334155;
  font-size: 13px;
  font-weight: 800;
}

.textarea {
  min-height: 84px;
  resize: vertical;
}

.case-main {
  display: grid;
  gap: 16px;
}

.quick-actions,
.work-grid,
.status-strip {
  display: grid;
  gap: 10px;
}

.quick-actions {
  grid-template-columns: repeat(4, auto);
}

.work-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.status-strip {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.status-strip div {
  border-right: 1px solid #e2e8f0;
  padding: 4px 12px;
}

.status-strip div:last-child {
  border-right: 0;
}

h1 {
  font-size: 24px;
  font-weight: 900;
}

h2 {
  font-size: 15px;
  font-weight: 900;
  margin-bottom: 12px;
}

p,
.hint,
.eyebrow {
  color: #64748b;
  font-size: 13px;
}

.eyebrow {
  color: #0f766e;
  font-weight: 900;
}

.field {
  width: 100%;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #0f172a;
  border-radius: 6px;
  padding: 8px;
  font-size: 13px;
}

.hidden-input {
  display: none;
}

.primary,
.secondary {
  width: 100%;
  border-radius: 6px;
  padding: 9px 12px;
  font-size: 13px;
  font-weight: 900;
}

.compact {
  width: auto;
  min-width: 120px;
}

.small {
  width: auto;
  padding: 7px 10px;
}

.primary {
  background: #0f766e;
  color: #ffffff;
}

.secondary {
  border: 1px solid #94a3b8;
  background: #ffffff;
  color: #0f172a;
  margin-bottom: 8px;
}

.danger {
  border: 1px solid #fecdd3;
  border-radius: 6px;
  background: #fff1f2;
  color: #be123c;
  padding: 9px 12px;
  font-size: 13px;
  font-weight: 900;
  margin-bottom: 8px;
}

button:disabled {
  opacity: 0.45;
}

.stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.stats div {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
}

.stats b {
  display: block;
  color: #0f172a;
  font-size: 24px;
}

.stats span {
  color: #64748b;
  font-size: 12px;
}

.status-note,
.skipped {
  margin-top: 12px;
}

.skipped {
  color: #475569;
  font-size: 13px;
}

.font-bold {
  font-weight: 900;
}

.error {
  margin-top: 12px;
  color: #be123c;
  background: #fff1f2;
  border: 1px solid #fecdd3;
  border-radius: 6px;
  padding: 10px;
  font-size: 13px;
}

@media (max-width: 900px) {
  .page-head,
  .case-layout,
  .work-grid,
  .status-strip {
    display: grid;
    grid-template-columns: 1fr;
  }

  .quick-actions {
    grid-template-columns: 1fr;
  }
}
</style>
