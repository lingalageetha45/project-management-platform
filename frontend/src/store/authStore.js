import { create } from 'zustand'
import api from '../api/client'

const useAuthStore = create((set) => ({
  user: null,
  loading: true,
  error: null,

  login: async (email, password) => {
    const { data } = await api.post('/auth/login', { email, password })
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    const me = await api.get('/auth/me')
    set({ user: me.data, error: null })
    return me.data
  },

  register: async (email, full_name, password) => {
    await api.post('/auth/register', { email, full_name, password })
  },

  logout: async () => {
    const refresh = localStorage.getItem('refresh_token')
    try {
      if (refresh) await api.post('/auth/logout', null, { params: { refresh_token: refresh } })
    } catch {}
    localStorage.clear()
    set({ user: null })
  },

  fetchMe: async () => {
    try {
      const token = localStorage.getItem('access_token')
      if (!token) {
        set({ user: null, loading: false })
        return
      }
      const { data } = await api.get('/auth/me')
      set({ user: data, loading: false })
    } catch {
      localStorage.clear()
      set({ user: null, loading: false })
    }
  },
}))

export default useAuthStore
