/**
 * Network Status Composable
 *
 * Provides network connectivity status monitoring.
 * Uses VueUse's useOnline and useNetwork composables.
 */
import { useOnline, useNetwork } from '@vueuse/core';
import { computed } from 'vue';

export function useNetworkStatus() {
  const isOnline = useOnline();
  const network = useNetwork();

  const status = computed(() => {
    if (!isOnline.value) {
      return {
        online: false,
        message: 'You are currently offline',
        type: 'error' as const,
      };
    }

    if (network.effectiveType) {
      const type = network.effectiveType.value;
      if (type === 'slow-2g' || type === '2g') {
        return {
          online: true,
          message: 'Slow connection detected',
          type: 'warning' as const,
        };
      }
    }

    return {
      online: true,
      message: null,
      type: null as null,
    };
  });

  return {
    isOnline,
    network,
    status,
  };
}
