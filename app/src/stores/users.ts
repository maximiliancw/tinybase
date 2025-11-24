/**
 * Users Pinia Store
 * 
 * Manages user administration state (admin only).
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api'

export interface AdminUser {
  id: string
  email: string
  is_admin: boolean
  created_at: string
  updated_at: string
}

export const useUsersStore = defineStore('users', () => {
  // State
  const users = ref<AdminUser[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Actions
  async function fetchUsers(
    limit = 100,
    offset = 0
  ): Promise<{ users: AdminUser[]; total: number }> {
    loading.value = true
    error.value = null

    try {
      const response = await api.get('/api/admin/users', {
        params: { limit, offset },
      })
      users.value = response.data.users
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch users'
      return { users: [], total: 0 }
    } finally {
      loading.value = false
    }
  }

  async function createUser(data: {
    email: string
    password: string
    is_admin?: boolean
  }): Promise<AdminUser | null> {
    loading.value = true
    error.value = null

    try {
      const response = await api.post('/api/admin/users', data)
      await fetchUsers()
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to create user'
      return null
    } finally {
      loading.value = false
    }
  }

  async function updateUser(
    id: string,
    data: { email?: string; password?: string; is_admin?: boolean }
  ): Promise<AdminUser | null> {
    loading.value = true
    error.value = null

    try {
      const response = await api.patch(`/api/admin/users/${id}`, data)
      await fetchUsers()
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to update user'
      return null
    } finally {
      loading.value = false
    }
  }

  async function deleteUser(id: string): Promise<boolean> {
    loading.value = true
    error.value = null

    try {
      await api.delete(`/api/admin/users/${id}`)
      await fetchUsers()
      return true
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to delete user'
      return false
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    users,
    loading,
    error,
    // Actions
    fetchUsers,
    createUser,
    updateUser,
    deleteUser,
  }
})

