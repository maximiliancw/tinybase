<script setup lang="ts">
/**
 * DataTable Component
 *
 * Enhanced table component built on PicoCSS with search, pagination, and responsive rendering.
 * Features:
 * - Reactive search filtering across searchable columns
 * - Client-side pagination
 * - Actions column with button definitions
 * - Responsive: renders as <table> on desktop, <dl> on mobile (≤768px)
 */
import { computed, ref, watch } from "vue";
import type { VNode } from "vue";
import Icon from "./Icon.vue";

interface ActionButton {
  label: string | ((row: any) => string);
  action: (row: any) => void | Promise<void>;
  variant?: "primary" | "secondary" | "contrast" | "outline";
  disabled?: boolean | ((row: any) => boolean);
  icon?: string;
}

interface Column {
  key: string;
  label: string;
  render?: (value: any, row: any) => string | VNode;
  searchable?: boolean; // default: true (ignored for actions columns)
  actions?: ActionButton[]; // For Actions column
}

interface HeaderAction {
  label: string;
  action: () => void | Promise<void>;
  variant?: "primary" | "secondary" | "contrast" | "outline";
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
const currentPage = ref(1);

// Reset to page 1 when search query changes
watch(searchQuery, () => {
  currentPage.value = 1;
});

// Check if a column is an Actions column
function isActionsColumn(column: Column): boolean {
  return !!column.actions;
}

// Get searchable columns (exclude Actions columns)
const searchableColumns = computed(() => {
  return props.columns.filter(
    (col) => !isActionsColumn(col) && col.searchable !== false
  );
});

// Filter data based on search query
const filteredData = computed(() => {
  if (!props.searchable || !searchQuery.value.trim()) {
    return props.data;
  }

  const query = searchQuery.value.toLowerCase().trim();

  return props.data.filter((row) => {
    return searchableColumns.value.some((column) => {
      // If column has a render function, use it for search (handles nested data)
      if (column.render) {
        const value = getCellValue(column, row);
        const rendered = column.render(value, row);
        const searchableText =
          typeof rendered === "string" ? rendered : String(rendered);
        return searchableText.toLowerCase().includes(query);
      }

      // Otherwise, use getCellValue which handles nested keys
      const value = getCellValue(column, row);
      if (value == null) return false;
      return String(value).toLowerCase().includes(query);
    });
  });
});

// Paginate filtered data
const paginatedData = computed(() => {
  if (!props.paginated) {
    return filteredData.value;
  }

  const start = (currentPage.value - 1) * props.pageSize;
  const end = start + props.pageSize;
  return filteredData.value.slice(start, end);
});

// Pagination info
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

// Check if button is disabled
function isButtonDisabled(button: ActionButton, row: any): boolean {
  if (typeof button.disabled === "function") {
    return button.disabled(row);
  }
  return button.disabled ?? false;
}

// Get button label
function getButtonLabel(button: ActionButton, row: any): string {
  if (typeof button.label === "function") {
    return button.label(row);
  }
  return button.label;
}

// Handle button click
async function handleAction(button: ActionButton, row: any) {
  if (isButtonDisabled(button, row)) return;
  await button.action(row);
}

// Get cell value for a column
function getCellValue(column: Column, row: any): any {
  // Handle nested keys (e.g., "data.field")
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

// Render cell content
function renderCell(column: Column, row: any): string | VNode {
  if (isActionsColumn(column)) {
    return ""; // Actions are handled separately
  }

  const value = getCellValue(column, row);
  if (column.render) {
    return column.render(value, row);
  }
  return value != null ? String(value) : "";
}

// Check if rendered content is a VNode
function isVNode(value: any): value is VNode {
  return value && typeof value === "object" && "type" in value;
}
</script>

<template>
  <div class="datatable">
    <!-- Search Bar and Header Action -->
    <div v-if="searchable || headerAction" class="datatable-header">
      <div class="grid">
        <div v-if="searchable" class="datatable-search-wrapper">
          <input
            type="search"
            :placeholder="searchPlaceholder"
            v-model="searchQuery"
          />
          <small
            v-if="searchQuery.trim() && filteredData.length !== data.length"
            class="text-muted"
          >
            Showing {{ filteredData.length }} of {{ data.length }} results
          </small>
        </div>
        <div v-if="headerAction" class="datatable-header-action">
          <button
            :class="[headerAction.variant || 'primary']"
            @click="headerAction.action"
          >
            <Icon
              v-if="headerAction.icon"
              :name="headerAction.icon"
              :size="16"
            />
            {{ headerAction.label }}
          </button>
        </div>
      </div>
    </div>

    <!-- Desktop Table View -->
    <div class="datatable-desktop">
      <table>
        <thead>
          <tr>
            <th v-for="column in columns" :key="column.key">
              {{ column.label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="paginatedData.length === 0">
            <td :colspan="columns.length" class="datatable-empty">
              <div data-empty data-empty-icon="📋">
                <p>{{ emptyMessage }}</p>
              </div>
            </td>
          </tr>
          <tr v-for="(row, index) in paginatedData" :key="index">
            <td v-for="column in columns" :key="column.key">
              <!-- Actions Column -->
              <div v-if="isActionsColumn(column)" class="datatable-actions">
                <a
                  v-for="(button, btnIndex) in column.actions"
                  :key="btnIndex"
                  href="#"
                  :class="['small', button.variant || 'secondary']"
                  :disabled="isButtonDisabled(button, row)"
                  @click="handleAction(button, row)"
                >
                  <Icon v-if="button.icon" :name="button.icon" :size="14" />
                  {{ getButtonLabel(button, row) }}
                </a>
              </div>
              <!-- Regular Column -->
              <template v-else>
                <component
                  v-if="isVNode(renderCell(column, row))"
                  :is="renderCell(column, row)"
                />
                <span v-else>{{ renderCell(column, row) }}</span>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Mobile List View -->
    <div class="datatable-mobile">
      <div v-if="paginatedData.length === 0" class="datatable-empty">
        <div data-empty data-empty-icon="📋">
          <p>{{ emptyMessage }}</p>
        </div>
      </div>
      <div
        v-for="(row, index) in paginatedData"
        :key="index"
        class="datatable-mobile-row"
      >
        <dl>
          <template v-for="column in columns" :key="column.key">
            <!-- Actions Column -->
            <template v-if="isActionsColumn(column)">
              <dt>{{ column.label }}</dt>
              <dd>
                <div class="datatable-mobile-actions">
                  <button
                    v-for="(button, btnIndex) in column.actions"
                    :key="btnIndex"
                    :class="['small', button.variant || 'secondary']"
                    :disabled="isButtonDisabled(button, row)"
                    @click="handleAction(button, row)"
                  >
                    <Icon v-if="button.icon" :name="button.icon" :size="14" />
                    {{ getButtonLabel(button, row) }}
                  </button>
                </div>
              </dd>
            </template>
            <!-- Regular Column -->
            <template v-else>
              <dt>{{ column.label }}</dt>
              <dd>
                <component
                  v-if="isVNode(renderCell(column, row))"
                  :is="renderCell(column, row)"
                />
                <span v-else>{{ renderCell(column, row) }}</span>
              </dd>
            </template>
          </template>
        </dl>
      </div>
    </div>

    <!-- Pagination -->
    <footer v-if="paginated && totalPages > 1" class="datatable-pagination">
      <button
        class="small secondary"
        :disabled="currentPage === 1"
        @click="currentPage--"
      >
        Previous
      </button>
      <small v-if="paginationInfo" class="text-muted">
        {{ paginationInfo.start }}-{{ paginationInfo.end }} of
        {{ paginationInfo.total }}
      </small>
      <button
        class="small secondary"
        :disabled="currentPage >= totalPages"
        @click="currentPage++"
      >
        Next
      </button>
    </footer>
  </div>
</template>

<style scoped>
.datatable {
  width: 100%;
}

/* Header (Search Bar and Action) */
.datatable-header {
  margin-bottom: var(--tb-spacing-md);
}

.datatable-header .grid {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--tb-spacing-md);
}

.datatable-search-wrapper {
  display: flex;
  flex-direction: column;
  min-width: 0;
  max-width: 50%;
}

.datatable-header input[type="search"] {
  width: 100%;
}

.datatable-header small {
  display: block;
  margin-top: var(--tb-spacing-xs);
}

.datatable-header-action {
  display: flex;
  align-items: flex-start;
  padding-top: 0;
  flex-shrink: 0;
}

.datatable-header-action button {
  white-space: nowrap;
  margin-top: 0;
}

/* Mobile: Stack and center */
@media (max-width: 768px) {
  .datatable-header .grid {
    flex-direction: column;
    align-items: center;
    justify-content: center;
  }

  .datatable-search-wrapper {
    width: 100%;
  }

  .datatable-header-action {
    width: 100%;
    justify-content: center;
  }

  .datatable-header-action button {
    width: auto;
  }
}

/* Desktop Table View */
.datatable-desktop {
  overflow-x: auto;
}

.datatable-desktop table {
  width: 100%;
}

/* Action buttons container */
.datatable-actions {
  display: flex;
  gap: var(--tb-spacing-xs);
  align-items: center;
  flex-wrap: wrap;
}

.datatable-actions a {
  padding: 5px 10px;
}

.datatable-empty {
  text-align: center;
  padding: var(--tb-spacing-xl) var(--tb-spacing-lg);
}

.datatable-empty [data-empty] {
  padding: var(--tb-spacing-lg);
  margin: 0;
}

/* Mobile List View */
.datatable-mobile {
  display: none;
}

.datatable-mobile-row {
  margin-bottom: var(--tb-spacing-md);
  padding: var(--tb-spacing-md);
  background: var(--pico-card-background-color);
  border: 1px solid var(--pico-card-border-color);
  border-radius: var(--tb-radius);
}

.datatable-mobile-row dl {
  margin: 0;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--tb-spacing-sm) var(--tb-spacing-md);
}

.datatable-mobile-row dt {
  font-weight: 600;
  color: var(--tb-text-secondary);
  font-size: 0.875rem;
}

.datatable-mobile-row dd {
  margin: 0;
  color: var(--tb-text);
}

.datatable-mobile-actions {
  display: flex;
  flex-direction: column;
  gap: var(--tb-spacing-xs);
  width: 100%;
}

.datatable-mobile-actions button {
  width: 100%;
  font-size: 0.8125rem;
  padding: 0.375rem 0.875rem;
  text-transform: uppercase;
}

/* Pagination */
.datatable-pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: var(--tb-spacing-md);
  padding-top: var(--tb-spacing-md);
  border-top: 1px solid var(--tb-border);
}

/* Responsive: Hide desktop table on mobile, show mobile list */
@media (max-width: 768px) {
  .datatable-desktop {
    display: none;
  }

  .datatable-mobile {
    display: block;
  }
}

/* Responsive: Hide mobile list on desktop, show desktop table */
@media (min-width: 769px) {
  .datatable-desktop {
    display: block;
  }

  .datatable-mobile {
    display: none;
  }
}
</style>
