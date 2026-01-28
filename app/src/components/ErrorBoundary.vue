<script setup lang="ts">
/**
 * ErrorBoundary Component
 *
 * Global error boundary that catches unhandled errors in child components.
 * Displays a user-friendly error message with a retry option.
 */
import { onErrorCaptured, ref } from 'vue';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { AlertCircle } from 'lucide-vue-next';

const error = ref<Error | null>(null);
const errorInfo = ref<string | null>(null);

onErrorCaptured((err, instance, info) => {
  error.value = err;
  errorInfo.value = info;
  // Prevent propagation to parent error handlers
  return false;
});

function reset() {
  error.value = null;
  errorInfo.value = null;
}
</script>

<template>
  <div v-if="error" class="flex items-center justify-center min-h-[400px] p-6">
    <div class="max-w-md w-full space-y-4">
      <Alert variant="destructive">
        <AlertCircle class="h-4 w-4" />
        <AlertTitle>Something went wrong</AlertTitle>
        <AlertDescription class="mt-2">
          <p class="text-sm">{{ error.message }}</p>
          <p v-if="errorInfo" class="text-xs mt-2 opacity-75">
            Error occurred in: {{ errorInfo }}
          </p>
        </AlertDescription>
      </Alert>
      <div class="flex gap-2">
        <Button variant="outline" size="sm" @click="reset">
          Try again
        </Button>
        <Button variant="ghost" size="sm" @click="$router.go(0)">
          Reload page
        </Button>
      </div>
    </div>
  </div>
  <slot v-else />
</template>
