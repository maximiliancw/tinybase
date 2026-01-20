<script setup lang="ts">
/**
 * Function Calls View
 *
 * View function call history (admin only).
 */
import { onMounted, ref, computed, h } from "vue";
import { useInfiniteScroll } from "@vueuse/core";
import { useFunctionsStore } from "../stores/functions";
import DataTable from "../components/DataTable.vue";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";

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

function getStatusVariant(
  status: string
): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case "succeeded":
      return "default";
    case "failed":
      return "destructive";
    case "running":
      return "secondary";
    default:
      return "outline";
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
    render: (value: any) => h("code", { class: "text-sm" }, value),
  },
  {
    key: "status",
    label: "Status",
    render: (value: any) =>
      h(Badge, { variant: getStatusVariant(value) }, () => value),
  },
  {
    key: "trigger_type",
    label: "Trigger",
    render: (value: any) => h(Badge, { variant: "outline" }, () => value),
  },
  {
    key: "duration_ms",
    label: "Duration",
    render: (value: any) =>
      h("span", { class: "text-sm text-muted-foreground" }, formatDuration(value)),
  },
  {
    key: "started_at",
    label: "Started",
    render: (value: any) =>
      h("span", { class: "text-sm text-muted-foreground" }, formatTimestamp(value)),
  },
  {
    key: "version_hash",
    label: "Version",
    render: (value: string | null, row: any) => {
      if (!value) return h("span", { class: "text-sm text-muted-foreground" }, "-");
      return h(
        "code",
        {
          class: "text-xs",
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
          "span",
          { class: "text-sm text-destructive" },
          `${row.error_type}: ${row.error_message.slice(0, 50)}...`
        );
      }
      return h("span", { class: "text-sm text-muted-foreground" }, "-");
    },
  },
]);
</script>

<template>
  <section class="space-y-6 animate-in fade-in duration-500">
    <!-- Page Header -->
    <header class="space-y-1">
      <h1 class="text-3xl font-bold tracking-tight">Function Calls</h1>
      <p class="text-muted-foreground">Execution history for all functions</p>
    </header>

    <!-- Filters -->
    <Card>
      <CardHeader>
        <CardTitle>Filters</CardTitle>
      </CardHeader>
      <CardContent>
        <div class="grid gap-4 md:grid-cols-3">
          <div class="space-y-2">
            <Label for="filter_function">Function</Label>
            <Select v-model="filters.function_name">
              <SelectTrigger>
                <SelectValue placeholder="All Functions" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Functions</SelectItem>
                <SelectItem
                  v-for="fn in functionsStore.functions"
                  :key="fn.name"
                  :value="fn.name"
                >
                  {{ fn.name }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="space-y-2">
            <Label for="filter_status">Status</Label>
            <Select v-model="filters.status">
              <SelectTrigger>
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Statuses</SelectItem>
                <SelectItem value="succeeded">Succeeded</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
                <SelectItem value="running">Running</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="space-y-2">
            <Label for="filter_trigger">Trigger</Label>
            <Select v-model="filters.trigger_type">
              <SelectTrigger>
                <SelectValue placeholder="All Triggers" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Triggers</SelectItem>
                <SelectItem value="manual">Manual</SelectItem>
                <SelectItem value="schedule">Schedule</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <Button
          class="mt-4"
          variant="secondary"
          @click="applyFilters"
        >
          Apply Filters
        </Button>
      </CardContent>
    </Card>

    <!-- Loading State -->
    <Card v-if="functionsStore.loading">
      <CardContent class="flex items-center justify-center py-10">
        <p class="text-sm text-muted-foreground">Loading function calls...</p>
      </CardContent>
    </Card>

    <!-- Empty State -->
    <Card v-else-if="displayedCalls.length === 0">
      <CardContent class="flex flex-col items-center justify-center py-16 text-center">
        <div class="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-muted text-3xl">
          📜
        </div>
        <p class="font-medium">No function calls yet</p>
        <p class="text-sm text-muted-foreground">
          Function calls will appear here when functions are invoked.
        </p>
      </CardContent>
    </Card>

    <!-- Function Calls Table -->
    <Card v-else ref="scrollContainer">
      <DataTable
        :data="displayedCalls"
        :columns="functionCallColumns"
        :paginated="false"
        search-placeholder="Search function calls..."
      />

      <!-- Server-side Pagination -->
      <div
        v-if="total > pageSize"
        class="flex items-center justify-between border-t p-4"
      >
        <Button
          size="sm"
          variant="ghost"
          :disabled="page === 1"
          @click="
            page--;
            loadCalls();
          "
        >
          Previous
        </Button>
        <span class="text-sm text-muted-foreground">
          Page {{ page }} of {{ Math.ceil(total / pageSize) }} ({{ total }}
          total)
        </span>
        <Button
          size="sm"
          variant="ghost"
          :disabled="page >= Math.ceil(total / pageSize)"
          @click="
            page++;
            loadCalls();
          "
        >
          Next
        </Button>
      </div>
    </Card>
  </section>
</template>
