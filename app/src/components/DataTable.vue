<script setup lang="ts">
/**
 * DataTable Component
 *
 * Enhanced table component with search, pagination, and responsive rendering.
 * Built on shadcn-vue Table components.
 */
import { computed, ref, watch } from "vue";
import type { VNode } from "vue";
import { refDebounced, useBreakpoints } from "@vueuse/core";
import Icon from "./Icon.vue";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface ActionButton {
  label: string | ((row: any) => string);
  action: (row: any) => void | Promise<void>;
  variant?: "default" | "secondary" | "destructive" | "outline" | "ghost";
  disabled?: boolean | ((row: any) => boolean);
  icon?: string;
}

interface Column {
  key: string;
  label: string;
  render?: (value: any, row: any) => string | VNode;
  searchable?: boolean;
  actions?: ActionButton[];
}

interface HeaderAction {
  label: string;
  action: () => void | Promise<void>;
  variant?: "default" | "secondary" | "destructive" | "outline" | "ghost";
  icon?: string;
}

interface Props {
  data: any[];
  columns: Column[];
  searchable?: boolean;
  paginated?: boolean;
  pageSize?: number;
  searchPlaceholder?: string;
  emptyMessage?: string;
  headerAction?: HeaderAction;
}

const props = withDefaults(defineProps<Props>(), {
  searchable: true,
  paginated: true,
  pageSize: 10,
  searchPlaceholder: "Search...",
  emptyMessage: "No data available",
});

const searchQuery = ref("");
const debouncedSearchQuery = refDebounced(searchQuery, 300);
const currentPage = ref(1);

// Responsive breakpoints
const breakpoints = useBreakpoints({
  mobile: 0,
  tablet: 768,
  desktop: 1024,
});
const isMobile = breakpoints.smaller("tablet");

// Reset to page 1 when search query changes
watch(debouncedSearchQuery, () => {
  currentPage.value = 1;
});

function isActionsColumn(column: Column): boolean {
  return !!column.actions;
}

const searchableColumns = computed(() => {
  return props.columns.filter(
    (col) => !isActionsColumn(col) && col.searchable !== false
  );
});

const filteredData = computed(() => {
  if (!props.searchable || !debouncedSearchQuery.value.trim()) {
    return props.data;
  }

  const query = debouncedSearchQuery.value.toLowerCase().trim();

  return props.data.filter((row) => {
    return searchableColumns.value.some((column) => {
      if (column.render) {
        const value = getCellValue(column, row);
        const rendered = column.render(value, row);
        const searchableText =
          typeof rendered === "string" ? rendered : String(rendered);
        return searchableText.toLowerCase().includes(query);
      }

      const value = getCellValue(column, row);
      if (value == null) return false;
      return String(value).toLowerCase().includes(query);
    });
  });
});

const paginatedData = computed(() => {
  if (!props.paginated) {
    return filteredData.value;
  }

  const start = (currentPage.value - 1) * props.pageSize;
  const end = start + props.pageSize;
  return filteredData.value.slice(start, end);
});

const totalPages = computed(() => {
  if (!props.paginated) return 1;
  return Math.ceil(filteredData.value.length / props.pageSize);
});

const paginationInfo = computed(() => {
  if (!props.paginated || filteredData.value.length === 0) {
    return null;
  }

  const start = (currentPage.value - 1) * props.pageSize + 1;
  const end = Math.min(
    currentPage.value * props.pageSize,
    filteredData.value.length
  );

  return {
    start,
    end,
    total: filteredData.value.length,
  };
});

function isButtonDisabled(button: ActionButton, row: any): boolean {
  if (typeof button.disabled === "function") {
    return button.disabled(row);
  }
  return button.disabled ?? false;
}

function getButtonLabel(button: ActionButton, row: any): string {
  if (typeof button.label === "function") {
    return button.label(row);
  }
  return button.label;
}

async function handleAction(button: ActionButton, row: any) {
  if (isButtonDisabled(button, row)) return;
  await button.action(row);
}

function getCellValue(column: Column, row: any): any {
  if (column.key.includes(".")) {
    const keys = column.key.split(".");
    let value = row;
    for (const key of keys) {
      value = value?.[key];
      if (value === undefined) break;
    }
    return value;
  }
  return row[column.key];
}

function renderCell(column: Column, row: any): string | VNode {
  if (isActionsColumn(column)) {
    return "";
  }

  const value = getCellValue(column, row);
  if (column.render) {
    return column.render(value, row);
  }
  return value != null ? String(value) : "";
}

