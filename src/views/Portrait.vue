<template>

<div class="h-full w-full relative flex">


<!-- Main Content Canvas -->
<div class="flex flex-1 overflow-hidden h-full">
<main class="p-8 flex-1 min-w-0 overflow-y-auto">
<div class="max-w-6xl mx-auto space-y-8">
<!-- Header: Suspect Profile -->
<section class="bg-white p-8 rounded border border-slate-200 shadow-sm relative overflow-hidden">
<div class="absolute top-0 right-0 p-4">
<span class="text-[10px] font-mono text-slate-400 tracking-tighter">案件编号: 编号_2024_0812</span>
</div>
<div class="flex gap-8 items-start">
<div class="w-32 h-40 bg-slate-100 border border-slate-200 rounded overflow-hidden flex-shrink-0">
<img alt="侦查对象画像" class="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDuJi9DCpNgxDf8fQNA2A37OhFK3z563odp7T6wvw74PFOlcUCwQYKzzk7v66Usp9vdid1bTu8YCCGvONVVKKf3KcIydVFlhFRpvRyZsT59FhuixSYHMda2sSDoQzTx2ekJkGNND6IJra9u43LMy8jMwxUtEe1PVNee8cN3zG-ZtFkhS9Kf8yqGbtScx2zHgnOQgWCAvAK29n0mYw4lznI_kDV2HHS-wUi8TeJ2pQgCSC5JWn6KV22weYG-cq7VKvihcxzH0nzMbu1y">
</div>
<div class="flex-grow">
<div class="flex items-center gap-3 mb-1">
<h1 class="text-2xl font-bold text-slate-900">程检察官</h1>
<span class="px-2 py-0.5 bg-error-container text-on-error-container text-[10px] font-bold rounded uppercase">高风险关注</span>
</div>
<p class="font-body-md text-on-surface-variant mb-6">“民名工程”内部事务调查重点关注对象。</p>
<div class="grid grid-cols-3 gap-y-4 gap-x-8">
<div class="border-l-2 border-blue-900 pl-3">
<div class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">职位</div>
<div class="font-data-mono text-on-surface">高级侦查员</div>
</div>
<div class="border-l-2 border-blue-900 pl-3">
<div class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">工号/证件号</div>
<div class="font-data-mono text-on-surface">普信-992-04182</div>
</div>
<div class="border-l-2 border-blue-900 pl-3">
<div class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">当前状态</div>
<div class="font-data-mono text-on-surface text-amber-600">实时监控中</div>
</div>
</div>
</div>
</div>
</section>
<div class="grid grid-cols-12 gap-8">
<!-- Section 1: Basic Info -->
<div class="col-span-12 lg:col-span-4 space-y-6">
<div class="bg-white p-6 rounded border border-slate-200 shadow-sm">
<div class="flex items-center gap-2 mb-4">
<Fingerprint class="shrink-0 w-5 h-5 text-blue-900 text-sm" />
<h2 class="text-xs font-bold uppercase tracking-widest">第一层：主体要件画像</h2>
</div>
<div class="space-y-4">
<div class="flex justify-between items-center py-2 border-b border-slate-50">
<span class="text-body-sm text-slate-500 whitespace-nowrap">法定姓名</span>
<span class="font-data-mono text-slate-900 whitespace-nowrap">程伟</span>
</div>
<div class="flex justify-between items-center py-2 border-b border-slate-50">
<span class="text-body-sm text-slate-500 whitespace-nowrap">出生日期</span>
<span class="font-data-mono text-slate-900 whitespace-nowrap">1978-05-12</span>
</div>
<div class="flex justify-between items-center py-2 border-b border-slate-50">
<span class="text-body-sm text-slate-500 whitespace-nowrap">国籍</span>
<span class="font-data-mono text-slate-900 whitespace-nowrap">中国</span>
</div>
<div class="flex justify-between items-center py-2 border-b border-slate-50">
<span class="text-body-sm text-slate-500 whitespace-nowrap">税务登记</span>
<span class="font-data-mono text-slate-900 whitespace-nowrap">已核验</span>
</div>
<div class="flex justify-between items-center py-2">
<span class="text-body-sm text-slate-500 whitespace-nowrap">资产评分</span>
<span class="font-data-mono text-blue-700">882 (极高)</span>
</div>
</div>
</div>
<!-- Risk Assessment Radar -->
<div class="bg-white p-6 rounded border border-slate-200 shadow-sm">
<div class="flex items-center gap-2 mb-4">
<Activity class="shrink-0 w-5 h-5 text-blue-900 text-sm" />
<h2 class="text-xs font-bold uppercase tracking-widest">第三层：主观意图研判</h2>
</div>
<div class="relative w-full aspect-square flex items-center justify-center mb-4">
<svg class="w-full h-full transform -rotate-18" viewBox="0 0 100 100">
<circle cx="50" cy="50" fill="none" r="45" stroke="#E2E8F0" stroke-width="0.5"></circle>
<circle cx="50" cy="50" fill="none" r="30" stroke="#E2E8F0" stroke-width="0.5"></circle>
<circle cx="50" cy="50" fill="none" r="15" stroke="#E2E8F0" stroke-width="0.5"></circle>
<path d="M50 5 L50 95 M5 50 L95 50 M18 18 L82 82 M18 82 L82 18" stroke="#E2E8F0" stroke-width="0.5"></path>
<polygon fill="#1B4D89" fill-opacity="0.2" points="50,20 80,40 70,75 30,80 20,40" stroke="#1B4D89" stroke-width="1.5"></polygon>
</svg>
<div class="absolute inset-0 flex flex-col items-center justify-center">
<span class="font-h2 text-blue-900">84</span>
<span class="text-[8px] font-bold uppercase">综合评分</span>
</div>
</div>
<div class="space-y-2">
<div class="flex justify-between text-[10px] font-bold text-slate-500 uppercase">
<span>犯罪意图</span>
<span class="text-error">92%</span>
</div>
<div class="w-full h-1 bg-slate-100 rounded-full overflow-hidden">
<div class="h-full bg-error w-[92%]"></div>
</div>
<div class="flex justify-between text-[10px] font-bold text-slate-500 uppercase mt-2">
<span>证据权重</span>
<span class="text-blue-900">65%</span>
</div>
<div class="w-full h-1 bg-slate-100 rounded-full overflow-hidden">
<div class="h-full bg-blue-900 w-[65%]"></div>
</div>
</div>
</div>
</div>
<!-- Section 2: Behavior Analysis -->
<div class="col-span-12 lg:col-span-8 space-y-6">
<div class="bg-white rounded border border-slate-200 shadow-sm overflow-hidden">
<div class="bg-slate-50 border-b border-slate-200 p-4 flex justify-between items-center">
<div class="flex items-center gap-2">
<History class="shrink-0 w-5 h-5 text-blue-900 text-sm" />
<h2 class="text-xs font-bold uppercase tracking-widest">第二层：行为事实还原</h2>
</div>
<span class="text-[10px] font-mono bg-white px-2 py-0.5 rounded border border-slate-200">记录总数：1247</span>
</div>
<div class="overflow-x-auto">
<table class="w-full text-left border-collapse">
<thead>
<tr class="bg-slate-50/50 text-[10px] font-bold text-slate-500 uppercase tracking-widest">
<th class="p-4 border-b border-slate-100">时间戳</th>
<th class="p-4 border-b border-slate-100">行为特征描述</th>
<th class="p-4 border-b border-slate-100">风险等级</th>
<th class="p-4 border-b border-slate-100 text-right">指标数据</th>
</tr>
</thead>
<tbody class="font-data-mono text-[13px]">
<tr class="hover:bg-slate-50/80 transition-colors border-b border-slate-50">
<td class="p-4 whitespace-nowrap text-slate-500">2024.08.10 03:22</td>
<td class="p-4 whitespace-nowrap">
<div class="font-bold text-on-surface">反侦查行为</div>
<div class="text-[11px] text-slate-400">在4号区域检测到重复的规避性驾驶行为模式。</div>
</td>
<td class="p-4 whitespace-nowrap">
<span class="px-2 py-0.5 bg-error/10 text-error rounded text-[10px] font-bold">严重</span>
</td>
<td class="p-4 whitespace-nowrap text-right">指标综合值: 0.89</td>
</tr>
<tr class="hover:bg-slate-50/80 transition-colors border-b border-slate-50 bg-slate-50/30">
<td class="p-4 whitespace-nowrap text-slate-500">2024.08.09 14:15</td>
<td class="p-4 whitespace-nowrap">
<div class="font-bold text-on-surface">可疑资金流动</div>
<div class="text-[11px] text-slate-400">在多个网点进行单日限额以下的结构化现金存款。</div>
</td>
<td class="p-4 whitespace-nowrap">
<span class="px-2 py-0.5 bg-amber-100 text-amber-700 rounded text-[10px] font-bold">预警</span>
</td>
<td class="p-4 whitespace-nowrap text-right">¥240,000</td>
</tr>
<tr class="hover:bg-slate-50/80 transition-colors border-b border-slate-50">
<td class="p-4 whitespace-nowrap text-slate-500">2024.08.08 22:10</td>
<td class="p-4 whitespace-nowrap">
<div class="font-bold text-on-surface">加密通讯活动</div>
<div class="text-[11px] text-slate-400">附近检测到未注册硬件物理网卡地址发出的信号脉冲。</div>
</td>
<td class="p-4 whitespace-nowrap">
<span class="px-2 py-0.5 bg-cyan-100 text-cyan-700 rounded text-[10px] font-bold">技术异常</span>
</td>
<td class="p-4 whitespace-nowrap text-right">高级加密标准</td>
</tr>
<tr class="hover:bg-slate-50/80 transition-colors border-b border-slate-50 bg-slate-50/30">
<td class="p-4 whitespace-nowrap text-slate-500">2024.08.07 11:30</td>
<td class="p-4 whitespace-nowrap">
<div class="font-bold text-on-surface">越权数据库访问</div>
<div class="text-[11px] text-slate-400">查询其管辖范围以外的有效逮捕令。</div>
</td>
<td class="p-4 whitespace-nowrap">
<span class="px-2 py-0.5 bg-error/10 text-error rounded text-[10px] font-bold">严重</span>
</td>
<td class="p-4 whitespace-nowrap text-right">查询次数: 14</td>
</tr>
</tbody>
</table>
</div>
</div>
<!-- Investigative Notes / AI Reasoning -->
<div class="bg-slate-900 text-slate-300 p-6 rounded shadow-lg border-l-4 border-cyan-500">
<div class="flex items-center justify-between mb-4">
<div class="flex items-center gap-2">
<BrainCircuit class="shrink-0 w-5 h-5 text-cyan-400 text-sm" />
<h3 class="text-xs font-bold uppercase tracking-widest text-white">智能推理链</h3>
</div>
<span class="text-[10px] font-mono text-cyan-500/70 tracking-tighter">置信度评分: 0.942</span>
</div>
<div class="font-data-mono text-[11px] leading-relaxed space-y-3">
<p>> [阶段 1] 财务行为表明处于洗钱循环的处置/层化阶段。</p>
<p>> [阶段 2] 反侦查规避行为与高价值会面之间的关联，证实了逃避监管的主观故意。</p>
<p>> [阶段 3] 数据库访问模式表明对象正在识别潜在杠杆或证人以进行恐吓。</p>
<p class="text-cyan-400 font-bold border-t border-slate-800 pt-3">> [研判结论] 该对象已满足妨害司法公正罪的 5 个构成要件中的 4 个。</p>
</div>
</div>
<div class="flex justify-end pt-4">
<button class="bg-white border border-slate-300 text-slate-900 px-6 py-3 rounded font-bold text-xs flex items-center gap-2 shadow-sm hover:bg-slate-50 transition-all uppercase tracking-widest">
<FileText class="shrink-0 w-5 h-5 text-lg" />
                        生成侦查研判报告
                    </button>
