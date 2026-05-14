<template>
  <div class="portrait-page" data-testid="portrait-page">
    <section class="shell" data-testid="portrait-report">
      <header class="topbar">
        <div>
          <p class="eyebrow">证据事实画像</p>
          <h1>人物关系与行为还原</h1>
          <p class="subtext">系统从案件证据与关系图谱中召回材料，整理成可点击、可溯源的事实片段。</p>
        </div>
        <button class="primary-btn" :disabled="!activeCaseId || loading" @click="refreshFacts(true)">
          {{ loading ? '检索中...' : '重新生成事实画像' }}
        </button>
      </header>

      <div class="case-line">
        <span>当前案件</span>
        <code>{{ activeCaseId || '未选择案件' }}</code>
      </div>
      <p v-if="!activeCaseId" class="warn">请先在案件导入页创建或选择案件。</p>
      <p v-if="error" class="error">{{ error }}</p>
      <AsyncProgressBar
        v-if="progress.active.value"
        compact
        :value="progress.value.value"
        :label="progress.label.value"
        :detail="progress.detail.value"
      />

      <section class="summary-grid">
        <div class="metric">
          <span>人物关系</span>
          <strong>{{ relationshipFacts.length }}</strong>
        </div>
        <div class="metric">
          <span>行为事实</span>
          <strong>{{ behaviorFacts.length }}</strong>
        </div>
        <div class="metric">
          <span>检索问题</span>
          <strong>{{ facts?.queries.length || 0 }}</strong>
        </div>
        <div class="metric">
          <span>检索调用</span>
          <strong>{{ facts?.tool_calls.length || 0 }}</strong>
        </div>
      </section>

      <details v-if="facts?.retrieval_session_id" class="retrieval-details" data-testid="retrieval-session" @toggle="onRetrievalToggle(facts.retrieval_session_id, $event)">
        <summary>检索与调用细节</summary>
        <div v-if="retrievalLoading" class="muted">正在读取检索记录...</div>
        <div v-else-if="retrievalDetail" class="retrieval-body">
          <div class="retrieval-meta">
            <span>检索规划</span>
            <span>答案生成</span>
            <span>{{ retrievalDetail.session.status }}</span>
          </div>
          <section v-for="step in retrievalDetail.steps" :key="step.step_id" class="retrieval-step">
            <h4>第 {{ step.round_index }} 轮</h4>
            <p v-if="step.retrieval_goals.length"><strong>目标：</strong>{{ step.retrieval_goals.join('；') }}</p>
            <p v-if="step.coverage_summary"><strong>覆盖：</strong>{{ step.coverage_summary }}</p>
            <p v-if="step.unresolved_gaps.length"><strong>缺口：</strong>{{ step.unresolved_gaps.join('；') }}</p>
            <article v-for="call in step.tool_calls" :key="call.tool_call_id" class="tool-call">
              <div class="tool-call-head">
                <strong>{{ toolLabel(call.tool_name) }}</strong>
                <code>{{ formatArgs(call.arguments) }}</code>
              </div>
              <p>{{ call.summary || '无摘要' }}</p>
              <p v-if="call.errors.length" class="error tiny">错误：{{ call.errors.join('；') }}</p>
              <div v-if="call.graph_facts.length" class="tool-block">
                <b>图谱关系</b>
                <ul>
                  <li v-for="fact in call.graph_facts.slice(0, 8)" :key="fact">{{ fact }}</li>
                </ul>
              </div>
              <div v-if="call.passages.length" class="tool-block">
                <b>证据片段</b>
                <ul>
                  <li v-for="passage in call.passages.slice(0, 5)" :key="`${passage.rank}-${passage.passage}`">
                    证据 {{ passage.rank }}：{{ passage.evidence_title || passage.evidence_id || '未映射证据' }} - {{ compactText(passage.passage, 110) }}
                  </li>
                </ul>
              </div>
              <div v-if="call.legal_passages.length" class="tool-block">
                <b>法律知识</b>
                <ul>
                  <li v-for="passage in call.legal_passages.slice(0, 4)" :key="`${passage.rank}-${passage.passage}`">
                    {{ passage.evidence_title || '法律知识' }} - {{ compactText(passage.passage, 100) }}
                  </li>
                </ul>
              </div>
              <div v-if="call.rule_findings.length" class="tool-block">
                <b>规则命中</b>
                <ul>
                  <li v-for="finding in call.rule_findings" :key="finding.finding_id">
                    {{ finding.title }}（{{ finding.severity }}）：{{ compactText(finding.reason, 110) }}
                  </li>
                </ul>
              </div>
              <div v-if="call.document_groups.length" class="tool-block">
                <b>文件聚合</b>
                <ul>
                  <li v-for="group in call.document_groups.slice(0, 8)" :key="String(group.doc_id || group.name || group.title)">
                    {{ group.doc_id || group.name || '文件' }}：{{ group.process_stage || group.title || '' }} {{ compactText(String(group.proof_purpose || group.document_summary || group.description || ''), 100) }}
                  </li>
                </ul>
              </div>
            </article>
          </section>
        </div>
      </details>

      <section class="fact-section">
        <div class="section-head">
          <div>
            <h2>规则命中</h2>
            <p>规则包只输出 finding、材料缺口和核查建议，不做犯罪定性。</p>
          </div>
          <button class="secondary" :disabled="loading || !activeCaseId" @click="runDefaultRules">运行默认规则</button>
        </div>
        <div v-if="ruleRuns.length">
          <article v-for="run in ruleRuns" :key="`${run.rule_pack}-${run.created_at}`" class="rule-run">
            <h3>{{ run.rule_pack }}：{{ run.findings.length }} 条 finding</h3>
            <div v-for="finding in run.findings" :key="finding.finding_id" class="finding-card" @click="selectedFinding = finding">
              <strong>{{ finding.title }}</strong>
              <span>{{ finding.severity }} / {{ finding.evidence_level }}</span>
              <p>{{ finding.reason }}</p>
              <small v-if="finding.missing_documents.length">缺失/待核查：{{ finding.missing_documents.join('、') }}</small>
            </div>
            <details v-if="!run.findings.length || run.not_triggered.length || run.data_gaps.length" class="not-triggered">
              <summary>未命中原因 / 数据缺口</summary>
              <p v-for="item in run.not_triggered" :key="item.rule_id">{{ item.rule_id }}：{{ item.reason }}</p>
              <p v-for="gap in run.data_gaps" :key="gap">数据缺口：{{ gap }}</p>
            </details>
          </article>
        </div>
        <div v-else class="empty-box">暂无规则运行结果。点击“运行默认规则”。</div>
      </section>

      <section class="fact-section">
        <div class="section-head">
          <div>
            <h2>人物关系</h2>
            <p>系统基于证据片段和图谱关系整理成人物关系文段。点击依据句可查看证据来源。</p>
          </div>
        </div>
        <div v-if="facts?.relationship_narrative" class="narrative-card" @mouseup="openSelectionTrace('relationship')">
          <p v-for="(paragraph, pIndex) in narrativeSentenceParagraphs(facts.relationship_narrative, relationshipFacts)" :key="pIndex">
            <button
              v-for="(sentence, sIndex) in paragraph"
              :key="`${pIndex}-${sIndex}`"
              :class="['narrative-sentence', { sourceable: sentence.fact }]"
              data-testid="evidence-citation"
              @click="openSentenceTrace(sentence)"
            >
              {{ sentence.text }}
            </button>
          </p>
          <p v-if="facts?.tool_call_summary || facts?.tool_call_note" class="tool-note">{{ facts.tool_call_summary || facts.tool_call_note }}</p>
        </div>
        <div v-else class="empty-box">暂无关系事实。点击“生成事实画像”后查看证据检索结果。</div>
      </section>

      <section class="fact-section">
        <div class="section-head">
          <div>
            <h2>行为还原</h2>
            <p>先用文段还原关键动作，之后再把复杂反侦察和异常资金作为深挖专题。</p>
          </div>
        </div>
        <div v-if="facts?.behavior_narrative" class="narrative-card" @mouseup="openSelectionTrace('behavior')">
          <p v-for="(paragraph, pIndex) in narrativeSentenceParagraphs(facts.behavior_narrative, behaviorFacts)" :key="pIndex">
            <button
              v-for="(sentence, sIndex) in paragraph"
              :key="`${pIndex}-${sIndex}`"
              :class="['narrative-sentence', { sourceable: sentence.fact }]"
              data-testid="evidence-citation"
              @click="openSentenceTrace(sentence)"
            >
              {{ sentence.text }}
            </button>
          </p>
          <p v-if="facts?.tool_call_summary || facts?.tool_call_note" class="tool-note">{{ facts.tool_call_summary || facts.tool_call_note }}</p>
        </div>
        <div v-else class="empty-box">暂无行为事实。若这里很少，说明证据召回或片段切分还要继续调。</div>
      </section>

      <section class="deferred-section">
        <h2>暂缓深挖</h2>
        <p>反侦察、异常资金、主观明知仍然重要，但先不在本页混入推理。事实链稳定后，再进入智能分析页。</p>
      </section>

      <section class="suspicion-section">
        <div class="section-head">
          <div>
            <h2>疑点画像</h2>
            <p>这里显示检察官在智能分析页采纳的疑点候选。它们是待核查方向，不等同于事实结论。</p>
          </div>
          <router-link to="/intelligence">进入智能分析</router-link>
        </div>
        <div v-if="adoptedSuspicion.length === 0" class="empty-box">暂无采纳疑点。</div>
        <article v-for="item in adoptedSuspicion" :key="item.candidate_id" class="suspicion-item">
          <div>
            <strong>{{ item.title }}</strong>
            <span>{{ suspicionCategoryLabel(item.category) }} / {{ item.risk_level }} / {{ Math.round(item.confidence * 100) }}%</span>
          </div>
          <p>{{ item.explanation }}</p>
          <ul v-if="item.gaps.length">
            <li v-for="gap in item.gaps.slice(0, 3)" :key="gap">缺口：{{ gap }}</li>
          </ul>
        </article>
      </section>
    </section>

    <aside v-if="traceOpen" class="trace-panel" data-testid="provenance-modal">
      <div class="trace-head">
        <div>
          <p class="eyebrow">证据溯源</p>
          <h2>{{ selectedFact?.subject }} {{ selectedFact?.relation }} {{ selectedFact?.object }}</h2>
        </div>
        <button @click="traceOpen = false">关闭</button>
      </div>

      <section class="trace-block">
        <h3>当前事实</h3>
        <p>{{ selectedFact?.text }}</p>
      </section>

      <section class="trace-block">
        <h3>关联证据片段</h3>
        <article v-for="item in selectedFact?.passages || []" :key="`${item.rank}-${item.evidence_id}-${item.score}`" class="passage">
          <div>
            <strong>证据片段 {{ item.rank }}</strong>
            <span>{{ item.evidence_title || item.evidence_id || '未知证据' }}</span>
          </div>
          <p>{{ compactText(item.passage) }}</p>
        </article>
        <p v-if="!selectedFact?.passages.length" class="muted">这条来自图谱补充，暂未直接绑定检索片段。</p>
      </section>

      <section class="trace-block">
        <h3>证据原文</h3>
        <div v-if="traceLoading" class="muted">正在读取证据原文...</div>
        <details v-for="item in traceEvidence" :key="item.evidence_id" class="evidence-doc">
          <summary>{{ item.title }}</summary>
          <pre>{{ item.content }}</pre>
        </details>
        <p v-if="!traceLoading && !traceEvidence.length" class="muted">暂无直接证据原文。</p>
      </section>
    </aside>

    <aside v-if="selectedMotherNode || selectedFinding" class="trace-panel">
      <div class="trace-head">
        <div>
          <p class="eyebrow">{{ selectedFinding ? '规则 Finding' : '文件节点' }}</p>
          <h2>{{ selectedFinding?.title || selectedMotherNode?.title }}</h2>
        </div>
        <button @click="selectedMotherNode = null; selectedFinding = null">关闭</button>
      </div>
      <template v-if="selectedMotherNode">
        <section class="trace-block">
          <h3>证明事项</h3>
          <p>{{ selectedMotherNode.proof_purpose }}</p>
        </section>
        <section class="trace-block">
          <h3>Verified Claims</h3>
          <article v-for="claim in selectedMotherNode.key_claims.filter((item) => item.status === 'verified')" :key="claim.claim_id" class="passage">
            <strong>{{ claim.claim_type }}</strong>
            <p>{{ claim.claim }}</p>
          </article>
          <p v-if="!selectedMotherNode.key_claims.some((item) => item.status === 'verified')" class="muted">暂无 verified claim。</p>
        </section>
      </template>
      <template v-if="selectedFinding">
        <section class="trace-block">
          <h3>规则依据</h3>
          <p>{{ selectedFinding.reason }}</p>
          <p>{{ selectedFinding.legal_caution }}</p>
        </section>
        <section class="trace-block">
          <h3>支撑文件 / Verified Claims</h3>
          <p>{{ selectedFinding.supporting_documents.join('、') || '暂无' }}</p>
          <article v-for="claim in selectedFinding.supporting_claims" :key="claim.claim_id" class="passage">
            <strong>{{ claim.claim_type }}</strong>
            <p>{{ claim.claim }}</p>
          </article>
        </section>
        <section class="trace-block">
          <h3>缺失材料与建议</h3>
          <p v-if="selectedFinding.missing_documents.length">缺失/待核查：{{ selectedFinding.missing_documents.join('、') }}</p>
          <ul>
            <li v-for="action in selectedFinding.next_actions" :key="action">{{ action }}</li>
          </ul>
          <details>
            <summary>debug trace</summary>
            <pre>{{ selectedFinding.debug_trace.join('\n') }}</pre>
          </details>
        </section>
      </template>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { backendApi, type DocumentMotherGraph, type DocumentMotherNode, type EvidenceDetail, type PortraitFact, type PortraitFactsResult, type RetrievalSessionDetail, type RuleFinding, type RulePackRunResult, type SuspicionCandidate } from '../api/backend';
