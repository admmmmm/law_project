<template>
  <div class="app-shell">
    <Header />
    <div class="workspace-frame">
      <CaseSpaceSidebar v-if="isCaseSpace" />
      <Sidebar v-else />
      <main class="workspace-main">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import Sidebar from './components/Sidebar.vue';
import Header from './components/Header.vue';
import CaseSpaceSidebar from './components/CaseSpaceSidebar.vue';

const route = useRoute();
const isCaseSpace = computed(() => route.meta.space === 'case');
</script>
