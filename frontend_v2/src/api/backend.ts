const configuredBackendUrl = String(import.meta.env.VITE_BACKEND_URL || '').replace(/\/$/, '');
const API_BASE = configuredBackendUrl && !configuredBackendUrl.includes('127.0.0.1') && !configuredBackendUrl.includes('localhost')
  ? configuredBackendUrl
  : '';

export interface CaseSummary {
  case_id: string;
  title: string;
  name?: string;
  status?: string;
  created_at?: string;
  updated_at?: string;
  legal_basis?: string;
  offense_id?: string;
  evidence_count?: number;
  memory_count?: number;
}

export interface OffenseTemplateSummary {
  offense_id: string;
  name: string;
}

export interface OverviewEvidence {
  evidence_id: string;
  name: string;
  brief?: string;
  evidence_type?: string;
  proof_item?: string;
  status?: string;
  created_at?: string;
  updated_at?: string;
  passage_count?: number;
}

export interface CaseOverview {
  case_id: string;
  name: string;
  case_number?: string;
  suspects?: string[];
  offense?: string;
  case_type?: string;
  stage?: string;
  created_at?: string;
  updated_at?: string;
  stats: Record<string, number>;
  next_step?: { label: string; reason: string; target?: string };
  recent_evidence: OverviewEvidence[];
}

export interface EvidenceRecord extends OverviewEvidence {
  title?: string;
  source_type?: string;
  metadata?: Record<string, unknown>;
}

export interface EvidenceDetail extends EvidenceRecord {
  case_id: string;
  content?: string;
  passages?: Array<{ passage_id: string; text: string; summary?: string; index?: number }>;
  triples?: Array<{ triple_id: string; subject: string; predicate: string; object: string; source_passage_id?: string }>;
}

export interface TracePassage {
  rank: number;
  score: number;
  passage: string;
  evidence_id?: string | null;
  evidence_title?: string | null;
}

export interface TracePath {
  source: string;
  relation: string;
  target: string;
  score: number;
  evidence_ids: string[];
}

export interface TraceResult {
  case_id: string;
  query: string;
  provider: string;
  passages: TracePassage[];
  paths: TracePath[];
  error?: string | null;
}

export interface GroundedSentence {
  sentence_id: string;
  text: string;
  start: number;
  end: number;
  status: string;
  supporting_passages: TracePassage[];
  supporting_graph_paths: TracePath[];
  confidence: number;
}

