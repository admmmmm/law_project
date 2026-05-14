export interface WorkspaceState {
  workspaceId: string;
  baseCaseId: string;
  selectedCaseIds: string[];
  temporary: boolean;
  title: string;
}

export function workspaceKey(workspaceId: string) {
  return `workspace:${workspaceId}`;
}

export function createTemporaryWorkspace(baseCaseId: string, selectedCaseIds: string[]) {
  const workspaceId = `tmp_${baseCaseId}_${Date.now().toString(36)}`;
  const state: WorkspaceState = {
    workspaceId,
    baseCaseId,
    selectedCaseIds,
    temporary: true,
    title: `临时联合分析 ${selectedCaseIds.length + 1} 个案件`,
  };
  localStorage.setItem(workspaceKey(workspaceId), JSON.stringify(state));
  return state;
}

export function resolveWorkspace(rawId: string | undefined | null): WorkspaceState | null {
  const id = String(rawId || '').trim();
  if (!id) return null;
  if (id.startsWith('tmp_')) {
    try {
      return JSON.parse(localStorage.getItem(workspaceKey(id)) || 'null') as WorkspaceState | null;
    } catch {
      return null;
    }
  }
  return {
    workspaceId: id,
    baseCaseId: id,
    selectedCaseIds: [],
    temporary: false,
    title: id,
  };
}

export function currentWorkspaceFromPath(pathname = window.location.pathname) {
  const base = import.meta.env.BASE_URL || '/';
  let path = pathname;
  if (base !== '/' && path.startsWith(base)) {
    path = `/${path.slice(base.length)}`;
  }
  const parts = path.split('/').filter(Boolean);
  if (parts[0] === 'cases' && parts[1]) {
    return resolveWorkspace(parts[1]);
  }
  return resolveWorkspace(parts[0]);
}
