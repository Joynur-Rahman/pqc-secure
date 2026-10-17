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
        setUser(result.data)
      } else {
        setUser(null)
      }
    } catch (error) {
      console.error('Failed to load session:', error)
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  async function login(email: string, password: string) {
    const result = await authService.login(email, password)
    if (result.data) {
      const loggedInUser: User = {
        id: result.data.id,
        email: result.data.email,
        account_status: result.data.account_status,
      }
      setUser(loggedInUser)
      setSession({
        session_token: result.data.session_token,
        user: loggedInUser,
      })
    } else {
      throw new Error(result.error || 'Login failed')
    }
  }

  async function logout() {
    try {
      await authService.logout()
    } finally {
      setSession(null)
      setUser(null)
    }
  }

  async function register(email: string, password: string) {
    const result = await authService.register(email, password)
    if (!result.data) {
      throw new Error(result.error || 'Registration failed')
    }
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
    return {
      user: null,
      session: null,
      loading: false,
      login: async () => {},
      logout: async () => {},
      register: async () => {},
    }
  }
  return context
}
