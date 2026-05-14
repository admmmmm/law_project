<template>
  <div class="page">
    <div class="page-narrow">
      <section class="panel overview-hero">
        <div>
          <div class="eyebrow">案件空间 / 案件概览</div>
          <h2 class="page-title">{{ overview?.name || '当前案件' }}</h2>
          <p class="muted">case_id：{{ caseId }}</p>
        </div>
        <div class="actions">
          <button class="btn" :disabled="loading" @click="loadOverview">刷新状态</button>
          <button class="btn primary" :disabled="!caseId" @click="goToGraph">进入证据地图</button>
        </div>
      </section>

      <div v-if="error" class="error-state" style="margin-top: 16px;">
        <h2>案件加载失败</h2>
        <p class="muted">{{ error }}</p>
        <button class="btn primary" style="margin-top: 14px;" @click="loadOverview">重试</button>
      </div>

      <template v-else>
        <section class="grid-2" style="margin-top: 16px; align-items: start;">
          <div class="panel">
            <h3 class="section-title">案件基础信息</h3>
            <div class="overview-fields">
              <div><span>案件名称</span><strong>{{ overview?.name || '-' }}</strong></div>
              <div><span>案号 / 编号</span><strong>{{ overview?.case_number || overview?.case_id || '-' }}</strong></div>
              <div><span>罪名 / 案件类型</span><strong>{{ overview?.offense || overview?.case_type || '可后续补充' }}</strong></div>
              <div><span>当前阶段</span><strong>{{ overview?.stage || '材料整理中' }}</strong></div>
              <div><span>嫌疑人</span><strong>{{ (overview?.suspects || []).join('、') || '-' }}</strong></div>
              <div><span>最近更新</span><strong>{{ formatDate(overview?.updated_at || overview?.created_at || '') }}</strong></div>
            </div>
          </div>

          <div class="panel">
            <h3 class="section-title">推荐下一步</h3>
            <div class="next-step-card">
              <strong>{{ overview?.next_step?.label || '继续完善案件材料' }}</strong>
              <p class="muted">{{ overview?.next_step?.reason || '可以继续导入证据，或进入证据地图查看当前结构。' }}</p>
              <div class="actions" style="margin-top: 12px;">
                <button class="btn primary" @click="goNextStep">前往处理</button>
              </div>
            </div>
          </div>
        </section>

        <section class="stats-band" style="margin-top: 16px;">
          <div><span>已导入证据</span><strong>{{ stat('evidence_count') }}</strong></div>
          <div><span>文件图节点</span><strong>{{ stat('document_graph_node_count') }}</strong></div>
          <div><span>片段图节点</span><strong>{{ stat('passage_graph_node_count') }}</strong></div>
          <div><span>原始图谱</span><strong>{{ stat('raw_graph_node_count') }} / {{ stat('raw_graph_edge_count') }}</strong></div>
          <div><span>分析 / 画像</span><strong>{{ stat('analysis_count') }} / {{ stat('portrait_count') }}</strong></div>
        </section>

        <section class="panel" style="margin-top: 16px;">
          <div class="toolbar">
            <div>
              <h3 class="section-title">已导入证据</h3>
              <p class="muted">点击证据条目查看 NAME、BRIEF、ID、原文和片段信息。</p>
            </div>
          </div>

          <div v-if="!overview?.recent_evidence?.length && !loading" class="empty-state" style="margin-top: 14px;">
            <h2>尚未导入证据</h2>
            <p class="muted">可以先创建空案件，稍后继续导入证据材料。</p>
          </div>

          <div v-else class="evidence-list">
            <button v-for="item in overview?.recent_evidence || []" :key="item.evidence_id" class="evidence-card" @click="openEvidence(item.evidence_id)">
              <div class="row-between">
                <strong>{{ item.name || item.evidence_id }}</strong>
                <span class="chip">{{ item.status || '已解析' }}</span>
              </div>
              <p class="muted">{{ item.brief || '暂无摘要。' }}</p>
              <div class="evidence-meta">
                <span>ID：{{ item.evidence_id }}</span>
                <span>类型：{{ item.evidence_type || '未知类型' }}</span>
                <span>片段：{{ item.passage_count || 0 }}</span>
              </div>
            </button>
          </div>
        </section>
      </template>

      <aside v-if="selectedEvidence" class="detail-drawer">
        <div class="toolbar">
          <div>
            <div class="eyebrow">证据详情</div>
            <h3>{{ selectedEvidence.name || selectedEvidence.title || selectedEvidence.evidence_id }}</h3>
          </div>
          <button class="btn" @click="selectedEvidence = null">关闭</button>
        </div>
        <div class="detail-grid">
          <div><span>NAME</span><strong>{{ selectedEvidence.name || selectedEvidence.title || '-' }}</strong></div>
          <div><span>BRIEF</span><strong>{{ selectedEvidence.brief || '-' }}</strong></div>
          <div><span>ID</span><strong>{{ selectedEvidence.evidence_id }}</strong></div>
          <div><span>类型</span><strong>{{ selectedEvidence.evidence_type || selectedEvidence.source_type || '-' }}</strong></div>
          <div><span>证明事项</span><strong>{{ selectedEvidence.proof_item || '-' }}</strong></div>
        </div>
        <section class="panel-soft">
          <h4>原文预览</h4>
          <p class="evidence-content">{{ selectedEvidence.content || '暂无原文内容。' }}</p>
        </section>
        <section class="panel-soft">
          <h4>片段</h4>
          <div v-if="selectedEvidence.passages?.length" class="passage-list">
            <p v-for="passage in selectedEvidence.passages.slice(0, 6)" :key="passage.passage_id">{{ passage.text }}</p>
          </div>
          <p v-else class="muted">暂无片段。</p>
        </section>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { backendApi, type CaseOverview, type EvidenceDetail } from '../api/backend';

