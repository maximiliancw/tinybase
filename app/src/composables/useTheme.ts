/**
 * Theme Management Composable
 *
 * Provides dark mode toggle functionality with persistence.
 * Uses VueUse's useDark composable for reactive theme management.
 * Integrates with Tailwind's dark mode class strategy.
 */
import { useDark, useToggle } from "@vueuse/core";

export function useTheme() {
  const isDark = useDark({
    selector: "html",
    attribute: "class",
    valueDark: "dark",
    valueLight: "",
    storageKey: "tinybase-theme",
  });

  const toggleTheme = useToggle(isDark);

  return {
    isDark,
    toggleTheme,
  };
}
