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
        setSharedFiles(result.data)
      }
    } catch (error) {
      console.error('Failed to load shared files:', error)
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

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
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
              {sharedFiles.map((file) => (
                <li key={file.id} className="flex justify-between items-center py-3 border-b border-gray-100">
                  <div>
                    <p className="font-medium text-gray-900">{file.fileName}</p>
                    <p className="text-sm text-gray-500">
                      {file.senderEmail} • {formatFileSize(file.fileSize)} • {formatDate(file.createdAt)}
                    </p>
                  </div>
                  <Link
                    to={`/files/${file.id}`}
                    className="text-blue-600 hover:text-blue-800 font-medium"
                  >
                    View
                  </Link>
                </li>
              ))}
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

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}
