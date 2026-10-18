import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function Header() {
  const { user, logout } = useAuth()

  return (
    <header className="bg-[#0c0d0e]/95 border-b border-white/[0.08] sticky top-0 z-40" data-ui="main-header">
      <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center">
          <Link to="/" className="flex items-center space-x-3 group">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 group-hover:border-emerald-400/50 transition-colors">
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                <path d="M12 8v4"/>
                <path d="M12 16h.01"/>
              </svg>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-xl font-semibold tracking-tight text-white group-hover:text-emerald-200 transition-colors">PQC Secure</h1>
                <span className="pqc-badge pqc-badge-quantum">ML-KEM / ML-DSA</span>
              </div>
              <p className="text-xs text-neutral-400 hidden sm:block">
                Post-Quantum Cryptography File Sharing
              </p>
            </div>
          </Link>
          
          <nav className="flex items-center space-x-4 sm:space-x-6">
            {user ? (
              <>
                <div className="hidden md:flex items-center space-x-2 px-2.5 py-1 rounded-md bg-white/[0.03] border border-white/[0.06] text-xs text-neutral-300">
                  <span className="pqc-dot-pulse"></span>
                  <span className="pqc-mono text-neutral-400 truncate max-w-[160px]">{user.email}</span>
                </div>
                <Link
                  to="/dashboard"
                  className="text-sm font-medium text-neutral-300 hover:text-white transition-colors"
                >
                  Dashboard
                </Link>
                <Link
                  to="/keys"
                  className="text-sm font-medium text-neutral-300 hover:text-white transition-colors"
                >
                  Keys
                </Link>
                <button
                  onClick={logout}
                  className="pqc-btn-danger text-xs py-1.5 px-3"
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  className="text-sm font-medium text-neutral-300 hover:text-white transition-colors"
                >
                  Login
                </Link>
                <Link
                  to="/register"
                  className="pqc-btn-primary text-xs py-1.5 px-3.5"
                >
                  Register
                </Link>
              </>
            )}
          </nav>
        </div>
      </div>
    </header>
  )
}
