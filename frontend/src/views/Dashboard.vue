<template>
  <div class="whiteboard-page">
    <div class="shell">
      <section class="board">
        <div>
          <h1>白板工作台</h1>
          <p>前端暂时只保留最小联调：建案、批量导入、运行分析、看图谱。</p>
        </div>
        <button class="primary" @click="createCase">新建默认案件</button>
      </section>

      <section class="grid">
        <div class="card">
          <h2>1. 案件</h2>
          <select v-model="selectedCaseId" class="field" @change="persistCase">
            <option value="">未选择</option>
            <option v-for="item in cases" :key="item.case_id" :value="item.case_id">
              {{ item.title }}（{{ item.evidence_count }}）
            </option>
          </select>
          <p class="hint">当前案件 ID：{{ selectedCaseId || '-' }}</p>
        </div>

        <div class="card">
          <h2>2. 导入</h2>
          <input ref="folderInput" class="hidden-input" type="file" multiple webkitdirectory @change="onFolderChange" />
          <input ref="zipInput" class="hidden-input" type="file" accept=".zip" @change="onZipChange" />
          <button class="secondary" :disabled="!selectedCaseId" @click="folderInput?.click()">选择文件夹</button>
          <button class="secondary" :disabled="!selectedCaseId" @click="zipInput?.click()">选择压缩包</button>
          <p class="hint">支持 txt/md/csv/xlsx/json/pdf/docx/zip；旧 xls 先转 CSV/XLSX。</p>
        </div>

        <div class="card">
          <h2>3. 分析</h2>
          <button class="primary" :disabled="!selectedCaseId" @click="runAnalysis">运行分析并进图谱</button>
          <p class="hint">{{ analysisSummary || '导入后点击分析。' }}</p>
        </div>
      </section>

      <section class="card">
        <h2>导入状态</h2>
        <div v-if="loading" class="hint">处理中...</div>
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

const router = useRouter();
const cases = ref<CaseSummary[]>([]);
const selectedCaseId = ref(localStorage.getItem('active_case_id') || '');
const batchResult = ref<BatchIngestionResult | null>(null);
const analysisSummary = ref('');
const loading = ref(false);
const error = ref('');
const folderInput = ref<HTMLInputElement | null>(null);
const zipInput = ref<HTMLInputElement | null>(null);

const selectedCase = computed(() => cases.value.find((item) => item.case_id === selectedCaseId.value));
const currentEvidenceCount = computed(() => selectedCase.value?.evidence_count || 0);
const totalTriples = computed(() => batchResult.value?.results.reduce((sum, item) => sum + (item.extraction?.triples.length || 0), 0) || 0);
const currentImportedCount = computed(() => batchResult.value?.imported_count ?? currentEvidenceCount.value);
const currentSkippedCount = computed(() => batchResult.value?.skipped_count ?? 0);
const currentTripleCount = computed(() => (batchResult.value ? totalTriples.value : '-'));

onMounted(loadCases);

async function loadCases() {
  cases.value = await backendApi.listCases();
  if (!selectedCaseId.value && cases.value[0]) {
    selectedCaseId.value = cases.value[0].case_id;
    persistCase();
  }
}

async function createCase() {
  const item = await backendApi.createCase('杨周武徇私枉法案', '批量导入证据、流水和案情材料的联调案件。');
  await loadCases();
  selectedCaseId.value = item.case_id;
  persistCase();
}

function persistCase() {
  localStorage.setItem('active_case_id', selectedCaseId.value);
  batchResult.value = null;
  analysisSummary.value = '';
}

async function onFolderChange(event: Event) {
  const files = Array.from((event.target as HTMLInputElement).files || []);
  if (!selectedCaseId.value || files.length === 0) return;
  await withLoading(async () => {
    batchResult.value = await backendApi.ingestBatch(selectedCaseId.value, files);
    await loadCases();
  });
}

async function onZipChange(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!selectedCaseId.value || !file) return;
  await withLoading(async () => {
    batchResult.value = await backendApi.ingestArchive(selectedCaseId.value, file);
    await loadCases();
  });
}

async function runAnalysis() {
  if (!selectedCaseId.value) return;
  await withLoading(async () => {
    const result = await backendApi.runAnalysis(selectedCaseId.value);
    analysisSummary.value = result.summary;
    await router.push('/graph');
  });
}

async function withLoading(task: () => Promise<void>) {
  loading.value = true;
  error.value = '';
  try {
    await task();
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
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
