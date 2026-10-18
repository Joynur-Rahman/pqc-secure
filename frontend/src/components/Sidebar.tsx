import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

interface NavItem {
  label: string
  path: string
  icon: (active: boolean) => React.ReactNode
}

const NAV_ITEMS: NavItem[] = [
  {
    label: 'Dashboard',
    path: '/dashboard',
    icon: (active) => (
      <svg className={`w-4 h-4 shrink-0 ${active ? 'text-emerald-400' : 'text-neutral-400'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z" />
      </svg>
    ),
  },
  {
    label: 'Upload File',
    path: '/files/upload',
    icon: (active) => (
      <svg className={`w-4 h-4 shrink-0 ${active ? 'text-emerald-400' : 'text-neutral-400'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
      </svg>
    ),
  },
  {
    label: 'Shared Files',
    path: '/shared-files',
    icon: (active) => (
      <svg className={`w-4 h-4 shrink-0 ${active ? 'text-emerald-400' : 'text-neutral-400'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
  },
  {
    label: 'Manage Keys',
    path: '/keys',
    icon: (active) => (
      <svg className={`w-4 h-4 shrink-0 ${active ? 'text-emerald-400' : 'text-neutral-400'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
      </svg>
    ),
  },
  {
    label: 'Performance',
    path: '/perf',
    icon: (active) => (
      <svg className={`w-4 h-4 shrink-0 ${active ? 'text-emerald-400' : 'text-neutral-400'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
  },
]

export default function Sidebar() {
  const { user } = useAuth()
  const location = useLocation()

  if (!user) {
    return null
  }

  const isActive = (path: string) => location.pathname === path

  return (
    <aside data-ui="sidebar" className="w-60 bg-[#0c0d0e] border-r border-white/[0.08] flex flex-col justify-between py-4 shrink-0">
      <nav className="flex flex-col space-y-1 px-2">
        <div className="px-3 py-1.5 text-xs font-semibold text-neutral-400">
          Navigation
        </div>
        {NAV_ITEMS.map((item) => {
          const active = isActive(item.path)
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center px-3 py-2 text-xs font-medium rounded-md transition-colors ${
                active
                  ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/30'
                  : 'text-neutral-400 hover:text-white hover:bg-white/[0.04]'
              }`}
            >
              <span className="mr-2.5 flex items-center justify-center">{item.icon(active)}</span>
              {item.label}
            </Link>
          )
        })}
      </nav>

      <div className="px-4 pt-4 space-y-3">
        <div className="p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.05] space-y-1.5">
          <div className="flex items-center justify-between text-xs font-medium text-neutral-400">
            <span>Security Mode</span>
            <span className="pqc-dot-pulse"></span>
          </div>
          <div className="text-xs font-medium text-emerald-400 flex items-center space-x-1.5">
            <span>FIPS 203/204</span>
            <span className="text-[10px] text-neutral-400">PQC Active</span>
          </div>
        </div>

        <div>
          <div className="text-xs font-medium text-neutral-400 mb-1">Signed in as</div>
          <p className="text-xs text-neutral-300 truncate" title={user.email}>
            <code>{user.email}</code>
          </p>
        </div>
      </div>
    </aside>
  )
}
