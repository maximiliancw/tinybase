/**
 * Authentication Pinia Store
 *
 * Manages user authentication state, login/logout operations,
 * and token persistence.
 */

import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useLocalStorage } from "@vueuse/core";
import { api } from "../api";

export interface User {
  id: string;
  email: string;
  is_admin: boolean;
  created_at: string;
}

export const useAuthStore = defineStore("auth", () => {
  // State
  const token = useLocalStorage<string | null>("tinybase_token", null);
  const user = ref<User | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const adminCreated = ref(false);
  const instanceName = ref<string>("TinyBase");
  const storageEnabled = ref(false);

  // Getters
  const isAuthenticated = computed(() => !!token.value && !!user.value);
  const isAdmin = computed(() => user.value?.is_admin ?? false);

  // Actions
  async function login(email: string, password: string): Promise<boolean> {
    loading.value = true;
    error.value = null;
    adminCreated.value = false;

    try {
      const response = await api.post("/api/auth/login", { email, password });
      const data = response.data;

      token.value = data.token;

      // Check if admin was auto-created
      if (data.admin_created) {
        adminCreated.value = true;
      }

      // Fetch full user info
      await fetchUser();

      return true;
    } catch (err: any) {
      error.value = err.response?.data?.detail || "Login failed";
      return false;
    } finally {
      loading.value = false;
    }
  }

  async function fetchUser(): Promise<void> {
    if (!token.value) {
      throw new Error("No token available");
    }

    try {
      const response = await api.get("/api/auth/me");
      user.value = response.data;
    } catch (err) {
      // Token might be invalid
      logout();
      throw err;
    }
  }

  function logout(): void {
    token.value = null;
    user.value = null;
  }

  function clearAdminCreated(): void {
    adminCreated.value = false;
  }

  async function fetchInstanceInfo(): Promise<void> {
    try {
      const response = await api.get("/api/auth/instance-info");
      instanceName.value = response.data.instance_name;
    } catch (err) {
      // Fallback to default name if fetch fails
      instanceName.value = "TinyBase";
    }
  }

  async function checkStorageStatus(): Promise<void> {
    try {
      const response = await api.get("/api/files/status");
      storageEnabled.value = response.data.enabled;
    } catch (err) {
      // If check fails, assume storage is disabled
      storageEnabled.value = false;
    }
  }

  return {
    // State
    token,
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
    clearAdminCreated,
    fetchInstanceInfo,
    checkStorageStatus,
  };
});
