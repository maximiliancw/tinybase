/**
 * Users Pinia Store
 *
 * Manages user administration state (admin only).
 */

import { defineStore } from 'pinia';
import { ref } from 'vue';
import { api } from '@/api';
import type { TinybaseApiRoutesAdminUserInfo } from '@/client';

export const useUsersStore = defineStore('users', () => {
  // State
  const users = ref<TinybaseApiRoutesAdminUserInfo[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  // Actions
  async function fetchUsers(
    limit = 100,
    offset = 0
  ): Promise<{ users: TinybaseApiRoutesAdminUserInfo[]; total: number }> {
    loading.value = true;
    error.value = null;

    try {
      const response = await api.admin.listUsers({
        query: { limit, offset },
      });
      users.value = response.data.users as TinybaseApiRoutesAdminUserInfo[];
      return response.data as { users: TinybaseApiRoutesAdminUserInfo[]; total: number };
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to fetch users';
      return { users: [], total: 0 };
    } finally {
      loading.value = false;
    }
  }

  async function createUser(data: {
    email: string;
    password: string;
    is_admin?: boolean;
  }): Promise<TinybaseApiRoutesAdminUserInfo | null> {
    loading.value = true;
    error.value = null;

    try {
      const response = await api.admin.createUser({
        body: data,
      });
      await fetchUsers();
      return response.data as TinybaseApiRoutesAdminUserInfo;
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to create user';
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function updateUser(
    id: string,
    data: { email?: string; password?: string; is_admin?: boolean }
  ): Promise<TinybaseApiRoutesAdminUserInfo | null> {
    loading.value = true;
    error.value = null;

    try {
      const response = await api.admin.updateUser({
        path: { user_id: id },
        body: data,
      });
      await fetchUsers();
      return response.data as TinybaseApiRoutesAdminUserInfo;
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to update user';
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function deleteUser(id: string): Promise<boolean> {
    loading.value = true;
    error.value = null;

    try {
      await api.admin.deleteUser({
        path: { user_id: id },
      });
      await fetchUsers();
      return true;
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to delete user';
      return false;
    } finally {
      loading.value = false;
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
  };
});
