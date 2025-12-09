<script setup lang="ts">
/**
 * Dashboard View
 * 
 * Overview page with key metrics and quick navigation.
 * Features animated stat cards and refined layout.
 */
import { onMounted, ref } from 'vue'
import { useCollectionsStore } from '../stores/collections'
import { useFunctionsStore } from '../stores/functions'
import { useUsersStore } from '../stores/users'
import { useAuthStore } from '../stores/auth'

const collectionsStore = useCollectionsStore()
const functionsStore = useFunctionsStore()
const usersStore = useUsersStore()
const authStore = useAuthStore()

const stats = ref({
  users: 0,
  collections: 0,
  functions: 0,
  activeSchedules: 0,
})

const showAdminCreatedNotice = ref(authStore.adminCreated)

onMounted(async () => {
  // Clear the flag after showing
  if (authStore.adminCreated) {
    authStore.clearAdminCreated()
  }
  
  await collectionsStore.fetchCollections()
  await functionsStore.fetchFunctions()
  
  stats.value.collections = collectionsStore.collections.length
  stats.value.functions = functionsStore.functions.length
  
  if (authStore.isAdmin) {
    const usersResult = await usersStore.fetchUsers(1, 0)
    stats.value.users = usersResult.total
    
    await functionsStore.fetchSchedules()
    stats.value.activeSchedules = functionsStore.schedules.filter(s => s.is_active).length
  }
})

function dismissNotice() {
  showAdminCreatedNotice.value = false
}
</script>

<template>
  <div data-animate="fade-in">
    <!-- Admin Created Notice -->
    <article v-if="showAdminCreatedNotice" data-status="success" class="notice mb-3">
      <div class="notice-content">
        <strong>🎉 Admin account created!</strong>
        <p>No users existed, so an admin account was automatically created with your credentials.</p>
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
        <router-link to="/collections" class="action-item">
          <span class="action-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
            </svg>
          </span>
          <span class="action-label">View Collections</span>
          <span class="action-arrow">→</span>
        </router-link>
        
        <router-link to="/functions" class="action-item">
          <span class="action-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
            </svg>
          </span>
          <span class="action-label">View Functions</span>
          <span class="action-arrow">→</span>
        </router-link>
        
        <router-link v-if="authStore.isAdmin" to="/users" class="action-item">
          <span class="action-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
            </svg>
          </span>
          <span class="action-label">Manage Users</span>
          <span class="action-arrow">→</span>
        </router-link>
        
        <router-link v-if="authStore.isAdmin" to="/settings" class="action-item">
          <span class="action-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
          </span>
          <span class="action-label">Settings</span>
          <span class="action-arrow">→</span>
        </router-link>
      </div>
    </article>
    
    <!-- Recent Collections Card -->
    <article>
      <header>
        <h3>Recent Collections</h3>
        <router-link to="/collections" role="button" class="secondary small">
          View All
        </router-link>
      </header>
      
      <div v-if="collectionsStore.collections.length === 0" data-empty data-empty-icon="📁">
        <p>No collections yet</p>
        <router-link to="/collections" role="button" class="small mt-2">
          Create Collection
        </router-link>
      </div>
      
      <table v-else>
        <thead>
          <tr>
            <th>Name</th>
            <th>Label</th>
            <th>Fields</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="collection in collectionsStore.collections.slice(0, 5)" :key="collection.id">
            <td>
              <router-link :to="`/collections/${collection.name}`">
                {{ collection.name }}
              </router-link>
            </td>
            <td class="text-secondary">{{ collection.label }}</td>
            <td><mark data-status="neutral">{{ collection.schema?.fields?.length || 0 }} fields</mark></td>
          </tr>
        </tbody>
      </table>
    </article>
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
  transition: 
    background var(--tb-transition-fast),
    border-color var(--tb-transition-fast),
    transform var(--tb-transition-fast);
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
</style>
