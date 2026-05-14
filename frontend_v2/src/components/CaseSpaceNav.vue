<template>
  <nav class="case-space-nav">
    <div class="case-space-nav__inner">
      <div class="case-space-nav__meta">
        <router-link class="case-space-nav__back" to="/cases">返回我的案件</router-link>
        <div>
          <div class="space-label">Case Space 案件空间</div>
          <strong>{{ caseLabel }}</strong>
        </div>
      </div>

      <div class="case-space-nav__tabs">
        <router-link :to="`/cases/${caseId}`">案件概览</router-link>
        <router-link :to="`/cases/${caseId}/graph`">案件证据地图</router-link>
        <router-link :to="`/cases/${caseId}/analysis`">智能分析</router-link>
        <router-link :to="`/cases/${caseId}/portrait`">信息画像</router-link>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();
const caseId = computed(() => String(route.params.caseId || localStorage.getItem('active_case_id') || ''));
const caseLabel = computed(() => (caseId.value ? `当前案件：${caseId.value}` : '当前案件'));
</script>
