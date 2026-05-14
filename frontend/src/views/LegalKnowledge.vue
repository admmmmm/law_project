<template>
  <div class="knowledge-page">
    <div class="shell">
      <header class="page-head">
        <div>
          <h1>法律知识库</h1>
          <p>浏览 14 个罪名模板，并检索法律条文、证据标准和办案流程。</p>
        </div>
        <button class="secondary" @click="router.push('/')">返回案件管理</button>
      </header>

      <section class="knowledge-grid">
        <aside class="panel">
          <div class="panel-head">
            <div>
              <h2>罪名模板</h2>
              <p>{{ offenseTemplates.length }} 个模板</p>
            </div>
          </div>
          <button
            v-for="item in offenseTemplates"
            :key="item.offense_id"
            class="template-row"
            :class="{ active: item.offense_id === selectedOffenseId }"
            @click="selectTemplate(item.offense_id)"
          >
            <strong>{{ item.name }}</strong>
            <span>{{ item.category || '未分类' }} · {{ item.status || 'skeleton' }}</span>
            <small>{{ item.article_hint || item.offense_id }}</small>
          </button>

          <div class="procedure-box">
            <div class="panel-head compact">
              <div>
                <h2>系统先验</h2>
                <p>{{ procedureFlows.length }} 份</p>
              </div>
            </div>
            <button
              v-for="item in procedureFlows"
              :key="item.relative_path"
              class="knowledge-row"
              @click="query = `${item.title} 应有材料 流程异常 证据缺口`"
            >
              <strong>{{ item.title }}</strong>
              <span>{{ item.kind }} · {{ item.relative_path }}</span>
            </button>
          </div>
        </aside>

        <main class="panel">
          <div class="panel-head">
            <div>
              <h2>{{ selectedTemplateName }}</h2>
              <p>模板浏览与法律知识检索</p>
            </div>
          </div>

          <div class="search-line">
            <input v-model="query" class="field" placeholder="例如：徇私枉法罪需要核查哪些证据缺口" @keydown.enter="retrieve" />
            <button class="primary" :disabled="loading || !query.trim()" @click="retrieve">知识检索</button>
          </div>

          <section class="knowledge-ingest">
            <details>
              <summary>添加系统级办案先验 / 法律知识</summary>
              <p>这里保存的是全系统知识，不属于单个案件。保存后会进入法律知识检索库。</p>
              <input v-model="newKnowledge.title" class="field" placeholder="标题，例如：刑事案件办理标准流程" />
              <textarea v-model="newKnowledge.content" rows="8" placeholder="粘贴流程图、应有材料、证据标准、专家补充意见等 Markdown/文本内容。" />
              <div class="upload-line">
                <button class="primary" :disabled="loading || !newKnowledge.title.trim() || !newKnowledge.content.trim()" @click="saveKnowledge">保存文本</button>
                <label class="secondary file-label">
                  上传 md/txt
                  <input type="file" accept=".md,.txt,.json" @change="uploadKnowledge" />
                </label>
              </div>
            </details>
          </section>

          <div v-if="selectedTemplate" class="template-detail">
            <h3>优先核查项</h3>
            <div class="chips">
              <span v-for="item in selectedTemplate.priority_elements || []" :key="item">{{ item }}</span>
            </div>
          </div>

          <div v-if="error" class="error">{{ error }}</div>

          <section v-if="result" class="results">
            <h3>检索结果</h3>
            <div v-if="result.error" class="error">{{ result.error }}</div>
            <article v-for="passage in result.passages" :key="`${passage.rank}-${passage.passage}`" class="passage">
              <div>
                <strong>结果 {{ passage.rank }}</strong>
                <span>{{ passage.evidence_title || '法律知识库' }}</span>
              </div>
              <p>{{ passage.passage }}</p>
            </article>
          </section>

          <section v-else class="hint">
            选择左侧罪名后可以查看模板；输入问题后会检索法律知识库。
          </section>
        </main>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { backendApi, type OffenseTemplateSummary, type ProcedureFlowSummary, type TraceResult } from '../api/backend';

const router = useRouter();
const offenseTemplates = ref<OffenseTemplateSummary[]>([]);
const procedureFlows = ref<ProcedureFlowSummary[]>([]);
const selectedOffenseId = ref('');
const query = ref('');
const result = ref<TraceResult | null>(null);
const loading = ref(false);
const error = ref('');
const newKnowledge = ref({ title: '', content: '' });

const selectedTemplate = computed(() => offenseTemplates.value.find((item) => item.offense_id === selectedOffenseId.value) || null);
const selectedTemplateName = computed(() => selectedTemplate.value?.name || '法律知识检索');

