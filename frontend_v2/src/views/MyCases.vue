<template>
  <div class="page">
    <div class="page-narrow">
      <div class="toolbar" style="margin-bottom: 16px;">
        <div>
          <div class="eyebrow">案件入口</div>
          <h2 class="page-title">选择案件进入案件空间</h2>
          <p class="muted">先从这里检索、筛选和定位案件，再进入专属案件空间查看证据地图、智能分析和信息画像。</p>
        </div>
        <button class="btn" :disabled="loading" @click="loadCases">刷新案件</button>
      </div>

      <section class="panel search-panel">
        <div class="search-panel__head">
          <div>
            <h3 class="section-title">案件检索</h3>
            <p class="muted">一个搜索栏配合过滤条件，快速定位目标案件。</p>
          </div>
          <button class="btn" :disabled="!hasQuery && activeFilter === 'all'" @click="resetFilters">清空筛选</button>
        </div>

        <div class="search-bar-row">
          <input
            v-model.trim="query"
            class="field search-field"
            :placeholder="searchPlaceholder"
          />
          <button class="btn primary">搜索</button>
        </div>

        <div class="chips">
          <button
            v-for="item in filterOptions"
            :key="item.value"
            class="chip-button"
            :class="{ active: activeFilter === item.value }"
            @click="activeFilter = item.value"
          >
            {{ item.label }}
          </button>
        </div>

        <div class="search-summary">
          <span class="chip active">共 {{ cases.length }} 个案件</span>
          <span class="chip">{{ filteredCases.length }} 个匹配结果</span>
        </div>
      </section>

      <div v-if="error" class="error-state" style="margin-top: 16px;">
        <h2>案件加载失败</h2>
        <p class="muted">{{ error }}</p>
        <button class="btn primary" style="margin-top: 14px;" @click="loadCases">重试</button>
      </div>

      <div v-else-if="!loading && cases.length === 0" class="empty-state" style="margin-top: 16px;">
        <h2>暂无案件</h2>
        <p class="muted">可以先创建一个案件，后续再导入证据材料。</p>
        <router-link class="btn primary" style="margin-top: 14px;" to="/cases/new">新建案件</router-link>
      </div>

      <div v-else-if="!loading && filteredCases.length === 0" class="empty-state" style="margin-top: 16px;">
        <h2>未找到匹配案件</h2>
        <p class="muted">可以调整关键词，或者切换过滤条件重新查看。</p>
        <button class="btn primary" style="margin-top: 14px;" @click="resetFilters">清空筛选</button>
      </div>

      <section v-else class="case-list-grid" style="margin-top: 16px;">
        <article v-for="item in filteredCases" :key="item.case_id" class="case-card" @click="enterCase(item.case_id)">
          <div class="row-between">
            <h3>{{ item.title }}</h3>
            <span class="chip active">{{ statusLabel(item.status) }}</span>
          </div>
          <p class="muted">{{ item.legal_basis || '暂未设置案件类型，可在案件概览中补充。' }}</p>
          <div class="case-meta">
            <span>案号 / ID：{{ item.case_id }}</span>
            <span>创建时间：{{ formatDate(item.created_at) }}</span>
          </div>
          <div class="case-stats">
            <span><b>{{ item.evidence_count }}</b>证据</span>
            <span><b>{{ item.memory_count }}</b>记忆</span>
            <span><b>{{ item.offense_id || '-' }}</b>罪名模板</span>
          </div>
          <div class="actions">
            <router-link class="btn primary" :to="`/cases/${item.case_id}`" @click.stop>进入案件</router-link>
            <router-link class="btn" :to="`/cases/${item.case_id}/graph`" @click.stop>证据地图</router-link>
          </div>
        </article>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { backendApi, type CaseSummary } from '../api/backend';

type FilterKey = 'all' | 'title' | 'caseNo' | 'keyword' | 'person';

const router = useRouter();
const cases = ref<CaseSummary[]>([]);
const loading = ref(false);
const error = ref('');
const query = ref('');
const activeFilter = ref<FilterKey>('all');

const filterOptions: Array<{ value: FilterKey; label: string }> = [
  { value: 'all', label: '全部' },
  { value: 'title', label: '名称' },
  { value: 'caseNo', label: '案号' },
  { value: 'keyword', label: '关键词' },
  { value: 'person', label: '人员' },
];

const hasQuery = computed(() => query.value.trim().length > 0);
const searchPlaceholder = computed(() => {
  return {
    all: '搜索案件名称、案号、关键词、人员',
    title: '搜索案件名称',
    caseNo: '搜索案号 / 内部编号',
    keyword: '搜索关键词',
    person: '搜索人员',
  }[activeFilter.value];
});

const filteredCases = computed(() => {
  const normalizedQuery = query.value.trim().toLowerCase();
  if (!normalizedQuery) return cases.value;

  return cases.value.filter((item) => {
    const fields = {
      title: item.title || '',
      caseNo: item.case_id || '',
      keyword: [item.title, item.case_id, item.legal_basis, item.offense_id].filter(Boolean).join(' '),
      person: [item.title, item.legal_basis].filter(Boolean).join(' '),
    };

    if (activeFilter.value === 'all') {
      return Object.values(fields).some((value) => value.toLowerCase().includes(normalizedQuery));
    }

    return fields[activeFilter.value].toLowerCase().includes(normalizedQuery);
  });
});

onMounted(loadCases);

async function loadCases() {
  loading.value = true;
  error.value = '';
  try {
    cases.value = await backendApi.listCases();
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    loading.value = false;
  }
}

function enterCase(caseId: string) {
  localStorage.setItem('active_case_id', caseId);
  localStorage.setItem('active_workspace_id', caseId);
  router.push(`/cases/${caseId}`);
}

function resetFilters() {
  query.value = '';
  activeFilter.value = 'all';
}

function statusLabel(status: string) {
  return ({ created: '已创建', data_ingested: '已导入', analyzed: '已分析' } as Record<string, string>)[status] || status || '未知';
}

function formatDate(value: string) {
  if (!value) return '-';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : `${date.getFullYear()}-${date.getMonth() + 1}-${date.getDate()}`;
}
</script>

<style scoped>
.search-panel {
  display: grid;
  gap: 14px;
}

.search-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.search-bar-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
}

.search-field {
  min-height: 42px;
}

.chip-button {
  border: 1px solid var(--line);
  border-radius: 999px;
  background: #f8fafc;
  color: var(--muted);
  padding: 7px 12px;
  font-size: 12px;
  font-weight: 800;
}

.chip-button.active {
  border-color: var(--primary);
  background: var(--primary-soft);
  color: var(--primary-strong);
}

.search-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.case-list-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.case-card {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  padding: 16px;
  display: grid;
  gap: 12px;
}

.case-card:hover {
  border-color: var(--primary);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

.case-card h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 900;
}

.case-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 18px;
  color: var(--muted);
  font-size: 12px;
}

.case-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.case-stats span {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #f8fafc;
  padding: 10px;
  color: var(--muted);
  font-size: 12px;
}

.case-stats b {
  display: block;
  color: var(--text);
  font-size: 18px;
}

@media (max-width: 1000px) {
  .search-bar-row,
  .case-list-grid {
    grid-template-columns: 1fr;
  }
}
</style>
