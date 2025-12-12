<script setup lang="ts">
/**
 * Function Calls View
 * 
 * View function call history (admin only).
 * Uses semantic HTML elements following PicoCSS conventions.
 */
import { onMounted, ref, computed, h } from 'vue'
import { useFunctionsStore } from '../stores/functions'
import DataTable from '../components/DataTable.vue'

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

const functionCallColumns = computed(() => [
  {
    key: 'function_name',
    label: 'Function',
    render: (value: any) => h('code', value),
  },
  {
    key: 'status',
    label: 'Status',
    render: (value: any) => h('mark', { 'data-status': getStatusType(value) }, value),
  },
  {
    key: 'trigger_type',
    label: 'Trigger',
    render: (value: any) => h('mark', { 'data-status': 'neutral' }, value),
  },
  {
    key: 'duration_ms',
    label: 'Duration',
    render: (value: any) => h('small', { class: 'text-muted' }, formatDuration(value)),
  },
  {
    key: 'started_at',
    label: 'Started',
    render: (value: any) => h('small', { class: 'text-muted' }, value ? new Date(value).toLocaleString() : '-'),
  },
  {
    key: 'error',
    label: 'Error',
    render: (_value: any, row: any) => {
      if (row.error_message) {
        return h('small', { class: 'text-error' }, `${row.error_type}: ${row.error_message.slice(0, 50)}...`);
      }
      return h('small', { class: 'text-muted' }, '-');
    },
  },
])
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
      <DataTable
        :data="functionsStore.functionCalls"
        :columns="functionCallColumns"
        :paginated="false"
        search-placeholder="Search function calls..."
      />
      
      <!-- Server-side Pagination -->
      <footer v-if="total > pageSize" class="server-pagination">
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

.server-pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: var(--tb-spacing-md);
  padding-top: var(--tb-spacing-md);
  border-top: 1px solid var(--tb-border);
}
</style>
