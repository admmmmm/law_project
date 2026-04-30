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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  });

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
  ingestText: (caseId: string, title: string, content: string) =>
    request(`/cases/${caseId}/ingestions/text`, {
      method: 'POST',
      body: JSON.stringify({ title, content, source_type: 'frontend_text' }),
    }),
  runAnalysis: (caseId: string) =>
    request(`/cases/${caseId}/analysis/run`, {
      method: 'POST',
      body: JSON.stringify({}),
    }),
  getGraph: (caseId: string) => request<InvestigationGraph>(`/cases/${caseId}/graph`),
  generatePortrait: (caseId: string) =>
    request<PortraitReport>(`/cases/${caseId}/reports/portrait`, {
      method: 'POST',
    }),
};
