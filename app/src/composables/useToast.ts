/**
 * Toast Composable
 *
 * Wrapper around vue-sonner for toast notifications.
 * Provides a consistent API similar to vue-toastification.
 */
import { toast as sonnerToast } from 'vue-sonner';

export interface ToastOptions {
  timeout?: number;
  duration?: number;
}

export function useToast() {
  return {
    success: (message: string, options?: ToastOptions) => {
      sonnerToast.success(message, {
        duration: options?.duration || options?.timeout || 3000,
      });
    },
    error: (message: string, options?: ToastOptions) => {
      sonnerToast.error(message, {
        duration: options?.duration || options?.timeout || 3000,
      });
    },
    warning: (message: string, options?: ToastOptions) => {
      sonnerToast.warning(message, {
        duration: options?.duration || options?.timeout || 3000,
      });
    },
    info: (message: string, options?: ToastOptions) => {
      sonnerToast.info(message, {
        duration: options?.duration || options?.timeout || 3000,
      });
    },
  };
}
