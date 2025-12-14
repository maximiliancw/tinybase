/**
 * Auto Refresh Composable
 *
 * Provides intelligent polling that pauses when the tab is hidden
 * or when the window loses focus. Uses VueUse's interval and visibility composables.
 */
import {
  useIntervalFn,
  useDocumentVisibility,
  useWindowFocus,
} from "@vueuse/core";
import { computed, watch } from "vue";

export interface UseAutoRefreshOptions {
  /** Interval in milliseconds */
  interval?: number;
  /** Whether to pause when tab is hidden */
  pauseOnHidden?: boolean;
  /** Whether to pause when window loses focus */
  pauseOnBlur?: boolean;
  /** Immediate execution on mount */
  immediate?: boolean;
}

export function useAutoRefresh(
  callback: () => void | Promise<void>,
  options: UseAutoRefreshOptions = {}
) {
  const {
    interval = 30000, // 30 seconds default
    pauseOnHidden = true,
    pauseOnBlur = false,
    immediate = false,
  } = options;

  const visibility = useDocumentVisibility();
  const { focused } = useWindowFocus();

  const shouldPause = computed(() => {
    if (pauseOnHidden && visibility.value === "hidden") {
      return true;
    }
    if (pauseOnBlur && !focused.value) {
      return true;
    }
    return false;
  });

  const { pause, resume, isActive } = useIntervalFn(callback, interval, {
    immediate,
  });

  // Pause/resume based on visibility and focus
  watch(
    shouldPause,
    (shouldPauseNow) => {
      if (shouldPauseNow) {
        pause();
      } else {
        resume();
      }
    },
    { immediate: true }
  );

  return {
    pause,
    resume,
    isActive,
    visibility,
    focused,
  };
}
