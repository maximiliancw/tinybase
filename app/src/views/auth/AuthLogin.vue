<script setup lang="ts">
/**
 * Auth Portal Login View
 *
 * Public-facing login page for users.
 */
import { ref, onMounted } from "vue";
import { useToast } from "vue-toastification";
import { useRouter, useRoute } from "vue-router";
import { api } from "../../api";
import { usePortalStore } from "../../stores/portal";
import { usePreviewParams } from "../../composables/usePreviewParams";
import Icon from "../../components/Icon.vue";

const toast = useToast();
const router = useRouter();
const route = useRoute();
const portalStore = usePortalStore();
const { withPreviewParams } = usePreviewParams();

const email = ref("");
const password = ref("");
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
});

function getRedirectUrl(): string {
  // Check for redirect query parameter first (takes precedence)
  const redirectParam = route.query.redirect as string | undefined;
  if (redirectParam && isValidAbsoluteUrl(redirectParam)) {
    return redirectParam;
  }
  // Use configured redirect URL (required when portal is enabled)
  const configuredUrl = portalStore.config.login_redirect_url;
  if (configuredUrl && isValidAbsoluteUrl(configuredUrl)) {
    return configuredUrl;
  }
  // No valid redirect URL - show error
  throw new Error(
    "No valid redirect URL configured. Please contact your administrator."
  );
}

async function handleLogin() {
  loading.value = true;

  try {
    const response = await api.post("/api/auth/login", {
      email: email.value,
      password: password.value,
    });

    // Store JWT tokens
    localStorage.setItem("tb_access_token", response.data.access_token);
    localStorage.setItem("tb_refresh_token", response.data.refresh_token);

    // Redirect to configured URL or query parameter
    try {
      const redirectUrl = getRedirectUrl();
      // Validate redirect URL - must be absolute URL
      if (isValidAbsoluteUrl(redirectUrl)) {
        window.location.href = redirectUrl;
      } else {
        throw new Error("Invalid redirect URL");
      }
    } catch (err: any) {
      toast.error(
        err.message ||
          "Redirect configuration error. Please contact your administrator."
      );
      loading.value = false;
      return;
    }
  } catch (err: any) {
    toast.error(err.response?.data?.detail || "Login failed");
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
        <p>Sign in to your account</p>
      </div>

      <!-- Login Form -->
      <form @submit.prevent="handleLogin" class="auth-form">
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
            autocomplete="current-password"
          />
        </label>

        <button type="submit" :aria-busy="loading" :disabled="loading">
          {{ loading ? "" : "Sign In" }}
        </button>
      </form>

      <!-- Links -->
      <div class="auth-links">
        <router-link :to="withPreviewParams('/auth/password-reset')"
          >Forgot password?</router-link
        >
        <span v-if="portalStore.config.registration_enabled">
          |
          <router-link :to="withPreviewParams('/auth/register')"
            >Create account</router-link
          >
        </span>
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
