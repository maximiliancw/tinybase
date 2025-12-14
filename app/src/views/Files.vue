<script setup lang="ts">
/**
 * Files View
 *
 * Admin page for managing file storage.
 * Allows uploading, downloading, and deleting files.
 */
import { onMounted, ref, computed, h, watch } from "vue";
import { useToast } from "vue-toastification";
import { useForm, Field } from "vee-validate";
import { useLocalStorage, useFileDialog, useDropZone } from "@vueuse/core";
import { api } from "../api";
import { validationSchemas } from "../composables/useFormValidation";
import Modal from "../components/Modal.vue";
import FormField from "../components/FormField.vue";
import DataTable from "../components/DataTable.vue";

interface FileInfo {
  key: string;
  filename: string;
  content_type: string;
  size: number;
  uploaded_at: string;
}

const toast = useToast();
const loading = ref(true);
const uploading = ref(false);
const storageEnabled = ref(false);

// Track uploaded files in component state with localStorage persistence
const files = useLocalStorage<FileInfo[]>("tinybase_files", []);

// Keep only last 100 files in storage
watch(
  files,
  (newFiles) => {
    if (newFiles.length > 100) {
      files.value = newFiles.slice(0, 100);
    }
  },
  { deep: true }
);

// Upload modal
const showUploadModal = ref(false);
const dropZoneRef = ref<HTMLElement>();

const { handleSubmit, resetForm, setFieldValue } = useForm({
  validationSchema: validationSchemas.uploadFile,
  initialValues: {
    file: null as File | null,
    path_prefix: "",
  },
});

// File dialog
const { open: openFileDialog, onChange: onFileDialogChange } = useFileDialog({
  accept: "*",
  multiple: false,
});

onFileDialogChange((selectedFiles) => {
  if (selectedFiles && selectedFiles.length > 0) {
    setFieldValue("file", selectedFiles[0]);
  }
});

// Drop zone for drag-and-drop
const { isOverDropZone } = useDropZone(dropZoneRef, {
  onDrop: (files) => {
    if (files && files.length > 0) {
      setFieldValue("file", files[0]);
    }
  },
});

// Manual key input
const manualKey = ref("");
const showKeyModal = ref(false);

onMounted(async () => {
  await checkStorageStatus();
});

async function checkStorageStatus() {
  loading.value = true;

  try {
    const response = await api.get("/api/files/status");
    storageEnabled.value = response.data.enabled;
  } catch (err: any) {
    toast.error(err.response?.data?.detail || "Failed to check storage status");
    storageEnabled.value = false;
  } finally {
    loading.value = false;
  }
}

function openUploadModal() {
  resetForm();
  showUploadModal.value = true;
}

function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    setFieldValue("file", target.files[0]);
  }
}

function handleFileDialogClick() {
  openFileDialog();
}

