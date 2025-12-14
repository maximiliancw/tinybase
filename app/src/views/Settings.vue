<script setup lang="ts">
/**
 * Settings View
 *
 * Admin page for configuring instance settings.
 * Uses semantic HTML elements following PicoCSS conventions.
 */
import { onMounted, ref, reactive, watch, computed } from "vue";
import { useToast } from "vue-toastification";
import { useForm, useField } from "vee-validate";
import { api } from "../api";
import { useAuthStore } from "../stores/auth";
import { validationSchemas } from "../composables/useFormValidation";
import Modal from "../components/Modal.vue";
import Icon from "../components/Icon.vue";
import FormField from "../components/FormField.vue";

const toast = useToast();
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
  auth_portal_enabled: boolean;
  auth_portal_logo_url: string | null;
  auth_portal_primary_color: string | null;
  auth_portal_background_image_url: string | null;
  auth_portal_login_redirect_url: string | null;
  auth_portal_register_redirect_url: string | null;
  updated_at: string;
}

interface ApplicationToken {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
  is_active: boolean;
  is_valid: boolean;
}

const loading = ref(true);
const saving = ref(false);

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
  auth_portal_enabled: true,
  auth_portal_logo_url: null,
  auth_portal_primary_color: null,
  auth_portal_background_image_url: null,
  auth_portal_login_redirect_url: null,
  auth_portal_register_redirect_url: null,
  updated_at: "",
});

// Storage credentials (not returned by API, only for updates)
const storageAccessKey = ref("");
const storageSecretKey = ref("");

// Application Tokens
const applicationTokens = ref<ApplicationToken[]>([]);
const loadingTokens = ref(false);
const showCreateTokenForm = ref(false);
const newlyCreatedToken = ref<{
  token: ApplicationToken;
  token_value: string;
} | null>(null);
const creatingToken = ref(false);

const { handleSubmit: handleTokenSubmit, resetForm: resetTokenForm } = useForm({
  validationSchema: validationSchemas.createToken,
  initialValues: {
    name: "",
    description: "",
    expires_days: null as number | null,
  },
});

// Get the name field value for button disable state
const { value: tokenName } = useField("name", undefined, {
  initialValue: "",
});

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
  await fetchApplicationTokens();
});

// Disable auth portal when public registration is disabled
watch(
  () => settings.allow_public_registration,
  (enabled) => {
    if (!enabled) {
      settings.auth_portal_enabled = false;
    }
  }
);

// Validate redirect URLs when saving if auth portal is enabled
function validateAuthPortalSettings() {
  if (settings.auth_portal_enabled) {
    if (
      !settings.auth_portal_login_redirect_url ||
      (!settings.auth_portal_login_redirect_url.startsWith("http://") &&
        !settings.auth_portal_login_redirect_url.startsWith("https://"))
    ) {
      throw new Error(
        "Login redirect URL is required and must be an absolute URL when auth portal is enabled"
      );
    }
    if (settings.auth_portal_login_redirect_url.includes("/admin")) {
      throw new Error("Login redirect URL must not point to /admin URLs");
    }
    if (
      !settings.auth_portal_register_redirect_url ||
      (!settings.auth_portal_register_redirect_url.startsWith("http://") &&
        !settings.auth_portal_register_redirect_url.startsWith("https://"))
    ) {
      throw new Error(
        "Register redirect URL is required and must be an absolute URL when auth portal is enabled"
      );
    }
    if (settings.auth_portal_register_redirect_url.includes("/admin")) {
      throw new Error("Register redirect URL must not point to /admin URLs");
    }
  }
}

// Generate preview URL with current (unsaved) settings
const previewUrl = computed(() => {
  const params = new URLSearchParams();
  params.append("preview", "true");
  // Only include params if they have values (non-empty)
  // This way, if a field is cleared, we don't pass it and backend uses saved value
  if (settings.auth_portal_logo_url) {
    params.append("logo_url", settings.auth_portal_logo_url);
  }
  if (settings.auth_portal_primary_color) {
    params.append("primary_color", settings.auth_portal_primary_color);
  }
  if (settings.auth_portal_background_image_url) {
    params.append(
      "background_image_url",
      settings.auth_portal_background_image_url
    );
  }
  // Include auth token for preview mode (iframe needs it for API calls)
  const token = localStorage.getItem("tinybase_token");
  if (token) {
    params.append("token", token);
  }
  return `/auth/login?${params.toString()}`;
});

function openPreviewInNewTab() {
  window.open(previewUrl.value, "_blank", "noopener,noreferrer");
}

