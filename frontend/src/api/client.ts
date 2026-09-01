/**
 * OneMate Centralized API Client
 * Single client layer for all communication with FastAPI backend.
 */

import type {
  HealthResponse,
  CPSE,
  CPSECreateRequest,
  CPSEDeleteResponse,
  MaterialListItem,
  MaterialDetailResponse,
  MaterialDeleteResponse,
  MaterialImportResponse,
  NormalizeResponse,
  MatchResponse,
  HarmonizeResponse,
  NationalMaterialListItem,
  NationalMaterialDetailResponse,
  MaterialMappingHistoryItem,
  ReviewQueueResponse,
  ReviewActionRequest,
  ReviewActionResponse,
  AuditLogItem,
  AuditLogFilterParams,
  DashboardResponse,
  ApiError,
} from '../types/api';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const API_PREFIX = '/api/v1';

export class ApiClientError extends Error {
  status: number;
  data: ApiError;

  constructor(status: number, data: ApiError) {
    let message = 'API Request Failed';
    if (typeof data.detail === 'string') {
      message = data.detail;
    } else if (Array.isArray(data.detail) && data.detail.length > 0) {
      message = data.detail.map((d) => d.msg || 'Validation error').join(', ');
    }
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.data = data;
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${API_PREFIX}${endpoint}`;

  const headers = new Headers(options.headers || {});
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }

  // Set Content-Type only if not FormData
  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (error) {
    throw new ApiClientError(0, {
      detail: error instanceof Error ? error.message : 'Network connection failed',
    });
  }

  if (!response.ok) {
    let errorData: ApiError;
    try {
      errorData = await response.json();
    } catch {
      errorData = { detail: `HTTP ${response.status}: ${response.statusText}` };
    }
    throw new ApiClientError(response.status, errorData);
  }

  return response.json() as Promise<T>;
}

export const api = {
  // ==========================================
  // Health
  // ==========================================
  health: {
    check: () => request<HealthResponse>('/health', { method: 'GET' }),
  },

  // ==========================================
  // CPSEs
  // ==========================================
  cpses: {
    list: () =>
      request<CPSE[]>('/cpses', { method: 'GET' }),

    create: (data: CPSECreateRequest) =>
      request<CPSE>('/cpses', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    delete: (cpseId: string, reviewerToken: string) =>
      request<CPSEDeleteResponse>(`/cpses/${cpseId}`, {
        method: 'DELETE',
        headers: {
          'X-Reviewer-Token': reviewerToken,
        },
      }),
  },

  // ==========================================
  // Materials
  // ==========================================
  materials: {
    listByCpse: (cpseId: string) =>
      request<MaterialListItem[]>(`/cpses/${cpseId}/materials`, {
        method: 'GET',
      }),

    get: (materialId: string) =>
      request<MaterialDetailResponse>(`/materials/${materialId}`, {
        method: 'GET',
      }),

    delete: (materialId: string, reviewerToken: string) =>
      request<MaterialDeleteResponse>(`/materials/${materialId}`, {
        method: 'DELETE',
        headers: {
          'X-Reviewer-Token': reviewerToken,
        },
      }),

    import: (cpseId: string, file: File) => {
      const formData = new FormData();
      formData.append('cpse_id', cpseId);
      formData.append('file', file);

      return request<MaterialImportResponse>('/materials/import', {
        method: 'POST',
        body: formData,
      });
    },

    normalize: (materialId: string) =>
      request<NormalizeResponse>(`/materials/${materialId}/normalize`, {
        method: 'POST',
      }),

    match: (materialId: string) =>
      request<MatchResponse>(`/materials/${materialId}/match`, {
        method: 'POST',
      }),

    harmonize: (materialId: string) =>
      request<HarmonizeResponse>(`/materials/${materialId}/harmonize`, {
        method: 'POST',
      }),
  },

  // ==========================================
  // National Materials
  // ==========================================
  nationalMaterials: {
    list: (skip = 0, limit = 100) =>
      request<NationalMaterialListItem[]>(`/national-materials?skip=${skip}&limit=${limit}`, {
        method: 'GET',
      }),

    get: (nationalMaterialId: string) =>
      request<NationalMaterialDetailResponse>(`/national-materials/${nationalMaterialId}`, {
        method: 'GET',
      }),
  },

  // ==========================================
  // Mapping History
  // ==========================================
  mappings: {
    getHistory: (materialId: string) =>
      request<MaterialMappingHistoryItem[]>(`/materials/${materialId}/mapping-history`, {
        method: 'GET',
      }),
  },

  // ==========================================
  // Reviews
  // ==========================================
  reviews: {
    getQueue: (reviewerToken: string) =>
      request<ReviewQueueResponse>('/reviews/queue', {
        method: 'GET',
        headers: {
          'X-Reviewer-Token': reviewerToken,
        },
      }),

    performAction: (
      recommendationId: string,
      data: ReviewActionRequest,
      reviewerToken: string
    ) =>
      request<ReviewActionResponse>(`/reviews/${recommendationId}/action`, {
        method: 'POST',
        headers: {
          'X-Reviewer-Token': reviewerToken,
        },
        body: JSON.stringify(data),
      }),
  },

  // ==========================================
  // Audit Logs
  // ==========================================
  audit: {
    list: (params: AuditLogFilterParams = {}) => {
      const searchParams = new URLSearchParams();
      if (params.entity_type) searchParams.set('entity_type', params.entity_type);
      if (params.entity_id) searchParams.set('entity_id', params.entity_id);
      if (params.skip !== undefined) searchParams.set('skip', String(params.skip));
      if (params.limit !== undefined) searchParams.set('limit', String(params.limit));

      const queryStr = searchParams.toString();
      return request<AuditLogItem[]>(`/audit${queryStr ? `?${queryStr}` : ''}`, {
        method: 'GET',
      });
    },
  },

  // ==========================================
  // Dashboard
  // ==========================================
  dashboard: {
    get: () => request<DashboardResponse>('/dashboard', { method: 'GET' }),
  },
};

