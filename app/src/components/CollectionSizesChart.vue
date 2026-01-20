<script setup lang="ts">
/**
 * Collection Sizes Pie Chart Component
 *
 * Displays a pie chart showing the distribution of records across collections using Unovis.
 */
import { computed } from "vue";
import { VisSingleContainer, VisDonut } from "@unovis/vue";
import { ChartContainer } from "@/components/ui/chart";

interface CollectionSize {
  collection_name: string;
  record_count: number;
}

const props = defineProps<{
  data: CollectionSize[];
}>();

const chartData = computed(() => props.data || []);

const chartConfig = computed(() => {
  const config: any = {};
  props.data.forEach((item, index) => {
    config[item.collection_name] = {
      label: item.collection_name,
      color: `hsl(${(index * 360) / props.data.length}, 70%, 50%)`,
    };
  });
  return config;
});

const colors = computed(() =>
  props.data.map(
    (_, index) => `hsl(${(index * 360) / props.data.length}, 70%, 50%)`
  )
);
</script>

<template>
  <ChartContainer :config="chartConfig" class="h-[300px]">
    <VisSingleContainer :data="chartData" class="h-full">
      <VisDonut
        :value="(d: CollectionSize) => d.record_count"
        :color="(_d: CollectionSize, i: number) => colors[i]"
        :arc-width="80"
      />
    </VisSingleContainer>
  </ChartContainer>
</template>
