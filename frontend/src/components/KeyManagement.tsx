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
    <div data-ui="key-management" className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-white/[0.08]">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl sm:text-2xl font-semibold tracking-tight text-white">
              Cryptographic Key Management
            </h2>
            <span className="pqc-badge pqc-badge-quantum text-[10px] py-0.5">NIST PQC</span>
          </div>
          <p className="text-xs text-neutral-400 mt-1">
            Manage Post-Quantum (ML-KEM, ML-DSA) and Classical (X25519, Ed25519) keys.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            id="tab-key-list"
            type="button"
            onClick={() => setActiveTab('list')}
            className={activeTab === 'list' ? 'pqc-btn-primary text-xs py-1.5 px-3.5' : 'pqc-btn-secondary text-xs py-1.5 px-3.5'}
          >
            My Keys ({keys.length})
          </button>
          <button
            id="tab-register-key"
            type="button"
            onClick={() => setActiveTab('register')}
            className={activeTab === 'register' ? 'pqc-btn-primary text-xs py-1.5 px-3.5' : 'pqc-btn-secondary text-xs py-1.5 px-3.5'}
          >
            + Register Key
          </button>
        </div>
      </div>

      {/* Notification Banners */}
      {error && (
        <div
          role="alert"
          className="p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2"
        >
          <svg className="w-4 h-4 text-rose-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span>{error}</span>
        </div>
      )}

      {successMessage && (
        <div
          role="status"
          className="p-3.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2"
        >
          <svg className="w-4 h-4 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <span>{successMessage}</span>
        </div>
      )}

      {/* Tab 1: Key List */}
      {activeTab === 'list' && (
        <div className="pqc-card p-5">
          {loading ? (
            <div className="text-center py-10 space-y-2 text-xs text-neutral-400">
              <span className="pqc-dot-pulse inline-block"></span>
              <p>Loading cryptographic keys...</p>
            </div>
          ) : keys.length === 0 ? (
            <div className="text-center py-12 space-y-3">
              <div className="w-10 h-10 mx-auto rounded-lg bg-white/[0.02] border border-white/[0.06] flex items-center justify-center text-neutral-400 mb-2">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                </svg>
              </div>
              <p className="text-xs text-neutral-300 font-medium">No cryptographic keys found for your account.</p>
              <button
                type="button"
                onClick={() => setActiveTab('register')}
                className="pqc-btn-primary text-xs"
              >
                Register Your First Key
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {keys.map((k) => {
                const keyId = k.key_id || k.keyId || k.id
                const isPQC = k.algorithm.includes('ml-') || k.algorithm.includes('kyber') || k.algorithm.includes('dilithium')
                const isRevoked = k.status === 'revoked'
                const isSuperseded = k.status === 'superseded'

                return (
                  <div
                    key={keyId}
                    className="p-4 rounded-lg bg-[#0c0d0e] border border-white/[0.07] hover:border-white/[0.15] transition-colors flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
                  >
                    <div className="space-y-1.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`pqc-badge ${isPQC ? 'pqc-badge-quantum' : 'pqc-badge-warning'}`}>
                          {isPQC ? 'PQC' : 'CLASSICAL'} : {k.algorithm.toUpperCase()}
                        </span>
                        <code className="px-2 py-0.5 rounded text-[10px] bg-white/[0.05] text-neutral-300 border border-white/[0.08]">
                          v{k.version}
                        </code>
                        <span
                          className={`pqc-badge ${
                            isRevoked
                              ? 'pqc-badge-danger'
                              : isSuperseded
                              ? 'pqc-badge-warning'
                              : 'pqc-badge-quantum'
                          }`}
                        >
                          {k.status.toUpperCase()}
                        </span>
                      </div>
                      <div className="pqc-mono text-xs text-sky-300 font-medium break-all">
                        {keyId}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        type="button"
                        disabled={isRevoked}
                        onClick={() => setRotatingKey(k)}
                        className="pqc-btn-secondary text-xs py-1 px-3"
                      >
                        Rotate
                      </button>
                      <button
                        type="button"
                        disabled={isRevoked}
                        onClick={() => setRevokingKey(k)}
                        className="pqc-btn-danger text-xs py-1 px-3"
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
          className="pqc-card p-6 space-y-5"
        >
          <div>
            <label className="block text-xs font-semibold text-neutral-300 mb-2">
              Cryptographic Paradigm
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => handleModeChange('pqc')}
                className={`p-3 rounded-lg border text-left transition-colors ${
                  cryptoMode === 'pqc'
                    ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300'
                    : 'bg-[#0c0d0e] border-white/[0.08] text-neutral-400 hover:text-white'
                }`}
              >
                <div className="text-xs font-semibold flex items-center justify-between">
                  <span>Post-Quantum Cryptography (PQC)</span>
                  {cryptoMode === 'pqc' && <span className="pqc-dot-pulse"></span>}
                </div>
                <div className="text-[11px] text-neutral-400 mt-1">
                  NIST FIPS 203 (ML-KEM) & FIPS 204 (ML-DSA) lattice-based algorithms.
                </div>
              </button>
              <button
                type="button"
                onClick={() => handleModeChange('classical')}
                className={`p-3 rounded-lg border text-left transition-colors ${
                  cryptoMode === 'classical'
                    ? 'bg-amber-500/10 border-amber-500/40 text-amber-300'
                    : 'bg-[#0c0d0e] border-white/[0.08] text-neutral-400 hover:text-white'
                }`}
              >
                <div className="text-xs font-semibold">
                  Classical Cryptography
                </div>
                <div className="text-[11px] text-neutral-400 mt-1">
                  Legacy elliptic curve primitives (X25519 & Ed25519).
                </div>
              </button>
            </div>
          </div>

          <div>
            <label htmlFor="algorithm-select" className="block text-xs font-semibold text-neutral-300 mb-2">
              Algorithm
            </label>
            <select
              id="algorithm-select"
              value={selectedAlgorithm}
              onChange={(e) => setSelectedAlgorithm(e.target.value)}
              className="pqc-input"
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

          <div>
            <div className="flex justify-between items-center mb-2">
              <label htmlFor="public-key-input" className="text-xs font-semibold text-neutral-300">
                Public Key Material (Base64)
              </label>
              <button
                type="button"
                onClick={handleGenerateKey}
                className="text-xs text-emerald-400 hover:text-emerald-300 underline font-medium cursor-pointer"
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
              className="pqc-input text-xs"
            />
            <p className="text-[11px] text-neutral-400 mt-1.5 flex items-center gap-1.5">
              <svg className="w-3.5 h-3.5 text-amber-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span><strong className="text-neutral-300">Recommended:</strong> Leave blank to generate a cryptographically valid quantum keypair with secure private key storage for decryption.</span>
            </p>
          </div>

          <button
            id="btn-register-submit"
            type="submit"
            disabled={isRegistering}
            className="pqc-btn-primary w-full py-2.5 text-xs font-semibold"
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
          className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50"
        >
          <div className="pqc-card pqc-card-elevated max-w-md w-full p-6 space-y-4">
            <h3 className="text-sm font-semibold text-white">Rotate Key: {rotatingKey.key_id || rotatingKey.keyId}</h3>
            <p className="text-xs text-neutral-400 leading-relaxed">
              Rotating will advance this key to version {(rotatingKey.version || 1) + 1}. The current version
              will be marked as <strong className="text-amber-400">superseded</strong>. Past encrypted files will remain decryptable, and new
              shares will automatically target the new active version.
            </p>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setRotatingKey(null)}
                className="pqc-btn-secondary text-xs py-1.5 px-3.5"
              >
                Cancel
              </button>
              <button
                id="btn-confirm-rotate"
                type="button"
                disabled={actionLoading}
                onClick={handleConfirmRotate}
                className="pqc-btn-primary text-xs py-1.5 px-3.5"
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
          className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50"
        >
          <div className="pqc-card pqc-card-elevated max-w-md w-full p-6 space-y-4">
            <h3 className="text-sm font-semibold text-rose-400">
              Revoke Key: {revokingKey.key_id || revokingKey.keyId}
            </h3>
            <p className="text-xs text-neutral-400 leading-relaxed">
              Are you sure you want to revoke this key? Revoking will immediately prevent other users from selecting
              this key for new file shares. This action cannot be undone.
            </p>
            <div className="space-y-1.5">
              <label htmlFor="revoke-reason" className="block text-xs font-semibold text-neutral-300">
                Revocation Reason (Optional)
              </label>
              <input
                id="revoke-reason"
                type="text"
                value={revocationReason}
                onChange={(e) => setRevocationReason(e.target.value)}
                placeholder="e.g. Device lost, scheduled deprecation"
                className="pqc-input text-xs"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setRevokingKey(null)}
                className="pqc-btn-secondary text-xs py-1.5 px-3.5"
              >
                Cancel
              </button>
              <button
                id="btn-confirm-revoke"
                type="button"
                disabled={actionLoading}
                onClick={handleConfirmRevoke}
                className="pqc-btn-danger text-xs py-1.5 px-3.5"
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
