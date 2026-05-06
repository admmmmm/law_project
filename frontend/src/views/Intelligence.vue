<template>
  <div class="analysis-page">
    <header class="hero">
      <div>
        <h1>智能分析</h1>
        <p>假设验证和可疑资金流以会话保存。点击卡片查看，继续追问，或删除会话。</p>
      </div>
    </header>

    <section class="case-line">
      <span>当前案件：</span>
      <code>{{ activeCaseId || '未选择案件' }}</code>
    </section>
    <p v-if="!activeCaseId" class="warn">请先到“案件管理”页新建或选择案件。</p>
    <p v-if="error" class="error">{{ error }}</p>
    <AsyncProgressBar v-if="progress.active.value" compact :value="progress.value.value" :label="progress.label.value" :detail="progress.detail.value" />

    <section class="mode-tabs">
      <button :class="{ active: activeMode === 'hypothesis' }" @click="switchMode('hypothesis')">假设验证</button>
      <button :class="{ active: activeMode === 'financial_flow' }" @click="switchMode('financial_flow')">可疑资金流</button>
      <button class="secondary" @click="showNewThread = !showNewThread">新建对话</button>
    </section>

    <section v-if="showNewThread" class="new-thread">
      <h2>{{ activeMode === 'hypothesis' ? '新建假设验证' : '新建可疑资金流分析' }}</h2>
      <input v-model="newTitle" class="field" placeholder="可选：给这轮分析起个标题" />
      <textarea
        v-model="newQuestion"
        rows="5"
        :placeholder="activeMode === 'hypothesis' ? '输入检察官假设，例如：某些执法文书可能存在倒签或补录。' : '输入资金流问题，留空也可以让系统按默认方向分析。'"
      />
      <button class="primary-btn" :disabled="loading || !activeCaseId || !effectiveNewQuestion.trim()" @click="createThread">创建并分析</button>
    </section>

    <section class="conversation-layout">
      <aside class="thread-panel">
        <div class="panel-head">
          <div>
            <h2>会话卡片</h2>
            <p>{{ threads.length }} 个</p>
          </div>
          <button class="secondary small" :disabled="loading" @click="loadThreads">刷新</button>
        </div>
        <div v-if="threads.length === 0" class="empty">暂无会话。点击“新建对话”开始。</div>
        <button v-for="thread in threads" :key="thread.thread_id" class="thread-card" :class="{ active: selectedThreadId === thread.thread_id }" @click="selectThread(thread.thread_id)">
          <div>
            <strong>{{ thread.title }}</strong>
            <span>{{ labelForMode(thread.mode) }} · {{ thread.message_count }} 条消息</span>
            <p>{{ thread.summary || '暂无摘要' }}</p>
          </div>
          <button class="delete-btn" @click.stop="deleteThread(thread)">删除</button>
        </button>
      </aside>

      <main class="detail-panel">
        <div v-if="!threadDetail" class="empty detail-empty">选择左侧会话，或新建一个分析对话。</div>
        <template v-else>
          <div class="detail-head">
            <div>
              <h2>{{ threadDetail.thread.title }}</h2>
              <p>{{ labelForMode(threadDetail.thread.mode) }} / {{ threadDetail.thread.thread_id }}</p>
            </div>
          </div>

          <article v-for="message in threadDetail.messages" :key="message.message_id" class="message" :class="message.role">
            <div class="message-role">{{ message.role === 'user' ? '检察官' : 'DeepSeek + RAG' }}</div>
            <div v-if="message.role === 'assistant'" class="answer-text">
              <button
                v-for="sentence in message.claims.length ? message.claims : fallbackSentences(message.content)"
                :key="sentence.sentence_id"
                class="sentence"
                :class="sentence.status"
                @click="selectedSentence = sentence"
              >
                <span v-html="renderInlineMarkdown(sentence.text)" />
              </button>
            </div>
            <div v-else class="message-text">{{ message.content }}</div>
            <p v-if="message.error" class="muted">提示：{{ message.error }}</p>
          </article>

          <section class="followup">
            <h3>继续追问</h3>
            <p class="hint">输入 <code>@</code> 后可选择证据。标准格式会插入为 <code>@[证据标题](证据ID)</code>。</p>
            <textarea v-model="followup" rows="4" placeholder="例如：请查看 @ 后选择某份证据，再重新判断这个假设。" @input="updateMentionSuggestions" />
            <div v-if="mentionSuggestions.length" class="mention-menu">
              <button v-for="item in mentionSuggestions" :key="item.evidence_id" @click="insertMention(item)">
                <strong>{{ item.title }}</strong>
                <span>{{ item.evidence_id }}</span>
              </button>
            </div>
            <button class="primary-btn" :disabled="loading || !followup.trim()" @click="sendFollowup">发送追问</button>
          </section>
        </template>
      </main>

      <aside class="source-drawer" :class="{ open: selectedSentence }">
        <button class="close-btn" @click="selectedSentence = null">关闭</button>
        <h2>句子溯源</h2>
        <p v-if="!selectedSentence" class="empty">点击答案中的句子查看来源。</p>
        <template v-else>
          <div class="source-status" :class="selectedSentence.status">
            {{ statusLabel(selectedSentence.status) }} / {{ Math.round(selectedSentence.confidence * 100) }}%
          </div>
          <p class="selected-text">{{ selectedSentence.text }}</p>
          <h3>证据 passage</h3>
          <article v-for="passage in selectedSentence.supporting_passages" :key="`${passage.rank}-${passage.passage}`" class="passage">
            <strong>#{{ passage.rank }} / {{ passage.score.toFixed(3) }}</strong>
            <span>{{ passage.evidence_title || passage.evidence_id || '未映射证据' }}</span>
            <p>{{ passage.passage }}</p>
          </article>
          <p v-if="!selectedSentence.supporting_passages.length" class="empty">暂无可靠 passage 支撑。</p>
        </template>
      </aside>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { backendApi, type AnalysisThread, type AnalysisThreadDetail, type EvidenceRecord, type GroundedSentence } from '../api/backend';
