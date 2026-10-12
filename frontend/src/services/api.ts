import { User, LoginResponse } from '../types'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'
const API_TIMEOUT = parseInt(import.meta.env.VITE_API_TIMEOUT || '30000', 10)

export interface ApiResponse<T> {
  data?: T
  error?: string
  message?: string
}

/**
 * Execute fetch with timeout
 */
function fetchWithTimeout<T>(url: string, init?: RequestInit): Promise<Response> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT)

  return fetch(url, {
    ...init,
    signal: controller.signal,
  }).finally(() => clearTimeout(timeoutId))
}

export async function apiRequest<T>(endpoint: string, options?: RequestInit): Promise<ApiResponse<T>> {
  const url = `${API_BASE_URL}${endpoint}`
  const token = typeof window !== 'undefined' ? localStorage.getItem('session_token') : null

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((options?.headers as Record<string, string>) || {}),
  }

  try {
    const response = await fetchWithTimeout(url, {
      ...options,
      headers,
      credentials: 'include',
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      let msg = errorData.detail || errorData.message || `API error: ${response.status}`
      if (Array.isArray(msg)) {
        msg = msg.map((m: any) => m.msg || JSON.stringify(m)).join(', ')
      } else if (typeof msg === 'object') {
        msg = JSON.stringify(msg)
      }
      throw new Error(msg)
    }

    return { data: await response.json() }
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : 'Unknown error',
    }
  }
}

export const authService = {
  register: (email: string, password: string) =>
    apiRequest<LoginResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  login: async (email: string, password: string) => {
    const res = await apiRequest<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    if (res.data?.session_token && typeof window !== 'undefined') {
      localStorage.setItem('session_token', res.data.session_token)
    }
    return res
  },
  logout: async () => {
    const res = await apiRequest<{ message: string }>('/auth/logout', { method: 'POST' })
    if (typeof window !== 'undefined') {
      localStorage.removeItem('session_token')
    }
    return res
  },
  getSession: () => apiRequest<User>('/auth/me'),
}

export const keyService = {
  register: (algorithm: string, publicKeyMaterial: string) =>
    apiRequest<CryptographicKey>('/keys/register', {
      method: 'POST',
      body: JSON.stringify({
        algorithm,
        public_key_material: publicKeyMaterial,
      }),
    }),
  getMyKeys: (includeInactive = true) =>
    apiRequest<KeyListResponse>(`/keys/my-keys?include_inactive=${includeInactive}`),
  getKeyById: (keyId: string) => apiRequest<CryptographicKey>(`/keys/${keyId}`),
  getUserKeys: (userId: string, algorithm?: string) =>
    apiRequest<KeyListResponse>(
      `/keys/user/${userId}${algorithm ? `?algorithm=${algorithm}` : ''}`
    ),
  rotateKey: (keyId: string, newPublicKeyMaterial?: string) =>
    apiRequest<CryptographicKey>(`/keys/${keyId}/rotate`, {
      method: 'POST',
      body: JSON.stringify({
        public_key_material: newPublicKeyMaterial || null,
      }),
    }),
  revokeKey: (keyId: string, reason?: string) =>
    apiRequest<{ key_id: string; status: string; message: string }>(
      `/keys/${keyId}/revoke`,
      {
        method: 'POST',
        body: JSON.stringify({ reason: reason || null }),
      }
    ),
}

export const fileService = {
  upload: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiRequest<{ fileId: string }>('/files/upload', {
      method: 'POST',
      body: formData,
    })
  },
  share: (fileId: string, recipientIds: string[], encryptionMode: 'pqc' | 'classical') =>
    apiRequest<FilePackage>('/files/share', {
      method: 'POST',
      body: JSON.stringify({ fileId, recipientIds, encryptionMode }),
    }),
  list: () => apiRequest<FilePackageMetadata[]>('/files'),
  getPackage: (packageId: string) => apiRequest<FilePackage>(`/files/${packageId}`),
  download: (packageId: string) => apiRequest<Blob>(`/files/${packageId}/download`, {
    headers: { Accept: 'application/octet-stream' },
  }),
  revokeGrant: (packageId: string, grantId: string) =>
    apiRequest<void>(`/files/${packageId}/grants/${grantId}/revoke`, { method: 'POST' }),
}

export const auditService = {
  getLogs: (params?: { eventType?: string; userId?: string; startDate?: string; endDate?: string }) => {
    const query = new URLSearchParams(params as Record<string, string>).toString()
    return apiRequest<AuditLog[]>(`/audit-logs?${query}`)
  },
}
