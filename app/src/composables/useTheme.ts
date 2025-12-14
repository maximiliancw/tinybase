/**
 * Theme Management Composable
 *
 * Provides dark mode toggle functionality with persistence.
 * Uses VueUse's useDark composable for reactive theme management.
 */
import { useDark, useToggle } from "@vueuse/core";

export function useTheme() {
  const isDark = useDark({
    selector: "html",
    attribute: "data-theme",
    valueDark: "dark",
    valueLight: "light",
    storageKey: "tinybase-theme",
  });

  const toggleTheme = useToggle(isDark);

  return {
    isDark,
    toggleTheme,
  };
}
