<script setup lang="ts">
/**
 * Function Statistics Bar Chart Component
 *
 * Displays a bar chart showing average runtime and error rate for functions.
 */
import { computed } from "vue";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { Bar } from "vue-chartjs";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

interface FunctionStat {
  function_name: string;
  avg_runtime_ms: number | null;
  error_rate: number;
  total_calls: number;
}

const props = defineProps<{
  data: FunctionStat[];
}>();

const chartData = computed(() => {
  if (!props.data || props.data.length === 0) {
    return {
      labels: [],
      datasets: [],
    };
  }

  return {
    labels: props.data.map((item) => item.function_name),
    datasets: [
      {
        label: "Average Runtime (ms)",
        data: props.data.map((item) => item.avg_runtime_ms || 0),
        backgroundColor: "rgba(59, 130, 246, 0.6)",
        borderColor: "rgb(59, 130, 246)",
        borderWidth: 1,
        yAxisID: "y",
      },
      {
        label: "Error Rate (%)",
        data: props.data.map((item) => item.error_rate),
        backgroundColor: "rgba(239, 68, 68, 0.6)",
        borderColor: "rgb(239, 68, 68)",
        borderWidth: 1,
        yAxisID: "y1",
      },
    ],
  };
});

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: "index" as const,
    intersect: false,
  },
  plugins: {
    legend: {
      position: "top" as const,
    },
    tooltip: {
      callbacks: {
        afterLabel: (context: any) => {
          const index = context.dataIndex;
          const stat = props.data[index];
          return `Total calls: ${stat.total_calls.toLocaleString()}`;
        },
      },
    },
  },
  scales: {
    x: {
      stacked: false,
    },
    y: {
      type: "linear" as const,
      display: true,
      position: "left" as const,
      title: {
        display: true,
        text: "Runtime (ms)",
      },
      beginAtZero: true,
    },
    y1: {
      type: "linear" as const,
      display: true,
      position: "right" as const,
      title: {
        display: true,
        text: "Error Rate (%)",
      },
      beginAtZero: true,
      max: 100,
      grid: {
        drawOnChartArea: false,
      },
    },
  },
};
</script>

<template>
  <div class="chart-container">
    <Bar :data="chartData" :options="chartOptions" />
  </div>
</template>

<style scoped>
.chart-container {
  position: relative;
  height: 300px;
  width: 100%;
}
</style>
