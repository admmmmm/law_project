<template>

<div class="h-full w-full relative flex">

<!-- Main Content Canvas Area -->
<main class="flex flex-col w-full h-full">

<!-- Primary Workspace -->
<div class="flex flex-grow overflow-hidden">
<!-- Relationship Analysis Sidebar (Left) -->
<aside class="w-64 h-full bg-surface shrink-0 z-10 border-r border-outline-variant p-margin flex flex-col gap-6 overflow-y-auto">
<div>
<h3 class="font-h3 text-h3 mb-4 flex items-center gap-2">
<Filter class="shrink-0 w-5 h-5" />
                    图谱过滤
                </h3>
<div class="space-y-5">
<section>
<label class="text-label-caps text-on-surface-variant block mb-2">关联强度</label>
<input class="w-full accent-secondary" max="100" min="0" type="range" value="65">
<div class="flex justify-between text-[10px] text-on-surface-variant mt-1">
<span>弱相关</span>
<span>强相关</span>
</div>
</section>
<section>
<label class="text-label-caps text-on-surface-variant block mb-3">数据源接入</label>
<div class="space-y-2">
<label class="flex items-center gap-3 p-2 bg-white border border-outline-variant rounded hover:border-secondary cursor-pointer transition-colors">
<input checked="" class="rounded border-outline-variant text-secondary focus:ring-secondary" type="checkbox">
<span class="text-body-sm flex-grow">银行转账记录</span>
<Landmark class="shrink-0 w-5 h-5" />
</label>
<label class="flex items-center gap-3 p-2 bg-white border border-outline-variant rounded hover:border-secondary cursor-pointer transition-colors">
<input checked="" class="rounded border-outline-variant text-secondary focus:ring-secondary" type="checkbox">
<span class="text-body-sm flex-grow">通讯通话详单</span>
<Phone class="shrink-0 w-5 h-5" />
</label>
<label class="flex items-center gap-3 p-2 bg-white border border-outline-variant rounded hover:border-secondary cursor-pointer transition-colors">
<input class="rounded border-outline-variant text-secondary focus:ring-secondary" type="checkbox">
<span class="text-body-sm flex-grow">民政公共记录</span>
<FileText class="shrink-0 w-5 h-5" />
</label>
<label class="flex items-center gap-3 p-2 bg-white border border-outline-variant rounded hover:border-secondary cursor-pointer transition-colors">
<input checked="" class="rounded border-outline-variant text-secondary focus:ring-secondary" type="checkbox">
<span class="text-body-sm flex-grow">出入境记录</span>
<Plane class="shrink-0 w-5 h-5" />
</label>
</div>
</section>
<section>
<label class="text-label-caps text-on-surface-variant block mb-2">时间维度重构</label>
<div class="bg-white border border-outline-variant p-3 rounded space-y-3">
<div>
<span class="text-[10px] text-slate-500 uppercase font-bold">起始节点</span>
<div class="text-xs font-data-mono mt-1">2023-11-04 08:30:00</div>
</div>
<div class="h-10 w-full bg-slate-50 rounded border border-dashed border-slate-200 relative">
<div class="absolute inset-y-0 left-1/4 w-1/2 bg-secondary/20 border-x border-secondary"></div>
</div>
<div>
<span class="text-[10px] text-slate-500 uppercase font-bold">截止节点</span>
<div class="text-xs font-data-mono mt-1">2024-05-12 23:59:59</div>
</div>
</div>
</section>
</div>
</div>
<div class="mt-auto pt-6 border-t border-outline-variant">
<div class="p-4 bg-primary-container rounded-lg text-white">
<div class="text-[10px] font-bold opacity-60 mb-1">研判聚类</div>
<div class="text-body-md font-bold mb-3 uppercase tracking-tighter">行为异常判定：高风险</div>
<div class="flex gap-1">
<span class="w-full h-1 bg-white/20 rounded-full overflow-hidden">
<span class="block h-full bg-error w-[88%]"></span>
</span>
</div>
<div class="text-[10px] mt-2 flex justify-between">
<span>88% 冲突指数</span>
<AlertTriangle class="shrink-0 w-5 h-5" />
</div>
</div>
</div>
</aside>
<!-- Center Canvas: Knowledge Graph -->
<section class="flex-grow relative bg-[#0B1220] overflow-hidden graph-canvas">
<!-- Floating Toolbar -->
<div class="absolute top-6 left-1/2 -translate-x-1/2 z-10 flex bg-white/90 backdrop-blur-md shadow-xl border border-slate-200 p-1.5 rounded-xl">
<button class="flex items-center gap-2 px-4 py-2 hover:bg-slate-100 rounded-lg text-sm font-semibold transition-colors border-r border-slate-200 whitespace-nowrap">
<Combine class="shrink-0 w-5 h-5" />
                    跨案碰撞
                </button>
