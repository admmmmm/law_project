<template>

<div class="h-full w-full relative flex">


<!-- Main Work Canvas -->
<div class="flex flex-1 overflow-hidden h-full">
<main class="pt-6 pb-24 px-6 gradient-mesh flex-1 min-w-0 overflow-y-auto">
<!-- Dashboard Header -->
<div class="mb-8 border-b border-outline-variant pb-4 flex justify-between items-end">
<div>
<h2 class="text-2xl font-bold text-slate-900 mb-1 flex items-center gap-2">
<Scale class="shrink-0 w-5 h-5" />
                主观意图研判：徇私枉法
            </h2>
<div class="flex gap-4 items-center">
<span class="text-data-mono bg-surface-container-high px-2 py-0.5 border border-outline-variant">案件编号: 案件-2024-0912</span>
<span class="text-data-mono text-secondary">涉及罪名: 徇私枉法罪</span>
</div>
</div>
<div class="flex gap-2">
<button class="flex items-center gap-2 px-3 py-1.5 border border-outline text-body-sm hover:bg-surface-container transition-colors">
<Download class="shrink-0 w-5 h-5" />
                导出研判结果
            </button>
<button class="flex items-center gap-2 px-3 py-1.5 bg-secondary text-on-secondary text-body-sm font-bold">
<CheckCircle class="shrink-0 w-5 h-5" />
                确认主观意图
            </button>
</div>
</div>
<div class="grid grid-cols-12 gap-6 items-stretch min-w-[1100px] h-[calc(100vh-12rem)] pb-4">
<!-- Left: Evidence Chain -->
<section class="col-span-3 flex flex-col gap-4">
<div class="flex items-center justify-between">
<h3 class="font-bold text-slate-800 text-sm">提取证据三元组</h3>
<span class="text-[10px] text-slate-500">已加载 12 组三元组</span>
</div>
<div class="flex flex-col gap-3 overflow-y-auto pr-2 pb-6">
<!-- Triple Item -->
<div class="p-3 bg-white border border-slate-200 rounded-lg shadow-sm hover:border-blue-400 transition-all group">
<div class="flex items-center justify-between mb-2">
<span class="text-[10px] font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded">结构化数据</span>
<Info class="shrink-0 w-4 h-4 text-slate-400" />
</div>
<div class="flex flex-col gap-1.5 text-xs">
<div class="flex items-center gap-2">
<span class="text-slate-400 w-8">主体</span>
<span class="text-slate-800 bg-slate-100 px-1.5 py-0.5 rounded font-medium">嫌疑人_张伟</span>
</div>
<div class="flex items-center gap-2">
<span class="text-slate-400 w-8">关系</span>
<span class="text-blue-600 font-bold">故意隐瞒证据</span>
</div>
<div class="flex items-center gap-2">
<span class="text-slate-400 w-8">客体</span>
<span class="text-slate-800 bg-slate-100 px-1.5 py-0.5 rounded font-medium">物证包_甲04</span>
</div>
</div>
<div class="mt-2 pt-2 border-t border-slate-100 flex gap-2">
<span class="text-[9px] text-slate-500 bg-slate-50 px-1.5 py-0.5 rounded border border-slate-100">日志_2023.10.12</span>
</div>
</div>
<!-- Triple Item 2 -->
<div class="p-3 bg-white border border-slate-200 rounded-lg shadow-sm hover:border-purple-400 transition-all group">
<div class="flex items-center justify-between mb-2">
<span class="text-[10px] font-bold text-purple-700 bg-purple-50 px-2 py-0.5 rounded">非结构化通讯</span>
<Link class="shrink-0 w-4 h-4 text-slate-400" />
</div>
<div class="flex flex-col gap-1.5 text-xs">
<div class="flex items-center gap-2">
<span class="text-slate-400 w-8">主体</span>
<span class="text-slate-800 bg-slate-100 px-1.5 py-0.5 rounded font-medium">关系人_李某</span>
</div>
<div class="flex items-center gap-2">
<span class="text-slate-400 w-8">关系</span>
<span class="text-purple-600 font-bold">利益输送承诺</span>
</div>
<div class="flex items-center gap-2">
<span class="text-slate-400 w-8">客体</span>
<span class="text-slate-800 bg-slate-100 px-1.5 py-0.5 rounded font-medium">撤诉请求</span>
</div>
</div>
</div>
</div>
</section>

