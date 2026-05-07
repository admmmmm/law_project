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
              <p v-if="message.tool_call_summary" class="tool-summary">{{ message.tool_call_summary }}</p>
              <button
                v-for="sentence in message.claims.length ? message.claims : fallbackSentences(message.content)"
                :key="sentence.sentence_id"
                class="sentence"
                :class="sentence.status"
                @click="selectedSentence = sentence"
              >
                <span v-html="renderInlineMarkdown(sentence.text)" />
              </button>
              <details v-if="message.retrieval_session_id" class="retrieval-details" @toggle="onRetrievalToggle(message.retrieval_session_id, $event)">
                <summary>检索与调用细节</summary>
                <div v-if="retrievalLoading[message.retrieval_session_id]" class="muted">正在读取检索记录...</div>
                <div v-else-if="retrievalDetails[message.retrieval_session_id]" class="retrieval-body">
                  <div class="retrieval-meta">
                    <span>{{ retrievalDetails[message.retrieval_session_id].session.planner_model }}</span>
                    <span>{{ retrievalDetails[message.retrieval_session_id].session.analysis_model }}</span>
                    <span>{{ retrievalDetails[message.retrieval_session_id].session.status }}</span>
                  </div>
                  <section v-for="step in retrievalDetails[message.retrieval_session_id].steps" :key="step.step_id" class="retrieval-step">
                    <h4>第 {{ step.round_index }} 轮</h4>
                    <p v-if="step.retrieval_goals.length"><strong>目标：</strong>{{ step.retrieval_goals.join('；') }}</p>
                    <p v-if="step.coverage_summary"><strong>覆盖：</strong>{{ step.coverage_summary }}</p>
                    <p v-if="step.unresolved_gaps.length"><strong>缺口：</strong>{{ step.unresolved_gaps.join('；') }}</p>
                    <article v-for="call in step.tool_calls" :key="call.tool_call_id" class="tool-call">
                      <div class="tool-call-head">
                        <strong>{{ toolLabel(call.tool_name) }}</strong>
                        <code>{{ formatArgs(call.arguments) }}</code>
                      </div>
                      <p>{{ call.summary || '无摘要' }}</p>
                      <p v-if="call.errors.length" class="error tiny">错误：{{ call.errors.join('；') }}</p>
                      <div v-if="call.graph_facts.length" class="tool-block">
                        <b>图谱关系</b>
                        <ul>
                          <li v-for="fact in call.graph_facts.slice(0, 8)" :key="fact">{{ fact }}</li>
                        </ul>
                      </div>
                      <div v-if="call.passages.length" class="tool-block">
                        <b>证据 passage</b>
                        <ul>
                          <li v-for="passage in call.passages.slice(0, 5)" :key="`${passage.rank}-${passage.passage}`">
                            Doc {{ passage.rank }}：{{ passage.evidence_title || passage.evidence_id || '未映射证据' }} - {{ compactText(passage.passage, 110) }}
                          </li>
                        </ul>
                      </div>
                      <div v-if="call.legal_passages.length" class="tool-block">
                        <b>法律知识</b>
                        <ul>
                          <li v-for="passage in call.legal_passages.slice(0, 4)" :key="`${passage.rank}-${passage.passage}`">
                            {{ passage.evidence_title || '法律知识' }} - {{ compactText(passage.passage, 100) }}
                          </li>
                        </ul>
                      </div>
                      <div v-if="call.rule_findings.length" class="tool-block">
                        <b>规则命中</b>
                        <ul>
                          <li v-for="finding in call.rule_findings" :key="finding.finding_id">
                            {{ finding.title }}（{{ finding.severity }}）：{{ compactText(finding.reason, 120) }}
                          </li>
                        </ul>
                      </div>
                      <div v-if="call.document_groups.length" class="tool-block">
                        <b>文件母图聚合</b>
                        <ul>
                          <li v-for="group in call.document_groups.slice(0, 8)" :key="String(group.doc_id || group.name || group.title)">
                            {{ group.doc_id || group.name || '文件' }}：{{ group.process_stage || group.title || '' }} {{ compactText(String(group.proof_purpose || group.document_summary || group.description || ''), 100) }}
                          </li>
                        </ul>
                      </div>
                    </article>
                  </section>
                </div>
              </details>
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
            {{ supportStrength(selectedSentence) }}
          </div>
          <p class="selected-text">{{ selectedSentence.text }}</p>
          <p v-if="threadDetail?.messages.find((item) => item.role === 'assistant' && item.claims.some((claim) => claim.sentence_id === selectedSentence?.sentence_id))?.retrieval_session_id" class="muted">
            本句来源于已保存的 agentic RAG 检索会话。
          </p>
          <h3>证据关系路径</h3>
          <article v-for="path in selectedSentence.supporting_graph_paths" :key="`${path.source}-${path.relation}-${path.target}`" class="graph-path">
            <span>{{ path.source }}</span>
            <strong>—[{{ path.relation }}]→</strong>
            <span>{{ path.target }}</span>
          </article>
          <p v-if="!selectedSentence.supporting_graph_paths.length" class="muted">暂无直接图谱路径。</p>
          <h3>证明文档</h3>
          <article v-for="passage in selectedSentence.supporting_passages" :key="`${passage.rank}-${passage.passage}`" class="passage">
            <strong>Doc {{ passage.rank }}</strong>
            <span>{{ passage.evidence_title || passage.evidence_id || '未映射证据' }}</span>
            <p>{{ passage.passage }}</p>
          </article>
          <p v-if="!selectedSentence.supporting_passages.length" class="empty">
            暂未绑定可靠 passage。该句只能作为待核查判断，不能作为正式事实结论；建议缩小问题或重新追问。
          </p>
        </template>
      </aside>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { backendApi, type AnalysisThread, type AnalysisThreadDetail, type EvidenceRecord, type GroundedSentence, type RetrievalSessionDetail } from '../api/backend';
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
const retrievalDetails = ref<Record<string, RetrievalSessionDetail>>({});
const retrievalLoading = ref<Record<string, boolean>>({});
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

