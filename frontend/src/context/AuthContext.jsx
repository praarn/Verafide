import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import api from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem('verafide_user')
    return stored ? JSON.parse(stored) : null
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('verafide_token')
    if (!token) {
      setLoading(false)
      return
    }
    api
      .get('/auth/me')
      .then((res) => {
        setUser(res.data)
        localStorage.setItem('verafide_user', JSON.stringify(res.data))
      })
      .catch(() => {
        localStorage.removeItem('verafide_token')
        localStorage.removeItem('verafide_user')
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const persist = (data) => {
    localStorage.setItem('verafide_token', data.access_token)
    localStorage.setItem('verafide_user', JSON.stringify(data.user))
    setUser(data.user)
  }

  const login = useCallback(async (email, password) => {
    const res = await api.post('/auth/login', { email, password })
    persist(res.data)
    return res.data.user
  }, [])

  const register = useCallback(async (email, password, full_name) => {
    const res = await api.post('/auth/register', { email, password, full_name })
    persist(res.data)
    return res.data.user
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('verafide_token')
    localStorage.removeItem('verafide_user')
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
