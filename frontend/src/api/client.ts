const BASE_URL = '/api';

class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body);
  }
  return res.json();
}

export const api = {
  boms: {
    list: () => request<import('../types').Bom[]>('/boms'),
    get: (id: string) => request<import('../types').Bom>(`/boms/${id}`),
    delete: (id: string) => request<void>(`/boms/${id}`, { method: 'DELETE' }),
    components: (id: string, params?: Record<string, string>) => {
      const qs = params ? '?' + new URLSearchParams(params).toString() : '';
      return request<import('../types').PaginatedResponse<import('../types').ComponentWithRisk>>(
        `/boms/${id}/components${qs}`,
      );
    },
    crossExposure: () => request<import('../types').CrossExposureRow[]>('/boms/cross-exposure'),
    upload: async (file: File, name: string, program?: string, description?: string) => {
      const form = new FormData();
      form.append('file', file);
      form.append('name', name);
      if (program) form.append('program', program);
      if (description) form.append('description', description);
      const res = await fetch(`${BASE_URL}/boms/upload`, { method: 'POST', body: form });
      if (!res.ok) throw new ApiError(res.status, await res.text());
      return res.json();
    },
  },

  enrichment: {
    run: (bomId: string) => request<unknown>(`/enrichment/run/${bomId}`, { method: 'POST' }),
    status: (bomId: string) => request<import('../types').EnrichmentStatus>(`/enrichment/status/${bomId}`),
    forComponent: (componentId: string) =>
      request<import('../types').EnrichmentRecord[]>(`/components/${componentId}/enrichment`),
  },

  risk: {
    score: (bomId: string) => request<unknown>(`/risk/score/${bomId}`, { method: 'POST' }),
    scores: (bomId: string) => request<import('../types').RiskScore[]>(`/risk/scores/${bomId}`),
    summary: (bomId: string) => request<import('../types').RiskSummary>(`/risk/summary/${bomId}`),
    profiles: () => request<unknown>('/risk/profiles'),
  },

  scenarios: {
    list: () => request<import('../types').Scenario[]>('/scenarios'),
    get: (id: string) => request<import('../types').Scenario>(`/scenarios/${id}`),
    create: (data: Record<string, unknown>) =>
      request<import('../types').Scenario>('/scenarios', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    results: (id: string) => request<import('../types').ScenarioResult>(`/scenarios/${id}/results`),
    delete: (id: string) => request<void>(`/scenarios/${id}`, { method: 'DELETE' }),
    templates: () => request<unknown>('/scenarios/templates'),
  },

  export: {
    riskReport: (bomId: string) => request<string>(`/export/risk-report/${bomId}`),
    scenarioReport: (id: string) => request<string>(`/export/scenario-report/${id}`),
  },

  health: {
    ready: () =>
      request<{
        status: string;
        checks: Record<string, unknown>;
      }>('/ready'),
  },
};
