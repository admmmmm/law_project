<template>
  <div class="chat-page">
    <section class="chat-shell">
      <header class="hero">
        <div>
          <h1>RAG 对话</h1>
          <p>基于当前案件证据问问题。回答由 HippoRAG 检索增强生成，并展示相关 passage。</p>
        </div>
        <div class="case-line">
          <span>当前案件</span>
          <code>{{ activeCaseId || '未选择案件' }}</code>
        </div>
      </header>

      <p v-if="!activeCaseId" class="warn">请先到“案件导入”页新建或选择案件。</p>
      <p v-if="error" class="error">{{ error }}</p>
      <AsyncProgressBar
        v-if="progress.active.value"
        compact
        :value="progress.value.value"
        :label="progress.label.value"
        :detail="progress.detail.value"
      />

      <section class="conversation">
        <div v-if="messages.length === 0" class="empty">
          可以直接问：“杨周武涉嫌徇私枉法的关键证据有哪些？”或者“请说明王静、何晓初与杨周武之间的关系。”
        </div>
        <article v-for="message in messages" :key="message.id" :class="['message', message.role]">
          <div class="bubble">
            <div class="markdown" v-html="renderMarkdown(message.content)" />
          </div>
          <div v-if="message.passages?.length" class="sources">
            <h3>相关证据 passage</h3>
            <article v-for="item in message.passages" :key="`${message.id}-${item.rank}-${item.evidence_id}`" class="source-card">
              <div>
                <strong>#{{ item.rank }} / score {{ item.score.toFixed(4) }}</strong>
                <span>{{ item.evidence_title || item.evidence_id || '未映射证据' }}</span>
              </div>
              <p>{{ item.passage }}</p>
            </article>
          </div>
        </article>
      </section>

      <form class="composer" @submit.prevent="sendQuestion">
        <textarea
          v-model="draft"
          :disabled="loading || !activeCaseId"
          placeholder="输入问题，例如：请还原杨周武从受请托到调解结案的行为链条。"
          @keydown.enter.exact.prevent="sendQuestion"
        />
        <button :disabled="loading || !activeCaseId || !draft.trim()">
          {{ loading ? '检索生成中...' : '发送' }}
        </button>
      </form>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { backendApi, type ChatResult } from '../api/backend';
import AsyncProgressBar from '../components/AsyncProgressBar.vue';
import { useSimulatedProgress } from '../composables/useSimulatedProgress';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  passages?: ChatResult['passages'];
}

const activeCaseId = ref(localStorage.getItem('active_case_id') || '');
const draft = ref('');
const loading = ref(false);
const error = ref('');
const progress = useSimulatedProgress();
const messages = ref<ChatMessage[]>([]);

async function sendQuestion() {
  const question = draft.value.trim();
  if (!activeCaseId.value || !question || loading.value) return;
  const userMessage: ChatMessage = { id: `user-${Date.now()}`, role: 'user', content: question };
  messages.value.push(userMessage);
  draft.value = '';
  loading.value = true;
  error.value = '';
  progress.start({
    label: '正在检索并生成回答',
    detail: 'HippoRAG 正在召回证据 passage 并组织答案',
  });
  try {
    const result = await backendApi.chatAnalysis(activeCaseId.value, question, [], 8);
    if (result.error) error.value = result.error;
    messages.value.push({
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: result.answer || '没有生成回答。请确认已导入证据，并且 HippoRAG/DeepSeek 配置可用。',
      passages: result.passages,
    });
    await progress.finish({
      label: '回答已生成',
      detail: '相关证据 passage 已附在消息下方',
    });
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
    progress.fail();
  } finally {
    loading.value = false;
  }
}

function renderMarkdown(value: string) {
  const escaped = escapeHtml(value || '');
  return escaped
    .replace(/^### (.*)$/gm, '<h4>$1</h4>')
    .replace(/^## (.*)$/gm, '<h3>$1</h3>')
    .replace(/^# (.*)$/gm, '<h2>$1</h2>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/==(.+?)==/g, '<mark>$1</mark>')
    .replace(/^- (.*)$/gm, '<div class="md-list">- $1</div>')
    .replace(/\n/g, '<br />');
}

function escapeHtml(value: string) {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
</script>

<style scoped>
.chat-page {
  height: 100%;
  overflow: auto;
  background: #eef3f7;
  color: #0f172a;
  padding: 24px;
}
.chat-shell {
  max-width: 980px;
  margin: 0 auto;
  display: grid;
  gap: 14px;
}
.hero,
.conversation,
.composer {
  border: 1px solid #d8e1ea;
  border-radius: 10px;
  background: #ffffff;
}
.hero {
  display: flex;
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
.empty {
  color: #64748b;
  font-size: 14px;
}
.case-line {
  text-align: right;
}
.case-line span,
.case-line code {
  display: block;
}
.warn,
.error {
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 14px;
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
.conversation {
  min-height: 420px;
  padding: 18px;
}
.empty {
  height: 280px;
  display: grid;
  place-items: center;
  text-align: center;
}
.message {
  display: grid;
  gap: 10px;
  margin-bottom: 16px;
}
.bubble {
  max-width: 78%;
  border-radius: 10px;
  padding: 12px 14px;
  line-height: 1.7;
}
.message.user {
  justify-items: end;
}
.message.user .bubble {
  background: #0f766e;
  color: #ffffff;
}
.message.assistant {
  justify-items: start;
}
.message.assistant .bubble {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}
.sources {
  width: min(760px, 100%);
  border: 1px solid #dbeafe;
  border-radius: 10px;
  background: #f8fbff;
  padding: 12px;
}
.sources h3 {
  font-weight: 900;
  margin-bottom: 8px;
}
.source-card {
  border-top: 1px solid #dbeafe;
  padding: 10px 0;
}
.source-card:first-of-type {
  border-top: 0;
}
.source-card div {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 13px;
}
.source-card span {
  color: #0f766e;
  text-align: right;
}
.source-card p {
  margin-top: 6px;
  color: #475569;
  font-size: 13px;
  line-height: 1.7;
}
.composer {
  display: grid;
  grid-template-columns: 1fr 120px;
  gap: 12px;
  padding: 14px;
}
.composer textarea {
  min-height: 72px;
  resize: vertical;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 14px;
  outline: none;
}
.composer textarea:focus {
  border-color: #0f766e;
}
.composer button {
  border-radius: 8px;
  background: #0f766e;
  color: #ffffff;
  font-weight: 900;
}
.composer button:disabled {
  opacity: 0.45;
}
.markdown :deep(strong) {
  font-weight: 900;
}
.markdown :deep(mark) {
  border-radius: 4px;
  background: #fed7aa;
  color: #9a3412;
  padding: 0 3px;
}
@media (max-width: 800px) {
  .hero,
  .composer {
    grid-template-columns: 1fr;
  }
  .bubble {
    max-width: 100%;
  }
}
</style>
