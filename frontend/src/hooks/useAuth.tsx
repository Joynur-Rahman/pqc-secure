import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { authService, AuthSession } from '../services/api'
import { User } from '../types'

interface AuthContextType {
  user: User | null
  session: AuthSession | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  register: (email: string, password: string) => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<AuthSession | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadSession()
  }, [])

  async function loadSession() {
    try {
      const result = await authService.getSession()
      if (result.data) {
        setSession(result.data)
        setUser(result.data.user)
      }
    } catch (error) {
      console.error('Failed to load session:', error)
    } finally {
      setLoading(false)
    }
  }

  async function login(email: string, password: string) {
    const result = await authService.login(email, password)
    if (result.data) {
      setSession(result.data)
      setUser(result.data.user)
    }
  }

  async function logout() {
    await authService.logout()
    setSession(null)
    setUser(null)
  }

  async function register(email: string, password: string) {
    await authService.register(email, password)
  }

  return (
    <AuthContext.Provider value={{ user, session, loading, login, logout, register }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
