<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue"
import * as echarts from "echarts"
import { RouterLink, useRoute } from "vue-router"
import { API_BASE_URL, readApiResponse } from "../api"
import { authFetch, fetchAuthStatus, isAuthenticated } from "../auth"

const route = useRoute()

const run = ref(null)
const summary = ref([])
const loading = ref(false)
const error = ref("")
const expandedWorkIds = ref(new Set())
const fragmentsByWorkId = ref({})
const fragmentLoadingByWorkId = ref({})
const fragmentErrorsByWorkId = ref({})
const selectedWorkIds = ref(new Set())
const chartFilters = ref([])
const selectedXAxis = ref("year")
const selectedMetric = ref("distribution")
const selectedChartType = ref("stacked_bar")
const renderedChart = ref({
  xAxis: "year",
  metric: "distribution",
  type: "stacked_bar",
  visible: false,
})
const chartContainer = ref(null)
let pollTimer = null
let chartInstance = null

const runId = computed(() => route.params.runId)

const filterableFields = [
  { key: "year", label: "Год" },
  { key: "date", label: "Дата" },
  { key: "recipient", label: "Адресат" },
  { key: "place", label: "Место" },
  { key: "genre", label: "Жанр" },
  { key: "author", label: "Автор" },
]
const xAxisFields = [
  ...filterableFields.filter((field) => field.key !== "date"),
]
const metricOptions = [
  { key: "distribution", label: "Количество негативных, нейтральных и позитивных" },
]
const chartTypeOptions = computed(() => {
  return [
    { key: "stacked_bar", label: "Составные столбики" },
    { key: "grouped_bar", label: "Группированные столбики" },
    { key: "line", label: "Линии" },
  ]
})
const filteredSummary = computed(() => {
  return summary.value.filter((item) => {
    return chartFilters.value.every((filterRow) => {
      if (!filterRow.field || !filterRow.value) return true

      return getFieldValue(item, filterRow.field) === filterRow.value
    })
  })
})
const selectedFilteredSummary = computed(() => {
  return filteredSummary.value.filter((item) => selectedWorkIds.value.has(item.original_work_id))
})
const selectedFilteredWorksCount = computed(() => selectedFilteredSummary.value.length)
const allFilteredSelected = computed(() => {
  return filteredSummary.value.length > 0
    && filteredSummary.value.every((item) => selectedWorkIds.value.has(item.original_work_id))
})
const renderedXAxisLabel = computed(() => fieldLabel(renderedChart.value.xAxis))
const renderedMetricLabel = computed(() => {
  return metricOptions.find((option) => option.key === renderedChart.value.metric)?.label || ""
})
const renderedChartTypeLabel = computed(() => {
  return chartTypeOptions.value.find((option) => option.key === renderedChart.value.type)?.label || ""
})
const chartItems = computed(() => {
  if (!renderedChart.value.visible) return []

  return selectedFilteredSummary.value
})
const distributionChartGroups = computed(() => {
  const groups = {}

  chartItems.value.forEach((item) => {
    const label = getFieldDisplayValue(item, renderedChart.value.xAxis)
    const polarity = getWorkPolarity(item)
    const group = groups[label] || {
      label,
      works_count: 0,
      negative_count: 0,
      neutral_count: 0,
      positive_count: 0,
    }

    group.works_count += 1
    group.negative_count += polarity === "-1" ? 1 : 0
    group.neutral_count += polarity === "0" ? 1 : 0
    group.positive_count += polarity === "1" ? 1 : 0
    groups[label] = group
  })

  return Object.values(groups).sort(compareChartLabels)
})
const echartsOption = computed(() => {
  if (!renderedChart.value.visible || chartItems.value.length === 0) return null

  return buildDistributionChartOption()
})
const workTotals = computed(() => {
  const totalsByWork = {
    total: summary.value.length,
    negative: 0,
    neutral: 0,
    positive: 0,
  }

  summary.value.forEach((item) => {
    const polarity = getWorkPolarity(item)

    if (polarity === "-1") {
      totalsByWork.negative += 1
    } else if (polarity === "1") {
      totalsByWork.positive += 1
    } else {
      totalsByWork.neutral += 1
    }
  })

  return totalsByWork
})

const sentimentLabels = {
  "-1": {
    label: "Негативная",
    class: "bg-red-50 text-red-700 ring-red-200",
  },
  "0": {
    label: "Нейтральная",
    class: "bg-slate-100 text-slate-700 ring-slate-200",
  },
  "1": {
    label: "Позитивная",
    class: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  },
}