const onSubmit = handleSubmit(async (values) => {
  uploading.value = true;

  try {
    const formData = new FormData();
    if (values.file) {
      formData.append("file", values.file);
    }
    if (values.path_prefix?.trim()) {
      formData.append("path_prefix", values.path_prefix.trim());
    }

    const response = await api.post("/api/files/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });

    const fileInfo: FileInfo = {
      key: response.data.key,
      filename: response.data.filename,
      content_type: response.data.content_type,
      size: response.data.size,
      uploaded_at: new Date().toISOString(),
    };

    // Add to tracked files (useLocalStorage will auto-save)
    files.value.unshift(fileInfo);

    showUploadModal.value = false;
    toast.success(`File "${fileInfo.filename}" uploaded successfully`);
  } catch (err: any) {
    toast.error(err.response?.data?.detail || "Upload failed");
  } finally {
    uploading.value = false;
  }
});

async function downloadFile(key: string) {
  try {
    const response = await api.get(
      `/api/files/download/${encodeURIComponent(key)}`,
      {
        responseType: "blob",
      }
    );

    // Extract filename from key
    const filename = key.split("/").pop() || "download";
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    toast.success(`File "${filename}" downloaded successfully`);
  } catch (err: any) {
    toast.error(err.response?.data?.detail || "Download failed");
  }
}

async function deleteFile(key: string) {
  if (!confirm(`Are you sure you want to delete file "${key}"?`)) {
    return;
  }

  try {
    await api.delete(`/api/files/${encodeURIComponent(key)}`);

    // Remove from tracked files (useLocalStorage will auto-save)
    files.value = files.value.filter((f) => f.key !== key);

    toast.success("File deleted successfully");
  } catch (err: any) {
    toast.error(err.response?.data?.detail || "Delete failed");
  }
}

const fileColumns = computed(() => [
  {
    key: "filename",
    label: "Filename",
    render: (value: any) => h("code", value),
  },
  {
    key: "key",
    label: "Key",
    render: (value: any) =>
      h("code", { class: "text-muted", style: "font-size: 0.75rem" }, value),
  },
  {
    key: "content_type",
    label: "Type",
    render: (value: any) => h("small", { class: "text-muted" }, value),
  },
  {
    key: "size",
    label: "Size",
    render: (value: any) =>
      h("small", { class: "text-muted" }, formatFileSize(value)),
  },
  {
    key: "uploaded_at",
    label: "Uploaded",
    render: (value: any) =>
      h("small", { class: "text-muted" }, formatDate(value)),
  },
  {
    key: "actions",
    label: "Actions",
    actions: [
      {
        label: "Download",
        action: (row: any) => downloadFile(row.key),
        variant: "primary" as const,
      },
      {
        label: "Delete",
        action: (row: any) => deleteFile(row.key),
        variant: "contrast" as const,
      },
    ],
  },
]);

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  if (bytes < 1024 * 1024 * 1024)
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  return (bytes / (1024 * 1024 * 1024)).toFixed(1) + " GB";
}

