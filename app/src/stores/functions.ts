/**
 * Functions Pinia Store
 * 
 * Manages functions, schedules, and function call history state.
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listFunctionsApiFunctionsGet,
  listFunctionsAdminApiFunctionsAdminListGet,
  callFunctionApiFunctionsFunctionNamePost,
  getFunctionSchemaApiFunctionsFunctionNameSchemaGet,
  listFunctionCallsApiAdminFunctionsCallsGet,
  listSchedulesApiAdminSchedulesGetData,
  listSchedulesApiAdminSchedulesGet,
  createScheduleApiAdminSchedulesPost,
  updateScheduleApiAdminSchedulesScheduleIdPatch,
  deleteScheduleApiAdminSchedulesScheduleIdDelete,
  uploadFunctionApiAdminFunctionsUploadPost,
  listFunctionVersionsApiAdminFunctionsFunctionNameVersionsGet,
} from '../api'

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
  version_id: string | null
  version_hash: string | null
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
  input_data: Record<string, any>
  is_active: boolean
  last_run_at: string | null
  next_run_at: string | null
  created_by_user_id: string | null
  created_at: string
  updated_at: string
}

export interface FunctionSchema {
  name: string
  has_input_model: boolean
  has_output_model: boolean
  input_schema: Record<string, any> | null
  output_schema: Record<string, any> | null
}

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
  const functionCalls = ref<FunctionCall[]>([])
  const schedules = ref<Schedule[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Actions
  async function fetchFunctions(): Promise<void> {
    loading.value = true
    error.value = null

    try {
      const response = await listFunctionsApiFunctionsGet()
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
      const response = await listFunctionsAdminApiFunctionsAdminListGet()
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
      const response = await callFunctionApiFunctionsFunctionNamePost({
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
  ): Promise<{ calls: FunctionCall[]; total: number }> {
    loading.value = true
    error.value = null

    try {
      const response = await listFunctionCallsApiAdminFunctionsCallsGet({
        query: filters,
      })
      functionCalls.value = response.data.calls as FunctionCall[]
      return response.data as { calls: FunctionCall[]; total: number }
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
      const response = await listSchedulesApiAdminSchedulesGet()
      schedules.value = response.data.schedules as Schedule[]
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
  }): Promise<Schedule | null> {
    loading.value = true
    error.value = null

    try {
      const response = await createScheduleApiAdminSchedulesPost({
        body: data,
      })
      await fetchSchedules()
      return response.data as Schedule
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
  ): Promise<Schedule | null> {
    loading.value = true
    error.value = null

    try {
      const response = await updateScheduleApiAdminSchedulesScheduleIdPatch({
        path: { schedule_id: id },
        body: data,
      })
      await fetchSchedules()
      return response.data as Schedule
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
      await deleteScheduleApiAdminSchedulesScheduleIdDelete({
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

  async function fetchFunctionSchema(name: string): Promise<FunctionSchema | null> {
    error.value = null

    try {
      const response = await getFunctionSchemaApiFunctionsFunctionNameSchemaGet({
        path: { function_name: name },
      })
      return response.data as FunctionSchema
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
      const response = await uploadFunctionApiAdminFunctionsUploadPost({
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
      const response = await listFunctionVersionsApiAdminFunctionsFunctionNameVersionsGet({
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
