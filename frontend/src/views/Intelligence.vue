<template>
  <div class="analysis-page">
    <section class="workspace">
      <header class="hero">
        <div>
          <h1>智能分析</h1>
          <p>三层画像白板：基础信息、行为事实、要件核查。字段可点击查看证据原文和溯源路径。</p>
        </div>
        <button class="primary-btn" :disabled="!activeCaseId || loading" @click="runAnalysis">
          {{ loading ? '分析中...' : '运行分析' }}
        </button>
      </header>

      <div class="case-line">
        <span>当前案件：</span>
        <code>{{ activeCaseId || '未选择案件' }}</code>
      </div>
      <p v-if="!activeCaseId" class="warn">请先到“案件导入”页新建或选择案件。</p>
      <p v-if="error" class="error">{{ error }}</p>

      <section class="stats">
        <div><span>节点</span><strong>{{ graph?.nodes.length ?? 0 }}</strong></div>
        <div><span>关系</span><strong>{{ graph?.edges.length ?? 0 }}</strong></div>
        <div><span>线索</span><strong>{{ graph?.clues.length ?? 0 }}</strong></div>
        <div><span>状态</span><strong>{{ runStatus }}</strong></div>
      </section>

      <section class="summary-card">
        <h2>分析摘要</h2>
        <div class="markdown" v-html="renderMarkdown(analysisSummary)" />
      </section>

      <section class="layer-card">
        <div class="layer-head">
          <span>第一层</span>
          <h2>基础信息卡片</h2>
          <p>身份、职务、权限、关系网络。每个字段都能回到证据原文和路径候选。</p>
        </div>
        <div class="field-grid">
          <button v-for="field in basicFields" :key="field.key" class="field-card" @click="openTrace(field)">
            <span>{{ field.label }}</span>
            <strong>{{ field.value }}</strong>
            <small>{{ field.evidenceIds.length ? `${field.evidenceIds.length} 份证据` : '暂无直接证据' }}</small>
          </button>
        </div>
      </section>

      <section class="layer-card">
        <div class="layer-head">
          <span>第二层</span>
          <h2>行为事实还原</h2>
          <p>更细地还原资金、通话、文书处置和行为方式，特别关注隐瞒、规避留痕和反侦察动作。</p>
        </div>
        <div class="timeline-list">
          <button v-for="field in behaviorFields" :key="field.key" class="fact-row" @click="openTrace(field)">
            <div>
              <strong>{{ field.label }}</strong>
              <div class="markdown" v-html="renderMarkdown(field.value)" />
            </div>
            <span>{{ field.evidenceIds.length }} 证据</span>
          </button>
        </div>
      </section>

      <section class="layer-card">
        <div class="layer-head">
          <span>第三层</span>
          <h2>要件拆解、证据归类、缺口标红、抗辩预判</h2>
          <p>这里不只列线索，而是看每个要件现在有没有证据支撑，缺什么，对方可能怎么辩。</p>
        </div>
        <div class="element-grid">
          <button v-for="item in elementFields" :key="item.key" class="element-card" :class="{ gap: item.status === 'gap' }" @click="openTrace(item)">
            <div>
              <strong>{{ item.label }}</strong>
              <span>{{ item.status === 'ok' ? '已有支撑' : '缺口待补强' }}</span>
            </div>
            <p>{{ item.value }}</p>
          </button>
        </div>
        <div class="defense-box">
          <h3>抗辩预判</h3>
          <button v-for="item in defenseFields" :key="item.key" class="defense-item" @click="openTrace(item)">
            <span>{{ item.label }}</span>
            <p>{{ item.value }}</p>
          </button>
        </div>
      </section>

      <section class="layer-card">
        <div class="layer-head inline">
          <div>
            <span>线索</span>
            <h2>案件级线索</h2>
          </div>
          <router-link to="/graph">查看证据图谱</router-link>
        </div>
        <div v-if="!graph?.clues.length" class="empty">暂无线索。</div>
        <article v-for="clue in graph?.clues || []" :key="clue.clue_id" class="clue" @click="openTrace(fieldFromClue(clue))">
          <div>
            <h3>{{ clue.title }}</h3>
            <span>{{ clue.category }} / {{ clue.risk_level }}</span>
          </div>
          <div class="markdown" v-html="renderMarkdown(clue.description)" />
        </article>
      </section>
    </section>

    <aside v-if="traceOpen" class="trace-panel">
      <div class="trace-head">
        <div>
          <h2>{{ traceField?.label }}</h2>
          <p>证据原文 + 溯源路径候选</p>
        </div>
        <button @click="traceOpen = false">关闭</button>
      </div>
      <div class="trace-section">
        <h3>字段内容</h3>
        <div class="markdown" v-html="renderMarkdown(traceField?.value || '')" />
      </div>
      <div class="trace-section">
        <h3>证据原文</h3>
        <div v-if="evidenceLoading" class="muted">正在读取证据和 HippoRAG PPR 排序...</div>
        <div v-else-if="traceEvidence.length === 0" class="muted">暂无直接证据 ID。可以到图谱页按主体和路径继续追。</div>
        <article v-for="item in traceEvidence" :key="item.evidence_id" class="evidence-doc">
          <strong>{{ item.title }}</strong>
          <pre>{{ item.content }}</pre>
        </article>
      </div>
      <div class="trace-section">
        <h3>HippoRAG PPR 检索结果</h3>
        <div v-if="traceResult?.error" class="trace-error">{{ traceResult.error }}</div>
        <div v-if="!traceResult?.passages.length" class="muted">暂无 PPR passage 结果。</div>
        <article v-for="item in traceResult?.passages || []" :key="`${item.rank}-${item.evidence_id}-${item.score}`" class="ppr-card">
          <div>
            <strong>#{{ item.rank }} / score {{ item.score.toFixed(4) }}</strong>
            <span>{{ item.evidence_title || item.evidence_id || '未映射证据' }}</span>
          </div>
          <p>{{ item.passage }}</p>
        </article>
      </div>
      <div class="trace-section">
        <h3>图谱溯源路径候选</h3>
        <div v-if="tracePaths.length === 0" class="muted">暂无路径候选。</div>
        <div v-for="path in tracePaths" :key="path" class="path-line">{{ path }}</div>
      </div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { backendApi, type AnalysisRunResult, type EvidenceDetail, type InvestigationGraph, type SuspiciousClue, type TraceResult } from '../api/backend';

