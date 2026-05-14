<template>
  <div class="page">
    <div class="page-narrow">
      <section class="panel">
        <div class="toolbar">
          <div>
            <div class="eyebrow">检察技能库</div>
            <h2 class="page-title">浏览技能</h2>
            <p class="muted">浏览系统内已有的检察分析技能包，查看用途、来源和适用场景。</p>
          </div>
          <router-link class="btn primary" to="/skills/editor">新建 / 编辑技能</router-link>
        </div>

        <div class="skill-filters">
          <input v-model.trim="query" class="field" placeholder="搜索技能名称、简介、来源、适用场景" />
          <div class="chips">
            <button v-for="tag in tags" :key="tag" class="chip" :class="{ active: activeTag === tag }" @click="activeTag = tag">
              {{ tag }}
            </button>
          </div>
        </div>
      </section>

      <div v-if="error" class="error-state" style="margin-top: 16px;">
        <h2>技能加载失败</h2>
        <p class="muted">{{ error }}</p>
        <button class="btn primary" style="margin-top: 12px;" @click="load">重试</button>
      </div>

      <section v-else-if="filteredSkills.length" class="skill-grid" style="margin-top: 16px;">
        <article v-for="item in filteredSkills" :key="item.name" class="skill-card" @click="router.push(`/skills/${item.name}`)">
          <div class="row-between">
            <h3>{{ item.title || item.name }}</h3>
            <span class="chip">{{ item.version || 'v1' }}</span>
          </div>
          <p class="muted">{{ item.description || '暂无技能简介。' }}</p>
          <div class="chips">
            <span v-for="tag in [...(item.case_types || []), ...(item.task_types || [])].slice(0, 4)" :key="tag" class="chip">{{ tag }}</span>
          </div>
          <div class="actions">
            <router-link class="btn" :to="`/skills/${item.name}`" @click.stop>查看详情</router-link>
            <router-link class="btn" :to="`/skills/${item.name}/edit`" @click.stop>编辑</router-link>
          </div>
        </article>
      </section>

      <div v-else class="empty-state" style="margin-top: 16px;">
        <h2>未找到匹配的技能</h2>
        <p class="muted">可以调整搜索关键词，或进入技能编辑页新建技能说明。</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { backendApi, type RulePackSummary } from '../api/backend';

const router = useRouter();
const skills = ref<RulePackSummary[]>([]);
const query = ref('');
const activeTag = ref('全部');
const error = ref('');
const tags = ['全部', '证据审查', '文书完整性', '反侦查行为', '资金流风险', '流程节点', '画像分析'];

const filteredSkills = computed(() => {
  const q = query.value.toLowerCase();
  return skills.value.filter((item) => {
    const text = [item.name, item.title, item.description, ...(item.case_types || []), ...(item.task_types || [])].filter(Boolean).join(' ').toLowerCase();
    const tagOk = activeTag.value === '全部' || text.includes(activeTag.value.toLowerCase());
    return tagOk && (!q || text.includes(q));
  });
});

onMounted(load);

async function load() {
  error.value = '';
  try {
    skills.value = await backendApi.listRulePacks();
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
    skills.value = [];
  }
}
</script>

<style scoped>
.skill-filters {
  margin-top: 14px;
  display: grid;
  gap: 12px;
}
.skill-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
.skill-card {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  padding: 16px;
  display: grid;
  gap: 12px;
}
.skill-card:hover {
  border-color: var(--primary);
}
.skill-card h3 {
  margin: 0;
  font-size: 17px;
}
</style>

