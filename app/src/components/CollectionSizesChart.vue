<script setup lang="ts">
/**
 * Collection Sizes Pie Chart Component
 *
 * Displays a pie chart showing the distribution of records across collections.
 */
import { computed, onMounted, ref } from "vue";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";
import { Pie } from "vue-chartjs";

ChartJS.register(ArcElement, Tooltip, Legend);

interface CollectionSize {
  collection_name: string;
  record_count: number;
}

const props = defineProps<{
  data: CollectionSize[];
}>();

const chartData = computed(() => {
  if (!props.data || props.data.length === 0) {
    return {
      labels: [],
      datasets: [
        {
          data: [],
          backgroundColor: [],
        },
      ],
    };
  }

  // Generate colors for each collection
  const colors = [
    "#3b82f6", // blue
    "#10b981", // green
    "#f59e0b", // amber
    "#ef4444", // red
    "#8b5cf6", // purple
    "#06b6d4", // cyan
    "#f97316", // orange
    "#84cc16", // lime
    "#ec4899", // pink
    "#6366f1", // indigo
  ];

  return {
    labels: props.data.map((item) => item.collection_name),
    datasets: [
      {
        data: props.data.map((item) => item.record_count),
        backgroundColor: props.data.map(
          (_, index) => colors[index % colors.length]
        ),
        borderWidth: 1,
        borderColor: "#ffffff",
      },
    ],
  };
});

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: "right" as const,
      labels: {
        padding: 15,
        usePointStyle: true,
      },
    },
    tooltip: {
      callbacks: {
        label: (context: any) => {
          const label = context.label || "";
          const value = context.parsed || 0;
          const total = context.dataset.data.reduce(
            (a: number, b: number) => a + b,
            0
          );
          const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
          return `${label}: ${value.toLocaleString()} records (${percentage}%)`;
        },
      },
    },
  },
};
</script>

<template>
  <div class="chart-container">
    <Pie :data="chartData" :options="chartOptions" />
  </div>
</template>

<style scoped>
.chart-container {
  position: relative;
  height: 300px;
  width: 100%;
}
</style>
