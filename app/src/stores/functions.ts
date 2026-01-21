/**
 * Functions Pinia Store
 * 
 * Manages functions, schedules, and function call history state.
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api'
import type { 
  FunctionInfo,
  FunctionCallInfo,
  ScheduleResponse,
  FunctionSchemaResponse
} from '@/client'

/**
 * Generate a template object from a JSON schema.
 * Creates an object with all properties set to appropriate default values.
 */
export function generateTemplateFromSchema(schema: Record<string, any> | null): Record<string, any> {
  if (!schema) return {}
  
  const properties = schema.properties
  if (!properties) return {}
  
  const template: Record<string, any> = {}
  const required = schema.required || []
  
  for (const [key, prop] of Object.entries(properties) as [string, any][]) {
    // Use default if available
    if ('default' in prop) {
      template[key] = prop.default
      continue
    }
    
    // Generate appropriate placeholder based on type
    const type = prop.type
    if (type === 'string') {
      template[key] = ''
    } else if (type === 'integer' || type === 'number') {
      template[key] = 0
    } else if (type === 'boolean') {
      template[key] = false
    } else if (type === 'array') {
      template[key] = []
    } else if (type === 'object') {
      template[key] = {}
    } else if (prop.anyOf || prop.oneOf) {
      // Union type - use null if nullable, otherwise use first type's default
      const types = prop.anyOf || prop.oneOf
      const hasNull = types.some((t: any) => t.type === 'null')
      if (hasNull) {
        template[key] = null
      } else if (types[0]?.type === 'string') {
        template[key] = ''
      } else if (types[0]?.type === 'integer' || types[0]?.type === 'number') {
        template[key] = 0
      } else {
        template[key] = null
      }
    } else {
      // For required fields without defaults, use null as placeholder
      if (required.includes(key)) {
        template[key] = null
      }
    }
  }
  
  return template
}

export const useFunctionsStore = defineStore('functions', () => {
  // State
  const functions = ref<FunctionInfo[]>([])
  const adminFunctions = ref<FunctionInfo[]>([])
  const functionCalls = ref<FunctionCallInfo[]>([])
  const schedules = ref<ScheduleResponse[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Actions
  async function fetchFunctions(): Promise<void> {
    loading.value = true
    error.value = null

    try {
      const response = await api.functions.listFunctions()
      functions.value = response.data as FunctionInfo[]
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to fetch functions'
    } finally {
      loading.value = false
    }
  }

  async function fetchAdminFunctions(): Promise<void> {
    loading.value = true
    error.value = null

    try {
      const response = await api.functions.listFunctionsAdmin()
      adminFunctions.value = response.data as FunctionInfo[]
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to fetch functions'
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
      const response = await api.functions.callFunction({
        path: { function_name: name },
        body: payload,
      })
      return response.data
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to call function'
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
  ): Promise<{ calls: FunctionCallInfo[]; total: number }> {
    loading.value = true
    error.value = null

    try {
      const response = await api.admin.listFunctionCalls({
        query: filters,
      })
      functionCalls.value = response.data.calls as FunctionCallInfo[]
      return response.data as { calls: FunctionCallInfo[]; total: number }
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to fetch function calls'
      return { calls: [], total: 0 }
    } finally {
      loading.value = false
    }
  }

  async function fetchSchedules(): Promise<void> {
    loading.value = true
    error.value = null

    try {
      const response = await api.schedules.listSchedules()
      schedules.value = response.data.schedules as ScheduleResponse[]
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to fetch schedules'
    } finally {
      loading.value = false
    }
  }

  async function createSchedule(data: {
    name: string
    function_name: string
    schedule: any
    input_data?: Record<string, any>
    is_active?: boolean
  }): Promise<ScheduleResponse | null> {
    loading.value = true
    error.value = null

    try {
      const response = await api.schedules.createSchedule({
        body: data,
      })
      await fetchSchedules()
      return response.data as ScheduleResponse
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to create schedule'
      return null
    } finally {
      loading.value = false
    }
  }

  async function updateSchedule(
    id: string,
    data: { name?: string; schedule?: any; is_active?: boolean }
  ): Promise<ScheduleResponse | null> {
    loading.value = true
    error.value = null

    try {
      const response = await api.schedules.updateSchedule({
        path: { schedule_id: id },
        body: data,
      })
      await fetchSchedules()
      return response.data as ScheduleResponse
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to update schedule'
      return null
    } finally {
      loading.value = false
    }
  }

  async function deleteSchedule(id: string): Promise<boolean> {
    loading.value = true
    error.value = null

    try {
      await api.schedules.deleteSchedule({
        path: { schedule_id: id },
      })
      await fetchSchedules()
      return true
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to delete schedule'
      return false
    } finally {
      loading.value = false
    }
  }

  async function fetchFunctionSchema(name: string): Promise<FunctionSchemaResponse | null> {
    error.value = null

    try {
      const response = await api.functions.getFunctionSchema({
        path: { function_name: name },
      })
      return response.data as FunctionSchemaResponse
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to fetch function schema'
      return null
    }
  }

  async function uploadFunction(
    filename: string,
    content: string,
    notes?: string
  ): Promise<any> {
    loading.value = true
    error.value = null

    try {
      const response = await api.admin.uploadFunction({
        body: {
          filename,
          content,
          notes,
        },
      })
      return response.data
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to upload function'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchFunctionVersions(functionName: string): Promise<any[]> {
    loading.value = true
    error.value = null

    try {
      const response = await api.admin.listFunctionVersions({
        path: { function_name: functionName },
      })
      return response.data.versions || []
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to fetch function versions'
      return []
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
    fetchFunctionSchema,
    uploadFunction,
    fetchFunctionVersions,
  }
})
