<script setup lang="ts">
/**
 * Auth Portal Register View
 *
 * Public-facing registration page.
 */
import { ref, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { api } from "../../api";
import { usePortalStore } from "../../stores/portal";
import { usePreviewParams } from "../../composables/usePreviewParams";

const router = useRouter();
const route = useRoute();
const portalStore = usePortalStore();
const { withPreviewParams } = usePreviewParams();

const email = ref("");
const password = ref("");
const confirmPassword = ref("");
const errorMessage = ref("");
const successMessage = ref("");
const loading = ref(false);

function isValidAbsoluteUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

onMounted(async () => {
  await portalStore.fetchConfig();

  // Redirect if registration is disabled
  if (!portalStore.config.registration_enabled) {
    router.push(withPreviewParams("/auth/login"));
  }
});

async function handleRegister() {
  errorMessage.value = "";
  successMessage.value = "";
  loading.value = true;

  // Validate passwords match
  if (password.value !== confirmPassword.value) {
    errorMessage.value = "Passwords do not match";
    loading.value = false;
    return;
  }

  try {
    await api.post("/api/auth/register", {
      email: email.value,
      password: password.value,
    });

    successMessage.value = "Registration successful! Redirecting...";

    // Clear form
    email.value = "";
    password.value = "";
    confirmPassword.value = "";

    // Get redirect URL
    const redirectParam = route.query.redirect as string | undefined;
    const configuredUrl = portalStore.config.register_redirect_url;

    let redirectUrl: string | null = null;
    if (redirectParam && isValidAbsoluteUrl(redirectParam)) {
      redirectUrl = redirectParam;
    } else if (configuredUrl && isValidAbsoluteUrl(configuredUrl)) {
      redirectUrl = configuredUrl;
    }

    // Redirect after 1 second
    setTimeout(() => {
      if (redirectUrl && isValidAbsoluteUrl(redirectUrl)) {
        // Absolute URL - redirect to it
        window.location.href = redirectUrl;
      } else {
        // No valid redirect URL configured - show error
        successMessage.value = "";
        errorMessage.value =
          "Registration successful, but redirect URL is not configured. Please contact your administrator.";
      }
    }, 1000);
  } catch (err: any) {
    errorMessage.value = err.response?.data?.detail || "Registration failed";
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
        <p>Create a new account</p>
      </div>

      <!-- Register Form -->
      <form @submit.prevent="handleRegister" class="auth-form">
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

        <label for="password">
          Password
          <input
            id="password"
            v-model="password"
            type="password"
            placeholder="••••••••"
            required
            autocomplete="new-password"
            minlength="8"
          />
          <small>Must be at least 8 characters</small>
        </label>

        <label for="confirmPassword">
          Confirm Password
          <input
            id="confirmPassword"
            v-model="confirmPassword"
            type="password"
            placeholder="••••••••"
            required
            autocomplete="new-password"
            minlength="8"
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
          {{ loading ? "" : "Create Account" }}
        </button>
      </form>

      <!-- Links -->
      <div class="auth-links">
        <router-link :to="withPreviewParams('/auth/login')"
          >Already have an account? Sign in</router-link
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
