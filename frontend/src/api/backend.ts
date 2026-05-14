const API_PREFIX = `${import.meta.env.BASE_URL}api/v1`.replace(/\/+/g, '/');

export interface CaseSummary {
  case_id: string;
  title: string;
  status: string;
  created_at: string;
  evidence_count: number;
  memory_count: number;
  offense_id?: string | null;
  legal_basis?: string | null;
}

export interface CaseCreatePayload {
  title: string;
  description?: string | null;
  legal_basis?: string | null;
  offense_id?: string | null;
  owner?: string | null;
}

export interface OffenseTemplateSummary {
  offense_id: string;
  name: string;
  category?: string | null;
  status?: string | null;
  article_hint?: string | null;
  priority_elements?: string[];
}

export interface GraphNode {
  node_id: string;
  label: string;
  type: string;
  tags?: string[];
  properties: Record<string, string | number | boolean | null>;
  evidence_ids: string[];
  timestamp?: string | null;
  time_range?: string[];
  manually_verified: boolean;
}

export interface GraphEdge {
  edge_id: string;
  source_id: string;
  target_id: string;
  relation: string;
  tags?: string[];
  confidence: number;
  properties: Record<string, string | number | boolean | null>;
  evidence_ids: string[];
  timestamp?: string | null;
  time_range?: string[];
  manually_verified: boolean;
}

export interface SuspiciousClue {
  clue_id: string;
  title: string;
  category: string;
  description: string;
  risk_level: string;
  evidence_ids: string[];
  source_passages?: Array<{
    rank: number;
    score: number;
    passage: string;
    evidence_id?: string | null;
    evidence_title?: string | null;
  }>;
}

export interface InvestigationGraph {
  case_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  clues: SuspiciousClue[];
}

export interface EvidenceMapDocument {
  id: string;
  type: 'document';
  evidence_id: string;
  title: string;
  doc_type: string;
  process_stage: string;
  summary: string;
  proof_purpose: string;
  map_tags: string[];
  passage_count: number;
  triple_count: number;
  finding_count: number;
  quality_status: string;
  event_time?: string | null;
  formation_time?: string | null;
}

export interface EvidenceMapPassage {
  id: string;
  type: 'passage';
  parent_doc_id: string;
  evidence_id: string;
  passage_index: number;
  summary: string;
  text_preview: string;
  text: string;
  triple_count: number;
  entities: string[];
  referenced_by_report: boolean;
}

export interface EvidenceMapTriple {
  id: string;
  type: 'triple';
  parent_passage_id: string;
  subject: string;
  predicate: string;
  object: string;
  confidence: 'high' | 'medium' | 'low' | string;
  supporting_text: string;
  source_doc_id: string;
  evidence_id: string;
}

export interface EvidenceMapContainmentEdge {
  id: string;
  source: string;
  target: string;
  type: 'CONTAINS' | 'EXTRACTS' | string;
}

export interface EvidenceMapDocumentEdge {
  id: string;
  source: string;
  target: string;
  type: 'PROCESS_NEXT' | 'SHARED_ENTITY' | 'SUPPORTS_SAME_FINDING' | 'AUTHORITY_CHAIN' | string;
  label: string;
  reason: string;
  supporting_passage_ids: string[];
  supporting_triple_ids: string[];
  shared_entities: string[];
  weight: number;
  visible_by_default: boolean;
}

export interface EvidenceMapPassageEdge {
  id: string;
  source: string;
  target: string;
  type: 'SAME_DOCUMENT_ORDER' | 'SHARED_ENTITY' | 'SUPPORTS_SAME_FINDING' | string;
  label: string;
  supporting_triple_ids: string[];
  shared_entities: string[];
  weight: number;
  visible_by_default: boolean;
}

export interface EvidenceMap {
  case_id: string;
  documents: EvidenceMapDocument[];
  passages: EvidenceMapPassage[];
  triples: EvidenceMapTriple[];
  document_edges: EvidenceMapDocumentEdge[];
  passage_edges: EvidenceMapPassageEdge[];
  containment_edges: EvidenceMapContainmentEdge[];
  warnings: string[];
}

export type GraphInterventionAction = 'upsert_node' | 'upsert_edge' | 'delete_node' | 'delete_edge' | 'verify_node' | 'verify_edge';

export interface GraphInterventionRequest {
  action: GraphInterventionAction;
  node?: GraphNode;
  edge?: GraphEdge;
  target_id?: string;
  reason?: string;
}

