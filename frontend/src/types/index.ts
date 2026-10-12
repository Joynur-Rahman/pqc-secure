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
  userId: string
  algorithm: 'ml-kem-768' | 'ml-dsa-65' | 'x25519' | 'ed25519'
  keyType: 'public' | 'private'
  version: number
  publicKeyMaterial: string
  keyId: string
  createdAt: string
  status: 'active' | 'revoked'
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
  userId?: string
  userEmail?: string
  timestamp: string
  details: Record<string, unknown>
}
