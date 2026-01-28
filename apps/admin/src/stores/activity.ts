/**
 * Activity Pinia Store
 *
 * Manages activity log state for the dashboard (admin only).
 */

import { defineStore } from 'pinia';
import { ref } from 'vue';
import { api } from '@/api';

export interface ActivityLogInfo {
  id: string;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  user_id: string | null;
  user_email: string | null;
  metadata: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}

export const useActivityStore = defineStore('activity', () => {
  // State
  const recentActivity = ref<ActivityLogInfo[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  // Actions
  async function fetchRecentActivity(limit = 10): Promise<ActivityLogInfo[]> {
    loading.value = true;
    error.value = null;

    try {
      const response = await api.admin.getRecentActivity({
        query: { limit },
      });
      recentActivity.value = response.data as ActivityLogInfo[];
      return recentActivity.value;
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to fetch activity';
      return [];
    } finally {
      loading.value = false;
    }
  }

  return {
    // State
    recentActivity,
    loading,
    error,
    // Actions
    fetchRecentActivity,
  };
});
