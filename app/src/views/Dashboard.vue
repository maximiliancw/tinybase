<script setup lang="ts">
/**
 * Dashboard View
 *
 * Overview page with key metrics and quick navigation.
 */
import { onMounted, ref, computed } from 'vue';
import { useToast } from '../composables/useToast';
import { useTimeAgo, useDateFormat } from '@vueuse/core';
import { useCollectionsStore } from '../stores/collections';
import { useFunctionsStore } from '../stores/functions';
import { useUsersStore } from '../stores/users';
import { useAuthStore } from '../stores/auth';
import { useActivityStore, type ActivityLogInfo } from '../stores/activity';
import { api } from '@/api';
import CollectionSizesChart from '../components/CollectionSizesChart.vue';
import FunctionStatsChart from '../components/FunctionStatsChart.vue';
import Icon from '../components/Icon.vue';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Database,
  Zap,
  Activity,
  LogIn,
  UserPlus,
  FileEdit,
  Trash2,
  FilePlus,
} from 'lucide-vue-next';

const toast = useToast();
const collectionsStore = useCollectionsStore();
const functionsStore = useFunctionsStore();
const usersStore = useUsersStore();
const authStore = useAuthStore();
const activityStore = useActivityStore();

const stats = ref({
  users: 0,
  collections: 0,
  functions: 0,
  activeSchedules: 0,
});

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

// Time utilities for metrics timestamps
const metricsCollectedAt = computed(() => metrics.value.collected_at);
const timeAgo = useTimeAgo(metricsCollectedAt);
const formattedDate = useDateFormat(metricsCollectedAt, 'YYYY-MM-DD HH:mm:ss');

onMounted(async () => {
  // Show toast if admin was created
  if (authStore.adminCreated) {
    toast.success(
      '🎉 Admin account created! No users existed, so an admin account was automatically created with your credentials.',
      {
        timeout: 5000,
      }
    );
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
    stats.value.activeSchedules = functionsStore.schedules.filter((s) => s.is_active).length;

    // Fetch metrics for charts
    await fetchMetrics();

    // Fetch recent activity
    await activityStore.fetchRecentActivity(10);
  }
});

// Get icon component for activity action
function getActivityIcon(action: string) {
  if (action.startsWith('user.login')) return LogIn;
  if (action.startsWith('user.register')) return UserPlus;
  if (action.includes('.create')) return FilePlus;
  if (action.includes('.update')) return FileEdit;
  if (action.includes('.delete')) return Trash2;
  return Activity;
}

// Format activity action for display
function formatAction(action: string): string {
  const parts = action.split('.');
  if (parts.length >= 2) {
    const [resource, verb] = parts;
    return `${verb.charAt(0).toUpperCase() + verb.slice(1)} ${resource}`;
  }
  return action;
}

// Format relative time for activity
function formatActivityTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

async function fetchMetrics() {
  if (!authStore.isAdmin) return;

  metricsLoading.value = true;
  metricsError.value = null;

  try {
    const response = await api.admin.getMetrics();
    metrics.value = {
      collection_sizes: response.data.collection_sizes || [],
      function_stats: response.data.function_stats || [],
      collected_at: response.data.collected_at || null,
    };
  } catch (err: any) {
    metricsError.value = err.error?.detail || 'Failed to load metrics';
    // Don't show error to user, just log it
    console.error('Failed to fetch metrics:', err);
  } finally {
    metricsLoading.value = false;
  }
}
</script>

