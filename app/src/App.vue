<script setup lang="ts">
/**
 * Main App Component
 * 
 * Provides the main layout with sidebar navigation and router outlet.
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const showSidebar = computed(() => {
  return authStore.isAuthenticated && router.currentRoute.value.name !== 'login'
})

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="app-container">
    <!-- Sidebar Navigation -->
    <aside v-if="showSidebar" class="sidebar">
      <div class="sidebar-brand">
        <h1>TinyBase</h1>
        <span class="version">Admin</span>
      </div>
      
      <nav>
        <ul class="sidebar-nav">
          <li>
            <router-link to="/">
              <span class="nav-icon">📊</span>
              Dashboard
            </router-link>
          </li>
          <li>
            <router-link to="/collections">
              <span class="nav-icon">📁</span>
              Collections
            </router-link>
          </li>
          <li>
            <router-link to="/functions">
              <span class="nav-icon">⚡</span>
              Functions
            </router-link>
          </li>
        </ul>
        
        <div v-if="authStore.isAdmin" class="sidebar-section">
          <div class="sidebar-section-title">Admin</div>
          <ul class="sidebar-nav">
            <li>
              <router-link to="/users">
                <span class="nav-icon">👥</span>
                Users
              </router-link>
            </li>
            <li>
              <router-link to="/schedules">
                <span class="nav-icon">⏰</span>
                Schedules
              </router-link>
            </li>
            <li>
              <router-link to="/function-calls">
                <span class="nav-icon">📜</span>
                Function Calls
              </router-link>
            </li>
          </ul>
        </div>
        
        <div class="sidebar-section">
          <ul class="sidebar-nav">
            <li>
              <a href="#" @click.prevent="handleLogout">
                <span class="nav-icon">🚪</span>
                Logout
              </a>
            </li>
          </ul>
        </div>
      </nav>
      
      <div v-if="authStore.user" class="sidebar-section" style="margin-top: auto;">
        <div class="text-muted" style="font-size: 0.75rem; padding: 0 1rem;">
          Logged in as<br>
          <strong>{{ authStore.user.email }}</strong>
          <span v-if="authStore.isAdmin" class="badge badge-info ml-1">Admin</span>
        </div>
      </div>
    </aside>
    
    <!-- Main Content -->
    <main :class="showSidebar ? 'main-content' : ''">
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
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.ml-1 {
  margin-left: 0.25rem;
}
</style>

