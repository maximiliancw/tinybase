<script setup lang="ts">
/**
 * Collections View
 * 
 * List and manage data collections.
 */
import { onMounted, ref } from 'vue'
import { useCollectionsStore } from '../stores/collections'
import { useAuthStore } from '../stores/auth'

const collectionsStore = useCollectionsStore()
const authStore = useAuthStore()

const showCreateModal = ref(false)
const newCollection = ref({
  name: '',
  label: '',
  schemaText: '{\n  "fields": [\n    {\n      "name": "title",\n      "type": "string",\n      "required": true\n    }\n  ]\n}',
})

onMounted(async () => {
  await collectionsStore.fetchCollections()
})

async function handleCreate() {
  try {
    const schema = JSON.parse(newCollection.value.schemaText)
    await collectionsStore.createCollection({
      name: newCollection.value.name,
      label: newCollection.value.label,
      schema,
    })
    showCreateModal.value = false
    newCollection.value = {
      name: '',
      label: '',
      schemaText: '{\n  "fields": [\n    {\n      "name": "title",\n      "type": "string",\n      "required": true\n    }\n  ]\n}',
    }
  } catch (err) {
    alert('Invalid schema JSON')
  }
}

async function handleDelete(name: string) {
  if (confirm(`Are you sure you want to delete collection "${name}"? This will delete all records.`)) {
    await collectionsStore.deleteCollection(name)
  }
}
</script>

<template>
  <div class="fade-in">
    <header class="page-header flex justify-between items-center">
      <div>
        <h1>Collections</h1>
        <p>Manage your data collections</p>
      </div>
      <button v-if="authStore.isAdmin" class="btn btn-primary" @click="showCreateModal = true">
        + New Collection
      </button>
    </header>
    
    <div v-if="collectionsStore.loading" class="card">
      <div class="flex items-center gap-2">
        <span class="spinner"></span>
        Loading collections...
      </div>
    </div>
    
    <div v-else-if="collectionsStore.collections.length === 0" class="card">
      <div class="empty-state">
        <div class="empty-state-icon">📁</div>
        <p>No collections yet</p>
        <p class="text-muted">Create your first collection to start storing data.</p>
        <button v-if="authStore.isAdmin" class="btn btn-primary mt-2" @click="showCreateModal = true">
          Create Collection
        </button>
      </div>
    </div>
    
    <div v-else class="card">
      <table class="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Label</th>
            <th>Fields</th>
            <th>Created</th>
            <th v-if="authStore.isAdmin">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="collection in collectionsStore.collections" :key="collection.id">
            <td>
              <router-link :to="`/collections/${collection.name}`" class="text-primary">
                {{ collection.name }}
              </router-link>
            </td>
            <td>{{ collection.label }}</td>
            <td>{{ collection.schema?.fields?.length || 0 }} fields</td>
            <td class="text-muted">{{ new Date(collection.created_at).toLocaleDateString() }}</td>
            <td v-if="authStore.isAdmin">
              <button class="btn btn-sm btn-danger" @click="handleDelete(collection.name)">
                Delete
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    
    <!-- Create Collection Modal -->
    <dialog v-if="showCreateModal" open class="modal">
      <article class="card" style="max-width: 600px; margin: 2rem auto;">
        <header class="card-header">
          <h3 class="card-title">Create Collection</h3>
          <button class="btn btn-sm btn-secondary" @click="showCreateModal = false">✕</button>
        </header>
        
        <form @submit.prevent="handleCreate">
          <div class="form-group">
            <label class="form-label" for="name">Name (snake_case)</label>
            <input
              id="name"
              v-model="newCollection.name"
              type="text"
              class="form-input"
              pattern="[a-z][a-z0-9_]*"
              placeholder="my_collection"
              required
            />
          </div>
          
          <div class="form-group">
            <label class="form-label" for="label">Label</label>
            <input
              id="label"
              v-model="newCollection.label"
              type="text"
              class="form-input"
              placeholder="My Collection"
              required
            />
          </div>
          
          <div class="form-group">
            <label class="form-label" for="schema">Schema (JSON)</label>
            <textarea
              id="schema"
              v-model="newCollection.schemaText"
              class="form-input"
              rows="10"
              style="font-family: monospace; font-size: 0.875rem;"
              required
            ></textarea>
          </div>
          
          <div v-if="collectionsStore.error" class="text-error mb-2">
            {{ collectionsStore.error }}
          </div>
          
          <div class="flex gap-2 justify-between">
            <button type="button" class="btn btn-secondary" @click="showCreateModal = false">
              Cancel
            </button>
            <button type="submit" class="btn btn-primary" :disabled="collectionsStore.loading">
              Create Collection
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

.text-primary {
  color: var(--tb-primary);
}
</style>

