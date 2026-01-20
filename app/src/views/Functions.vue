<script setup lang="ts">
/**
 * Functions View
 *
 * View and invoke registered functions.
 * Uses semantic HTML elements following PicoCSS conventions.
 */
import { onMounted, ref, computed, h } from "vue";
import { useToast } from "vue-toastification";
import {
  useFunctionsStore,
  generateTemplateFromSchema,
  type FunctionInfo,
} from "../stores/functions";
import { useAuthStore } from "../stores/auth";
import Modal from "../components/Modal.vue";
import DataTable from "../components/DataTable.vue";

const toast = useToast();
const functionsStore = useFunctionsStore();
const authStore = useAuthStore();

const showCallModal = ref(false);
const selectedFunction = ref<FunctionInfo | null>(null);
const callPayload = ref("{}");
const callResult = ref<any>(null);
const loadingSchema = ref(false);

// Upload function state
const showUploadModal = ref(false);
const uploadFilename = ref("");
const uploadContent = ref("");
const uploadNotes = ref("");
const uploading = ref(false);

// Version history state
const showVersionsModal = ref(false);
const selectedFunctionVersions = ref<any[]>([]);
const loadingVersions = ref(false);

onMounted(async () => {
  if (authStore.isAdmin) {
    await functionsStore.fetchAdminFunctions();
  } else {
    await functionsStore.fetchFunctions();
  }
});

async function openCallModal(fn: FunctionInfo) {
  selectedFunction.value = fn;
  callResult.value = null;
  showCallModal.value = true;

  // Fetch schema and generate template
  loadingSchema.value = true;
  try {
    const schema = await functionsStore.fetchFunctionSchema(fn.name);
    if (schema?.input_schema) {
      const template = generateTemplateFromSchema(schema.input_schema);
      callPayload.value = JSON.stringify(template, null, 2);
    } else {
      callPayload.value = "{}";
    }
  } catch {
    callPayload.value = "{}";
  } finally {
    loadingSchema.value = false;
  }
}

async function handleCall() {
  if (!selectedFunction.value) return;

  callResult.value = null;

  try {
    const payload = JSON.parse(callPayload.value);
    const result = await functionsStore.callFunction(
      selectedFunction.value.name,
      payload
    );
    callResult.value = result;
    if (result.status === "succeeded") {
      toast.success(
        `Function "${selectedFunction.value.name}" executed successfully`
      );
    } else {
      toast.error(
        `Function "${selectedFunction.value.name}" failed: ${
          result.error_message || "Unknown error"
        }`
      );
    }
  } catch (err: any) {
    const errorMsg = err.response?.data?.detail || err.message || "Call failed";
    toast.error(errorMsg);
    callResult.value = {
      status: "failed",
      error_type: "ExecutionError",
      error_message: errorMsg,
    };
  }
}

function openUploadModal() {
  uploadFilename.value = "";
  uploadContent.value = "";
  uploadNotes.value = "";
  showUploadModal.value = true;
}

async function handleUpload() {
  if (!uploadFilename.value || !uploadContent.value) {
    toast.error("Filename and content are required");
    return;
  }

  // Validate filename
  if (!uploadFilename.value.endsWith(".py")) {
    toast.error("Filename must end with .py");
    return;
  }

  uploading.value = true;
  try {
    const result = await functionsStore.uploadFunction(
      uploadFilename.value,
      uploadContent.value,
      uploadNotes.value || undefined
    );

    toast.success(
      result.is_new_version
        ? `Function "${result.function_name}" updated successfully`
        : `Function "${result.function_name}" created successfully`
    );

    // Show warnings if any
    if (result.warnings && result.warnings.length > 0) {
      result.warnings.forEach((warning: string) => {
        toast.warning(warning);
      });
    }

    showUploadModal.value = false;
    await functionsStore.fetchAdminFunctions();
  } catch (err: any) {
    toast.error(err.response?.data?.detail || "Failed to upload function");
  } finally {
    uploading.value = false;
  }
}

