/**
 * Settings Pinia Store
 * 
 * Manages instance settings and application tokens (admin only).
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api, type InstanceSettingsResponse, type ApplicationTokenInfo, type ApplicationTokenCreateResponse } from '../api'

export const useSettingsStore = defineStore('settings', () => {
  // State
  const settings = ref<InstanceSettingsResponse | null>(null)
  const applicationTokens = ref<ApplicationTokenInfo[]>([])
  const loading = ref(false)
  const loadingTokens = ref(false)
  const error = ref<string | null>(null)

  // Actions
  async function fetchSettings(): Promise<void> {
    loading.value = true
    error.value = null

    try {
      const response = await api.admin.getSettings()
      settings.value = response.data
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to fetch settings'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateSettings(data: Partial<InstanceSettingsResponse>): Promise<void> {
    loading.value = true
    error.value = null

    try {
      const response = await api.admin.updateSettings({
        body: data,
      })
      settings.value = response.data
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to update settings'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchApplicationTokens(): Promise<void> {
    loadingTokens.value = true

    try {
      const response = await api.admin.listApplicationTokens()
      applicationTokens.value = response.data.tokens
    } catch (err: any) {
      console.error('Failed to load application tokens:', err)
      throw err
    } finally {
      loadingTokens.value = false
    }
  }

  async function createApplicationToken(data: {
    name: string
    description?: string
    expires_days?: number
  }): Promise<ApplicationTokenCreateResponse> {
    try {
      const response = await api.admin.createApplicationToken({
        body: data,
      })
      await fetchApplicationTokens()
      return response.data
    } catch (err: any) {
      throw err
    }
  }

  async function updateApplicationToken(
    tokenId: string,
    data: { is_active?: boolean }
  ): Promise<void> {
    try {
      await api.admin.updateApplicationToken({
        path: { token_id: tokenId },
        body: data,
      })
      await fetchApplicationTokens()
    } catch (err: any) {
      throw err
    }
  }

  async function revokeApplicationToken(tokenId: string): Promise<void> {
    try {
      await api.admin.revokeApplicationToken({
        path: { token_id: tokenId },
      })
      await fetchApplicationTokens()
    } catch (err: any) {
      throw err
    }
  }

  return {
    // State
    settings,
    applicationTokens,
    loading,
    loadingTokens,
    error,
    // Actions
    fetchSettings,
    updateSettings,
    fetchApplicationTokens,
    createApplicationToken,
    updateApplicationToken,
    revokeApplicationToken,
  }
})
