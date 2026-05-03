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
          <article v-for="field in basicFields" :key="field.key" class="field-card">
            <span>{{ field.label }}</span>
            <div class="sentence-stack">
              <button
                v-for="sentence in traceSentences(field)"
                :key="sentenceKey(field, sentence)"
                class="claim-chip"
                :class="{ hover: hoveredSentenceKey === sentenceKey(field, sentence), active: traceKey === sentenceKey(field, sentence) }"
                @mouseenter="hoveredSentenceKey = sentenceKey(field, sentence)"
                @mouseleave="hoveredSentenceKey = ''"
                @click="openTraceSentenceForField(field, sentence)"
              >
                <span v-html="renderMarkdown(sentence)" />
              </button>
            </div>
            <small>{{ field.evidenceIds.length ? `${field.evidenceIds.length} 份证据` : '暂无直接证据' }}</small>
          </article>
        </div>
      </section>

      <section class="layer-card">
        <div class="layer-head">
          <span>第二层</span>
          <h2>行为事实还原</h2>
          <p>更细地还原资金、通话、文书处置和行为方式，特别关注隐瞒、规避留痕和反侦察动作。</p>
        </div>
        <div class="timeline-list">
          <article v-for="field in behaviorFields" :key="field.key" class="fact-row">
            <div>
              <strong>{{ field.label }}</strong>
              <div class="sentence-stack">
                <button
                  v-for="sentence in traceSentences(field)"
                  :key="sentenceKey(field, sentence)"
                  class="claim-chip"
                  :class="{ hover: hoveredSentenceKey === sentenceKey(field, sentence), active: traceKey === sentenceKey(field, sentence) }"
                  @mouseenter="hoveredSentenceKey = sentenceKey(field, sentence)"
                  @mouseleave="hoveredSentenceKey = ''"
                  @click="openTraceSentenceForField(field, sentence)"
                >
                  <span v-html="renderMarkdown(sentence)" />
                </button>
              </div>
            </div>
            <span>{{ field.evidenceIds.length }} 证据</span>
          </article>
        </div>
      </section>

      <section class="layer-card">
        <div class="layer-head">
          <span>第三层</span>
          <h2>要件拆解、证据归类、缺口标红、抗辩预判</h2>
          <p>这里不只列线索，而是看每个要件现在有没有证据支撑，缺什么，对方可能怎么辩。</p>
        </div>
        <div class="element-grid">
          <article v-for="item in elementFields" :key="item.key" class="element-card" :class="{ gap: item.status === 'gap' }">
            <div>
              <strong>{{ item.label }}</strong>
              <span>{{ item.status === 'ok' ? '已有支撑' : '缺口待补强' }}</span>
            </div>
            <div class="sentence-stack compact">
              <button
                v-for="sentence in traceSentences(item)"
                :key="sentenceKey(item, sentence)"
                class="claim-chip"
                :class="{ hover: hoveredSentenceKey === sentenceKey(item, sentence), active: traceKey === sentenceKey(item, sentence) }"
                @mouseenter="hoveredSentenceKey = sentenceKey(item, sentence)"
                @mouseleave="hoveredSentenceKey = ''"
                @click="openTraceSentenceForField(item, sentence)"
              >
                <span v-html="renderMarkdown(sentence)" />
              </button>
            </div>
          </article>
        </div>
        <div class="defense-box">
          <h3>抗辩预判</h3>
          <article v-for="item in defenseFields" :key="item.key" class="defense-item">
            <span>{{ item.label }}</span>
            <div class="sentence-stack compact">
              <button
                v-for="sentence in traceSentences(item)"
                :key="sentenceKey(item, sentence)"
                class="claim-chip"
                :class="{ hover: hoveredSentenceKey === sentenceKey(item, sentence), active: traceKey === sentenceKey(item, sentence) }"
                @mouseenter="hoveredSentenceKey = sentenceKey(item, sentence)"
                @mouseleave="hoveredSentenceKey = ''"
                @click="openTraceSentenceForField(item, sentence)"
              >
                <span v-html="renderMarkdown(sentence)" />
              </button>
            </div>
          </article>
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
        <h3>当前选中</h3>
        <p class="trace-query">{{ traceQueryText || '尚未选择具体句子' }}</p>
      </div>
      <div class="trace-section">
        <h3>证据原文</h3>
        <div v-if="evidenceLoading" class="muted">正在读取证据和 HippoRAG PPR 排序...</div>
        <div v-else-if="traceEvidence.length === 0" class="muted">暂无直接证据 ID。可以到图谱页按主体和路径继续追。</div>
        <details v-for="item in traceEvidence" :key="item.evidence_id" class="evidence-doc">
          <summary>{{ item.title }}</summary>
          <pre>{{ item.content }}</pre>
        </details>
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
        <details v-else class="path-details">
          <summary>{{ tracePaths.length }} 条候选路径</summary>
          <div v-for="path in tracePaths" :key="path" class="path-line">{{ path }}</div>
        </details>
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
const traceQueryText = ref('');
const traceKey = ref('');
const hoveredSentenceKey = ref('');

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
    makeField('behavior.fund', '资金往来', relationSummary(/资金|交易|转账|收款|付款|金额|现金|取现|存入/) || '暂无明确资金链条。', ['资金', '交易', '转账', '现金']),
    makeField('behavior.duty', '职务处置', clueText('duty_behavior') || relationSummary(/立案|拘留|释放|调解|撤销|审批|执法|报告|决定/) || '暂无明确职务处置链条。', ['立案', '拘留', '释放', '调解', '撤销']),
    makeField('behavior.method', '行为方式/反侦察', behaviorModeText() || '暂未发现足够明确的隐瞒、白手套过桥、现金化处理、文书倒签或规避留痕迹象。', ['隐瞒', '现金', '取现', '代持', '马甲', '倒签']),
    ...clues.filter((clue) => !['behavior_reconstruction', 'fund_flow', 'duty_behavior'].includes(clue.category)).slice(0, 4).map(fieldFromClue),
  ];
});

