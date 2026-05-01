const API_PREFIX = '/api/v1';

export interface CaseSummary {
  case_id: string;
  title: string;
  status: string;
  created_at: string;
  evidence_count: number;
  memory_count: number;
}

export interface GraphNode {
  node_id: string;
  label: string;
  type: string;
  properties: Record<string, string | number | boolean | null>;
  evidence_ids: string[];
  manually_verified: boolean;
}

export interface GraphEdge {
  edge_id: string;
  source_id: string;
  target_id: string;
  relation: string;
  confidence: number;
  evidence_ids: string[];
  manually_verified: boolean;
}

export interface SuspiciousClue {
  clue_id: string;
  title: string;
  category: string;
  description: string;
  risk_level: string;
  evidence_ids: string[];
}

export interface InvestigationGraph {
  case_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  clues: SuspiciousClue[];
}

export interface PortraitReport {
  report_id: string;
  case_id: string;
  generated_at: string;
  title: string;
  sections: Array<{ title: string; items: string[] }>;
  suggestions: string[];
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
  runAnalysis: (caseId: string) =>
    request<AnalysisRunResult>(`/cases/${caseId}/analysis/run`, {
      method: 'POST',
      body: JSON.stringify({ scopes: ['full'] }),
    }),
  getGraph: (caseId: string) => request<InvestigationGraph>(`/cases/${caseId}/graph`),
  generatePortrait: (caseId: string) =>
    request<PortraitReport>(`/cases/${caseId}/reports/portrait`, {
      method: 'POST',
    }),
};