function isVNode(value: any): value is VNode {
  return value && typeof value === "object" && "type" in value;
}
</script>

<template>
  <div class="space-y-4">
    <!-- Search Bar and Header Action -->
    <div v-if="searchable || headerAction" class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div v-if="searchable" class="flex-1 space-y-1">
        <Input
          v-model="searchQuery"
          :placeholder="searchPlaceholder"
          class="max-w-sm"
        />
        <p
          v-if="debouncedSearchQuery.trim() && filteredData.length !== data.length"
          class="text-xs text-muted-foreground"
        >
          Showing {{ filteredData.length }} of {{ data.length }} results
        </p>
      </div>
      <div v-if="headerAction">
        <Button
          :variant="headerAction.variant || 'default'"
          @click="headerAction.action"
        >
          <Icon
            v-if="headerAction.icon"
            :name="headerAction.icon"
            :size="16"
          />
          {{ headerAction.label }}
        </Button>
      </div>
    </div>

    <!-- Desktop Table View -->
    <div class="hidden md:block rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead v-for="column in columns" :key="column.key">
              {{ column.label }}
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-if="paginatedData.length === 0">
            <TableCell :colspan="columns.length" class="h-24 text-center">
              {{ emptyMessage }}
            </TableCell>
          </TableRow>
          <TableRow v-for="(row, index) in paginatedData" :key="index">
            <TableCell v-for="column in columns" :key="column.key">
              <!-- Actions Column -->
              <div v-if="isActionsColumn(column)" class="flex gap-2">
                <Button
                  v-for="(button, btnIndex) in column.actions"
                  :key="btnIndex"
                  size="sm"
                  :variant="button.variant || 'ghost'"
                  :disabled="isButtonDisabled(button, row)"
                  @click="handleAction(button, row)"
                >
                  <Icon v-if="button.icon" :name="button.icon" :size="14" />
                  {{ getButtonLabel(button, row) }}
                </Button>
              </div>
              <!-- Regular Column -->
              <template v-else>
                <component
                  v-if="isVNode(renderCell(column, row))"
                  :is="renderCell(column, row)"
                />
                <span v-else>{{ renderCell(column, row) }}</span>
              </template>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>

    <!-- Mobile List View -->
    <div class="md:hidden space-y-4">
      <div v-if="paginatedData.length === 0" class="flex flex-col items-center justify-center py-16 text-center border rounded-lg">
        <p class="text-sm text-muted-foreground">{{ emptyMessage }}</p>
      </div>
      <div
        v-for="(row, index) in paginatedData"
        :key="index"
        class="rounded-lg border p-4 space-y-2"
      >
        <div v-for="column in columns" :key="column.key" class="flex justify-between gap-4">
          <!-- Actions Column -->
          <template v-if="isActionsColumn(column)">
            <span class="text-sm font-medium">{{ column.label }}</span>
            <div class="flex flex-col gap-2">
              <Button
                v-for="(button, btnIndex) in column.actions"
                :key="btnIndex"
                size="sm"
                :variant="button.variant || 'ghost'"
                :disabled="isButtonDisabled(button, row)"
                @click="handleAction(button, row)"
                class="w-full"
              >
                <Icon v-if="button.icon" :name="button.icon" :size="14" />
                {{ getButtonLabel(button, row) }}
              </Button>
            </div>
          </template>
          <!-- Regular Column -->
          <template v-else>
            <span class="text-sm font-medium text-muted-foreground">{{ column.label }}</span>
            <div class="text-sm">
              <component
                v-if="isVNode(renderCell(column, row))"
                :is="renderCell(column, row)"
              />
              <span v-else>{{ renderCell(column, row) }}</span>
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="paginated && totalPages > 1" class="flex items-center justify-between border-t pt-4">
      <Button
        size="sm"
        variant="outline"
        :disabled="currentPage === 1"
        @click="currentPage--"
      >
        Previous
      </Button>
      <p v-if="paginationInfo" class="text-sm text-muted-foreground">
        {{ paginationInfo.start }}-{{ paginationInfo.end }} of
        {{ paginationInfo.total }}
      </p>
      <Button
        size="sm"
        variant="outline"
        :disabled="currentPage >= totalPages"
        @click="currentPage++"
      >
        Next
      </Button>
    </div>
  </div>
</template>
