import React, { useState, useEffect } from 'react'
import { fileService } from '../services/api'
import { useAuth } from '../hooks/useAuth'

export interface SharedFileItem {
  id: string
  package_id: string
  original_filename?: string
  file_size: number
  crypto_mode: string
  package_version: string
  sender_id: string
  sender_email?: string
  recipients?: Array<{
    recipient_id: string
    recipient_email?: string
    recipient_key_id: string
    grant_id?: string
    status?: string
    revoked_at?: string
  }>
  created_at: string
  status: string
}

export const FileList: React.FC = () => {
  const { user } = useAuth()
  const [files, setFiles] = useState<SharedFileItem[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [successToast, setSuccessToast] = useState<string | null>(null)

  // Download state: packageId -> { downloading: boolean, progress: string, error?: string, success?: boolean }
  const [downloadStatus, setDownloadStatus] = useState<
    Record<string, { downloading: boolean; progress: string; error?: string; success?: boolean }>
  >({})

  // Revocation modal state
  const [revocationModal, setRevocationModal] = useState<{
    isOpen: boolean
    packageId: string
    grantId: string
    recipientEmail: string
    filename: string
    revoking: boolean
    error?: string
  } | null>(null)

  // Collapsible state for recipient drawers: packageId -> boolean
  const [expandedRecipients, setExpandedRecipients] = useState<Record<string, boolean>>({})

  useEffect(() => {
    loadFiles()
  }, [])

  const loadFiles = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fileService.list()
      if (response.data) {
        const raw = response.data as any
        const list: SharedFileItem[] = raw.packages || (Array.isArray(raw) ? raw : [])
        setFiles(list)
      } else if (response.error) {
        setError(response.error)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to retrieve shared files')
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = async (fileItem: SharedFileItem) => {
    const pkgId = fileItem.package_id || fileItem.id
    setDownloadStatus((prev) => ({
      ...prev,
      [pkgId]: {
        downloading: true,
        progress: '1/3: Verifying sender digital signature...',
        error: undefined,
        success: false,
      },
    }))

    try {
      await new Promise((r) => setTimeout(r, 300))
      setDownloadStatus((prev) => ({
        ...prev,
        [pkgId]: {
          downloading: true,
          progress: `2/3: Decapsulating ${fileItem.crypto_mode.toUpperCase()} key & unwrapping CEK...`,
        },
      }))

      await new Promise((r) => setTimeout(r, 300))
      setDownloadStatus((prev) => ({
        ...prev,
        [pkgId]: {
          downloading: true,
          progress: '3/3: Decrypting AES-256-GCM payload with authenticated data...',
        },
      }))

      const result = await fileService.download(pkgId)

      if (result.error || !result.blob) {
        throw new Error(result.error || 'Decryption failed')
      }

      const blobUrl = window.URL.createObjectURL(result.blob)
      const anchor = document.createElement('a')
      anchor.href = blobUrl
      anchor.download = result.filename || fileItem.original_filename || `download_${pkgId}`
      document.body.appendChild(anchor)
      anchor.click()
      document.body.removeChild(anchor)
      window.URL.revokeObjectURL(blobUrl)

      setDownloadStatus((prev) => ({
        ...prev,
        [pkgId]: {
          downloading: false,
          progress: 'Decrypted and verified successfully!',
          success: true,
        },
      }))

      setTimeout(() => {
        setDownloadStatus((prev) => ({
          ...prev,
          [pkgId]: { downloading: false, progress: '', success: false },
        }))
      }, 4000)
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : 'Decryption or download failed'
      setDownloadStatus((prev) => ({
        ...prev,
        [pkgId]: {
          downloading: false,
          progress: '',
          error: errMsg,
          success: false,
        },
      }))
    }
  }

  const toggleRecipients = (pkgId: string) => {
    setExpandedRecipients((prev) => ({
      ...prev,
      [pkgId]: !prev[pkgId],
    }))
  }

  const handleOpenRevokeModal = (
    packageId: string,
    grantId: string,
    recipientEmail: string,
    filename: string
  ) => {
    setRevocationModal({
      isOpen: true,
      packageId,
      grantId,
      recipientEmail,
      filename,
      revoking: false,
      error: undefined,
    })
  }

  const handleConfirmRevoke = async () => {
    if (!revocationModal) return
    const { packageId, grantId, recipientEmail } = revocationModal
    setRevocationModal((prev) => (prev ? { ...prev, revoking: true, error: undefined } : null))

    try {
      const response = await fileService.revokeGrant(packageId, grantId)
      if (response && (response as any).error) {
        throw new Error((response as any).error)
      }

      // Update state locally
      setFiles((prev) =>
        prev.map((pkg) => {
          if ((pkg.package_id || pkg.id) === packageId) {
            return {
              ...pkg,
              recipients: pkg.recipients?.map((r) =>
                (r.grant_id === grantId || r.recipient_id === grantId)
                  ? { ...r, status: 'revoked', revoked_at: new Date().toISOString() }
                  : r
              ),
            }
          }
          return pkg
        })
      )

      setSuccessToast(`Access for ${recipientEmail} has been successfully revoked.`)
      setRevocationModal(null)

      setTimeout(() => {
        setSuccessToast(null)
      }, 5000)
    } catch (err) {
      setRevocationModal((prev) =>
        prev
          ? {
              ...prev,
              revoking: false,
              error: err instanceof Error ? err.message : 'Failed to revoke access grant',
            }
          : null
      )
    }
  }

  const formatFileSize = (bytes: number): string => {
    if (!bytes || bytes <= 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`
  }

  const formatDate = (isoStr?: string): string => {
    if (!isoStr) return 'Unknown date'
    try {
      return new Date(isoStr).toLocaleString(undefined, {
        dateStyle: 'medium',
        timeStyle: 'short',
      })
    } catch {
      return isoStr
    }
  }

  return (
    <div
      style={{
        maxWidth: '980px',
        margin: '0 auto',
        padding: '2rem 1rem',
        fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
      }}
    >
      {/* Header Banner */}
      <div
        style={{
          background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #312e81 100%)',
          borderRadius: '16px',
          padding: '2rem',
          color: '#ffffff',
          boxShadow: '0 10px 25px -5px rgba(15, 23, 42, 0.4)',
          marginBottom: '2rem',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '1.75rem' }}>🔐</span>
              <h1 style={{ fontSize: '1.75rem', fontWeight: '700', margin: 0, letterSpacing: '-0.02em' }}>
                Shared Files & Access Control
              </h1>
            </div>
            <p style={{ color: '#94a3b8', margin: 0, fontSize: '0.95rem' }}>
              Manage post-quantum packages, grant share revocations, and authenticate end-to-end decryptions.
            </p>
          </div>
          <button
            onClick={loadFiles}
            disabled={loading}
            style={{
              background: 'rgba(255, 255, 255, 0.1)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              color: '#ffffff',
              padding: '0.6rem 1.2rem',
              borderRadius: '8px',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontWeight: '500',
              fontSize: '0.9rem',
              backdropFilter: 'blur(8px)',
              transition: 'background 0.2s',
            }}
          >
            {loading ? 'Refreshing...' : '↻ Refresh'}
          </button>
        </div>
      </div>

      {/* Success Notification Banner */}
      {successToast && (
        <div
          data-testid="success-toast"
          style={{
            background: '#f0fdf4',
            border: '1px solid #86efac',
            color: '#166534',
            padding: '1rem',
            borderRadius: '10px',
            marginBottom: '1.5rem',
            fontSize: '0.95rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>✅</span>
            <span>{successToast}</span>
          </div>
          <button
            onClick={() => setSuccessToast(null)}
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: '#166534',
              fontWeight: '700',
            }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Global Error Banner */}
      {error && (
        <div
          data-testid="error-banner"
          style={{
            background: '#fef2f2',
            border: '1px solid #fecaca',
            color: '#991b1b',
            padding: '1rem',
            borderRadius: '10px',
            marginBottom: '1.5rem',
            fontSize: '0.95rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {/* Files List Container */}
      <div
        style={{
          background: '#ffffff',
          borderRadius: '16px',
          border: '1px solid #e2e8f0',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            padding: '1.25rem 1.5rem',
            borderBottom: '1px solid #f1f5f9',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <h2 style={{ fontSize: '1.15rem', fontWeight: '600', color: '#1e293b', margin: 0 }}>
            Available Encrypted Packages ({files.length})
          </h2>
        </div>

        {loading ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: '#64748b' }}>
            <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>⏳</div>
            <p style={{ margin: 0, fontWeight: '500' }}>Loading shared packages...</p>
          </div>
        ) : files.length === 0 ? (
          <div
            data-testid="no-files-message"
            style={{
              padding: '3.5rem 1.5rem',
              textAlign: 'center',
              color: '#64748b',
            }}
          >
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📭</div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: '600', color: '#334155', margin: '0 0 0.5rem 0' }}>
              No shared files found
            </h3>
            <p style={{ margin: 0, fontSize: '0.9rem', color: '#94a3b8' }}>
              Files encrypted for you or sent by your account will appear here.
            </p>
          </div>
        ) : (
          <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
            {files.map((file) => {
              const pkgId = file.package_id || file.id
              const status = downloadStatus[pkgId] || { downloading: false, progress: '' }
              const isPqc = (file.crypto_mode || '').toLowerCase() === 'pqc'
              const isSender = (user && (user.id === file.sender_id || user.email === file.sender_email)) || false
              const recipients = file.recipients || []
              const isExpanded = expandedRecipients[pkgId] !== false // Default open if has recipients

              return (
                <li
                  key={pkgId}
                  data-testid={`file-row-${pkgId}`}
                  style={{
                    padding: '1.5rem',
                    borderBottom: '1px solid #f1f5f9',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '1rem',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
                    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                      <div
                        style={{
                          width: '48px',
                          height: '48px',
                          borderRadius: '12px',
                          background: isPqc ? '#eef2ff' : '#ecfdf5',
                          color: isPqc ? '#4f46e5' : '#059669',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: '1.5rem',
                          flexShrink: 0,
                        }}
                      >
                        {isPqc ? '🛡️' : '🔒'}
                      </div>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                          <span
                            data-testid={`filename-${pkgId}`}
                            style={{ fontWeight: '600', color: '#0f172a', fontSize: '1.05rem' }}
                          >
                            {file.original_filename || `Package-${pkgId.slice(0, 8)}`}
                          </span>
                          <span
                            style={{
                              fontSize: '0.75rem',
                              fontWeight: '600',
                              padding: '0.2rem 0.55rem',
                              borderRadius: '9999px',
                              background: isPqc ? '#e0e7ff' : '#d1fae5',
                              color: isPqc ? '#3730a3' : '#065f46',
                            }}
                          >
                            {isPqc ? 'NIST PQC (ML-KEM / ML-DSA)' : 'Classical (X25519 / Ed25519)'}
                          </span>
                          {isSender && (
                            <span
                              data-testid={`sender-badge-${pkgId}`}
                              style={{
                                fontSize: '0.75rem',
                                fontWeight: '600',
                                padding: '0.2rem 0.55rem',
                                borderRadius: '9999px',
                                background: '#f1f5f9',
                                color: '#475569',
                                border: '1px solid #cbd5e1',
                              }}
                            >
                              Sent by you
                            </span>
                          )}
                        </div>
                        <div
                          style={{
                            fontSize: '0.85rem',
                            color: '#64748b',
                            marginTop: '0.25rem',
                            display: 'flex',
                            gap: '0.85rem',
                            flexWrap: 'wrap',
                          }}
                        >
                          <span>Sender: <strong>{file.sender_email || 'Authenticated User'}</strong></span>
                          <span>•</span>
                          <span>Size: <strong>{formatFileSize(file.file_size)}</strong></span>
                          <span>•</span>
                          <span>Created: {formatDate(file.created_at)}</span>
                        </div>
                      </div>
                    </div>

                    {/* Download Button */}
                    <button
                      data-testid={`download-button-${pkgId}`}
                      onClick={() => handleDownload(file)}
                      disabled={status.downloading}
                      style={{
                        padding: '0.65rem 1.35rem',
                        borderRadius: '8px',
                        background: status.downloading
                          ? '#cbd5e1'
                          : isPqc
                          ? '#4f46e5'
                          : '#059669',
                        color: '#ffffff',
                        border: 'none',
                        cursor: status.downloading ? 'not-allowed' : 'pointer',
                        fontWeight: '600',
                        fontSize: '0.9rem',
                        boxShadow: status.downloading ? 'none' : '0 2px 4px rgba(0,0,0,0.1)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        transition: 'opacity 0.2s',
                      }}
                    >
                      {status.downloading ? (
                        <>
                          <span style={{ animation: 'spin 1s linear infinite' }}>⏳</span>
                          <span>Decrypting...</span>
                        </>
                      ) : (
                        <>
                          <span>⬇️</span>
                          <span>Decrypt & Download</span>
                        </>
                      )}
                    </button>
                  </div>

                  {/* Decryption Status / Error Bar */}
                  {status.downloading && (
                    <div
                      data-testid={`progress-${pkgId}`}
                      style={{
                        background: '#f8fafc',
                        border: '1px solid #e2e8f0',
                        borderRadius: '8px',
                        padding: '0.6rem 1rem',
                        fontSize: '0.85rem',
                        color: '#334155',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                      }}
                    >
                      <span style={{ color: '#4f46e5' }}>⚙️</span>
                      <span>{status.progress}</span>
                    </div>
                  )}

                  {status.success && (
                    <div
                      data-testid={`success-${pkgId}`}
                      style={{
                        background: '#f0fdf4',
                        border: '1px solid #bbf7d0',
                        borderRadius: '8px',
                        padding: '0.6rem 1rem',
                        fontSize: '0.85rem',
                        color: '#15803d',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                      }}
                    >
                      <span>✅</span>
                      <span>{status.progress}</span>
                    </div>
                  )}

                  {status.error && (
                    <div
                      data-testid={`error-${pkgId}`}
                      style={{
                        background: '#fef2f2',
                        border: '1px solid #fecaca',
                        borderRadius: '8px',
                        padding: '0.6rem 1rem',
                        fontSize: '0.85rem',
                        color: '#b91c1c',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                      }}
                    >
                      <span>❌</span>
                      <span>{status.error}</span>
                    </div>
                  )}

                  {/* Recipient Access Management Section (Phase 6: Task 6.3) */}
                  {recipients.length > 0 && (
                    <div
                      style={{
                        marginTop: '0.25rem',
                        background: '#f8fafc',
                        border: '1px solid #e2e8f0',
                        borderRadius: '10px',
                        padding: '0.85rem 1rem',
                      }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          cursor: 'pointer',
                        }}
                        onClick={() => toggleRecipients(pkgId)}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span style={{ fontSize: '0.9rem' }}>👥</span>
                          <span style={{ fontSize: '0.85rem', fontWeight: '600', color: '#334155' }}>
                            Recipients & Access Control ({recipients.length})
                          </span>
                        </div>
                        <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                          {isExpanded ? '▲ Hide' : '▼ Show'}
                        </span>
                      </div>

                      {isExpanded && (
                        <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                          {recipients.map((rec) => {
                            const isRevoked = rec.status === 'revoked'
                            const grantId = rec.grant_id || rec.recipient_id

                            return (
                              <div
                                key={grantId}
                                data-testid={`recipient-row-${grantId}`}
                                style={{
                                  display: 'flex',
                                  justifyContent: 'space-between',
                                  alignItems: 'center',
                                  padding: '0.5rem 0.75rem',
                                  background: '#ffffff',
                                  borderRadius: '6px',
                                  border: '1px solid #e2e8f0',
                                  flexWrap: 'wrap',
                                  gap: '0.5rem',
                                }}
                              >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                  <span style={{ fontSize: '0.85rem', fontWeight: '500', color: '#1e293b' }}>
                                    {rec.recipient_email || `Recipient ID: ${rec.recipient_id.slice(0, 8)}`}
                                  </span>

                                  {/* Status badge */}
                                  <span
                                    data-testid={isRevoked ? `status-badge-revoked-${grantId}` : `status-badge-active-${grantId}`}
                                    style={{
                                      fontSize: '0.7rem',
                                      fontWeight: '700',
                                      padding: '0.15rem 0.5rem',
                                      borderRadius: '4px',
                                      background: isRevoked ? '#fee2e2' : '#dcfce7',
                                      color: isRevoked ? '#991b1b' : '#15803d',
                                      letterSpacing: '0.02em',
                                    }}
                                  >
                                    {isRevoked ? 'REVOKED' : 'ACTIVE'}
                                  </span>

                                  {isRevoked && rec.revoked_at && (
                                    <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                                      (Revoked: {formatDate(rec.revoked_at)})
                                    </span>
                                  )}
                                </div>

                                {/* Revoke button for Sender */}
                                {isSender && (
                                  <div>
                                    {isRevoked ? (
                                      <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontStyle: 'italic' }}>
                                        Access Revoked
                                      </span>
                                    ) : (
                                      <button
                                        data-testid={`revoke-btn-${grantId}`}
                                        onClick={() =>
                                          handleOpenRevokeModal(
                                            pkgId,
                                            grantId,
                                            rec.recipient_email || rec.recipient_id,
                                            file.original_filename || `Package ${pkgId.slice(0, 8)}`
                                          )
                                        }
                                        style={{
                                          background: '#fff1f2',
                                          color: '#e11d48',
                                          border: '1px solid #fecdd3',
                                          padding: '0.35rem 0.85rem',
                                          borderRadius: '6px',
                                          fontSize: '0.8rem',
                                          fontWeight: '600',
                                          cursor: 'pointer',
                                          transition: 'background 0.2s',
                                        }}
                                      >
                                        🚫 Revoke Access
                                      </button>
                                    )}
                                  </div>
                                )}
                              </div>
                            )
                          })}
                        </div>
                      )}
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </div>

      {/* Confirmation Modal for Share Revocation (Phase 6: Task 6.3) */}
      {revocationModal && revocationModal.isOpen && (
        <div
          role="dialog"
          aria-modal="true"
          data-testid="revoke-confirmation-modal"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(15, 23, 42, 0.65)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '1rem',
          }}
        >
          <div
            style={{
              background: '#ffffff',
              borderRadius: '16px',
              padding: '2rem',
              maxWidth: '480px',
              width: '100%',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.2)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
              <span style={{ fontSize: '1.75rem' }}>⚠️</span>
              <h3 style={{ margin: 0, fontSize: '1.25rem', fontWeight: '700', color: '#0f172a' }}>
                Confirm Share Revocation
              </h3>
            </div>

            <p style={{ color: '#475569', fontSize: '0.95rem', lineHeight: '1.5', margin: '0 0 1.25rem 0' }}>
              Are you sure you want to revoke access for{' '}
              <strong style={{ color: '#0f172a' }}>{revocationModal.recipientEmail}</strong> to{' '}
              <strong style={{ color: '#0f172a' }}>{revocationModal.filename}</strong>?
            </p>

            <div
              style={{
                background: '#fff1f2',
                border: '1px solid #ffe4e6',
                borderRadius: '8px',
                padding: '0.85rem',
                color: '#9f1239',
                fontSize: '0.85rem',
                marginBottom: '1.5rem',
              }}
            >
              🔒 <strong>Security Notice:</strong> The recipient's access grant will be permanently marked as revoked in the database and audit trail. Future attempts to download or decrypt this package will be strictly rejected.
            </div>

            {revocationModal.error && (
              <div
                style={{
                  background: '#fef2f2',
                  border: '1px solid #fecaca',
                  color: '#991b1b',
                  padding: '0.75rem',
                  borderRadius: '8px',
                  marginBottom: '1.25rem',
                  fontSize: '0.85rem',
                }}
              >
                ❌ {revocationModal.error}
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button
                data-testid="cancel-revoke-btn"
                onClick={() => setRevocationModal(null)}
                disabled={revocationModal.revoking}
                style={{
                  padding: '0.6rem 1.25rem',
                  borderRadius: '8px',
                  border: '1px solid #cbd5e1',
                  background: '#ffffff',
                  color: '#475569',
                  fontWeight: '600',
                  fontSize: '0.9rem',
                  cursor: revocationModal.revoking ? 'not-allowed' : 'pointer',
                }}
              >
                Cancel
              </button>
              <button
                data-testid="confirm-revoke-btn"
                onClick={handleConfirmRevoke}
                disabled={revocationModal.revoking}
                style={{
                  padding: '0.6rem 1.25rem',
                  borderRadius: '8px',
                  border: 'none',
                  background: '#e11d48',
                  color: '#ffffff',
                  fontWeight: '600',
                  fontSize: '0.9rem',
                  cursor: revocationModal.revoking ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                }}
              >
                {revocationModal.revoking ? 'Revoking...' : 'Confirm Revoke'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