import AsyncProgressBar from '../components/AsyncProgressBar.vue';
import { useSimulatedProgress } from '../composables/useSimulatedProgress';

const activeCaseId = ref(localStorage.getItem('active_case_id') || '');
const facts = ref<PortraitFactsResult | null>(null);
const loading = ref(false);
const error = ref('');
const progress = useSimulatedProgress();
const traceOpen = ref(false);
const traceLoading = ref(false);
const selectedFact = ref<PortraitFact | null>(null);
const traceEvidence = ref<EvidenceDetail[]>([]);
const adoptedSuspicion = ref<SuspicionCandidate[]>([]);
const retrievalDetail = ref<RetrievalSessionDetail | null>(null);
const retrievalLoading = ref(false);
const documentMother = ref<DocumentMotherGraph>({ case_id: '', nodes: [], rebuilt_count: 0, warnings: [] });
const ruleRuns = ref<RulePackRunResult[]>([]);
const selectedMotherNode = ref<DocumentMotherNode | null>(null);
const selectedFinding = ref<RuleFinding | null>(null);

const relationshipFacts = computed(() => facts.value?.relationship_facts || []);
const behaviorFacts = computed(() => facts.value?.behavior_facts || []);

onMounted(() => {
  adoptedSuspicion.value = readAdoptedSuspicion();
  if (activeCaseId.value) {
    refreshFacts(false);
    loadMotherGraph();
  }
});