<button class="flex items-center gap-2 px-4 py-2 hover:bg-slate-100 rounded-lg text-sm font-semibold transition-colors border-r border-slate-200 whitespace-nowrap">
<Waypoints class="shrink-0 w-5 h-5" />
                    路径追踪
                </button>
<button class="flex items-center gap-2 px-4 py-2 hover:bg-slate-100 rounded-lg text-sm font-semibold transition-colors whitespace-nowrap">
<Network class="shrink-0 w-5 h-5" />
                    扩线分析
                </button>
</div>
<!-- Graph Visualization -->
<svg class="w-full h-full" viewBox="0 0 1000 800">
<defs>
<linearGradient id="linkGradient" x1="0%" x2="100%" y1="0%" y2="0%">
<stop offset="0%" stop-color="#325f9c"></stop>
<stop offset="100%" stop-color="#009397"></stop>
</linearGradient>
</defs>
<g class="stroke-slate-700 opacity-40">
<path d="M500 400 L300 250" stroke-width="1"></path>
<path class="stroke-secondary" d="M500 400 L700 280" stroke-width="2"></path>
<path d="M500 400 L500 650" stroke-dasharray="4,4" stroke-width="1"></path>
<path d="M700 280 L850 450" stroke-width="1.5"></path>
<path d="M300 250 L150 400" stroke-width="1"></path>
<path d="M700 280 L680 100" stroke-width="1"></path>
</g>
<g>
<!-- Main Subject -->
<g class="cursor-pointer">
<circle class="node-pulse" cx="500" cy="400" fill="#1B4D89" r="45"></circle>
<image clip-path="inset(0% round 50%)" height="60" width="60" x="470" xlink:href="https://images.unsplash.com/photo-1560250097-0b93528c311a?auto=format&fit=crop&q=80&w=100&h=100" y="370"></image>
<text class="font-data-mono text-[10px] tracking-widest uppercase" fill="#FFFFFF" text-anchor="middle" x="500" y="465">核心目标_01</text>
<circle cx="535" cy="375" fill="#BA1A1A" r="8"></circle>
<text class="text-[8px] font-bold" fill="#FFFFFF" text-anchor="middle" x="535" y="378">!</text>
</g>
<!-- Bank Account Node -->
<g class="cursor-pointer">
<circle cx="700" cy="280" fill="#1E293B" r="30" stroke="#A7C8FF" stroke-width="2"></circle>
<Landmark class="text-lg" color="#A7C8FF" x="688" y="269" width="24" height="24" />
<text class="font-data-mono text-[8px]" fill="#94A3B8" text-anchor="middle" x="700" y="325">账户_4420_香港</text>
</g>
<!-- Organization Node -->
<g class="cursor-pointer">
<circle cx="300" cy="250" fill="#002021" r="35" stroke="#2BDBE1" stroke-width="1"></circle>
<Building2 class="text-xl" color="#2BDBE1" x="288" y="239" width="24" height="24" />
<text class="font-data-mono text-[8px]" fill="#94A3B8" text-anchor="middle" x="300" y="305">全球物流有限公司</text>
</g>
<!-- Behavior Node -->
<g class="cursor-pointer">
<rect fill="#000000" height="50" rx="4" stroke="#E63946" stroke-width="1" width="50" x="475" y="625"></rect>
<Handshake class="text-xl" color="#E63946" x="488" y="639" width="24" height="24" />
<text class="font-data-mono text-[8px]" fill="#94A3B8" text-anchor="middle" x="500" y="695">事件：隐秘同步</text>
</g>
</g>
</svg>
<!-- Legend Overlay -->
<div class="absolute bottom-margin left-margin bg-black/40 backdrop-blur-sm p-4 rounded-lg border border-slate-700/50">
<div class="text-[10px] text-slate-400 font-bold uppercase mb-2">图谱图例</div>
<div class="space-y-2">
<div class="flex items-center gap-3">
<span class="w-3 h-3 rounded-full bg-secondary"></span>
<span class="text-xs text-white">主体节点</span>
</div>
<div class="flex items-center gap-3">
<span class="w-3 h-3 rounded bg-on-tertiary-container"></span>
<span class="text-xs text-white">法律实体</span>
</div>
<div class="flex items-center gap-3">
<span class="w-3 h-0.5 bg-secondary"></span>
<span class="text-xs text-white">确证关联</span>
</div>
<div class="flex items-center gap-3">
<span class="w-3 h-0.5 border-t border-dashed border-slate-500"></span>
<span class="text-xs text-white">推断相关</span>
</div>
</div>
</div>
<!-- Canvas Controls -->
<div class="absolute bottom-margin right-margin flex flex-col gap-2">
<button class="w-10 h-10 bg-white shadow-lg rounded-lg flex items-center justify-center text-slate-600 hover:text-blue-600 active:scale-95 transition-all">
<ZoomIn class="shrink-0 w-5 h-5" />
</button>
<button class="w-10 h-10 bg-white shadow-lg rounded-lg flex items-center justify-center text-slate-600 hover:text-blue-600 active:scale-95 transition-all">
<ZoomOut class="shrink-0 w-5 h-5" />
</button>
<button class="w-10 h-10 bg-white shadow-lg rounded-lg flex items-center justify-center text-slate-600 hover:text-blue-600 active:scale-95 transition-all">
<Focus class="shrink-0 w-5 h-5" />
</button>
</div>
</section>
<!-- Node Details Sidebar (Right) -->
<aside class="w-72 h-full bg-slate-50 border-l border-slate-200 flex flex-col z-40 shrink-0">
<div class="p-density-comfortable border-b border-slate-200 bg-white">
<div class="flex justify-between items-start mb-4">
<h2 class="text-cyan-800 font-bold text-sm tracking-tight uppercase">智能研判面板</h2>
<button class="text-slate-400 hover:text-slate-600">
<X class="shrink-0 w-5 h-5" />
</button>
</div>
<div class="flex gap-3 mb-4">
<div class="w-16 h-16 rounded bg-slate-100 border border-slate-200 overflow-hidden flex-shrink-0">
<img alt="选中节点" class="w-full h-full object-cover grayscale" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDUjfUHodjWYsYnQLVpyUxCfy5Rdux4GtMkRCXYx9llpfQfQHBghA0kJusScv-YV_-mI4iP4WTPiYHDBM1tfdFnqk1UAvfM21pHJGg4KsyCPe3IGZGdeEzninNmd6xqrFqHSU5PtPJzgebtIsUvExYbZWh8ApApUwe_1_xJalVSFJkNBfp_Pv4ESfU_TeFNEABAwi5lXa_Ax7NQkNgagNtdso0c9v2BSqbAZ3ZCxQEVrV2lKc_B8GgsNvOMAI7OYr6tle-hgMkKNxl5">
</div>
<div>
<div class="text-body-md font-bold text-slate-900 leading-tight">程伟良</div>
<div class="text-xs font-data-mono text-secondary mt-1">编号: 综研-99283-01</div>
<div class="flex gap-1 mt-2">
<span class="px-1.5 py-0.5 bg-error/10 text-error rounded text-[9px] font-black tracking-widest uppercase">高风险</span>
<span class="px-1.5 py-0.5 bg-slate-200 text-slate-600 rounded text-[9px] font-black tracking-widest uppercase">活跃中</span>
</div>
</div>
</div>
</div>
<div class="flex border-b border-slate-200">
<button class="flex-grow py-3 text-cyan-900 bg-cyan-50 border-b-2 border-cyan-700 font-mono text-xs uppercase flex items-center justify-center gap-2">
<BrainCircuit class="shrink-0 w-5 h-5" />
                    主观意图
                </button>
