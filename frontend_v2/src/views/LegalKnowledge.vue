<template>
  <div class="page">
    <div class="page-narrow">
      <section class="panel">
        <div class="toolbar">
          <div>
            <div class="eyebrow">知识库 / 法律知识</div>
            <h2 class="page-title">法律知识</h2>
            <p class="muted">第一阶段提供只读浏览和上传入口，后续可接入编辑、版本管理和检索调试。</p>
          </div>
          <div class="actions">
            <input ref="fileInput" class="hidden-file" type="file" accept=".md,.txt,.json" @change="uploadKnowledge" />
            <button class="btn" :disabled="uploading" @click="fileInput?.click()">{{ uploading ? '上传中...' : '上传知识材料' }}</button>
            <button class="btn primary" @click="load">刷新</button>
          </div>
        </div>
      </section>

      <div v-if="error" class="error-state" style="margin-top: 16px;">
        <h2>法律知识加载失败</h2>
        <p class="muted">{{ error }}</p>
      </div>

      <section class="grid-3" style="margin-top: 16px;">
        <article v-for="card in cards" :key="card.title" class="panel">
          <h3 class="section-title">{{ card.title }}</h3>
          <p class="muted">{{ card.brief }}</p>
          <div class="chips" style="margin-top: 12px;">
            <span v-for="item in card.items" :key="item" class="chip">{{ item }}</span>
          </div>
        </article>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { backendApi } from '../api/backend';

const error = ref('');
const uploading = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);
const cards = ref([
  { title: '罪名模板', brief: '十四种重点罪名、构成要件和审查重点。', items: ['徇私枉法', '滥用职权', '玩忽职守'] },
  { title: '办案流程', brief: '接警、受案、立案、侦查、强制措施、移送审查等流程模板。', items: ['刑事案件流程', '伤害案件流程', '释放审查'] },
  { title: '证据标准', brief: '不同事实和要件对应的应有材料与证明标准。', items: ['主体身份', '职权依据', '主观明知'] },
]);

onMounted(load);

async function load() {
  error.value = '';
  try {
    const data = await backendApi.getLegalKnowledgeIndex();
    if (Array.isArray(data?.sections)) {
      cards.value = data.sections.map((item: any) => ({
        title: item.title || item.name || '法律知识',
        brief: item.description || item.brief || '暂无说明。',
        items: (item.items || item.children || [])
          .slice(0, 12)
          .map((child: any) => child.title || child.name || child.offense_id || child.id || String(child)),
      }));
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
}

async function uploadKnowledge(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  uploading.value = true;
  error.value = '';
  try {
    await backendApi.uploadLegalKnowledge(file);
    await load();
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    uploading.value = false;
    input.value = '';
  }
}
</script>

<style scoped>
.hidden-file {
  display: none;
}
</style>
