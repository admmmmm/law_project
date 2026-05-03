<template>
  <div class="portrait-page">
    <section class="shell">
      <header class="hero">
        <div>
          <h1>画像报告</h1>
          <p>报告中的每一句结论都可以单独点击，查看证据原文与 HippoRAG PPR 溯源。</p>
        </div>
        <button class="primary-btn" :disabled="!activeCaseId || loading" @click="generateReport">
          {{ loading ? '生成中...' : '生成画像报告' }}
        </button>
      </header>

      <div class="case-line">
        <span>当前案件：</span>
        <code>{{ activeCaseId || '未选择案件' }}</code>
      </div>
      <p v-if="!activeCaseId" class="warn">请先到“案件导入”页新建或选择案件。</p>
      <p v-if="error" class="error">{{ error }}</p>

      <section v-if="!report" class="empty-report">
        暂无报告。运行智能分析后，再生成画像报告效果更完整。
      </section>

      <section v-else class="report-card">
        <div class="report-head">
          <h2>{{ report.title }}</h2>
          <p>报告 ID：{{ report.report_id }} / 生成时间：{{ formatTime(report.generated_at) }}</p>
        </div>

        <article v-for="section in report.sections" :key="section.title" class="report-section">
          <h3>{{ section.title }}</h3>
          <div v-if="sectionClaims(section).length" class="items">
            <button
              v-for="claim in sectionClaims(section)"
              :key="claim.claim_id"
              class="claim-sentence"
              :class="[claim.status, { hover: hoveredClaim === claim.claim_id, active: traceText === cleanSourceSentence(claim.text) }]"
              @mouseenter="hoveredClaim = claim.claim_id"
              @mouseleave="hoveredClaim = ''"
              @click="openClaimTrace(section.title, claim)"
            >
              <span v-html="renderMarkdown(cleanSourceSentence(claim.text))" />
              <small>{{ claimStatusLabel(claim.status) }} / {{ Math.round((claim.confidence || 0) * 100) }}%</small>
            </button>
          </div>
          <div v-else class="items">
            <div v-for="item in section.items" :key="item" class="claim-group">
              <button
                v-for="sentence in sourceableSentences(item)"
                :key="sentence"
                class="claim-sentence"
                :class="{ hover: hoveredClaim === sentence, active: traceText === sentence }"
                @mouseenter="hoveredClaim = sentence"
                @mouseleave="hoveredClaim = ''"
                @click="openTrace(section.title, sentence)"
              >
                <span v-html="renderMarkdown(sentence)" />
              </button>
            </div>
          </div>
        </article>

        <section class="suggestions">
          <h3>参考建议</h3>
          <div v-for="item in report.suggestions" :key="item" class="claim-group">
            <button
              v-for="sentence in sourceableSentences(item)"
              :key="sentence"
              class="claim-sentence"
              :class="{ hover: hoveredClaim === sentence, active: traceText === sentence }"
              @mouseenter="hoveredClaim = sentence"
              @mouseleave="hoveredClaim = ''"
              @click="openTrace('参考建议', sentence)"
            >
              <span v-html="renderMarkdown(sentence)" />
            </button>
          </div>
        </section>
      </section>
    </section>

    <aside v-if="traceOpen" class="trace-panel">
      <div class="trace-head">
        <div>
          <h2>{{ traceLabel }}</h2>
          <p>当前结论句的证据原文与 HippoRAG PPR 溯源。</p>
        </div>
        <button @click="traceOpen = false">关闭</button>
      </div>
      <div class="trace-section">
        <h3>当前结论句</h3>
        <div class="markdown" v-html="renderMarkdown(traceText)" />
      </div>
      <div class="trace-section">
        <h3>HippoRAG PPR 检索结果</h3>
        <div v-if="traceLoading" class="muted">正在检索证据...</div>
        <div v-if="traceResult?.error" class="trace-error">{{ traceResult.error }}</div>
        <div v-if="!traceLoading && !traceResult?.passages.length" class="muted">暂无 PPR passage 结果。</div>
        <article v-for="item in traceResult?.passages || []" :key="`${item.rank}-${item.evidence_id}-${item.score}`" class="ppr-card">
          <div>
            <strong>#{{ item.rank }} / score {{ item.score.toFixed(4) }}</strong>
            <span>{{ item.evidence_title || item.evidence_id || '未映射证据' }}</span>
          </div>
          <p>{{ item.passage }}</p>
        </article>
      </div>
      <div class="trace-section">
        <h3>证据原文</h3>
        <details v-for="item in traceEvidence" :key="item.evidence_id" class="evidence-doc">
          <summary>{{ item.title }}</summary>
          <pre>{{ item.content }}</pre>
        </details>
      </div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { backendApi, type EvidenceDetail, type PortraitReport, type TraceResult } from '../api/backend';

const activeCaseId = ref(localStorage.getItem('active_case_id') || '');
const loading = ref(false);
const error = ref('');
const report = ref<PortraitReport | null>(null);
const traceOpen = ref(false);
const traceLoading = ref(false);
const traceLabel = ref('');
const traceText = ref('');
const hoveredClaim = ref('');
const traceResult = ref<TraceResult | null>(null);
const traceEvidence = ref<EvidenceDetail[]>([]);
type PortraitClaim = NonNullable<NonNullable<PortraitReport['sections'][number]['claims']>[number]>;
type PortraitSection = PortraitReport['sections'][number];