import AsyncProgressBar from '../components/AsyncProgressBar.vue';
import { useSimulatedProgress } from '../composables/useSimulatedProgress';

type ThreadMode = 'hypothesis' | 'financial_flow';

const activeCaseId = ref(localStorage.getItem('active_case_id') || '');
const activeMode = ref<ThreadMode>('hypothesis');
const threads = ref<AnalysisThread[]>([]);
const threadDetail = ref<AnalysisThreadDetail | null>(null);
const selectedThreadId = ref(localStorage.getItem('active_analysis_thread_id') || '');
const evidence = ref<EvidenceRecord[]>([]);
const loading = ref(false);
const error = ref('');
const showNewThread = ref(false);
const newTitle = ref('');
const newQuestion = ref('');
const followup = ref('');
const mentionSuggestions = ref<EvidenceRecord[]>([]);
const selectedSentence = ref<GroundedSentence | null>(null);
const progress = useSimulatedProgress();

const effectiveNewQuestion = computed(() => {
  if (newQuestion.value.trim()) return newQuestion.value.trim();
  return activeMode.value === 'financial_flow'
    ? '请分析本案是否存在可疑资金流动、现金化、过桥账户、资金与处置节点前后呼应的问题。'
    : '';
});

onMounted(async () => {
  await loadEvidence();
  await loadThreads();
  if (selectedThreadId.value) await selectThread(selectedThreadId.value);
});

async function switchMode(mode: ThreadMode) {
  activeMode.value = mode;
  selectedSentence.value = null;
  threadDetail.value = null;
  selectedThreadId.value = '';
  await loadThreads();
}

async function loadThreads() {
  if (!activeCaseId.value) return;
  threads.value = await backendApi.listAnalysisThreads(activeCaseId.value, activeMode.value);
}

async function loadEvidence() {
  if (!activeCaseId.value) return;
  try {
    evidence.value = await backendApi.listEvidence(activeCaseId.value);
  } catch {
    evidence.value = [];
  }
}

