<script setup lang="ts">
/**
 * Function Calls View
 * 
 * View function call history (admin only).
 * Uses semantic HTML elements following PicoCSS conventions.
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

function getStatusType(status: string): 'success' | 'error' | 'warning' | 'neutral' {
  switch (status) {
    case 'succeeded': return 'success'
    case 'failed': return 'error'
    case 'running': return 'warning'
    default: return 'neutral'
  }
}

function formatDuration(ms: number | null): string {
  if (ms === null) return '-'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(2)}s`
}
</script>

<template>
  <section data-animate="fade-in">
    <header class="page-header">
      <h1>Function Calls</h1>
      <p>Execution history for all functions</p>
    </header>
    
    <!-- Filters - using Pico's grid for layout -->
    <article class="filters">
      <div class="grid">
        <label>
          Function
          <select v-model="filters.function_name">
            <option value="">All Functions</option>
            <option v-for="fn in functionsStore.functions" :key="fn.name" :value="fn.name">
              {{ fn.name }}
            </option>
          </select>
        </label>
        
        <label>
          Status
          <select v-model="filters.status">
            <option value="">All Statuses</option>
            <option value="succeeded">Succeeded</option>
            <option value="failed">Failed</option>
            <option value="running">Running</option>
          </select>
        </label>
        
        <label>
          Trigger
          <select v-model="filters.trigger_type">
            <option value="">All Triggers</option>
            <option value="manual">Manual</option>
            <option value="schedule">Schedule</option>
          </select>
        </label>
      </div>
      <button class="secondary" @click="applyFilters">
        Apply Filters
      </button>
    </article>
    
    <!-- Loading State -->
    <article v-if="functionsStore.loading" aria-busy="true">
      Loading function calls...
    </article>
    
    <!-- Empty State -->
    <article v-else-if="functionsStore.functionCalls.length === 0">
      <div data-empty data-empty-icon="📜">
        <p>No function calls yet</p>
        <p><small class="text-muted">Function calls will appear here when functions are invoked.</small></p>
      </div>
    </article>
    
    <!-- Function Calls Table -->
    <article v-else>
      <table>
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
            <td><code>{{ call.function_name }}</code></td>
            <td>
              <mark :data-status="getStatusType(call.status)">
                {{ call.status }}
              </mark>
            </td>
            <td>
              <mark data-status="neutral">{{ call.trigger_type }}</mark>
            </td>
            <td><small class="text-muted">{{ formatDuration(call.duration_ms) }}</small></td>
            <td><small class="text-muted">
              {{ call.started_at ? new Date(call.started_at).toLocaleString() : '-' }}
            </small></td>
            <td>
              <small v-if="call.error_message" class="text-error">
                {{ call.error_type }}: {{ call.error_message.slice(0, 50) }}...
              </small>
              <small v-else class="text-muted">-</small>
            </td>
          </tr>
        </tbody>
      </table>
      
      <!-- Pagination -->
      <footer v-if="total > pageSize">
        <button
          class="small secondary"
          :disabled="page === 1"
          @click="page--; loadCalls()"
        >
          Previous
        </button>
        <small class="text-muted">
          Page {{ page }} of {{ Math.ceil(total / pageSize) }} ({{ total }} total)
        </small>
        <button
          class="small secondary"
          :disabled="page >= Math.ceil(total / pageSize)"
          @click="page++; loadCalls()"
        >
          Next
        </button>
      </footer>
    </article>
  </section>
</template>

<style scoped>
.filters {
  margin-bottom: var(--tb-spacing-lg);
}

.filters .grid {
  margin-bottom: var(--tb-spacing-md);
}

article > footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: var(--tb-spacing-md);
  padding-top: var(--tb-spacing-md);
  border-top: 1px solid var(--tb-border);
}
</style>