</div>
</div>
</div>
</div>
</main>
<!-- Navigation Drawer (AI Panel) -->
<aside class="z-40 w-72 bg-slate-50 dark:bg-slate-950 border-l border-slate-200 dark:border-slate-800 shadow-sm font-mono text-xs flex flex-col shrink-0 overflow-hidden">
<div class="p-6 border-b border-slate-200 dark:border-slate-800">
<div class="text-sm font-bold text-cyan-800 dark:text-cyan-300">智能推理面板</div>
<div class="text-[9px] text-slate-500 uppercase tracking-widest mt-1">基于大模型的意图研判</div>
</div>
<div class="p-4 space-y-4">
<div class="p-3 bg-cyan-50 dark:bg-cyan-900/30 text-cyan-900 dark:text-cyan-200 rounded border border-cyan-100 dark:border-cyan-800 flex items-center gap-3">
<BrainCircuit class="shrink-0 w-5 h-5" />
            主观意图分析
        </div>
<div class="p-3 text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-800 rounded flex items-center gap-3 cursor-pointer">
<Network class="shrink-0 w-5 h-5" />
            推理路径
        </div>
<div class="p-3 text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-800 rounded flex items-center gap-3 cursor-pointer">
<Database class="shrink-0 w-5 h-5" />
            源数据元数据
        </div>
