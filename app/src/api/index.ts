/**
 * API Client
 * 
 * Axios instance configured for TinyBase API requests.
 * Automatically includes authentication token in requests.
 * 
 * In development, set VITE_API_URL to point to your FastAPI server:
 *   VITE_API_URL=http://localhost:8000
 * 
 * In production (when served from FastAPI), leave it empty to use relative URLs.
 */

import axios from 'axios'

// Get API base URL from environment variable
// In dev: VITE_API_URL=http://localhost:8000
// In prod: empty (relative URLs)
const API_BASE_URL = import.meta.env.VITE_API_URL || ''

// Create axios instance
export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('tb_access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle errors
api.interceptors.response.use(
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

export default api

