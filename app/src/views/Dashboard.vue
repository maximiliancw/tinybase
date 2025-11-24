<script setup lang="ts">
/**
 * Dashboard View
 * 
 * Overview page showing key metrics and quick links.
 */
import { onMounted, ref } from 'vue'
import { useCollectionsStore } from '../stores/collections'
import { useFunctionsStore } from '../stores/functions'
import { useAuthStore } from '../stores/auth'

const collectionsStore = useCollectionsStore()
const functionsStore = useFunctionsStore()
const authStore = useAuthStore()

const stats = ref({
  collections: 0,
  functions: 0,
  recentCalls: 0,
  activeSchedules: 0,
})

onMounted(async () => {
  await collectionsStore.fetchCollections()
  await functionsStore.fetchFunctions()
  
  stats.value.collections = collectionsStore.collections.length
  stats.value.functions = functionsStore.functions.length
  
  if (authStore.isAdmin) {
    const callsResult = await functionsStore.fetchFunctionCalls({ limit: 1 })
    stats.value.recentCalls = callsResult.total
    
    await functionsStore.fetchSchedules()
    stats.value.activeSchedules = functionsStore.schedules.filter(s => s.is_active).length
  }
})
</script>

<template>
  <div class="fade-in">
    <header class="page-header">
      <h1>Dashboard</h1>
      <p>Welcome to TinyBase Admin</p>
    </header>
    
    <div class="stats-grid">
      <div class="stat-card">
        <p class="stat-value">{{ stats.collections }}</p>
        <p class="stat-label">Collections</p>
      </div>
      <div class="stat-card">
        <p class="stat-value">{{ stats.functions }}</p>
        <p class="stat-label">Functions</p>
      </div>
      <div v-if="authStore.isAdmin" class="stat-card">
        <p class="stat-value">{{ stats.activeSchedules }}</p>
        <p class="stat-label">Active Schedules</p>
      </div>
      <div v-if="authStore.isAdmin" class="stat-card">
        <p class="stat-value">{{ stats.recentCalls }}</p>
        <p class="stat-label">Total Function Calls</p>
      </div>
    </div>
    
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">Quick Actions</h3>
      </div>
      <div class="flex gap-2">
        <router-link to="/collections" class="btn btn-secondary">
          📁 View Collections
        </router-link>
        <router-link to="/functions" class="btn btn-secondary">
          ⚡ View Functions
        </router-link>
        <router-link v-if="authStore.isAdmin" to="/users" class="btn btn-secondary">
          👥 Manage Users
        </router-link>
      </div>
    </div>
    
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">Recent Collections</h3>
        <router-link to="/collections" class="btn btn-sm btn-secondary">
          View All
        </router-link>
      </div>
      <div v-if="collectionsStore.collections.length === 0" class="empty-state">
        <p>No collections yet</p>
        <router-link to="/collections" class="btn btn-primary btn-sm mt-2">
          Create Collection
        </router-link>
      </div>
      <table v-else class="data-table">
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
            <td>{{ collection.label }}</td>
            <td>{{ collection.schema?.fields?.length || 0 }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

