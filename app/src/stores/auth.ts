/**
 * Authentication Pinia Store
 * 
 * Manages user authentication state, login/logout operations,
 * and token persistence.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '../api'

export interface User {
  id: string
  email: string
  is_admin: boolean
  created_at: string
}

export const useAuthStore = defineStore('auth', () => {
  // State
  const token = ref<string | null>(localStorage.getItem('tinybase_token'))
  const user = ref<User | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const isAdmin = computed(() => user.value?.is_admin ?? false)

  // Actions
  async function login(email: string, password: string): Promise<boolean> {
    loading.value = true
    error.value = null

    try {
      const response = await api.post('/api/auth/login', { email, password })
      const data = response.data

      token.value = data.token
      localStorage.setItem('tinybase_token', data.token)

      // Fetch full user info
      await fetchUser()

      return true
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Login failed'
      return false
    } finally {
      loading.value = false
    }
  }

  async function fetchUser(): Promise<void> {
    if (!token.value) {
      throw new Error('No token available')
    }

    try {
      const response = await api.get('/api/auth/me')
      user.value = response.data
    } catch (err) {
      // Token might be invalid
      logout()
      throw err
    }
  }

  function logout(): void {
    token.value = null
    user.value = null
    localStorage.removeItem('tinybase_token')
  }

  return {
    // State
    token,
    user,
    loading,
    error,
    // Getters
    isAuthenticated,
    isAdmin,
    // Actions
    login,
    fetchUser,
    logout,
  }
})

