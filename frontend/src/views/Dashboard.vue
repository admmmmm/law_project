<template>
  <div class="h-full overflow-auto p-6">
    <div class="max-w-6xl mx-auto grid grid-cols-[minmax(0,1fr)_360px] gap-6">
      <section class="space-y-4">
        <div class="bg-white border border-slate-200 rounded-lg">
          <div class="p-4 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h2 class="font-bold text-slate-900">案件列表</h2>
              <p class="text-sm text-slate-500">这里不再显示演示数据；没有创建或导入时就是空的。</p>
            </div>
            <button class="btn-primary" @click="createCase">新建案件</button>
          </div>
          <div v-if="loading" class="p-8 text-sm text-slate-500">正在读取后端案件...</div>
          <div v-else-if="cases.length === 0" class="p-10 text-center">
            <Database class="mx-auto text-slate-300 mb-3" :size="42" />
            <div class="font-bold text-slate-700">还没有案件</div>
            <p class="text-sm text-slate-500 mt-1">先创建案件，再导入证据文本或银行流水文件。</p>
          </div>
          <div v-else class="divide-y divide-slate-100">
            <button
              v-for="item in cases"
              :key="item.case_id"
              class="w-full text-left p-4 hover:bg-slate-50 flex items-center justify-between"
              :class="selectedCaseId === item.case_id ? 'bg-blue-50' : ''"
              @click="selectCase(item.case_id)"
            >
              <div>
                <div class="font-bold text-slate-900">{{ item.title }}</div>
                <div class="text-xs text-slate-500 font-mono">{{ item.case_id }}</div>
              </div>
              <div class="flex items-center gap-3 text-sm">
                <span class="tag">{{ statusLabel(item.status) }}</span>
                <span class="text-slate-500">{{ item.evidence_count }} 份证据</span>
              </div>
            </button>
          </div>
        </div>

        <div class="bg-white border border-slate-200 rounded-lg p-4">
          <div class="flex items-center justify-between mb-3">
            <div>
              <h2 class="font-bold text-slate-900">导入结果</h2>
              <p class="text-sm text-slate-500">导入会立即抽取三元组和 passage，分析后生成图谱。</p>
            </div>
            <button class="btn-secondary" :disabled="!selectedCaseId || running" @click="runAnalysis">运行分析</button>
          </div>
          <div v-if="lastResult" class="grid grid-cols-3 gap-3">
            <div class="metric">
              <span>抽取路线</span>
              <strong>{{ lastResult.extraction?.route || '-' }}</strong>
            </div>
            <div class="metric">
              <span>三元组</span>
              <strong>{{ lastResult.extraction?.triples.length || 0 }}</strong>
            </div>
            <div class="metric">
              <span>Passage</span>
              <strong>{{ lastResult.extraction?.passages.length || 0 }}</strong>
            </div>
          </div>
          <div v-if="analysisSummary" class="mt-4 p-3 bg-emerald-50 border border-emerald-100 rounded text-sm text-emerald-800">
            {{ analysisSummary }}
          </div>
          <div v-if="error" class="mt-4 p-3 bg-rose-50 border border-rose-100 rounded text-sm text-rose-700">{{ error }}</div>
        </div>
      </section>

      <aside class="space-y-4">
        <div class="bg-white border border-slate-200 rounded-lg p-4">
          <h2 class="font-bold text-slate-900 mb-3">创建案件</h2>
          <label class="label">案件标题</label>
          <input v-model="newCaseTitle" class="input" placeholder="例如：杨周武徇私枉法案" />
          <label class="label mt-3">案情说明</label>
          <textarea v-model="newCaseDescription" class="input min-h-24" placeholder="可选"></textarea>
        </div>

        <div class="bg-white border border-slate-200 rounded-lg p-4">
          <h2 class="font-bold text-slate-900 mb-3">导入文本证据</h2>
          <label class="label">证据标题</label>
          <input v-model="textTitle" class="input" placeholder="证据1-1 接警登记表" />
          <label class="label mt-3">证据正文</label>
          <textarea v-model="textContent" class="input min-h-32" placeholder="粘贴笔录、报告或其他证据文本"></textarea>
          <button class="btn-primary w-full mt-3" :disabled="!selectedCaseId || !textContent.trim()" @click="ingestText">导入文本</button>
        </div>

        <div class="bg-white border border-slate-200 rounded-lg p-4">
          <h2 class="font-bold text-slate-900 mb-3">导入流水文件</h2>
          <input class="block w-full text-sm" type="file" accept=".csv,.xlsx,.json,.txt" @change="onFileChange" />
          <button class="btn-primary w-full mt-3" :disabled="!selectedCaseId || !selectedFile" @click="ingestFile">导入文件</button>
          <p class="text-xs text-slate-500 mt-2">建议先用 `data/processed/*.csv` 或 `.xlsx` 联调。</p>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { Database } from 'lucide-vue-next';
