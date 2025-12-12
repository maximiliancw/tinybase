<script setup lang="ts">
/**
 * Extensions View
 *
 * Admin page for managing TinyBase extensions.
 * Allows installing, uninstalling, and enabling/disabling extensions.
 */
import { onMounted, ref } from "vue";
import { useForm } from "vee-validate";
import { api } from "../api";
import { validationSchemas } from "../composables/useFormValidation";
import Modal from "../components/Modal.vue";
import FormField from "../components/FormField.vue";

interface Extension {
  id: string;
  name: string;
  version: string;
  description: string | null;
  author: string | null;
  repo_url: string;
  is_enabled: boolean;
  installed_at: string;
  updated_at: string;
  update_available: string | null;
}

interface ExtensionListResponse {
  extensions: Extension[];
  total: number;
  limit: number;
  offset: number;
}

const loading = ref(true);
const installing = ref(false);
const error = ref<string | null>(null);
const success = ref<string | null>(null);

const extensions = ref<Extension[]>([]);
const total = ref(0);

// Install modal
const showInstallModal = ref(false);
const installError = ref<string | null>(null);
const showWarningAccepted = ref(false);

const { handleSubmit, resetForm } = useForm({
  validationSchema: validationSchemas.installExtension,
  initialValues: {
    repo_url: "",
  },
});

// Uninstall confirmation
const showUninstallModal = ref(false);
const extensionToUninstall = ref<Extension | null>(null);
const uninstalling = ref(false);

onMounted(async () => {
  await fetchExtensions();
});

async function fetchExtensions() {
  loading.value = true;
  error.value = null;

  try {
    const response = await api.get<ExtensionListResponse>(
      "/api/admin/extensions",
      { params: { check_updates: true } }
    );
    extensions.value = response.data.extensions;
    total.value = response.data.total;
  } catch (err: any) {
    error.value = err.response?.data?.detail || "Failed to load extensions";
  } finally {
    loading.value = false;
  }
}

function openInstallModal() {
  resetForm();
  installError.value = null;
  showWarningAccepted.value = false;
  showInstallModal.value = true;
}

const onSubmit = handleSubmit(async (values) => {
  installing.value = true;
  installError.value = null;

  try {
    await api.post("/api/admin/extensions", {
      repo_url: values.repo_url.trim(),
    });

    showInstallModal.value = false;
    success.value =
      "Extension installed successfully. Restart the server to load it.";
    setTimeout(() => {
      success.value = null;
    }, 5000);

    await fetchExtensions();
  } catch (err: any) {
    installError.value = err.response?.data?.detail || "Installation failed";
  } finally {
    installing.value = false;
  }
});

function openUninstallModal(ext: Extension) {
  extensionToUninstall.value = ext;
  showUninstallModal.value = true;
}

async function handleUninstall() {
  if (!extensionToUninstall.value) return;

  uninstalling.value = true;

  try {
    await api.delete(
      `/api/admin/extensions/${extensionToUninstall.value.name}`
    );

    showUninstallModal.value = false;
    success.value =
      "Extension uninstalled. Restart the server to fully unload it.";
    setTimeout(() => {
      success.value = null;
    }, 5000);

    await fetchExtensions();
  } catch (err: any) {
    error.value = err.response?.data?.detail || "Uninstall failed";
  } finally {
    uninstalling.value = false;
    extensionToUninstall.value = null;
  }
}