async function refreshFacts(force = false) {
  if (!activeCaseId.value) return;
  loading.value = true;
  error.value = '';
  progress.start({
    label: '正在检索事实',
    detail: '多角度查询人物关系、请托、指派、调解、释放和资金事实。',
  });
  try {
    facts.value = await backendApi.getPortraitFacts(activeCaseId.value, force);
    retrievalDetail.value = null;
    if (facts.value.error) error.value = facts.value.error;
    await progress.finish({
      label: '事实画像已生成',
      detail: '人物关系和行为还原来自证据检索结果。',
    });
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
    progress.fail();
  } finally {
    loading.value = false;
  }
}

async function loadMotherGraph() {
  if (!activeCaseId.value) return;
  try {
    documentMother.value = await backendApi.getDocumentMotherGraph(activeCaseId.value);
  } catch {
    documentMother.value = { case_id: activeCaseId.value, nodes: [], rebuilt_count: 0, warnings: [] };
  }
}

async function rebuildMotherGraph() {
  loading.value = true;
  error.value = '';
  try {
    documentMother.value = await backendApi.rebuildDocumentMotherGraph(activeCaseId.value);
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    loading.value = false;
  }
}

async function runDefaultRules() {
  loading.value = true;
  error.value = '';
  try {
    if (!documentMother.value.nodes.length) {
      await rebuildMotherGraph();
    }
    const names = ['document_completeness', 'process_turning_point', 'authority_control'];
    ruleRuns.value = [];
    for (const name of names) {
      ruleRuns.value.push(await backendApi.runRulePack(activeCaseId.value, name));
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    loading.value = false;
  }
}

function openMotherNode(node: DocumentMotherNode) {
  selectedMotherNode.value = node;
  selectedFinding.value = null;
}

async function onRetrievalToggle(sessionId: string | null | undefined, event: Event) {
  const target = event.target as HTMLDetailsElement;
  if (!target.open || !sessionId || retrievalDetail.value || retrievalLoading.value) return;
  retrievalLoading.value = true;
  try {
    retrievalDetail.value = await backendApi.getRetrievalSession(activeCaseId.value, sessionId);
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    retrievalLoading.value = false;
  }
}

async function openFact(fact: PortraitFact) {
  if (!activeCaseId.value) return;
  selectedFact.value = fact;
  traceOpen.value = true;
  traceLoading.value = true;
  traceEvidence.value = [];
  try {
    const ids = new Set<string>();
    fact.evidence_ids.forEach((id) => ids.add(id));
    fact.passages.forEach((item) => {
      if (item.evidence_id) ids.add(item.evidence_id);
    });
    traceEvidence.value = await Promise.all([...ids].slice(0, 5).map((id) => backendApi.getEvidenceDetail(activeCaseId.value, id)));
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    traceLoading.value = false;
  }
}

interface NarrativeSentence {
  text: string;
  fact: PortraitFact | null;
}

function narrativeSentenceParagraphs(value: string, candidates: PortraitFact[]): NarrativeSentence[][] {
  return String(value || '')
    .split(/\n+/)
    .map((paragraph) =>
      splitSentences(paragraph)
        .map((text) => ({ text, fact: bestFactForText(text, candidates) }))
        .filter((item) => item.text),
    )
    .filter((paragraph) => paragraph.length);
}

function splitSentences(value: string) {
  return String(value || '')
    .replace(/\s+/g, ' ')
    .match(/[^。！？；;]+[。！？；;]?/g)?.map((item) => item.trim()).filter(Boolean) || [];
}

function openSentenceTrace(sentence: NarrativeSentence) {
  if (sentence.fact) openFact(sentence.fact);
}

function openSelectionTrace(kind: 'relationship' | 'behavior') {
  window.setTimeout(() => {
    const selected = window.getSelection()?.toString().trim() || '';
    if (selected.length < 4) return;
    const fact = bestFactForText(selected, kind === 'relationship' ? relationshipFacts.value : behaviorFacts.value);
    if (fact) openFact(fact);
  }, 0);
}

function bestFactForText(text: string, candidates: PortraitFact[]) {
  const terms = keyTerms(text);
  if (!terms.length) return null;
  let best: PortraitFact | null = null;
  let bestScore = 0;
  candidates.forEach((fact) => {
    const haystack = `${fact.subject} ${fact.relation} ${fact.object} ${fact.text}`;
    const score = terms.reduce((sum, term) => sum + (haystack.includes(term) ? Math.min(term.length, 6) : 0), 0);
    if (score > bestScore) {
      bestScore = score;
      best = fact;
    }
  });
  return bestScore >= 4 ? best : null;
}

function keyTerms(text: string) {
  const raw = String(text || '');
  const names = ['杨周武', '王静', '何晓初', '刘力飚', '罗贤涛', '易承桂', '江军', '汪春蓉', '赵志高', '张夏天', '陈三一', '罗宇', '同乐派出所', '舞王俱乐部'];
  const verbs = ['请托', '收受', '指派', '安排', '介入', '调解', '释放', '拘留', '立案', '侦查', '转账', '通话', '赔偿', '批准', '承诺', '负责', '隐患', '取现', '存入'];
  return [...names, ...verbs, ...(raw.match(/\d+(?:\.\d+)?万?元/g) || []), ...(raw.match(/20\d{2}年\d{1,2}月\d{1,2}日/g) || [])].filter((term) => raw.includes(term));
}

function compactText(value: string, limit = 280) {
  const text = String(value || '').replace(/\s+/g, ' ').trim();
  if (text.split(',').length >= 6) {
    return text
      .split(',')
      .map((part) => part.trim())
      .filter((part) => /[\u4e00-\u9fa5]/.test(part))
      .slice(0, 10)
      .join(' / ');
  }
  return text.length > limit ? `${text.slice(0, limit)}...` : text;
}

function toolLabel(name: string) {
  const labels: Record<string, string> = {
    search_documents: '文档检索',
    search_graph: '图谱检索',
    expand_node: '节点扩展',
    search_time_range: '时间检索',
    search_legal: '法律知识',
  };
  return labels[name] || name;
}

function formatArgs(args: Record<string, unknown>) {
  const text = JSON.stringify(args || {}, null, 0);
  return text.length > 160 ? `${text.slice(0, 160)}...` : text;
}

function sourceLabel(source: string) {
  if (source === 'deepseek') return '模型生成';
  if (source === 'hipporag') return '证据召回';
  return '图谱补充';
}

function readAdoptedSuspicion() {
  try {
    return JSON.parse(localStorage.getItem(`adopted_suspicion:${activeCaseId.value}`) || '[]') as SuspicionCandidate[];
  } catch {
    return [];
  }
}

function suspicionCategoryLabel(category: string) {
  return {
    cross_case: '跨案件碰撞',
    hypothesis: '假设验证',
    financial_flow: '可疑资金流',
  }[category] || category;
}
</script>

<style scoped>
.portrait-page {
  min-height: 100%;
  overflow: auto;
  background: #eef3f7;
  color: #0f172a;
  padding: 24px;
}

.shell {
  max-width: 1120px;
  margin: 0 auto;
  display: grid;
  gap: 16px;
}

.topbar,
.fact-section,
.deferred-section,
.suspicion-section,
.metric {
  border: 1px solid #d8e1ea;
  border-radius: 10px;
  background: #ffffff;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 18px;
}

.eyebrow {
  color: #0f766e;
  font-size: 13px;
  font-weight: 900;
}

h1,
h2,
h3 {
  color: #0f172a;
  font-weight: 900;
}

h1 {
  margin-top: 4px;
  font-size: 24px;
}

h2 {
  font-size: 19px;
}

h3 {
  font-size: 15px;
}

.subtext,
.section-head p,
.deferred-section p,
.suspicion-section p,
.case-line,
.muted {
  color: #64748b;
  font-size: 14px;
}

.primary-btn {
  min-width: 148px;
  border-radius: 8px;
  background: #0f766e;
  color: #ffffff;
  padding: 10px 16px;
  font-weight: 900;
}

.primary-btn:disabled {
  opacity: 0.55;
}

.case-line {
  display: flex;
  gap: 10px;
  align-items: center;
}

.case-line code {
  color: #334155;
}

.warn,
.error {
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 14px;
}

.warn {
  border: 1px solid #fde68a;
  background: #fffbeb;
  color: #92400e;
}

.error,
.trace-error {
  border: 1px solid #fecdd3;
  background: #fff1f2;
  color: #be123c;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.metric {
  padding: 14px;
}

.metric span {
  display: block;
  color: #64748b;
  font-size: 13px;
}

.metric strong {
  margin-top: 5px;
  display: block;
  font-size: 24px;
  color: #0f766e;
}

.tool-note {
  margin-top: 10px;
  color: #64748b;
  font-size: 13px;
  font-weight: 700;
}

.retrieval-details {
  border: 1px solid #dbeafe;
  border-radius: 12px;
  background: #f8fafc;
  padding: 12px 14px;
}

.retrieval-details summary {
  cursor: pointer;
  font-weight: 900;
  color: #0f766e;
}

.retrieval-body {
  margin-top: 10px;
  display: grid;
  gap: 12px;
}

.retrieval-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.retrieval-meta span {
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  padding: 4px 8px;
  background: #fff;
  color: #475569;
  font-size: 12px;
  font-weight: 800;
}

.retrieval-step {
  border-top: 1px solid #e2e8f0;
  padding-top: 10px;
}

.retrieval-step h4 {
  margin: 0 0 6px;
}

.tool-call {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
  padding: 10px;
  margin-top: 8px;
}

.tool-call-head {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 8px;
  align-items: start;
}

.tool-call-head code {
  overflow-wrap: anywhere;
  color: #475569;
}

.tool-block {
  margin-top: 8px;
}

.tool-block ul {
  margin: 6px 0 0;
  padding-left: 18px;
}

.tool-block li {
  margin-bottom: 4px;
}

.tiny {
  font-size: 12px;
}

.fact-section,
.suspicion-section {
  padding: 18px;
}

.doc-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
}

