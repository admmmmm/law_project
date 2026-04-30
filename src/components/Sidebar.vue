<template>
<aside class="flex flex-col h-screen left-0 top-0 z-40 w-48 shrink-0 bg-slate-50 dark:bg-slate-950 border-r border-slate-200 dark:border-slate-800 font-sans tracking-tight font-medium">
  <div class="p-4 flex flex-col gap-2">
    <div class="flex items-center gap-3 mb-8">
      <div class="w-10 h-10 bg-slate-900 rounded-lg flex items-center justify-center overflow-hidden shrink-0">
        <Gavel class="text-white w-5 h-5" />
      </div>
      <div class="flex items-center">
        <h1 class="text-base font-black tracking-tighter text-slate-900 dark:text-white leading-tight whitespace-nowrap">智慧检察系统</h1>
      </div>
    </div>
    
    <button class="w-full bg-blue-900 dark:bg-blue-600 text-white p-2.5 rounded text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 hover:opacity-90 transition-all mb-4">
      <Plus class="w-4 h-4" />
      新建侦查任务
    </button>
    
    <div class="space-y-1">
      <router-link to="/" class="group flex items-center gap-3 px-3 py-2.5 rounded cursor-pointer text-sm transition-colors duration-150 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-900 font-medium" exact-active-class="!bg-slate-200/50 dark:!bg-slate-800 !text-blue-900 dark:!text-blue-400 border-r-2 !border-blue-900 dark:!border-blue-400 font-bold">
        <FolderOpen class="w-5 h-5" />
        案件管理
      </router-link>
      <router-link to="/graph" class="group flex items-center gap-3 px-3 py-2.5 rounded cursor-pointer text-sm transition-colors duration-150 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-900 font-medium" active-class="!bg-slate-200/50 dark:!bg-slate-800 !text-blue-900 dark:!text-blue-400 border-r-2 !border-blue-900 dark:!border-blue-400 font-bold">
        <Network class="w-5 h-5" />
        图谱分析
      </router-link>
      <router-link to="/portrait" class="group flex items-center gap-3 px-3 py-2.5 rounded cursor-pointer text-sm transition-colors duration-150 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-900 font-medium" active-class="!bg-slate-200/50 dark:!bg-slate-800 !text-blue-900 dark:!text-blue-400 border-r-2 !border-blue-900 dark:!border-blue-400 font-bold">
        <UserSearch class="w-5 h-5" />
        画像分析
      </router-link>
      <router-link to="/intelligence" class="group flex items-center gap-3 px-3 py-2.5 rounded cursor-pointer text-sm transition-colors duration-150 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-900 font-medium" active-class="!bg-slate-200/50 dark:!bg-slate-800 !text-blue-900 dark:!text-blue-400 border-r-2 !border-blue-900 dark:!border-blue-400 font-bold">
        <Brain class="w-5 h-5" />
        主观意图研判
      </router-link>
    </div>
  </div>
  
  <div class="mt-auto p-4 border-t border-slate-200 dark:border-slate-800">
    <div class="space-y-1">
      <div class="px-3 py-2 rounded flex items-center gap-3 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer text-xs">
        <Terminal class="w-4 h-4" />
        系统日志
      </div>
      <div class="px-3 py-2 rounded flex items-center gap-3 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer text-xs">
        <Shield class="w-4 h-4" />
        安全设置
      </div>
    </div>
  </div>
</aside>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router';
import { Gavel, Plus, FolderOpen, Network, UserSearch, Brain, Terminal, Shield } from 'lucide-vue-next';
</script>
