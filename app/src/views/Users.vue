<script setup lang="ts">
/**
 * Users View
 * 
 * Manage user accounts (admin only).
 */
import { onMounted, ref } from 'vue'
import { useUsersStore } from '../stores/users'

const usersStore = useUsersStore()

const showCreateModal = ref(false)
const newUser = ref({
  email: '',
  password: '',
  is_admin: false,
})

onMounted(async () => {
  await usersStore.fetchUsers()
})

async function handleCreate() {
  const result = await usersStore.createUser(newUser.value)
  if (result) {
    showCreateModal.value = false
    newUser.value = { email: '', password: '', is_admin: false }
  }
}

async function handleToggleAdmin(userId: string, currentStatus: boolean) {
  await usersStore.updateUser(userId, { is_admin: !currentStatus })
}

async function handleDelete(userId: string) {
  if (confirm('Are you sure you want to delete this user?')) {
    await usersStore.deleteUser(userId)
  }
}
</script>

<template>
  <div class="fade-in">
    <header class="page-header flex justify-between items-center">
      <div>
        <h1>Users</h1>
        <p>Manage user accounts</p>
      </div>
      <button class="btn btn-primary" @click="showCreateModal = true">
        + New User
      </button>
    </header>
    
    <div v-if="usersStore.loading" class="card">
      <div class="flex items-center gap-2">
        <span class="spinner"></span>
        Loading users...
      </div>
    </div>
    
    <div v-else class="card">
      <table class="data-table">
        <thead>
          <tr>
            <th>Email</th>
            <th>Role</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in usersStore.users" :key="user.id">
            <td>{{ user.email }}</td>
            <td>
              <span :class="['badge', user.is_admin ? 'badge-info' : 'badge-neutral']">
                {{ user.is_admin ? 'Admin' : 'User' }}
              </span>
            </td>
            <td class="text-muted">
              {{ new Date(user.created_at).toLocaleDateString() }}
            </td>
            <td class="flex gap-1">
              <button
                class="btn btn-sm btn-secondary"
                @click="handleToggleAdmin(user.id, user.is_admin)"
              >
                {{ user.is_admin ? 'Remove Admin' : 'Make Admin' }}
              </button>
              <button class="btn btn-sm btn-danger" @click="handleDelete(user.id)">
                Delete
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    
    <!-- Create User Modal -->
    <dialog v-if="showCreateModal" open class="modal">
      <article class="card" style="max-width: 400px; margin: 2rem auto;">
        <header class="card-header">
          <h3 class="card-title">Create User</h3>
          <button class="btn btn-sm btn-secondary" @click="showCreateModal = false">✕</button>
        </header>
        
        <form @submit.prevent="handleCreate">
          <div class="form-group">
            <label class="form-label" for="email">Email</label>
            <input
              id="email"
              v-model="newUser.email"
              type="email"
              class="form-input"
              required
            />
          </div>
          
          <div class="form-group">
            <label class="form-label" for="password">Password</label>
            <input
              id="password"
              v-model="newUser.password"
              type="password"
              class="form-input"
              minlength="8"
              required
            />
          </div>
          
          <div class="form-group">
            <label class="flex items-center gap-2">
              <input type="checkbox" v-model="newUser.is_admin" />
              Admin privileges
            </label>
          </div>
          
          <div v-if="usersStore.error" class="text-error mb-2">
            {{ usersStore.error }}
          </div>
          
          <div class="flex gap-2 justify-between">
            <button type="button" class="btn btn-secondary" @click="showCreateModal = false">
              Cancel
            </button>
            <button type="submit" class="btn btn-primary" :disabled="usersStore.loading">
              Create User
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

