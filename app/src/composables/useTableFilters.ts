/**
 * Table Filters Composable
 *
 * Provides reusable table filtering logic with URL search params
 * and debounced search. Combines VueUse composables for a complete
 * filtering solution.
 */
import { ref, computed, watch } from "vue";
import { useUrlSearchParams, refDebounced } from "@vueuse/core";

export interface UseTableFiltersOptions {
  /** Debounce delay in milliseconds */
  debounceMs?: number;
  /** Whether to sync filters with URL */
  syncWithUrl?: boolean;
  /** Initial search query */
  initialSearch?: string;
}

export function useTableFilters(options: UseTableFiltersOptions = {}) {
  const { debounceMs = 300, syncWithUrl = false, initialSearch = "" } = options;

  // URL search params for filter state
  const params = syncWithUrl ? useUrlSearchParams("history") : null;

  // Search query
  const searchQuery = ref<string>(
    syncWithUrl && params
      ? (params.search as string) || initialSearch
      : initialSearch
  );
  const debouncedSearchQuery = refDebounced(searchQuery, debounceMs);

  // Sync search with URL if enabled
  if (syncWithUrl && params) {
    watch(searchQuery, (newValue) => {
      if (newValue) {
        params.search = newValue;
      } else {
        params.search = undefined;
      }
    });

    watch(
      () => params.search,
      (newValue) => {
        if (newValue !== searchQuery.value) {
          searchQuery.value = (newValue as string) || "";
        }
      }
    );
  }

  // Filter function helper
  function createFilter<T>(
    data: T[],
    filterFn: (item: T, query: string) => boolean
  ) {
    return computed(() => {
      if (!debouncedSearchQuery.value.trim()) {
        return data;
      }
      const query = debouncedSearchQuery.value.toLowerCase().trim();
      return data.filter((item) => filterFn(item, query));
    });
  }

  return {
    searchQuery,
    debouncedSearchQuery,
    createFilter,
    clearSearch: () => {
      searchQuery.value = "";
    },
  };
}
