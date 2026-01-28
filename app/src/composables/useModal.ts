/**
 * Modal Composable
 *
 * Manages modal state with optional URL parameter integration.
 * Simplifies the common pattern of opening modals via URL params (e.g., ?action=create).
 */
import { ref, watch, computed } from 'vue';
import { useUrlSearchParams } from '@vueuse/core';

export interface UseModalOptions {
  /**
   * URL action parameter name to watch for auto-opening the modal.
   * Set to null to disable URL parameter watching.
   * @default 'create'
   */
  actionName?: string | null;
}

/**
 * Composable for managing modal open/close state with URL parameter support.
 *
 * @example
 * // Basic usage
 * const { isOpen, open, close } = useModal();
 *
 * @example
 * // With custom action name
 * const { isOpen, open, close } = useModal({ actionName: 'edit' });
 *
 * @example
 * // Without URL parameter support
 * const { isOpen, open, close } = useModal({ actionName: null });
 */
export function useModal(options: UseModalOptions = {}) {
  const { actionName = 'create' } = options;

  const isOpen = ref(false);

  // URL parameter integration
  if (actionName !== null) {
    const params = useUrlSearchParams('history');
    const action = computed(() => params.action as string | null);

    // Watch URL param to auto-open modal
    watch(
      action,
      (newAction) => {
        if (newAction === actionName) {
          isOpen.value = true;
          params.action = undefined;
        }
      },
      { immediate: true }
    );
  }

  const open = () => {
    isOpen.value = true;
  };

  const close = () => {
    isOpen.value = false;
  };

  const toggle = () => {
    isOpen.value = !isOpen.value;
  };

  return {
    isOpen,
    open,
    close,
    toggle,
  };
}
