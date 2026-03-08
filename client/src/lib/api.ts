const BASE = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Request failed: ${res.status}`);
  }
  return res.json();
}

// Verticals
export const fetchVerticals = () => request<any[]>('/verticals');

// Projects
export const fetchProjects = (verticalId?: string) =>
  request<any[]>(`/projects${verticalId ? `?verticalId=${verticalId}` : ''}`);
export const fetchProject = (id: string) => request<any>(`/projects/${id}`);
export const createProject = (data: any) =>
  request<any>('/projects', { method: 'POST', body: JSON.stringify(data) });
export const updateProject = (id: string, data: any) =>
  request<any>(`/projects/${id}`, { method: 'PUT', body: JSON.stringify(data) });
export const deleteProject = (id: string) =>
  request<any>(`/projects/${id}`, { method: 'DELETE' });

// Blocks
export const fetchBlocks = (params?: Record<string, string>) => {
  const qs = params ? '?' + new URLSearchParams(params).toString() : '';
  return request<any[]>(`/blocks${qs}`);
};
export const fetchBlock = (id: string) => request<any>(`/blocks/${id}`);
export const createBlock = (data: any) =>
  request<any>('/blocks', { method: 'POST', body: JSON.stringify(data) });
export const updateBlock = (id: string, data: any) =>
  request<any>(`/blocks/${id}`, { method: 'PUT', body: JSON.stringify(data) });
export const deleteBlock = (id: string) =>
  request<any>(`/blocks/${id}`, { method: 'DELETE' });
export const generateBlocks = (data: any) =>
  request<any[]>('/blocks/generate', { method: 'POST', body: JSON.stringify(data) });
export const bulkApproveBlocks = (ids: string[]) =>
  request<any>('/blocks/bulk-approve', { method: 'POST', body: JSON.stringify({ ids }) });
export const bulkDeleteBlocks = (ids: string[]) =>
  request<any>('/blocks/bulk-delete', { method: 'POST', body: JSON.stringify({ ids }) });

// Outputs
export const fetchOutputs = (params?: Record<string, string>) => {
  const qs = params ? '?' + new URLSearchParams(params).toString() : '';
  return request<any[]>(`/outputs${qs}`);
};
export const fetchOutput = (id: string) => request<any>(`/outputs/${id}`);
export const composeOutput = (data: any) =>
  request<any>('/outputs/compose', { method: 'POST', body: JSON.stringify(data) });
export const bulkGenerateOutputs = (data: any) =>
  request<any>('/outputs/bulk-generate', { method: 'POST', body: JSON.stringify(data) });
export const updateOutput = (id: string, data: any) =>
  request<any>(`/outputs/${id}`, { method: 'PUT', body: JSON.stringify(data) });
export const deleteOutput = (id: string) =>
  request<any>(`/outputs/${id}`, { method: 'DELETE' });

// Templates
export const fetchTemplates = () => request<any[]>('/templates');

// Export helpers
export const getExportURL = (type: 'blocks.csv' | 'outputs.csv' | 'outputs.json') =>
  `${BASE}/export/${type}`;