.doc-card,
.finding-card {
  width: 100%;
  display: grid;
  gap: 6px;
  text-align: left;
  border: 1px solid #dbe3ee;
  border-radius: 12px;
  background: #f8fafc;
  padding: 12px;
  color: #0f172a;
  cursor: pointer;
}

.doc-card span,
.finding-card span,
.doc-card small,
.finding-card small {
  color: #64748b;
}

.rule-run {
  border: 1px solid #dbe3ee;
  border-radius: 12px;
  padding: 12px;
  margin-top: 10px;
  background: #fff;
}

.rule-run h3 {
  margin-bottom: 10px;
}

.finding-card {
  margin-top: 8px;
  border-color: #fbbf24;
  background: #fffbeb;
}

.not-triggered {
  margin-top: 10px;
  color: #475569;
}

.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 14px;
}

.section-head a {
  color: #0f766e;
  font-weight: 900;
  white-space: nowrap;
}

.suspicion-item {
  border-top: 1px solid #e2e8f0;
  padding: 12px 0;
}

.suspicion-item:first-of-type {
  border-top: 0;
}

.suspicion-item > div {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.suspicion-item strong {
  font-weight: 900;
}

.suspicion-item span {
  color: #0f766e;
  font-size: 12px;
  font-weight: 900;
  white-space: nowrap;
}

.suspicion-item li {
  margin-top: 6px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.narrative-card {
  border: 1px solid #d8e1ea;
  border-radius: 10px;
  background: #fbfdff;
  padding: 16px;
}

.narrative-card p {
  color: #243047;
  font-size: 15px;
  line-height: 1.9;
  margin: 0;
}

.narrative-card p + p {
  margin-top: 12px;
}

.narrative-sentence {
  display: inline;
  border-radius: 5px;
  color: inherit;
  line-height: inherit;
  text-align: left;
}

.narrative-sentence.sourceable {
  cursor: pointer;
  text-decoration: underline;
  text-decoration-color: rgba(15, 118, 110, 0.25);
  text-decoration-thickness: 2px;
  text-underline-offset: 4px;
}

.narrative-sentence.sourceable:hover {
  background: #ccfbf1;
  color: #0f766e;
}

.relation-groups {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.relation-group {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fbfdff;
  padding: 12px;
}

.relation-group h3 {
  margin-bottom: 10px;
  color: #0f766e;
}

.relation-card {
  width: 100%;
  display: grid;
  gap: 7px;
  border-top: 1px solid #e2e8f0;
  padding: 10px 0;
  color: #0f172a;
  text-align: left;
}

.relation-card:first-of-type {
  border-top: 0;
}

.relation-card:hover .relation-line {
  color: #0f766e;
}

.relation-line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: 15px;
}

.relation-line em {
  border-radius: 999px;
  background: #ccfbf1;
  color: #0f766e;
  padding: 2px 9px;
  font-size: 12px;
  font-style: normal;
  font-weight: 900;
}

.fact-note {
  color: #475569;
  font-size: 13px;
  line-height: 1.65;
}

.fact-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: #64748b;
  font-size: 12px;
}

.timeline {
  display: grid;
  gap: 9px;
  list-style: none;
  padding: 0;
  margin: 0;
}

.timeline-item {
  width: 100%;
  display: grid;
  grid-template-columns: 34px 1fr auto;
  align-items: start;
  gap: 10px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fafc;
  color: #0f172a;
  padding: 12px;
  text-align: left;
}

.timeline-item:hover {
  border-color: #0f766e;
  background: #f0fdfa;
}

.index {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 999px;
  background: #ccfbf1;
  color: #0f766e;
  font-weight: 900;
}

.timeline-body {
  display: grid;
  gap: 5px;
}

.timeline-title {
  font-weight: 900;
  line-height: 1.55;
}

.timeline-detail {
  color: #475569;
  font-size: 13px;
  line-height: 1.65;
}

.time {
  margin-right: 8px;
  color: #b45309;
  font-weight: 900;
}

.evidence-count {
  color: #64748b;
  font-size: 12px;
  white-space: nowrap;
}

.empty-box {
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  color: #64748b;
  padding: 18px;
  text-align: center;
}

.deferred-section {
  padding: 16px 18px;
}

.trace-panel {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  z-index: 20;
  width: min(440px, 92vw);
  overflow: auto;
  border-left: 1px solid #23324b;
  background: #0f172a;
  color: #ffffff;
  padding: 16px;
  box-shadow: -16px 0 40px rgba(15, 23, 42, 0.22);
}

.trace-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 14px;
}

