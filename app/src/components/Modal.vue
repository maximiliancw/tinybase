<script setup lang="ts">
/**
 * Modal Component
 *
 * Standardized modal component built on PicoCSS's dialog element.
 * Provides consistent structure and behavior across the application.
 */
import { ref, watch } from "vue";
import { onKeyStroke } from "@vueuse/core";
import { useFocusTrap } from "@vueuse/integrations/useFocusTrap";

interface Props {
  /** Whether the modal is open */
  open: boolean;
  /** Optional title for the modal header */
  title?: string;
}

interface Emits {
  (e: "update:open", value: boolean): void;
  (e: "close"): void;
}

const props = withDefaults(defineProps<Props>(), {
  open: false,
  title: undefined,
});

const emit = defineEmits<Emits>();

const modalRef = ref<HTMLElement>();

// Focus trap for accessibility - only active when modal is open
const { activate, deactivate } = useFocusTrap(modalRef, {
  immediate: false,
  escapeDeactivates: true,
  clickOutsideDeactivates: false,
});

// Activate/deactivate focus trap based on modal state
watch(
  () => props.open,
  (isOpen) => {
    if (isOpen && modalRef.value) {
      activate();
    } else {
      deactivate();
    }
  }
);

function close() {
  emit("update:open", false);
  emit("close");
}

// Watch for ESC key to close modal
onKeyStroke("Escape", () => {
  if (props.open) {
    close();
  }
});
</script>

<template>
  <dialog :open="open">
    <article ref="modalRef">
      <header v-if="title || $slots.header">
        <h3 v-if="title && !$slots.header">{{ title }}</h3>
        <slot v-else name="header" />
        <button
          aria-label="Close"
          rel="prev"
          class="secondary icon-only"
          @click="close"
        ></button>
      </header>

      <slot />

      <footer v-if="$slots.footer">
        <slot name="footer" />
      </footer>
    </article>
  </dialog>
</template>

<style scoped>
/* Footer button layout - consistent across all modals */
footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--tb-spacing-sm);
  margin-top: var(--tb-spacing-lg);
}

footer button {
  margin: 0;
}

/* Close button positioning */
header {
  display: flex;
  align-items: center;
  gap: var(--tb-spacing-md);
}

header button.icon-only {
  margin: 0;
  margin-left: auto;
  flex-shrink: 0;
  align-self: center;
}
</style>
