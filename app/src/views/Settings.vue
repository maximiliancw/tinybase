<script setup lang="ts">
/**
 * Settings View
 *
 * Admin page for configuring instance settings.
 * Uses semantic HTML elements following PicoCSS conventions.
 */
import { onMounted, ref, reactive } from "vue";
import { api } from "../api";
import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();

interface InstanceSettings {
  instance_name: string;
  allow_public_registration: boolean;
  server_timezone: string;
  token_cleanup_interval: number;
  metrics_collection_interval: number;
  scheduler_function_timeout_seconds: number | null;
  scheduler_max_schedules_per_tick: number | null;
  scheduler_max_concurrent_executions: number | null;
  storage_enabled: boolean;
  storage_endpoint: string | null;
  storage_bucket: string | null;
  storage_region: string | null;
  updated_at: string;
}

const loading = ref(true);
const saving = ref(false);
const error = ref<string | null>(null);
const success = ref<string | null>(null);

const settings = reactive<InstanceSettings>({
  instance_name: "TinyBase",
  allow_public_registration: true,
  server_timezone: "UTC",
  token_cleanup_interval: 60,
  metrics_collection_interval: 360,
  scheduler_function_timeout_seconds: null,
  scheduler_max_schedules_per_tick: null,
  scheduler_max_concurrent_executions: null,
  storage_enabled: false,
  storage_endpoint: null,
  storage_bucket: null,
  storage_region: null,
  updated_at: "",
});

// Storage credentials (not returned by API, only for updates)
const storageAccessKey = ref("");
const storageSecretKey = ref("");

// Common timezones for selection
const commonTimezones = [
  "UTC",
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "Europe/London",
  "Europe/Paris",
  "Europe/Berlin",
  "Asia/Tokyo",
  "Asia/Shanghai",
  "Asia/Singapore",
  "Australia/Sydney",
];

onMounted(async () => {
  await fetchSettings();
});

async function fetchSettings() {
  loading.value = true;
  error.value = null;

  try {
    const response = await api.get("/api/admin/settings");
    Object.assign(settings, response.data);
  } catch (err: any) {
    error.value = err.response?.data?.detail || "Failed to load settings";
  } finally {
    loading.value = false;
  }
}