import { backendApi, type CaseSummary, type IngestionResult } from '../api/backend';

const router = useRouter();
const cases = ref<CaseSummary[]>([]);
const loading = ref(false);
const running = ref(false);
const selectedCaseId = ref(localStorage.getItem('active_case_id') || '');
const newCaseTitle = ref('杨周武徇私枉法案');
const newCaseDescription = ref('围绕徇私动机、明知、异常资金往来和执法处置过程进行证据碰撞。');
const textTitle = ref('');
const textContent = ref('');
const selectedFile = ref<File | null>(null);
const lastResult = ref<IngestionResult | null>(null);
const analysisSummary = ref('');
const error = ref('');

onMounted(loadCases);

async function loadCases() {
  loading.value = true;
  error.value = '';
  try {
    cases.value = await backendApi.listCases();
    if (!selectedCaseId.value && cases.value[0]) selectCase(cases.value[0].case_id);
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    loading.value = false;
  }
}

async function createCase() {
  error.value = '';
  const title = newCaseTitle.value.trim();
  if (!title) return;
  try {
    const item = await backendApi.createCase(title, newCaseDescription.value);
    await loadCases();
    selectCase(item.case_id);
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
}

function selectCase(caseId: string) {
  selectedCaseId.value = caseId;
  localStorage.setItem('active_case_id', caseId);
}

async function ingestText() {
  if (!selectedCaseId.value) return;
  error.value = '';
  lastResult.value = await backendApi.ingestText(selectedCaseId.value, textTitle.value || '文本证据', textContent.value, '笔录');
  textContent.value = '';
  await loadCases();
}

function onFileChange(event: Event) {
  selectedFile.value = (event.target as HTMLInputElement).files?.[0] || null;
}

async function ingestFile() {
  if (!selectedCaseId.value || !selectedFile.value) return;
  error.value = '';
  const file = selectedFile.value;
  const sourceType = file.name.endsWith('.csv') || file.name.endsWith('.xlsx') ? file.name.split('.').pop() || 'unknown' : 'unknown';
  lastResult.value = await backendApi.ingestFile(selectedCaseId.value, file, sourceType, file.name);
  await loadCases();
}

async function runAnalysis() {
  if (!selectedCaseId.value) return;
  running.value = true;
  error.value = '';
  try {
    const result = await backendApi.runAnalysis(selectedCaseId.value);
    analysisSummary.value = result.summary;
    await router.push('/graph');
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    running.value = false;
  }
}

function statusLabel(status: string) {
  return status === 'analyzed' ? '已分析' : status === 'data_ingested' ? '已导入' : '新建';
}
</script>

<style scoped>
.btn-primary {
  border-radius: 8px;
  background: #0f766e;
  color: white;
  padding: 9px 13px;
  font-size: 13px;
  font-weight: 700;
}
.btn-secondary {
  border-radius: 8px;
  border: 1px solid #cbd5e1;
  padding: 9px 13px;
  font-size: 13px;
  font-weight: 700;
}
.btn-primary:disabled,
.btn-secondary:disabled {
  opacity: 0.45;
}
.input {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 9px 10px;
  font-size: 13px;
}
.label {
  display: block;
  font-size: 12px;
  font-weight: 700;
  color: #475569;
  margin-bottom: 6px;
}
.tag {
  border-radius: 999px;
  background: #e2e8f0;
  color: #334155;
  padding: 3px 8px;
  font-size: 12px;
}
.metric {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
}
.metric span {
  display: block;
  color: #64748b;
  font-size: 12px;
}
.metric strong {
  display: block;
  margin-top: 4px;
  font-size: 22px;
  color: #0f172a;
}
</style>
