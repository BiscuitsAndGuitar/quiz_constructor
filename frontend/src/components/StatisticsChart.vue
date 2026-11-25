<script setup>
import { computed } from 'vue'
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, LineElement, PointElement, Tooltip, Legend, Title } from 'chart.js'
import { Bar, Line } from 'vue-chartjs'

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, Tooltip, Legend, Title)
const props = defineProps({ data: { type: Object, required: true }, horizontal: Boolean, line: Boolean, percent: Boolean, title: { type: String, required: true } })
const options = computed(() => ({
  responsive: true, maintainAspectRatio: false,
  indexAxis: props.horizontal ? 'y' : 'x',
  plugins: { legend: { display: false }, title: { display: true, text: props.title } },
  scales: { [props.horizontal ? 'x' : 'y']: { beginAtZero: true, max: props.percent ? 100 : undefined, ticks: { precision: props.percent ? 1 : 0 } } },
}))
</script>

<template>
  <div class="statistics-chart" :style="{ height: `${horizontal ? Math.max(240, data.labels.length * 42 + 80) : 300}px` }">
    <Line v-if="line" :data="data" :options="options" :aria-label="title" role="img" />
    <Bar v-else :data="data" :options="options" :aria-label="title" role="img" />
  </div>
  <details><summary>Данные диаграммы</summary><table><tbody><tr v-for="(label, index) in data.labels" :key="index"><th>{{ label }}</th><td>{{ data.datasets[0].data[index] }}{{ percent ? '%' : '' }}</td></tr></tbody></table></details>
</template>

<style scoped>
.statistics-chart { position: relative; min-width: 0; width: 100%; }
details { margin-bottom: 1rem; overflow-wrap: anywhere; }
</style>