.trace-head h2 {
  color: #ffffff;
  font-size: 18px;
}

.trace-head button {
  align-self: start;
  border: 1px solid #334155;
  border-radius: 7px;
  padding: 6px 10px;
}

.trace-block {
  border: 1px solid #23324b;
  border-radius: 9px;
  background: #111c31;
  padding: 13px;
  margin-bottom: 12px;
}

.trace-block h3 {
  color: #ffffff;
  margin-bottom: 8px;
}

.trace-block p,
.passage p,
.evidence-doc pre {
  color: #cbd5e1;
  font-size: 13px;
  line-height: 1.65;
}

.passage,
.evidence-doc {
  border-top: 1px solid #23324b;
  padding-top: 10px;
  margin-top: 10px;
}

.passage div {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.passage span {
  color: #7dd3fc;
  font-size: 12px;
  text-align: right;
}

.evidence-doc summary {
  cursor: pointer;
  font-weight: 900;
}

.evidence-doc pre {
  max-height: 300px;
  overflow: auto;
  white-space: pre-wrap;
}

@media (max-width: 860px) {
  .topbar {
    align-items: stretch;
    flex-direction: column;
  }

  .summary-grid,
  .relation-groups {
    grid-template-columns: 1fr;
  }

  .timeline-item {
    grid-template-columns: 34px 1fr;
  }

  .evidence-count {
    grid-column: 2;
  }
}
</style>
