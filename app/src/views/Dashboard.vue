<script setup lang="ts">
/**
 * Dashboard View
 *
 * Overview page with key metrics and quick navigation.
 * Features animated stat cards and refined layout with charts.
 */
import { onMounted, ref } from "vue";
import { useCollectionsStore } from "../stores/collections";
import { useFunctionsStore } from "../stores/functions";
import { useUsersStore } from "../stores/users";
import { useAuthStore } from "../stores/auth";
import { api } from "../api";
import CollectionSizesChart from "../components/CollectionSizesChart.vue";
import FunctionStatsChart from "../components/FunctionStatsChart.vue";
import Icon from "../components/Icon.vue";

const collectionsStore = useCollectionsStore();
const functionsStore = useFunctionsStore();
const usersStore = useUsersStore();
const authStore = useAuthStore();

const stats = ref({
  users: 0,
  collections: 0,
  functions: 0,
  activeSchedules: 0,
});

const showAdminCreatedNotice = ref(authStore.adminCreated);

// Metrics data
const metrics = ref({
  collection_sizes: [] as Array<{
    collection_name: string;
    record_count: number;
  }>,
  function_stats: [] as Array<{
    function_name: string;
    avg_runtime_ms: number | null;
    error_rate: number;
    total_calls: number;
  }>,
  collected_at: null as string | null,
});
const metricsLoading = ref(false);
const metricsError = ref<string | null>(null);

onMounted(async () => {
  // Clear the flag after showing
  if (authStore.adminCreated) {
    authStore.clearAdminCreated();
  }

  await collectionsStore.fetchCollections();
  await functionsStore.fetchFunctions();

  stats.value.collections = collectionsStore.collections.length;
  stats.value.functions = functionsStore.functions.length;

  if (authStore.isAdmin) {
    const usersResult = await usersStore.fetchUsers(1, 0);
    stats.value.users = usersResult.total;

    await functionsStore.fetchSchedules();
    stats.value.activeSchedules = functionsStore.schedules.filter(
      (s) => s.is_active
    ).length;

    // Fetch metrics for charts
    await fetchMetrics();
  }
});

async function fetchMetrics() {
  if (!authStore.isAdmin) return;

  metricsLoading.value = true;
  metricsError.value = null;

  try {
    const response = await api.get("/api/admin/metrics");
    metrics.value = {
      collection_sizes: response.data.collection_sizes || [],
      function_stats: response.data.function_stats || [],
      collected_at: response.data.collected_at || null,
    };
  } catch (err: any) {
    metricsError.value = err.response?.data?.detail || "Failed to load metrics";
    // Don't show error to user, just log it
    console.error("Failed to fetch metrics:", err);
  } finally {
    metricsLoading.value = false;
  }
}

function dismissNotice() {
  showAdminCreatedNotice.value = false;
}
</script>

