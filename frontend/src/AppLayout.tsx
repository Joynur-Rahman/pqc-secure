import { Outlet } from 'react-router-dom'
import Header from './components/Header'
import Sidebar from './components/Sidebar'
import Footer from './components/Footer'
import { useAuth } from './hooks/useAuth'
import ErrorBoundary from './components/ErrorBoundary'

export default function AppLayout() {
  const { user } = useAuth()

  return (
    <div className="flex flex-col min-h-svh pqc-bg-ambient text-[#f7f8f8] relative overflow-x-hidden selection:bg-emerald-500/30 selection:text-emerald-200">
      <div className="pqc-hero-glow" />
      <Header />
      <div className="flex flex-1">
        {user && <Sidebar />}
        <main className={`flex-1 ${user ? 'px-4 py-8 sm:px-6 lg:px-8' : 'max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8 w-full'}`}>
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
      <Footer />
    </div>
  )
}