function formatDate(dateStr: string): string {
  if (!dateStr) return "-";
  const date = new Date(dateStr);
  // Use a simple format for now - composables can't be called in render functions
  const now = Date.now();
  const diff = now - date.getTime();
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  let timeAgo = "";
  if (days > 0) timeAgo = `${days} day${days > 1 ? "s" : ""} ago`;
  else if (hours > 0) timeAgo = `${hours} hour${hours > 1 ? "s" : ""} ago`;
  else if (minutes > 0)
    timeAgo = `${minutes} minute${minutes > 1 ? "s" : ""} ago`;
  else timeAgo = "just now";

  const formattedDate = date.toLocaleString("en-US", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  return `${timeAgo} (${formattedDate})`;
}

function openKeyModal() {
  manualKey.value = "";
  showKeyModal.value = true;
}

async function handleKeyAction(action: "download" | "delete") {
  if (!manualKey.value.trim()) {
    return;
  }

  const key = manualKey.value.trim();
  showKeyModal.value = false;

  if (action === "download") {
    await downloadFile(key);
  } else {
    await deleteFile(key);
  }
}
</script>

<template>
  <section data-animate="fade-in">
    <header class="page-header">
      <hgroup>
        <h1>Files</h1>
        <p>Manage files in storage</p>
      </hgroup>
      <div class="header-actions">
        <button class="secondary" @click="openKeyModal">Access by Key</button>
        <button v-if="storageEnabled" @click="openUploadModal">
          Upload File
        </button>
      </div>
    </header>

    <!-- Loading State -->
    <article v-if="loading" aria-busy="true">
      Checking storage status...
    </article>

    <!-- Storage Not Enabled -->
    <article v-else-if="!storageEnabled">
      <div data-empty data-empty-icon="📦">
        <p>File storage is not enabled</p>
        <p>
          <small class="text-muted">
            Configure file storage in Settings to enable file uploads and
            management.
          </small>
        </p>
        <router-link to="/settings" role="button" class="mt-3">
          Go to Settings
        </router-link>
      </div>
    </article>

    <!-- Storage Enabled - File Management -->
    <div v-else>
      <!-- Uploaded Files Table -->
      <article v-if="files.length > 0">
        <header>
          <h3>Recent Files</h3>
          <small class="text-muted">
            Files you've uploaded in this session. Use "Access by Key" to manage
            other files.
          </small>
        </header>

        <DataTable
          :data="files"
          :columns="fileColumns"
          :page-size="20"
          search-placeholder="Search files..."
        />
      </article>

      <!-- Empty State -->
      <article v-else>
        <div data-empty data-empty-icon="📁">
          <p>No files uploaded yet</p>
          <p>
            <small class="text-muted">
              Upload files to get started, or use "Access by Key" to manage
              existing files.
            </small>
          </p>
          <button @click="openUploadModal" class="mt-3">
            Upload Your First File
          </button>
        </div>
      </article>
    </div>

    <!-- Upload Modal -->
    <Modal v-model:open="showUploadModal" title="Upload File">
      <form id="upload-form" @submit="onSubmit">
        <div
          ref="dropZoneRef"
          :class="{ 'drop-zone-active': isOverDropZone }"
          style="
            border: 2px dashed var(--tb-border);
            border-radius: var(--tb-radius);
            padding: var(--tb-spacing-lg);
            text-align: center;
            margin-bottom: var(--tb-spacing-md);
            transition: all 0.2s;
          "
        >
          <p v-if="!isOverDropZone">Drag and drop a file here, or</p>
          <p v-else style="color: var(--tb-primary); font-weight: 600">
            Drop file here
          </p>
          <button
            type="button"
            class="secondary"
            @click="handleFileDialogClick"
            :disabled="uploading"
            style="margin-top: var(--tb-spacing-sm)"
          >
            Browse Files
          </button>
        </div>
        <Field name="file" v-slot="{ field, errors, meta }">
          <label for="field-file" style="display: none">
            File
            <input
              id="field-file"
              type="file"
              @change="handleFileSelect"
              :disabled="uploading"
              :aria-invalid="meta.touched && !meta.valid ? 'true' : 'false'"
            />
            <small v-if="meta.touched && errors[0]" class="text-error">
              {{ errors[0] }}
            </small>
          </label>
          <small
            v-if="meta.touched && errors[0]"
            class="text-error"
            style="display: block; margin-top: var(--tb-spacing-xs)"
          >
            {{ errors[0] }}
          </small>
        </Field>

        <FormField
          name="path_prefix"
          type="text"
          label="Path Prefix (optional)"
          placeholder="uploads/images/"
          :disabled="uploading"
          helper="Optional prefix to organize files (e.g., 'uploads/images/'). Trailing slash is optional."
        />
      </form>
      <template #footer>
        <button
          type="button"
          class="secondary"
          @click="showUploadModal = false"
          :disabled="uploading"
        >
          Cancel
        </button>
        <button
          type="submit"
          form="upload-form"
          :aria-busy="uploading"
          :disabled="uploading"
        >
          {{ uploading ? "" : "Upload" }}
        </button>
      </template>
    </Modal>

    <!-- Access by Key Modal -->
    <Modal v-model:open="showKeyModal" title="Access File by Key">
      <p class="text-muted">
        Enter the storage key (path) of a file to download or delete it.
      </p>

      <label for="manual_key">
        Storage Key
        <input
          id="manual_key"
          v-model="manualKey"
          type="text"
          placeholder="uploads/images/abc123.jpg"
          required
        />
      </label>

      <template #footer>
        <button type="button" class="secondary" @click="showKeyModal = false">
          Cancel
        </button>
        <button
          type="button"
          class="contrast"
          @click="handleKeyAction('delete')"
          :disabled="!manualKey.trim()"
        >
          Delete
        </button>
        <button
          type="button"
          @click="handleKeyAction('download')"
          :disabled="!manualKey.trim()"
        >
          Download
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
  margin-bottom: var(--tb-spacing-lg);
}

.page-header hgroup {
  margin: 0;
}

.page-header hgroup h1 {
  margin-bottom: var(--tb-spacing-xs);
}

.page-header hgroup p {
  margin: 0;
  color: var(--pico-muted-color);
}

.header-actions {
  display: flex;
  gap: var(--tb-spacing-sm);
}

.action-buttons {
  display: flex;
  gap: var(--tb-spacing-xs);
}

.action-buttons button {
  margin: 0;
}

.mt-3 {
  margin-top: var(--tb-spacing-lg);
}

code {
  font-size: 0.875rem;
  background: var(--tb-surface-1);
  padding: 0.125rem 0.25rem;
  border-radius: var(--tb-radius);
}

.drop-zone-active {
  border-color: var(--tb-primary) !important;
  background: var(--tb-primary-focus);
}
</style>