const elementFields = computed<TraceField[]>(() => [
  elementAnalysisField(
    'element.subject',
    '主体要件',
    '法定要求：行为人须属于司法工作人员，且对相关案件处置具有职务权限、指派权限、审批权限或实际影响力。',
    ['杨周武', '同乐派出所', '所长', '民警', '指派', '批准人', '责任区民警', '公安', '扫雷'],
    '缺口：尚需明确任职文件、干部履历、岗位职责说明、案件审批权限或指派权限来源。',
    '建议：调取杨周武任职文件、岗位职责、分工记录、同乐派出所层级关系及相关文书审批流。'
  ),
  elementAnalysisField(
    'element.objective',
    '客观行为',
    '法定要求：存在应依法追究而不追究、违法调解、撤案、释放、降格处理、隐瞒事实或改变处置方向等枉法处置行为。',
    ['立案', '拘留', '释放', '调解', '撤销', '结案', '伤情', '鉴定', '赔偿', '刘力飚', '罗贤涛', '易承桂'],
    '缺口：尚需把案发事实、伤情结论、处置决定、调解结案、释放结果按时间线闭合。',
    '建议：按时间轴核对接警、鉴定、拘留、调解、撤案或结案、释放、后续追责材料是否互相矛盾。'
  ),
  elementAnalysisField(
    'element.subjective',
    '主观方面',
    '法定要求：需要证明明知案件事实或法律后果，仍因徇私动机故意作出枉法处置。',
    ['明知', '徇私', '请托', '王静', '何晓初', '短信', '宴请', '送钱', '27万', '3万', '现金', '转账', '好处'],
    '缺口：仍需区分普通业务判断、程序瑕疵与明知故意；资金或请托线索必须与具体处置节点建立时间和对象对应。',
    '建议：将短信、通话、银行流水、现金取存、证人证言与拘留、调解、释放、结案节点放在同一时间轴交叉验证。'
  ),
  elementAnalysisField(
    'element.result',
    '结果与因果',
    '法定要求：枉法处置造成有罪人员逃避追诉、案件被错误处理、被害人权益受损或其他严重后果，并能证明结果与职务行为存在因果关系。',
    ['逃避', '未追究', '释放', '解除', '赔偿', '11万', '结案', '火灾', '死亡', '受伤', '后果'],
    '缺口：仍需确认错误处置与未追究刑责之间的因果，而不是只证明后来发生了结果。',
    '建议：补强原案应追责标准、实际处理结果、责任人员未被追究原因及后续检察机关立案材料。'
  ),
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
  const firstSentence = traceSentences(field)[0] || field.value;
  traceKey.value = sentenceKey(field, firstSentence);
  await runTraceForText(field, firstSentence);
}

async function openTraceSentence(sentence: string) {
  if (!traceField.value) return;
  traceKey.value = sentenceKey(traceField.value, sentence);
  await runTraceForText(traceField.value, sentence);
}

async function openTraceSentenceForField(field: TraceField, sentence: string) {
  traceField.value = field;
  traceOpen.value = true;
  traceKey.value = sentenceKey(field, sentence);
  await runTraceForText(field, sentence);
}

async function runTraceForText(field: TraceField, queryText: string) {
  traceQueryText.value = queryText;
  traceEvidence.value = [];
  traceResult.value = null;
  evidenceLoading.value = true;
  try {
    traceResult.value = await backendApi.traceAnalysis(activeCaseId.value, `${field.label}\n${queryText}`, field.evidenceIds, 8);
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

function traceSentences(field: TraceField) {
  const chunks = (field.value || '')
    .split(/\n+/)
    .flatMap((line) => line.split(/(?<=[。！？；;])/))
    .map(cleanSourceSentence)
    .filter(isSourceableSentence);
  return Array.from(new Set(chunks));
}

function cleanSourceSentence(value: string) {
  return (value || '')
    .replace(/^[-*•]\s*/, '')
    .replace(/^\d+[.、]\s*/, '')
    .replace(/\*\*/g, '')
    .replace(/==/g, '')
    .replace(/^["“”'‘’]+|["“”'‘’]+$/g, '')
    .trim();
}

function isSourceableSentence(value: string) {
  const text = cleanSourceSentence(value);
  const withoutColon = text.replace(/[：:]\s*$/, '').trim();
  if (withoutColon.length < 8) return false;
  if (/^[\s*#\-•：:]+$/.test(withoutColon)) return false;
  if (/^(结论|支持证据|仍需补强|证明力|身份|任职|职权|关键人员关系|案件对象|批准人|发信人|收信人|证明事项|来源文件)$/.test(withoutColon)) return false;
  if (/^(证据|材料|相关证据)\s*\d*(?:-\d+)?$/.test(withoutColon)) return false;
  if (/^(第一层|第二层|第三层|主体要件|客观行为|主观方面|结果与因果|抗辩预判)$/.test(withoutColon)) return false;
  return true;
}

function sentenceKey(field: TraceField, sentence: string) {
  return `${field.key}::${sentence}`;
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

function elementAnalysisField(key: string, label: string, requirement: string, keywords: string[], gap: string, suggestion: string): TraceField {
  const supportLines = supportLinesForKeywords(keywords, 4);
  const evidenceIds = evidenceIdsForKeywords(keywords);
  const currentEvidence = supportLines.length ? `当前证据：${supportLines.join('；')}` : '当前证据：尚未找到高匹配证据片段。';
  const conclusion = supportLines.length
    ? `初步结论：✅ 已有材料可以作为“${label}”分析入口，但仍需人工复核证据证明力。`
    : `初步结论：⚠️ 现有材料不足以稳定支撑“${label}”。`;
  return {
    key,
    label,
    value: [requirement, currentEvidence, conclusion, gap, suggestion].join('\n'),
    evidenceIds,
    keywords,
    status: supportLines.length ? 'ok' : 'gap',
  };
}

function supportLinesForKeywords(keywords: string[], limit = 4) {
  const rows: Array<{ score: number; text: string }> = [];
  (graph.value?.clues || []).forEach((clue) => {
    const text = `${clue.title}：${clue.description}`;
    const score = keywords.filter((word) => text.includes(word)).length;
    if (score) rows.push({ score, text });
  });
  (graph.value?.edges || []).forEach((edge) => {
    const source = graph.value?.nodes.find((node) => node.node_id === edge.source_id)?.label || edge.source_id;
    const target = graph.value?.nodes.find((node) => node.node_id === edge.target_id)?.label || edge.target_id;
    const text = `${source} -> ${edge.relation} -> ${target}`;
    const score = keywords.filter((word) => text.includes(word)).length;
    if (score) rows.push({ score, text });
  });
  return rows
    .sort((a, b) => b.score - a.score)
    .map((row) => (row.text.length > 90 ? `${row.text.slice(0, 90)}...` : row.text))
    .filter((text, index, arr) => arr.indexOf(text) === index)
    .slice(0, limit);
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
  const escaped = escapeHtml(cleanMarkdownText(value || ''));
  return escaped
    .replace(/^### (.*)$/gm, '<h4>$1</h4>')
    .replace(/^## (.*)$/gm, '<h3>$1</h3>')
    .replace(/^# (.*)$/gm, '<h2>$1</h2>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/==(.+?)==/g, '<mark>$1</mark>')
    .replace(/^- (.*)$/gm, '<div class="md-list">• $1</div>')
    .replace(/\n/g, '<br />');
}

function cleanMarkdownText(value: string) {
  return value
    .replace(/^\s*[-*•]\s+/gm, '- ')
    .replace(/\*{1,2}([^*\n：:]{1,24})\*{1,2}([：:])/g, '**$1**$2')
    .trim();
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
.sentence-stack {
  display: grid;
  gap: 7px;
  margin: 8px 0;
}
.sentence-stack.compact {
  margin-bottom: 0;
}
.claim-chip {
  width: 100%;
  border: 1px solid transparent;
  border-radius: 7px;
  background: transparent;
  color: #334155;
  padding: 7px 8px;
  text-align: left;
  font-size: 14px;
  line-height: 1.65;
}
.claim-chip:hover,
.claim-chip.hover {
  border-color: #5eead4;
  background: #ecfeff;
}
.claim-chip.active {
  border-color: #0f766e;
  background: #ccfbf1;
  box-shadow: inset 3px 0 0 #0f766e;
}
.field-card:has(.claim-chip.hover),
.fact-row:has(.claim-chip.hover),
.element-card:has(.claim-chip.hover),
.defense-item:has(.claim-chip.hover) {
  border-color: #99f6e4;
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
.trace-query {
  color: #bae6fd;
  font-size: 12px;
  line-height: 1.5;
  margin-bottom: 8px;
}
.sentence-list {
  display: grid;
  gap: 7px;
  margin-bottom: 10px;
}
.sentence-button {
  width: 100%;
  border: 1px solid #334155;
  border-radius: 7px;
  background: #0f172a;
  color: #cbd5e1;
  padding: 8px 10px;
  text-align: left;
  font-size: 12px;
  line-height: 1.5;
}
.sentence-button:hover,
.sentence-button.active {
  border-color: #14b8a6;
  background: #123b3c;
  color: #ffffff;
}
.evidence-doc {
  border-top: 1px solid #23324b;
  padding-top: 10px;
  margin-top: 10px;
}
.evidence-doc summary {
  display: block;
  margin-bottom: 8px;
  cursor: pointer;
  font-weight: 900;
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
.path-details summary {
  cursor: pointer;
  color: #bae6fd;
  font-size: 13px;
  font-weight: 900;
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