<!-- Center: Reasoning Chain -->
<section class="col-span-6 bg-white border border-slate-200 p-5 rounded-xl shadow-sm flex flex-col relative overflow-hidden">
<div class="absolute inset-0 bg-slate-50 opacity-50 pointer-events-none" style="background-image: radial-gradient(circle at 2px 2px, #cbd5e1 1px, transparent 0); background-size: 24px 24px;"></div>
<h3 class="font-bold text-slate-800 text-sm mb-6 flex items-center gap-2 relative shrink-0">
<Network class="shrink-0 w-4 h-4 text-blue-600" />
主观意图逻辑链
</h3>
<div class="flex flex-row items-center justify-center gap-3 flex-1 overflow-x-auto pb-4 relative">
<!-- Step 1 -->
<div class="flex flex-col items-center gap-3 w-40 shrink-0">
<div class="w-8 h-8 rounded-full border-2 border-blue-500 bg-blue-50 text-blue-600 flex items-center justify-center font-bold text-sm z-10 relative">
1
</div>
<div class="p-3 bg-white border border-slate-200 shadow-sm rounded-lg flex flex-col gap-1.5 text-center w-full z-10">
<span class="text-[11px] font-bold text-blue-600">知情阶段</span>
<p class="text-[11px] text-slate-700 leading-relaxed font-medium">签收物证包 '甲04'，确认已接触关键证据。</p>
</div>
</div>
<!-- Arrow -->
<div class="h-px w-6 bg-slate-300 relative shrink-0">
<div class="absolute -right-1 -top-[3px] w-1.5 h-1.5 border-t-2 border-r-2 border-slate-400 transform rotate-45"></div>
</div>
<!-- Step 2 -->
<div class="flex flex-col items-center gap-3 w-40 shrink-0">
<div class="w-8 h-8 rounded-full border-2 border-blue-500 bg-blue-50 text-blue-600 flex items-center justify-center font-bold text-sm z-10 relative">
2
</div>
<div class="p-3 bg-white border border-slate-200 shadow-sm rounded-lg flex flex-col gap-1.5 text-center w-full z-10">
<span class="text-[11px] font-bold text-blue-600">认知认同</span>
<p class="text-[11px] text-slate-700 leading-relaxed font-medium">明知 '甲04' 足以支持起诉但选择隐瞒。</p>
</div>
</div>
<!-- Arrow -->
<div class="h-px w-6 bg-slate-300 relative shrink-0">
<div class="absolute -right-1 -top-[3px] w-1.5 h-1.5 border-t-2 border-r-2 border-slate-400 transform rotate-45"></div>
</div>
<!-- Step 3 (Fork) -->
<div class="flex flex-col gap-3 shrink-0 w-44 z-10">
<div class="p-3 border-[1.5px] border-blue-500 bg-blue-50 rounded-lg flex flex-col gap-1 shadow-sm ring-2 ring-blue-500/10">
<div class="flex items-center justify-between">
<span class="text-[11px] font-bold text-blue-700">故意性成立</span>
<CheckCircle class="shrink-0 w-3.5 h-3.5 text-blue-600" />
</div>
<p class="text-[11px] font-bold text-slate-800">蓄意渎职 / 徇私</p>
</div>
<div class="p-3 border border-slate-200 bg-white opacity-60 rounded-lg flex flex-col gap-1">
<span class="text-[11px] font-bold text-slate-500">严重过失排除</span>
<p class="text-[11px] font-bold text-slate-700">非意外遗失</p>
</div>
</div>
</div>

<!-- Final Conclusion Node -->
<div class="mt-4 p-4 bg-slate-900 border border-slate-700 rounded-xl shadow-lg flex justify-between items-center w-full shrink-0 relative z-10">
<div class="flex items-center gap-4">
<div class="w-10 h-10 bg-blue-900/40 text-blue-400 rounded-full flex items-center justify-center shrink-0">
<Scale class="w-5 h-5" />
</div>
<div>
<span class="text-[10px] uppercase tracking-widest font-black text-slate-400 block mb-0.5">研判结论</span>
<h4 class="text-lg font-black text-white tracking-tight leading-none">主观故意: 徇私枉法</h4>
</div>
</div>
<div class="flex gap-5 items-center">
<div class="flex flex-col items-end">
<span class="text-xl font-black text-blue-400">94%</span>
<span class="text-[9px] uppercase text-slate-400 mt-0.5">置信度</span>
</div>
<div class="w-px h-6 bg-slate-700"></div>
<div class="flex flex-col items-end">
<span class="text-xl font-black text-red-500">严重</span>
<span class="text-[9px] uppercase text-slate-400 mt-0.5">情节程度</span>
</div>
</div>
</div>
</section>

<!-- Right: Prosecution Suggestion -->
<section class="col-span-3 flex flex-col gap-4">
<div class="flex items-center justify-between">
<h3 class="font-bold text-slate-800 text-sm flex items-center gap-2">
<Gavel class="shrink-0 w-4 h-4 text-slate-500" />
起诉建议书
</h3>
<span class="text-[10px] text-blue-600 font-bold bg-blue-50 px-2 py-0.5 rounded border border-blue-100">草案生成</span>
</div>
<div class="bg-slate-50 p-4 rounded-xl border border-slate-200 shadow-inner flex flex-col flex-1 gap-3 overflow-y-auto">
<div class="text-[11px] text-slate-700 leading-relaxed font-medium">
<p class="mb-2">
<span class="font-bold text-slate-900">摘要:</span> 被告人张伟在承办案件期间，涉嫌犯有 <span class="text-red-700 font-bold bg-red-50 px-1 rounded border-b border-red-200">徇私枉法罪</span>。
</p>
<p class="mb-2">证据链显示，被告人于接受利益承诺后故意隐瞒关键物证，致使嫌疑人逃避法律制裁，主观故意明显。</p>
<p>建议处理：立即采取刑事拘留措施，并启动进一步审查程序。</p>
</div>