interface TraceField {
  key: string;
  label: string;
  value: string;
  evidenceIds: string[];
  status?: 'ok' | 'gap';
  keywords?: string[];
}

const activeCaseId = ref(localStorage.getItem('active_case_id') || '');
const loading = ref(false);
const error = ref('');
const result = ref<AnalysisRunResult | null>(null);
const graph = ref<InvestigationGraph | null>(null);
const traceOpen = ref(false);
const traceField = ref<TraceField | null>(null);
const traceEvidence = ref<EvidenceDetail[]>([]);
const traceResult = ref<TraceResult | null>(null);
const evidenceLoading = ref(false);

const analysisSummary = computed(() => {
  if (result.value?.summary) return `**${result.value.summary}**`;
  if (graph.value?.nodes.length) {
    return `已有图谱结果：**${graph.value.nodes.length}** 个节点，**${graph.value.edges.length}** 条关系，**${graph.value.clues.length}** 条案件级线索。点击“运行分析”可重新生成。`;
  }
  return '暂无分析结果。导入证据后点击 **运行分析**。';
});

const runStatus = computed(() => {
  if (loading.value) return '分析中';
  if (result.value?.status) return result.value.status;
  if (graph.value?.nodes.length) return '已有图谱';
  return '未运行';
});

const basicFields = computed<TraceField[]>(() => {
  const current = graph.value;
  const top = topEntityLabels(current);
  return [
    makeField('basic.case', '案件对象', '杨周武徇私枉法案', ['案件', '杨周武']),
    makeField('basic.identity', '身份/职务', findText('杨周武|派出所|所长|民警|司法工作人员') || '待从证据中确认司法工作人员身份、任职单位和职责权限。', ['杨周武', '派出所', '所长']),
    makeField('basic.power', '职权范围', findText('立案|拘留|释放|调解|撤销|审批|处置') || '待确认其是否实际参与或控制立案、拘留、调解、撤案、释放等处置。', ['立案', '拘留', '释放', '调解']),
    makeField('basic.relations', '关键关系人', top.length ? top.join('、') : '待识别关键人员关系。', top),
  ];
});