function percent(value, total) {
  if (!total) return 0

  return Math.round((value / total) * 100)
}

function scoreLabel(score) {
  return Number(score || 0).toFixed(2)
}

function scoreClass(score) {
  if (score < -0.15) return "text-red-700"
  if (score > 0.15) return "text-emerald-700"

  return "text-slate-700"
}

function getWorkPolarity(item) {
  const score = Number(item?.mean_score || 0)

  if (score < -0.15) return "-1"
  if (score > 0.15) return "1"

  return "0"
}

function fieldLabel(field) {
  return xAxisFields.find((option) => option.key === field)?.label || field
}

function getFieldValue(item, field) {
  const value = item?.[field]

  if (value === null || value === undefined || String(value).trim() === "") {
    return ""
  }

  return String(value).trim()
}

function getFieldDisplayValue(item, field) {
  return getFieldValue(item, field) || "Без значения"
}

function filterValueOptions(field) {
  if (!field) return []

  return [...new Set(summary.value.map((item) => getFieldValue(item, field)).filter(Boolean))]
    .sort(compareLabels)
}

function addChartFilter() {
  chartFilters.value = [
    ...chartFilters.value,
    { id: Date.now() + Math.random(), field: "year", value: "" },
  ]
}

function removeChartFilter(filterId) {
  chartFilters.value = chartFilters.value.filter((filterRow) => filterRow.id !== filterId)
}

function updateChartFilterField(filterRow, field) {
  filterRow.field = field
  filterRow.value = ""
}

function toggleWorkSelection(originalWorkId) {
  const nextSelectedIds = new Set(selectedWorkIds.value)

  if (nextSelectedIds.has(originalWorkId)) {
    nextSelectedIds.delete(originalWorkId)
  } else {
    nextSelectedIds.add(originalWorkId)
  }

  selectedWorkIds.value = nextSelectedIds
}

function selectFilteredWorks() {
  const nextSelectedIds = new Set(selectedWorkIds.value)

  filteredSummary.value.forEach((item) => {
    nextSelectedIds.add(item.original_work_id)
  })

  selectedWorkIds.value = nextSelectedIds
}

function deselectFilteredWorks() {
  const nextSelectedIds = new Set(selectedWorkIds.value)

  filteredSummary.value.forEach((item) => {
    nextSelectedIds.delete(item.original_work_id)
  })

  selectedWorkIds.value = nextSelectedIds
}

function clearSelectedWorks() {
  selectedWorkIds.value = new Set()
}

function generateChart() {
  renderedChart.value = {
    xAxis: selectedXAxis.value,
    metric: selectedMetric.value,
    type: selectedChartType.value,
    visible: true,
  }

  nextTick(() => {
    updateEcharts()
  })
}

function compareLabels(first, second) {
  const firstText = String(first || "")
  const secondText = String(second || "")
  const firstNumber = Number(firstText)
  const secondNumber = Number(secondText)

  if (Number.isFinite(firstNumber) && Number.isFinite(secondNumber)) {
    return firstNumber - secondNumber
  }

  return firstText.localeCompare(secondText, "ru")
}

function compareChartLabels(first, second) {
  return compareLabels(first.label, second.label)
}

function buildBaseChartOption() {
  return {
    color: ["#ef4444", "#94a3b8", "#10b981"],
    tooltip: {
      trigger: "axis",
      axisPointer: {
        type: "shadow",
      },
    },
    legend: {
      top: 0,
    },
    grid: {
      left: 48,
      right: 24,
      top: 56,
      bottom: distributionChartGroups.value.length > 8 ? 96 : 56,
      containLabel: true,
    },
    dataZoom: distributionChartGroups.value.length > 12
      ? [
          {
            type: "slider",
            bottom: 24,
            height: 22,
            labelFormatter: () => "",
          },
          {
            type: "inside",
          },
        ]
      : [],
  }
}

