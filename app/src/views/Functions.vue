<script setup lang="ts">
/**
 * Functions View
 * 
 * View and invoke registered functions.
 */
import { onMounted, ref } from 'vue'
import { useFunctionsStore, type FunctionInfo } from '../stores/functions'
import { useAuthStore } from '../stores/auth'

const functionsStore = useFunctionsStore()
const authStore = useAuthStore()

const showCallModal = ref(false)
const selectedFunction = ref<FunctionInfo | null>(null)
const callPayload = ref('{}')
const callResult = ref<any>(null)
const callError = ref<string | null>(null)

onMounted(async () => {
  if (authStore.isAdmin) {
    await functionsStore.fetchAdminFunctions()
  } else {
    await functionsStore.fetchFunctions()
  }
})

function openCallModal(fn: FunctionInfo) {
  selectedFunction.value = fn
  callPayload.value = '{}'
  callResult.value = null
  callError.value = null
  showCallModal.value = true
}

async function handleCall() {
  if (!selectedFunction.value) return
  
  callError.value = null
  callResult.value = null
  
  try {
    const payload = JSON.parse(callPayload.value)
    const result = await functionsStore.callFunction(selectedFunction.value.name, payload)
    callResult.value = result
  } catch (err: any) {
    callError.value = err.response?.data?.detail || err.message || 'Call failed'
  }
}

function getAuthBadgeClass(auth: string) {
  switch (auth) {
    case 'public': return 'badge-success'
    case 'auth': return 'badge-info'
    case 'admin': return 'badge-warning'
    default: return 'badge-neutral'
  }
}

const displayFunctions = () => {
  return authStore.isAdmin ? functionsStore.adminFunctions : functionsStore.functions
}
</script>

<template>
  <div class="fade-in">
    <header class="page-header">
      <h1>Functions</h1>
      <p>Registered server-side functions</p>
    </header>
    
    <div v-if="functionsStore.loading" class="card">
      <div class="flex items-center gap-2">
        <span class="spinner"></span>
        Loading functions...
      </div>
    </div>
    
    <div v-else-if="displayFunctions().length === 0" class="card">
      <div class="empty-state">
        <div class="empty-state-icon">⚡</div>
        <p>No functions registered</p>
        <p class="text-muted">Define functions in functions.py using the @register decorator.</p>
      </div>
    </div>
    
    <div v-else class="card">
      <table class="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Description</th>
            <th>Auth</th>
            <th>Tags</th>
            <th v-if="authStore.isAdmin">Module</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="fn in displayFunctions()" :key="fn.name">
            <td style="font-family: monospace;">{{ fn.name }}</td>
            <td class="text-muted">{{ fn.description || '-' }}</td>
            <td>
              <span :class="['badge', getAuthBadgeClass(fn.auth)]">
                {{ fn.auth }}
              </span>
            </td>
            <td>
              <span
                v-for="tag in fn.tags"
                :key="tag"
                class="badge badge-neutral"
                style="margin-right: 0.25rem;"
              >
                {{ tag }}
              </span>
              <span v-if="fn.tags.length === 0" class="text-muted">-</span>
            </td>
            <td v-if="authStore.isAdmin" class="text-muted" style="font-size: 0.75rem;">
              {{ fn.module }}
            </td>
            <td>
              <button class="btn btn-sm btn-primary" @click="openCallModal(fn)">
                Call
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    
    <!-- Call Function Modal -->
    <dialog v-if="showCallModal" open class="modal">
      <article class="card" style="max-width: 600px; margin: 2rem auto;">
        <header class="card-header">
          <h3 class="card-title">Call: {{ selectedFunction?.name }}</h3>
          <button class="btn btn-sm btn-secondary" @click="showCallModal = false">✕</button>
        </header>
        
        <div v-if="selectedFunction?.description" class="text-muted mb-2">
          {{ selectedFunction.description }}
        </div>
        
        <form @submit.prevent="handleCall">
          <div class="form-group">
            <label class="form-label" for="payload">Payload (JSON)</label>
            <textarea
              id="payload"
              v-model="callPayload"
              class="form-input"
              rows="6"
              style="font-family: monospace; font-size: 0.875rem;"
            ></textarea>
          </div>
          
          <button type="submit" class="btn btn-primary" :disabled="functionsStore.loading">
            <span v-if="functionsStore.loading" class="spinner"></span>
            <span v-else>Execute</span>
          </button>
        </form>
        
        <!-- Result Display -->
        <div v-if="callResult" class="mt-3">
          <h4>Result</h4>
          <div
            :class="['badge', callResult.status === 'succeeded' ? 'badge-success' : 'badge-error']"
            style="margin-bottom: 0.5rem;"
          >
            {{ callResult.status }}
          </div>
          <div v-if="callResult.duration_ms" class="text-muted" style="font-size: 0.75rem;">
            Duration: {{ callResult.duration_ms }}ms
          </div>
          <pre v-if="callResult.result" style="background: var(--tb-bg-dark); padding: 1rem; border-radius: 0.5rem; overflow: auto; margin-top: 0.5rem;">{{ JSON.stringify(callResult.result, null, 2) }}</pre>
          <div v-if="callResult.error_message" class="text-error mt-2">
            <strong>{{ callResult.error_type }}:</strong> {{ callResult.error_message }}
          </div>
        </div>
        
        <div v-if="callError" class="text-error mt-2">
          {{ callError }}
        </div>
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
  max-height: 90vh;
  overflow-y: auto;
}

pre {
  font-size: 0.875rem;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>

