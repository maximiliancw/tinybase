<script setup lang="ts">
/**
 * Files View
 *
 * Admin page for managing file storage.
 * Allows uploading, downloading, and deleting files.
 */
import { onMounted, ref, computed, h, watch } from "vue";
import { useToast } from "../composables/useToast";
import { useForm, Field, useField } from "vee-validate";
import { useLocalStorage, useFileDialog, useDropZone } from "@vueuse/core";
import { api } from "@/api";
import { client } from "../client/client.gen";
import { validationSchemas } from "../composables/useFormValidation";
import DataTable from "../components/DataTable.vue";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

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

const fileField = useField("file");
const pathPrefixField = useField("path_prefix");

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
    const response = await api.files.getStorageStatus();
    storageEnabled.value = response.data.enabled;
  } catch (err: any) {
    toast.error(err.error?.detail || "Failed to check storage status");
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

    const response = await api.files.uploadFile({
      body: formData,
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
    toast.error(err.error?.detail || "Upload failed");
  } finally {
    uploading.value = false;
  }
});

async function downloadFile(key: string) {
  try {
    // Use axios instance directly for blob downloads
    const response = await client.instance.get(
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
    toast.error(err.error?.detail || "Download failed");
  }
}

async function deleteFile(key: string) {
  if (!confirm(`Are you sure you want to delete file "${key}"?`)) {
    return;
  }

  try {
    await api.files.deleteFile({
      path: { key: encodeURIComponent(key) },
    });

    // Remove from tracked files (useLocalStorage will auto-save)
    files.value = files.value.filter((f) => f.key !== key);

    toast.success("File deleted successfully");
  } catch (err: any) {
    toast.error(err.error?.detail || "Delete failed");
  }
}

const fileColumns = computed(() => [
  {
    key: "filename",
    label: "Filename",
    render: (value: any) => h("code", { class: "text-sm" }, value),
  },
  {
    key: "key",
    label: "Key",
    render: (value: any) =>
      h("code", { class: "text-xs text-muted-foreground" }, value),
  },
  {
    key: "content_type",
    label: "Type",
    render: (value: any) => h("span", { class: "text-sm text-muted-foreground" }, value),
  },
  {
    key: "size",
    label: "Size",
    render: (value: any) =>
      h("span", { class: "text-sm text-muted-foreground" }, formatFileSize(value)),
  },
  {
    key: "uploaded_at",
    label: "Uploaded",
    render: (value: any) =>
      h("span", { class: "text-sm text-muted-foreground" }, formatDate(value)),
  },
  {
    key: "actions",
    label: "Actions",
    actions: [
      {
        label: "Download",
        action: (row: any) => downloadFile(row.key),
        variant: "default" as const,
      },
      {
        label: "Delete",
        action: (row: any) => deleteFile(row.key),
        variant: "destructive" as const,
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
  <section class="space-y-6 animate-in fade-in duration-500">
    <!-- Page Header -->
    <header class="flex items-start justify-between">
      <div class="space-y-1">
        <h1 class="text-3xl font-bold tracking-tight">Files</h1>
        <p class="text-muted-foreground">Manage files in storage</p>
      </div>
      <Button variant="ghost" @click="openKeyModal">
        Access by Key
      </Button>
    </header>

    <!-- Loading State -->
    <Card v-if="loading">
      <CardContent class="flex items-center justify-center py-10">
        <p class="text-sm text-muted-foreground">Checking storage status...</p>
      </CardContent>
    </Card>

    <!-- Storage Not Enabled -->
    <Card v-else-if="!storageEnabled">
      <CardContent class="flex flex-col items-center justify-center py-16 text-center">
        <div class="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-muted text-3xl">
          📦
        </div>
        <h3 class="mb-1 text-lg font-semibold">File storage is not enabled</h3>
        <p class="mb-4 text-sm text-muted-foreground">
          Configure file storage in Settings to enable file uploads and management.
        </p>
        <Button as-child>
          <router-link to="/settings">Go to Settings</router-link>
        </Button>
      </CardContent>
    </Card>

    <!-- Storage Enabled - File Management -->
    <template v-else>
      <!-- Uploaded Files Table -->
      <Card v-if="files.length > 0">
        <CardHeader>
          <CardTitle>Recent Files</CardTitle>
          <p class="text-sm text-muted-foreground">
            Files you've uploaded in this session. Use "Access by Key" to manage
            other files.
          </p>
        </CardHeader>
        <CardContent>
          <DataTable
            :data="files"
            :columns="fileColumns"
            :page-size="20"
            search-placeholder="Search files..."
            :header-action="{
              label: 'Upload File',
              action: () => {
                openUploadModal();
              },
              variant: 'default',
              icon: 'Plus',
            }"
          />
        </CardContent>
      </Card>

      <!-- Empty State -->
      <Card v-else>
        <CardContent class="flex flex-col items-center justify-center py-16 text-center">
          <div class="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-muted text-3xl">
            📁
          </div>
          <h3 class="mb-1 text-lg font-semibold">No files uploaded yet</h3>
          <p class="mb-4 text-sm text-muted-foreground">
            Upload files to get started, or use "Access by Key" to manage existing files.
          </p>
          <Button @click="openUploadModal">
            Upload Your First File
          </Button>
        </CardContent>
      </Card>
    </template>

    <!-- Upload Modal -->
    <Dialog v-model:open="showUploadModal">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Upload File</DialogTitle>
        </DialogHeader>

        <form id="upload-form" @submit.prevent="onSubmit" class="space-y-4">
          <div
            ref="dropZoneRef"
            class="border-2 border-dashed rounded-lg p-8 text-center transition-colors"
            :class="{
              'border-primary bg-primary/10': isOverDropZone,
              'border-border': !isOverDropZone,
            }"
          >
            <p v-if="!isOverDropZone" class="mb-3 text-sm text-muted-foreground">
              Drag and drop a file here, or
            </p>
            <p v-else class="mb-3 text-sm font-semibold text-primary">
              Drop file here
            </p>
            <Button
              type="button"
              variant="secondary"
              @click="handleFileDialogClick"
              :disabled="uploading"
            >
              Browse Files
            </Button>
          </div>

          <Field name="file" v-slot="{ errors, meta }">
            <input
              type="file"
              class="sr-only"
              @change="handleFileSelect"
              :disabled="uploading"
              :aria-invalid="meta.touched && !meta.valid ? 'true' : 'false'"
            />
            <p v-if="meta.touched && errors[0]" class="text-sm text-destructive">
              {{ errors[0] }}
            </p>
          </Field>

          <div class="space-y-2">
            <Label for="path_prefix">Path Prefix (optional)</Label>
            <Input
              id="path_prefix"
              v-model="pathPrefixField.value.value"
              placeholder="uploads/images/"
              :disabled="uploading"
            />
            <p class="text-xs text-muted-foreground">
              Optional prefix to organize files (e.g., 'uploads/images/'). Trailing slash is optional.
            </p>
          </div>
        </form>

        <DialogFooter>
          <Button
            type="button"
            variant="ghost"
            @click="showUploadModal = false"
            :disabled="uploading"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            form="upload-form"
            :disabled="uploading"
          >
            {{ uploading ? "Uploading..." : "Upload" }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Access by Key Modal -->
    <Dialog v-model:open="showKeyModal">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Access File by Key</DialogTitle>
        </DialogHeader>

        <div class="space-y-4">
          <p class="text-sm text-muted-foreground">
            Enter the storage key (path) of a file to download or delete it.
          </p>

          <div class="space-y-2">
            <Label for="manual_key">Storage Key</Label>
            <Input
              id="manual_key"
              v-model="manualKey"
              placeholder="uploads/images/abc123.jpg"
              required
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="ghost"
            @click="showKeyModal = false"
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="destructive"
            @click="handleKeyAction('delete')"
            :disabled="!manualKey.trim()"
          >
            Delete
          </Button>
          <Button
            type="button"
            @click="handleKeyAction('download')"
            :disabled="!manualKey.trim()"
          >
            Download
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </section>
</template>