function buildDistributionChartOption() {
  const labels = distributionChartGroups.value.map((group) => group.label)
  const seriesType = renderedChart.value.type === "line" ? "line" : "bar"
  const stack = renderedChart.value.type === "stacked_bar" ? "sentiment" : undefined

  return {
    ...buildBaseChartOption(),
    tooltip: {
      trigger: "axis",
    },
    xAxis: {
      type: "category",
      name: renderedXAxisLabel.value,
      data: labels,
      axisLabel: chartAxisLabelOptions(labels),
    },
    yAxis: {
      type: "value",
      name: "Произведения",
      minInterval: 1,
    },
    series: [
      {
        name: "Негативные произведения",
        type: seriesType,
        stack,
        smooth: seriesType === "line",
        data: distributionChartGroups.value.map((group) => group.negative_count),
      },
      {
        name: "Нейтральные произведения",
        type: seriesType,
        stack,
        smooth: seriesType === "line",
        data: distributionChartGroups.value.map((group) => group.neutral_count),
      },
      {
        name: "Позитивные произведения",
        type: seriesType,
        stack,
        smooth: seriesType === "line",
        data: distributionChartGroups.value.map((group) => group.positive_count),
      },
    ],
  }
}

function chartAxisLabelOptions(labels) {
  return {
    show: true,
    interval: 0,
    rotate: labels.length > 6 ? 35 : 0,
    overflow: "truncate",
    width: 120,
  }
}

function updateEcharts() {
  if (!chartContainer.value || !echartsOption.value) return

  if (!chartInstance) {
    chartInstance = echarts.init(chartContainer.value)
  }

  chartInstance.setOption(echartsOption.value, true)
  chartInstance.resize()
}

function resizeEcharts() {
  chartInstance?.resize()
}

function disposeEcharts() {
  chartInstance?.dispose()
  chartInstance = null
}

function segmentationLabel(runData) {
  if (runData.max_segment_size) {
    return `фрагменты ${runData.segment_size}-${runData.max_segment_size} слов`
  }

  if (runData.window_step && runData.window_step !== runData.segment_size) {
    return `окна по ${runData.segment_size} слов, шаг ${runData.window_step}`
  }

  return `фрагменты по ${runData.segment_size} слов`
}

function sentimentMeta(label) {
  return sentimentLabels[label] || {
    label: label || "Неизвестно",
    class: "bg-slate-100 text-slate-700 ring-slate-200",
  }
}

function isWorkExpanded(originalWorkId) {
  return expandedWorkIds.value.has(originalWorkId)
}

function toggleExpandedWork(originalWorkId) {
  const nextExpandedIds = new Set(expandedWorkIds.value)

  if (nextExpandedIds.has(originalWorkId)) {
    nextExpandedIds.delete(originalWorkId)
    expandedWorkIds.value = nextExpandedIds
    return
  }

  nextExpandedIds.add(originalWorkId)
  expandedWorkIds.value = nextExpandedIds

  if (!fragmentsByWorkId.value[originalWorkId]) {
    fetchWorkFragments(originalWorkId)
  }
}

async function fetchWorkFragments(originalWorkId) {
  fragmentLoadingByWorkId.value = {
    ...fragmentLoadingByWorkId.value,
    [originalWorkId]: true,
  }
  fragmentErrorsByWorkId.value = {
    ...fragmentErrorsByWorkId.value,
    [originalWorkId]: "",
  }

  try {
    const response = await authFetch(
      `${API_BASE_URL}/sentiment/results/${runId.value}/works/${originalWorkId}/`
    )
    const data = await readApiResponse(response, "Не удалось загрузить фрагменты")

    if (!response.ok) {
      throw new Error(data.detail || "Не удалось загрузить фрагменты")
    }

    fragmentsByWorkId.value = {
      ...fragmentsByWorkId.value,
      [originalWorkId]: data.fragments || [],
    }
  } catch (err) {
    fragmentErrorsByWorkId.value = {
      ...fragmentErrorsByWorkId.value,
      [originalWorkId]: err.message || "Неизвестная ошибка",
    }
  } finally {
    fragmentLoadingByWorkId.value = {
      ...fragmentLoadingByWorkId.value,
      [originalWorkId]: false,
    }
  }
}

function clearPollTimer() {
  if (!pollTimer) return

  clearTimeout(pollTimer)
  pollTimer = null
}

function scheduleResultsPolling() {
  clearPollTimer()

  if (run.value?.status !== "running") return

  pollTimer = setTimeout(() => {
    fetchResults({ silent: true })
  }, 2500)
}

async function fetchResults({ silent = false } = {}) {
  if (!silent) {
    loading.value = true
  }

  error.value = ""

  const url = runId.value
    ? `${API_BASE_URL}/sentiment/results/${runId.value}/`
    : `${API_BASE_URL}/sentiment/results/`

  try {
    const response = await authFetch(url)
    const data = await readApiResponse(response, "Не удалось загрузить результаты анализа")

    if (!response.ok) {
      throw new Error(data.detail || "Не удалось загрузить результаты анализа")
    }

    run.value = data.run
    summary.value = data.summary
    if (selectedWorkIds.value.size === 0 && summary.value.length) {
      selectedWorkIds.value = new Set(summary.value.map((item) => item.original_work_id))
    }
    scheduleResultsPolling()
  } catch (err) {
    error.value = err.message || "Неизвестная ошибка"
    clearPollTimer()
  } finally {
    loading.value = false
  }
}

