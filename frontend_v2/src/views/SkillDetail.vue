<template>
  <div class="page">
    <div class="page-narrow skill-detail">
      <div v-if="loading" class="panel">正在加载技能详情...</div>
      <div v-else-if="error" class="error-state">
        <h2>技能详情加载失败</h2>
        <p class="muted">{{ error }}</p>
      </div>
      <template v-else-if="detail">
        <section class="panel">
          <div class="toolbar">
            <div>
              <div class="eyebrow">基础信息</div>
              <h2 class="page-title">{{ detail.title || detail.name }}</h2>
              <p class="muted">{{ detail.description || '暂无技能说明。' }}</p>
            </div>
            <div class="actions">
              <router-link class="btn" to="/skills">返回列表</router-link>
              <router-link class="btn primary" :to="`/skills/${detail.name}/edit`">编辑技能</router-link>
            </div>
          </div>
          <div class="chips" style="margin-top: 12px;">
            <span class="chip">版本 {{ detail.version || '0.1.0' }}</span>
            <span v-for="tag in detail.case_types || []" :key="tag" class="chip">{{ tag }}</span>
            <span v-for="tag in detail.task_types || []" :key="tag" class="chip">{{ tag }}</span>
          </div>
        </section>

        <div class="grid-2" style="margin-top: 16px;">
          <section class="panel">
            <h3 class="section-title">技能说明</h3>
            <pre class="detail-pre">{{ detail.skill_md || '暂无 SKILL 说明。' }}</pre>
          </section>
          <section class="panel">
            <h3 class="section-title">输出结构</h3>
            <pre class="detail-pre">{{ pretty(detail.finding_templates || detail.manifest || {}) }}</pre>
          </section>
        </div>

        <section class="panel" style="margin-top: 16px;">
          <h3 class="section-title">检查重点</h3>
          <pre class="detail-pre">{{ pretty(detail.checks || []) }}</pre>
        </section>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { backendApi, type RulePackDetail } from '../api/backend';

const route = useRoute();
const detail = ref<RulePackDetail | null>(null);
const loading = ref(false);
const error = ref('');

onMounted(load);

async function load() {
  loading.value = true;
  error.value = '';
  try {
    detail.value = await backendApi.getRulePack(String(route.params.skillName || ''));
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    loading.value = false;
  }
}

function pretty(value: unknown) {
  return JSON.stringify(value ?? {}, null, 2);
}
</script>

<style scoped>
.detail-pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
  color: var(--text);
  font-size: 13px;
}
</style>