async function fetchSettings() {
  loading.value = true;

  try {
    const response = await api.get("/api/admin/settings");
    Object.assign(settings, response.data);
  } catch (err: any) {
    toast.error(err.response?.data?.detail || "Failed to load settings");
  } finally {
    loading.value = false;
  }
}

async function fetchApplicationTokens() {
  loadingTokens.value = true;
  try {
    const response = await api.get("/api/admin/application-tokens");
    applicationTokens.value = response.data.tokens;
  } catch (err: any) {
    console.error("Failed to load application tokens:", err);
  } finally {
    loadingTokens.value = false;
  }
}

const onCreateToken = handleTokenSubmit(async (values) => {
  creatingToken.value = true;

  try {
    const payload: Record<string, any> = {
      name: values.name,
    };
    if (values.description) {
      payload.description = values.description;
    }
    if (values.expires_days) {
      payload.expires_days = values.expires_days;
    }

    const response = await api.post("/api/admin/application-tokens", payload);
    newlyCreatedToken.value = response.data;
    await fetchApplicationTokens();

    // Reset form and close modal
    resetTokenForm();
    showCreateTokenForm.value = false;
    toast.success("Application token created successfully");
  } catch (err: any) {
    toast.error(err.response?.data?.detail || "Failed to create token");
  } finally {
    creatingToken.value = false;
  }
});

async function revokeApplicationToken(tokenId: string) {
  if (
    !confirm(
      "Are you sure you want to revoke this token? It will no longer be usable."
    )
  ) {
    return;
  }

  try {
    await api.delete(`/api/admin/application-tokens/${tokenId}`);
    await fetchApplicationTokens();
    if (newlyCreatedToken.value?.token.id === tokenId) {
      newlyCreatedToken.value = null;
    }
    toast.success("Token revoked successfully");
  } catch (err: any) {
    toast.error(err.response?.data?.detail || "Failed to revoke token");
  }
}

async function toggleTokenActive(tokenId: string, currentStatus: boolean) {
  try {
    await api.patch(`/api/admin/application-tokens/${tokenId}`, {
      is_active: !currentStatus,
    });
    await fetchApplicationTokens();
    toast.success(
      `Token ${!currentStatus ? "activated" : "deactivated"} successfully`
    );
  } catch (err: any) {
    toast.error(err.response?.data?.detail || "Failed to update token");
  }
}

function copyTokenToClipboard(tokenValue: string) {
  navigator.clipboard.writeText(tokenValue);
  toast.success("Token copied to clipboard");
}

function dismissNewToken() {
  newlyCreatedToken.value = null;
}

