<template>
  <div class="flex h-screen w-full bg-slate-50 text-slate-900 font-sans overflow-hidden dark:bg-slate-950 dark:text-white">
    <Sidebar />
    <div class="flex flex-col flex-1 min-w-0 h-full">
      <Header />
      <main class="flex-1 bg-slate-50 dark:bg-slate-950 relative overflow-hidden flex flex-col">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import Sidebar from './components/Sidebar.vue';
import Header from './components/Header.vue';
</script>
