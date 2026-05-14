<template>
  <div class="page">
    <div class="page-narrow">
      <section class="panel">
        <div class="toolbar">
          <div>
            <div class="eyebrow">技能编辑</div>
            <h2 class="page-title">{{ skillName ? `编辑技能：${skillName}` : '新建技能' }}</h2>
            <p class="muted">第一阶段先提供基础编辑视图。保存能力稍后接入后端写入接口。</p>
          </div>
          <div class="actions">
            <router-link class="btn" to="/skills">返回</router-link>
            <button class="btn primary" disabled>保存</button>
          </div>
        </div>
      </section>

      <div class="grid-3" style="margin-top: 16px; grid-template-columns: 280px minmax(0,1fr) 320px;">
        <section class="panel">
          <h3 class="section-title">技能信息</h3>
          <div class="form-field">技能名称 name *
            <input v-model="form.name" class="field" />
          </div>
          <div class="form-field" style="margin-top: 12px;">一句话简介 brief *
            <input v-model="form.brief" class="field" />
          </div>
          <div class="form-field" style="margin-top: 12px;">来源 source
            <input v-model="form.source" class="field" />
          </div>
          <div class="form-field" style="margin-top: 12px;">标签 tags
            <input v-model="form.tags" class="field" placeholder="用逗号分隔" />
          </div>
        </section>

        <section class="panel">
          <h3 class="section-title">文本编辑器</h3>
          <textarea v-model="form.content" class="textarea editor"></textarea>
        </section>

        <section class="panel">
          <h3 class="section-title">预览 / 校验</h3>
          <p class="muted">必填项：{{ form.name.trim() && form.brief.trim() ? '已填写' : '未完成' }}</p>
          <pre class="preview">{{ form.content }}</pre>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive } from 'vue';
import { useRoute } from 'vue-router';
import { backendApi } from '../api/backend';

const route = useRoute();
const skillName = computed(() => String(route.params.skillName || ''));
const form = reactive({
  name: '',
  brief: '',
  source: '',
  tags: '',
  content: '# 技能名称\n\n## 适用场景\n\n## 分析目标\n\n## 需要检查的材料\n\n## 检查重点\n\n## 输出格式\n\n## 示例\n\n## 注意事项\n',
});

onMounted(async () => {
  if (!skillName.value) return;
  try {
    const detail = await backendApi.getRulePack(skillName.value);
    form.name = detail.title || detail.name || '';
    form.brief = detail.description || '';
    form.tags = [...(detail.case_types || []), ...(detail.task_types || [])].join(', ');
    form.content = detail.skill_md || form.content;
  } catch {
    // keep placeholder editor state
  }
});
</script>

<style scoped>
.editor {
  min-height: 540px;
}

.preview {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
  font-size: 13px;
}
</style>
