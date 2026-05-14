<template>
  <LegalKnowledge v-if="kind === 'legal'" />
  <div v-else class="page">
    <div class="page-narrow">
      <section class="panel">
        <div class="toolbar">
          <div>
            <div class="eyebrow">知识库 / 实务知识</div>
            <h2 class="page-title">实务知识</h2>
            <p class="muted">第一阶段先提供结构化占位页，后续再接独立的实务知识接口。</p>
          </div>
          <div class="actions">
            <button class="btn">上传实务材料</button>
            <button class="btn primary">新增实务知识</button>
          </div>
        </div>
      </section>

      <section class="panel" style="margin-top: 16px;">
        <div class="chips">
          <span v-for="item in categories" :key="item" class="chip">{{ item }}</span>
        </div>
        <div class="grid-2" style="margin-top: 16px;">
          <article v-for="item in mockItems" :key="item.title" class="panel-soft">
            <h3 class="section-title" style="margin-bottom: 6px;">{{ item.title }}</h3>
            <p class="muted">{{ item.brief }}</p>
            <div class="chips" style="margin-top: 10px;">
              <span class="chip">{{ item.type }}</span>
              <span class="chip">{{ item.source }}</span>
            </div>
          </article>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import LegalKnowledge from './LegalKnowledge.vue';

defineProps<{ kind: 'legal' | 'practice' }>();

const categories = ['审查清单', '风险提示', '类案经验', '补证建议', '流程经验', '画像经验'];
const mockItems = [
  { title: '证言前后不一致审查要点', type: '审查清单', source: '检察实务整理', brief: '用于核查同一证人不同阶段陈述变化、补强证据和合理解释。' },
  { title: '资金流异常提示模板', type: '风险提示', source: '办案经验沉淀', brief: '用于梳理大额拆分转账、过桥账户和异常回流等高风险信号。' },
];
</script>
