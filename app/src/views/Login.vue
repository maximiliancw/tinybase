<script setup lang="ts">
/**
 * Login View
 *
 * Premium authentication page with ambient effects and smooth interactions.
 */
import { ref, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useForm } from "vee-validate";
import { useAuthStore } from "../stores/auth";
import { api } from "../api";
import { validationSchemas } from "../composables/useFormValidation";
import Icon from "../components/Icon.vue";
import FormField from "../components/FormField.vue";

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const errorMessage = ref("");
const needsSetup = ref(false);
const checkingSetup = ref(true);

const { handleSubmit } = useForm({
  validationSchema: validationSchemas.login,
  initialValues: {
    email: "",
    password: "",
  },
});

const onSubmit = handleSubmit(async (values) => {
  errorMessage.value = "";

  const success = await authStore.login(values.email, values.password);

  if (success) {
    // Redirect to intended destination or dashboard
    const redirect = (route.query.redirect as string) || "/";
    router.push(redirect);
  } else {
    errorMessage.value = authStore.error || "Login failed";
  }
});

onMounted(async () => {
  // Fetch instance name and setup status in parallel
  await Promise.all([
    authStore.fetchInstanceInfo(),
    api
      .get("/api/auth/setup-status")
      .then((response) => {
        needsSetup.value = response.data.needs_setup;
      })
      .catch(() => {
        /* Ignore errors */
      }),
  ]);
  checkingSetup.value = false;
});
</script>

<template>
  <div class="login-layout">
    <!-- Login Card -->
    <article data-animate="fade-in">
      <!-- Logo -->
      <div class="login-logo">
        <div class="logo-icon">
          <Icon name="Box" :size="28" color="white" />
        </div>
        <h1>{{ authStore.instanceName }}</h1>
        <p>Admin Dashboard</p>
      </div>

      <!-- First-time setup notice -->
      <div v-if="needsSetup && !checkingSetup" class="setup-notice">
        <div class="setup-icon">
          <Icon name="ThumbsUp" :size="18" />
        </div>
        <div class="setup-content">
          <strong>Welcome!</strong>
          <p>
            No users exist yet. Enter your credentials to create the first admin
            account.
          </p>
        </div>
      </div>

      <!-- Login Form -->
      <form @submit="onSubmit">
        <FormField
          name="email"
          type="email"
          label="Email"
          placeholder="admin@example.com"
          autocomplete="email"
        />

        <FormField
          name="password"
          type="password"
          label="Password"
          placeholder="••••••••"
          autocomplete="current-password"
        />

        <!-- Error message -->
        <div v-if="errorMessage" class="error-message">
          <Icon name="AlertCircle" :size="16" />
          {{ errorMessage }}
        </div>

        <button
          type="submit"
          class="login-button"
          :aria-busy="authStore.loading"
          :disabled="authStore.loading"
        >
          {{
            authStore.loading
              ? ""
              : needsSetup
              ? "Create Admin & Sign In"
              : "Sign In"
          }}
        </button>
      </form>

      <!-- Footer -->
      <div class="login-footer">
        <small>Powered by TinyBase</small>
      </div>
    </article>
  </div>
</template>

<style scoped>
/* Logo area */
.login-logo {
  text-align: center;
  margin-bottom: var(--tb-spacing-xl);
}

.logo-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 3.5rem;
  height: 3.5rem;
  background: var(--tb-gradient-primary);
  border-radius: var(--tb-radius-lg);
  box-shadow: var(--tb-btn-primary-shadow-hover), var(--tb-shadow-glow);
  margin-bottom: var(--tb-spacing-md);
}

.logo-icon svg {
  width: 1.75rem;
  height: 1.75rem;
  color: white;
}

.login-logo h1 {
  font-size: 1.75rem;
  font-weight: 700;
  margin: 0 0 var(--tb-spacing-xs) 0;
  background: var(--tb-gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.login-logo p {
  margin: 0;
  color: var(--tb-text-muted);
  font-size: 0.9375rem;
}

/* Setup notice */
.setup-notice {
  display: flex;
  align-items: flex-start;
  gap: var(--tb-spacing-md);
  background: var(--tb-info-bg);
  border: 1px solid var(--tb-info-bg);
  border-radius: var(--tb-radius);
  padding: var(--tb-spacing-md);
  margin-bottom: var(--tb-spacing-xl);
}

.setup-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  background: var(--tb-info-bg);
  border-radius: var(--tb-radius);
  flex-shrink: 0;
}

.setup-icon svg {
  width: 1.125rem;
  height: 1.125rem;
  color: var(--tb-info);
}

.setup-content strong {
  display: block;
  color: var(--tb-info);
  font-size: 0.875rem;
  margin-bottom: var(--tb-spacing-xs);
}

.setup-content p {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--tb-text-secondary);
  line-height: 1.5;
}

/* Form styling */
form {
  display: flex;
  flex-direction: column;
  gap: var(--tb-spacing-md);
}

form label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--tb-text-secondary);
}

/* Error message */
.error-message {
  display: flex;
  align-items: center;
  gap: var(--tb-spacing-sm);
  padding: var(--tb-spacing-sm) var(--tb-spacing-md);
  background: var(--tb-error-bg);
  border: 1px solid var(--tb-error-bg);
  border-radius: var(--tb-radius);
  color: var(--tb-error);
  font-size: 0.8125rem;
}

.error-message svg {
  width: 1rem;
  height: 1rem;
  flex-shrink: 0;
}

/* Login button */
.login-button {
  margin-top: var(--tb-spacing-sm);
  padding: 0.875rem var(--tb-spacing-lg);
  font-size: 0.9375rem;
  font-weight: 600;
}

/* Footer */
.login-footer {
  margin-top: var(--tb-spacing-xl);
  padding-top: var(--tb-spacing-lg);
  border-top: 1px solid var(--tb-border-subtle);
  text-align: center;
}

.login-footer small {
  color: var(--tb-text-muted);
  font-size: 0.75rem;
}
</style>
