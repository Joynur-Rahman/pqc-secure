const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
const API_TIMEOUT = parseInt(import.meta.env.VITE_API_TIMEOUT || '30000', 10)

interface ApiResponse<T> {
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
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
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
      throw new Error(errorData.message || `API error: ${response.status}`)
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
    apiRequest<{ userId: string }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  login: (email: string, password: string) =>
    apiRequest<AuthSession>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  logout: () => apiRequest<void>('/auth/logout', { method: 'POST' }),
  getSession: () => apiRequest<AuthSession>('/auth/session'),
}

export const keyService = {
  register: (algorithm: string, publicKey: string) =>
    apiRequest<CryptographicKey>('/keys/register', {
      method: 'POST',
      body: JSON.stringify({ algorithm, publicKey }),
    }),
  getMyKeys: () => apiRequest<CryptographicKey[]>('/keys/my-keys'),
  getKeyById: (keyId: string) => apiRequest<CryptographicKey>(`/keys/${keyId}`),
  getUserKeys: (userId: string) => apiRequest<CryptographicKey[]>(`/keys/user/${userId}`),
  rotateKey: (keyId: string) => apiRequest<CryptographicKey>(`/keys/${keyId}/rotate`, { method: 'POST' }),
  revokeKey: (keyId: string) => apiRequest<void>(`/keys/${keyId}/revoke`, { method: 'POST' }),
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
