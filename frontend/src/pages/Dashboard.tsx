import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { fileService } from '../services/api'

export default function Dashboard() {
  const { user } = useAuth()
  const [sharedFiles, setSharedFiles] = useState<FilePackageMetadata[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadSharedFiles()
  }, [])

  async function loadSharedFiles() {
    try {
      const result = await fileService.list()
      if (result.data) {
        const raw = result.data as any
        const list = Array.isArray(raw) ? raw : (Array.isArray(raw.packages) ? raw.packages : [])
        setSharedFiles(list)
      } else {
        setSharedFiles([])
      }
    } catch (error) {
      console.error('Failed to load shared files:', error)
      setSharedFiles([])
    } finally {
      setLoading(false)
    }
  }

  if (!user) {
    return <div>Loading...</div>
  }

  return (
    <div data-ui="dashboard" className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-semibold tracking-tight text-white flex items-center gap-2">
            Dashboard
            <span className="pqc-badge pqc-badge-quantum text-xs py-0.5">Post-Quantum Active</span>
          </h2>
          <p className="text-xs text-neutral-400 mt-1">
            Enterprise zero-trust cryptographic package management and lattice-secure file exchange.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/files/upload" className="pqc-btn-primary text-xs">
            <span>+ Encrypt & Upload</span>
          </Link>
        </div>
      </div>

      {/* Quick Action Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Link
          to="/files/upload"
          className="pqc-card pqc-card-interactive p-5 block group"
        >
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-3 text-emerald-400 group-hover:border-emerald-500/40 transition-colors">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
          </div>
          <h3 className="text-sm font-semibold text-white group-hover:text-emerald-300 transition-colors">Upload File</h3>
          <p className="text-xs text-neutral-400 mt-1 line-clamp-2 leading-relaxed">
            Encrypt and share packages with ML-KEM-768 key encapsulation.
          </p>
        </Link>

        <Link
          to="/keys"
          className="pqc-card pqc-card-interactive p-5 block group"
        >
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-3 text-emerald-400 group-hover:border-emerald-500/40 transition-colors">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
            </svg>
          </div>
          <h3 className="text-sm font-semibold text-white group-hover:text-emerald-300 transition-colors">Manage Keys</h3>
          <p className="text-xs text-neutral-400 mt-1 line-clamp-2 leading-relaxed">
            Register, rotate, or revoke ML-KEM and ML-DSA cryptographic keys.
          </p>
        </Link>

        <Link
          to="/shared-files"
          className="pqc-card pqc-card-interactive p-5 block group"
        >
          <div className="w-10 h-10 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center mb-3 text-cyan-400 group-hover:border-cyan-500/40 transition-colors">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h3 className="text-sm font-semibold text-white group-hover:text-cyan-300 transition-colors">Shared Files</h3>
          <p className="text-xs text-neutral-400 mt-1 line-clamp-2 leading-relaxed">
            Access, verify lattice signatures, and decrypt incoming packages.
          </p>
        </Link>

        <Link
          to="/perf"
          className="pqc-card pqc-card-interactive p-5 block group"
        >
          <div className="w-10 h-10 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mb-3 text-amber-400 group-hover:border-amber-500/40 transition-colors">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <h3 className="text-sm font-semibold text-white group-hover:text-amber-300 transition-colors">Performance</h3>
          <p className="text-xs text-neutral-400 mt-1 line-clamp-2 leading-relaxed">
            Run benchmarks & compare PQC vs Classical primitive latencies.
          </p>
        </Link>
      </div>

      {/* Shared Files Section */}
      <div className="pqc-card overflow-hidden">
        <div className="px-5 py-3.5 bg-[#0c0d0e]/80 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-xs font-semibold text-neutral-300">Shared Files</h3>
            <span className="pqc-badge pqc-badge-subtle text-[10px] py-0 px-2">{sharedFiles.length} packages</span>
          </div>
          <Link to="/shared-files" className="text-xs text-emerald-400 hover:text-emerald-300 font-medium transition-colors">
            View All →
          </Link>
        </div>
        <div className="p-5">
          {loading ? (
            <div className="flex items-center justify-center py-10 space-x-2 text-xs text-neutral-400">
              <span className="pqc-dot-pulse"></span>
              <span>Loading encrypted packages...</span>
            </div>
          ) : sharedFiles.length === 0 ? (
            <div className="text-center py-10 space-y-2">
              <div className="w-10 h-10 mx-auto rounded-lg bg-white/[0.02] border border-white/[0.06] flex items-center justify-center text-neutral-400 mb-2">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                </svg>
              </div>
              <p className="text-xs font-medium text-neutral-300">No shared files yet.</p>
              <p className="text-xs text-neutral-400 max-w-sm mx-auto">
                Encrypted file packages shared with your public key will appear here for client-side decryption.
              </p>
            </div>
          ) : (
            <ul className="space-y-1">
              {sharedFiles.map((file: any) => {
                const pkgId = file.id || file.package_id
                const fileName = file.fileName || file.original_filename || 'Encrypted File'
                const sender = file.senderEmail || file.sender_email || 'Unknown'
                const size = file.fileSize || file.file_size || 0
                const createdAt = file.createdAt || file.created_at
                return (
                  <li key={pkgId} className="flex justify-between items-center py-3 px-1 hover:bg-white/[0.02] rounded-md transition-colors">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <p className="text-xs font-medium text-white">{fileName}</p>
                        <span className="pqc-badge pqc-badge-quantum text-[10px] py-0 px-1.5">ML-KEM-768</span>
                      </div>
                      <p className="text-[11px] text-neutral-400">
                        From <span className="text-neutral-300">{sender}</span> • <code>{formatFileSize(size)}</code> • {formatDate(createdAt)}
                      </p>
                    </div>
                    <Link
                      to="/shared-files"
                      className="pqc-btn-secondary text-xs py-1 px-3"
                    >
                      View
                    </Link>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(dateString?: string): string {
  if (!dateString) return 'Recent'
  try {
    const d = new Date(dateString)
    if (isNaN(d.getTime())) return 'Recent'
    return d.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  } catch {
    return 'Recent'
  }
}
