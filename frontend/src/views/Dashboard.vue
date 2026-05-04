<template>
  <div class="whiteboard-page">
    <div class="shell">
      <section class="board">
        <div>
          <h1>白板工作台</h1>
          <p>先在这里建案、导入材料、运行分析，再进入图谱和画像页继续深挖。</p>
        </div>
        <button class="primary" :disabled="loading" @click="createCase">新建默认案件</button>
      </section>

      <AsyncProgressBar
        v-if="progress.active.value"
        :value="progress.value.value"
        :label="progress.label.value"
        :detail="progress.detail.value"
      />

      <section class="card custom-case">
        <div class="custom-head">
          <div>
            <h2>自定义案件</h2>
            <p class="hint">用于真实联调或新材料测试。创建后会自动切换为当前案件。</p>
          </div>
          <button class="secondary compact" :disabled="loading" @click="resetCustomCase">清空</button>
        </div>
        <div class="custom-grid">
          <label>
            案件名称
            <input v-model="customCase.title" class="field" placeholder="例如：杨周武徇私枉法案" />
          </label>
          <label>
            办案人/负责人
            <input v-model="customCase.owner" class="field" placeholder="可选" />
          </label>
          <label class="wide">
            法律依据/罪名方向
            <input v-model="customCase.legalBasis" class="field" placeholder="例如：徇私枉法罪、玩忽职守罪" />
          </label>
          <label class="wide">
            案件说明
            <textarea
              v-model="customCase.description"
              class="field textarea"
              placeholder="简要写明案由、对象、当前已有材料范围。"
            />
          </label>
        </div>
        <button class="primary create-custom" :disabled="!customCase.title.trim() || loading" @click="createCustomCase">
          创建自定义案件并切换
        </button>
      </section>

      <section class="grid">
        <div class="card">
          <h2>1. 案件</h2>
          <select v-model="selectedCaseId" class="field" @change="persistCase">
            <option value="">未选择</option>
            <option v-for="item in cases" :key="item.case_id" :value="item.case_id">
              {{ item.title }} ({{ item.evidence_count }})
            </option>
          </select>
          <p class="hint">当前案件 ID：{{ selectedCaseId || '-' }}</p>
        </div>

        <div class="card">
          <h2>2. 导入</h2>
          <input ref="folderInput" class="hidden-input" type="file" multiple webkitdirectory @change="onFolderChange" />
          <input ref="zipInput" class="hidden-input" type="file" accept=".zip" @change="onZipChange" />
          <button class="secondary" :disabled="!selectedCaseId || loading" @click="folderInput?.click()">选择文件夹</button>
          <button class="secondary" :disabled="!selectedCaseId || loading" @click="zipInput?.click()">选择压缩包</button>
          <p class="hint">支持 txt / md / csv / xlsx / json / pdf / docx / zip；旧 xls 建议先转成 CSV 或 XLSX。</p>
        </div>

        <div class="card">
          <h2>3. 分析</h2>
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
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { backendApi, type BatchIngestionResult, type CaseSummary } from '../api/backend';
import AsyncProgressBar from '../components/AsyncProgressBar.vue';
import { useSimulatedProgress } from '../composables/useSimulatedProgress';

const router = useRouter();
const cases = ref<CaseSummary[]>([]);
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
        legal_basis: customCase.value.legalBasis.trim() || null,
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

function resetCustomCase() {
  customCase.value = {
    title: '',
    description: '',
    legalBasis: '',
    owner: '',
  };
}

function persistCase() {
  localStorage.setItem('active_case_id', selectedCaseId.value);
  restoreDashboardState();
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
      await router.push('/graph');
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
.whiteboard-page {
  height: 100%;
  overflow: auto;
  background: #f1f5f9;
  color: #0f172a;
  padding: 20px;
}

.shell {
  max-width: 1024px;
  margin: 0 auto;
  display: grid;
  gap: 16px;
}

.board,
.card {
  border: 1px solid #cbd5e1;
  background: #ffffff;
  border-radius: 8px;
  padding: 18px;
}

.board {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.custom-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.custom-case {
  display: grid;
  gap: 14px;
}

.custom-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.custom-grid label {
  color: #334155;
  font-size: 13px;
  font-weight: 800;
}

.custom-grid .wide {
  grid-column: 1 / -1;
}

.textarea {
  min-height: 84px;
  resize: vertical;
}

.create-custom {
  max-width: 280px;
  justify-self: end;
}

.grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
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
.hint {
  color: #64748b;
  font-size: 13px;
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
  .board,
  .grid {
    display: grid;
    grid-template-columns: 1fr;
  }
}
</style>
