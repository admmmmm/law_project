<template>
  <aside class="w-56 bg-slate-950 text-slate-100 h-screen shrink-0 flex flex-col">
    <div class="px-5 h-14 flex items-center border-b border-slate-800 font-bold">侦查中台</div>
    <nav class="p-3 space-y-1 text-sm">
      <router-link class="nav-link" active-class="nav-active" to="/">案件导入</router-link>
      <router-link class="nav-link" active-class="nav-active" to="/graph">证据图谱</router-link>
      <router-link class="nav-link" active-class="nav-active" to="/intelligence">智能分析</router-link>
      <router-link class="nav-link" active-class="nav-active" to="/portrait">画像报告</router-link>
    </nav>
    <div class="mt-auto p-4 text-xs text-slate-400 border-t border-slate-800">
      adm 整合分支<br />
      Backend: <span class="font-mono">:8000</span><br />
      Frontend: <span class="font-mono">:5173</span>
    </div>
  </aside>
</template>

<style scoped>
.nav-link {
  display: block;
  border-radius: 8px;
  padding: 10px 12px;
  color: rgb(203 213 225);
}
.nav-link:hover,
.nav-active {
  background: rgb(30 41 59);
  color: white;
}
</style>