watch(runId, () => {
  clearPollTimer()
  expandedWorkIds.value = new Set()
  selectedWorkIds.value = new Set()
  chartFilters.value = []
  renderedChart.value = {
    xAxis: selectedXAxis.value,
    metric: selectedMetric.value,
    type: selectedChartType.value,
    visible: false,
  }
  disposeEcharts()
  fragmentsByWorkId.value = {}
  fragmentLoadingByWorkId.value = {}
  fragmentErrorsByWorkId.value = {}
  fetchResults()
})

watch(selectedMetric, () => {
  selectedChartType.value = chartTypeOptions.value[0]?.key || "stacked_bar"
})

watch(echartsOption, () => {
  if (!echartsOption.value) {
    disposeEcharts()
    return
  }

  nextTick(() => {
    updateEcharts()
  })
})

onMounted(async () => {
  await fetchAuthStatus()
  window.addEventListener("resize", resizeEcharts)

  if (isAuthenticated.value) {
    fetchResults()
  }
})

onUnmounted(() => {
  clearPollTimer()
  window.removeEventListener("resize", resizeEcharts)
  disposeEcharts()
})
</script>

<template>
  <main class="p-6">
    <div class="mx-auto max-w-7xl">
      <div class="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 class="text-3xl font-bold text-slate-900">
            Результаты анализа
          </h1>
          <p v-if="run" class="mt-2 text-slate-600">
            {{ run.model_name }}
          </p>
          <p
            v-if="run?.status === 'failed'"
            class="mt-2 text-sm font-medium text-red-700"
          >
            Анализ завершился ошибкой: {{ run.error_message || "подробности не указаны" }}
          </p>
        </div>
      </div>

      <div v-if="error" class="mb-4 rounded-xl bg-red-50 p-4 text-red-700">
        {{ error }}
      </div>

      <div
        v-if="!isAuthenticated"
        class="rounded-2xl bg-white p-5 text-slate-600 shadow-sm ring-1 ring-slate-200"
      >
        Результаты анализа доступны только вошедшим пользователям.
        <RouterLink to="/login" class="font-medium text-slate-900 underline">
          Войти
        </RouterLink>
      </div>

      <div v-else-if="loading" class="rounded-2xl bg-white p-5 text-slate-500 shadow-sm ring-1 ring-slate-200">
        Загружаю результаты...
      </div>

      <template v-else-if="run">
        <section class="mb-6 grid gap-4 md:grid-cols-4">
          <div class="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <p class="text-sm text-slate-500">Количество документов</p>
            <p class="mt-2 text-3xl font-bold text-slate-900">{{ workTotals.total }}</p>
          </div>
          <div class="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <p class="text-sm text-slate-500">Негативные</p>
            <p class="mt-2 text-3xl font-bold text-red-700">{{ workTotals.negative}}</p>
          </div>
          <div class="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <p class="text-sm text-slate-500">Нейтральные</p>
            <p class="mt-2 text-3xl font-bold text-slate-700">{{ workTotals.neutral }}</p>
          </div>
          <div class="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <p class="text-sm text-slate-500">Позитивные</p>
            <p class="mt-2 text-3xl font-bold text-emerald-700">{{ workTotals.positive }}</p>
          </div>
        </section>

        <section class="mb-6 rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
          <div class="border-b border-slate-200 px-5 py-4">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 class="text-lg font-semibold text-slate-900">
                  Конструктор графика
                </h2>
                <p class="mt-1 text-sm text-slate-600">
                  Найдено: {{ filteredSummary.length }} · выбрано в найденных: {{ selectedFilteredWorksCount }}
                </p>
              </div>
            </div>
          </div>

          <div class="space-y-5 p-5">
            <div class="space-y-3">
              <div
                v-for="filterRow in chartFilters"
                :key="filterRow.id"
                class="grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]"
              >
                <select
                  :value="filterRow.field"
                  class="w-full rounded-xl border border-slate-300 bg-white px-4 py-2 text-slate-900 outline-none focus:border-slate-500"
                  @change="updateChartFilterField(filterRow, $event.target.value)"
                >
                  <option
                    v-for="field in filterableFields"
                    :key="field.key"
                    :value="field.key"
                  >
                    {{ field.label }}
                  </option>
                </select>

                <select
                  v-model="filterRow.value"
                  class="w-full rounded-xl border border-slate-300 bg-white px-4 py-2 text-slate-900 outline-none focus:border-slate-500"
                >
                  <option value="">Любое значение</option>
                  <option
                    v-for="value in filterValueOptions(filterRow.field)"
                    :key="value"
                    :value="value"
                  >
                    {{ value }}
                  </option>
                </select>

                <button
                  type="button"
                  @click="removeChartFilter(filterRow.id)"
                  class="rounded-xl border border-red-200 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50"
                >
                  Удалить
                </button>
              </div>

              <button
                type="button"
                @click="addChartFilter"
                class="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
              >
                Добавить фильтр
              </button>
            </div>

            <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)_minmax(0,1fr)_auto]">
              <div>
                <label class="mb-1 block text-sm font-medium text-slate-700">
                  Ось X
                </label>
                <select
                  v-model="selectedXAxis"
                  class="w-full rounded-xl border border-slate-300 bg-white px-4 py-2 text-slate-900 outline-none focus:border-slate-500"
                >
                  <option
                    v-for="field in xAxisFields"
                    :key="field.key"
                    :value="field.key"
                  >
                    {{ field.label }}
                  </option>
                </select>
              </div>

              <div>
                <label class="mb-1 block text-sm font-medium text-slate-700">
                  Ось Y
                </label>
                <div class="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-slate-700">
                  {{ metricOptions[0].label }}
                </div>
              </div>

              <div>
                <label class="mb-1 block text-sm font-medium text-slate-700">
                  Тип графика
                </label>
                <select
                  v-model="selectedChartType"
                  class="w-full rounded-xl border border-slate-300 bg-white px-4 py-2 text-slate-900 outline-none focus:border-slate-500"
                >
                  <option
                    v-for="typeOption in chartTypeOptions"
                    :key="typeOption.key"
                    :value="typeOption.key"
                  >
                    {{ typeOption.label }}
                  </option>
                </select>
              </div>

              <div class="flex items-end">
                <button
                  type="button"
                  @click="generateChart"
                  :disabled="selectedFilteredWorksCount === 0"
                  class="w-full rounded-xl bg-slate-900 px-5 py-2 font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Построить
                </button>
              </div>
            </div>

            <div
              v-if="renderedChart.visible"
              class="overflow-hidden rounded-xl border border-slate-200"
            >
              <div class="border-b border-slate-200 bg-slate-50 px-4 py-3">
                <p class="font-semibold text-slate-900">
                  X: {{ renderedXAxisLabel }} · Y: {{ renderedMetricLabel }} · {{ renderedChartTypeLabel }}
                </p>
              </div>

              <div v-if="chartItems.length === 0" class="p-5 text-slate-500">
                Для выбранных условий нет выбранных работ.
              </div>

              <div v-else class="p-5">
                <div
                  ref="chartContainer"
                  class="h-[30rem] w-full"
                ></div>
              </div>
            </div>
          </div>
        </section>

        <section class="mb-6 overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
          <div class="border-b border-slate-200 px-5 py-4">
            <h2 class="text-lg font-semibold text-slate-900">
              Итоги
            </h2>
          </div>

          <div class="overflow-x-auto">
            <table class="w-full border-collapse text-left">
              <thead class="bg-slate-100 text-sm text-slate-700">
                <tr>
                  <th class="w-12 px-5 py-3 font-semibold">
                    <input
                      type="checkbox"
                      :checked="allFilteredSelected"
                      class="h-4 w-4 rounded border-slate-300"
                      title="Выбрать найденные"
                      @change="allFilteredSelected ? deselectFilteredWorks() : selectFilteredWorks()"
                    />
                  </th>
                  <th class="w-14 px-5 py-3 font-semibold"></th>
                  <th class="w-[36%] px-5 py-3 font-semibold">Название</th>
                  <th class="w-[12%] px-5 py-3 font-semibold">Среднее</th>
                  <th class="w-[12%] px-5 py-3 font-semibold">Нег.</th>
                  <th class="w-[12%] px-5 py-3 font-semibold">Нейтр.</th>
                  <th class="w-[12%] px-5 py-3 font-semibold">Поз.</th>
                  <th class="w-[16%] px-5 py-3 font-semibold">Фрагменты</th>
                </tr>
              </thead>

              <tbody class="divide-y divide-slate-200">
                <template
                  v-for="item in filteredSummary"
                  :key="item.original_work_id"
                >
                  <tr class="hover:bg-slate-50">
                    <td class="px-5 py-3 align-top">
                      <input
                        type="checkbox"
                        :checked="selectedWorkIds.has(item.original_work_id)"
                        class="mt-2 h-4 w-4 rounded border-slate-300"
                        :title="selectedWorkIds.has(item.original_work_id) ? 'Убрать из графика' : 'Добавить в график'"
                        @change="toggleWorkSelection(item.original_work_id)"
                      />
                    </td>
                    <td class="px-5 py-3 align-top">
                      <button
                        type="button"
                        :aria-expanded="isWorkExpanded(item.original_work_id)"
                        :aria-label="isWorkExpanded(item.original_work_id) ? 'Скрыть фрагменты' : 'Показать фрагменты'"
                        :title="isWorkExpanded(item.original_work_id) ? 'Скрыть фрагменты' : 'Показать фрагменты'"
                        class="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-300 text-lg leading-none text-slate-700 hover:bg-slate-100"
                        @click="toggleExpandedWork(item.original_work_id)"
                      >
                        {{ isWorkExpanded(item.original_work_id) ? "-" : "+" }}
                      </button>
                    </td>
                    <td class="px-5 py-3">
                      <RouterLink
                        v-if="item.work_id"
                        :to="{ name: 'work-detail', params: { id: item.work_id } }"
                        class="font-medium text-slate-900 hover:text-slate-600 hover:underline"
                      >
                        {{ item.title || "Без названия" }}
                      </RouterLink>
                      <span v-else class="font-medium text-slate-900">
                        {{ item.title || "Без названия" }}
                      </span>
                      <p class="mt-1 text-sm text-slate-500">
                        {{ item.author || "Автор не указан" }} · {{ item.date || "Дата не указана" }}
                      </p>
                    </td>
                    <td class="px-5 py-3 font-semibold" :class="scoreClass(item.mean_score)">
                      {{ item.mean_score.toFixed(2) }}
                    </td>
                    <td class="px-5 py-3 text-red-700">{{ item.negative_count }}</td>
                    <td class="px-5 py-3 text-slate-700">{{ item.neutral_count }}</td>
                    <td class="px-5 py-3 text-emerald-700">{{ item.positive_count }}</td>
                    <td class="px-5 py-3 text-slate-700">{{ item.segments_count }}</td>
                  </tr>

                  <tr v-if="isWorkExpanded(item.original_work_id)" class="bg-slate-50/70">
                    <td colspan="8" class="px-5 py-4">
                      <p
                        v-if="fragmentLoadingByWorkId[item.original_work_id]"
                        class="text-sm text-slate-500"
                      >
                        Загружаю фрагменты...
                      </p>

                      <p
                        v-else-if="fragmentErrorsByWorkId[item.original_work_id]"
                        class="text-sm text-red-700"
                      >
                        {{ fragmentErrorsByWorkId[item.original_work_id] }}
                      </p>

                      <div
                        v-else-if="fragmentsByWorkId[item.original_work_id]?.length"
                        class="space-y-3"
                      >
                        <article
                          v-for="fragment in fragmentsByWorkId[item.original_work_id]"
                          :key="fragment.segment_index"
                          class="rounded-xl border border-slate-200 bg-white p-4"
                        >
                          <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
                            <div class="flex flex-wrap items-center gap-3">
                              <p class="text-sm font-semibold text-slate-900">
                                Фрагмент {{ fragment.segment_index + 1 }}
                              </p>
                              <span
                                class="rounded-full px-3 py-1 text-xs font-medium ring-1"
                                :class="sentimentMeta(fragment.label).class"
                              >
                                {{ sentimentMeta(fragment.label).label }}
                              </span>
                            </div>
                            <p class="text-sm text-slate-500">
                              Слова {{ fragment.word_start + 1 }}-{{ fragment.word_end }}
                            </p>
                          </div>

                          <p class="whitespace-pre-wrap text-sm leading-6 text-slate-900">
                            {{ fragment.text }}
                          </p>
                        </article>
                      </div>

                      <p v-else class="text-sm text-slate-500">
                        Фрагменты еще не появились.
                      </p>
                    </td>
                  </tr>
                </template>

                <tr v-if="filteredSummary.length === 0">
                  <td colspan="8" class="px-5 py-8 text-center text-slate-500">
                    По фильтрам конструктора ничего не найдено.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </template>
    </div>
  </main>
</template>
