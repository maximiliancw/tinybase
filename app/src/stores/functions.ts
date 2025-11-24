/**
 * Functions Pinia Store
 * 
 * Manages functions, schedules, and function call history state.
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api'

export interface FunctionInfo {
  name: string
  description: string | null
  auth: 'public' | 'auth' | 'admin'
  tags: string[]
  module?: string
  file_path?: string
  last_loaded_at?: string
  has_input_model?: boolean
  has_output_model?: boolean
}

export interface FunctionCall {
  id: string
  function_name: string
  status: 'running' | 'succeeded' | 'failed'
  trigger_type: 'manual' | 'schedule'
  trigger_id: string | null
  requested_by_user_id: string | null
  started_at: string | null
  finished_at: string | null
  duration_ms: number | null
  error_message: string | null
  error_type: string | null
  created_at: string
}

export interface Schedule {
  id: string
  name: string
  function_name: string
  schedule: {
    method: 'once' | 'interval' | 'cron'
    timezone?: string
    date?: string
    time?: string
    unit?: string
    value?: number
    cron?: string
    description?: string
  }
  is_active: boolean
  last_run_at: string | null
  next_run_at: string | null
  created_by_user_id: string | null
  created_at: string
  updated_at: string
}

export const useFunctionsStore = defineStore('functions', () => {
  // State
  const functions = ref<FunctionInfo[]>([])
  const adminFunctions = ref<FunctionInfo[]>([])
  const functionCalls = ref<FunctionCall[]>([])
  const schedules = ref<Schedule[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Actions
  async function fetchFunctions(): Promise<void> {
    loading.value = true
    error.value = null

    try {
      const response = await api.get('/api/functions')
      functions.value = response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch functions'
    } finally {
      loading.value = false
    }
  }

  async function fetchAdminFunctions(): Promise<void> {
    loading.value = true
    error.value = null

    try {
      const response = await api.get('/api/functions/admin/list')
      adminFunctions.value = response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch functions'
    } finally {
      loading.value = false
    }
  }

  async function callFunction(
    name: string,
    payload: Record<string, any> = {}
  ): Promise<any> {
    loading.value = true
    error.value = null

    try {
      const response = await api.post(`/api/functions/${name}`, payload)
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to call function'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchFunctionCalls(
    filters: {
      function_name?: string
      status?: string
      trigger_type?: string
      limit?: number
      offset?: number
    } = {}
  ): Promise<{ calls: FunctionCall[]; total: number }> {
    loading.value = true
    error.value = null

    try {
      const response = await api.get('/api/admin/functions/calls', {
        params: filters,
      })
      functionCalls.value = response.data.calls
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch function calls'
      return { calls: [], total: 0 }
    } finally {
      loading.value = false
    }
  }

  async function fetchSchedules(): Promise<void> {
    loading.value = true
    error.value = null

    try {
      const response = await api.get('/api/admin/schedules')
      schedules.value = response.data.schedules
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch schedules'
    } finally {
      loading.value = false
    }
  }

  async function createSchedule(data: {
    name: string
    function_name: string
    schedule: any
    is_active?: boolean
  }): Promise<Schedule | null> {
    loading.value = true
    error.value = null

    try {
      const response = await api.post('/api/admin/schedules', data)
      await fetchSchedules()
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to create schedule'
      return null
    } finally {
      loading.value = false
    }
  }

  async function updateSchedule(
    id: string,
    data: { name?: string; schedule?: any; is_active?: boolean }
  ): Promise<Schedule | null> {
    loading.value = true
    error.value = null

    try {
      const response = await api.patch(`/api/admin/schedules/${id}`, data)
      await fetchSchedules()
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to update schedule'
      return null
    } finally {
      loading.value = false
    }
  }

  async function deleteSchedule(id: string): Promise<boolean> {
    loading.value = true
    error.value = null

    try {
      await api.delete(`/api/admin/schedules/${id}`)
      await fetchSchedules()
      return true
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to delete schedule'
      return false
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    functions,
    adminFunctions,
    functionCalls,
    schedules,
    loading,
    error,
    // Actions
    fetchFunctions,
    fetchAdminFunctions,
    callFunction,
    fetchFunctionCalls,
    fetchSchedules,
    createSchedule,
    updateSchedule,
    deleteSchedule,
  }
})