async function openVersionsModal(fn: FunctionInfo) {
  selectedFunction.value = fn;
  showVersionsModal.value = true;
  loadingVersions.value = true;

  try {
    selectedFunctionVersions.value = await functionsStore.fetchFunctionVersions(
      fn.name
    );
  } catch (err) {
    toast.error("Failed to load version history");
  } finally {
    loadingVersions.value = false;
  }
}

function getAuthStatus(
  auth: string
): "success" | "info" | "warning" | "neutral" {
  switch (auth) {
    case "public":
      return "success";
    case "auth":
      return "info";
    case "admin":
      return "warning";
    default:
      return "neutral";
  }
}

const displayFunctions = () => {
  return authStore.isAdmin
    ? functionsStore.adminFunctions
    : functionsStore.functions;
};

const functionColumns = computed(() => {
  const columns: any[] = [
    {
      key: "name",
      label: "Name",
      render: (value: any) => h("code", value),
    },
    {
      key: "description",
      label: "Description",
      render: (value: any) => h("small", { class: "text-muted" }, value || "-"),
    },
    {
      key: "auth",
      label: "Auth",
      render: (value: any) =>
        h("mark", { "data-status": getAuthStatus(value) }, value),
    },
    {
      key: "tags",
      label: "Tags",
      render: (value: any, row: any) => {
        if (!row.tags || row.tags.length === 0) {
          return h("small", { class: "text-muted" }, "-");
        }
        return h(
          "span",
          row.tags.map((tag: string) =>
            h(
              "mark",
              { "data-status": "neutral", style: "margin-right: 0.25rem" },
              tag
            )
          )
        );
      },
    },
  ];

  if (authStore.isAdmin) {
    columns.push({
      key: "module",
      label: "Module",
      render: (value: any) => h("small", { class: "text-muted" }, value),
    });
  }

  const actions: any[] = [
    {
      label: "Call",
      action: (row: any) => openCallModal(row),
      variant: "primary" as const,
    },
  ];

  // Add "Versions" action for admins
  if (authStore.isAdmin) {
    actions.push({
      label: "Versions",
      action: (row: any) => openVersionsModal(row),
      variant: "secondary" as const,
    });
  }

  columns.push({
    key: "actions",
    label: "Actions",
    actions,
  });

  return columns;
});
</script>

<template>
  <section data-animate="fade-in">
    <header class="page-header">
      <div>
        <h1>Functions</h1>
        <p>Registered server-side functions</p>
      </div>
      <button
        v-if="authStore.isAdmin"
        type="button"
        class="primary"
        @click="openUploadModal"
      >
        Upload Function
      </button>
    </header>

    <!-- Loading State -->
    <article v-if="functionsStore.loading" aria-busy="true">
      Loading functions...
    </article>

    <!-- Functions Table -->
    <article v-else>
      <DataTable
        :data="displayFunctions()"
        :columns="functionColumns"
        :page-size="20"
        search-placeholder="Search functions..."
        empty-message="No functions registered. Define functions in functions.py using the @register decorator."
      />
    </article>

    <!-- Call Function Modal -->
    <Modal v-model:open="showCallModal">
      <template #header>
        <h3>
          Call: <code>{{ selectedFunction?.name }}</code>
        </h3>
      </template>

      <p v-if="selectedFunction?.description" class="text-muted">
        {{ selectedFunction.description }}
      </p>

      <form @submit.prevent="handleCall">
        <label for="payload">
          Payload (JSON)
          <textarea
            v-if="loadingSchema"
            id="payload"
            rows="8"
            disabled
            aria-busy="true"
            class="code-editor"
          >
