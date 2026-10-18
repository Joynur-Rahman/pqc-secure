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
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Link
          to="/files/upload"
          className="block p-6 bg-white rounded-lg border border-gray-200 hover:border-blue-300 hover:shadow-md transition-all"
        >
          <div className="text-3xl mb-4">📤</div>
          <h3 className="text-lg font-semibold text-gray-900">Upload File</h3>
          <p className="text-sm text-gray-500 mt-2">
            Encrypt and share files with recipients
          </p>
        </Link>

        <Link
          to="/keys"
          className="block p-6 bg-white rounded-lg border border-gray-200 hover:border-blue-300 hover:shadow-md transition-all"
        >
          <div className="text-3xl mb-4">🔑</div>
          <h3 className="text-lg font-semibold text-gray-900">Manage Keys</h3>
          <p className="text-sm text-gray-500 mt-2">
            Register, rotate, or revoke your cryptographic keys
          </p>
        </Link>

        <Link
          to="/shared-files"
          className="block p-6 bg-white rounded-lg border border-gray-200 hover:border-blue-300 hover:shadow-md transition-all"
        >
          <div className="text-3xl mb-4">📋</div>
          <h3 className="text-lg font-semibold text-gray-900">Shared Files</h3>
          <p className="text-sm text-gray-500 mt-2">
            View and manage your shared files
          </p>
        </Link>

        <Link
          to="/perf"
          className="block p-6 bg-white rounded-lg border border-gray-200 hover:border-blue-300 hover:shadow-md transition-all"
        >
          <div className="text-3xl mb-4">⚡</div>
          <h3 className="text-lg font-semibold text-gray-900">Performance</h3>
          <p className="text-sm text-gray-500 mt-2">
            Run benchmarks & compare PQC vs Classical primitives
          </p>
        </Link>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Shared Files</h3>
        </div>
        <div className="p-6">
          {loading ? (
            <p className="text-gray-500">Loading...</p>
          ) : sharedFiles.length === 0 ? (
            <p className="text-gray-500">No shared files yet.</p>
          ) : (
            <ul className="space-y-3">
              {sharedFiles.map((file: any) => {
                const pkgId = file.id || file.package_id
                const fileName = file.fileName || file.original_filename || 'Encrypted File'
                const sender = file.senderEmail || file.sender_email || 'Unknown'
                const size = file.fileSize || file.file_size || 0
                const createdAt = file.createdAt || file.created_at
                return (
                  <li key={pkgId} className="flex justify-between items-center py-3 border-b border-gray-100">
                    <div>
                      <p className="font-medium text-gray-900">{fileName}</p>
                      <p className="text-sm text-gray-500">
                        {sender} • {formatFileSize(size)} • {formatDate(createdAt)}
                      </p>
                    </div>
                    <Link
                      to="/shared-files"
                      className="text-blue-600 hover:text-blue-800 font-medium"
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