<button class="flex-grow py-3 text-slate-500 hover:bg-slate-200 font-mono text-xs uppercase flex items-center justify-center gap-2">
<Network class="shrink-0 w-5 h-5" />
                    逻辑链条
                </button>
<button class="flex-grow py-3 text-slate-500 hover:bg-slate-200 font-mono text-xs uppercase flex items-center justify-center gap-2">
<Database class="shrink-0 w-5 h-5" />
                    元数据
                </button>
</div>
<div class="flex-grow overflow-y-auto p-density-comfortable space-y-6">
<div>
<h4 class="text-label-caps text-slate-400 mb-3 flex items-center gap-2">
                        行为轨迹还原
                        <span class="h-px bg-slate-200 flex-grow"></span>
</h4>
<div class="space-y-3">
<div class="bg-white p-3 border border-slate-200 rounded relative overflow-hidden">
<div class="absolute top-0 left-0 w-1 h-full bg-secondary"></div>
<div class="flex justify-between text-[10px] text-slate-500 mb-1">
<span>2024-04-12 14:02</span>
<span class="text-secondary font-bold">同步日志</span>
</div>
<div class="text-xs leading-relaxed text-slate-700">
                                实体在“全球物流有限公司”附近被探测到，与大额空壳账户电汇时间吻合。
                            </div>
