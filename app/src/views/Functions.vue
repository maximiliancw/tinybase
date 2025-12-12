<script setup lang="ts">
/**
 * Functions View
 *
 * View and invoke registered functions.
 * Uses semantic HTML elements following PicoCSS conventions.
 */
import { onMounted, ref } from "vue";
import {
  useFunctionsStore,
  generateTemplateFromSchema,
  type FunctionInfo,
} from "../stores/functions";
import { useAuthStore } from "../stores/auth";
import Modal from "../components/Modal.vue";

const functionsStore = useFunctionsStore();
const authStore = useAuthStore();

const showCallModal = ref(false);
const selectedFunction = ref<FunctionInfo | null>(null);
const callPayload = ref("{}");
const callResult = ref<any>(null);
const callError = ref<string | null>(null);
const loadingSchema = ref(false);

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
  callError.value = null;
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

  callError.value = null;
  callResult.value = null;

  try {
    const payload = JSON.parse(callPayload.value);
    const result = await functionsStore.callFunction(
      selectedFunction.value.name,
      payload
    );
    callResult.value = result;
  } catch (err: any) {
    callError.value =
      err.response?.data?.detail || err.message || "Call failed";
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
</script>

<template>
  <section data-animate="fade-in">
    <header class="page-header">
      <h1>Functions</h1>
      <p>Registered server-side functions</p>
    </header>

    <!-- Loading State -->
    <article v-if="functionsStore.loading" aria-busy="true">
      Loading functions...
    </article>

    <!-- Empty State -->
    <article v-else-if="displayFunctions().length === 0">
      <div data-empty data-empty-icon="⚡">
        <p>No functions registered</p>
        <p>
          <small class="text-muted"
            >Define functions in functions.py using the @register
            decorator.</small
          >
        </p>
      </div>
    </article>

    <!-- Functions Table -->
    <article v-else>
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Description</th>
            <th>Auth</th>
            <th>Tags</th>
            <th v-if="authStore.isAdmin">Module</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="fn in displayFunctions()" :key="fn.name">
            <td>
              <code>{{ fn.name }}</code>
            </td>
            <td>
              <small class="text-muted">{{ fn.description || "-" }}</small>
            </td>
            <td>
              <mark :data-status="getAuthStatus(fn.auth)">
                {{ fn.auth }}
              </mark>
            </td>
            <td>
              <mark
                v-for="tag in fn.tags"
                :key="tag"
                data-status="neutral"
                style="margin-right: 0.25rem"
              >
                {{ tag }}
              </mark>
              <small v-if="fn.tags.length === 0" class="text-muted">-</small>
            </td>
            <td v-if="authStore.isAdmin">
              <small class="text-muted">{{ fn.module }}</small>
            </td>
            <td>
              <button class="small" @click="openCallModal(fn)">Call</button>
            </td>
          </tr>
        </tbody>
      </table>
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

      <small v-if="callError" class="text-error">
        {{ callError }}
      </small>
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
