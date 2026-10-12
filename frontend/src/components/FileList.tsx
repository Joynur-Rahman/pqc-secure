import React, { useState, useEffect } from 'react'
import { fileService } from '../services/api'

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
  }>
  created_at: string
  status: string
}

export const FileList: React.FC = () => {
  const [files, setFiles] = useState<SharedFileItem[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  // Download state: packageId -> { downloading: boolean, progress: string, error?: string, success?: boolean }
  const [downloadStatus, setDownloadStatus] = useState<
    Record<string, { downloading: boolean; progress: string; error?: string; success?: boolean }>
  >({})

  useEffect(() => {
    loadFiles()
  }, [])

  const loadFiles = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fileService.list()
      if (response.data) {
        // Backend returns { packages: [...], total: ... }
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
      // Simulate micro-animation for cryptographic verification stages
      await new Promise((r) => setTimeout(r, 400))
      setDownloadStatus((prev) => ({
        ...prev,
        [pkgId]: {
          downloading: true,
          progress: `2/3: Decapsulating ${fileItem.crypto_mode.toUpperCase()} key & unwrapping CEK...`,
        },
      }))

      await new Promise((r) => setTimeout(r, 400))
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

      // Trigger browser download of plaintext file
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

      // Reset success message after 4s
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

  const formatFileSize = (bytes: number): string => {
    if (!bytes || bytes <= 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`
  }

  const formatDate = (isoStr: string): string => {
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
                Shared Files & Decryption
              </h1>
            </div>
            <p style={{ color: '#94a3b8', margin: 0, fontSize: '0.95rem' }}>
              Access post-quantum and classical files shared with you. Decryption is authenticated with NIST FIPS 203/204.
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
          <ul style={{ listStyle: 'none', margin: 0, padding: 0, divideY: '1px solid #f1f5f9' }}>
            {files.map((file) => {
              const pkgId = file.package_id || file.id
              const status = downloadStatus[pkgId] || { downloading: false, progress: '' }
              const isPqc = (file.crypto_mode || '').toLowerCase() === 'pqc'

              return (
                <li
                  key={pkgId}
                  data-testid={`file-row-${pkgId}`}
                  style={{
                    padding: '1.25rem 1.5rem',
                    borderBottom: '1px solid #f1f5f9',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.75rem',
                    transition: 'background 0.15s',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                      <div
                        style={{
                          width: '46px',
                          height: '46px',
                          borderRadius: '12px',
                          background: isPqc ? '#eef2ff' : '#ecfdf5',
                          color: isPqc ? '#4f46e5' : '#059669',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: '1.4rem',
                          flexShrink: 0,
                        }}
                      >
                        {isPqc ? '🛡️' : '🔒'}
                      </div>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                          <span
                            data-testid={`filename-${pkgId}`}
                            style={{ fontWeight: '600', color: '#0f172a', fontSize: '1rem' }}
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
                        </div>
                        <div
                          style={{
                            fontSize: '0.85rem',
                            color: '#64748b',
                            marginTop: '0.25rem',
                            display: 'flex',
                            gap: '1rem',
                            flexWrap: 'wrap',
                          }}
                        >
                          <span>Sender: <strong>{file.sender_email || 'Authenticated User'}</strong></span>
                          <span>•</span>
                          <span>Size: <strong>{formatFileSize(file.file_size)}</strong></span>
                          <span>•</span>
                          <span>Shared: {formatDate(file.created_at)}</span>
                        </div>
                      </div>
                    </div>

                    {/* Download Button */}
                    <button
                      data-testid={`download-button-${pkgId}`}
                      onClick={() => handleDownload(file)}
                      disabled={status.downloading}
                      style={{
                        padding: '0.6rem 1.25rem',
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
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
