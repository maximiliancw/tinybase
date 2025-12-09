<script setup lang="ts">
/**
 * Schedules View
 * 
 * Manage function schedules (admin only).
 * Uses semantic HTML elements following PicoCSS conventions.
 */
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useFunctionsStore, generateTemplateFromSchema } from '../stores/functions'

const route = useRoute()
const functionsStore = useFunctionsStore()

const showCreateModal = ref(false)
const loadingSchema = ref(false)
const newSchedule = ref({
  name: '',
  function_name: '',
  method: 'interval' as 'once' | 'interval' | 'cron',
  timezone: 'UTC',
  // Interval fields
  unit: 'hours',
  value: 1,
  // Cron fields
  cron: '0 * * * *',
  // Once fields
  date: '',
  time: '',
  // Input data for the function
  input_data: '{}',
})

// Watch for function selection changes to fetch schema
watch(() => newSchedule.value.function_name, async (functionName) => {
  if (!functionName) {
    newSchedule.value.input_data = '{}'
    return
  }
  
  loadingSchema.value = true
  try {
    const schema = await functionsStore.fetchFunctionSchema(functionName)
    if (schema?.input_schema) {
      const template = generateTemplateFromSchema(schema.input_schema)
      newSchedule.value.input_data = JSON.stringify(template, null, 2)
    } else {
      newSchedule.value.input_data = '{}'
    }
  } catch {
    newSchedule.value.input_data = '{}'
  } finally {
    loadingSchema.value = false
  }
})

onMounted(async () => {
  await functionsStore.fetchSchedules()
  await functionsStore.fetchFunctions()
  if (route.query.action === 'create') {
    showCreateModal.value = true
  }
})

function buildSchedulePayload() {
  const base = {
    timezone: newSchedule.value.timezone,
  }
  
  switch (newSchedule.value.method) {
    case 'interval':
      return {
        ...base,
        method: 'interval',
        unit: newSchedule.value.unit,
        value: newSchedule.value.value,
      }
    case 'cron':
      return {
        ...base,
        method: 'cron',
        cron: newSchedule.value.cron,
      }
    case 'once':
      return {
        ...base,
        method: 'once',
        date: newSchedule.value.date,
        time: newSchedule.value.time,
      }
  }
}

async function handleCreate() {
  let inputData = {}
  try {
    inputData = JSON.parse(newSchedule.value.input_data)
  } catch {
    functionsStore.error = 'Invalid JSON in input data'
    return
  }
  
  const result = await functionsStore.createSchedule({
    name: newSchedule.value.name,
    function_name: newSchedule.value.function_name,
    schedule: buildSchedulePayload(),
    input_data: inputData,
  })
  
  if (result) {
    showCreateModal.value = false
    newSchedule.value = {
      name: '',
      function_name: '',
      method: 'interval',
      timezone: 'UTC',
      unit: 'hours',
      value: 1,
      cron: '0 * * * *',
      date: '',
      time: '',
      input_data: '{}',
    }
  }
}

async function handleToggleActive(scheduleId: string, currentStatus: boolean) {
  await functionsStore.updateSchedule(scheduleId, { is_active: !currentStatus })
}

async function handleDelete(scheduleId: string) {
  if (confirm('Are you sure you want to delete this schedule?')) {
    await functionsStore.deleteSchedule(scheduleId)
  }
}

function formatSchedule(schedule: any): string {
  switch (schedule.method) {
    case 'interval':
      return `Every ${schedule.value} ${schedule.unit}`
    case 'cron':
      return `Cron: ${schedule.cron}`
    case 'once':
      return `Once: ${schedule.date} ${schedule.time}`
    default:
      return 'Unknown'
  }
}
</script>

