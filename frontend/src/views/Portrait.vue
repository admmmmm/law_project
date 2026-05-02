<template>
  <div class="portrait-page">
    <section class="shell">
      <header class="hero">
        <div>
          <h1>画像报告</h1>
          <p>白板页：调用后端报告接口，以 Markdown 渲染当前报告内容，缺口会高亮。</p>
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
          <div class="items">
            <div v-for="item in section.items" :key="item" class="markdown-item" v-html="renderMarkdown(item)" />
          </div>
        </article>

        <section class="suggestions">
          <h3>参考建议</h3>
          <div v-for="item in report.suggestions" :key="item" class="markdown-item" v-html="renderMarkdown(item)" />
        </section>
      </section>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { backendApi, type PortraitReport } from '../api/backend';

const activeCaseId = ref(localStorage.getItem('active_case_id') || '');
const loading = ref(false);
const error = ref('');
const report = ref<PortraitReport | null>(null);

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

function formatTime(value: string) {
  return new Date(value).toLocaleString();
}

function renderMarkdown(value: string) {
  const escaped = escapeHtml(value || '');
  return escaped
    .replace(/^### (.*)$/gm, '<h4>$1</h4>')
    .replace(/^## (.*)$/gm, '<h3>$1</h3>')
    .replace(/^# (.*)$/gm, '<h2>$1</h2>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/==(.+?)==/g, '<mark>$1</mark>')
    .replace(/^- (.*)$/gm, '<div class="md-list">• $1</div>')
    .replace(/\n/g, '<br />');
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
.markdown-item {
  border: 1px solid #e2e8f0;
  border-radius: 9px;
  background: #f8fafc;
  padding: 12px;
  color: #334155;
  font-size: 14px;
  line-height: 1.7;
}
.suggestions {
  margin-top: 22px;
  border: 1px solid #99f6e4;
  border-radius: 10px;
  background: #f0fdfa;
  padding: 16px;
}
.suggestions .markdown-item {
  border-color: #ccfbf1;
  background: #ffffff;
}
.markdown-item :deep(strong) {
  color: #0f172a;
  font-weight: 900;
}
.markdown-item :deep(mark) {
  border-radius: 4px;
  background: #fed7aa;
  color: #9a3412;
  padding: 0 3px;
}
.markdown-item :deep(.md-list) {
  margin: 2px 0;
}
</style>