export interface AnalysisThread {
  thread_id: string;
  case_id: string;
  mode: 'hypothesis' | 'financial_flow';
  title: string;
  summary: string;
  status: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface AnalysisMessage {
  message_id: string;
  thread_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  claims: GroundedSentence[];
  retrievals: TracePassage[];
  graph_context: string[];
  legal_context: TracePassage[];
  mentioned_evidence_ids: string[];
  tool_call_summary: string;
  retrieval_session_id?: string | null;
  retrieval_steps_count: number;
  error?: string | null;
}

export interface AnalysisThreadDetail {
  thread: AnalysisThread;
  messages: AnalysisMessage[];
}

export interface PortraitFact {
  fact_id: string;
  category: string;
  group: string;
  subject: string;
  relation: string;
  object: string;
  text: string;
  time?: string | null;
  evidence_ids: string[];
  passages: TracePassage[];
  confidence: number;
  source: string;
}

export interface RagToolCall {
  name: string;
  query: string;
  mode: string;
  top_k: number;
  returned: number;
  note?: string | null;
}

export interface PortraitFactsResult {
  case_id: string;
  provider: string;
  relationship_narrative: string;
  behavior_narrative: string;
  relationship_facts: PortraitFact[];
  behavior_facts: PortraitFact[];
  queries: string[];
  tool_calls: RagToolCall[];
  tool_call_note: string;
  tool_call_summary: string;
  retrieval_session_id?: string | null;
  retrieval_steps_count: number;
  error?: string | null;
}

export interface SuspicionCandidate {
  candidate_id: string;
  title: string;
  category: string;
  method: string;
  risk_level: string;
  status: string;
  confidence: number;
  explanation: string;
  support_paths: string[];
  evidence_ids: string[];
  supporting_passages: TracePassage[];
  gaps: string[];
  suggestions: string[];
  gnn_note?: string | null;
}

export interface DocumentClaim {
  claim_id: string;
  claim: string;
  claim_type: string;
  supporting_passage_refs: Array<{ passage_index: number; evidence_id?: string | null; text: string }>;
  confidence: number;
  status: 'verified' | 'unverified_claim' | 'rejected';
}

export interface DocumentMotherNode {
  doc_id: string;
  evidence_id: string;
  title: string;
  doc_type: string;
  process_stage: string;
  formation_time?: string | null;
  event_time?: string | null;
  source_quality: string;
  summary: string;
  proof_purpose: string;
  key_claims: DocumentClaim[];
  key_entities: string[];
  risk_tags: string[];
  quality_status: string;
  warnings: string[];
}

export interface DocumentMotherGraph {
  case_id: string;
  nodes: DocumentMotherNode[];
  rebuilt_count: number;
  warnings: string[];
}

export interface RuleFinding {
  finding_id: string;
  skill_name: string;
  rule_id: string;
  finding_type: string;
  severity: string;
  title: string;
  reason: string;
  supporting_documents: string[];
  supporting_claims: DocumentClaim[];
  missing_documents: string[];
  process_stage?: string | null;
  next_actions: string[];
  legal_caution: string;
  confidence: number;
  evidence_level: string;
  data_completeness: string;
  related_hypotheses: string[];
  debug_trace: string[];
  created_from: string;
  status: string;
}

export interface RulePackRunResult {
  case_id: string;
  rule_pack: string;
  status: string;
  findings: RuleFinding[];
  not_triggered: Array<{ rule_id: string; reason: string }>;
  data_gaps: string[];
  created_at: string;
}

export interface RetrievalToolCall {
  tool_call_id: string;
  tool_name: string;
  arguments: Record<string, string | number | boolean | string[] | null>;
  summary: string;
  passages: TracePassage[];
  graph_facts: string[];
  legal_passages: TracePassage[];
  rule_findings: RuleFinding[];
  document_groups: Array<Record<string, unknown>>;
  new_entities: string[];
  errors: string[];
}

export interface RetrievalStep {
  step_id: string;
  session_id: string;
  round_index: number;
  retrieval_goals: string[];
  tool_calls: RetrievalToolCall[];
  coverage_summary: string;
  unresolved_gaps: string[];
  ready_to_answer: boolean;
  created_at: string;
}

export interface RetrievalSession {
  session_id: string;
  case_id: string;
  mode: string;
  question: string;
  status: string;
  planner_model: string;
  analysis_model: string;
  tool_call_summary: string;
  retrieval_steps_count: number;
  created_at: string;
  updated_at: string;
  error?: string | null;
}

export interface RetrievalSessionDetail {
  session: RetrievalSession;
  steps: RetrievalStep[];
}

export interface GraphNode {
  id: string;
  label: string;
  type?: string;
  layer?: string;
  summary?: string;
  properties?: Record<string, unknown>;
  source?: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type?: string;
  label?: string;
  properties?: Record<string, unknown>;
  source_refs?: unknown[];
}

export interface LegendItem {
  type: string;
  label: string;
  description?: string;
}

export interface EvidenceLayer {
  label: string;
  editable: boolean;
  nodes: GraphNode[];
  edges: GraphEdge[];
  legend: { node_types: LegendItem[]; edge_types: LegendItem[] };
  stats: { nodes: number; edges: number };
}

export interface EvidenceMap {
  case_id?: string;
  layers?: Record<'document' | 'passage' | 'raw', EvidenceLayer>;
  stats?: Record<string, number>;
  documents?: unknown[];
  passages?: unknown[];
  triples?: unknown[];
}

export interface RulePackSummary {
  name: string;
  title?: string;
  description?: string;
  version?: string;
  enabled?: boolean;
  case_types?: string[];
  task_types?: string[];
  rules_count?: number;
  findings_count?: number;
  last_run_at?: string;
}

export interface RulePackDetail extends RulePackSummary {
  skill_md?: string;
  manifest?: unknown;
  checks?: unknown;
  finding_templates?: unknown;
  examples?: unknown;
  test_cases?: unknown;
}

export interface LegalKnowledgeIndex {
  sections: Array<{ title: string; description?: string; items: Array<Record<string, unknown> | string> }>;
  offenses?: OffenseTemplateSummary[];
  procedure_flows?: Array<Record<string, unknown>>;
  sources?: Array<Record<string, unknown>>;
  evidence_type_mapping?: Record<string, unknown>;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}/api/v1${path}`;
  const response = await fetch(url, {
    ...init,
    headers: init?.body instanceof FormData ? init.headers : { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  });
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const data = await response.json();
      message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail || data);
    } catch {
      // keep status message
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export const backendApi = {
  health: () => request<{ status: string; version?: string; time?: string }>('/health'),
  listCases: () => request<CaseSummary[]>('/cases'),
  createCustomCase: (payload: Record<string, unknown>) => request<CaseSummary>('/cases', { method: 'POST', body: JSON.stringify(payload) }),
  listOffenseTemplates: async () => {
    try {
      const data = await request<any[]>('/legal-knowledge/crimes');
      return data.map((item) => ({ offense_id: item.offense_id || item.id || item.name, name: item.name || item.title || item.offense_id }));
    } catch {
      try {
        const data = await request<any[]>('/legal-knowledge/offense-templates');
        return data.map((item) => ({
          offense_id: item.offense_id || item.id || item.name,
          name: item.name || item.title || item.offense_id,
          ...item,
        }));
      } catch {
        return [];
      }
    }
  },
  listLegalProcesses: async () => {
    try {
      return await request<any[]>('/legal-knowledge/processes');
    } catch {
      return request<any[]>('/legal-knowledge/procedure-flows');
    }
  },
  getCaseOverview: (caseId: string) => request<CaseOverview>(`/cases/${caseId}/overview`),
  listEvidence: (caseId: string) => request<EvidenceRecord[]>(`/cases/${caseId}/evidence`),
  getEvidenceDetail: (caseId: string, evidenceId: string) => request<EvidenceDetail>(`/cases/${caseId}/evidence/${evidenceId}`),
  getEvidenceMap: (caseId: string) => request<EvidenceMap>(`/cases/${caseId}/evidence-map`),
  ingestBatch: (caseId: string, files: File[]) => {
    const body = new FormData();
    files.forEach((file) => body.append('files', file, (file as any).webkitRelativePath || file.name));
    return request(`/cases/${caseId}/ingestions/batch`, { method: 'POST', body });
  },
  ingestArchive: (caseId: string, file: File) => {
    const body = new FormData();
    body.append('file', file, file.name);
    return request(`/cases/${caseId}/ingestions/archive`, { method: 'POST', body });
  },
  runAnalysis: (caseId: string) => request(`/cases/${caseId}/analysis/run`, { method: 'POST' }),
  getPortraitFacts: (caseId: string, force = false) =>
    request<PortraitFactsResult>(`/cases/${caseId}/analysis/portrait-facts${force ? '?force=true' : ''}`, { method: 'POST' }),
  listAnalysisThreads: (caseId: string, mode?: 'hypothesis' | 'financial_flow') =>
    request<AnalysisThread[]>(`/cases/${caseId}/analysis/threads${mode ? `?mode=${mode}` : ''}`),
  createAnalysisThread: (caseId: string, payload: { mode: 'hypothesis' | 'financial_flow'; title?: string | null; initial_question: string }) =>
    request<AnalysisThreadDetail>(`/cases/${caseId}/analysis/threads`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getAnalysisThread: (caseId: string, threadId: string) =>
    request<AnalysisThreadDetail>(`/cases/${caseId}/analysis/threads/${threadId}`),
  addAnalysisThreadMessage: (caseId: string, threadId: string, question: string) =>
    request<AnalysisThreadDetail>(`/cases/${caseId}/analysis/threads/${threadId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ question }),
    }),
  deleteAnalysisThread: (caseId: string, threadId: string) =>
    fetch(`${API_BASE}/api/v1/cases/${caseId}/analysis/threads/${threadId}`, { method: 'DELETE' }).then(async (response) => {
      if (!response.ok) throw new Error((await response.text()) || `Request failed: ${response.status}`);
    }),
  getRetrievalSession: (caseId: string, sessionId: string) =>
    request<RetrievalSessionDetail>(`/cases/${caseId}/analysis/retrieval-sessions/${sessionId}`),
  getDocumentMotherGraph: (caseId: string) => request<DocumentMotherGraph>(`/cases/${caseId}/document-mother-graph`),
  rebuildDocumentMotherGraph: (caseId: string) =>
    request<DocumentMotherGraph>(`/cases/${caseId}/document-mother-graph/rebuild`, { method: 'POST' }),
  runRulePack: (caseId: string, packName: string) =>
    request<RulePackRunResult>(`/cases/${caseId}/analysis/rule-packs/${packName}/run`, { method: 'POST' }),
  listRulePacks: () => request<RulePackSummary[]>('/analysis-skills/rule-packs'),
  getRulePack: (skillName: string) => request<RulePackDetail>(`/analysis-skills/rule-packs/${skillName}`),
  getLegalKnowledgeIndex: async () => {
    try {
      return await request<LegalKnowledgeIndex>('/legal-knowledge/index');
    } catch {
      const [offenses, flows, sources, evidenceTypeMapping] = await Promise.all([
        backendApi.listOffenseTemplates().catch(() => []),
        backendApi.listLegalProcesses().catch(() => []),
        request<any[]>('/legal-knowledge/sources').catch(() => []),
        request<Record<string, unknown>>('/legal-knowledge/evidence-type-mapping').catch(() => ({})),
      ]);
      const evidenceItems = Object.keys(evidenceTypeMapping || {}).slice(0, 12);
      return {
        offenses,
        procedure_flows: flows,
        sources,
        evidence_type_mapping: evidenceTypeMapping,
        sections: [
          {
            title: '罪名模板',
            description: '重点罪名、构成要件和审查重点。',
            items: offenses,
          },
          {
            title: '办案流程',
            description: '接警、受案、立案、侦查、强制措施、移送审查等流程模板。',
            items: flows,
          },
          {
            title: '证据标准',
            description: '不同事实和要件对应的应有材料与证明标准。',
            items: evidenceItems,
          },
        ],
      } satisfies LegalKnowledgeIndex;
    }
  },
  uploadLegalKnowledge: (file: File) => {
    const body = new FormData();
    body.append('file', file, file.name);
    return request('/legal-knowledge/procedure-flows/upload', { method: 'POST', body });
  },
  runRawGraphAction: (caseId: string, action: string, payload: Record<string, unknown>) =>
    request<{ status: string; message?: string; graph?: EvidenceLayer }>(`/cases/${caseId}/graph/raw/actions`, {
      method: 'POST',
      body: JSON.stringify({ action, payload }),
    }),
};