<div class="mt-auto flex flex-col gap-2 pt-4">
<div class="p-2 border-l-2 border-blue-500 bg-white shadow-sm mb-1">
<span class="text-[9px] font-bold text-blue-700 block mb-0.5 uppercase tracking-wider">法律判例参考</span>
<p class="text-[10px] text-slate-600 font-medium">高法案例 #1029-22: 枉法裁判主观故意认定</p>
</div>
<button class="w-full py-2.5 bg-slate-900 hover:bg-black text-white rounded font-bold text-xs shadow-sm transition-colors text-center w-full block border-none">
生成正式起诉稿
</button>
<button class="w-full py-2 border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 rounded font-bold text-xs transition-colors text-center w-full block">
提交专家评议
</button>
</div>
</div>
</section>
</div>
</main>
<!-- Right side: AI Inference Assistant -->
<aside class="z-40 bg-slate-50 dark:bg-slate-950 border-l border-slate-200 dark:border-slate-800 flex flex-col shadow-sm font-mono text-xs shrink-0 w-72">
<div class="p-6 border-b border-slate-200">
<h2 class="text-sm font-bold text-cyan-800 dark:text-cyan-300">智能研判面板</h2>
<p class="text-[10px] text-slate-500 mt-1 uppercase tracking-tighter font-sans">基于大模型的意图分析</p>
</div>
<div class="flex flex-1 overflow-hidden">
<!-- Sidebar within drawer -->
<div class="w-12 flex flex-col items-center py-4 gap-6 bg-slate-100 border-r border-slate-200">
<BrainCircuit class="shrink-0 w-5 h-5" />
<Network class="shrink-0 w-5 h-5" />
<Database class="shrink-0 w-5 h-5" />
</div>
<div class="flex-1 p-4 overflow-y-auto">
<div class="space-y-6">
<div>
<h4 class="text-[10px] font-bold text-cyan-700 uppercase mb-3">提取原始片段</h4>
<!-- Passage Card -->
<div class="p-3 bg-white border border-slate-200 rounded-sm mb-3">
<div class="flex justify-between items-center mb-2">
<span class="bg-cyan-100 text-cyan-800 text-[9px] px-1 font-bold">来源: 聊天记录_#441</span>
<span class="text-slate-400 text-[8px]">0.98 可靠度</span>
</div>
<p class="italic text-slate-700 leading-relaxed">“……只要10月12号那个片子消失，大家的麻烦就都解决了。事成之后，后台少不了你的好处。”</p>
</div>
<!-- Passage Card 2 -->
<div class="p-3 bg-white border border-slate-200 rounded-sm">
<div class="flex justify-between items-center mb-2">
<span class="bg-cyan-100 text-cyan-800 text-[9px] px-1 font-bold">来源: 证人证言笔录</span>
<span class="text-slate-400 text-[8px]">0.84 可靠度</span>
</div>
<p class="italic text-slate-700 leading-relaxed">“张伟盯着卷宗看了很久，最后他没把东西放进证据柜，而是锁进了自己的私人抽屉里。”</p>
</div>
</div>
<div class="pt-4 border-t border-slate-200">
<h4 class="text-[10px] font-bold text-cyan-700 uppercase mb-3">推理步骤分析</h4>
<div class="space-y-2">
<div class="flex gap-2">
<span class="text-cyan-600 font-bold">01</span>
<p class="text-[11px] text-slate-600">交叉比对物理证据接触时间与系统录入缺失记录。</p>
</div>
<div class="flex gap-2">
<span class="text-cyan-600 font-bold">02</span>
<p class="text-[11px] text-slate-600">语义关联分析：“后台好处”与次日账户异常入账 12,000 元的高度对齐。</p>
</div>
</div>
</div>
<div class="mt-8 bg-cyan-900 text-cyan-50 p-4 rounded-lg">
<div class="flex items-center gap-2 mb-2">
<Zap class="shrink-0 w-5 h-5" />
<span class="text-[10px] font-bold">推理引擎报告</span>
</div>
<p class="text-[10px] leading-relaxed opacity-80">
                        最终分析建议认定为“故意渎职”，且存在明显的“权钱交易”次生特征。证据库映射密度直接指向徇私枉法罪犯罪构成要件。
                    </p>
</div>
</div>
</div>
</div>
</aside>
</div>
</div>

</template>
<script setup lang="ts">
import { Scale, Download, CheckCircle, Info, Link, Network, Gavel, BrainCircuit, Database, Zap } from "lucide-vue-next";
</script>
