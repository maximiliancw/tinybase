<script setup lang="ts">
/**
 * Main App Component
 *
 * Provides the main layout with sidebar navigation and router outlet.
 * Features premium styling with Lucide icons and refined interactions.
 */
import { computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useBreakpoints } from "@vueuse/core";
import { useAuthStore } from "./stores/auth";
import { usePortalStore } from "./stores/portal";
import { useNetworkStatus } from "./composables/useNetworkStatus";
import Icon from "./components/Icon.vue";

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
const isMobile = breakpoints.smaller("tablet");

const isAuthPortal = computed(() => {
  return router.currentRoute.value.meta?.isAuthPortal === true;
});

const showSidebar = computed(() => {
  return (
    authStore.isAuthenticated &&
    router.currentRoute.value.name !== "admin-login" &&
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
  router.push("/admin/login");
}
</script>

<template>
  <div
    id="app-root"
    :class="{ 'has-sidebar': showSidebar, 'auth-portal': isAuthPortal }"
    :style="isAuthPortal ? portalStore.styles : {}"
  >
    <!-- Sidebar Navigation -->
    <aside v-if="showSidebar" class="sidebar">
      <header
        style="
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
        "
      >
        <div
          style="
            display: flex;
            align-items: center;
            gap: var(--tb-spacing-md);
            width: 100%;
          "
        >
          <div class="logo">
            <Icon name="Box" :size="24" />
          </div>
          <h1>{{ authStore.instanceName }}</h1>
        </div>
        <div style="width: 100%; margin-top: var(--tb-spacing-lg)">
          <small class="text-muted">
            Logged in as
            <b>{{ authStore.user?.email }}</b>
            <mark v-if="authStore.isAdmin" data-status="info" class="badge">
              Admin
            </mark>
          </small>
        </div>
      </header>

      <nav aria-label="Main navigation">
        <small>Overview</small>
        <ul>
          <li>
            <router-link to="/admin">
              <span class="nav-icon">
                <Icon name="Dashboard" :size="20" />
              </span>
              Dashboard
            </router-link>
          </li>
          <li>
            <router-link to="/admin/settings">
              <span class="nav-icon">
                <Icon name="Settings" :size="20" />
              </span>
              Settings
            </router-link>
          </li>
          <li>
            <router-link to="/admin/extensions">
              <span class="nav-icon">
                <Icon name="Extensions" :size="20" />
              </span>
              Extensions
            </router-link>
          </li>
        </ul>

        <small>Database</small>
        <ul>
          <li>
            <router-link to="/admin/users">
              <span class="nav-icon">
                <Icon name="Users" :size="20" />
              </span>
              Users
            </router-link>
          </li>
          <li>
            <router-link to="/admin/collections">
              <span class="nav-icon">
                <Icon name="Collections" :size="20" />
              </span>
              Collections
            </router-link>
          </li>
          <li>
            <router-link to="/admin/files">
              <span class="nav-icon">
                <Icon name="Files" :size="20" />
              </span>
              Files
            </router-link>
          </li>
        </ul>

        <small v-if="authStore.isAdmin">Functions</small>
        <ul v-if="authStore.isAdmin">
          <li>
            <router-link to="/admin/functions">
              <span class="nav-icon">
                <Icon name="Functions" :size="20" />
              </span>
              Overview
            </router-link>
          </li>
          <li>
            <router-link to="/admin/schedules">
              <span class="nav-icon">
                <Icon name="Schedules" :size="20" />
              </span>
              Schedules
            </router-link>
          </li>
          <li>
            <router-link to="/admin/function-calls">
              <span class="nav-icon">
                <Icon name="List" :size="20" />
              </span>
              Function Calls
            </router-link>
          </li>
        </ul>
      </nav>

      <footer v-if="authStore.user">
        <button class="secondary small outline" @click.prevent="handleLogout">
          <span class="nav-icon">
            <Icon name="Logout" :size="20" />
          </span>
          Logout
        </button>
      </footer>
    </aside>

    <!-- Network Status Banner -->
    <div
      v-if="networkStatus.message"
      :data-status="networkStatus.type"
      style="
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 1000;
        padding: var(--tb-spacing-sm) var(--tb-spacing-md);
        text-align: center;
        font-size: 0.875rem;
      "
    >
      {{ networkStatus.message }}
    </div>

    <!-- Main Content Area -->
    <main>
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
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(4px);
}

/* Sidebar layout */
aside.sidebar {
  display: flex;
  flex-direction: column;
}

aside.sidebar > footer {
  margin-top: auto;
  padding: var(--tb-spacing-lg);
  padding-bottom: var(--tb-spacing-md);
}

/* Auth portal layout */
#app-root.auth-portal {
  min-height: 100vh;
}

#app-root.auth-portal main {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--tb-spacing-lg);
}
</style>
