<script setup lang="ts">
import { computed, inject } from 'vue';
import { cn } from '@/lib/utils';

interface Props {
  class?: string;
}

const props = defineProps<Props>();
const chartConfig = inject<any>('chartConfig', {});
</script>

<template>
  <div
    :class="
      cn(
        'grid min-w-[8rem] items-start gap-1.5 rounded-lg border border-border/50 bg-background px-2.5 py-1.5 text-xs shadow-xl',
        props.class
      )
    "
  >
    <slot />
  </div>
</template>
