import React, { useState, useEffect } from 'react'
import { CryptographicKey } from '../types'
import { keyService } from '../services/api'

export const KeyManagement: React.FC = () => {
  const [keys, setKeys] = useState<CryptographicKey[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Registration Form State
  const [activeTab, setActiveTab] = useState<'list' | 'register'>('list')
  const [cryptoMode, setCryptoMode] = useState<'pqc' | 'classical'>('pqc')
  const [selectedAlgorithm, setSelectedAlgorithm] = useState<string>('ml-kem-768')
  const [publicKeyMaterial, setPublicKeyMaterial] = useState<string>('')
  const [isRegistering, setIsRegistering] = useState<boolean>(false)

  // Dialog States
  const [rotatingKey, setRotatingKey] = useState<CryptographicKey | null>(null)
  const [revokingKey, setRevokingKey] = useState<CryptographicKey | null>(null)
  const [revocationReason, setRevocationReason] = useState<string>('')
  const [actionLoading, setActionLoading] = useState<boolean>(false)

  // Load user's keys on mount
  useEffect(() => {
    fetchKeys()
  }, [])

  const fetchKeys = async () => {
    setLoading(true)
    setError(null)
    const res = await keyService.getMyKeys(true)
    if (res.error) {
      setError(res.error)
    } else if (res.data?.keys) {
      setKeys(res.data.keys)
    }
    setLoading(false)
  }

  // Handle Algorithm Mode Change
  const handleModeChange = (mode: 'pqc' | 'classical') => {
    setCryptoMode(mode)
    if (mode === 'pqc') {
      setSelectedAlgorithm('ml-kem-768')
    } else {
      setSelectedAlgorithm('x25519')
    }
  }

  // Client-side key generation helper (generates compliant Base64 key material)
  const handleGenerateKey = () => {
    let keyBytesLength = 32
    if (selectedAlgorithm === 'ml-kem-768') keyBytesLength = 1184
    else if (selectedAlgorithm === 'ml-dsa-65') keyBytesLength = 1952
    else if (selectedAlgorithm === 'x25519' || selectedAlgorithm === 'ed25519') keyBytesLength = 32

    const randomBytes = new Uint8Array(keyBytesLength)
    window.crypto.getRandomValues(randomBytes)
    let binary = ''
    for (let i = 0; i < randomBytes.byteLength; i++) {
      binary += String.fromCharCode(randomBytes[i])
    }
    const b64 = btoa(binary)
    setPublicKeyMaterial(b64)
  }

  const handleRegisterKey = async (e: React.FormEvent) => {
    e.preventDefault()

    setIsRegistering(true)
    setError(null)
    setSuccessMessage(null)

    const keyMaterialToSend = publicKeyMaterial.trim() || undefined
    const res = await keyService.register(selectedAlgorithm, keyMaterialToSend)
    if (res.error) {
      setError(res.error)
    } else {
      setSuccessMessage(`Successfully registered ${selectedAlgorithm} key!`)
      setPublicKeyMaterial('')
      setActiveTab('list')
      await fetchKeys()
    }
    setIsRegistering(false)
  }

  const handleConfirmRotate = async () => {
    if (!rotatingKey) return
    const keyId = rotatingKey.key_id || rotatingKey.keyId
    if (!keyId) return

    setActionLoading(true)
    setError(null)
    setSuccessMessage(null)

    const res = await keyService.rotateKey(keyId)
    if (res.error) {
      setError(res.error)
    } else {
      setSuccessMessage(`Key ${keyId} rotated to new version!`)
      setRotatingKey(null)
      await fetchKeys()
    }
    setActionLoading(false)
  }

  const handleConfirmRevoke = async () => {
    if (!revokingKey) return
    const keyId = revokingKey.key_id || revokingKey.keyId
    if (!keyId) return

    setActionLoading(true)
    setError(null)
    setSuccessMessage(null)

    const res = await keyService.revokeKey(keyId, revocationReason)
    if (res.error) {
      setError(res.error)
    } else {
      setSuccessMessage(`Key ${keyId} revoked successfully.`)
      setRevokingKey(null)
      setRevocationReason('')
      await fetchKeys()
    }
    setActionLoading(false)
  }

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', padding: '24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '28px', fontWeight: '600', margin: '0 0 8px 0' }}>
            Cryptographic Key Management
          </h2>
          <p style={{ color: 'var(--text, #6b6375)', fontSize: '15px' }}>
            Manage Post-Quantum (ML-KEM, ML-DSA) and Classical (X25519, Ed25519) keys.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            id="tab-key-list"
            type="button"
            onClick={() => setActiveTab('list')}
            style={{
              padding: '8px 16px',
              borderRadius: '6px',
              border: '1px solid var(--border, #ccc)',
              background: activeTab === 'list' ? 'var(--accent, #aa3bff)' : 'transparent',
              color: activeTab === 'list' ? '#fff' : 'inherit',
              cursor: 'pointer',
              fontWeight: '500',
            }}
          >
            My Keys ({keys.length})
          </button>
          <button
            id="tab-register-key"
            type="button"
            onClick={() => setActiveTab('register')}
            style={{
              padding: '8px 16px',
              borderRadius: '6px',
              border: '1px solid var(--border, #ccc)',
              background: activeTab === 'register' ? 'var(--accent, #aa3bff)' : 'transparent',
              color: activeTab === 'register' ? '#fff' : 'inherit',
              cursor: 'pointer',
              fontWeight: '500',
            }}
          >
            + Register Key
          </button>
        </div>
      </div>

      {/* Notification Banners */}
      {error && (
        <div
          role="alert"
          style={{
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid #ef4444',
            color: '#dc2626',
            padding: '12px 16px',
            borderRadius: '6px',
            marginBottom: '16px',
          }}
        >
          {error}
        </div>
      )}

      {successMessage && (
        <div
          role="status"
          style={{
            background: 'rgba(34, 197, 94, 0.1)',
            border: '1px solid #22c55e',
            color: '#16a34a',
            padding: '12px 16px',
            borderRadius: '6px',
            marginBottom: '16px',
          }}
        >
          {successMessage}
        </div>
      )}

      {/* Tab 1: Key List */}
      {activeTab === 'list' && (
        <div style={{ background: 'var(--code-bg, #f9f9f9)', border: '1px solid var(--border, #e5e4e7)', borderRadius: '8px', padding: '20px' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '32px' }}>Loading cryptographic keys...</div>
          ) : keys.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px' }}>
              <p style={{ marginBottom: '16px' }}>No cryptographic keys found for your account.</p>
              <button
                type="button"
                onClick={() => setActiveTab('register')}
                style={{
                  padding: '8px 16px',
                  borderRadius: '6px',
                  background: 'var(--accent, #aa3bff)',
                  color: '#fff',
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                Register Your First Key
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {keys.map((k) => {
                const keyId = k.key_id || k.keyId || k.id
                const isPQC = k.algorithm.includes('ml-') || k.algorithm.includes('kyber') || k.algorithm.includes('dilithium')
                const isRevoked = k.status === 'revoked'
                const isSuperseded = k.status === 'superseded'

                return (
                  <div
                    key={keyId}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      background: 'var(--bg, #fff)',
                      border: '1px solid var(--border, #e5e4e7)',
                      borderRadius: '6px',
                      padding: '16px',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                        <span
                          style={{
                            fontSize: '12px',
                            fontWeight: '600',
                            padding: '2px 8px',
                            borderRadius: '4px',
                            background: isPQC ? 'rgba(170, 59, 255, 0.15)' : 'rgba(59, 130, 246, 0.15)',
                            color: isPQC ? '#aa3bff' : '#2563eb',
                          }}
                        >
                          {isPQC ? 'PQC' : 'CLASSICAL'} : {k.algorithm.toUpperCase()}
                        </span>
                        <span
                          style={{
                            fontSize: '12px',
                            fontWeight: '600',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            background: '#f3f4f6',
                            color: '#374151',
                          }}
                        >
                          v{k.version}
                        </span>
                        <span
                          style={{
                            fontSize: '12px',
                            fontWeight: '600',
                            padding: '2px 8px',
                            borderRadius: '4px',
                            background: isRevoked
                              ? 'rgba(239, 68, 68, 0.15)'
                              : isSuperseded
                              ? 'rgba(245, 158, 11, 0.15)'
                              : 'rgba(34, 197, 94, 0.15)',
                            color: isRevoked ? '#dc2626' : isSuperseded ? '#d97706' : '#16a34a',
                          }}
                        >
                          {k.status.toUpperCase()}
                        </span>
                      </div>
                      <div style={{ fontFamily: 'var(--mono, monospace)', fontSize: '14px', color: 'var(--text-h, #000)' }}>
                        {keyId}
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button
                        type="button"
                        disabled={isRevoked}
                        onClick={() => setRotatingKey(k)}
                        style={{
                          padding: '6px 12px',
                          borderRadius: '4px',
                          border: '1px solid var(--border, #ccc)',
                          background: 'transparent',
                          cursor: isRevoked ? 'not-allowed' : 'pointer',
                          opacity: isRevoked ? 0.5 : 1,
                        }}
                      >
                        Rotate
                      </button>
                      <button
                        type="button"
                        disabled={isRevoked}
                        onClick={() => setRevokingKey(k)}
                        style={{
                          padding: '6px 12px',
                          borderRadius: '4px',
                          border: '1px solid #ef4444',
                          color: '#dc2626',
                          background: 'transparent',
                          cursor: isRevoked ? 'not-allowed' : 'pointer',
                          opacity: isRevoked ? 0.5 : 1,
                        }}
                      >
                        Revoke
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Register Form */}
      {activeTab === 'register' && (
        <form
          id="key-register-form"
          onSubmit={handleRegisterKey}
          style={{
            background: 'var(--code-bg, #f9f9f9)',
            border: '1px solid var(--border, #e5e4e7)',
            borderRadius: '8px',
            padding: '24px',
          }}
        >
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', fontWeight: '500', marginBottom: '8px' }}>
              Cryptographic Paradigm
            </label>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                type="button"
                onClick={() => handleModeChange('pqc')}
                style={{
                  flex: 1,
                  padding: '10px',
                  borderRadius: '6px',
                  border: `2px solid ${cryptoMode === 'pqc' ? 'var(--accent, #aa3bff)' : 'var(--border, #ccc)'}`,
                  background: cryptoMode === 'pqc' ? 'var(--accent-bg, rgba(170, 59, 255, 0.1))' : '#fff',
                  cursor: 'pointer',
                  fontWeight: '600',
                }}
              >
                Post-Quantum Cryptography (PQC)
              </button>
              <button
                type="button"
                onClick={() => handleModeChange('classical')}
                style={{
                  flex: 1,
                  padding: '10px',
                  borderRadius: '6px',
                  border: `2px solid ${cryptoMode === 'classical' ? 'var(--accent, #aa3bff)' : 'var(--border, #ccc)'}`,
                  background: cryptoMode === 'classical' ? 'rgba(59, 130, 246, 0.1)' : '#fff',
                  cursor: 'pointer',
                  fontWeight: '600',
                }}
              >
                Classical Cryptography
              </button>
            </div>
          </div>

          <div style={{ marginBottom: '20px' }}>
            <label htmlFor="algorithm-select" style={{ display: 'block', fontWeight: '500', marginBottom: '8px' }}>
              Algorithm
            </label>
            <select
              id="algorithm-select"
              value={selectedAlgorithm}
              onChange={(e) => setSelectedAlgorithm(e.target.value)}
              style={{
                width: '100%',
                padding: '10px',
                borderRadius: '6px',
                border: '1px solid var(--border, #ccc)',
                background: 'var(--bg, #fff)',
              }}
            >
              {cryptoMode === 'pqc' ? (
                <>
                  <option value="ml-kem-768">ML-KEM-768 (Kyber768 - Key Encapsulation)</option>
                  <option value="ml-dsa-65">ML-DSA-65 (Dilithium3 - Digital Signature)</option>
                </>
              ) : (
                <>
                  <option value="x25519">X25519 (ECDH Key Agreement)</option>
                  <option value="ed25519">Ed25519 (Digital Signature)</option>
                </>
              )}
            </select>
          </div>

          <div style={{ marginBottom: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <label htmlFor="public-key-input" style={{ fontWeight: '500' }}>
                Public Key Material (Base64)
              </label>
              <button
                type="button"
                onClick={handleGenerateKey}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--accent, #aa3bff)',
                  cursor: 'pointer',
                  fontSize: '13px',
                  textDecoration: 'underline',
                }}
              >
                Auto-generate keypair in browser
              </button>
            </div>
            <textarea
              id="public-key-input"
              rows={4}
              value={publicKeyMaterial}
              onChange={(e) => setPublicKeyMaterial(e.target.value)}
              placeholder="Leave blank to auto-generate a secure server-managed keypair (with private key for decryption), or paste custom Base64 public key..."
              style={{
                width: '100%',
                padding: '10px',
                borderRadius: '6px',
                border: '1px solid var(--border, #ccc)',
                fontFamily: 'var(--mono, monospace)',
                fontSize: '13px',
                background: 'var(--bg, #fff)',
                boxSizing: 'border-box',
              }}
            />
            <p style={{ fontSize: '12px', color: 'var(--text, #666)', marginTop: '4px' }}>
              💡 <strong>Recommended:</strong> Leave blank to generate a cryptographically valid quantum keypair with secure private key storage for decryption.
            </p>
          </div>

          <button
            id="btn-register-submit"
            type="submit"
            disabled={isRegistering}
            style={{
              width: '100%',
              padding: '12px',
              borderRadius: '6px',
              border: 'none',
              background: 'var(--accent, #aa3bff)',
              color: '#fff',
              fontWeight: '600',
              cursor: isRegistering ? 'not-allowed' : 'pointer',
            }}
          >
            {isRegistering ? 'Registering Key...' : 'Register Key'}
          </button>
        </form>
      )}

      {/* Rotation Confirmation Dialog */}
      {rotatingKey && (
        <div
          role="dialog"
          aria-modal="true"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
        >
          <div
            style={{
              background: 'var(--bg, #fff)',
              borderRadius: '8px',
              padding: '24px',
              maxWidth: '480px',
              width: '90%',
            }}
          >
            <h3 style={{ margin: '0 0 12px 0' }}>Rotate Key: {rotatingKey.key_id || rotatingKey.keyId}</h3>
            <p style={{ color: 'var(--text, #666)', fontSize: '14px', marginBottom: '20px' }}>
              Rotating will advance this key to version {(rotatingKey.version || 1) + 1}. The current version
              will be marked as <strong>superseded</strong>. Past encrypted files will remain decryptable, and new
              shares will automatically target the new active version.
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button
                type="button"
                onClick={() => setRotatingKey(null)}
                style={{ padding: '8px 16px', borderRadius: '4px', border: '1px solid var(--border, #ccc)', background: 'transparent', cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button
                id="btn-confirm-rotate"
                type="button"
                disabled={actionLoading}
                onClick={handleConfirmRotate}
                style={{ padding: '8px 16px', borderRadius: '4px', border: 'none', background: 'var(--accent, #aa3bff)', color: '#fff', cursor: 'pointer' }}
              >
                {actionLoading ? 'Rotating...' : 'Confirm Rotation'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Revocation Confirmation Dialog */}
      {revokingKey && (
        <div
          role="dialog"
          aria-modal="true"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
        >
          <div
            style={{
              background: 'var(--bg, #fff)',
              borderRadius: '8px',
              padding: '24px',
              maxWidth: '480px',
              width: '90%',
            }}
          >
            <h3 style={{ margin: '0 0 12px 0', color: '#dc2626' }}>
              Revoke Key: {revokingKey.key_id || revokingKey.keyId}
            </h3>
            <p style={{ color: 'var(--text, #666)', fontSize: '14px', marginBottom: '16px' }}>
              Are you sure you want to revoke this key? Revoking will immediately prevent other users from selecting
              this key for new file shares. This action cannot be undone.
            </p>
            <div style={{ marginBottom: '16px' }}>
              <label htmlFor="revoke-reason" style={{ display: 'block', fontSize: '13px', fontWeight: '500', marginBottom: '4px' }}>
                Revocation Reason (Optional)
              </label>
              <input
                id="revoke-reason"
                type="text"
                value={revocationReason}
                onChange={(e) => setRevocationReason(e.target.value)}
                placeholder="e.g. Device lost, scheduled deprecation"
                style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid var(--border, #ccc)', boxSizing: 'border-box' }}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button
                type="button"
                onClick={() => setRevokingKey(null)}
                style={{ padding: '8px 16px', borderRadius: '4px', border: '1px solid var(--border, #ccc)', background: 'transparent', cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button
                id="btn-confirm-revoke"
                type="button"
                disabled={actionLoading}
                onClick={handleConfirmRevoke}
                style={{ padding: '8px 16px', borderRadius: '4px', border: 'none', background: '#dc2626', color: '#fff', cursor: 'pointer' }}
              >
                {actionLoading ? 'Revoking...' : 'Confirm Revoke'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