async function saveSettings() {
  saving.value = true;

  try {
    // Validate auth portal settings
    try {
      validateAuthPortalSettings();
    } catch (validationError: any) {
      // Show validation error and prevent save
      toast.error(
        validationError.message || "Invalid auth portal configuration"
      );
      saving.value = false;
      return;
    }

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
      auth_portal_enabled: settings.auth_portal_enabled,
      auth_portal_logo_url: settings.auth_portal_logo_url,
      auth_portal_primary_color: settings.auth_portal_primary_color,
      auth_portal_background_image_url:
        settings.auth_portal_background_image_url,
      auth_portal_login_redirect_url: settings.auth_portal_login_redirect_url,
      auth_portal_register_redirect_url:
        settings.auth_portal_register_redirect_url,
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

    toast.success("Settings saved successfully");
  } catch (err: any) {
    const errorMessage =
      err.response?.data?.detail || err.message || "Failed to save settings";
    toast.error(errorMessage);
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <section data-animate="fade-in">
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
        <div class="grid">
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
          <label for="server_timezone">
            Server Timezone
            <select id="server_timezone" v-model="settings.server_timezone">
              <option v-for="tz in commonTimezones" :key="tz" :value="tz">
                {{ tz }}
              </option>
            </select>
            <small>
              Default timezone for scheduled functions. Individual schedules can
              override this.
            </small>
          </label>
        </div>
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

        <!-- Auth Portal Settings (only shown when public registration is enabled) -->
        <div v-if="settings.allow_public_registration" class="portal-fields">
          <header
            style="
              margin-top: var(--tb-spacing-lg);
              margin-bottom: var(--tb-spacing-md);
            "
          >
            <h4 style="margin: 0; font-size: 1rem; font-weight: 600">
              Auth Portal
            </h4>
          </header>

          <label>
            <input
              type="checkbox"
              v-model="settings.auth_portal_enabled"
              role="switch"
            />
            Enable Auth Portal
          </label>
          <small class="text-muted">
            When enabled, a public-facing authentication portal will be
            available at <code>/auth</code> with login, registration, and
            password reset functionality. <br />
            <small class="text-muted">
              Example: <code>https://where.you.host.tinybase.com/auth</code>
            </small>
          </small>

          <div
            v-if="settings.auth_portal_enabled"
            class="portal-config-fields grid"
          >
            <!-- Redirects Section -->
            <details name="auth-portal-config" open>
              <summary role="button" class="outline">Redirects</summary>
              <div>
                <label for="auth_portal_login_redirect_url">
                  Login Redirect URL
                  <input
                    id="auth_portal_login_redirect_url"
                    v-model="settings.auth_portal_login_redirect_url"
                    type="url"
                    placeholder="https://app.example.com/dashboard"
                    pattern="https?://.+"
                    required
                  />
                  <small>
                    Required: Absolute URL where users are redirected after
                    successful login (e.g., https://app.example.com/dashboard).
                    Must not point to /admin URLs.
                  </small>
                </label>

                <label for="auth_portal_register_redirect_url">
                  Registration Redirect URL
                  <input
                    id="auth_portal_register_redirect_url"
                    v-model="settings.auth_portal_register_redirect_url"
                    type="url"
                    placeholder="https://app.example.com/welcome"
                    pattern="https?://.+"
                    required
                  />
                  <small>
                    Required: Absolute URL where users are redirected after
                    successful registration (e.g.,
                    https://app.example.com/welcome). Must not point to /admin
                    URLs.
                  </small>
                </label>
              </div>
            </details>

            <!-- Styling Section -->
            <details name="auth-portal-config">
              <summary role="button" class="outline">Styling</summary>
              <div>
                <label for="auth_portal_logo_url">
                  Logo URL
                  <input
                    id="auth_portal_logo_url"
                    v-model="settings.auth_portal_logo_url"
                    type="url"
                    placeholder="https://example.com/logo.png"
                  />
                  <small
                    >Optional logo URL to display in the auth portal.</small
                  >
                </label>

                <label for="auth_portal_background_image_url">
                  Background Image URL
                  <input
                    id="auth_portal_background_image_url"
                    v-model="settings.auth_portal_background_image_url"
                    type="url"
                    placeholder="https://example.com/background.jpg"
                  />
                  <small
                    >Optional background image. The login card will have a
                    frosted glass effect when a background image is set.</small
                  >
                </label>
              </div>

              <div class="color-picker-group">
                <label for="auth_portal_primary_color_hex">
                  Primary Color
                  <div class="color-input-row">
                    <input
                      id="auth_portal_primary_color_hex"
                      v-model="settings.auth_portal_primary_color"
                      type="text"
                      class="color-hex"
                      placeholder="#000000"
                      pattern="^#?[0-9A-Fa-f]{6}$"
                      @blur="
                          (e) => {
                            const val = (e.target as HTMLInputElement).value;
                            if (val && !val.startsWith('#')) {
                              settings.auth_portal_primary_color = '#' + val;
                            }
                          }
                        "
                    />
                    <label
                      for="auth_portal_primary_color"
                      class="color-picker-trigger"
                    >
                      <input
                        id="auth_portal_primary_color"
                        v-model="settings.auth_portal_primary_color"
                        type="color"
                        class="color-picker-input"
                      />
                      <span
                        class="color-picker-preview"
                        :style="{
                          backgroundColor:
                            settings.auth_portal_primary_color || '#000000',
                        }"
                      ></span>
                    </label>
                  </div>
                  <small>Primary color for buttons and links.</small>
                </label>
              </div>
            </details>

            <!-- Preview Controls -->
            <div
              style="display: flex; align-items: start; justify-content: center"
            >
              <button
                type="button"
                @click="openPreviewInNewTab"
                class="primary"
              >
                Open Preview in New Tab
                <Icon
                  name="ExternalLink"
                  :size="16"
                  style="
                    display: inline-block;
                    vertical-align: middle;
                    margin-left: 0.25rem;
                  "
                />
              </button>
            </div>
          </div>
        </div>
      </article>

      <!-- Scheduler Settings -->
      <article>
        <header>
          <h3>Scheduler</h3>
        </header>

        <div class="grid grid-3">
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
              >How often to collect metrics (in scheduler ticks). For example,
              if scheduler runs every 5 seconds and this is set to 360, metrics
              are collected every 30 minutes (360 × 5s).</small
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
              >Maximum execution time for scheduled functions. Leave empty to
              use default (1800 seconds = 30 minutes).</small
            >
          </label>
        </div>

        <div class="grid grid-3">
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
              >Maximum number of schedules to execute concurrently. Leave empty
              to use default (10).</small
            >
          </label>
        </div>
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

      <!-- Application Tokens -->
      <article>
        <header class="token-header">
          <div>
            <h3>Application Tokens</h3>
            <small class="text-muted">
              Application tokens allow client applications to authenticate with
              your TinyBase instance. Create tokens for each client application
              and use them in API requests.
            </small>
          </div>
          <button
            type="button"
            @click="showCreateTokenForm = true"
            class="primary outline small"
          >
            Create Token
          </button>
        </header>

        <!-- Newly Created Token Display -->
        <div v-if="newlyCreatedToken" class="token-created-alert">
          <strong>Token Created Successfully!</strong>
          <p>Copy this token now - you won't be able to see it again:</p>
          <div class="token-display">
            <code>{{ newlyCreatedToken.token_value }}</code>
            <button
              type="button"
              @click="copyTokenToClipboard(newlyCreatedToken.token_value)"
              class="secondary"
            >
              Copy
            </button>
          </div>
          <button type="button" @click="dismissNewToken" class="secondary">
            Dismiss
          </button>
        </div>

        <!-- Token List -->
        <div>
          <div v-if="loadingTokens" aria-busy="true">Loading tokens...</div>

          <div v-else-if="applicationTokens.length === 0" class="empty-state">
            <p>No application tokens yet. Create one to get started.</p>
          </div>

          <table v-else>
            <thead>
              <tr>
                <th>Name</th>
                <th>Description</th>
                <th>Status</th>
                <th>Created</th>
                <th>Last Used</th>
                <th>Expires</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="token in applicationTokens" :key="token.id">
                <td>
                  <strong>{{ token.name }}</strong>
                </td>
                <td>{{ token.description || "-" }}</td>
                <td>
                  <span
                    :class="{
                      'status-active': token.is_valid,
                      'status-inactive': !token.is_valid,
                    }"
                  >
                    {{ token.is_valid ? "✓ Active" : "✗ Inactive" }}
                  </span>
                </td>
                <td>{{ new Date(token.created_at).toLocaleDateString() }}</td>
                <td>
                  {{
                    token.last_used_at
                      ? new Date(token.last_used_at).toLocaleDateString()
                      : "Never"
                  }}
                </td>
                <td>
                  {{
                    token.expires_at
                      ? new Date(token.expires_at).toLocaleDateString()
                      : "Never"
                  }}
                </td>
                <td class="actions-cell">
                  <div class="token-actions">
                    <button
                      type="button"
                      @click="toggleTokenActive(token.id, token.is_active)"
                      class="secondary outline small"
                      :data-tooltip="
                        token.is_active
                          ? 'Deactivate token temporarily'
                          : 'Activate token'
                      "
                    >
                      <Icon
                        v-if="token.is_active"
                        name="Power"
                        :size="16"
                        color="orange"
                      />
                      <Icon v-else name="PowerOff" :size="16" color="green" />
                    </button>
                    <button
                      type="button"
                      @click="revokeApplicationToken(token.id)"
                      class="secondary outline small"
                      data-tooltip="Revoke token permanently"
                    >
                      <Icon name="Delete" :size="16" color="red" />
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </article>

      <!-- Create Token Modal -->
      <Modal
        v-model:open="showCreateTokenForm"
        title="Create Application Token"
      >
        <form id="token-form" @submit="onCreateToken">
          <FormField
            name="name"
            type="text"
            label="Name"
            placeholder="e.g., Production API Client"
            :maxlength="200"
            helper="A descriptive name for this token."
          />

          <FormField
            name="description"
            as="textarea"
            label="Description (optional)"
            placeholder="What will this token be used for?"
            :maxlength="500"
            :rows="3"
          />

          <FormField
            name="expires_days"
            type="number"
            label="Expires in (days)"
            placeholder="Leave empty for no expiration"
            :min="1"
            helper="Leave empty if the token should never expire."
          />
        </form>
        <template #footer>
          <button
            type="button"
            class="secondary"
            @click="showCreateTokenForm = false"
            :disabled="creatingToken"
          >
            Cancel
          </button>
          <button
            type="submit"
            form="token-form"
            :aria-busy="creatingToken"
            :disabled="creatingToken || !tokenName"
          >
            {{ creatingToken ? "" : "Create Token" }}
          </button>
        </template>
      </Modal>

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
        <div
          style="display: flex; justify-content: center; align-items: center"
        >
          <button type="submit" :aria-busy="saving" :disabled="saving">
            {{ saving ? "" : "Save Settings" }}
          </button>
        </div>
      </article>
    </form>
  </section>
</template>

<style scoped>
/* Component-specific layout - not overriding PicoCSS semantic elements */
.storage-fields {
  margin-top: var(--pico-block-spacing-vertical);
  padding-top: var(--pico-block-spacing-vertical);
  border-top: 1px solid var(--pico-muted-border-color);
}

.portal-fields {
  margin-top: var(--pico-block-spacing-vertical);
  padding-top: var(--pico-block-spacing-vertical);
  border-top: 1px solid var(--pico-muted-border-color);
}

.portal-config-fields {
  margin-top: var(--pico-spacing);
  padding-top: var(--pico-spacing);
  border-top: 1px solid var(--pico-muted-border-color);
}

.preview-controls {
  display: flex;
  flex-direction: column;
  gap: var(--tb-spacing-xs);
}

.preview-controls button {
  display: inline-flex;
  align-items: center;
  padding: var(--tb-spacing-sm) var(--tb-spacing-md);
  font-size: 0.875rem;
  align-self: flex-start;
}

/* Accordion styling for portal config - minimal overrides for spacing */
.portal-config-fields details {
  margin-bottom: var(--tb-spacing-md);
}

.portal-config-fields details .grid {
  margin-top: var(--tb-spacing-md);
}

.portal-config-fields details .color-picker-group {
  margin-top: var(--tb-spacing-md);
}

.save-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* Alert styles using Pico's ins/del for success/error - theme colors only */
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

.color-picker-group {
  margin-bottom: var(--tb-spacing-md);
}

.color-input-row {
  display: flex;
  gap: var(--tb-spacing-md);
  align-items: flex-start;
}

.color-hex {
  flex: 1;
  font-family: monospace;
  font-size: 0.875rem;
}

.color-picker-trigger {
  position: relative;
  display: inline-block;
  cursor: pointer;
  margin: 0;
  padding: 0;
  width: 3rem;
  height: 2.5rem;
  border: 2px solid var(--pico-form-element-border-color);
  border-radius: var(--pico-border-radius);
  overflow: hidden;
  background: var(--pico-background-color);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.color-picker-trigger:hover {
  border-color: var(--pico-primary);
  box-shadow: 0 0 0 2px var(--pico-primary-focus);
}

.color-picker-input {
  position: absolute;
  opacity: 0;
  width: 100%;
  height: 100%;
  cursor: pointer;
  margin: 0;
  padding: 0;
}

.color-picker-preview {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: calc(var(--pico-border-radius) - 2px);
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.1);
}

.token-created-alert {
  background: var(--pico-background-color);
  border: 2px solid var(--pico-primary);
  border-radius: var(--pico-border-radius);
  padding: var(--pico-block-spacing-vertical);
  margin-bottom: var(--pico-block-spacing-vertical);
}

.token-created-alert strong {
  display: block;
  margin-bottom: var(--tb-spacing-sm);
  color: var(--pico-primary);
}

.token-display {
  display: flex;
  gap: var(--tb-spacing-sm);
  align-items: center;
  justify-content: center;
  margin: var(--pico-spacing) 0;
  padding: var(--tb-spacing-sm);
  background: var(--pico-background-color);
  border: 1px solid var(--pico-muted-border-color);
  border-radius: var(--pico-border-radius);
}

.token-display code {
  flex: 1;
  word-break: break-all;
  font-family: monospace;
  font-size: 0.875rem;
}

.empty-state {
  padding: var(--pico-block-spacing-vertical);
  text-align: center;
  color: var(--pico-muted-color);
}

.status-active {
  color: var(--tb-success);
  font-weight: 600;
}

.status-inactive {
  color: var(--pico-muted-color);
}

/* Table styling removed - use PicoCSS defaults */
/* Only keep specific alignment override */
table tr:first-child th:last-child {
  text-align: center;
}

.actions-cell {
  padding-bottom: 0;
}

.token-actions {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: var(--tb-spacing-xs);
}

.token-actions button {
  display: flex;
  align-items: center;
  justify-content: center;
  max-width: 50px;
}

.grid-3 {
  grid-template-columns: repeat(3, 1fr);
}

@media (max-width: 768px) {
  .grid-3 {
    grid-template-columns: 1fr;
  }
}

.token-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* Button small variant - let PicoCSS handle sizing */
</style>
