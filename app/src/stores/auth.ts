/**
 * Authentication Pinia Store
 *
 * Manages user authentication state, login/logout operations,
 * and token persistence.
 */

import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useLocalStorage } from "@vueuse/core";
import { api } from "@/api";
import type { TinybaseApiRoutesAuthUserInfo } from "@/client";

export const useAuthStore = defineStore("auth", () => {
  // State - JWT tokens with synchronous localStorage sync
  // Using flush: 'sync' ensures immediate write to localStorage
  // https://vueuse.org/core/useStorage/#usage
  const accessToken = useLocalStorage<string | null>("tb_access_token", null, {
    flush: 'sync', // Write to localStorage immediately, not on next tick
  });
  const refreshToken = useLocalStorage<string | null>("tb_refresh_token", null, {
    flush: 'sync',
  });
  const user = ref<TinybaseApiRoutesAuthUserInfo | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const adminCreated = ref(false);
  const instanceName = ref<string>("TinyBase");
  const storageEnabled = ref(false);

  // Getters
  const isAuthenticated = computed(() => !!accessToken.value && !!user.value);
  const isAdmin = computed(() => user.value?.is_admin ?? false);

  // Actions
  async function login(email: string, password: string): Promise<boolean> {
    loading.value = true;
    error.value = null;
    adminCreated.value = false;

    try {
      const response = await api.auth.login({
        body: { email, password },
      });
      
      const data = response.data;
      
      if (!data) {
        throw new Error('No data in login response');
      }

      // Store JWT tokens - VueUse with flush: 'sync' writes immediately to localStorage
      accessToken.value = data.access_token;
      refreshToken.value = data.refresh_token;

      // Check if admin was auto-created
      if (data.admin_created) {
        adminCreated.value = true;
      }

      // Fetch full user info
      await fetchUser();

      return true;
    } catch (err: any) {
      error.value = err.error?.detail || "Login failed";
      return false;
    } finally {
      loading.value = false;
    }
  }

  async function fetchUser(): Promise<void> {
    if (!accessToken.value) {
      throw new Error("No token available");
    }

    try {
      const response = await api.auth.getMe();
      user.value = response.data as TinybaseApiRoutesAuthUserInfo;
    } catch (err) {
      // Token might be invalid
      clearTokens();
      throw err;
    }
  }

  async function logout(): Promise<void> {
    try {
      // Call backend logout to revoke all tokens
      if (accessToken.value) {
        await api.auth.logout();
      }
    } catch (err) {
      // Log error but continue with local logout
      console.error("Logout API call failed:", err);
    } finally {
      // Always clear local tokens
      clearTokens();
    }
  }

  function clearTokens(): void {
    accessToken.value = null;
    refreshToken.value = null;
    user.value = null;
  }

  function clearAdminCreated(): void {
    adminCreated.value = false;
  }

  async function fetchInstanceInfo(): Promise<void> {
    try {
      const response = await api.auth.getInstanceInfo();
      instanceName.value = response.data.instance_name;
    } catch {
      // Fallback to default name if fetch fails
      instanceName.value = "TinyBase";
    }
  }

  async function checkStorageStatus(): Promise<void> {
    // Only check if user is authenticated
    if (!isAuthenticated.value) {
      storageEnabled.value = false;
      return;
    }

    try {
      const response = await api.files.getStorageStatus();
      storageEnabled.value = response.data.enabled;
    } catch (err: any) {
      // If check fails (including 401), assume storage is disabled
      // Don't log 401 errors as they're expected when not authenticated
      if (err.response?.status !== 401) {
        console.error("Failed to check storage status:", err);
      }
      storageEnabled.value = false;
    }
  }

  return {
    // State
    accessToken,
    refreshToken,
    user,
    loading,
    error,
    adminCreated,
    instanceName,
    storageEnabled,
    // Getters
    isAuthenticated,
    isAdmin,
    // Actions
    login,
    fetchUser,
    logout,
    clearTokens,
    clearAdminCreated,
    fetchInstanceInfo,
    checkStorageStatus,
  };
});