const behaviorFields = computed<TraceField[]>(() => {
  const clues = graph.value?.clues || [];
  return [
    makeField('behavior.qa', '模型行为链条还原', clueText('behavior_reconstruction') || '暂无模型生成的完整行为链条。', ['行为', '链条', '处置']),
    makeField('behavior.fund', '资金往来', clueText('fund_flow') || relationSummary(/资金|交易|转账|收款|付款|金额|现金|取现|存入/) || '暂无明确资金链条。', ['资金', '交易', '转账', '现金']),
    makeField('behavior.duty', '职务处置', clueText('duty_behavior') || relationSummary(/立案|拘留|释放|调解|撤销|审批|执法|报告|决定/) || '暂无明确职务处置链条。', ['立案', '拘留', '释放', '调解', '撤销']),
    makeField('behavior.method', '行为方式/反侦察', behaviorModeText() || '暂未发现足够明确的隐瞒、白手套过桥、现金化处理、文书倒签或规避留痕迹象。', ['隐瞒', '现金', '取现', '代持', '马甲', '倒签']),
    ...clues.filter((clue) => !['behavior_reconstruction', 'fund_flow', 'duty_behavior'].includes(clue.category)).slice(0, 4).map(fieldFromClue),
  ];
});

const elementFields = computed<TraceField[]>(() => [
  elementField('element.subject', '主体要件', /杨周武|派出所|所长|民警|司法工作人员/, '司法工作人员身份、职务权限、经办范围。'),
  elementField('element.objective', '客观行为', /立案|拘留|释放|调解|撤销|审批|执法|处置|包庇|追诉/, '是否存在应立不立、违法调解、违法撤案、释放或降低处理强度。'),
  elementField('element.subjective', '主观方面', /明知|故意|徇私|请托|收钱|利益|动机|隐瞒/, '明知、徇私动机、请托、利益输送与处置变化之间的关联。'),
  elementField('element.result', '结果与因果', /逃避追诉|释放|撤销|被害人|赔偿|后果|影响/, '错误处置、逃避追诉、被害人权益受损及因果关系。'),
]);

const defenseFields = computed<TraceField[]>(() => [
  makeField('defense.mistake', '认识错误抗辩', '可能主张只是业务判断或事实认识偏差。需要补强其知悉伤情、案件事实、法律后果的证据。', ['明知', '伤情', '鉴定']),
  makeField('defense.procedure', '程序瑕疵抗辩', '可能主张只是程序不规范而非徇私枉法。需要证明异常处置与请托、利益输送或特定关系存在关联。', ['程序', '调解', '撤销', '释放']),
  makeField('defense.money', '资金无关抗辩', '可能主张资金是借款、还款、投资或正常往来。需要核查备注、资金来源、过桥账户、现金取存闭环与处置节点。', ['借款', '还款', '资金', '现金']),
  makeField('defense.power', '职责边界抗辩', '可能主张没有决定权或只是执行上级意见。需要还原经办、审批、授意、协调、签批链条。', ['审批', '经办', '决定', '上级']),
]);

const tracePaths = computed(() => (traceResult.value?.paths || []).map((path) => `${path.source} --${path.relation}--> ${path.target}  score ${path.score.toFixed(2)}`));

onMounted(loadGraph);

async function loadGraph() {
  if (!activeCaseId.value) return;
  try {
    graph.value = await backendApi.getGraph(activeCaseId.value);
  } catch {
    graph.value = null;
  }
}

async function runAnalysis() {
  if (!activeCaseId.value) return;
  loading.value = true;
  error.value = '';
  try {
    result.value = await backendApi.runAnalysis(activeCaseId.value);
    graph.value = result.value.graph;
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    loading.value = false;
  }
}

