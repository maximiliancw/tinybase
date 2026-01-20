/**
 * API Client Configuration
 * 
 * Configures the auto-generated client with authentication and error handling.
 * The client is generated from the OpenAPI spec - see openapi-ts.config.ts
 * 
 * To regenerate the client:
 *   1. Start the TinyBase server: tinybase serve
 *   2. Run: yarn generate:client
 */

import { TinyBaseClient } from '@/client'
import { client as baseClient } from '@/client/client.gen'

// Get API base URL from environment variable
// In dev: VITE_API_URL=http://localhost:8000
// In prod: empty (relative URLs)
const API_BASE_URL = import.meta.env.VITE_API_URL || ''

// Configure the base client
baseClient.setConfig({
  baseURL: API_BASE_URL,
})

// Add request interceptor for auth token
baseClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('tb_access_token')
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Add response interceptor for error handling
baseClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle 401 errors (unauthorized)
    if (error.response?.status === 401) {
      // Clear stored tokens and redirect to login
      localStorage.removeItem('tb_access_token')
      localStorage.removeItem('tb_refresh_token')
      if (window.location.pathname !== '/admin/login') {
        window.location.href = '/admin/login'
      }
    }
    return Promise.reject(error)
  }
)

// Create and export the configured TinyBase client
export const api = new TinyBaseClient({ client: baseClient })

// Re-export types for convenience
export * from '@/client/types.gen'
