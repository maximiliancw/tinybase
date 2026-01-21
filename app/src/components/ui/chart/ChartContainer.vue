<script setup lang="ts">
import { computed, provide, ref, toRef, watch } from 'vue';
import { cn } from '@/lib/utils';

interface ChartConfig {
  [key: string]: {
    label: string;
    color?: string;
  };
}

interface Props {
  config: ChartConfig;
  class?: string;
}

const props = defineProps<Props>();

provide('chartConfig', toRef(props, 'config'));
</script>

<template>
  <div
    :class="
      cn(
        'flex aspect-video justify-center text-xs [&_.unovis-xy-container]:!pointer-events-none',
        props.class
      )
    "
  >
    <slot />
  </div>
</template>
