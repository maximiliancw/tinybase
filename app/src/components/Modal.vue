<script setup lang="ts">
/**
 * Modal Component
 *
 * Standardized modal component built on PicoCSS's dialog element.
 * Provides consistent structure and behavior across the application.
 */
import { watch, onUnmounted } from "vue";
import Icon from "./Icon.vue";

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

function close() {
  emit("update:open", false);
  emit("close");
}

// Watch for ESC key to close modal
let cleanup: (() => void) | null = null;

watch(
  () => props.open,
  (isOpen) => {
    if (cleanup) {
      cleanup();
      cleanup = null;
    }

    if (isOpen) {
      const handleEscape = (e: KeyboardEvent) => {
        if (e.key === "Escape") {
          close();
        }
      };
      document.addEventListener("keydown", handleEscape);
      cleanup = () => {
        document.removeEventListener("keydown", handleEscape);
      };
    }
  }
);

onUnmounted(() => {
  if (cleanup) {
    cleanup();
  }
});
</script>

<template>
  <dialog :open="open">
    <article>
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
