import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { authApi, User } from '../api/auth'

interface AuthContextType {
  user: User | null
  login: (user: User, token?: string) => void
  logout: () => void
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)

  useEffect(() => {
    // Load user from localStorage on mount
    const savedUser = authApi.getCurrentUser()
    if (savedUser) {
      setUser(savedUser)
    }
  }, [])

  const login = (user: User, token?: string) => {
    setUser(user)
    authApi.setCurrentUser(user)
    if (token) {
      localStorage.setItem('authToken', token)
    }
  }

  const logout = () => {
    setUser(null)
    authApi.logout()
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, isAuthenticated: !!user }}>
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
