<script setup lang="ts">
/**
 * Auth Portal Password Reset Request View
 *
 * Allows users to request a password reset email.
 */
import { ref, onMounted } from "vue";
import { useToast } from "vue-toastification";
import { usePortalStore } from "../../stores/portal";
import { api } from "../../api";
import { usePreviewParams } from "../../composables/usePreviewParams";
import Icon from "../../components/Icon.vue";

const toast = useToast();
const portalStore = usePortalStore();
const { withPreviewParams } = usePreviewParams();

const email = ref("");
const loading = ref(false);

onMounted(async () => {
  await portalStore.fetchConfig();
});

async function handleRequestReset() {
  loading.value = true;

  try {
    await api.post("/api/auth/password-reset/request", {
      email: email.value,
    });

    // Always show success message (security best practice)
    toast.success("If that email exists, a password reset link has been sent.");
    email.value = "";
  } catch (err: any) {
    toast.error(
      err.response?.data?.detail || "Failed to request password reset"
    );
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
