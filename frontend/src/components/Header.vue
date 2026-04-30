<template>
<header class="flex justify-between items-center w-full px-6 sticky top-0 z-30 h-14 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 shadow-sm shrink-0">
  <div class="flex items-center gap-8 h-full">
    <div class="text-xl font-bold text-slate-900 dark:text-white tracking-tighter">案件侦查工作台</div>
    <div class="flex gap-6 h-full items-center">
      <div class="font-sans text-xs uppercase tracking-widest font-bold text-slate-500 hover:text-blue-800 transition-all cursor-pointer h-full flex items-center border-b-2 border-transparent">活跃案件</div>
      <div class="text-blue-900 dark:text-blue-400 border-b-2 border-blue-900 font-sans text-xs uppercase tracking-widest font-bold cursor-pointer h-full flex items-center">证据档案库</div>
      <div class="font-sans text-xs uppercase tracking-widest font-bold text-slate-500 hover:text-blue-800 transition-all cursor-pointer h-full flex items-center border-b-2 border-transparent">辖区划分</div>
    </div>
  </div>
  
  <div class="flex items-center gap-4">
    <div class="flex items-center bg-slate-100 dark:bg-slate-800 px-3 py-1.5 rounded gap-2 mr-4 border border-slate-200">
      <Search class="text-slate-400 w-4 h-4" />
      <input class="bg-transparent border-none focus:ring-0 text-xs w-48 font-medium p-0" placeholder="检索实体/人员..." type="text"/>
    </div>
    <div class="flex items-center gap-2">
      <div class="flex items-center gap-1.5 px-3 py-1.5 bg-amber-50 border border-amber-200 text-amber-700 rounded text-[10px] font-bold tracking-widest uppercase">
        <span class="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse"></span>
        分类预警
      </div>
    </div>
    <div class="flex items-center gap-3 ml-4 border-l border-slate-200 pl-4">
      <ShieldAlert class="text-slate-500 cursor-pointer hover:text-blue-900 transition-colors w-5 h-5" />
      <Bell class="text-slate-500 cursor-pointer hover:text-blue-900 transition-colors w-5 h-5" />
      <div class="w-8 h-8 rounded-full bg-slate-200 overflow-hidden border border-slate-300 shrink-0">
        <img alt="调查员头像" class="w-full h-full object-cover" src="https://i.pravatar.cc/150?u=a042581f4e290267041" />
      </div>
    </div>
  </div>
</header>
</template>

<script setup lang="ts">
import { Search, ShieldAlert, Bell } from 'lucide-vue-next';
</script>