async function openTrace(field: TraceField) {
  traceField.value = field;
  traceOpen.value = true;
  traceEvidence.value = [];
  traceResult.value = null;
  evidenceLoading.value = true;
  try {
    traceResult.value = await backendApi.traceAnalysis(activeCaseId.value, `${field.label}\n${field.value}`, field.evidenceIds, 8);
    const ids = new Set<string>(field.evidenceIds.slice(0, 5));
    traceResult.value.passages.forEach((item) => {
      if (item.evidence_id && ids.size < 5) ids.add(item.evidence_id);
    });
    traceEvidence.value = await Promise.all([...ids].map((id) => backendApi.getEvidenceDetail(activeCaseId.value, id)));
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    evidenceLoading.value = false;
  }
}

function makeField(key: string, label: string, value: string, keywords: string[] = []): TraceField {
  return { key, label, value, keywords, evidenceIds: evidenceIdsForKeywords(keywords.length ? keywords : [label, value]) };
}

function fieldFromClue(clue: SuspiciousClue): TraceField {
  return {
    key: clue.clue_id,
    label: clue.title,
    value: clue.description,
    evidenceIds: clue.evidence_ids,
    keywords: [clue.title, clue.category],
    status: clue.risk_level === 'high' ? 'gap' : 'ok',
  };
}

function elementField(key: string, label: string, pattern: RegExp, fallback: string): TraceField {
  const matched = relationSummary(pattern) || findText(pattern.source) || fallback;
  const evidenceIds = evidenceIdsForPattern(pattern);
  return { key, label, value: matched, evidenceIds, keywords: [label, ...pattern.source.split('|')], status: evidenceIds.length ? 'ok' : 'gap' };
}

function clueText(category: string) {
  return (graph.value?.clues || []).filter((clue) => clue.category === category).map((clue) => clue.description).join('\n\n');
}

function relationSummary(pattern: RegExp) {
  const edges = (graph.value?.edges || []).filter((edge) => pattern.test(`${edge.relation} ${JSON.stringify(edge.properties || {})}`)).slice(0, 6);
  if (edges.length === 0) return '';
  return edges
    .map((edge) => {
      const source = graph.value?.nodes.find((node) => node.node_id === edge.source_id)?.label || edge.source_id;
      const target = graph.value?.nodes.find((node) => node.node_id === edge.target_id)?.label || edge.target_id;
      return `- ${source} -> **${edge.relation}** -> ${target}`;
    })
    .join('\n');
}

function behaviorModeText() {
  const parts: string[] = [];
  const all = JSON.stringify(graph.value || {});
  if (/现金|取现|存入|ATM/.test(all)) parts.push('**现金化处理**：出现取现、存入或现金相关表述，应核查是否用于切断资金流留痕。');
  if (/过桥|代持|控制账户|马甲|假名|别名/.test(all)) parts.push('**白手套/马甲账户**：出现控制、代持、马甲或别名线索，应建立真人合并建议并人工确认。');
  if (/删除|隐瞒|倒签|补录|撤销|释放/.test(all)) parts.push('**程序规避或留痕异常**：出现删除、隐瞒、倒签、补录、撤销、释放等词，需核查文书时间和审批链。');
  return parts.join('\n\n');
}

function findText(patternSource: string) {
  const pattern = new RegExp(patternSource);
  const clue = (graph.value?.clues || []).find((item) => pattern.test(item.title + item.description));
  if (clue) return clue.description;
  const edge = (graph.value?.edges || []).find((item) => pattern.test(item.relation + JSON.stringify(item.properties || {})));
  if (!edge) return '';
  const source = graph.value?.nodes.find((node) => node.node_id === edge.source_id)?.label || edge.source_id;
  const target = graph.value?.nodes.find((node) => node.node_id === edge.target_id)?.label || edge.target_id;
  return `${source} -> ${edge.relation} -> ${target}`;
}

function evidenceIdsForKeywords(keywords: string[]) {
  const ids = new Set<string>();
  const words = keywords.filter(Boolean).slice(0, 8);
  (graph.value?.nodes || []).forEach((node) => {
    const text = `${node.label} ${JSON.stringify(node.properties || {})}`;
    if (words.some((word) => text.includes(word))) node.evidence_ids.forEach((id) => ids.add(id));
  });
  (graph.value?.edges || []).forEach((edge) => {
    const text = `${edge.relation} ${JSON.stringify(edge.properties || {})}`;
    if (words.some((word) => text.includes(word))) edge.evidence_ids.forEach((id) => ids.add(id));
  });
  return [...ids];
}

