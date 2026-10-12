import { Routes, Route } from 'react-router-dom'
import AppLayout from './AppLayout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import KeysPage from './pages/Keys'
import UploadPage from './pages/Upload'
import NotFound from './pages/NotFound'
import ProtectedRoute from './components/ProtectedRoute'
import { AuthProvider } from './hooks/useAuth'

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<Login />} />
          <Route path="login" element={<Login />} />
          <Route path="register" element={<Register />} />
          <Route
            path="dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="keys"
            element={
              <ProtectedRoute>
                <KeysPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="files/upload"
            element={
              <ProtectedRoute>
                <UploadPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </AuthProvider>
  )
}
