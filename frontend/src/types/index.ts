export interface User {
  id: string
  email: string
  createdAt?: string
  created_at?: string
  updatedAt?: string
  updated_at?: string
  accountStatus?: 'active' | 'suspended' | 'deleted' | string
  account_status?: 'active' | 'suspended' | 'deleted' | string
}

export interface AuthSession {
  token?: string
  session_token?: string
  user: User
  expiresAt?: string
}

export interface LoginResponse {
  id: string
  email: string
  account_status: string
  session_token: string
}

export interface CryptographicKey {
  id: string
  key_id?: string
  keyId?: string
  user_id?: string
  userId?: string
  algorithm: 'ml-kem-768' | 'ml-dsa-65' | 'x25519' | 'ed25519' | string
  key_type?: 'public' | 'private' | string
  keyType?: 'public' | 'private' | string
  version: number
  public_key_material?: string
  publicKeyMaterial?: string
  created_at?: string
  createdAt?: string
  status: 'active' | 'revoked' | 'superseded' | string
}

export interface KeyListResponse {
  keys: CryptographicKey[]
  total: number
}

export interface FilePackage {
  id: string
  senderId: string
  senderEmail: string
  recipients: string[]
  fileName: string
  fileSize: number
  encryptionMode: 'pqc' | 'classical'
  createdAt: string
  status: 'pending' | 'shared' | 'revoked'
}

export interface FilePackageMetadata {
  id: string
  senderId: string
  senderEmail: string
  fileName: string
  fileSize: number
  encryptionMode: 'pqc' | 'classical'
  createdAt: string
}

export interface AuditLog {
  id: string
  eventType: string
  action?: string
  status?: string
  userId?: string
  userEmail?: string
  resourceId?: string
  resourceType?: string
  timestamp: string
  details?: Record<string, unknown>
  ipAddress?: string
  userAgent?: string
}

export interface AuditLogsResponse {
  logs: AuditLog[]
  total: number
  limit: number
  offset: number
}

export interface TimingStats {
  median_ms: number
  p90_ms: number
  p95_ms: number
  p99_ms: number
  min_ms: number
  max_ms: number
  mean_ms: number
  std_dev_ms: number
  iterations: number
}

export interface SizeMetrics {
  public_key_bytes?: number | null
  private_key_bytes?: number | null
  ciphertext_bytes?: number | null
  signature_bytes?: number | null
  shared_secret_bytes?: number | null
  overhead_bytes?: number | null
}

export interface BenchmarkItem {
  operation: string
  algorithm: string
  mode: 'pqc' | 'classical' | 'hybrid' | 'symmetric'
  category: 'key_generation' | 'key_establishment' | 'signatures' | 'symmetric_encryption'
  payload_size_bytes?: number | null
  timing: TimingStats
  sizes: SizeMetrics
  throughput_mb_s?: number | null
}

export interface EnvironmentMetadata {
  cpu_model: string
  cpu_cores: number
  total_ram_gb: number
  os_name: string
  os_version: string
  architecture: string
  python_version: string
  cryptography_version: string
  pqc_backend: string
  environment_notice: string
}

export interface BenchmarkSummary {
  pqc_total_time_ms: number
  classical_total_time_ms: number
  time_ratio: number
  key_size_overhead_ratio: number
  signature_size_overhead_ratio: number
}

export interface BenchmarkResponse {
  id: string
  timestamp: string
  iterations: number
  environment: EnvironmentMetadata
  summary: BenchmarkSummary
  results: BenchmarkItem[]
}

export interface BenchmarkRequest {
  iterations?: number
  file_sizes_kb?: number[]
  include_pqc?: boolean
  include_classical?: boolean
}