const route = useRoute();
const router = useRouter();
const caseId = computed(() => String(route.params.caseId || localStorage.getItem('active_case_id') || ''));
const overview = ref<CaseOverview | null>(null);
const selectedEvidence = ref<EvidenceDetail | null>(null);
const loading = ref(false);
const error = ref('');

onMounted(loadOverview);

async function loadOverview() {
  if (!caseId.value) return;
  loading.value = true;
  error.value = '';
  try {
    overview.value = await backendApi.getCaseOverview(caseId.value);
    localStorage.setItem(`case_title:${caseId.value}`, overview.value.name || caseId.value);
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    loading.value = false;
  }
}

function stat(key: string) {
  return overview.value?.stats?.[key] ?? 0;
}

function goToGraph() {
  router.push(`/cases/${caseId.value}/graph?layer=document`);
}

function goNextStep() {
  const target = overview.value?.next_step?.target;
  if (target && target.startsWith('/cases/')) router.push(target);
  else goToGraph();
}

async function openEvidence(evidenceId: string) {
  selectedEvidence.value = await backendApi.getEvidenceDetail(caseId.value, evidenceId);
}

function formatDate(value: string) {
  if (!value) return '-';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : `${date.getFullYear()}-${date.getMonth() + 1}-${date.getDate()}`;
}
</script>

<style scoped>
.overview-hero {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}
.overview-fields,
.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.overview-fields div,
.stats-band div,
.detail-grid div {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #f8fafc;
  padding: 12px;
}
.overview-fields span,
.stats-band span,
.detail-grid span {
  display: block;
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 6px;
}
.overview-fields strong,
.stats-band strong,
.detail-grid strong {
  color: var(--text);
  font-size: 15px;
}
.stats-band {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}
.evidence-list {
  margin-top: 14px;
  display: grid;
  gap: 10px;
}
.evidence-card {
  text-align: left;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  padding: 14px;
}
.evidence-card:hover {
  border-color: var(--primary);
}
.evidence-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 18px;
  color: var(--muted);
  font-size: 12px;
  margin-top: 10px;
}
.detail-drawer {
  position: fixed;
  top: 104px;
  right: 20px;
  bottom: 20px;
  width: min(520px, calc(100vw - 40px));
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.18);
  padding: 16px;
  overflow: auto;
  display: grid;
  align-content: start;
  gap: 14px;
  z-index: 20;
}
.evidence-content,
.passage-list p {
  white-space: pre-wrap;
  word-break: break-word;
  color: #334155;
  line-height: 1.7;
  font-size: 13px;
}
@media (max-width: 1000px) {
  .overview-hero,
  .overview-fields,
  .stats-band,
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
