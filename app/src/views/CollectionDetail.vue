<script setup lang="ts">
/**
 * Collection Detail View
 * 
 * View and manage records in a collection.
 */
import { onMounted, ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useCollectionsStore, type Record } from '../stores/collections'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const collectionsStore = useCollectionsStore()
const authStore = useAuthStore()

const collectionName = computed(() => route.params.name as string)
const records = ref<Record[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20

const showCreateModal = ref(false)
const newRecordData = ref('{}')

onMounted(async () => {
  await collectionsStore.fetchCollection(collectionName.value)
  await loadRecords()
})

async function loadRecords() {
  const result = await collectionsStore.fetchRecords(
    collectionName.value,
    pageSize,
    (page.value - 1) * pageSize
  )
  records.value = result.records
  total.value = result.total
}

async function handleCreateRecord() {
  try {
    const data = JSON.parse(newRecordData.value)
    await collectionsStore.createRecord(collectionName.value, data)
    showCreateModal.value = false
    newRecordData.value = '{}'
    await loadRecords()
  } catch (err) {
    alert('Invalid JSON data')
  }
}

async function handleDeleteRecord(recordId: string) {
  if (confirm('Are you sure you want to delete this record?')) {
    await collectionsStore.deleteRecord(collectionName.value, recordId)
    await loadRecords()
  }
}

function getFieldNames() {
  return collectionsStore.currentCollection?.schema?.fields?.map(f => f.name) || []
}
</script>

<template>
  <div class="fade-in">
    <header class="page-header flex justify-between items-center">
      <div>
        <h1>{{ collectionsStore.currentCollection?.label || collectionName }}</h1>
        <p>Collection: {{ collectionName }}</p>
      </div>
      <button class="btn btn-primary" @click="showCreateModal = true">
        + New Record
      </button>
    </header>
    
    <!-- Schema Info -->
    <div class="card mb-3">
      <div class="card-header">
        <h3 class="card-title">Schema</h3>
      </div>
      <div v-if="collectionsStore.currentCollection" class="flex gap-2" style="flex-wrap: wrap;">
        <span
          v-for="field in collectionsStore.currentCollection.schema?.fields || []"
          :key="field.name"
          class="badge badge-neutral"
        >
          {{ field.name }}
          <span class="text-muted">({{ field.type }})</span>
          <span v-if="field.required" class="text-warning">*</span>
        </span>
      </div>
    </div>
    
    <!-- Records Table -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">Records ({{ total }})</h3>
      </div>
      
      <div v-if="collectionsStore.loading" class="flex items-center gap-2">
        <span class="spinner"></span>
        Loading records...
      </div>
      
      <div v-else-if="records.length === 0" class="empty-state">
        <div class="empty-state-icon">📄</div>
        <p>No records yet</p>
        <button class="btn btn-primary btn-sm mt-2" @click="showCreateModal = true">
          Create Record
        </button>
      </div>
      
      <div v-else style="overflow-x: auto;">
        <table class="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th v-for="field in getFieldNames().slice(0, 5)" :key="field">
                {{ field }}
              </th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="record in records" :key="record.id">
              <td class="text-muted" style="font-family: monospace; font-size: 0.75rem;">
                {{ record.id.slice(0, 8) }}...
              </td>
              <td v-for="field in getFieldNames().slice(0, 5)" :key="field">
                {{ typeof record.data[field] === 'object' ? JSON.stringify(record.data[field]) : record.data[field] }}
              </td>
              <td class="text-muted">
                {{ new Date(record.created_at).toLocaleDateString() }}
              </td>
              <td>
                <button
                  class="btn btn-sm btn-danger"
                  @click="handleDeleteRecord(record.id)"
                  :disabled="!authStore.isAdmin && record.owner_id !== authStore.user?.id"
                >
                  Delete
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      
      <!-- Pagination -->
      <div v-if="total > pageSize" class="flex justify-between items-center mt-2">
        <button
          class="btn btn-sm btn-secondary"
          :disabled="page === 1"
          @click="page--; loadRecords()"
        >
          Previous
        </button>
        <span class="text-muted">
          Page {{ page }} of {{ Math.ceil(total / pageSize) }}
        </span>
        <button
          class="btn btn-sm btn-secondary"
          :disabled="page >= Math.ceil(total / pageSize)"
          @click="page++; loadRecords()"
        >
          Next
        </button>
      </div>
    </div>
    
    <!-- Create Record Modal -->
    <dialog v-if="showCreateModal" open class="modal">
      <article class="card" style="max-width: 600px; margin: 2rem auto;">
        <header class="card-header">
          <h3 class="card-title">Create Record</h3>
          <button class="btn btn-sm btn-secondary" @click="showCreateModal = false">✕</button>
        </header>
        
        <form @submit.prevent="handleCreateRecord">
          <div class="form-group">
            <label class="form-label" for="data">Record Data (JSON)</label>
            <textarea
              id="data"
              v-model="newRecordData"
              class="form-input"
              rows="10"
              style="font-family: monospace; font-size: 0.875rem;"
              required
            ></textarea>
            <p class="text-muted" style="font-size: 0.75rem; margin-top: 0.5rem;">
              Fields: {{ getFieldNames().join(', ') }}
            </p>
          </div>
          
          <div v-if="collectionsStore.error" class="text-error mb-2">
            {{ collectionsStore.error }}
          </div>
          
          <div class="flex gap-2 justify-between">
            <button type="button" class="btn btn-secondary" @click="showCreateModal = false">
              Cancel
            </button>
            <button type="submit" class="btn btn-primary" :disabled="collectionsStore.loading">
              Create Record
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

