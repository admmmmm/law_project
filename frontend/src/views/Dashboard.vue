<template>
  <div class="p-6 h-full flex gap-6 overflow-hidden max-w-[1400px] mx-auto">
    
    <!-- Left Column -->
    <div class="flex-1 flex flex-col gap-6 min-w-0 h-full">
      
      <!-- Cases List -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col flex-1 overflow-hidden">
        <div class="grid grid-cols-5 text-[11px] text-gray-400 font-bold tracking-wider uppercase border-b border-gray-100 p-4 pb-3">
          <div class="col-span-1 whitespace-nowrap overflow-hidden text-ellipsis pl-2">案件编号</div>
          <div class="col-span-1 whitespace-nowrap overflow-hidden text-ellipsis">侦查对象</div>
          <div class="col-span-1 whitespace-nowrap overflow-hidden text-ellipsis">罪名</div>
          <div class="col-span-1 whitespace-nowrap overflow-hidden text-ellipsis">案件进度</div>
          <div class="col-span-1 whitespace-nowrap overflow-hidden text-ellipsis text-right pr-2">风险等级</div>
        </div>
        <div class="overflow-y-auto flex-1 px-2 pb-2">
          <div v-for="(item, idx) in cases" :key="idx" class="grid grid-cols-5 items-center p-3 hover:bg-[#f8fafc] rounded-lg transition-colors border-b border-gray-50/50 text-[13px] last:border-0 group cursor-pointer">
            <div class="col-span-1 whitespace-nowrap overflow-hidden text-ellipsis text-[#1e4b8c] font-medium tracking-wide">{{ item.id }}</div>
            <div class="col-span-1 whitespace-nowrap overflow-hidden text-ellipsis flex items-center gap-3">
              <img :src="item.avatar" class="w-7 h-7 rounded-full shadow-sm" />
              <span class="font-bold text-gray-900 group-hover:text-[#1e4b8c] transition-colors">{{ item.name }}</span>
            </div>
            <div class="col-span-1 whitespace-nowrap overflow-hidden text-ellipsis font-bold text-gray-700">
              <span class="bg-[#f1f5f9] px-2.5 py-1 rounded-[4px] text-[12px] whitespace-nowrap">{{ item.charge }}</span>
            </div>
            <div class="col-span-1 whitespace-nowrap overflow-hidden text-ellipsis flex items-center pr-4">
              <div class="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
                <div class="bg-[#1e4b8c] h-full rounded-full transition-all duration-500" :style="{ width: item.progress + '%' }"></div>
              </div>
            </div>
            <div class="col-span-1 whitespace-nowrap overflow-hidden text-ellipsis flex items-center justify-end gap-1.5 font-bold text-[12px] pr-2" :class="item.riskColor">
              <div class="w-1.5 h-1.5 rounded-full" :class="item.riskDot"></div>
              {{ item.risk }}
            </div>
          </div>
        </div>
      </div>

      <!-- Evidence Timeline -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 flex-1 overflow-hidden flex flex-col p-5">
        <div class="flex items-center gap-2 mb-5">
          <div class="text-[#0ea5e9]">
            <History :size="20" :stroke-width="2.5" />
          </div>
          <h3 class="font-bold text-gray-900 text-[15px] tracking-wide">证据活动时序图</h3>
        </div>
        <div class="flex-1 overflow-y-auto pr-2 relative mt-2">
          <div class="absolute left-[11px] top-2 bottom-0 w-[2px] bg-gray-100"></div>
          
          <div class="relative flex items-start gap-4 mb-5">
            <div class="w-6 h-6 rounded-full bg-[#0ea5e9] text-white flex items-center justify-center shrink-0 z-10 shadow-sm ring-[6px] ring-white">
              <Mic :size="12" :stroke-width="3" />
            </div>
            <div class="flex-1 mt-0.5">
              <div class="flex justify-between items-baseline mb-1">
                <h4 class="font-bold text-[13px] text-gray-900">录音日志已上传</h4>
                <span class="text-[11px] text-gray-400 font-medium tracking-wide">14:22:10</span>
              </div>
              <p class="text-[12px] text-gray-500 break-keep leading-relaxed max-w-[90%]">对象 中发-4421 的最新谈话录音已存入证据库。自动转写已启动。</p>
            </div>
          </div>

          <div class="relative flex items-start gap-4 mb-5">
            <div class="w-6 h-6 rounded-full bg-[#1e4b8c] text-white flex items-center justify-center shrink-0 z-10 shadow-sm ring-[6px] ring-white">
              <Database :size="12" :stroke-width="3" />
            </div>
            <div class="flex-1 mt-0.5">
              <div class="flex justify-between items-baseline mb-1">
                <h4 class="font-bold text-[13px] text-gray-900">财务记录已关联</h4>
                <span class="text-[11px] text-gray-400 font-medium tracking-wide">11:05:45</span>
              </div>
              <p class="text-[12px] text-gray-500 break-keep leading-relaxed max-w-[90%]">已从04管辖区关联跨境跨行外汇转账数据。系统识别出相关键碰撞点。</p>
            </div>
          </div>

          <div class="relative flex items-start gap-4">
            <div class="w-6 h-6 rounded-full bg-gray-200 text-gray-400 flex items-center justify-center shrink-0 z-10 shadow-sm ring-[6px] ring-white">
              <FileText :size="12" :stroke-width="3" />
            </div>
            <div class="flex-1 mt-0.5">
              <div class="flex justify-between items-baseline mb-1">
                <h4 class="font-bold text-[13px] text-gray-500">案件文档归档</h4>
                <span class="text-[11px] text-gray-400 font-medium tracking-wide">08:00:00</span>
              </div>
              <p class="text-[12px] text-gray-400 leading-relaxed max-w-[90%]">系统维护：正在将2023年历史案卷文档移至冷存储。</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Middle Column -->
    <div class="w-[280px] flex flex-col gap-6 h-full shrink-0">
      
      <!-- Alert 丙ard -->
      <div class="bg-white rounded-xl shadow-sm border border-red-200 p-5 relative overflow-hidden group hover:border-red-300 transition-colors">
        <div class="absolute top-0 left-0 w-[3px] h-full bg-red-500"></div>
        <div class="flex items-start gap-3">
          <AlertTriangle :size="20" class="text-red-500 shrink-0 mt-0.5 group-hover:scale-110 transition-transform" />
          <div>
            <h4 class="font-bold text-[14px] text-red-600 mb-2">异常循环注资</h4>
            <p class="text-[12px] text-gray-600 break-keep leading-[1.6]">识别到目标甲与目标丙之间通过壳公司进行的1,200万资金往来。</p>
          </div>
        </div>
        <div class="flex gap-2 mt-4 ml-[32px]">
          <span class="bg-gray-100 text-gray-700 text-[10px] px-2 py-0.5 rounded-[4px] font-bold border border-gray-200 tracking-wide">主体碰撞</span>
          <span class="bg-red-50 text-red-600 text-[10px] px-2 py-0.5 rounded-[4px] font-bold border border-red-100 tracking-wide">高风险</span>
        </div>
      </div>

      <!-- Relationship 丙ard -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
        <div class="flex items-start gap-3 mb-2">
          <Users :size="20" class="text-[#1e4b8c] shrink-0 mt-0.5" />
          <div>
            <h4 class="font-bold text-[14px] text-gray-900 mb-2">关联关系重叠</h4>
            <p class="text-[12px] text-gray-600 break-keep leading-[1.6]">对象王伟与黑名单账户 <span class="font-mono bg-gray-100 px-1 py-0.5 rounded text-[11px]">#7712</span> 共享4个共同联系节点。</p>
          </div>
        </div>
        <div class="ml-[32px] mt-3">
          <a href="#" class="text-[#1e4b8c] text-[12px] font-bold hover:underline flex items-center gap-1 w-max">核查图谱 <ChevronRight :size="14" /></a>
        </div>
        <button class="w-full mt-5 bg-[#f8fafc] hover:bg-gray-100 text-gray-600 text-xs font-bold py-2.5 rounded-lg border border-gray-200 transition-colors">
          清除已处理项
        </button>
      </div>

      <!-- Map 丙ard -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 relative overflow-hidden">
        <div class="flex items-center gap-2 mb-3 px-1">
          <MapPin :size="18" class="text-[#1e4b8c]" />
          <h4 class="font-bold text-[14px] text-gray-900">实时管辖地图</h4>
        </div>
        <div class="h-28 bg-[#dff0ea] rounded-xl relative overflow-hidden mb-3 border border-[#bde0d5]">
           <div class="absolute inset-0 bg-[#c6e4db] opacity-60" style="background-image: radial-gradient(#9ebdbe 1.5px, transparent 1.5px); background-size: 10px 10px;"></div>
           
           <!-- Map Points -->
           <div class="absolute top-[40%] left-[30%] w-3 h-3 bg-red-500 rounded-full ring-4 ring-red-500/30 animate-pulse -translate-x-1/2 -translate-y-1/2"></div>
           <div class="absolute top-[30%] left-[60%] w-2 h-2 bg-[#1e4b8c] rounded-full ring-[3px] ring-blue-500/30 -translate-x-1/2 -translate-y-1/2"></div>
           <div class="absolute bottom-[20%] right-[25%] w-2.5 h-2.5 bg-teal-500 rounded-full ring-[3px] ring-teal-500/30 -translate-x-1/2 -translate-y-1/2"></div>
           <div class="absolute top-[60%] left-[75%] w-1.5 h-1.5 bg-[#0ea5e9] rounded-full ring-[2px] ring-sky-500/20"></div>
           
           <div class="absolute top-2 right-2 bg-gray-900/90 text-white text-[10px] px-2 py-1 rounded-md font-bold tracking-wide backdrop-blur-sm">实时动态</div>
        </div>
        <div class="flex items-center justify-between text-[11px] font-bold text-gray-600 px-1">
          <div class="flex items-center gap-2"><span class="w-2 h-2 rounded-full bg-red-500"></span> <span class="text-gray-800">1条预警</span></div>
          <div class="flex items-center gap-2"><span class="w-2 h-2 rounded-full bg-teal-500"></span> 28件在办</div>
        </div>
      </div>

      <!-- Terminal Panel -->
      <div class="bg-[#0f172a] rounded-xl p-5 flex-1 overflow-hidden flex flex-col border border-gray-800 shadow-lg relative min-h-[160px]">
        <div class="absolute inset-0 bg-gradient-to-b from-[#1e293b]/50 to-transparent pointer-events-none"></div>
        <div class="flex items-center gap-2 mb-4 text-[#38bdf8] relative z-10">
          <TerminalSquare :size="16" />
          <h4 class="font-bold text-[13px] tracking-wide">智能思考进程记录</h4>
        </div>
        <div class="flex-1 overflow-y-auto text-[11px] font-mono space-y-2.5 leading-relaxed relative z-10 tracking-tight">
          <p class="text-gray-400"><span class="text-[#38bdf8] font-bold">></span> 启动向量检索... <span class="text-[#34d399] font-bold ml-1">完成</span></p>
          <p class="text-gray-400"><span class="text-[#38bdf8] font-bold">></span> 分析意图模式: "被迫行为" <span class="text-yellow-400 font-bold">(78%)</span></p>
          <p class="text-gray-400"><span class="text-[#38bdf8] font-bold">></span> 交叉比对笔录全文... <span class="text-[#34d399] font-bold ml-1">发现匹配</span></p>
          <div class="mt-4 pt-4 border-t border-gray-700/50">
            <p class="text-[#f8fafc] font-bold mb-1.5 flex items-center gap-1.5"><Sparkles :size="12" class="text-yellow-400"/> 系统建议：</p>
            <p class="text-gray-300 pb-1">在证据 <span class="text-[#38bdf8]">#8812</span> 上部署 "<span class="text-white font-bold">寻真者</span>" 逻辑链以确证动机。</p>
          </div>
        </div>
      </div>

    </div>

    <!-- Right Column -->
    <div class="w-[280px] bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col shrink-0 overflow-hidden relative">
      <div class="p-6 border-b border-gray-100 z-10 relative bg-white">
        <h3 class="font-bold text-[16px] text-gray-900 mb-1 tracking-wide">智能研判面板</h3>
        <p class="text-[11px] text-gray-500 mb-6 font-medium">基于大语言模型的主观意图分析</p>

        <div class="space-y-3">
          <button class="w-full flex items-center bg-[#ebf3fc] border border-[#1e4b8c]/20 text-left px-4 py-3.5 rounded-xl transition-all shadow-sm group">
            <div class="flex items-center gap-3">
              <Lightbulb :size="18" class="text-[#1e4b8c]" :stroke-width="2.5" />
              <span class="text-[13px] font-bold text-[#1e4b8c] tracking-wide">主观意图分析</span>
            </div>
          </button>
          
          <button class="w-full flex items-center hover:bg-gray-50 text-left px-4 py-3.5 rounded-xl transition-all border border-gray-100 group">
            <div class="flex items-center gap-3">
              <GitMerge :size="18" class="text-gray-400 group-hover:text-[#1e4b8c] transition-colors" />
              <span class="text-[13px] font-bold text-gray-600 group-hover:text-gray-900 transition-colors">推理逻辑链</span>
            </div>
          </button>

          <button class="w-full flex items-center hover:bg-gray-50 text-left px-4 py-3.5 rounded-xl transition-all border border-gray-100 group">
            <div class="flex items-center gap-3">
              <Database :size="18" class="text-gray-400 group-hover:text-[#1e4b8c] transition-colors" />
              <span class="text-[13px] font-bold text-gray-600 group-hover:text-gray-900 transition-colors">数据原元数据</span>
            </div>
          </button>
        </div>
      </div>

      <div class="p-5 flex-1 overflow-y-auto bg-gray-50/50 z-10 relative">
        <h4 class="text-[11px] font-bold text-gray-400 tracking-widest mb-4 uppercase">推演任务队列</h4>
        
        <div class="space-y-3 relative">
          <!-- Connective line -->
          <div class="absolute left-4 top-4 bottom-4 w-px bg-gray-200"></div>

          <!-- Task 1 -->
          <div class="bg-white border text-left p-4 rounded-xl border-[#1e4b8c]/20 shadow-sm relative overflow-hidden z-10">
            <div class="flex items-center justify-between mb-3">
              <div class="flex items-center gap-2">
                <Spinner :size="14" class="text-[#1e4b8c] animate-spin" />
                <span class="font-bold text-[13px] text-gray-900 tracking-wide">案件-<span class="font-mono">0089</span></span>
              </div>
              <span class="text-[10px] font-bold text-[#1e4b8c] tracking-wider">正在运行</span>
            </div>
            <div class="w-full bg-gray-100 rounded-full h-1.5 mb-3 overflow-hidden">
              <div class="bg-[#1e4b8c] h-1.5 rounded-full w-[65%] shadow-[0_0_10px_rgba(30,75,140,0.5)]"></div>
            </div>
            <p class="text-[11.5px] break-keep text-gray-600 leading-relaxed font-medium">正在从42份笔录中提取动机模式...</p>
          </div>

          <!-- Task 2 -->
          <div class="bg-white border border-gray-200 text-left p-4 rounded-xl relative z-10 hover:border-gray-300 transition-colors">
            <div class="flex items-center justify-between mb-2">
              <span class="font-bold text-[13px] text-gray-700 tracking-wide pl-6 relative">
                 <div class="absolute left-1 top-1.5 w-1.5 h-1.5 rounded-full bg-gray-300"></div>
                 案件-<span class="font-mono">0091</span>
              </span>
              <span class="text-[10px] font-bold text-gray-400 tracking-wider">排队中</span>
            </div>
            <p class="text-[11.5px] break-keep text-gray-500 leading-relaxed font-medium">预定计划：资金流向意图深度分析。</p>
          </div>

          <!-- Task 3 -->
          <div class="bg-white border border-gray-200 text-left p-4 rounded-xl opacity-75 relative z-10">
            <div class="flex items-center justify-between mb-2">
              <span class="font-bold text-[13px] text-gray-600 tracking-wide pl-6 relative">
                 <CheckCircle2 :size="12" class="absolute left-0 top-1 text-teal-500" />
                 案件-<span class="font-mono">1422</span>
              </span>
              <span class="text-[10px] font-bold text-teal-600 tracking-wider bg-teal-50 px-2 py-0.5 rounded-full">已完成</span>
            </div>
            <p class="text-[11.5px] break-keep text-gray-500 leading-relaxed font-medium">摘要：检测到高概率 <span class="bg-red-50 text-red-600 px-1 rounded font-bold">徇私枉法</span> 主观意图。</p>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { 
  History, Mic, Database, FileText, AlertTriangle, Users, MapPin, 
  TerminalSquare, Lightbulb, GitMerge, ChevronRight, Loader2 as Spinner, CheckCircle2, Sparkles 
} from 'lucide-vue-next';

