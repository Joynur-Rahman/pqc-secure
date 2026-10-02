import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

interface NavItem {
  label: string
  path: string
  icon: string
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', path: '/dashboard', icon: '📊' },
  { label: 'Upload File', path: '/files/upload', icon: '📤' },
  { label: 'Shared Files', path: '/shared-files', icon: '📋' },
  { label: 'Manage Keys', path: '/keys', icon: '🔑' },
]

export default function Sidebar() {
  const { user } = useAuth()
  const location = useLocation()

  if (!user) {
    return null
  }

  const isActive = (path: string) => location.pathname === path

  return (
    <aside className="w-64 bg-gray-900 text-white shadow-lg">
      <nav className="flex flex-col">
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={`flex items-center px-6 py-4 text-sm font-medium transition-colors ${
              isActive(item.path)
                ? 'bg-blue-600 border-l-4 border-blue-400'
                : 'text-gray-300 hover:bg-gray-800 hover:text-white'
            }`}
          >
            <span className="mr-3 text-lg">{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>

      <div className="border-t border-gray-700 mt-6 pt-6 px-6">
        <div className="text-xs text-gray-400 mb-2">User Info</div>
        <p className="text-sm text-gray-300 break-words">{user.email}</p>
      </div>
    </aside>
  )
}