async function createThread() {
  await runTask('正在创建分析会话', async () => {
    const detail = await backendApi.createAnalysisThread(activeCaseId.value, {
      mode: activeMode.value,
      title: newTitle.value.trim() || null,
      initial_question: effectiveNewQuestion.value,
    });
    threadDetail.value = detail;
    selectedThreadId.value = detail.thread.thread_id;
    localStorage.setItem('active_analysis_thread_id', selectedThreadId.value);
    newTitle.value = '';
    newQuestion.value = '';
    showNewThread.value = false;
    await loadThreads();
  });
}

async function selectThread(threadId: string) {
  if (!threadId || !activeCaseId.value) return;
  selectedSentence.value = null;
  threadDetail.value = await backendApi.getAnalysisThread(activeCaseId.value, threadId);
  selectedThreadId.value = threadId;
  localStorage.setItem('active_analysis_thread_id', threadId);
}

async function sendFollowup() {
  if (!threadDetail.value || !followup.value.trim()) return;
  await runTask('正在继续追问', async () => {
    threadDetail.value = await backendApi.addAnalysisThreadMessage(activeCaseId.value, threadDetail.value!.thread.thread_id, followup.value.trim());
    selectedThreadId.value = threadDetail.value.thread.thread_id;
    followup.value = '';
    mentionSuggestions.value = [];
    selectedSentence.value = null;
    await loadThreads();
  });
}

async function deleteThread(thread: AnalysisThread) {
  const ok = window.confirm(`确定删除会话「${thread.title}」吗？`);
  if (!ok) return;
  await runTask('正在删除会话', async () => {
    await backendApi.deleteAnalysisThread(activeCaseId.value, thread.thread_id);
    if (selectedThreadId.value === thread.thread_id) {
      selectedThreadId.value = '';
      threadDetail.value = null;
      selectedSentence.value = null;
      localStorage.removeItem('active_analysis_thread_id');
    }
    await loadThreads();
  });
}

function updateMentionSuggestions() {
  const match = followup.value.match(/@([^\s@，。；,;]*)$/);
  if (!match) {
    mentionSuggestions.value = [];
    return;
  }
  const keyword = match[1] || '';
  mentionSuggestions.value = evidence.value
    .filter((item) => item.title.includes(keyword) || item.evidence_id.includes(keyword))
    .slice(0, 8);
}

function insertMention(item: EvidenceRecord) {
  followup.value = followup.value.replace(/@([^\s@，。；,;]*)$/, `@[${item.title}](${item.evidence_id}) `);
  mentionSuggestions.value = [];
}

function fallbackSentences(content: string): GroundedSentence[] {
  return content
    .split(/(?<=[。！？\n])/)
    .map((text, index) => text.trim())
    .filter(Boolean)
    .map((text, index) => ({
      sentence_id: `fallback_${index}`,
      text,
      start: 0,
      end: 0,
      status: 'weak',
      confidence: 0,
      supporting_passages: [],
      supporting_graph_paths: [],
    }));
}

function labelForMode(mode: string) {
  return mode === 'financial_flow' ? '可疑资金流' : '假设验证';
}

function statusLabel(status: string) {
  return { supported: '证据支撑', weak: '支撑较弱', unsupported: '暂无支撑' }[status] || status;
}

function renderInlineMarkdown(value: string) {
  const escaped = String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  return escaped
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<span class="md-link">$1</span>');
}

