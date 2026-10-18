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
    <div data-ui="file-list" className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      {/* Header Banner */}
      <div className="pqc-card p-6 bg-[#0c0d0e] border border-white/[0.08]">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5 mb-1.5">
              <svg className="w-5 h-5 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              <h1 className="text-xl sm:text-2xl font-semibold tracking-tight text-white">
                Shared Files & Access Control
              </h1>
              <span className="pqc-badge pqc-badge-quantum text-[10px] py-0.5">Encrypted Store</span>
            </div>
            <p className="text-xs text-neutral-400">
              Manage post-quantum packages, grant share revocations, and authenticate end-to-end decryptions.
            </p>
          </div>
          <button
            onClick={loadFiles}
            disabled={loading}
            className="pqc-btn-secondary text-xs py-1.5 px-3.5 self-start sm:self-auto shrink-0"
          >
            {loading ? 'Refreshing...' : '↻ Refresh'}
          </button>
        </div>
      </div>

      {/* Success Notification Banner */}
      {successToast && (
        <div
          data-testid="success-toast"
          className="p-3.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center justify-between"
        >
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span>{successToast}</span>
          </div>
          <button
            onClick={() => setSuccessToast(null)}
            className="text-emerald-400 hover:text-emerald-200 font-bold ml-2 cursor-pointer"
          >
            ×
          </button>
        </div>
      )}

      {/* Global Error Banner */}
      {error && (
        <div
          data-testid="error-banner"
          className="p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2"
        >
          <svg className="w-4 h-4 text-rose-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span>{error}</span>
        </div>
      )}

      {/* Files List Container */}
      <div className="pqc-card overflow-hidden">
        <div className="px-5 py-3.5 bg-[#0c0d0e]/80 flex items-center justify-between">
          <h2 className="text-xs font-semibold text-neutral-300">
            Available Encrypted Packages ({files.length})
          </h2>
          <span className="text-[11px] text-neutral-400 font-medium">Zero-Trust Manifests</span>
        </div>

        {loading ? (
          <div className="text-center py-12 space-y-2 text-xs text-neutral-400">
            <span className="pqc-dot-pulse inline-block"></span>
            <p className="font-medium">Loading shared packages...</p>
          </div>
        ) : files.length === 0 ? (
          <div
            data-testid="no-files-message"
            className="text-center py-14 space-y-2"
          >
            <div className="w-10 h-10 mx-auto rounded-lg bg-white/[0.02] border border-white/[0.06] flex items-center justify-center text-neutral-400 mb-2">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
              </svg>
            </div>
            <h3 className="text-xs font-semibold text-neutral-300">
              No shared files found
            </h3>
            <p className="text-xs text-neutral-400 max-w-sm mx-auto">
              Files encrypted for you or sent by your account will appear here.
            </p>
          </div>
        ) : (
          <ul className="space-y-1">
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
                  className="p-5 flex flex-col gap-3 hover:bg-white/[0.02] transition-colors"
                >
                  <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                    <div className="flex items-start gap-3.5">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 border ${
                        isPqc
                          ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                          : 'bg-amber-500/10 border-amber-500/20 text-amber-400'
                      }`}>
                        {isPqc ? (
                          <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                          </svg>
                        ) : (
                          <svg className="w-5 h-5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                          </svg>
                        )}
                      </div>
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span
                            data-testid={`filename-${pkgId}`}
                            className="text-sm font-semibold text-white tracking-tight"
                          >
                            {file.original_filename || `Package-${pkgId.slice(0, 8)}`}
                          </span>
                          <span className={`pqc-badge ${isPqc ? 'pqc-badge-quantum' : 'pqc-badge-warning'} text-[10px] py-0.5`}>
                            {isPqc ? 'NIST PQC (ML-KEM / ML-DSA)' : 'Classical (X25519 / Ed25519)'}
                          </span>
                          {isSender && (
                            <span
                              data-testid={`sender-badge-${pkgId}`}
                              className="pqc-badge pqc-badge-subtle text-[10px] py-0.5"
                            >
                              Sent by you
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] text-neutral-400 flex flex-wrap items-center gap-2">
                          <span>Sender: <code className="text-neutral-300 font-medium">{file.sender_email || 'Authenticated User'}</code></span>
                          <span>•</span>
                          <span>Size: <code className="text-neutral-300 font-medium">{formatFileSize(file.file_size)}</code></span>
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
                      className="pqc-btn-primary text-xs py-2 px-4 shrink-0 flex items-center gap-1.5"
                    >
                      {status.downloading ? (
                        <>
                          <span className="pqc-dot-pulse"></span>
                          <span>Decrypting...</span>
                        </>
                      ) : (
                        <>
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                          </svg>
                          <span>Decrypt & Download</span>
                        </>
                      )}
                    </button>
                  </div>

                  {/* Decryption Status / Error Bar */}
                  {status.downloading && (
                    <div
                      data-testid={`progress-${pkgId}`}
                      className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2"
                    >
                      <span className="pqc-dot-pulse"></span>
                      <span>{status.progress}</span>
                    </div>
                  )}

                  {status.success && (
                    <div
                      data-testid={`success-${pkgId}`}
                      className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2"
                    >
                      <svg className="w-4 h-4 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span>{status.progress}</span>
                    </div>
                  )}

                  {status.error && (
                    <div
                      data-testid={`error-${pkgId}`}
                      className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2"
                    >
                      <svg className="w-4 h-4 text-rose-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                      <span>{status.error}</span>
                    </div>
                  )}

                  {/* Recipient Access Management Section (Phase 6: Task 6.3) */}
                  {recipients.length > 0 && (
                    <div className="mt-1 bg-[#0c0d0e]/60 border border-white/[0.06] rounded-lg p-3 space-y-2">
                      <div
                        className="flex justify-between items-center cursor-pointer select-none"
                        onClick={() => toggleRecipients(pkgId)}
                      >
                        <div className="flex items-center gap-2">
                          <svg className="w-4 h-4 text-neutral-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                          </svg>
                          <span className="text-xs font-semibold text-neutral-300">
                            Recipients & Access Control ({recipients.length})
                          </span>
                        </div>
                        <span className="text-[11px] text-neutral-400">
                          {isExpanded ? '▲ Hide' : '▼ Show'}
                        </span>
                      </div>

                      {isExpanded && (
                        <div className="space-y-1.5 pt-1">
                          {recipients.map((rec) => {
                            const isRevoked = rec.status === 'revoked'
                            const grantId = rec.grant_id || rec.recipient_id

                            return (
                              <div
                                key={grantId}
                                data-testid={`recipient-row-${grantId}`}
                                className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 p-2 rounded bg-white/[0.02] border border-white/[0.04]"
                              >
                                <div className="flex flex-wrap items-center gap-2">
                                  <code className="text-xs text-neutral-200">
                                    {rec.recipient_email || `Recipient ID: ${rec.recipient_id.slice(0, 8)}`}
                                  </code>

                                  {/* Status badge */}
                                  <span
                                    data-testid={isRevoked ? `status-badge-revoked-${grantId}` : `status-badge-active-${grantId}`}
                                    className={`pqc-badge ${isRevoked ? 'pqc-badge-danger' : 'pqc-badge-quantum'} text-[10px] py-0 px-2`}
                                  >
                                    {isRevoked ? 'REVOKED' : 'ACTIVE'}
                                  </span>

                                  {isRevoked && rec.revoked_at && (
                                    <span className="text-[11px] text-neutral-400">
                                      (Revoked: {formatDate(rec.revoked_at)})
                                    </span>
                                  )}
                                </div>

                                {/* Revoke button for Sender */}
                                {isSender && (
                                  <div>
                                    {isRevoked ? (
                                      <span className="text-xs text-neutral-400 italic">
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
                                        className="pqc-btn-danger text-[11px] py-0.5 px-2 flex items-center gap-1"
                                      >
                                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                                        </svg>
                                        <span>Revoke Access</span>
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
          className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50"
        >
          <div className="pqc-card pqc-card-elevated max-w-md w-full p-6 space-y-4">
            <div className="flex items-center gap-2 text-rose-400">
              <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <h3 className="text-sm font-semibold text-white">
                Confirm Share Revocation
              </h3>
            </div>

            <p className="text-xs text-neutral-300 leading-relaxed">
              Are you sure you want to revoke access for{' '}
              <code className="text-white font-medium">{revocationModal.recipientEmail}</code> to{' '}
              <strong className="text-white">{revocationModal.filename}</strong>?
            </p>

            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs leading-relaxed flex items-start gap-2">
              <svg className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              <div>
                <strong>Security Notice:</strong> The recipient's access grant will be permanently marked as revoked in the database and audit trail. Future attempts to download or decrypt this package will be strictly rejected.
              </div>
            </div>

            {revocationModal.error && (
              <div className="p-2.5 rounded-lg bg-rose-500/20 text-rose-300 text-xs flex items-center gap-1.5">
                <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                <span>{revocationModal.error}</span>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <button
                data-testid="cancel-revoke-btn"
                onClick={() => setRevocationModal(null)}
                disabled={revocationModal.revoking}
                className="pqc-btn-secondary text-xs py-1.5 px-3.5"
              >
                Cancel
              </button>
              <button
                data-testid="confirm-revoke-btn"
                onClick={handleConfirmRevoke}
                disabled={revocationModal.revoking}
                className="pqc-btn-danger text-xs py-1.5 px-3.5"
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