<div class="mt-8">
<div class="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-4">证据图谱片段</div>
<div class="bg-white rounded border border-slate-200 h-48 overflow-hidden flex items-center justify-center">
<img alt="证据图谱" class="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBBRijnGzhW_uddi_PdFsN59ONVE6izuDfBDxBs7m2Stpu86NtCMlIir9uu-4PtpSft9Jf2Vth7yDBBXo-eGVofr4QigffmR2SnR08w4Er-jbZxRga38_q1RPY9nBOrDUO8u9PQOTG1aApShgYF5sNben9gC_KzLtJ76vqM7rKcYaXfZl0r4aumDBCd9VxyoG_vnKdBSCWURIchZGhDYplC4ELJYtBxHZadlTlbbu87_yaVvdC64Qnrtml-XXm0iHnkibCLYQ364BqL">
</div>
</div>
</div>
<div class="absolute bottom-0 w-full p-6 border-t border-slate-200 dark:border-slate-800 bg-slate-50/80 backdrop-blur-sm">
<div class="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-2">系统运行状态</div>
<div class="flex gap-1 h-1.5">
<div class="w-1/4 bg-blue-900 rounded-full"></div>
<div class="w-1/4 bg-blue-900 rounded-full"></div>
<div class="w-1/4 bg-blue-900 rounded-full"></div>
<div class="w-1/4 bg-slate-200 rounded-full"></div>
</div>
<div class="flex justify-between mt-2 text-[8px] text-slate-400">
<span>算力占用: 72%</span>
<span>延迟: 12毫秒</span>
</div>
</div>
</aside>
</div>
</div>

</template>
<script setup lang="ts">
import { Fingerprint, Activity, History, BrainCircuit, FileText, Network, Database } from "lucide-vue-next";
</script>
