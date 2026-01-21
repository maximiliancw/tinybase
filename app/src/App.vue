<script setup lang="ts">
/**
 * Main App Component
 *
 * Provides the main layout with sidebar navigation and router outlet.
 */
import { computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useBreakpoints } from '@vueuse/core';
import { useAuthStore } from './stores/auth';
import { usePortalStore } from './stores/portal';
import { useNetworkStatus } from './composables/useNetworkStatus';
import Icon from './components/Icon.vue';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Toaster } from 'vue-sonner';

const router = useRouter();
const authStore = useAuthStore();
const portalStore = usePortalStore();
const { status: networkStatus } = useNetworkStatus();

// Responsive breakpoints for sidebar behavior
const breakpoints = useBreakpoints({
  mobile: 0,
  tablet: 768,
  desktop: 1024,
});
const isMobile = breakpoints.smaller('tablet');

const isAuthPortal = computed(() => {
  return router.currentRoute.value.meta?.isAuthPortal === true;
});

const showSidebar = computed(() => {
  return (
    authStore.isAuthenticated &&
    router.currentRoute.value.name !== 'admin-login' &&
    !isAuthPortal.value
  );
});

onMounted(async () => {
  // Only fetch portal config if we're on an auth portal route
  if (isAuthPortal.value) {
    await portalStore.fetchConfig();
  }
  await authStore.fetchInstanceInfo();
  // Only check storage status if user is authenticated
  if (authStore.isAuthenticated) {
    await authStore.checkStorageStatus();
  }
});

function handleLogout() {
  authStore.logout();
  router.push('/admin/login');
}
</script>

<template>
  <div
    id="app-root"
    class="flex min-h-screen bg-background"
    :class="{ 'auth-portal': isAuthPortal }"
    :style="isAuthPortal ? portalStore.styles : {}"
  >
    <Toaster position="top-right" :duration="3000" />
    <!-- Sidebar Navigation -->
    <aside
      v-if="showSidebar"
      class="fixed left-0 top-0 z-50 flex h-screen w-64 flex-col border-r bg-card overflow-y-auto transition-transform md:translate-x-0"
      :class="{ '-translate-x-full': isMobile }"
    >
      <!-- Header -->
      <header class="flex flex-col items-center justify-center p-6 border-b">
        <div class="flex w-full items-center gap-3">
          <div
            class="flex h-9 w-9 items-center justify-center rounded-md bg-gradient-to-br from-primary to-primary/80 shadow-md"
          >
            <Icon name="Box" :size="20" class="text-primary-foreground" />
          </div>
          <h1
            class="text-xl font-bold bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent"
          >
            {{ authStore.instanceName }}
          </h1>
        </div>
        <div class="w-full mt-4">
          <p class="text-xs text-muted-foreground">
            Logged in as
            <span class="font-medium text-foreground">{{ authStore.user?.email }}</span>
            <Badge v-if="authStore.isAdmin" variant="secondary" class="ml-1.5"> Admin </Badge>
          </p>
        </div>
      </header>

      <!-- Navigation -->
      <nav aria-label="Main navigation" class="flex flex-col gap-1 p-3 flex-1">
        <!-- Overview Section -->
        <div class="px-3 py-2">
          <h2 class="mb-2 text-xs font-semibold tracking-wider uppercase text-muted-foreground">
            Overview
          </h2>
          <div class="flex flex-col gap-0.5">
            <router-link
              to="/admin"
              class="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
              active-class="bg-accent/50 text-primary"
            >
              <Icon name="Dashboard" :size="18" />
              <span>Dashboard</span>
            </router-link>
            <router-link
              to="/admin/settings"
              class="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
              active-class="bg-accent/50 text-primary"
            >
              <Icon name="Settings" :size="18" />
              <span>Settings</span>
            </router-link>
            <router-link
              to="/admin/extensions"
              class="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
              active-class="bg-accent/50 text-primary"
            >
              <Icon name="Extensions" :size="18" />
              <span>Extensions</span>
            </router-link>
          </div>
        </div>

        <!-- Database Section -->
        <div class="px-3 py-2">
          <h2 class="mb-2 text-xs font-semibold tracking-wider uppercase text-muted-foreground">
            Database
          </h2>
          <div class="flex flex-col gap-0.5">
            <router-link
              to="/admin/users"
              class="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
              active-class="bg-accent/50 text-primary"
            >
              <Icon name="Users" :size="18" />
              <span>Users</span>
            </router-link>
            <router-link
              to="/admin/collections"
              class="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
              active-class="bg-accent/50 text-primary"
            >
              <Icon name="Collections" :size="18" />
              <span>Collections</span>
            </router-link>
            <router-link
              to="/admin/files"
              class="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
              active-class="bg-accent/50 text-primary"
            >
              <Icon name="Files" :size="18" />
              <span>Files</span>
            </router-link>
          </div>
        </div>

        <!-- Functions Section -->
        <div v-if="authStore.isAdmin" class="px-3 py-2">
          <h2 class="mb-2 text-xs font-semibold tracking-wider uppercase text-muted-foreground">
            Functions
          </h2>
          <div class="flex flex-col gap-0.5">
            <router-link
              to="/admin/functions"
              class="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
              active-class="bg-accent/50 text-primary"
            >
              <Icon name="Functions" :size="18" />
              <span>Overview</span>
            </router-link>
            <router-link
              to="/admin/schedules"
              class="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
              active-class="bg-accent/50 text-primary"
            >
              <Icon name="Schedules" :size="18" />
              <span>Schedules</span>
            </router-link>
            <router-link
              to="/admin/function-calls"
              class="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
              active-class="bg-accent/50 text-primary"
            >
              <Icon name="List" :size="18" />
              <span>Function Calls</span>
            </router-link>
          </div>
        </div>
      </nav>

      <!-- Footer -->
      <footer v-if="authStore.user" class="mt-auto p-4 border-t">
        <Button variant="ghost" size="sm" class="w-full justify-start" @click="handleLogout">
          <Icon name="Logout" :size="18" />
          <span>Logout</span>
        </Button>
      </footer>
    </aside>

    <!-- Network Status Banner -->
    <div
      v-if="networkStatus.message"
      class="fixed top-0 left-0 right-0 z-[100] px-4 py-2 text-center text-sm"
      :class="{
        'bg-destructive text-destructive-foreground': networkStatus.type === 'error',
        'bg-yellow-500 text-yellow-50': networkStatus.type === 'warning',
        'bg-blue-500 text-blue-50': networkStatus.type === 'info',
        'bg-green-500 text-green-50': networkStatus.type === 'success',
      }"
    >
      {{ networkStatus.message }}
    </div>

    <!-- Main Content Area -->
    <main
      class="flex-1 p-6 transition-all"
      :class="{
        'md:ml-64': showSidebar && !isMobile,
        'flex items-center justify-center min-h-screen': isAuthPortal,
      }"
    >
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(4px);
}
</style>