<template>
  <section class="space-y-6 animate-in fade-in duration-500">
    <!-- Page Header -->
    <header class="space-y-1">
      <h1 class="text-3xl font-bold tracking-tight">Dashboard</h1>
      <p class="text-muted-foreground">Welcome to your TinyBase instance's admin dashboard</p>
    </header>

    <!-- Stats Grid -->
    <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <Card v-if="authStore.isAdmin">
        <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle class="text-sm font-medium"> Total Users </CardTitle>
          <Icon name="Users" :size="16" class="text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div class="text-2xl font-bold">
            {{ stats.users }}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle class="text-sm font-medium"> Collections </CardTitle>
          <Icon name="Collections" :size="16" class="text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div class="text-2xl font-bold">
            {{ stats.collections }}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle class="text-sm font-medium"> Functions </CardTitle>
          <Icon name="Functions" :size="16" class="text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div class="text-2xl font-bold">
            {{ stats.functions }}
          </div>
        </CardContent>
      </Card>

      <Card v-if="authStore.isAdmin">
        <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle class="text-sm font-medium"> Active Schedules </CardTitle>
          <Icon name="Schedules" :size="16" class="text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div class="text-2xl font-bold">
            {{ stats.activeSchedules }}
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Quick Actions -->
    <Card>
      <CardHeader>
        <CardTitle>Quick Actions</CardTitle>
      </CardHeader>
      <CardContent>
        <div class="grid gap-3 md:grid-cols-3">
          <router-link
            v-if="authStore.isAdmin"
            to="/collections?action=create"
            class="flex items-center gap-3 rounded-lg border p-4 transition-colors hover:bg-accent"
          >
            <div class="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10">
              <Icon name="FolderPlus" :size="20" class="text-primary" />
            </div>
            <div class="flex-1">
              <p class="text-sm font-medium">Create Collection</p>
            </div>
            <Icon name="Arrow" :size="16" class="text-muted-foreground" />
          </router-link>

          <router-link
            v-if="authStore.isAdmin"
            to="/users?action=create"
            class="flex items-center gap-3 rounded-lg border p-4 transition-colors hover:bg-accent"
          >
            <div class="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10">
              <Icon name="UserPlus" :size="20" class="text-primary" />
            </div>
            <div class="flex-1">
              <p class="text-sm font-medium">Create User</p>
            </div>
            <Icon name="Arrow" :size="16" class="text-muted-foreground" />
          </router-link>

          <router-link
            v-if="authStore.isAdmin"
            to="/schedules?action=create"
            class="flex items-center gap-3 rounded-lg border p-4 transition-colors hover:bg-accent"
          >
            <div class="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10">
              <Icon name="Schedules" :size="20" class="text-primary" />
            </div>
            <div class="flex-1">
              <p class="text-sm font-medium">Create Schedule</p>
            </div>
            <Icon name="Arrow" :size="16" class="text-muted-foreground" />
          </router-link>
        </div>
      </CardContent>
    </Card>

    <!-- Charts Section -->
    <div v-if="authStore.isAdmin" class="grid gap-4 md:grid-cols-2">
      <!-- Collection Sizes Chart -->
      <Card class="overflow-hidden">
        <CardHeader>
          <div class="flex items-center justify-between gap-2">
            <CardTitle class="shrink-0">Collection Sizes</CardTitle>
            <p v-if="metrics.collected_at" class="truncate text-xs text-muted-foreground">
              Updated {{ timeAgo }}
            </p>
          </div>
        </CardHeader>
        <CardContent class="overflow-hidden">
          <div v-if="metricsLoading" class="h-[300px] space-y-3 p-4">
            <Skeleton class="h-8 w-3/4" />
            <Skeleton class="h-8 w-full" />
            <Skeleton class="h-8 w-5/6" />
            <Skeleton class="h-8 w-2/3" />
            <Skeleton class="h-8 w-4/5" />
          </div>

          <Empty v-else-if="metrics.collection_sizes.length === 0" class="h-[300px]">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <Database />
              </EmptyMedia>
              <EmptyTitle>No metrics available yet</EmptyTitle>
              <EmptyDescription>
                Metrics will be collected automatically by the scheduler.
              </EmptyDescription>
            </EmptyHeader>
          </Empty>

          <CollectionSizesChart v-else :data="metrics.collection_sizes" />
        </CardContent>
      </Card>

      <!-- Function Statistics Chart -->
      <Card class="overflow-hidden">
        <CardHeader>
          <div class="flex items-center justify-between gap-2">
            <CardTitle class="shrink-0">Function Statistics</CardTitle>
            <p v-if="metrics.collected_at" class="truncate text-xs text-muted-foreground">
              Updated {{ timeAgo }}
            </p>
          </div>
        </CardHeader>
        <CardContent class="overflow-hidden">
          <div v-if="metricsLoading" class="h-[300px] space-y-3 p-4">
            <Skeleton class="h-8 w-3/4" />
            <Skeleton class="h-8 w-full" />
            <Skeleton class="h-8 w-5/6" />
            <Skeleton class="h-8 w-2/3" />
            <Skeleton class="h-8 w-4/5" />
          </div>

          <Empty v-else-if="metrics.function_stats.length === 0" class="h-[300px]">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <Zap />
              </EmptyMedia>
              <EmptyTitle>No function statistics available yet</EmptyTitle>
              <EmptyDescription>
                Metrics will be collected automatically by the scheduler.
              </EmptyDescription>
            </EmptyHeader>
          </Empty>

          <FunctionStatsChart v-else :data="metrics.function_stats" />
        </CardContent>
      </Card>
    </div>

    <!-- Recent Activity -->
    <Card v-if="authStore.isAdmin">
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
      </CardHeader>
      <CardContent>
        <div v-if="activityStore.loading" class="space-y-4">
          <div v-for="i in 5" :key="i" class="flex items-start gap-3">
            <Skeleton class="h-8 w-8 rounded-full shrink-0" />
            <div class="flex-1 space-y-2">
              <Skeleton class="h-4 w-3/4" />
              <Skeleton class="h-3 w-1/2" />
            </div>
          </div>
        </div>

        <Empty v-else-if="activityStore.recentActivity.length === 0" class="py-8">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <Activity />
            </EmptyMedia>
            <EmptyTitle>No activity yet</EmptyTitle>
            <EmptyDescription>
              Activity will appear here as users interact with your TinyBase instance.
            </EmptyDescription>
          </EmptyHeader>
        </Empty>

        <div v-else class="space-y-4">
          <div
            v-for="activity in activityStore.recentActivity"
            :key="activity.id"
            class="flex items-start gap-3"
          >
            <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted">
              <component
                :is="getActivityIcon(activity.action)"
                class="h-4 w-4 text-muted-foreground"
              />
            </div>
            <div class="flex-1 space-y-1">
              <p class="text-sm font-medium leading-none">
                {{ formatAction(activity.action) }}
                <span v-if="activity.resource_type" class="text-muted-foreground">
                  ({{ activity.resource_type }})
                </span>
              </p>
              <p class="text-xs text-muted-foreground">
                <span v-if="activity.user_email">{{ activity.user_email }}</span>
                <span v-else>System</span>
                <span class="mx-1">·</span>
                <span>{{ formatActivityTime(activity.created_at) }}</span>
              </p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  </section>
</template>