</div>
<div class="bg-white p-3 border border-slate-200 rounded relative overflow-hidden">
<div class="absolute top-0 left-0 w-1 h-full bg-error"></div>
<div class="flex justify-between text-[10px] text-slate-500 mb-1">
<span>2024-05-01 03:15</span>
<span class="text-error font-bold">行为异常判定</span>
</div>
<div class="text-xs leading-relaxed text-slate-700">
                                检测到加密通讯绕过。确认在移动过程中使用了本地网状网络。
                            </div>
</div>
</div>
</div>
<div>
<h4 class="text-label-caps text-slate-400 mb-3 flex items-center gap-2">
                        核心关联关系
                        <span class="h-px bg-slate-200 flex-grow"></span>
</h4>
<div class="bg-white border border-slate-200 divide-y divide-slate-100 rounded">
<div class="p-3 flex items-center gap-3">
<div class="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center">
<User class="shrink-0 w-5 h-5" />
</div>
<div class="flex-grow">
<div class="text-[11px] font-bold">黄莎莎</div>
<div class="text-[10px] text-slate-500">法律顾问</div>
</div>
<div class="text-[10px] font-bold text-secondary">82% 匹配度</div>
</div>
<div class="p-3 flex items-center gap-3">
<div class="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center">
<Building2 class="shrink-0 w-5 h-5" />
</div>
<div class="flex-grow">
<div class="text-[11px] font-bold">顶峰创投</div>
<div class="text-[10px] text-slate-500">控股公司</div>
</div>
<div class="text-[10px] font-bold text-secondary">95% 关联度</div>
</div>
</div>
</div>
</div>
<div class="p-density-comfortable border-t border-slate-200 bg-white">
<button class="w-full bg-secondary text-white py-3 rounded text-[11px] font-bold uppercase tracking-widest hover:opacity-90 active:scale-95 transition-all">
                    生成全案卷宗
                </button>
</div>
</aside>
</div>
</main>
</div>

</template>
<script setup lang="ts">
import { Filter, Landmark, Phone, FileText, Plane, AlertTriangle, Combine, Waypoints, Network, Handshake, ZoomIn, ZoomOut, Focus, X, BrainCircuit, Database, User, Building2 } from "lucide-vue-next";
</script>