<template>
  <div data-animate="fade-in">
    <header class="page-header">
      <hgroup>
        <h1>Schedules</h1>
        <p>Manage function schedules</p>
      </hgroup>
      <button @click="showCreateModal = true">
        + New Schedule
      </button>
    </header>
    
    <!-- Loading State -->
    <article v-if="functionsStore.loading" aria-busy="true">
      Loading schedules...
    </article>
    
    <!-- Empty State -->
    <article v-else-if="functionsStore.schedules.length === 0">
      <div data-empty data-empty-icon="⏰">
        <p>No schedules yet</p>
        <p><small class="text-muted">Create schedules to run functions automatically.</small></p>
        <button class="small mt-2" @click="showCreateModal = true">
          Create Schedule
        </button>
      </div>
    </article>
    
    <!-- Schedules Table -->
    <article v-else>
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Function</th>
            <th>Schedule</th>
            <th>Status</th>
            <th>Next Run</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="schedule in functionsStore.schedules" :key="schedule.id">
            <td>{{ schedule.name }}</td>
            <td><code>{{ schedule.function_name }}</code></td>
            <td><small class="text-muted">{{ formatSchedule(schedule.schedule) }}</small></td>
            <td>
              <mark :data-status="schedule.is_active ? 'success' : 'neutral'">
                {{ schedule.is_active ? 'Active' : 'Inactive' }}
              </mark>
            </td>
            <td><small class="text-muted">
              {{ schedule.next_run_at ? new Date(schedule.next_run_at).toLocaleString() : '-' }}
            </small></td>
            <td>
              <div role="group">
                <button
                  class="small secondary"
                  @click="handleToggleActive(schedule.id, schedule.is_active)"
                >
                  {{ schedule.is_active ? 'Pause' : 'Resume' }}
                </button>
                <button class="small contrast" @click="handleDelete(schedule.id)">
                  Delete
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </article>
    
    <!-- Create Schedule Modal -->
    <dialog :open="showCreateModal">
      <article>
        <header>
          <button aria-label="Close" rel="prev" @click="showCreateModal = false"></button>
          <h3>Create Schedule</h3>
        </header>
        
        <form @submit.prevent="handleCreate">
          <label for="name">
            Name
            <input
              id="name"
              v-model="newSchedule.name"
              type="text"
              required
            />
          </label>
          
          <label for="function">
            Function
            <select id="function" v-model="newSchedule.function_name" required>
              <option value="">Select a function</option>
              <option v-for="fn in functionsStore.functions" :key="fn.name" :value="fn.name">
                {{ fn.name }}
              </option>
            </select>
          </label>
          
          <fieldset>
            <legend>Schedule Type</legend>
            <label>
              <input type="radio" v-model="newSchedule.method" value="interval" />
              Interval
            </label>
            <label>
              <input type="radio" v-model="newSchedule.method" value="cron" />
              Cron
            </label>
            <label>
              <input type="radio" v-model="newSchedule.method" value="once" />
              Once
            </label>
          </fieldset>
          
          <!-- Interval Options -->
          <div v-if="newSchedule.method === 'interval'" class="grid">
            <label>
              Value
              <input
                v-model.number="newSchedule.value"
                type="number"
                min="1"
              />
            </label>
            <label>
              Unit
              <select v-model="newSchedule.unit">
                <option value="seconds">Seconds</option>
                <option value="minutes">Minutes</option>
                <option value="hours">Hours</option>
                <option value="days">Days</option>
              </select>
            </label>
          </div>
          
          <!-- Cron Options -->
          <label v-if="newSchedule.method === 'cron'">
            Cron Expression
            <input
              v-model="newSchedule.cron"
              type="text"
              placeholder="0 * * * *"
            />
            <small>Format: minute hour day_of_month month day_of_week</small>
          </label>
          
          <!-- Once Options -->
          <div v-if="newSchedule.method === 'once'" class="grid">
            <label>
              Date
              <input v-model="newSchedule.date" type="date" />
            </label>
            <label>
              Time
              <input v-model="newSchedule.time" type="time" />
            </label>
          </div>
          
          <label>
            Timezone
            <input
              v-model="newSchedule.timezone"
              type="text"
              placeholder="UTC"
            />
          </label>
          
          <!-- Input Data -->
          <label for="input_data">
            Input Data (JSON)
            <textarea
              v-if="loadingSchema"
              id="input_data"
              rows="6"
              disabled
              aria-busy="true"
              class="code-editor"
            >Loading schema...</textarea>
            <textarea
              v-else
              id="input_data"
              v-model="newSchedule.input_data"
              rows="6"
              class="code-editor"
              spellcheck="false"
              placeholder="{}"
            ></textarea>
            <small>Data to pass to the function when executed</small>
          </label>
          
          <small v-if="functionsStore.error" class="text-error">
            {{ functionsStore.error }}
          </small>
          
          <footer>
            <button type="button" class="secondary" @click="showCreateModal = false">
              Cancel
            </button>
            <button type="submit" :aria-busy="functionsStore.loading" :disabled="functionsStore.loading">
              {{ functionsStore.loading ? '' : 'Create Schedule' }}
            </button>
          </footer>
        </form>
      </article>
    </dialog>
  </div>
</template>

<style scoped>
/* Page header layout */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.page-header hgroup {
  margin: 0;
}

.page-header hgroup h1 {
  margin-bottom: var(--tb-spacing-xs);
}

.page-header hgroup p {
  margin: 0;
  color: var(--pico-muted-color);
}

/* Dialog footer buttons */
dialog article footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--tb-spacing-sm);
}

/* Code editor textarea */
.code-editor {
  font-family: ui-monospace, 'SF Mono', 'Cascadia Code', 'Source Code Pro', Menlo, Consolas, monospace;
  font-size: 0.875rem;
  line-height: 1.5;
  tab-size: 2;
  resize: vertical;
}
</style>
