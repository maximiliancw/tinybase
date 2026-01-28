/**
 * Dark Mode Composable
 *
 * Automatically syncs with system color scheme preference
 */
import { useColorMode } from '@vueuse/core';

export function useDarkMode() {
  const mode = useColorMode({
    selector: 'html',
    attribute: 'class',
    modes: {
      // auto will sync with system preference
      light: 'light',
      dark: 'dark',
      auto: 'auto',
    },
    // Start with auto to follow system preference
    initialValue: 'auto',
  });

  return {
    mode,
    isDark: () => mode.value === 'dark',
    isLight: () => mode.value === 'light',
    isAuto: () => mode.value === 'auto',
  };
}