onMounted(async () => {
  try {
    offenseTemplates.value = await backendApi.listOffenseTemplates();
    procedureFlows.value = await backendApi.listProcedureFlows();
    selectedOffenseId.value = offenseTemplates.value[0]?.offense_id || '';
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
});

function selectTemplate(offenseId: string) {
  selectedOffenseId.value = offenseId;
  result.value = null;
  if (!query.value.trim()) {
    const item = selectedTemplate.value;
    query.value = `${item?.name || ''} 需要核查哪些证据和缺口`.trim();
  }
}

async function saveKnowledge() {
  loading.value = true;
  error.value = '';
  try {
    await backendApi.createProcedureFlow({
      title: newKnowledge.value.title.trim(),
      content: newKnowledge.value.content.trim(),
      kind: 'user_knowledge',
    });
    newKnowledge.value = { title: '', content: '' };
    procedureFlows.value = await backendApi.listProcedureFlows();
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    loading.value = false;
  }
}

async function uploadKnowledge(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  loading.value = true;
  error.value = '';
  try {
    await backendApi.uploadProcedureFlow(file);
    procedureFlows.value = await backendApi.listProcedureFlows();
    input.value = '';
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    loading.value = false;
  }
}

async function retrieve() {
  if (!query.value.trim()) return;
  loading.value = true;
  error.value = '';
  try {
    result.value = await backendApi.retrieveLegalKnowledge(query.value.trim(), selectedOffenseId.value || null, 8);
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.knowledge-page {
  height: 100%;
  overflow: auto;
  background: #f1f5f9;
  color: #0f172a;
  padding: 20px;
}

.shell {
  max-width: 1360px;
  margin: 0 auto;
}

.page-head,
.panel-head,
.search-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.panel-head.compact {
  margin-top: 18px;
}

.page-head {
  margin-bottom: 18px;
}

h1,
h2,
h3,
p {
  margin: 0;
}

.page-head p,
.panel-head p,
.hint,
.template-row span,
.template-row small {
  color: #64748b;
}

.knowledge-grid {
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  gap: 16px;
}

.panel {
  background: #fff;
  border: 1px solid #dbe3ee;
  border-radius: 14px;
  padding: 18px;
}

.template-row {
  width: 100%;
  display: grid;
  gap: 4px;
  text-align: left;
  margin-top: 10px;
  padding: 12px;
  border: 1px solid #dbe3ee;
  border-radius: 10px;
  background: #fff;
  color: #0f172a;
  cursor: pointer;
}

.template-row.active {
  border-color: #0f766e;
  background: #ecfdf5;
}

.procedure-box {
  margin-top: 18px;
  border-top: 1px solid #e2e8f0;
}

.knowledge-row {
  width: 100%;
  display: grid;
  gap: 4px;
  text-align: left;
  margin-top: 10px;
  padding: 10px;
  border: 1px solid #c7d2fe;
  border-radius: 10px;
  background: #f8fafc;
  color: #0f172a;
  cursor: pointer;
}

.knowledge-row span {
  color: #64748b;
  font-size: 12px;
}

.field {
  width: 100%;
  min-height: 42px;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 0 12px;
  color: #0f172a;
  background: #fff;
}

.primary,
.secondary {
  min-height: 42px;
  border-radius: 10px;
  border: 1px solid #cbd5e1;
  padding: 0 16px;
  font-weight: 700;
  cursor: pointer;
}

.primary {
  background: #0f766e;
  color: #fff;
  border-color: #0f766e;
}

.secondary {
  background: #fff;
  color: #0f172a;
}

.template-detail,
.results,
.knowledge-ingest {
  margin-top: 18px;
}

.knowledge-ingest {
  border: 1px solid #dbe3ee;
  border-radius: 12px;
  padding: 12px;
  background: #f8fafc;
}

.knowledge-ingest summary {
  cursor: pointer;
  font-weight: 900;
  color: #0f766e;
}

.knowledge-ingest p {
  margin-top: 8px;
  color: #64748b;
}

.knowledge-ingest textarea {
  width: 100%;
  margin-top: 10px;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 10px 12px;
  color: #0f172a;
  background: #fff;
  resize: vertical;
}

.knowledge-ingest .field {
  margin-top: 10px;
}

.upload-line {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 10px;
}

.file-label {
  display: inline-flex;
  align-items: center;
}

.file-label input {
  display: none;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.chips span {
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  padding: 6px 10px;
  background: #f8fafc;
}

.passage {
  margin-top: 12px;
  border: 1px solid #dbe3ee;
  border-radius: 12px;
  padding: 14px;
  background: #f8fafc;
}

.passage div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.passage p {
  white-space: pre-wrap;
  line-height: 1.7;
}

.error {
  margin-top: 12px;
  color: #b91c1c;
  font-weight: 700;
}

@media (max-width: 900px) {
  .knowledge-grid {
    grid-template-columns: 1fr;
  }
}
</style>
