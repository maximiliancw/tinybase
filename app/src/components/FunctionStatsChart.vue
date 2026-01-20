<script setup lang="ts">
/**
 * Function Statistics Bar Chart Component
 *
 * Displays a bar chart showing average runtime and error rate for functions using Unovis.
 */
import { computed } from "vue";
import { VisXYContainer, VisGroupedBar, VisAxis, VisTooltip } from "@unovis/vue";
import { ChartContainer } from "@/components/ui/chart";

interface FunctionStat {
  function_name: string;
  avg_runtime_ms: number | null;
  error_rate: number;
  total_calls: number;
}

const props = defineProps<{
  data: FunctionStat[];
}>();

const chartData = computed(() => props.data || []);

const chartConfig = {
  avg_runtime_ms: {
    label: "Avg Runtime (ms)",
    color: "hsl(var(--primary))",
  },
  error_rate: {
    label: "Error Rate (%)",
    color: "hsl(var(--destructive))",
  },
};
</script>

<template>
  <ChartContainer :config="chartConfig" class="h-[300px]">
    <VisXYContainer :data="chartData" class="h-full">
      <VisGroupedBar
        :x="(d: FunctionStat, i: number) => i"
        :y="[(d: FunctionStat) => d.avg_runtime_ms || 0, (d: FunctionStat) => d.error_rate]"
        :color="['hsl(var(--primary))', 'hsl(var(--destructive))']"
      />
      <VisAxis type="x" :tick-format="(i: number) => chartData[i]?.function_name || ''" />
      <VisAxis type="y" label="Runtime (ms)" />
      <VisTooltip />
    </VisXYContainer>
  </ChartContainer>
</template>