async function runTask(label: string, task: () => Promise<void>) {
  loading.value = true;
  error.value = '';
  progress.start({ label, detail: '后端正在检索证据、调用 DeepSeek 并保存会话' });
  try {
    await task();
    await progress.finish({ label: `${label}完成`, detail: '结果已保存到后端' });
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
    progress.fail();
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.analysis-page {
  min-height: 100%;
  background: #eef3f7;
  color: #0f172a;
  padding: 24px;
}
.hero,
.new-thread,
.thread-panel,
.detail-panel,
.source-drawer {
  border: 1px solid #d8e1ea;
  border-radius: 10px;
  background: #ffffff;
  padding: 18px;
}
.hero,
.case-line,
.mode-tabs,
.new-thread {
  margin-bottom: 14px;
}
.hero h1 {
  font-size: 24px;
  font-weight: 900;
}
.hero p,
.case-line,
.hint,
.muted,
.empty,
.thread-card span,
.thread-card p,
.detail-head p {
  color: #64748b;
  font-size: 14px;
}
.warn,
.error {
  border-radius: 8px;
  padding: 10px 12px;
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
.mode-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.mode-tabs button,
.primary-btn,
.secondary,
.delete-btn,
.close-btn {
  border-radius: 8px;
  padding: 9px 13px;
  font-weight: 900;
}
.mode-tabs button.active,
.primary-btn {
  background: #0f766e;
  color: #fff;
}
.secondary {
  border: 1px solid #94a3b8;
  background: #fff;
}
.small {
  padding: 7px 10px;
}
.new-thread {
  display: grid;
  gap: 10px;
}
.field,
textarea {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 10px 12px;
  color: #0f172a;
  background: #fff;
}
textarea {
  resize: vertical;
  line-height: 1.6;
}
.conversation-layout {
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr) 360px;
  gap: 14px;
  align-items: start;
}
.panel-head,
.detail-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.thread-card {
  width: 100%;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  text-align: left;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fafc;
  padding: 12px;
  margin-top: 10px;
}
.thread-card.active {
  border-color: #0f766e;
  background: #ecfdf5;
}
.thread-card strong,
.thread-card span,
.thread-card p {
  display: block;
}
.thread-card p {
  margin-top: 6px;
}
.delete-btn {
  align-self: start;
  border: 1px solid #fecdd3;
  background: #fff1f2;
  color: #be123c;
}
.message {
  border-top: 1px solid #e2e8f0;
  padding: 16px 0;
}
.message:first-of-type {
  border-top: 0;
}
.message-role {
  color: #0f766e;
  font-weight: 900;
  margin-bottom: 8px;
}
.message-text,
.answer-text {
  white-space: pre-wrap;
  line-height: 1.9;
}
.sentence {
  display: inline;
  border: 0;
  border-radius: 5px;
  background: transparent;
  color: #334155;
  padding: 1px 2px;
  text-align: left;
  line-height: 1.9;
}
.sentence:hover {
  background: #ccfbf1;
}
.sentence.supported {
  text-decoration: underline;
  text-decoration-color: #0f766e;
}
.sentence.weak {
  text-decoration: underline;
  text-decoration-color: #f59e0b;
}
.sentence.unsupported {
  text-decoration: underline;
  text-decoration-color: #ef4444;
}
.sentence :deep(strong) {
  font-weight: 900;
  color: #0f172a;
}
.sentence :deep(code) {
  border-radius: 4px;
  background: #e2e8f0;
  padding: 1px 4px;
}
.sentence :deep(.md-link) {
  color: #0f766e;
  font-weight: 800;
}
.followup {
  border-top: 1px solid #e2e8f0;
  margin-top: 16px;
  padding-top: 16px;
}
.mention-menu {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #fff;
  margin: 8px 0;
  max-height: 240px;
  overflow: auto;
}
.mention-menu button {
  width: 100%;
  display: grid;
  gap: 3px;
  text-align: left;
  border-top: 1px solid #e2e8f0;
  padding: 8px 10px;
}
.mention-menu button:first-child {
  border-top: 0;
}
.mention-menu span {
  color: #64748b;
  font-size: 12px;
}
.source-drawer {
  position: sticky;
  top: 14px;
  display: none;
  max-height: calc(100vh - 40px);
  overflow: auto;
}
.source-drawer.open {
  display: block;
}
.close-btn {
  float: right;
  border: 1px solid #cbd5e1;
  background: #fff;
}
.source-status {
  display: inline-block;
  border-radius: 999px;
  padding: 6px 10px;
  margin: 12px 0;
  font-weight: 900;
}
.source-status.supported {
  background: #dcfce7;
  color: #166534;
}
.source-status.weak {
  background: #fef3c7;
  color: #92400e;
}
.source-status.unsupported {
  background: #fee2e2;
  color: #991b1b;
}
.selected-text {
  line-height: 1.8;
}
.passage {
  border-top: 1px solid #e2e8f0;
  padding: 10px 0;
  line-height: 1.6;
}
.passage span {
  display: block;
  color: #0f766e;
  font-size: 13px;
}
@media (max-width: 1200px) {
  .conversation-layout {
    grid-template-columns: 1fr;
  }
  .source-drawer {
    position: static;
  }
}
</style>
