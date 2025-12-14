<script setup lang="ts">
/**
 * Auth Portal Password Reset Confirm View
 *
 * Allows users to set a new password using a reset token.
 */
import { ref, onMounted } from "vue";
import { useToast } from "vue-toastification";
import { useRoute, useRouter } from "vue-router";
import { api } from "../../api";
import { usePortalStore } from "../../stores/portal";
import { usePreviewParams } from "../../composables/usePreviewParams";
import Icon from "../../components/Icon.vue";

const toast = useToast();
const route = useRoute();
const router = useRouter();
const portalStore = usePortalStore();
const { withPreviewParams } = usePreviewParams();

const token = ref<string>("");
const password = ref("");
const confirmPassword = ref("");
const loading = ref(false);

onMounted(async () => {
  await portalStore.fetchConfig();

  // Get token from route params
  token.value = route.params.token as string;

  if (!token.value) {
    toast.error("Invalid reset token");
  }
});

async function handleResetPassword() {
  loading.value = true;

  // Validate passwords match
  if (password.value !== confirmPassword.value) {
    toast.error("Passwords do not match");
    loading.value = false;
    return;
  }

  try {
    await api.post("/api/auth/password-reset/confirm", {
      token: token.value,
      password: password.value,
    });

    toast.success("Password reset successful! Redirecting to login...");

    // Redirect to login after 2 seconds
    setTimeout(() => {
      router.push(withPreviewParams("/auth/login"));
    }, 2000);
  } catch (err: any) {
    toast.error(err.response?.data?.detail || "Failed to reset password");
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
        <p>Set your new password</p>
      </div>

      <!-- Reset Confirm Form -->
      <form @submit.prevent="handleResetPassword" class="auth-form">
        <label for="password">
          New Password
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
          Confirm New Password
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

        <button
          type="submit"
          :aria-busy="loading"
          :disabled="loading || !token"
        >
          {{ loading ? "" : "Reset Password" }}
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