const cases = ref([
  { id: '中发-2024-4421', avatar: 'https://i.pravatar.cc/150?u=12', name: '王伟', charge: '徇私枉法', progress: 65, risk: '高风险', riskColor: 'text-red-600', riskDot: 'bg-red-500' },
  { id: '中发-2024-3819', avatar: 'https://i.pravatar.cc/150?u=24', name: '李娜', charge: '滥用职权', progress: 40, risk: '中风险', riskColor: 'text-orange-500', riskDot: 'bg-orange-500' },
  { id: '中发-2024-1104', avatar: 'https://i.pravatar.cc/150?u=36', name: '张强', charge: '玩忽职守', progress: 15, risk: '低风险', riskColor: 'text-teal-500', riskDot: 'bg-teal-500' },
  { id: '中发-2024-9912', avatar: 'https://i.pravatar.cc/150?u=48', name: '陈磊', charge: '贪污受贿', progress: 85, risk: '高风险', riskColor: 'text-red-600', riskDot: 'bg-red-500' },
  { id: '中发-2024-2211', avatar: 'https://i.pravatar.cc/150?u=50', name: '刘洋', charge: '受贿罪', progress: 50, risk: '中风险', riskColor: 'text-orange-500', riskDot: 'bg-orange-500' },
  { id: '中发-2024-3388', avatar: 'https://i.pravatar.cc/150?u=62', name: '赵静', charge: '巨额财产来源不明', progress: 25, risk: '高风险', riskColor: 'text-red-600', riskDot: 'bg-red-500' },
]);
</script>
