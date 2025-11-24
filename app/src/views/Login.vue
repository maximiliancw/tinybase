<script setup lang="ts">
/**
 * Login View
 * 
 * Authentication page for admin users.
 */
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const errorMessage = ref('')

async function handleLogin() {
  errorMessage.value = ''
  
  const success = await authStore.login(email.value, password.value)
  
  if (success) {
    // Redirect to intended destination or dashboard
    const redirect = route.query.redirect as string || '/'
    router.push(redirect)
  } else {
    errorMessage.value = authStore.error || 'Login failed'
  }
}
</script>

<template>
  <div class="login-container">
    <div class="login-card fade-in">
      <h1>🔐 TinyBase</h1>
      <p class="text-muted" style="text-align: center; margin-bottom: 2rem;">
        Admin Dashboard
      </p>
      
      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label class="form-label" for="email">Email</label>
          <input
            id="email"
            v-model="email"
            type="email"
            class="form-input"
            placeholder="admin@example.com"
            required
            autocomplete="email"
          />
        </div>
        
        <div class="form-group">
          <label class="form-label" for="password">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            class="form-input"
            placeholder="••••••••"
            required
            autocomplete="current-password"
          />
        </div>
        
        <div v-if="errorMessage" class="text-error mb-2">
          {{ errorMessage }}
        </div>
        
        <button
          type="submit"
          class="btn btn-primary"
          style="width: 100%;"
          :disabled="authStore.loading"
        >
          <span v-if="authStore.loading" class="spinner"></span>
          <span v-else>Sign In</span>
        </button>
      </form>
    </div>
  </div>
</template>