async function toggleEnabled(ext: Extension) {
  try {
    await api.patch(`/api/admin/extensions/${ext.name}`, {
      is_enabled: !ext.is_enabled,
    });

    ext.is_enabled = !ext.is_enabled;
    success.value = `Extension ${
      ext.is_enabled ? "enabled" : "disabled"
    }. Restart the server to apply changes.`;
    setTimeout(() => {
      success.value = null;
    }, 3000);
  } catch (err: any) {
    error.value = err.response?.data?.detail || "Failed to update extension";
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}
</script>

<template>
  <section data-animate="fade-in">
    <header class="page-header">
      <div>
        <h1>Extensions</h1>
        <p>Manage TinyBase plugins and integrations</p>
      </div>
      <button @click="openInstallModal">Install Extension</button>
    </header>

    <!-- Status Messages -->
    <ins v-if="success" class="alert-success">
      {{ success }}
    </ins>

    <del v-if="error" class="alert-error">
      {{ error }}
    </del>

    <!-- Loading State -->
    <article v-if="loading" aria-busy="true">Loading extensions...</article>

    <!-- Empty State -->
    <article v-else-if="extensions.length === 0">
      <div data-empty data-empty-icon="🧩">
        <p>No extensions installed</p>
        <p>
          <small class="text-muted">
            Install extensions from GitHub to add new features to TinyBase.
          </small>
        </p>
        <button @click="openInstallModal" class="mt-3">
          Install Your First Extension
        </button>
      </div>
    </article>

    <!-- Extensions List -->
    <div v-else class="extensions-grid">
      <article v-for="ext in extensions" :key="ext.id" class="extension-card">
        <header>
          <div class="extension-header">
            <h3>{{ ext.name }}</h3>
            <mark :data-status="ext.is_enabled ? 'success' : 'neutral'">
              {{ ext.is_enabled ? "Enabled" : "Disabled" }}
            </mark>
          </div>
          <small class="text-muted">v{{ ext.version }}</small>
          <mark
            v-if="ext.update_available"
            data-status="info"
            class="update-badge"
          >
            Update available: v{{ ext.update_available }}
          </mark>
        </header>

        <p v-if="ext.description" class="extension-description">
          {{ ext.description }}
        </p>
        <p v-else class="extension-description text-muted">
          No description provided.
        </p>

        <div class="extension-meta">
          <small v-if="ext.author" class="text-muted">
            By {{ ext.author }}
          </small>
          <small class="text-muted">
            Installed {{ formatDate(ext.installed_at) }}
          </small>
        </div>

        <footer>
          <div class="extension-actions">
            <label class="toggle-label">
              <input
                type="checkbox"
                role="switch"
                :checked="ext.is_enabled"
                @change="toggleEnabled(ext)"
              />
              {{ ext.is_enabled ? "Enabled" : "Disabled" }}
            </label>
            <div class="action-buttons">
              <a
                :href="ext.repo_url"
                target="_blank"
                rel="noopener noreferrer"
                class="button small outline"
              >
                GitHub
              </a>
              <button
                class="small outline danger"
                @click="openUninstallModal(ext)"
              >
                Uninstall
              </button>
            </div>
          </div>
        </footer>
      </article>
    </div>

    <!-- Install Modal -->
    <Modal v-model:open="showInstallModal" title="Install Extension">
      <div v-if="!showWarningAccepted" class="warning-box">
        <h4>Security Warning</h4>
        <p>
          Extensions can execute arbitrary Python code on your server. Only
          install extensions from sources you trust.
        </p>
        <p>
          <small class="text-muted">
            Before installing, review the extension's source code on GitHub.
          </small>
        </p>
        <button class="secondary" @click="showWarningAccepted = true">
          I understand, continue
        </button>
      </div>

      <form id="install-form" v-else @submit="onSubmit">
        <FormField
          name="repo_url"
          type="url"
          label="GitHub Repository URL"
          placeholder="https://github.com/username/tinybase-extension"
          :disabled="installing"
          helper="The repository must contain an extension.toml manifest."
        />

        <small v-if="installError" class="text-error">
          {{ installError }}
        </small>
      </form>
      <template #footer>
        <button
          type="button"
          class="outline"
          @click="showInstallModal = false"
          :disabled="installing"
        >
          Cancel
        </button>
        <button
          type="submit"
          form="install-form"
          :aria-busy="installing"
          :disabled="installing"
        >
          {{ installing ? "" : "Install" }}
        </button>
      </template>
    </Modal>

    <!-- Uninstall Confirmation Modal -->
    <Modal v-model:open="showUninstallModal" title="Uninstall Extension">
      <p>
        Are you sure you want to uninstall
        <strong>{{ extensionToUninstall?.name }}</strong
        >?
      </p>
      <p class="text-muted">
        This will remove the extension files. Any functions registered by this
        extension will no longer be available after the server restarts.
      </p>

      <template #footer>
        <button
          type="button"
          class="outline"
          @click="showUninstallModal = false"
          :disabled="uninstalling"
        >
          Cancel
        </button>
        <button
          class="danger"
          @click="handleUninstall"
          :aria-busy="uninstalling"
          :disabled="uninstalling"
        >
          {{ uninstalling ? "" : "Uninstall" }}
        </button>
      </template>
    </Modal>
  </section>
</template>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.page-header > div {
  flex: 1;
}

.page-header > button {
  white-space: nowrap;
}

.extensions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: var(--tb-spacing-lg);
}