async function generateReport() {
  if (!activeCaseId.value) return;
  loading.value = true;
  error.value = '';
  try {
    report.value = await backendApi.generatePortrait(activeCaseId.value);
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    loading.value = false;
  }
}

async function openTrace(label: string, text: string) {
  if (!activeCaseId.value) return;
  const cleanText = cleanSourceSentence(text);
  traceOpen.value = true;
  traceLoading.value = true;
  traceLabel.value = label;
  traceText.value = cleanText;
  traceResult.value = null;
  traceEvidence.value = [];
  try {
    traceResult.value = await backendApi.traceAnalysis(activeCaseId.value, `${label}\n${cleanText}`, [], 8);
    const ids = new Set<string>();
    traceResult.value.passages.forEach((item) => {
      if (item.evidence_id && ids.size < 5) ids.add(item.evidence_id);
    });
    traceEvidence.value = await Promise.all([...ids].map((id) => backendApi.getEvidenceDetail(activeCaseId.value, id)));
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    traceLoading.value = false;
  }
}

async function openClaimTrace(label: string, claim: PortraitClaim) {
  if (!activeCaseId.value) return;
  const claimText = cleanSourceSentence(claim.text);
  traceOpen.value = true;
  traceLoading.value = true;
  traceLabel.value = `${label}${claim.element ? ` / ${claim.element}` : ''}`;
  traceText.value = claimText;
  traceResult.value = {
    case_id: activeCaseId.value,
    query: claimText,
    provider: 'claim_verifier',
    passages: claim.supporting_passages.map((item, index) => ({
      rank: index + 1,
      score: item.score,
      passage: item.passage,
      evidence_id: item.evidence_id,
      evidence_title: item.evidence_title,
    })),
    paths: [],
  };
  try {
    const ids = Array.from(new Set(claim.supporting_passages.map((item) => item.evidence_id).filter(Boolean))).slice(0, 5);
    traceEvidence.value = await Promise.all(ids.map((id) => backendApi.getEvidenceDetail(activeCaseId.value, id)));
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    traceLoading.value = false;
  }
}

function sourceableSentences(value: string) {
  const normalized = value.replace(/\r/g, '\n');
  const chunks = normalized
    .split(/\n+/)
    .flatMap((line) => line.split(/(?<=[。！？；;])/))
    .map(cleanSourceSentence)
    .filter(isSourceableSentence);
  return Array.from(new Set(chunks));
}

function sectionClaims(section: PortraitSection) {
  return (section.claims || []).filter((claim) => isSourceableSentence(cleanSourceSentence(claim.text)));
}

