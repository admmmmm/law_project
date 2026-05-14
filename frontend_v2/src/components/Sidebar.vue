<template>
  <aside class="sidebar" :class="{ collapsed }">
    <div class="brand-row">
      <button class="icon-btn" :title="collapsed ? '展开侧栏' : '折叠侧栏'" @click="collapsed = !collapsed">
        <PanelLeftClose v-if="!collapsed" :size="18" />
        <PanelLeftOpen v-else :size="18" />
      </button>
    </div>

    <nav class="nav-cards">
      <router-link class="nav-card" :class="{ active: primaryKey === 'cases' }" to="/cases" title="我的案件">
        <FolderOpen :size="20" />
        <span v-if="!collapsed"><b>我的案件</b><small>选择案件进入空间</small></span>
      </router-link>

      <router-link class="nav-card" :class="{ active: primaryKey === 'new-case' }" to="/cases/new" title="新建案件">
        <FilePlus2 :size="20" />
        <span v-if="!collapsed"><b>新建案件</b><small>两步创建并导入证据</small></span>
      </router-link>

      <button class="nav-card" :class="{ active: primaryKey === 'skills' }" title="检察技能库" @click="toggle('skills')">
        <Library :size="20" />
        <span v-if="!collapsed"><b>检察技能库</b><small>浏览和编辑分析技能</small></span>
        <ChevronDown v-if="!collapsed" :size="16" :class="{ rotate: expanded.skills }" />
      </button>
      <div v-if="!collapsed && expanded.skills" class="subnav">
        <router-link :class="{ active: route.path === '/skills' }" to="/skills">浏览技能</router-link>
        <router-link :class="{ active: route.path.includes('/skills/editor') || route.path.endsWith('/edit') }" to="/skills/editor">技能编辑</router-link>
      </div>

      <button class="nav-card" :class="{ active: primaryKey === 'knowledge' }" title="知识库" @click="toggle('knowledge')">
        <BookOpenCheck :size="20" />
        <span v-if="!collapsed"><b>知识库</b><small>法律知识与实务经验</small></span>
        <ChevronDown v-if="!collapsed" :size="16" :class="{ rotate: expanded.knowledge }" />
      </button>
      <div v-if="!collapsed && expanded.knowledge" class="subnav">
        <router-link :class="{ active: route.path === '/knowledge/legal' }" to="/knowledge/legal">法律知识</router-link>
        <router-link :class="{ active: route.path === '/knowledge/practice' }" to="/knowledge/practice">实务知识</router-link>
      </div>

      <router-link class="nav-card" :class="{ active: primaryKey === 'settings' }" to="/settings" title="设置">
        <Settings :size="20" />
        <span v-if="!collapsed"><b>设置</b><small>系统偏好与状态</small></span>
      </router-link>
    </nav>
  </aside>
</template>

<script setup lang="ts">
import { reactive, ref, computed } from 'vue';
import { useRoute } from 'vue-router';
import { BookOpenCheck, ChevronDown, FilePlus2, FolderOpen, Library, PanelLeftClose, PanelLeftOpen, Settings } from 'lucide-vue-next';

const route = useRoute();
const collapsed = ref(false);
const expanded = reactive({ skills: false, knowledge: false });

const primaryKey = computed(() => {
  if (route.path === '/cases/new') return 'new-case';
  if (route.path.startsWith('/skills')) return 'skills';
  if (route.path.startsWith('/knowledge')) return 'knowledge';
  if (route.path.startsWith('/settings')) return 'settings';
  return 'cases';
});

function toggle(key: 'skills' | 'knowledge') {
  expanded[key] = !expanded[key];
}
</script>
