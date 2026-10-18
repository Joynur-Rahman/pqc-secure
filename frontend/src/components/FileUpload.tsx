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
    <div data-ui="file-upload" className="max-w-3xl mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="pb-4 border-b border-white/[0.08]">
        <div className="flex items-center gap-2">
          <h2 className="text-xl sm:text-2xl font-semibold tracking-tight text-white">
            Post-Quantum File Encryption & Sharing
          </h2>
          <span className="pqc-badge pqc-badge-quantum text-[10px] py-0.5">FIPS 203 ML-KEM</span>
        </div>
        <p className="text-xs text-neutral-400 mt-1">
          Encrypt files with AES-256-GCM and bind recipients using ML-KEM-768 or X25519.
        </p>
      </div>

      {/* Error Banner */}
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

      {successPackageId ? (
        <div className="pqc-card pqc-card-quantum p-8 text-center space-y-4">
          <div className="w-14 h-14 mx-auto rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <h3 className="text-base font-semibold text-white">File Encrypted & Shared Successfully!</h3>
          <p className="text-xs text-neutral-400">
            Package ID: <code className="pqc-code-pill font-mono font-bold text-sky-300">{successPackageId}</code>
          </p>
          <div className="text-xs text-neutral-400">
            Shared with: <span className="text-neutral-200 font-medium">{recipientEmails.join(', ')}</span> ({encryptionMode.toUpperCase()} mode)
          </div>
          <button
            type="button"
            onClick={handleReset}
            className="pqc-btn-primary text-xs py-2 px-5 inline-block"
          >
            Upload Another File
          </button>
        </div>
      ) : (
        <form
          id="file-upload-form"
          onSubmit={handleSubmit}
          className="pqc-card p-6 space-y-6"
        >
          {/* File Selector */}
          <div>
            <label htmlFor="file-input" className="block text-xs font-semibold text-neutral-300 mb-2">
              Select File to Encrypt (Up to 500 MB)
            </label>
            <div className="border-2 border-dashed border-white/[0.12] hover:border-emerald-500/40 hover:bg-white/[0.02] rounded-xl p-8 text-center transition-colors bg-[#0c0d0e]/50">
              <input
                id="file-input"
                type="file"
                onChange={handleFileChange}
                disabled={isProcessing}
                className="hidden"
              />
              <label
                htmlFor="file-input"
                className={`pqc-btn-primary text-xs py-2 px-4 cursor-pointer inline-flex items-center gap-2 ${
                  isProcessing ? 'opacity-50 cursor-not-allowed' : ''
                }`}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
                <span>Choose File</span>
              </label>
              {selectedFile ? (
                <div className="mt-3 text-xs text-neutral-300 flex items-center justify-center gap-2">
                  <span>Selected: <span className="pqc-mono text-emerald-400 font-semibold">{selectedFile.name}</span> ({(selectedFile.size / 1024).toFixed(1)} KB)</span>
                </div>
              ) : (
                <p className="text-xs text-neutral-400 mt-2">
                  Drag & drop your file here or click to browse
                </p>
              )}
            </div>
          </div>

          {/* Encryption Mode Selector */}
          <div>
            <label className="block text-xs font-semibold text-neutral-300 mb-2">
              Cryptographic Encryption Mode
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div
                onClick={() => setEncryptionMode('pqc')}
                className={`p-4 rounded-lg border cursor-pointer transition-colors ${
                  encryptionMode === 'pqc'
                    ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300'
                    : 'bg-[#0c0d0e] border-white/[0.08] text-neutral-400 hover:text-white'
                }`}
              >
                <div className="text-xs font-semibold flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                    <span>Post-Quantum Mode (Recommended)</span>
                  </span>
                  {encryptionMode === 'pqc' && <span className="pqc-dot-pulse"></span>}
                </div>
                <div className="text-[11px] text-neutral-400 mt-1 leading-relaxed">
                  ML-KEM-768 key encapsulation + ML-DSA-65 manifest signature (Quantum-resistant)
                </div>
              </div>

              <div
                onClick={() => setEncryptionMode('classical')}
                className={`p-4 rounded-lg border cursor-pointer transition-colors ${
                  encryptionMode === 'classical'
                    ? 'bg-amber-500/10 border-amber-500/40 text-amber-300'
                    : 'bg-[#0c0d0e] border-white/[0.08] text-neutral-400 hover:text-white'
                }`}
              >
                <div className="text-xs font-semibold flex items-center gap-1.5">
                  <svg className="w-4 h-4 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  <span>Classical Mode</span>
                </div>
                <div className="text-[11px] text-neutral-400 mt-1 leading-relaxed">
                  X25519 ECDH key agreement + Ed25519 signature
                </div>
              </div>
            </div>
          </div>

          {/* Recipient Multi-Selector */}
          <div>
            <label htmlFor="recipient-input" className="block text-xs font-semibold text-neutral-300 mb-2">
              Recipients ({recipientEmails.length}/10)
            </label>
            <div className="flex gap-2 mb-2.5">
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
                className="pqc-input text-xs"
              />
              <button
                id="btn-add-recipient"
                type="button"
                onClick={handleAddRecipient}
                disabled={isProcessing}
                className="pqc-btn-secondary text-xs py-2 px-4 shrink-0"
              >
                + Add
              </button>
            </div>

            {/* Recipient Pills */}
            <div className="flex flex-wrap gap-2">
              {recipientEmails.map((email) => (
                <span
                  key={email}
                  className="pqc-badge pqc-badge-quantum text-xs py-1 px-2.5 flex items-center gap-1.5"
                >
                  <code>{email}</code>
                  <button
                    type="button"
                    onClick={() => handleRemoveRecipient(email)}
                    className="text-neutral-400 hover:text-rose-400 transition-colors ml-1 font-bold cursor-pointer"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          </div>

          {/* Progress Display */}
          {isProcessing && (
            <div className="space-y-2 p-3.5 rounded-lg bg-white/[0.02] border border-white/[0.06]">
              <div className="flex justify-between text-xs text-neutral-300">
                <span className="flex items-center gap-2">
                  <span className="pqc-dot-pulse"></span>
                  <span>{progressStage}</span>
                </span>
                <span className="text-emerald-400 font-medium">{progressPercent}%</span>
              </div>
              <div className="w-full h-2 bg-[#0c0d0e] rounded-full overflow-hidden border border-white/[0.08]">
                <div
                  className="h-full bg-emerald-500 transition-[width] duration-300 ease-out"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
            </div>
          )}

          {/* Submit Button */}
          <button
            id="btn-share-submit"
            type="submit"
            disabled={isProcessing || !selectedFile || recipientEmails.length === 0}
            className="pqc-btn-primary w-full py-3 text-xs font-semibold"
          >
            {isProcessing ? 'Encrypting & Sharing File...' : 'Encrypt & Share File'}
          </button>
        </form>
      )}
    </div>
  )
}