export interface PortraitReport {
  report_id: string;
  case_id: string;
  generated_at: string;
  title: string;
  sections: Array<{
    title: string;
    items: string[];
    claims?: Array<{
      claim_id: string;
      text: string;
      section: string;
      element?: string | null;
      status: string;
      confidence: number;
      supporting_passages: Array<{
        evidence_id: string;
        evidence_title?: string | null;
        passage: string;
        score: number;
      }>;
      verification_notes: string;
    }>;
  }>;
  suggestions: string[];
  generation_method?: string;
}

export interface IngestionResult {
  case_id: string;
  accepted: boolean;
  evidence: {
    evidence_id: string;
    case_id: string;
    title: string;
    source_type: string;
    source_ref?: string | null;
    content_preview: string;
    created_at: string;
  };
  extraction?: {
    route: string;
    triples: Array<{ subject: string; relation: string; object: string }>;
    passages: Array<{ text: string }>;
    metadata: Record<string, string | number | boolean | null>;
  } | null;
  next_step: string;
}

export interface EvidenceDetail {
  evidence_id: string;
  case_id: string;
  title: string;
  source_type: string;
  source_ref?: string | null;
  content_preview: string;
  content: string;
  created_at: string;
}

export interface EvidenceRecord {
  evidence_id: string;
  case_id: string;
  title: string;
  source_type: string;
  source_ref?: string | null;
  content_preview: string;
  created_at: string;
}

export interface BatchIngestionResult {
  case_id: string;
  accepted: boolean;
  imported_count: number;
  skipped_count: number;
  evidences: IngestionResult['evidence'][];
  results: IngestionResult[];
  skipped: Array<{ filename: string; reason: string }>;
  next_step: string;
}

export interface AnalysisRunResult {
  case_id: string;
  status: string;
  summary: string;
  graph: InvestigationGraph;
}

export interface TraceResult {
  case_id: string;
  query: string;
  provider: string;
  passages: Array<{
    rank: number;
    score: number;
    passage: string;
    evidence_id?: string | null;
    evidence_title?: string | null;
  }>;
  paths: Array<{
    source: string;
    relation: string;
    target: string;
    score: number;
    evidence_ids: string[];
  }>;
  error?: string | null;
}

export interface ChatResult {
  case_id: string;
  question: string;
  answer: string;
  provider: string;
  passages: TraceResult['passages'];
  paths: TraceResult['paths'];
  error?: string | null;
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
  passages: TraceResult['passages'];
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
  supporting_passages: TraceResult['passages'];
  gaps: string[];
  suggestions: string[];
  gnn_note?: string | null;
}

export interface SuspicionAnalysisResult {
  case_id: string;
  provider: string;
  summary: string;
  candidates: SuspicionCandidate[];
  adopted_hint: string;
  error?: string | null;
}