function evidenceIdsForPattern(pattern: RegExp) {
  const ids = new Set<string>();
  (graph.value?.nodes || []).forEach((node) => {
    if (pattern.test(`${node.label} ${JSON.stringify(node.properties || {})}`)) node.evidence_ids.forEach((id) => ids.add(id));
  });
  (graph.value?.edges || []).forEach((edge) => {
    if (pattern.test(`${edge.relation} ${JSON.stringify(edge.properties || {})}`)) edge.evidence_ids.forEach((id) => ids.add(id));
  });
  return [...ids];
}

function topEntityLabels(currentGraph: InvestigationGraph | null) {
  if (!currentGraph) return [];
  const labels = new Map(currentGraph.nodes.filter((node) => node.type !== 'evidence' && node.type !== 'algorithm_provider').map((node) => [node.node_id, node.label]));
  const degree = new Map<string, number>();
  currentGraph.edges.forEach((edge) => {
    if (labels.has(edge.source_id)) degree.set(edge.source_id, (degree.get(edge.source_id) || 0) + 1);
    if (labels.has(edge.target_id)) degree.set(edge.target_id, (degree.get(edge.target_id) || 0) + 1);
  });
  return Array.from(degree.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([id]) => labels.get(id) || id);
}

function renderMarkdown(value: string) {
  const escaped = escapeHtml(value || '');
  return escaped
    .replace(/^### (.*)$/gm, '<h4>$1</h4>')
    .replace(/^## (.*)$/gm, '<h3>$1</h3>')
    .replace(/^# (.*)$/gm, '<h2>$1</h2>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/==(.+?)==/g, '<mark>$1</mark>')
    .replace(/^- (.*)$/gm, '<div class="md-list">• $1</div>')
    .replace(/\n/g, '<br />');
}

function escapeHtml(value: string) {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
</script>

<style scoped>
.analysis-page {
  height: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  background: #eef3f7;
  color: #0f172a;
}
.workspace {
  overflow: auto;
  padding: 24px;
}
.hero,
.summary-card,
.layer-card {
  border: 1px solid #d8e1ea;
  border-radius: 10px;
  background: #ffffff;
  padding: 18px;
  margin-bottom: 16px;
}
.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.hero h1 {
  font-size: 22px;
  font-weight: 900;
}
.hero p,
.case-line,
.layer-head p,
.empty {
  color: #64748b;
  font-size: 14px;
}
.primary-btn {
  border-radius: 8px;
  background: #0f766e;
  color: #ffffff;
  padding: 10px 16px;
  font-weight: 900;
}
.primary-btn:disabled {
  opacity: 0.5;
}
.case-line {
  margin: 0 0 14px;
}
.warn,
.error {
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 14px;
  margin-bottom: 14px;
}
.warn {
  border: 1px solid #fde68a;
  background: #fffbeb;
  color: #92400e;
}
.error {
  border: 1px solid #fecdd3;
  background: #fff1f2;
  color: #be123c;
}
.stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.stats div {
  border: 1px solid #d8e1ea;
  border-radius: 10px;
  background: #ffffff;
  padding: 14px;
}
.stats span {
  display: block;
  color: #64748b;
  font-size: 13px;
}
.stats strong {
  display: block;
  margin-top: 5px;
  font-size: 26px;
}
.summary-card h2,
.layer-head h2 {
  font-size: 18px;
  font-weight: 900;
}
.layer-head span {
  color: #0f766e;
  font-size: 12px;
  font-weight: 900;
}
.layer-head.inline {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.layer-head a {
  color: #0f766e;
  font-weight: 900;
}
.field-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-top: 14px;
}
.field-card,
.fact-row,
.element-card,
.defense-item,
.clue {
  text-align: left;
  border: 1px solid #e2e8f0;
  border-radius: 9px;
  background: #f8fafc;
  padding: 13px;
}
.field-card:hover,
.fact-row:hover,
.element-card:hover,
.defense-item:hover,
.clue:hover {
  border-color: #0f766e;
  background: #f0fdfa;
}
.field-card span,
.field-card small {
  display: block;
  color: #64748b;
  font-size: 12px;
}
.field-card strong {
  display: block;
  margin: 8px 0;
  font-size: 16px;
  line-height: 1.4;
}
.timeline-list {
  display: grid;
  gap: 10px;
  margin-top: 14px;
}
.fact-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 12px;
}
.fact-row strong {
  font-size: 15px;
}
.fact-row > span {
  color: #0f766e;
  font-size: 12px;
  font-weight: 900;
}
.element-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-top: 14px;
}
.element-card.gap {
  border-color: #fdba74;
  background: #fff7ed;
}
.element-card div {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}
.element-card strong {
  font-weight: 900;
}
.element-card span {
  color: #0f766e;
  font-size: 12px;
  font-weight: 900;
}
.element-card.gap span {
  color: #c2410c;
}
.element-card p,
.defense-item p {
  margin-top: 8px;
  color: #475569;
  font-size: 13px;
  line-height: 1.6;
}
.defense-box {
  margin-top: 16px;
}
.defense-box h3 {
  font-weight: 900;
  margin-bottom: 10px;
}
.defense-item {
  width: 100%;
  margin-bottom: 8px;
}
.defense-item span {
  font-weight: 900;
}
.clue {
  width: 100%;
  margin-top: 10px;
}
.clue div:first-child {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.clue h3 {
  font-weight: 900;
}
.clue span {
  color: #64748b;
  font-size: 12px;
}
.trace-panel {
  overflow: auto;
  border-left: 1px solid #23324b;
  background: #0f172a;
  color: #ffffff;
  padding: 16px;
}
.trace-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 14px;
}
.trace-head h2 {
  font-size: 18px;
  font-weight: 900;
}
.trace-head p,
.muted {
  color: #94a3b8;
  font-size: 13px;
}
.trace-head button {
  align-self: start;
  border: 1px solid #334155;
  border-radius: 7px;
  padding: 6px 10px;
}
.trace-section {
  border: 1px solid #23324b;
  border-radius: 9px;
  background: #111c31;
  padding: 13px;
  margin-bottom: 12px;
}
.trace-section h3 {
  font-weight: 900;
  margin-bottom: 8px;
}
.evidence-doc {
  border-top: 1px solid #23324b;
  padding-top: 10px;
  margin-top: 10px;
}
.evidence-doc strong {
  display: block;
  margin-bottom: 8px;
}
.evidence-doc pre {
  max-height: 360px;
  overflow: auto;
  white-space: pre-wrap;
  color: #cbd5e1;
  font-size: 12px;
  line-height: 1.6;
}
.path-line {
  border-top: 1px solid #23324b;
  padding: 8px 0;
  color: #bae6fd;
  font-size: 13px;
}
.trace-error {
  border: 1px solid #7f1d1d;
  border-radius: 7px;
  background: #450a0a;
  color: #fecaca;
  padding: 8px;
  font-size: 12px;
  line-height: 1.5;
  margin-bottom: 8px;
}
.ppr-card {
  border-top: 1px solid #23324b;
  padding: 10px 0;
}
.ppr-card div {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  color: #ffffff;
  font-size: 13px;
}
.ppr-card span {
  color: #7dd3fc;
  font-size: 12px;
  text-align: right;
}
.ppr-card p {
  margin-top: 6px;
  color: #cbd5e1;
  font-size: 12px;
  line-height: 1.6;
}
.markdown {
  color: inherit;
  font-size: 14px;
  line-height: 1.7;
}
.markdown :deep(strong) {
  font-weight: 900;
}
.markdown :deep(mark) {
  border-radius: 4px;
  background: #fed7aa;
  color: #9a3412;
  padding: 0 3px;
}
.markdown :deep(.md-list) {
  margin: 2px 0;
}
@media (max-width: 1200px) {
  .analysis-page {
    grid-template-columns: 1fr;
  }
  .trace-panel {
    border-left: 0;
    border-top: 1px solid #23324b;
  }
  .field-grid,
  .element-grid,
  .stats {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
