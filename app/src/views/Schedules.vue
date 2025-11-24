<script setup lang="ts">
/**
 * Schedules View
 * 
 * Manage function schedules (admin only).
 */
import { onMounted, ref } from 'vue'
import { useFunctionsStore } from '../stores/functions'

const functionsStore = useFunctionsStore()

const showCreateModal = ref(false)
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
})

onMounted(async () => {
  await functionsStore.fetchSchedules()
  await functionsStore.fetchFunctions()
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
  const result = await functionsStore.createSchedule({
    name: newSchedule.value.name,
    function_name: newSchedule.value.function_name,
    schedule: buildSchedulePayload(),
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
  <div class="fade-in">
    <header class="page-header flex justify-between items-center">
      <div>
        <h1>Schedules</h1>
        <p>Manage function schedules</p>
      </div>
      <button class="btn btn-primary" @click="showCreateModal = true">
        + New Schedule
      </button>
    </header>
    
    <div v-if="functionsStore.loading" class="card">
      <div class="flex items-center gap-2">
        <span class="spinner"></span>
        Loading schedules...
      </div>
    </div>
    
    <div v-else-if="functionsStore.schedules.length === 0" class="card">
      <div class="empty-state">
        <div class="empty-state-icon">⏰</div>
        <p>No schedules yet</p>
        <p class="text-muted">Create schedules to run functions automatically.</p>
        <button class="btn btn-primary btn-sm mt-2" @click="showCreateModal = true">
          Create Schedule
        </button>
      </div>
    </div>
    
    <div v-else class="card">
      <table class="data-table">
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
            <td style="font-family: monospace;">{{ schedule.function_name }}</td>
            <td class="text-muted">{{ formatSchedule(schedule.schedule) }}</td>
            <td>
              <span :class="['badge', schedule.is_active ? 'badge-success' : 'badge-neutral']">
                {{ schedule.is_active ? 'Active' : 'Inactive' }}
              </span>
            </td>
            <td class="text-muted">
              {{ schedule.next_run_at ? new Date(schedule.next_run_at).toLocaleString() : '-' }}
            </td>
            <td class="flex gap-1">
              <button
                class="btn btn-sm btn-secondary"
                @click="handleToggleActive(schedule.id, schedule.is_active)"
              >
                {{ schedule.is_active ? 'Pause' : 'Resume' }}
              </button>
              <button class="btn btn-sm btn-danger" @click="handleDelete(schedule.id)">
                Delete
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    
    <!-- Create Schedule Modal -->
    <dialog v-if="showCreateModal" open class="modal">
      <article class="card" style="max-width: 500px; margin: 2rem auto;">
        <header class="card-header">
          <h3 class="card-title">Create Schedule</h3>
          <button class="btn btn-sm btn-secondary" @click="showCreateModal = false">✕</button>
        </header>
        
        <form @submit.prevent="handleCreate">
          <div class="form-group">
            <label class="form-label" for="name">Name</label>
            <input
              id="name"
              v-model="newSchedule.name"
              type="text"
              class="form-input"
              required
            />
          </div>
          
          <div class="form-group">
            <label class="form-label" for="function">Function</label>
            <select
              id="function"
              v-model="newSchedule.function_name"
              class="form-input"
              required
            >
              <option value="">Select a function</option>
              <option v-for="fn in functionsStore.functions" :key="fn.name" :value="fn.name">
                {{ fn.name }}
              </option>
            </select>
          </div>
          
          <div class="form-group">
            <label class="form-label">Schedule Type</label>
            <div class="flex gap-2">
              <label class="flex items-center gap-1">
                <input type="radio" v-model="newSchedule.method" value="interval" />
                Interval
              </label>
              <label class="flex items-center gap-1">
                <input type="radio" v-model="newSchedule.method" value="cron" />
                Cron
              </label>
              <label class="flex items-center gap-1">
                <input type="radio" v-model="newSchedule.method" value="once" />
                Once
              </label>
            </div>
          </div>
          
          <!-- Interval Options -->
          <div v-if="newSchedule.method === 'interval'" class="form-group">
            <label class="form-label">Interval</label>
            <div class="flex gap-2">
              <input
                v-model.number="newSchedule.value"
                type="number"
                class="form-input"
                min="1"
                style="width: 100px;"
              />
              <select v-model="newSchedule.unit" class="form-input">
                <option value="seconds">Seconds</option>
                <option value="minutes">Minutes</option>
                <option value="hours">Hours</option>
                <option value="days">Days</option>
              </select>
            </div>
          </div>
          
          <!-- Cron Options -->
          <div v-if="newSchedule.method === 'cron'" class="form-group">
            <label class="form-label" for="cron">Cron Expression</label>
            <input
              id="cron"
              v-model="newSchedule.cron"
              type="text"
              class="form-input"
              placeholder="0 * * * *"
            />
            <p class="text-muted" style="font-size: 0.75rem; margin-top: 0.25rem;">
              Format: minute hour day_of_month month day_of_week
            </p>
          </div>
          
          <!-- Once Options -->
          <div v-if="newSchedule.method === 'once'" class="form-group">
            <label class="form-label">Date and Time</label>
            <div class="flex gap-2">
              <input
                v-model="newSchedule.date"
                type="date"
                class="form-input"
              />
              <input
                v-model="newSchedule.time"
                type="time"
                class="form-input"
              />
            </div>
          </div>
          
          <div class="form-group">
            <label class="form-label" for="timezone">Timezone</label>
            <input
              id="timezone"
              v-model="newSchedule.timezone"
              type="text"
              class="form-input"
              placeholder="UTC"
            />
          </div>
          
          <div v-if="functionsStore.error" class="text-error mb-2">
            {{ functionsStore.error }}
          </div>
          
          <div class="flex gap-2 justify-between">
            <button type="button" class="btn btn-secondary" @click="showCreateModal = false">
              Cancel
            </button>
            <button type="submit" class="btn btn-primary" :disabled="functionsStore.loading">
              Create Schedule
            </button>
          </div>
        </form>
      </article>
    </dialog>
  </div>
</template>

<style scoped>
.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  border: none;
  padding: 0;
  margin: 0;
  width: 100%;
  height: 100%;
  max-width: none;
  max-height: none;
}

.modal article {
  background: var(--tb-bg-card);
  width: 100%;
}
</style>