export interface GroundedSentence {
  sentence_id: string;
  text: string;
  start: number;
  end: number;
  status: string;
  supporting_passages: TraceResult['passages'];
  supporting_graph_paths: TraceResult['paths'];
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
  retrievals: TraceResult['passages'];
  graph_context: string[];
  legal_context: TraceResult['passages'];
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

export interface RetrievalToolCall {
  tool_call_id: string;
  tool_name: string;
  arguments: Record<string, string | number | boolean | string[] | null>;
  summary: string;
  passages: TraceResult['passages'];
  graph_facts: string[];
  legal_passages: TraceResult['passages'];
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

export interface ProcedureFlowSummary {
  id: string;
  title: string;
  kind: string;
  relative_path: string;
  size: number;
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

export interface RulePackSummary {
  name: string;
  title: string;
  version: string;
  description: string;
  enabled: boolean;
  case_types: string[];
  task_types: string[];
  triggers: string[];
  content_hash: string;
  rules_count?: number;
  findings_count?: number;
  last_run_at?: string | null;
}

export interface RulePackDetail extends RulePackSummary {
  skill_md?: string;
  manifest?: Record<string, unknown>;
  checks?: unknown[];
  finding_templates?: Record<string, unknown>;
  examples?: unknown[];
  test_cases?: unknown[];
  run_history?: Array<Record<string, unknown>>;
}

export interface LegalKnowledgeIndex {
  crimes?: OffenseTemplateSummary[];
  processes?: ProcedureFlowSummary[];
  material_lists?: Array<Record<string, unknown>>;
  evidence_standards?: Array<Record<string, unknown>>;
  legal_sources?: Array<Record<string, unknown>>;
}

export interface AnalysisContextSummary {
  context_id: string;
  case_id: string;
  title: string;
  kind: string;
  created_at: string;
  used_evidence_map: boolean;
  used_rule_packs: boolean;
  used_findings: boolean;
  used_hipporag: boolean;
  used_legal_knowledge: boolean;
  unsupported_claims_count: number;
}

export interface AnalysisContextDetail extends AnalysisContextSummary {
  evidence_map?: Partial<EvidenceMap>;
  rule_findings?: RuleFinding[];
  hipporag_passages?: TraceResult['passages'];
  hipporag_paths?: TraceResult['paths'];
  legal_passages?: TraceResult['passages'];
  prompt?: string;
  answer_constraints?: string[];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = init?.body instanceof FormData ? init.headers : { 'Content-Type': 'application/json', ...(init?.headers ?? {}) };
  const response = await fetch(`${API_PREFIX}${path}`, { headers, ...init });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const backendApi = {
  health: () => request<{ status: string; env: string }>('/health'),
  listCases: () => request<CaseSummary[]>('/cases'),
  createCase: (title: string, description?: string) =>
    request<CaseSummary>('/cases', {
      method: 'POST',
      body: JSON.stringify({ title, description }),
    }),
  createCustomCase: (payload: CaseCreatePayload) =>
    request<CaseSummary>('/cases', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateCase: (caseId: string, payload: Partial<CaseCreatePayload>) =>
    request<CaseSummary>(`/cases/${caseId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteCase: (caseId: string) =>
    fetch(`${API_PREFIX}/cases/${caseId}`, { method: 'DELETE' }).then(async (response) => {
      if (!response.ok) throw new Error((await response.text()) || `Request failed: ${response.status}`);
    }),
  ingestText: (caseId: string, title: string, content: string, sourceType = 'text') =>
    request<IngestionResult>(`/cases/${caseId}/ingestions/text`, {
      method: 'POST',
      body: JSON.stringify({ title, content, source_type: sourceType }),
    }),
  ingestFile: (caseId: string, file: File, sourceType = 'unknown', title?: string) => {
    const body = new FormData();
    body.append('file', file);
    body.append('source_type', sourceType);
    if (title) body.append('title', title);
    return request<IngestionResult>(`/cases/${caseId}/ingestions/files`, {
      method: 'POST',
      body,
    });
  },
  ingestBatch: (caseId: string, files: File[]) => {
    const body = new FormData();
    files.forEach((file) => body.append('files', file, file.webkitRelativePath || file.name));
    body.append('source_type', 'unknown');
    return request<BatchIngestionResult>(`/cases/${caseId}/ingestions/batch`, {
      method: 'POST',
      body,
    });
  },
  ingestArchive: (caseId: string, file: File) => {
    const body = new FormData();
    body.append('file', file);
    return request<BatchIngestionResult>(`/cases/${caseId}/ingestions/archive`, {
      method: 'POST',
      body,
    });
  },
  listEvidence: (caseId: string) => request<EvidenceRecord[]>(`/cases/${caseId}/evidence`),
  getEvidenceDetail: (caseId: string, evidenceId: string) => request<EvidenceDetail>(`/cases/${caseId}/evidence/${evidenceId}`),
  runAnalysis: (caseId: string) =>
    request<AnalysisRunResult>(`/cases/${caseId}/analysis/run`, {
      method: 'POST',
      body: JSON.stringify({ scopes: ['full'] }),
    }),
  traceAnalysis: (caseId: string, query: string, evidenceIds: string[] = [], topK = 8) =>
    request<TraceResult>(`/cases/${caseId}/analysis/trace`, {
      method: 'POST',
      body: JSON.stringify({ query, evidence_ids: evidenceIds, top_k: topK }),
    }),
  chatAnalysis: (caseId: string, question: string, evidenceIds: string[] = [], topK = 8) =>
    request<ChatResult>(`/cases/${caseId}/analysis/chat`, {
      method: 'POST',
      body: JSON.stringify({ question, evidence_ids: evidenceIds, top_k: topK }),
    }),
  getPortraitFacts: (caseId: string, force = false) =>
    request<PortraitFactsResult>(`/cases/${caseId}/analysis/portrait-facts${force ? '?force=true' : ''}`, {
      method: 'POST',
    }),
  runSuspicionAnalysis: (caseId: string, payload: { mode: 'cross_case' | 'hypothesis' | 'financial_flow'; hypothesis?: string; selected_case_ids?: string[] }) =>
    request<SuspicionAnalysisResult>(`/cases/${caseId}/analysis/suspicion`, {
      method: 'POST',
      body: JSON.stringify({
        mode: payload.mode,
        hypothesis: payload.hypothesis || null,
        selected_case_ids: payload.selected_case_ids || [],
        max_items: 12,
      }),
    }),
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
    fetch(`${API_PREFIX}/cases/${caseId}/analysis/threads/${threadId}`, { method: 'DELETE' }).then(async (response) => {
      if (!response.ok) throw new Error((await response.text()) || `Request failed: ${response.status}`);
    }),
  getRetrievalSession: (caseId: string, sessionId: string) =>
    request<RetrievalSessionDetail>(`/cases/${caseId}/analysis/retrieval-sessions/${sessionId}`),
  getDocumentMotherGraph: (caseId: string) => request<DocumentMotherGraph>(`/cases/${caseId}/document-mother-graph`),
  rebuildDocumentMotherGraph: (caseId: string) =>
    request<DocumentMotherGraph>(`/cases/${caseId}/document-mother-graph/rebuild`, { method: 'POST' }),
  listRulePacks: () => request<RulePackSummary[]>('/analysis-skills/rule-packs'),
  getRulePack: (skillName: string) => request<RulePackDetail>(`/analysis-skills/rule-packs/${skillName}`),
  importRulePack: (file: File) => {
    const body = new FormData();
    body.append('file', file);
    return request<RulePackDetail>('/analysis-skills/import', { method: 'POST', body });
  },
  exportRulePack: (skillName: string) =>
    fetch(`${API_PREFIX}/analysis-skills/${skillName}/export`).then(async (response) => {
      if (!response.ok) throw new Error((await response.text()) || `Request failed: ${response.status}`);
      return response.blob();
    }),
  runRulePack: (caseId: string, packName: string) =>
    request<RulePackRunResult>(`/cases/${caseId}/analysis/rule-packs/${packName}/run`, { method: 'POST' }),
  getLegalKnowledgeIndex: () => request<LegalKnowledgeIndex>('/legal-knowledge/index'),
  listLegalCrimes: () => request<OffenseTemplateSummary[]>('/legal-knowledge/crimes'),
  listLegalProcesses: () => request<ProcedureFlowSummary[]>('/legal-knowledge/processes'),
  uploadLegalKnowledge: (file: File) => {
    const body = new FormData();
    body.append('file', file);
    return request<ProcedureFlowSummary>('/legal-knowledge/upload', { method: 'POST', body });
  },
  listAnalysisContexts: (caseId: string) => request<AnalysisContextSummary[]>(`/cases/${caseId}/analysis/contexts`),
  getAnalysisContext: (caseId: string, contextId: string) => request<AnalysisContextDetail>(`/cases/${caseId}/analysis/contexts/${contextId}`),
  getGraph: (caseId: string) => request<InvestigationGraph>(`/cases/${caseId}/graph`),
  getEvidenceMap: (caseId: string) => request<EvidenceMap>(`/cases/${caseId}/evidence-map`),
  getMergedGraph: (caseId: string, selectedCaseIds: string[]) =>
    request<InvestigationGraph>(`/cases/${caseId}/graph/merged`, {
      method: 'POST',
      body: JSON.stringify({ selected_case_ids: selectedCaseIds }),
    }),
  applyGraphIntervention: (caseId: string, payload: GraphInterventionRequest) =>
    request<InvestigationGraph>(`/cases/${caseId}/graph/interventions`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  generatePortrait: (caseId: string) =>
    request<PortraitReport>(`/cases/${caseId}/reports/portrait`, {
      method: 'POST',
    }),
  getLatestPortrait: (caseId: string) =>
    request<PortraitReport>(`/cases/${caseId}/reports/portrait/latest`),
  listOffenseTemplates: () => request<OffenseTemplateSummary[]>('/legal-knowledge/offense-templates'),
  getOffenseTemplate: (offenseId: string) => request<Record<string, unknown>>(`/legal-knowledge/offense-templates/${offenseId}`),
  listProcedureFlows: () => request<ProcedureFlowSummary[]>('/legal-knowledge/procedure-flows'),
  createProcedureFlow: (payload: { title: string; content: string; kind?: string }) =>
    request<ProcedureFlowSummary>('/legal-knowledge/procedure-flows', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  uploadProcedureFlow: (file: File, title?: string, kind = 'user_knowledge') => {
    const form = new FormData();
    form.append('file', file);
    if (title) form.append('title', title);
    form.append('kind', kind);
    return request<ProcedureFlowSummary>('/legal-knowledge/procedure-flows/upload', {
      method: 'POST',
      body: form,
    });
  },
  retrieveLegalKnowledge: (query: string, offenseId?: string | null, topK = 8) => {
    const params = new URLSearchParams({ query, top_k: String(topK) });
    if (offenseId) params.set('offense_id', offenseId);
    return request<TraceResult>(`/legal-knowledge/retrieve?${params.toString()}`);
  },
};
