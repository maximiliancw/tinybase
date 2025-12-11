<script setup lang="ts">
/**
 * Auth Portal Password Reset Request View
 *
 * Allows users to request a password reset email.
 */
import { ref, onMounted } from "vue";
import { usePortalStore } from "../../stores/portal";
import { api } from "../../api";
import { usePreviewParams } from "../../composables/usePreviewParams";

const portalStore = usePortalStore();
const { withPreviewParams } = usePreviewParams();

const email = ref("");
const errorMessage = ref("");
const successMessage = ref("");
const loading = ref(false);

onMounted(async () => {
  await portalStore.fetchConfig();
});

async function handleRequestReset() {
  errorMessage.value = "";
  successMessage.value = "";
  loading.value = true;

  try {
    await api.post("/api/auth/password-reset/request", {
      email: email.value,
    });

    // Always show success message (security best practice)
    successMessage.value =
      "If that email exists, a password reset link has been sent.";
    email.value = "";
  } catch (err: any) {
    errorMessage.value =
      err.response?.data?.detail || "Failed to request password reset";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div
    class="auth-layout"
    :data-has-background="
      portalStore.config.background_image_url ? true : undefined
    "
  >
    <article class="auth-card" data-animate="fade-in">
      <!-- Logo -->
      <div class="auth-logo">
        <img
          v-if="portalStore.config.logo_url"
          :src="portalStore.config.logo_url"
          alt="Logo"
        />
        <h1>{{ portalStore.config.instance_name }}</h1>
        <p>Reset your password</p>
      </div>

      <!-- Reset Request Form -->
      <form @submit.prevent="handleRequestReset" class="auth-form">
        <p>
          Enter your email address and we'll send you a link to reset your
          password.
        </p>

        <label for="email">
          Email
          <input
            id="email"
            v-model="email"
            type="email"
            placeholder="user@example.com"
            required
            autocomplete="email"
          />
        </label>

        <!-- Error message -->
        <div v-if="errorMessage" class="error-message">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {{ errorMessage }}
        </div>

        <!-- Success message -->
        <div v-if="successMessage" class="success-message">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
            <polyline points="22 4 12 14.01 9 11.01" />
          </svg>
          {{ successMessage }}
        </div>

        <button type="submit" :aria-busy="loading" :disabled="loading">
          {{ loading ? "" : "Send Reset Link" }}
        </button>
      </form>

      <!-- Links -->
      <div class="auth-links">
        <router-link :to="withPreviewParams('/auth/login')"
          >Back to sign in</router-link
        >
      </div>

      <!-- Footer -->
      <div class="auth-footer">
        <small>Powered by TinyBase</small>
      </div>
    </article>
  </div>
</template>

<style scoped>
.auth-layout {
  width: 100%;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--tb-spacing-lg);
}
</style>
