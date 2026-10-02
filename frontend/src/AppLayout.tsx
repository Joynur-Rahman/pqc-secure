import { Outlet } from 'react-router-dom'
import Header from './components/Header'
import Sidebar from './components/Sidebar'
import Footer from './components/Footer'
import { useAuth } from './hooks/useAuth'

export default function AppLayout() {
  const { user } = useAuth()

  return (
    <div className="flex flex-col min-h-screen bg-gray-50">
      <Header />
      <div className="flex flex-1">
        {user && <Sidebar />}
        <main className={`flex-1 ${user ? 'px-4 py-8 sm:px-6 lg:px-8' : 'max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8 w-full'}`}>
          <Outlet />
        </main>
      </div>
      <Footer />
    </div>
  )
}