function supportStrength(sentence: GroundedSentence) {
  if (sentence.status === 'unsupported') return '待核查';
  if (sentence.status === 'weak') return '弱';
  if (sentence.confidence >= 0.65) return '强';
  return '中';
}

async function onRetrievalToggle(sessionId: string | null | undefined, event: Event) {
  const target = event.target as HTMLDetailsElement;
  if (!target.open || !sessionId || retrievalDetails.value[sessionId] || retrievalLoading.value[sessionId]) return;
  retrievalLoading.value = { ...retrievalLoading.value, [sessionId]: true };
  try {
    const detail = await backendApi.getRetrievalSession(activeCaseId.value, sessionId);
    retrievalDetails.value = { ...retrievalDetails.value, [sessionId]: detail };
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    retrievalLoading.value = { ...retrievalLoading.value, [sessionId]: false };
  }
}

function toolLabel(name: string) {
  const labels: Record<string, string> = {
    search_documents: '文档检索',
    search_graph: '图谱检索',
    expand_node: '节点扩展',
    search_time_range: '时间检索',
    search_legal: '法律知识',
  };
  return labels[name] || name;
}

function formatArgs(args: Record<string, unknown>) {
  const text = JSON.stringify(args || {}, null, 0);
  return text.length > 160 ? `${text.slice(0, 160)}...` : text;
}

function compactText(value: string, limit: number) {
  const text = String(value || '').replace(/\s+/g, ' ').trim();
  return text.length > limit ? `${text.slice(0, limit)}...` : text;
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
  height: 100%;
  min-height: 0;
  overflow: auto;
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
  min-height: 0;
}
.thread-panel,
.detail-panel {
  min-width: 0;
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
.tool-summary {
  display: inline-block;
  border: 1px solid #99f6e4;
  border-radius: 999px;
  background: #f0fdfa;
  color: #0f766e;
  padding: 5px 10px;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 900;
}
.retrieval-details {
  margin-top: 14px;
  border: 1px solid #dbeafe;
  border-radius: 12px;
  background: #f8fafc;
  padding: 10px 12px;
}
.retrieval-details summary {
  cursor: pointer;
  font-weight: 900;
  color: #0f766e;
}
.retrieval-body {
  margin-top: 10px;
  display: grid;
  gap: 12px;
}
.retrieval-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.retrieval-meta span {
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  padding: 4px 8px;
  background: #fff;
  color: #475569;
  font-size: 12px;
  font-weight: 800;
}
.retrieval-step {
  border-top: 1px solid #e2e8f0;
  padding-top: 10px;
}
.retrieval-step h4 {
  margin: 0 0 6px;
}
.tool-call {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
  padding: 10px;
  margin-top: 8px;
}
.tool-call-head {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 8px;
  align-items: start;
}
.tool-call-head code {
  overflow-wrap: anywhere;
  color: #475569;
}
.tool-block {
  margin-top: 8px;
}
.tool-block ul {
  margin: 6px 0 0;
  padding-left: 18px;
}
.tool-block li {
  margin-bottom: 4px;
}
.tiny {
  font-size: 12px;
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
.graph-path {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  border: 1px solid #dbeafe;
  background: #eff6ff;
  border-radius: 10px;
  padding: 10px;
  margin: 8px 0;
  color: #1e3a8a;
  line-height: 1.5;
}
.graph-path strong {
  color: #0f766e;
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
