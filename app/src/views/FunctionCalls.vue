<script setup lang="ts">
/**
 * Function Calls View
 *
 * View function call history (admin only).
 * Uses semantic HTML elements following PicoCSS conventions.
 */
import { onMounted, ref, computed, h } from "vue";
import { useInfiniteScroll } from "@vueuse/core";
import { useFunctionsStore } from "../stores/functions";
import DataTable from "../components/DataTable.vue";

const functionsStore = useFunctionsStore();

const page = ref(1);
const pageSize = 50;
const total = ref(0);
const loadingMore = ref(false);
const filters = ref({
  function_name: "",
  status: "",
  trigger_type: "",
});

// Local ref for infinite scroll (appends instead of replacing)
const displayedCalls = ref<any[]>([]);

const scrollContainer = ref<HTMLElement>();

onMounted(async () => {
  await loadCalls(true); // Reset on initial load
  await functionsStore.fetchFunctions();
});

async function loadCalls(reset = false) {
  loadingMore.value = true;
  try {
    const result = await functionsStore.fetchFunctionCalls({
      ...filters.value,
      limit: pageSize,
      offset: (page.value - 1) * pageSize,
    });
    if (reset) {
      displayedCalls.value = result.calls;
    } else {
      displayedCalls.value = [...displayedCalls.value, ...result.calls];
    }
    total.value = result.total;
  } finally {
    loadingMore.value = false;
  }
}

async function loadMore() {
  if (loadingMore.value || page.value * pageSize >= total.value) {
    return;
  }
  page.value++;
  await loadCalls(false); // Don't reset, append
}

// Infinite scroll
useInfiniteScroll(
  scrollContainer,
  () => {
    loadMore();
  },
  { distance: 10 }
);

async function applyFilters() {
  page.value = 1;
  await loadCalls(true); // Reset when filters change
}

function getStatusType(
  status: string
): "success" | "error" | "warning" | "neutral" {
  switch (status) {
    case "succeeded":
      return "success";
    case "failed":
      return "error";
    case "running":
      return "warning";
    default:
      return "neutral";
  }
}

function formatDuration(ms: number | null): string {
  if (ms === null) return "-";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

function formatTimestamp(value: string | null): string {
  if (!value) return "-";
  const date = new Date(value);
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

const functionCallColumns = computed(() => [
  {
    key: "function_name",
    label: "Function",
    render: (value: any) => h("code", value),
  },
  {
    key: "status",
    label: "Status",
    render: (value: any) =>
      h("mark", { "data-status": getStatusType(value) }, value),
  },
  {
    key: "trigger_type",
    label: "Trigger",
    render: (value: any) => h("mark", { "data-status": "neutral" }, value),
  },
  {
    key: "duration_ms",
    label: "Duration",
    render: (value: any) =>
      h("small", { class: "text-muted" }, formatDuration(value)),
  },
  {
    key: "started_at",
    label: "Started",
    render: (value: any) =>
      h("small", { class: "text-muted" }, formatTimestamp(value)),
  },
  {
    key: "version_hash",
    label: "Version",
    render: (value: string | null, row: any) => {
      if (!value) return h("small", { class: "text-muted" }, "-");
      return h(
        "code",
        {
          style: { fontSize: "0.75rem" },
          title: `Version ID: ${row.version_id || "N/A"}`,
        },
        value.substring(0, 8)
      );
    },
  },
  {
    key: "error",
    label: "Error",
    render: (_value: any, row: any) => {
      if (row.error_message) {
        return h(
          "small",
          { class: "text-error" },
          `${row.error_type}: ${row.error_message.slice(0, 50)}...`
        );
      }
      return h("small", { class: "text-muted" }, "-");
    },
  },
]);
</script>

<template>
  <section data-animate="fade-in">
    <header class="page-header">
      <h1>Function Calls</h1>
      <p>Execution history for all functions</p>
    </header>

    <!-- Filters - using Pico's grid for layout -->
    <article class="filters">
      <div class="grid">
        <label>
          Function
          <select v-model="filters.function_name">
            <option value="">All Functions</option>
            <option
              v-for="fn in functionsStore.functions"
              :key="fn.name"
              :value="fn.name"
            >
              {{ fn.name }}
            </option>
          </select>
        </label>

        <label>
          Status
          <select v-model="filters.status">
            <option value="">All Statuses</option>
            <option value="succeeded">Succeeded</option>
            <option value="failed">Failed</option>
            <option value="running">Running</option>
          </select>
        </label>

        <label>
          Trigger
          <select v-model="filters.trigger_type">
            <option value="">All Triggers</option>
            <option value="manual">Manual</option>
            <option value="schedule">Schedule</option>
          </select>
        </label>
      </div>
      <button class="secondary" @click="applyFilters">Apply Filters</button>
    </article>

    <!-- Loading State -->
    <article v-if="functionsStore.loading" aria-busy="true">
      Loading function calls...
    </article>

    <!-- Empty State -->
    <article v-else-if="displayedCalls.length === 0">
      <div data-empty data-empty-icon="📜">
        <p>No function calls yet</p>
        <p>
          <small class="text-muted"
            >Function calls will appear here when functions are invoked.</small
          >
        </p>
      </div>
    </article>

    <!-- Function Calls Table -->
    <article v-else ref="scrollContainer">
      <DataTable
        :data="displayedCalls"
        :columns="functionCallColumns"
        :paginated="false"
        search-placeholder="Search function calls..."
      />

      <!-- Server-side Pagination -->
      <footer v-if="total > pageSize" class="server-pagination">
        <button
          class="small secondary"
          :disabled="page === 1"
          @click="
            page--;
            loadCalls();
          "
        >
          Previous
        </button>
        <small class="text-muted">
          Page {{ page }} of {{ Math.ceil(total / pageSize) }} ({{ total }}
          total)
        </small>
        <button
          class="small secondary"
          :disabled="page >= Math.ceil(total / pageSize)"
          @click="
            page++;
            loadCalls();
          "
        >
          Next
        </button>
      </footer>
    </article>
  </section>
</template>

<style scoped>
.filters {
  margin-bottom: var(--tb-spacing-lg);
}

.filters .grid {
  margin-bottom: var(--tb-spacing-md);
}

.server-pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: var(--tb-spacing-md);
  padding-top: var(--tb-spacing-md);
  border-top: 1px solid var(--tb-border);
}
</style>