<template>
  <div data-animate="fade-in">
    <!-- Admin Created Notice -->
    <article
      v-if="showAdminCreatedNotice"
      data-status="success"
      class="notice mb-3"
    >
      <div class="notice-content">
        <strong>🎉 Admin account created!</strong>
        <p>
          No users existed, so an admin account was automatically created with
          your credentials.
        </p>
      </div>
      <button class="secondary small" @click="dismissNotice">Dismiss</button>
    </article>

    <header class="page-header">
      <hgroup>
        <h1>Dashboard</h1>
        <p>Welcome to your TinyBase instance's admin dashboard</p>
      </hgroup>
    </header>

    <!-- Stats Grid with stagger animation -->
    <div class="stats-grid" data-animate="stagger">
      <article v-if="authStore.isAdmin" class="stat-card">
        <p>{{ stats.users }}</p>
        <p>Users</p>
      </article>
      <article class="stat-card">
        <p>{{ stats.collections }}</p>
        <p>Collections</p>
      </article>
      <article class="stat-card">
        <p>{{ stats.functions }}</p>
        <p>Functions</p>
      </article>
      <article v-if="authStore.isAdmin" class="stat-card">
        <p>{{ stats.activeSchedules }}</p>
        <p>Active Schedules</p>
      </article>
    </div>

    <!-- Quick Actions Card -->
    <article class="quick-actions">
      <header>
        <h3>Quick Actions</h3>
      </header>
      <div class="action-grid">
        <router-link
          v-if="authStore.isAdmin"
          to="/collections?action=create"
          class="action-item"
        >
          <span class="action-icon">
            <Icon name="FolderPlus" :size="18" />
          </span>
          <span class="action-label">Create Collection</span>
          <span class="action-arrow">→</span>
        </router-link>

        <router-link
          v-if="authStore.isAdmin"
          to="/users?action=create"
          class="action-item"
        >
          <span class="action-icon">
            <Icon name="UserPlus" :size="18" />
          </span>
          <span class="action-label">Create User</span>
          <span class="action-arrow">→</span>
        </router-link>

        <router-link
          v-if="authStore.isAdmin"
          to="/schedules?action=create"
          class="action-item"
        >
          <span class="action-icon">
            <Icon name="Schedules" :size="18" />
          </span>
          <span class="action-label">Create Schedule</span>
          <span class="action-arrow">→</span>
        </router-link>
      </div>
    </article>

    <!-- Charts Section -->
    <div v-if="authStore.isAdmin" class="charts-grid">
      <!-- Collection Sizes Chart -->
      <article>
        <header>
          <h3>Collection Sizes</h3>
          <small v-if="metrics.collected_at" class="text-muted">
            Updated {{ new Date(metrics.collected_at).toLocaleString() }}
          </small>
        </header>

        <div v-if="metricsLoading" aria-busy="true" style="min-height: 300px">
          Loading metrics...
        </div>

        <div
          v-else-if="metrics.collection_sizes.length === 0"
          data-empty
          data-empty-icon="📊"
          style="min-height: 300px"
        >
          <p>No metrics available yet</p>
          <p>
            <small class="text-muted"
              >Metrics will be collected automatically by the scheduler.</small
            >
          </p>
        </div>

        <CollectionSizesChart v-else :data="metrics.collection_sizes" />
      </article>

      <!-- Function Statistics Chart -->
      <article>
        <header>
          <h3>Function Statistics</h3>
          <small v-if="metrics.collected_at" class="text-muted">
            Updated {{ new Date(metrics.collected_at).toLocaleString() }}
          </small>
        </header>

        <div v-if="metricsLoading" aria-busy="true" style="min-height: 300px">
          Loading metrics...
        </div>

        <div
          v-else-if="metrics.function_stats.length === 0"
          data-empty
          data-empty-icon="⚡"
          style="min-height: 300px"
        >
          <p>No function statistics available yet</p>
          <p>
            <small class="text-muted"
              >Metrics will be collected automatically by the scheduler.</small
            >
          </p>
        </div>

        <FunctionStatsChart v-else :data="metrics.function_stats" />
      </article>
    </div>
  </div>
</template>

<style scoped>
/* Quick actions grid */
.quick-actions {
  margin-bottom: var(--tb-spacing-lg);
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--tb-spacing-md);
}

.action-item {
  display: flex;
  align-items: center;
  gap: var(--tb-spacing-md);
  padding: var(--tb-spacing-md);
  background: var(--tb-surface-1);
  border: 1px solid var(--tb-border);
  border-radius: var(--tb-radius);
  color: var(--tb-text);
  text-decoration: none;
  transition: background var(--tb-transition-fast),
    border-color var(--tb-transition-fast), transform var(--tb-transition-fast);
}

.action-item:hover {
  background: var(--tb-surface-2);
  border-color: var(--tb-border-strong);
  transform: translateY(-2px);
}

.action-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  background: var(--tb-primary-focus);
  border-radius: var(--tb-radius);
  color: var(--tb-primary);
  flex-shrink: 0;
}

.action-icon svg {
  width: 1.125rem;
  height: 1.125rem;
}

.action-label {
  flex: 1;
  font-weight: 500;
  font-size: 0.875rem;
}

.action-arrow {
  color: var(--tb-text-muted);
  transition: transform var(--tb-transition-fast);
}

.action-item:hover .action-arrow {
  transform: translateX(4px);
  color: var(--tb-primary);
}

/* Page header layout */
.page-header hgroup {
  margin: 0;
}

.page-header hgroup h1 {
  margin-bottom: var(--tb-spacing-xs);
}

.page-header hgroup p {
  margin: 0;
}

/* Charts grid */
.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: var(--tb-spacing-lg);
  margin-bottom: var(--tb-spacing-lg);
}

.charts-grid article {
  min-height: 400px;
}

.charts-grid article header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--tb-spacing-md);
}

.charts-grid article header h3 {
  margin: 0;
}
</style>