async function saveSettings() {
  saving.value = true;
  error.value = null;
  success.value = null;

  try {
    const payload: Record<string, any> = {
      instance_name: settings.instance_name,
      allow_public_registration: settings.allow_public_registration,
      server_timezone: settings.server_timezone,
      token_cleanup_interval: settings.token_cleanup_interval,
      metrics_collection_interval: settings.metrics_collection_interval,
      scheduler_function_timeout_seconds:
        settings.scheduler_function_timeout_seconds,
      scheduler_max_schedules_per_tick:
        settings.scheduler_max_schedules_per_tick,
      scheduler_max_concurrent_executions:
        settings.scheduler_max_concurrent_executions,
      storage_enabled: settings.storage_enabled,
      storage_endpoint: settings.storage_endpoint,
      storage_bucket: settings.storage_bucket,
      storage_region: settings.storage_region,
    };

    // Only include credentials if they're filled in
    if (storageAccessKey.value) {
      payload.storage_access_key = storageAccessKey.value;
    }
    if (storageSecretKey.value) {
      payload.storage_secret_key = storageSecretKey.value;
    }

    const response = await api.patch("/api/admin/settings", payload);
    Object.assign(settings, response.data);

    // Clear credential fields after save
    storageAccessKey.value = "";
    storageSecretKey.value = "";

    // Update instance name in sidebar
    await authStore.fetchInstanceInfo();
    // Refresh storage status if it changed
    await authStore.checkStorageStatus();

    success.value = "Settings saved successfully";
    setTimeout(() => {
      success.value = null;
    }, 3000);
  } catch (err: any) {
    error.value = err.response?.data?.detail || "Failed to save settings";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <div data-animate="fade-in">
    <header class="page-header">
      <h1>Settings</h1>
      <p>Configure your TinyBase instance</p>
    </header>

    <!-- Loading State -->
    <article v-if="loading" aria-busy="true">Loading settings...</article>

    <form v-else @submit.prevent="saveSettings">
      <!-- General Settings -->
      <article>
        <header>
          <h3>General</h3>
        </header>

        <label for="instance_name">
          Instance Name
          <input
            id="instance_name"
            v-model="settings.instance_name"
            type="text"
            maxlength="100"
          />
          <small>The name displayed in the admin UI and API responses.</small>
        </label>
      </article>

      <!-- Authentication Settings -->
      <article>
        <header>
          <h3>Authentication</h3>
        </header>

        <label>
          <input
            type="checkbox"
            v-model="settings.allow_public_registration"
            role="switch"
          />
          Allow Public Registration
        </label>
        <small class="text-muted">
          When enabled, anyone can register for an account. When disabled, only
          admins can create users.
        </small>
      </article>

      <!-- Timezone Settings -->
      <article>
        <header>
          <h3>Timezone</h3>
        </header>

        <label for="server_timezone">
          Server Timezone
          <select id="server_timezone" v-model="settings.server_timezone">
            <option v-for="tz in commonTimezones" :key="tz" :value="tz">
              {{ tz }}
            </option>
          </select>
          <small
            >Default timezone for scheduled functions. Individual schedules can
            override this.</small
          >
        </label>
      </article>

      <!-- Scheduler Settings -->
      <article>
        <header>
          <h3>Scheduler</h3>
        </header>

        <label for="token_cleanup_interval">
          Token Cleanup Interval
          <input
            id="token_cleanup_interval"
            v-model.number="settings.token_cleanup_interval"
            type="number"
            min="1"
            step="1"
          />
          <small
            >How often to run token cleanup (in scheduler ticks). For example,
            if scheduler runs every 5 seconds and this is set to 60, cleanup
            runs every 5 minutes (60 × 5s).</small
          >
        </label>

        <label for="metrics_collection_interval">
          Metrics Collection Interval
          <input
            id="metrics_collection_interval"
            v-model.number="settings.metrics_collection_interval"
            type="number"
            min="1"
            step="1"
          />
          <small
            >How often to collect metrics (in scheduler ticks). For example, if
            scheduler runs every 5 seconds and this is set to 360, metrics are
            collected every 30 minutes (360 × 5s).</small
          >
        </label>

        <label for="scheduler_function_timeout_seconds">
          Function Execution Timeout (seconds)
          <input
            id="scheduler_function_timeout_seconds"
            v-model.number="settings.scheduler_function_timeout_seconds"
            type="number"
            min="1"
            step="1"
            placeholder="1800"
          />
          <small
            >Maximum execution time for scheduled functions. Leave empty to use
            default (1800 seconds = 30 minutes).</small
          >
        </label>

        <label for="scheduler_max_schedules_per_tick">
          Max Schedules Per Tick
          <input
            id="scheduler_max_schedules_per_tick"
            v-model.number="settings.scheduler_max_schedules_per_tick"
            type="number"
            min="1"
            step="1"
            placeholder="100"
          />
          <small
            >Maximum number of schedules to process in each scheduler tick.
            Leave empty to use default (100).</small
          >
        </label>

        <label for="scheduler_max_concurrent_executions">
          Max Concurrent Executions
          <input
            id="scheduler_max_concurrent_executions"
            v-model.number="settings.scheduler_max_concurrent_executions"
            type="number"
            min="1"
            step="1"
            placeholder="10"
          />
          <small
            >Maximum number of schedules to execute concurrently. Leave empty to
            use default (10).</small
          >
        </label>
      </article>

      <!-- Storage Settings -->
      <article>
        <header>
          <h3>File Storage (S3-compatible)</h3>
        </header>

        <label>
          <input
            type="checkbox"
            v-model="settings.storage_enabled"
            role="switch"
          />
          Enable File Storage
        </label>
        <small class="text-muted mb-3">
          Enable S3-compatible file storage for file uploads.
        </small>

        <div v-if="settings.storage_enabled" class="storage-fields">
          <label for="storage_endpoint">
            Endpoint URL
            <input
              id="storage_endpoint"
              v-model="settings.storage_endpoint"
              type="url"
              placeholder="https://s3.amazonaws.com or https://your-minio-server:9000"
            />
          </label>

          <div class="grid">
            <label for="storage_bucket">
              Bucket Name
              <input
                id="storage_bucket"
                v-model="settings.storage_bucket"
                type="text"
                placeholder="my-bucket"
              />
            </label>

            <label for="storage_region">
              Region
              <input
                id="storage_region"
                v-model="settings.storage_region"
                type="text"
                placeholder="us-east-1"
              />
            </label>
          </div>

          <div class="grid">
            <label for="storage_access_key">
              Access Key
              <input
                id="storage_access_key"
                v-model="storageAccessKey"
                type="password"
                placeholder="Leave empty to keep existing"
              />
            </label>

            <label for="storage_secret_key">
              Secret Key
              <input
                id="storage_secret_key"
                v-model="storageSecretKey"
                type="password"
                placeholder="Leave empty to keep existing"
              />
            </label>
          </div>
        </div>
      </article>

      <!-- Status Messages -->
      <ins v-if="success" class="pico-background-green-500">
        {{ success }}
      </ins>

      <del v-if="error" class="pico-background-red-500">
        {{ error }}
      </del>

      <!-- Save Footer -->
      <article class="save-footer">
        <div class="text-muted">
          Last updated:
          {{
            settings.updated_at
              ? new Date(settings.updated_at).toLocaleString()
              : "Never"
          }}
        </div>
        <div>
          <button type="submit" :aria-busy="saving" :disabled="saving">
            {{ saving ? "" : "Save Settings" }}
          </button>
        </div>
      </article>
    </form>
  </div>
</template>

<style scoped>
article {
  margin-bottom: var(--tb-spacing-lg);
}

.storage-fields {
  margin-top: var(--tb-spacing-lg);
  padding-top: var(--tb-spacing-lg);
  border-top: 1px solid var(--tb-border);
}

.save-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* Alert styles using Pico's ins/del for success/error */
ins,
del {
  display: block;
  padding: var(--tb-spacing-sm) var(--tb-spacing-md);
  border-radius: var(--tb-radius);
  margin-bottom: var(--tb-spacing-lg);
  text-decoration: none;
}

ins {
  background: var(--tb-success-bg);
  color: var(--tb-success);
  border: 1px solid var(--tb-success);
}

del {
  background: var(--tb-error-bg);
  color: var(--tb-error);
  border: 1px solid var(--tb-error);
}

.mb-3 {
  margin-bottom: var(--tb-spacing-lg);
}
</style>