function cleanSourceSentence(value: string) {
  return (value || '')
    .replace(/^[-*•]\s*/, '')
    .replace(/^\d+[.、]\s*/, '')
    .replace(/\*\*/g, '')
    .replace(/==/g, '')
    .replace(/^["“”'‘’]+|["“”'‘’]+$/g, '')
    .trim();
}

function isSourceableSentence(value: string) {
  const text = cleanSourceSentence(value);
  const withoutColon = text.replace(/[：:]\s*$/, '').trim();
  if (withoutColon.length < 8) return false;
  if (/^[\s*#\-•：:]+$/.test(withoutColon)) return false;
  if (/^(结论|支持证据|仍需补强|证明力|身份|任职|职权|关键人员关系|案件对象|批准人|发信人|收信人|证明事项|来源文件)$/.test(withoutColon)) return false;
  if (/^(证据|材料|相关证据)\s*\d*(?:-\d+)?$/.test(withoutColon)) return false;
  if (/^(第一层|第二层|第三层|主体要件|客观行为|主观方面|结果与因果|抗辩预判)$/.test(withoutColon)) return false;
  return true;
}

function formatTime(value: string) {
  return new Date(value).toLocaleString();
}

function claimStatusLabel(status: string) {
  if (status === 'supported') return '证据支撑';
  if (status === 'weak') return '需复核';
  if (status === 'unsupported') return '未证实';
  if (status === 'conflict') return '证据冲突';
  return status;
}

function renderMarkdown(value: string) {
  const escaped = escapeHtml(cleanMarkdownText(value || ''));
  return escaped
    .replace(/^### (.*)$/gm, '<h4>$1</h4>')
    .replace(/^## (.*)$/gm, '<h3>$1</h3>')
    .replace(/^# (.*)$/gm, '<h2>$1</h2>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/==(.+?)==/g, '<mark>$1</mark>')
    .replace(/^- (.*)$/gm, '<div class="md-list">- $1</div>')
    .replace(/\n/g, '<br />');
}

function cleanMarkdownText(value: string) {
  return value
    .replace(/^\s*[-*•]\s+/gm, '- ')
    .replace(/\*{1,2}([^*\n：:]{1,24})\*{1,2}([：:])/g, '**$1**$2')
    .trim();
}

function escapeHtml(value: string) {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
</script>

<style scoped>
.portrait-page {
  height: 100%;
  overflow: auto;
  background: #eef3f7;
  color: #0f172a;
  padding: 24px;
}
.shell {
  max-width: 980px;
  margin: 0 auto;
}
.hero,
.report-card,
.empty-report {
  border: 1px solid #d8e1ea;
  border-radius: 10px;
  background: #ffffff;
}
.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px;
}
.hero h1 {
  font-size: 22px;
  font-weight: 900;
}
.hero p,
.case-line,
.report-head p,
.empty-report {
  color: #64748b;
  font-size: 14px;
}
.primary-btn {
  border-radius: 8px;
  background: #0f766e;
  color: #ffffff;
  padding: 10px 16px;
  font-weight: 900;
}
.primary-btn:disabled {
  opacity: 0.5;
}
.case-line {
  margin: 14px 0;
}
.warn,
.error {
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 14px;
  margin-bottom: 14px;
}
.warn {
  border: 1px solid #fde68a;
  background: #fffbeb;
  color: #92400e;
}
.error {
  border: 1px solid #fecdd3;
  background: #fff1f2;
  color: #be123c;
}
.empty-report {
  padding: 36px;
  text-align: center;
  border-style: dashed;
}
.report-card {
  padding: 22px;
}
.report-head {
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 14px;
  margin-bottom: 18px;
}
.report-head h2 {
  font-size: 20px;
  font-weight: 900;
}
.report-section {
  margin-top: 20px;
}
.report-section h3,
.suggestions h3 {
  font-size: 17px;
  font-weight: 900;
  margin-bottom: 10px;
}
.items {
  display: grid;
  gap: 9px;
}
.claim-group {
  display: grid;
  gap: 7px;
}
.claim-sentence {
  width: 100%;
  border: 1px solid #e2e8f0;
  border-radius: 9px;
  background: #f8fafc;
  padding: 11px 12px;
  color: #334155;
  font-size: 14px;
  line-height: 1.7;
  text-align: left;
}
.claim-sentence small {
  display: block;
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}
.claim-sentence:hover,
.claim-sentence.hover {
  border-color: #0f766e;
  background: #f0fdfa;
}
.claim-sentence.supported {
  border-left: 4px solid #0f766e;
}
.claim-sentence.weak {
  border-left: 4px solid #f59e0b;
}
.claim-sentence.unsupported {
  border-left: 4px solid #dc2626;
  background: #fff7f7;
}
.claim-sentence.active {
  border-color: #0f766e;
  background: #ccfbf1;
  box-shadow: inset 3px 0 0 #0f766e;
}
.suggestions {
  margin-top: 22px;
  border: 1px solid #99f6e4;
  border-radius: 10px;
  background: #f0fdfa;
  padding: 16px;
}
.suggestions .claim-sentence {
  border-color: #ccfbf1;
  background: #ffffff;
}
.trace-panel {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  z-index: 20;
  width: min(460px, 92vw);
  overflow: auto;
  border-left: 1px solid #23324b;
  background: #0f172a;
  color: #ffffff;
  padding: 16px;
  box-shadow: -16px 0 40px rgba(15, 23, 42, 0.22);
}
.trace-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 14px;
}
.trace-head h2 {
  font-size: 18px;
  font-weight: 900;
}
.trace-head p,
.muted {
  color: #94a3b8;
  font-size: 13px;
}
.trace-head button {
  align-self: start;
  border: 1px solid #334155;
  border-radius: 7px;
  padding: 6px 10px;
}
.trace-section {
  border: 1px solid #23324b;
  border-radius: 9px;
  background: #111c31;
  padding: 13px;
  margin-bottom: 12px;
}
.trace-section h3 {
  font-weight: 900;
  margin-bottom: 8px;
}
.trace-error {
  border: 1px solid #7f1d1d;
  border-radius: 7px;
  background: #450a0a;
  color: #fecaca;
  padding: 8px;
  font-size: 12px;
  line-height: 1.5;
  margin-bottom: 8px;
}
.ppr-card,
.evidence-doc {
  border-top: 1px solid #23324b;
  padding-top: 10px;
  margin-top: 10px;
}
.evidence-doc summary {
  cursor: pointer;
  font-weight: 900;
}
.ppr-card div {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  color: #ffffff;
  font-size: 13px;
}
.ppr-card span {
  color: #7dd3fc;
  font-size: 12px;
  text-align: right;
}
.ppr-card p,
.evidence-doc pre {
  margin-top: 6px;
  color: #cbd5e1;
  font-size: 12px;
  line-height: 1.6;
}
.evidence-doc pre {
  max-height: 360px;
  overflow: auto;
  white-space: pre-wrap;
}
.markdown {
  color: inherit;
  font-size: 14px;
  line-height: 1.7;
}
.markdown :deep(strong),
.claim-sentence :deep(strong) {
  color: #0f172a;
  font-weight: 900;
}
.markdown :deep(mark),
.claim-sentence :deep(mark) {
  border-radius: 4px;
  background: #fed7aa;
  color: #9a3412;
  padding: 0 3px;
}
</style>
