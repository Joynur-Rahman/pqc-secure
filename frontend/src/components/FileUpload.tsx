import React, { useState } from 'react'
import { fileService } from '../services/api'

interface FileUploadProps {
  onSuccess?: (packageId: string) => void
}

export const FileUpload: React.FC<FileUploadProps> = ({ onSuccess }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [recipientInput, setRecipientInput] = useState<string>('')
  const [recipientEmails, setRecipientEmails] = useState<string[]>([])
  const [encryptionMode, setEncryptionMode] = useState<'pqc' | 'classical'>('pqc')

  // Progress and status states
  const [isProcessing, setIsProcessing] = useState<boolean>(false)
  const [progressStage, setProgressStage] = useState<string>('')
  const [progressPercent, setProgressPercent] = useState<number>(0)
  const [error, setError] = useState<string | null>(null)
  const [successPackageId, setSuccessPackageId] = useState<string | null>(null)

  const MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024 // 500 MB

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null)
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0]
      if (file.size > MAX_FILE_SIZE_BYTES) {
        setError(`File size exceeds maximum allowed 500 MB limit (${(file.size / (1024 * 1024)).toFixed(1)} MB).`)
        setSelectedFile(null)
        return
      }
      setSelectedFile(file)
    }
  }

  const handleAddRecipient = () => {
    const email = recipientInput.trim().toLowerCase()
    if (!email) return

    // Simple email regex validation
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError('Please enter a valid email address.')
      return
    }

    if (recipientEmails.includes(email)) {
      setError('Recipient is already in the list.')
      return
    }

    if (recipientEmails.length >= 10) {
      setError('Maximum 10 recipients allowed per share.')
      return
    }

    setRecipientEmails([...recipientEmails, email])
    setRecipientInput('')
    setError(null)
  }

  const handleRemoveRecipient = (emailToRemove: string) => {
    setRecipientEmails(recipientEmails.filter((e) => e !== emailToRemove))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedFile) {
      setError('Please select a file to encrypt and share.')
      return
    }

    if (recipientEmails.length === 0) {
      setError('Please add at least one recipient email address.')
      return
    }

    setIsProcessing(true)
    setError(null)
    setProgressStage('Uploading file payload...')
    setProgressPercent(25)

    try {
      // Step 1: Upload file to staging
      const uploadRes = await fileService.upload(selectedFile)
      if (uploadRes.error || !uploadRes.data?.upload_id) {
        throw new Error(uploadRes.error || 'Failed to upload file.')
      }

      const uploadId = uploadRes.data.upload_id
      setProgressStage('Orchestrating PQC key encapsulation & AES-GCM encryption...')
      setProgressPercent(65)

      // Step 2: Share and encrypt file
      const shareRes = await fileService.share(uploadId, recipientEmails, encryptionMode)
      if (shareRes.error || !shareRes.data) {
        throw new Error(shareRes.error || 'Encryption and sharing failed.')
      }

      setProgressStage('Package manifest signed and stored!')
      setProgressPercent(100)

      const pkgId = shareRes.data.id || (shareRes.data as any).package_id
      setSuccessPackageId(pkgId)
      if (onSuccess) onSuccess(pkgId)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred during encryption.')
      setProgressStage('')
      setProgressPercent(0)
    } finally {
      setIsProcessing(false)
    }
  }

  const handleReset = () => {
    setSelectedFile(null)
    setRecipientEmails([])
    setRecipientInput('')
    setSuccessPackageId(null)
    setError(null)
    setProgressStage('')
    setProgressPercent(0)
  }

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '24px' }}>
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '26px', fontWeight: '600', margin: '0 0 8px 0' }}>
          Post-Quantum File Encryption & Sharing
        </h2>
        <p style={{ color: 'var(--text, #6b6375)', fontSize: '15px' }}>
          Encrypt files with AES-256-GCM and bind recipients using ML-KEM-768 or X25519.
        </p>
      </div>

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

      {successPackageId ? (
        <div
          style={{
            background: 'rgba(34, 197, 94, 0.1)',
            border: '1px solid #22c55e',
            borderRadius: '8px',
            padding: '24px',
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: '40px', marginBottom: '12px' }}>🔒</div>
          <h3 style={{ margin: '0 0 8px 0', color: '#16a34a' }}>File Encrypted & Shared Successfully!</h3>
          <p style={{ color: 'var(--text, #6b6375)', fontSize: '14px', marginBottom: '16px' }}>
            Package ID: <code style={{ fontWeight: 'bold' }}>{successPackageId}</code>
          </p>
          <div style={{ marginBottom: '20px', fontSize: '14px' }}>
            Shared with: {recipientEmails.join(', ')} ({encryptionMode.toUpperCase()} mode)
          </div>
          <button
            type="button"
            onClick={handleReset}
            style={{
              padding: '10px 20px',
              borderRadius: '6px',
              border: 'none',
              background: 'var(--accent, #aa3bff)',
              color: '#fff',
              fontWeight: '600',
              cursor: 'pointer',
            }}
          >
            Upload Another File
          </button>
        </div>
      ) : (
        <form
          id="file-upload-form"
          onSubmit={handleSubmit}
          style={{
            background: 'var(--code-bg, #f9f9f9)',
            border: '1px solid var(--border, #e5e4e7)',
            borderRadius: '8px',
            padding: '24px',
          }}
        >
          {/* File Selector */}
          <div style={{ marginBottom: '24px' }}>
            <label htmlFor="file-input" style={{ display: 'block', fontWeight: '600', marginBottom: '8px' }}>
              Select File to Encrypt (Up to 500 MB)
            </label>
            <div
              style={{
                border: '2px dashed var(--border, #ccc)',
                borderRadius: '8px',
                padding: '24px',
                textAlign: 'center',
                background: 'var(--bg, #fff)',
              }}
            >
              <input
                id="file-input"
                type="file"
                onChange={handleFileChange}
                disabled={isProcessing}
                style={{ display: 'none' }}
              />
              <label
                htmlFor="file-input"
                style={{
                  display: 'inline-block',
                  padding: '8px 16px',
                  borderRadius: '6px',
                  background: 'var(--accent, #aa3bff)',
                  color: '#fff',
                  cursor: isProcessing ? 'not-allowed' : 'pointer',
                  fontWeight: '500',
                  marginBottom: '10px',
                }}
              >
                Choose File
              </label>
              {selectedFile ? (
                <div style={{ marginTop: '8px', fontSize: '14px', color: 'var(--text-h, #000)' }}>
                  Selected: <strong>{selectedFile.name}</strong> ({(selectedFile.size / 1024).toFixed(1)} KB)
                </div>
              ) : (
                <p style={{ color: 'var(--text, #888)', fontSize: '13px' }}>
                  Drag & drop your file here or click to browse
                </p>
              )}
            </div>
          </div>

          {/* Encryption Mode Selector */}
          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', fontWeight: '600', marginBottom: '8px' }}>
              Cryptographic Encryption Mode
            </label>
            <div style={{ display: 'flex', gap: '12px' }}>
              <div
                onClick={() => setEncryptionMode('pqc')}
                style={{
                  flex: 1,
                  padding: '14px',
                  borderRadius: '6px',
                  border: `2px solid ${encryptionMode === 'pqc' ? 'var(--accent, #aa3bff)' : 'var(--border, #ccc)'}`,
                  background: encryptionMode === 'pqc' ? 'rgba(170, 59, 255, 0.08)' : 'var(--bg, #fff)',
                  cursor: 'pointer',
                }}
              >
                <div style={{ fontWeight: '600', color: encryptionMode === 'pqc' ? 'var(--accent, #aa3bff)' : 'inherit' }}>
                  🛡️ Post-Quantum Mode (Recommended)
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text, #666)', marginTop: '4px' }}>
                  ML-KEM-768 key encapsulation + ML-DSA-65 manifest signature (Quantum-resistant)
                </div>
              </div>

              <div
                onClick={() => setEncryptionMode('classical')}
                style={{
                  flex: 1,
                  padding: '14px',
                  borderRadius: '6px',
                  border: `2px solid ${encryptionMode === 'classical' ? 'var(--accent, #aa3bff)' : 'var(--border, #ccc)'}`,
                  background: encryptionMode === 'classical' ? 'rgba(59, 130, 246, 0.08)' : 'var(--bg, #fff)',
                  cursor: 'pointer',
                }}
              >
                <div style={{ fontWeight: '600', color: encryptionMode === 'classical' ? '#2563eb' : 'inherit' }}>
                  ⚡ Classical Mode
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text, #666)', marginTop: '4px' }}>
                  X25519 ECDH key agreement + Ed25519 signature
                </div>
              </div>
            </div>
          </div>

          {/* Recipient Multi-Selector */}
          <div style={{ marginBottom: '24px' }}>
            <label htmlFor="recipient-input" style={{ display: 'block', fontWeight: '600', marginBottom: '8px' }}>
              Recipients ({recipientEmails.length}/10)
            </label>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '10px' }}>
              <input
                id="recipient-input"
                type="email"
                value={recipientInput}
                onChange={(e) => setRecipientInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    handleAddRecipient()
                  }
                }}
                disabled={isProcessing}
                placeholder="recipient@example.com"
                style={{
                  flex: 1,
                  padding: '10px',
                  borderRadius: '6px',
                  border: '1px solid var(--border, #ccc)',
                  background: 'var(--bg, #fff)',
                }}
              />
              <button
                id="btn-add-recipient"
                type="button"
                onClick={handleAddRecipient}
                disabled={isProcessing}
                style={{
                  padding: '10px 16px',
                  borderRadius: '6px',
                  border: '1px solid var(--border, #ccc)',
                  background: 'var(--bg, #fff)',
                  cursor: 'pointer',
                  fontWeight: '500',
                }}
              >
                + Add
              </button>
            </div>

            {/* Recipient Pills */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {recipientEmails.map((email) => (
                <span
                  key={email}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '4px 10px',
                    borderRadius: '16px',
                    background: 'var(--accent-bg, rgba(170, 59, 255, 0.15))',
                    color: 'var(--text-h, #000)',
                    fontSize: '13px',
                  }}
                >
                  {email}
                  <button
                    type="button"
                    onClick={() => handleRemoveRecipient(email)}
                    style={{
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      fontSize: '14px',
                      color: '#dc2626',
                    }}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          </div>

          {/* Progress Display */}
          {isProcessing && (
            <div style={{ marginBottom: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '6px' }}>
                <span>{progressStage}</span>
                <span>{progressPercent}%</span>
              </div>
              <div style={{ width: '100%', height: '8px', background: '#e5e7eb', borderRadius: '4px', overflow: 'hidden' }}>
                <div
                  style={{
                    width: `${progressPercent}%`,
                    height: '100%',
                    background: 'var(--accent, #aa3bff)',
                    transition: 'width 0.3s ease',
                  }}
                />
              </div>
            </div>
          )}

          {/* Submit Button */}
          <button
            id="btn-share-submit"
            type="submit"
            disabled={isProcessing || !selectedFile || recipientEmails.length === 0}
            style={{
              width: '100%',
              padding: '14px',
              borderRadius: '6px',
              border: 'none',
              background: 'var(--accent, #aa3bff)',
              color: '#fff',
              fontSize: '16px',
              fontWeight: '600',
              cursor: isProcessing || !selectedFile || recipientEmails.length === 0 ? 'not-allowed' : 'pointer',
              opacity: isProcessing || !selectedFile || recipientEmails.length === 0 ? 0.6 : 1,
            }}
          >
            {isProcessing ? 'Encrypting & Sharing File...' : 'Encrypt & Share File'}
          </button>
        </form>
      )}
    </div>
  )
}