.extension-card {
  display: flex;
  flex-direction: column;
}

.extension-card header {
  padding-bottom: var(--tb-spacing-md);
  border-bottom: 1px solid var(--tb-border);
  margin-bottom: var(--tb-spacing-md);
}

.extension-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--tb-spacing-sm);
}

.extension-header h3 {
  margin: 0;
  font-size: 1.1rem;
}

.update-badge {
  display: inline-block;
  margin-top: var(--tb-spacing-xs);
}

.extension-description {
  flex: 1;
  margin-bottom: var(--tb-spacing-md);
}

.extension-meta {
  display: flex;
  flex-direction: column;
  gap: var(--tb-spacing-xs);
  margin-bottom: var(--tb-spacing-md);
}

.extension-card footer {
  padding-top: var(--tb-spacing-md);
  border-top: 1px solid var(--tb-border);
  margin-top: auto;
}

.extension-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--tb-spacing-md);
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: var(--tb-spacing-sm);
  cursor: pointer;
  margin: 0;
}

.toggle-label input[type="checkbox"] {
  margin: 0;
}

.action-buttons {
  display: flex;
  gap: var(--tb-spacing-sm);
}

.action-buttons .button,
.action-buttons button {
  margin: 0;
}

.warning-box {
  background: var(--tb-warning-bg);
  border: 1px solid var(--tb-warning);
  border-radius: var(--tb-radius);
  padding: var(--tb-spacing-lg);
  margin-bottom: var(--tb-spacing-lg);
}

.warning-box h4 {
  color: var(--tb-warning);
  margin-top: 0;
}

button.danger,
.button.danger {
  --pico-background-color: var(--tb-error);
  --pico-border-color: var(--tb-error);
}

button.danger:hover,
.button.danger:hover {
  --pico-background-color: var(--tb-error);
  --pico-border-color: var(--tb-error);
  filter: brightness(0.9);
}

button.outline.danger {
  --pico-color: var(--tb-error);
  --pico-border-color: var(--tb-error);
  --pico-background-color: transparent;
}

button.outline.danger:hover {
  --pico-background-color: var(--tb-error);
  --pico-color: white;
}

/* Alert styles */
ins.alert-success,
del.alert-error {
  display: block;
  padding: var(--tb-spacing-sm) var(--tb-spacing-md);
  border-radius: var(--tb-radius);
  margin-bottom: var(--tb-spacing-lg);
  text-decoration: none;
}

ins.alert-success {
  background: var(--tb-success-bg);
  color: var(--tb-success);
  border: 1px solid var(--tb-success);
}

del.alert-error {
  background: var(--tb-error-bg);
  color: var(--tb-error);
  border: 1px solid var(--tb-error);
}

.mt-3 {
  margin-top: var(--tb-spacing-lg);
}

.button {
  display: inline-block;
  padding: calc(var(--pico-spacing) * 0.5) var(--pico-spacing);
  border-radius: var(--pico-border-radius);
  text-decoration: none;
  text-align: center;
  cursor: pointer;
}

.button.outline {
  background: transparent;
  border: 1px solid var(--pico-primary);
  color: var(--pico-primary);
}

.button.outline:hover {
  background: var(--pico-primary);
  color: white;
}

.button.small,
button.small {
  padding: calc(var(--pico-spacing) * 0.25) calc(var(--pico-spacing) * 0.5);
  font-size: 0.875rem;
}
</style>
