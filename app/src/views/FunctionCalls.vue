<script setup lang="ts">
/**
 * Function Calls View
 * 
 * View function call history (admin only).
 */
import { onMounted, ref } from 'vue'
import { useFunctionsStore } from '../stores/functions'

const functionsStore = useFunctionsStore()

const page = ref(1)
const pageSize = 50
const total = ref(0)
const filters = ref({
  function_name: '',
  status: '',
  trigger_type: '',
})

onMounted(async () => {
  await loadCalls()
  await functionsStore.fetchFunctions()
})

async function loadCalls() {
  const result = await functionsStore.fetchFunctionCalls({
    ...filters.value,
    limit: pageSize,
    offset: (page.value - 1) * pageSize,
  })
  total.value = result.total
}

async function applyFilters() {
  page.value = 1
  await loadCalls()
}

function getStatusBadgeClass(status: string) {
  switch (status) {
    case 'succeeded': return 'badge-success'
    case 'failed': return 'badge-error'
    case 'running': return 'badge-warning'
    default: return 'badge-neutral'
  }
}

function formatDuration(ms: number | null): string {
  if (ms === null) return '-'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(2)}s`
}
</script>

<template>
  <div class="fade-in">
    <header class="page-header">
      <h1>Function Calls</h1>
      <p>Execution history for all functions</p>
    </header>
    
    <!-- Filters -->
    <div class="card mb-3">
      <div class="flex gap-2 items-center" style="flex-wrap: wrap;">
        <select v-model="filters.function_name" class="form-input" style="width: auto;">
          <option value="">All Functions</option>
          <option v-for="fn in functionsStore.functions" :key="fn.name" :value="fn.name">
            {{ fn.name }}
          </option>
        </select>
        
        <select v-model="filters.status" class="form-input" style="width: auto;">
          <option value="">All Statuses</option>
          <option value="succeeded">Succeeded</option>
          <option value="failed">Failed</option>
          <option value="running">Running</option>
        </select>
        
        <select v-model="filters.trigger_type" class="form-input" style="width: auto;">
          <option value="">All Triggers</option>
          <option value="manual">Manual</option>
          <option value="schedule">Schedule</option>
        </select>
        
        <button class="btn btn-secondary" @click="applyFilters">
          Apply Filters
        </button>
      </div>
    </div>
    
    <div v-if="functionsStore.loading" class="card">
      <div class="flex items-center gap-2">
        <span class="spinner"></span>
        Loading function calls...
      </div>
    </div>
    
    <div v-else-if="functionsStore.functionCalls.length === 0" class="card">
      <div class="empty-state">
        <div class="empty-state-icon">📜</div>
        <p>No function calls yet</p>
        <p class="text-muted">Function calls will appear here when functions are invoked.</p>
      </div>
    </div>
    
    <div v-else class="card">
      <table class="data-table">
        <thead>
          <tr>
            <th>Function</th>
            <th>Status</th>
            <th>Trigger</th>
            <th>Duration</th>
            <th>Started</th>
            <th>Error</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="call in functionsStore.functionCalls" :key="call.id">
            <td style="font-family: monospace;">{{ call.function_name }}</td>
            <td>
              <span :class="['badge', getStatusBadgeClass(call.status)]">
                {{ call.status }}
              </span>
            </td>
            <td>
              <span class="badge badge-neutral">{{ call.trigger_type }}</span>
            </td>
            <td class="text-muted">{{ formatDuration(call.duration_ms) }}</td>
            <td class="text-muted">
              {{ call.started_at ? new Date(call.started_at).toLocaleString() : '-' }}
            </td>
            <td>
              <span v-if="call.error_message" class="text-error" style="font-size: 0.75rem;">
                {{ call.error_type }}: {{ call.error_message.slice(0, 50) }}...
              </span>
              <span v-else class="text-muted">-</span>
            </td>
          </tr>
        </tbody>
      </table>
      
      <!-- Pagination -->
      <div v-if="total > pageSize" class="flex justify-between items-center mt-2">
        <button
          class="btn btn-sm btn-secondary"
          :disabled="page === 1"
          @click="page--; loadCalls()"
        >
          Previous
        </button>
        <span class="text-muted">
          Page {{ page }} of {{ Math.ceil(total / pageSize) }} ({{ total }} total)
        </span>
        <button
          class="btn btn-sm btn-secondary"
          :disabled="page >= Math.ceil(total / pageSize)"
          @click="page++; loadCalls()"
        >
          Next
        </button>
      </div>
    </div>
  </div>
</template>