Loading schema...</textarea
          >
          <textarea
            v-else
            id="payload"
            v-model="callPayload"
            rows="8"
            class="code-editor"
            spellcheck="false"
          ></textarea>
        </label>

        <button
          type="submit"
          :aria-busy="functionsStore.loading"
          :disabled="functionsStore.loading || loadingSchema"
        >
          {{ functionsStore.loading ? "" : "Execute" }}
        </button>
      </form>

      <!-- Result Display -->
      <div v-if="callResult" class="mt-3">
        <h4>Result</h4>
        <p>
          <mark
            :data-status="
              callResult.status === 'succeeded' ? 'success' : 'error'
            "
          >
            {{ callResult.status }}
          </mark>
          <small
            v-if="callResult.duration_ms"
            class="text-muted"
            style="margin-left: 0.5rem"
          >
            Duration: {{ callResult.duration_ms }}ms
          </small>
        </p>
        <pre v-if="callResult.result">{{
          JSON.stringify(callResult.result, null, 2)
        }}</pre>
        <p v-if="callResult.error_message" class="text-error">
          <strong>{{ callResult.error_type }}:</strong>
          {{ callResult.error_message }}
        </p>
      </div>
    </Modal>

    <!-- Upload Function Modal -->
    <Modal v-model:open="showUploadModal">
      <template #header>
        <h3>Upload Function</h3>
      </template>

      <form @submit.prevent="handleUpload">
        <label for="upload-filename">
          Filename
          <input
            id="upload-filename"
            v-model="uploadFilename"
            type="text"
            placeholder="my_function.py"
            required
          />
          <small>Must end with .py and be a valid Python identifier.</small>
        </label>

        <label for="upload-content">
          Function Code
          <textarea
            id="upload-content"
            v-model="uploadContent"
            rows="15"
            class="code-editor"
            spellcheck="false"
            required
            placeholder="# /// script
# dependencies = [
#   &quot;tinybase-sdk&quot;,
# ]
# ///

from pydantic import BaseModel
from tinybase_sdk import register

@register(name=&quot;my_function&quot;, description=&quot;My function&quot;)
def my_function(client, payload):
    return {&quot;result&quot;: &quot;success&quot;}
"
          ></textarea>
        </label>

        <label for="upload-notes">
          Deployment Notes (optional)
          <textarea
            id="upload-notes"
            v-model="uploadNotes"
            rows="3"
            placeholder="What changed in this version..."
          ></textarea>
        </label>

        <div style="display: flex; gap: 0.5rem; justify-content: flex-end">
          <button
            type="button"
            class="secondary"
            @click="showUploadModal = false"
            :disabled="uploading"
          >
            Cancel
          </button>
          <button type="submit" :aria-busy="uploading" :disabled="uploading">
            {{ uploading ? "" : "Upload" }}
          </button>
        </div>
      </form>
    </Modal>

    <!-- Version History Modal -->
    <Modal v-model:open="showVersionsModal" wide>
      <template #header>
        <h3>
          Version History: <code>{{ selectedFunction?.name }}</code>
        </h3>
      </template>

      <div v-if="loadingVersions" aria-busy="true">Loading versions...</div>

      <div v-else-if="selectedFunctionVersions.length === 0">
        <p class="text-muted">No version history available.</p>
      </div>

      <table v-else>
        <thead>
          <tr>
            <th>Version ID</th>
            <th>Content Hash</th>
            <th>Deployed By</th>
            <th>Deployed At</th>
            <th>Executions</th>
            <th>Notes</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="version in selectedFunctionVersions" :key="version.id">
            <td>
              <code style="font-size: 0.75rem">{{
                version.id.substring(0, 8)
              }}</code>
            </td>
            <td>
              <code style="font-size: 0.75rem">{{
                version.content_hash.substring(0, 8)
              }}</code>
            </td>
            <td>
              <small>{{ version.deployed_by_email || "-" }}</small>
            </td>
            <td>
              <small>{{ new Date(version.deployed_at).toLocaleString() }}</small>
            </td>
            <td>{{ version.execution_count }}</td>
            <td>
              <small>{{ version.notes || "-" }}</small>
            </td>
          </tr>
        </tbody>
      </table>
    </Modal>
  </section>
</template>

<style scoped>
pre {
  font-size: 0.875rem;
  white-space: pre-wrap;
  word-break: break-word;
}

.code-editor {
  font-family: ui-monospace, "SF Mono", "Cascadia Code", "Source Code Pro",
    Menlo, Consolas, monospace;
  font-size: 0.875rem;
  line-height: 1.5;
  tab-size: 2;
  resize: vertical;
}
</style>
